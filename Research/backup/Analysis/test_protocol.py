#!/usr/bin/env python3
"""
GD32F103 Communication Protocol Test Script

This script tests the communication protocol between the Allwinner A33 and GD32F103 MCU
based on the analysis of the AuxCtrl binary.

Protocol Structure (from Ghidra analysis):
- SYNC1: 0xFA (assumed based on common practice)
- SYNC2: 0xFB (assumed based on common practice)
- LENGTH: 1 byte (payload length)
- CMD_ID: 1 byte (command identifier)
- DATA: variable length payload
- CRC: 2 bytes (checksum)

Usage:
  Run on the vacuum device: python3 test_protocol.py
  Requires root access to open /dev/ttyS1
"""

import serial
import struct
import time
import sys

# Command IDs discovered from Ghidra decompilation
COMMANDS = {
    'CMD_STM32_SLEEP': 0x04,
    'CMD_WAKEUP_ACK': 0x05,
    'CMD_HEARTBEAT': 0x06,
    'CMD_REQUIRE_VERSION': 0x07,
    'CMD_SET_IMU_ZERO': 0x08,
    'CMD_RESET_ERROR_CODE': 0x0A,
    'CMD_MOTOR_CONTROL_TYPE': 0x65,  # 'e'
    'CMD_MOTOR_VELOCITY': 0x66,  # 'f'
    'CMD_MOTOR_SPEED': 0x67,  # 'g'
    'CMD_BLOWER_SPEED': 0x68,  # 'h'
    'CMD_BRUSH_SPEED': 0x69,  # 'i'
    'CMD_ROLLING_SPEED': 0x6A,  # 'j'
    'CMD_CLIFF_IR_CONTROL': 0x78,  # 'x'
    'CMD_CLIFF_IR_DIRECTION': 0x79,  # 'y'
    'CMD_BUTTON_LED_STATE': 0x8D,
    'CMD_LIDAR_POWER': 0x97,
    'CMD_RESTART_R16': 0x9A,
    'CMD_CHARGER_POWER': 0x9B,
    'CMD_IMU_FACTORY_CALIBRATE': 0xA1,
    'CMD_IMU_FACTORY_CALIBRATE_STATE': 0xA2,
    'CMD_GEOMAGNETISM_CALIBRATE': 0xA3,
    'CMD_GEOMAGNETISM_CALIBRATE_STATE': 0xA4,
}

# Assumed sync bytes (common pattern, needs verification)
SYNC1 = 0xFA
SYNC2 = 0xFB

class GD32Protocol:
    def __init__(self, port='/dev/ttyS1', baudrate=115200):
        """Initialize serial connection to GD32F103"""
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.5
            )
            print(f"[+] Connected to {port} at {baudrate} baud")
        except Exception as e:
            print(f"[!] Failed to open {port}: {e}")
            print(f"[!] Make sure you have root access and the port exists")
            sys.exit(1)

    def calculate_crc(self, data):
        """
        Calculate CRC checksum
        Note: The exact CRC algorithm needs to be determined from testing
        This is a placeholder using simple checksum
        """
        # Try simple 16-bit checksum first
        checksum = sum(data) & 0xFFFF
        return checksum

    def build_packet(self, cmd_id, payload=b''):
        """
        Build a packet according to the protocol structure

        Format: SYNC1 + SYNC2 + LENGTH + CMD_ID + PAYLOAD + CRC16
        """
        # Build packet without CRC first
        length = len(payload)
        packet_base = bytes([SYNC1, SYNC2, length, cmd_id]) + payload

        # Calculate CRC on the packet (excluding CRC itself)
        crc = self.calculate_crc(packet_base)

        # Add CRC as big-endian 16-bit value
        packet = packet_base + struct.pack('>H', crc)

        return packet

    def send_command(self, cmd_name, payload=b'', description=""):
        """Send a command and wait for response"""
        if cmd_name not in COMMANDS:
            print(f"[!] Unknown command: {cmd_name}")
            return None

        cmd_id = COMMANDS[cmd_name]
        packet = self.build_packet(cmd_id, payload)

        print(f"\n{'='*80}")
        print(f"[>] Sending: {cmd_name} (0x{cmd_id:02X})")
        if description:
            print(f"[i] {description}")
        print(f"[>] Packet: {packet.hex(' ')}")
        print(f"[>] Length: {len(packet)} bytes")

        try:
            # Clear input buffer
            self.ser.reset_input_buffer()

            # Send packet
            self.ser.write(packet)
            self.ser.flush()

            # Wait for response
            time.sleep(0.1)

            if self.ser.in_waiting > 0:
                response = self.ser.read(self.ser.in_waiting)
                print(f"[<] Response ({len(response)} bytes): {response.hex(' ')}")
                self.parse_response(response)
                return response
            else:
                print(f"[<] No response received")
                return None

        except Exception as e:
            print(f"[!] Error sending command: {e}")
            return None

    def parse_response(self, data):
        """Parse response packet"""
        if len(data) < 6:  # Minimum: SYNC1 + SYNC2 + LEN + CMD + CRC
            print(f"[!] Response too short: {len(data)} bytes")
            return

        # Try to parse assuming same structure
        sync1 = data[0]
        sync2 = data[1]
        length = data[2]
        cmd_id = data[3]

        print(f"[<] Parsed: SYNC1=0x{sync1:02X}, SYNC2=0x{sync2:02X}, LEN={length}, CMD=0x{cmd_id:02X}")

        if length > 0 and len(data) >= 4 + length + 2:
            payload = data[4:4+length]
            crc = struct.unpack('>H', data[4+length:4+length+2])[0]
            print(f"[<] Payload ({length} bytes): {payload.hex(' ')}")
            print(f"[<] CRC: 0x{crc:04X}")

    def test_heartbeat(self):
        """Test heartbeat command (simplest, no payload)"""
        return self.send_command(
            'CMD_HEARTBEAT',
            description="Heartbeat packet - should elicit a response if protocol is correct"
        )

    def test_require_version(self):
        """Test system version request"""
        return self.send_command(
            'CMD_REQUIRE_VERSION',
            description="Request system version from GD32"
        )

    def test_motor_stop(self):
        """Test motor velocity command with zero velocity (safe test)"""
        # Motor velocity: left_vel (4 bytes) + right_vel (4 bytes)
        payload = struct.pack('<ii', 0, 0)  # Both motors at 0
        return self.send_command(
            'CMD_MOTOR_VELOCITY',
            payload=payload,
            description="Set both motor velocities to 0 (safe command)"
        )

    def close(self):
        """Close serial connection"""
        if self.ser.is_open:
            self.ser.close()
            print("\n[+] Connection closed")


def main():
    print("="*80)
    print("GD32F103 Communication Protocol Test")
    print("="*80)
    print()
    print("[!] WARNING: This script sends commands to the vacuum's MCU")
    print("[!] Only proceed if you understand what you're doing")
    print()

    # Check if running on the device
    try:
        protocol = GD32Protocol()
    except SystemExit:
        return

    try:
        # Test 1: Heartbeat (safest test)
        print("\n" + "="*80)
        print("TEST 1: Heartbeat Command")
        print("="*80)
        protocol.test_heartbeat()
        time.sleep(1)

        # Test 2: Request version
        print("\n" + "="*80)
        print("TEST 2: System Version Request")
        print("="*80)
        protocol.test_require_version()
        time.sleep(1)

        # Test 3: Motor stop (safe since it's zero velocity)
        print("\n" + "="*80)
        print("TEST 3: Motor Velocity (Zero/Stop)")
        print("="*80)
        protocol.test_motor_stop()
        time.sleep(1)

        print("\n" + "="*80)
        print("Testing Complete")
        print("="*80)
        print()
        print("[i] Next steps:")
        print("    1. Analyze responses to determine correct sync bytes and CRC algorithm")
        print("    2. If no responses, try different sync byte values")
        print("    3. Monitor /dev/ttyS1 with logic analyzer to capture actual traffic")

    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
    finally:
        protocol.close()


if __name__ == '__main__':
    main()
