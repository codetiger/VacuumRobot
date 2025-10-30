#!/usr/bin/env python3
"""
Heartbeat Monitor - Send periodic heartbeats to GD32 and log responses

This script:
1. Sends heartbeat packets (0x06) every 50ms to keep GD32 alive
2. Captures and logs all responses from GD32
3. Parses sensor data packets (0x15) to show real-time sensor values
4. Runs for specified duration or until Ctrl+C

Usage: python3 heartbeat_monitor.py [duration_seconds]
"""

import serial
import time
import sys
import signal
from datetime import datetime

# Protocol constants
SYNC1 = 0xFA
SYNC2 = 0xFB
CMD_HEARTBEAT = 0x06
CMD_SENSOR = 0x15

# Global flag for clean shutdown
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n\n[*] Shutting down...")
    running = False

def build_heartbeat_packet():
    """Build heartbeat packet: FA FB 03 06 00 06"""
    # LENGTH = 3 (CMD + DATA + CRC)
    # CMD = 0x06
    # DATA = 0x00 (no data)
    # CRC = 0x06 (observed from captures)
    return bytes([SYNC1, SYNC2, 0x03, CMD_HEARTBEAT, 0x00, 0x06])

def parse_packet(data):
    """Parse received packet"""
    if len(data) < 4:
        return None

    if data[0] != SYNC1 or data[1] != SYNC2:
        return None

    length = data[2]
    cmd_id = data[3]

    expected_total = 3 + length  # SYNC1 + SYNC2 + LEN + (CMD + DATA + CRC)

    if len(data) < expected_total:
        return None

    if length > 0:
        crc = data[2 + length]
        payload = data[4:2 + length]
    else:
        crc = None
        payload = b''

    return {
        'cmd_id': cmd_id,
        'length': length,
        'payload': payload,
        'crc': crc,
        'raw': data[:expected_total]
    }

def parse_sensor_data(payload):
    """Parse sensor data payload (99 bytes based on captures)"""
    if len(payload) < 97:  # 99 - 1 CMD - 1 CRC = 97 data bytes
        return None

    # This is a guess based on typical robot sensor layouts
    # Will need to be refined by observing actual data changes
    try:
        import struct

        # Assuming little-endian int32 values at various offsets
        # These offsets are guesses and will be validated by observation

        sensor_info = {
            'timestamp_offset_0': struct.unpack('<I', payload[0:4])[0],
            'value_offset_4': struct.unpack('<I', payload[4:8])[0],
            'encoder_left?': struct.unpack('<I', payload[12:16])[0],
            'encoder_right?': struct.unpack('<I', payload[20:24])[0],
            'imu_accel_x?': struct.unpack('<h', payload[40:42])[0],
            'imu_accel_y?': struct.unpack('<h', payload[42:44])[0],
            'imu_accel_z?': struct.unpack('<h', payload[44:46])[0],
            'imu_gyro_x?': struct.unpack('<h', payload[46:48])[0],
            'imu_gyro_y?': struct.unpack('<h', payload[48:50])[0],
            'imu_gyro_z?': struct.unpack('<h', payload[50:52])[0],
            'battery?': payload[70:72].hex(),
            'bumper?': payload[80],
            'cliff?': payload[82],
        }
        return sensor_info
    except Exception as e:
        return None

def format_timestamp():
    """Get formatted timestamp"""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def main():
    global running

    # Parse arguments
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60  # Default 60 seconds
    serial_port = '/dev/ttyS1'
    baud_rate = 115200

    print("=" * 80)
    print("GD32 Heartbeat Monitor")
    print("=" * 80)
    print(f"Serial Port: {serial_port}")
    print(f"Baud Rate: {baud_rate}")
    print(f"Duration: {duration} seconds")
    print(f"Heartbeat: Every 50ms")
    print()
    print("Instructions:")
    print("  - Script will keep GD32 alive with heartbeat packets")
    print("  - Move the robot manually to trigger sensors")
    print("  - Press bumpers, trigger cliff sensors")
    print("  - Spin wheels to see encoder changes")
    print("  - Press Ctrl+C to stop early")
    print()
    print("Starting in 3 seconds...")
    print("=" * 80)
    time.sleep(3)

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Open serial port
    try:
        ser = serial.Serial(
            port=serial_port,
            baudrate=baud_rate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.01  # 10ms timeout for non-blocking read
        )
    except Exception as e:
        print(f"[!] Failed to open {serial_port}: {e}")
        print("[!] Make sure AuxCtrl is stopped: killall AuxCtrl")
        return 1

    print(f"[+] Serial port opened: {serial_port}")

    # Prepare logging
    log_filename = f"/tmp/heartbeat_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logfile = open(log_filename, 'w')
    logfile.write(f"# GD32 Heartbeat Monitor Log\n")
    logfile.write(f"# Started: {datetime.now()}\n")
    logfile.write(f"# Format: [timestamp] direction command_id data_hex\n\n")

    print(f"[+] Logging to: {log_filename}")
    print()
    print("-" * 80)
    print("LIVE MONITORING (Ctrl+C to stop)")
    print("-" * 80)
    print()

    # Statistics
    tx_count = 0
    rx_count = 0
    sensor_packets = 0
    other_packets = 0
    errors = 0

    start_time = time.time()
    last_heartbeat = 0
    rx_buffer = bytearray()

    try:
        while running and (time.time() - start_time) < duration:
            current_time = time.time()

            # Send heartbeat every 50ms
            if (current_time - last_heartbeat) >= 0.05:
                packet = build_heartbeat_packet()
                ser.write(packet)
                tx_count += 1
                last_heartbeat = current_time

                # Log TX
                logfile.write(f"[{format_timestamp()}] TX {packet.hex(' ')}\n")

            # Read any incoming data
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting)
                rx_buffer.extend(chunk)

                # Try to parse complete packets from buffer
                while len(rx_buffer) >= 4:
                    # Look for sync bytes
                    if rx_buffer[0] == SYNC1 and rx_buffer[1] == SYNC2:
                        packet = parse_packet(rx_buffer)
                        if packet:
                            rx_count += 1

                            # Log RX
                            logfile.write(f"[{format_timestamp()}] RX {packet['raw'].hex(' ')}\n")

                            # Process packet
                            if packet['cmd_id'] == CMD_SENSOR:
                                sensor_packets += 1
                                print(f"[{format_timestamp()}] SENSOR DATA (packet #{sensor_packets}):")

                                # Try to parse sensor fields
                                sensor_info = parse_sensor_data(packet['payload'])
                                if sensor_info:
                                    for key, value in sensor_info.items():
                                        print(f"  {key:20s}: {value}")
                                else:
                                    print(f"  Raw ({len(packet['payload'])} bytes): {packet['payload'].hex(' ')[:80]}...")
                                print()
                            else:
                                other_packets += 1
                                print(f"[{format_timestamp()}] CMD 0x{packet['cmd_id']:02X} "
                                      f"({len(packet['payload'])} bytes): {packet['raw'].hex(' ')}")

                            # Remove parsed packet from buffer
                            rx_buffer = rx_buffer[len(packet['raw']):]
                        else:
                            # Incomplete packet, wait for more data
                            break
                    else:
                        # Invalid sync, skip one byte
                        errors += 1
                        rx_buffer.pop(0)

            # Small sleep to prevent CPU spinning
            time.sleep(0.001)

    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        ser.close()
        logfile.close()

        elapsed = time.time() - start_time

        print()
        print("=" * 80)
        print("SESSION SUMMARY")
        print("=" * 80)
        print(f"Duration: {elapsed:.1f} seconds")
        print(f"TX Heartbeats: {tx_count}")
        print(f"RX Packets: {rx_count}")
        print(f"  - Sensor data (0x15): {sensor_packets}")
        print(f"  - Other responses: {other_packets}")
        print(f"Sync errors: {errors}")
        print()
        print(f"Log saved to: {log_filename}")
        print()
        print("Next steps:")
        print(f"  - Analyze log: cat {log_filename}")
        print(f"  - Copy to computer: scp root@vacuum:{log_filename} .")
        print("=" * 80)

    return 0

if __name__ == '__main__':
    sys.exit(main())
