#!/usr/bin/env python3
"""
Analyze serial communication capture logs and reconstruct packets
"""

import re
import sys
from collections import defaultdict, Counter

# Known commands from AuxCtrl-Details.md
COMMANDS_TX = {
    0x04: "STM32_SLEEP",
    0x05: "WAKEUP_ACK",
    0x06: "HEARTBEAT",
    0x07: "REQUIRE_VERSION",
    0x08: "SET_IMU_ZERO",
    0x0A: "RESET_ERROR_CODE",
    0x0D: "HEARTBEAT/STATUS_REQUEST",
    0x65: "MOTOR_CONTROL_TYPE",
    0x66: "MOTOR_VELOCITY",
    0x67: "MOTOR_SPEED",
    0x68: "BLOWER_SPEED",
    0x69: "BRUSH_SPEED",
    0x6A: "ROLLING_SPEED",
    0x78: "CLIFF_IR_CONTROL",
    0x79: "CLIFF_IR_DIRECTION",
    0x8D: "BUTTON_LED_STATE",
    0x97: "LIDAR_POWER",
    0x99: "R16_POWER",
    0x9A: "RESTART_R16",
    0x9B: "CHARGER_POWER",
    0xA1: "IMU_FACTORY_CALIBRATE",
    0xA2: "IMU_FACTORY_STATE",
    0xA3: "GEO_MAGNETISM_CALIBRATE",
    0xA4: "GEO_MAGNETISM_STATE",
}

COMMANDS_RX = {
    0x15: "CMD_SENSOR",
}

def parse_strace_line(line):
    """Parse strace output line"""
    # Match: 552   write(5, "\xfa\xfb\x03...", 14) = 14
    # Or:    write(5, "\xfa\xfb\x03...", 14) = 14
    match = re.search(r'\s*(read|write)\((\d+),\s*"([^"]+)".*?\)\s*=\s*(\d+)', line)
    if not match:
        return None

    direction = match.group(1)
    fd = int(match.group(2))
    hex_str = match.group(3)
    byte_count = int(match.group(4))

    # Convert \xHH format to bytes
    hex_bytes = re.findall(r'\\x([0-9a-fA-F]{2})', hex_str)
    if not hex_bytes:
        return None

    packet_bytes = bytes([int(b, 16) for b in hex_bytes])

    return {
        'direction': direction,
        'fd': fd,
        'data': packet_bytes,
        'length': byte_count
    }

def parse_packet(data):
    """Parse protocol packet structure"""
    if len(data) < 4:
        return None

    if data[0] != 0xFA or data[1] != 0xFB:
        return None  # Invalid sync bytes

    length = data[2]
    cmd_id = data[3]

    # Length includes CMD + DATA + CRC
    expected_total = 3 + length  # SYNC1 + SYNC2 + LEN + (CMD + DATA + CRC)

    if len(data) < expected_total:
        return None  # Incomplete packet

    if length == 0:
        # No payload or CRC
        crc = None
        payload = b''
    else:
        # Last byte of the length field is CRC
        # Length includes: CMD (1 byte) + PAYLOAD (n bytes) + CRC (1 byte)
        crc_pos = 2 + length  # SYNC1 + SYNC2 + LEN bytes = index where CRC is
        if crc_pos >= len(data):
            return None
        crc = data[crc_pos]
        # Payload is between CMD and CRC
        payload = data[4:crc_pos]

    return {
        'sync1': data[0],
        'sync2': data[1],
        'length': length,
        'cmd_id': cmd_id,
        'payload': payload,
        'crc': crc,
        'raw': data[:expected_total]
    }

def format_packet(pkt, direction):
    """Format packet for display"""
    if not pkt:
        return "Invalid packet"

    cmd_dict = COMMANDS_TX if direction == 'TX' else COMMANDS_RX
    cmd_name = cmd_dict.get(pkt['cmd_id'], f"UNKNOWN_0x{pkt['cmd_id']:02X}")

    parts = [
        f"[{direction}]",
        f"CMD: 0x{pkt['cmd_id']:02X} ({cmd_name})",
        f"LEN: {pkt['length']}",
    ]

    if len(pkt['payload']) > 0:
        parts.append(f"DATA: {pkt['payload'].hex(' ')}")

    if pkt['crc'] is not None:
        parts.append(f"CRC: 0x{pkt['crc']:02X}")

    parts.append(f"RAW: {pkt['raw'].hex(' ')}")

    return " | ".join(parts)

def analyze_file(filename):
    """Analyze capture file"""
    print(f"Analyzing: {filename}")
    print("=" * 100)
    print()

    tx_packets = []
    rx_data = bytearray()

    with open(filename, 'r') as f:
        for line in f:
            parsed = parse_strace_line(line)
            if not parsed:
                continue

            if parsed['direction'] == 'write':
                # TX packet
                pkt = parse_packet(parsed['data'])
                if pkt:
                    tx_packets.append(pkt)
            elif parsed['direction'] == 'read':
                # RX data (accumulate)
                rx_data.extend(parsed['data'])

    # Analyze TX packets
    print(f"Total TX packets: {len(tx_packets)}")
    print()

    # Count command frequency
    cmd_counter = Counter([p['cmd_id'] for p in tx_packets])
    print("TX Command Frequency:")
    for cmd_id, count in cmd_counter.most_common():
        cmd_name = COMMANDS_TX.get(cmd_id, f"UNKNOWN_0x{cmd_id:02X}")
        print(f"  0x{cmd_id:02X} {cmd_name:30s} : {count:5d} packets")

    print()
    print("=" * 100)
    print("Sample TX Packets (first 10 unique):")
    print("=" * 100)

    seen_packets = set()
    for pkt in tx_packets[:100]:  # Check first 100
        pkt_sig = (pkt['cmd_id'], bytes(pkt['payload']))
        if pkt_sig not in seen_packets:
            seen_packets.add(pkt_sig)
            print(format_packet(pkt, 'TX'))
            if len(seen_packets) >= 10:
                break

    print()
    print("=" * 100)
    print("RX Data Analysis:")
    print("=" * 100)
    print(f"Total bytes received: {len(rx_data)}")
    print()

    # Try to find packets in RX data
    i = 0
    rx_packets = []
    while i < len(rx_data) - 3:
        if rx_data[i] == 0xFA and rx_data[i+1] == 0xFB:
            # Found potential packet
            remaining = rx_data[i:]
            pkt = parse_packet(remaining)
            if pkt:
                rx_packets.append(pkt)
                i += len(pkt['raw'])
                continue
        i += 1

    print(f"RX packets reconstructed: {len(rx_packets)}")
    print()

    if rx_packets:
        # Count RX commands
        rx_cmd_counter = Counter([p['cmd_id'] for p in rx_packets])
        print("RX Command Frequency:")
        for cmd_id, count in rx_cmd_counter.most_common():
            cmd_name = COMMANDS_RX.get(cmd_id, f"UNKNOWN_0x{cmd_id:02X}")
            print(f"  0x{cmd_id:02X} {cmd_name:30s} : {count:5d} packets")

        print()
        print("Sample RX Packets (first 5):")
        for pkt in rx_packets[:5]:
            print(format_packet(pkt, 'RX'))
    else:
        print("No valid RX packets found. Showing raw hex dump (first 200 bytes):")
        print(rx_data[:200].hex(' '))

    print()
    print("=" * 100)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <capture_log_file>")
        sys.exit(1)

    analyze_file(sys.argv[1])
