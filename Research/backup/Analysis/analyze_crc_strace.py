#!/usr/bin/env python3
"""
Analyze CRC from strace log to reverse-engineer the algorithm.
"""

import re

def parse_strace_log(filename):
    """Parse strace log and extract packets."""
    packets = []

    with open(filename, 'r') as f:
        for line in f:
            # Match write() calls: write(5, "\xfa\xfb\x03\x06\x00\x06", 6) = 6
            match = re.search(r'write\([^,]+,\s*"([^"]+)"', line)
            if match:
                hex_str = match.group(1)

                # Convert escape sequences to bytes
                packet = bytearray()
                i = 0
                while i < len(hex_str):
                    if hex_str[i:i+2] == '\\x':
                        # Hex byte
                        packet.append(int(hex_str[i+2:i+4], 16))
                        i += 4
                    else:
                        # ASCII char
                        packet.append(ord(hex_str[i]))
                        i += 1

                if packet and packet[0] == 0xFA and packet[1] == 0xFB:
                    packets.append(bytes(packet))

    return packets

def test_crc_on_packet(packet):
    """Test various CRC algorithms on a single packet."""
    if len(packet) < 4:
        return None

    sync1, sync2, length, cmd_id = packet[0], packet[1], packet[2], packet[3]

    if sync1 != 0xFA or sync2 != 0xFB:
        return None

    # CRC is last byte
    actual_crc = packet[-1]

    # Data between CMD and CRC
    # Format: FA FB LEN CMD [DATA...] CRC
    data_bytes = packet[4:-1]

    results = {}

    # Test 1: XOR of LEN, CMD, and all DATA
    calc = length
    calc ^= cmd_id
    for b in data_bytes:
        calc ^= b
    results['xor_len_cmd_data'] = (calc, calc == actual_crc)

    # Test 2: Sum of LEN, CMD, and all DATA
    calc = (length + cmd_id + sum(data_bytes)) & 0xFF
    results['sum_len_cmd_data'] = (calc, calc == actual_crc)

    # Test 3: Just CMD XOR all DATA
    calc = cmd_id
    for b in data_bytes:
        calc ^= b
    results['xor_cmd_data'] = (calc, calc == actual_crc)

    # Test 4: Just sum of all DATA
    calc = sum(data_bytes) & 0xFF
    results['sum_data'] = (calc, calc == actual_crc)

    # Test 5: XOR all (including sync)
    calc = 0
    for b in packet[:-1]:  # All except CRC
        calc ^= b
    results['xor_all'] = (calc, calc == actual_crc)

    # Test 6: Sum all (including sync)
    calc = sum(packet[:-1]) & 0xFF
    results['sum_all'] = (calc, calc == actual_crc)

    # Test 7: XOR of LEN and CMD only
    calc = length ^ cmd_id
    results['xor_len_cmd'] = (calc, calc == actual_crc)

    return {
        'packet': packet,
        'length': length,
        'cmd': cmd_id,
        'data': data_bytes,
        'actual_crc': actual_crc,
        'results': results
    }

def main():
    print("=" * 80)
    print("CRC Analysis from strace Log")
    print("=" * 80)
    print()

    filename = 'serial_capture_20251028_163742.log'
    print(f"Parsing {filename}...")

    packets = parse_strace_log(filename)
    print(f"Found {len(packets)} packets")
    print()

    # Collect algorithm votes
    algorithm_votes = {}

    # Analyze unique packet types
    unique_packets = []
    seen = set()

    for packet in packets:
        key = packet.hex()
        if key not in seen:
            seen.add(key)
            unique_packets.append(packet)

    print(f"Analyzing {len(unique_packets)} unique packet types...")
    print()

    for i, packet in enumerate(unique_packets[:10]):  # Analyze first 10 unique types
        analysis = test_crc_on_packet(packet)
        if not analysis:
            continue

        print(f"Packet {i+1}:")
        print(f"  Raw: {packet.hex(' ')}")
        print(f"  LEN: 0x{analysis['length']:02X} ({analysis['length']})")
        print(f"  CMD: 0x{analysis['cmd']:02X}")
        print(f"  DATA: {analysis['data'].hex(' ') if analysis['data'] else '(none)'}")
        print(f"  CRC: 0x{analysis['actual_crc']:02X}")
        print()

        # Show matches
        matches = [name for name, (calc, match) in analysis['results'].items() if match]

        if matches:
            print(f"  ✓ Matching algorithms: {', '.join(matches)}")
            for algo in matches:
                algorithm_votes[algo] = algorithm_votes.get(algo, 0) + 1
        else:
            print("  ✗ No match! Algorithm results:")
            for name, (calc, match) in analysis['results'].items():
                print(f"      {name:25s}: calculated=0x{calc:02X}, actual=0x{analysis['actual_crc']:02X}")

        print()

    # Final results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    if algorithm_votes:
        print("Algorithm success rate:")
        total = len(unique_packets[:10])
        for algo, count in sorted(algorithm_votes.items(), key=lambda x: x[1], reverse=True):
            print(f"  {algo:25s}: {count}/{total} packets")

        winner = max(algorithm_votes.items(), key=lambda x: x[1])
        print()
        print(f"✓ Winner: {winner[0]} ({winner[1]}/{total} matches)")
    else:
        print("✗ No algorithm matched!")

if __name__ == '__main__':
    main()
