#!/usr/bin/env python3
"""
Test GD32 Version Request (Command 0x07)

This script tests different sync byte and baud rate combinations
to find the correct protocol parameters by requesting firmware version.

WARNING: Stop AuxCtrl before running this to avoid conflicts!
"""

import serial
import struct
import time
import sys

CMD_REQUIRE_VERSION = 0x07

# Possible sync byte combinations to try
SYNC_COMBINATIONS = [
    (0xFA, 0xFB, "Common pattern 1"),
    (0xAA, 0x55, "Classic embedded"),
    (0xFA, 0xAF, "3irobotix pattern"),
    (0x5A, 0xA5, "Alternative pattern"),
]

# Possible baud rates to try
BAUD_RATES = [115200, 230400, 460800, 57600, 9600]

def calculate_crc_sum(data):
    """Simple arithmetic sum"""
    return sum(data) & 0xFFFF

def calculate_crc16_ccitt(data):
    """CRC-16-CCITT"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
        crc &= 0xFFFF
    return crc

def calculate_crc16_modbus(data):
    """CRC-16-MODBUS"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc = crc >> 1
    return crc

def build_packet(sync1, sync2, cmd_id, payload, crc_func):
    """Build packet with specified parameters"""
    length = len(payload)
    packet_base = bytes([sync1, sync2, length, cmd_id]) + payload
    crc = crc_func(packet_base)
    packet = packet_base + struct.pack('>H', crc)
    return packet

def test_combination(port, baudrate, sync1, sync2, desc):
    """Test a specific sync byte combination"""
    print(f"\n{'='*80}")
    print(f"Testing: {desc}")
    print(f"Baud: {baudrate}, SYNC1: 0x{sync1:02X}, SYNC2: 0x{sync2:02X}")
    print(f"{'='*80}")

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.2
        )
    except Exception as e:
        print(f"[!] Failed to open port: {e}")
        return False

    # Try different CRC algorithms
    crc_algorithms = [
        (calculate_crc_sum, "SUM"),
        (calculate_crc16_ccitt, "CRC16-CCITT"),
        (calculate_crc16_modbus, "CRC16-MODBUS"),
    ]

    for crc_func, crc_name in crc_algorithms:
        packet = build_packet(sync1, sync2, CMD_REQUIRE_VERSION, b'', crc_func)

        print(f"\n[>] Trying CRC: {crc_name}")
        print(f"[>] Packet: {packet.hex(' ')}")

        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Send packet
        ser.write(packet)
        ser.flush()

        # Wait for response
        time.sleep(0.1)

        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"[<] RESPONSE! ({len(response)} bytes): {response.hex(' ')}")
            print(f"[<] ASCII: {response}")

            # Try to parse response
            if len(response) >= 4:
                r_sync1 = response[0]
                r_sync2 = response[1]
                r_len = response[2]
                r_cmd = response[3]
                print(f"[<] Parsed: SYNC1=0x{r_sync1:02X}, SYNC2=0x{r_sync2:02X}, LEN={r_len}, CMD=0x{r_cmd:02X}")

                if r_sync1 == sync1 and r_sync2 == sync2:
                    print(f"[+] MATCH FOUND! Sync bytes confirmed!")
                    print(f"[+] Baud: {baudrate}, CRC: {crc_name}")
                    ser.close()
                    return True

            ser.close()
            return True  # Got some response
        else:
            print(f"[<] No response")

    ser.close()
    return False

def main():
    port = '/dev/ttyS1'

    print("="*80)
    print("GD32 Version Request Test")
    print("="*80)
    print()
    print("[!] WARNING: Make sure AuxCtrl is stopped!")
    print("[!] Run: killall AuxCtrl")
    print()

    input("Press Enter to continue...")

    # Test all combinations
    for baudrate in BAUD_RATES:
        for sync1, sync2, desc in SYNC_COMBINATIONS:
            if test_combination(port, baudrate, sync1, sync2, desc):
                print("\n[+] Got response! Check output above for details.")
                print("\n[?] Continue testing other combinations? (y/N): ", end='')
                choice = input().strip().lower()
                if choice != 'y':
                    return

    print("\n[!] No valid responses found.")
    print("\n[i] Next steps:")
    print("    1. Capture actual AuxCtrl traffic: strace -e write -s 1000 -p $(pidof AuxCtrl)")
    print("    2. Check if port is correct: ls -la /dev/ttyS*")
    print("    3. Verify GD32 is powered and responding")

if __name__ == '__main__':
    main()
