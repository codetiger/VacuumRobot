#!/usr/bin/env python3
"""
Reverse engineer the CRC algorithm by analyzing captured packets.
We have many valid packets with known CRC values - we can test different algorithms.
"""

import re
from typing import List, Tuple

def parse_hexdump(filename: str) -> List[bytes]:
    """Parse hexdump output and extract complete packets."""
    packets = []
    current_packet = bytearray()

    with open(filename, 'r') as f:
        for line in f:
            # Parse hexdump format: "00000000  fa fb 03 06 00 06  |......|"
            match = re.search(r'  ([0-9a-f ]{47})', line)
            if match:
                hex_bytes = match.group(1).strip().split()
                for byte_str in hex_bytes:
                    if byte_str:  # Skip empty strings
                        byte_val = int(byte_str, 16)

                        # Check for packet start
                        if byte_val == 0xFA:
                            if current_packet:
                                packets.append(bytes(current_packet))
                            current_packet = bytearray([byte_val])
                        else:
                            current_packet.append(byte_val)

        # Don't forget last packet
        if current_packet:
            packets.append(bytes(current_packet))

    return packets

def test_crc_algorithms(packet: bytes) -> dict:
    """Test various CRC algorithms on a packet."""
    if len(packet) < 4:
        return {}

    # Packet format: FA FB LEN CMD [DATA...] CRC
    sync1, sync2, length, cmd_id = packet[0], packet[1], packet[2], packet[3]

    if sync1 != 0xFA or sync2 != 0xFB:
        return {}

    # CRC is the last byte
    actual_crc = packet[-1]

    # Data to checksum (everything except CRC)
    data = packet[:-1]

    results = {}

    # Test 1: Sum of all bytes (including sync)
    calc = sum(data) & 0xFF
    results['sum_all'] = (calc, calc == actual_crc)

    # Test 2: Sum without sync bytes
    calc = sum(data[2:]) & 0xFF
    results['sum_no_sync'] = (calc, calc == actual_crc)

    # Test 3: XOR of all bytes
    calc = 0
    for b in data:
        calc ^= b
    results['xor_all'] = (calc, calc == actual_crc)

    # Test 4: XOR without sync
    calc = 0
    for b in data[2:]:
        calc ^= b
    results['xor_no_sync'] = (calc, calc == actual_crc)

    # Test 5: Sum of length, cmd, and data only
    calc = sum(data[2:]) & 0xFF
    results['sum_payload'] = (calc, calc == actual_crc)

    # Test 6: Simple CRC-8 (polynomial 0x07)
    crc = 0
    for b in data[2:]:  # Skip sync bytes
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc = crc << 1
        crc &= 0xFF
    results['crc8_0x07'] = (crc, crc == actual_crc)

    # Test 7: Simple CRC-8 (polynomial 0x31)
    crc = 0
    for b in data[2:]:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x31
            else:
                crc = crc << 1
        crc &= 0xFF
    results['crc8_0x31'] = (crc, crc == actual_crc)

    # Test 8: Simple CRC-8 (polynomial 0x8C) - Dallas/Maxim
    crc = 0
    for b in data[2:]:
        crc ^= b
        for _ in range(8):
            if crc & 0x01:
                crc = (crc >> 1) ^ 0x8C
            else:
                crc = crc >> 1
    results['crc8_dallas'] = (crc, crc == actual_crc)

    return results, packet

def main():
    print("=" * 80)
    print("CRC Algorithm Reverse Engineering")
    print("=" * 80)
    print()

    # Parse the largest capture file
    filename = 'serial_capture_20251028_163742.log'
    print(f"Parsing {filename}...")

    try:
        packets = parse_hexdump(filename)
        print(f"Found {len(packets)} packets")
        print()

        # Analyze first 20 packets to find the algorithm
        algorithm_votes = {}

        for i, packet in enumerate(packets[:20]):
            if len(packet) < 4:
                continue

            results, pkt = test_crc_algorithms(packet)
            if not results:
                continue

            # Show packet details
            print(f"Packet {i+1}: {packet.hex(' ')}")
            print(f"  Length: {len(packet)} bytes")
            if len(packet) >= 4:
                print(f"  CMD: 0x{packet[3]:02X}")
                print(f"  Actual CRC: 0x{packet[-1]:02X}")

            # Show which algorithms match
            matches = [name for name, (calc, match) in results.items() if match]
            if matches:
                print(f"  ✓ Matching algorithms: {', '.join(matches)}")
                for algo in matches:
                    algorithm_votes[algo] = algorithm_votes.get(algo, 0) + 1
            else:
                print("  ✗ No algorithm matched!")
                print("  Algorithm results:")
                for name, (calc, match) in results.items():
                    print(f"    {name:20s}: 0x{calc:02X}")
            print()

        # Show final results
        print("=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        print()

        if algorithm_votes:
            print("Algorithm success rate:")
            for algo, count in sorted(algorithm_votes.items(), key=lambda x: x[1], reverse=True):
                print(f"  {algo:20s}: {count}/20 packets")
            print()

            # Get the winner
            winner = max(algorithm_votes.items(), key=lambda x: x[1])
            print(f"✓ Most likely CRC algorithm: {winner[0]} ({winner[1]}/20 matches)")
        else:
            print("✗ No CRC algorithm matched the packets!")
            print()
            print("This suggests a more complex CRC algorithm or different structure.")
            print("Recommend using Ghidra to decompile the calcCheckSum function.")

    except FileNotFoundError:
        print(f"Error: {filename} not found")
        print("Please ensure the capture file is in the current directory.")

if __name__ == '__main__':
    main()
