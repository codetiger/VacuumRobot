# GD32F103 Communication Protocol - Final Verified Documentation

**Status**: ✅ VERIFIED via Serial MITM Capture
**Last Updated**: 2025-10-30

This document represents the final, verified protocol specification between the Allwinner A33 (running AuxCtrl) and the GD32F103 microcontroller, based on successful bidirectional communication capture and working Rust implementation.

## Quick Navigation
- [How We Discovered This](CHANGELOG.md) - Evolution through 5 phases of research
- [How to Implement](Firmware/auxctrl-rust/README.md) - Rust library and examples
- [How to Capture Traffic](SERIAL_MITM_APPROACH.md) - Serial MITM technique
- [Test Results](TEST_RESULTS.md) - What worked and what didn't
- [Hardware Connections](../Motherboard/Connection_Evidence.md) - Physical layer evidence

## 1. Physical Layer

### Serial Configuration
- **Port**: `/dev/ttyS3` (NOT /dev/ttyS1 as initially believed)
- **Baud Rate**: 115200
- **Data Format**: 8N1 (8 data bits, no parity, 1 stop bit)
- **Flow Control**: None
- **Mode**: Raw, non-blocking

### Important Discovery
Early documentation incorrectly identified `/dev/ttyS1` as the primary port. The serial MITM capture definitively proved `/dev/ttyS3` is the correct port for GD32 communication.

## 2. Protocol Layer

### Packet Structure
```
┌──────┬──────┬────────┬────────┬─────────────┬──────┐
│SYNC1 │SYNC2 │ LENGTH │ CMD_ID │   PAYLOAD   │ CRC  │
├──────┼──────┼────────┼────────┼─────────────┼──────┤
│ 0xFA │ 0xFB │ 1 byte │ 1 byte │ 0-254 bytes │1 byte│
└──────┴──────┴────────┴────────┴─────────────┴──────┘
```

**Field Descriptions**:
- **SYNC1, SYNC2**: Fixed synchronization bytes (0xFA, 0xFB)
- **LENGTH**: Total length of remaining packet (CMD_ID + PAYLOAD + CRC)
- **CMD_ID**: Command identifier
- **PAYLOAD**: Variable-length data (0-254 bytes)
- **CRC**: Simple XOR checksum: `CMD_ID ⊕ all PAYLOAD bytes ⊕ CMD_ID`

### CRC Algorithm
```python
def calculate_crc(cmd_id, payload):
    crc = cmd_id
    for byte in payload:
        crc ^= byte
    crc ^= cmd_id
    return crc & 0xFF
```

## 3. Communication Model

### Bidirectional Communication (CORRECTED)
**Critical Update**: Contrary to initial assumptions, the GD32 DOES respond to commands:
- **TX (A33→GD32)**: Commands for control and queries
- **RX (GD32→A33)**: Status packets (CMD=0x15) containing sensor data

### Communication Pattern
1. **Initialization Phase**: Repeated CMD=0x08 packets until GD32 responds
2. **Operational Phase**: Heartbeat/command stream with periodic status responses
3. **Status Updates**: GD32 autonomously sends CMD=0x15 packets (~1-2 Hz)

## 4. Initialization Sequence (VERIFIED)

The following sequence was captured during successful communication:

### Phase 1: Wake-up Loop (5 seconds)
Send CMD=0x08 repeatedly every 200ms until GD32 responds with CMD=0x15:
```
TX: FA FB 63 08 20 08 08 20 08 08 20 08 08 ... (99 bytes total)
    └─ Repeating pattern: 0x20 0x08 0x08 (32 times)
```
**Note**: This is NOT an IMU command as initially thought, but a wake-up/init sequence.

### Phase 2: Version Request
```
TX: FA FB 03 07 00 07  (Get firmware version)
RX: Contains version string "2.0.1_19082728"
```

### Phase 3: Enable Command
```
TX: FA FB 03 06 00 06  (Wake/enable motors)
```

### Phase 4: Control Mode
```
TX: FA FB 04 8D 01 8D 01  (Set control mode)
```

### Phase 5: Heartbeat Loop
Send CMD=0x66 every 20-50ms:
```
TX: FA FB 0B 66 00 00 00 00 00 00 00 00 66 00
RX: FA FB 63 15 ... (99-byte status packet)
```

## 5. Command Reference (VERIFIED)

### Corrected Command IDs

| CMD ID | Direction | Name | Payload Size | Description |
|--------|-----------|------|--------------|-------------|
| 0x04 | A33→GD32 | STM32_SLEEP | 0 | Put GD32 into sleep mode |
| 0x05 | A33→GD32 | WAKEUP_ACK | 0 | Acknowledge wakeup |
| 0x06 | A33→GD32 | WAKE | 0 | Wake/enable motors |
| 0x07 | A33→GD32 | GET_VERSION | 0 | Request firmware version |
| **0x08** | A33→GD32 | **INITIALIZE** | 96 | **Wake-up sequence (NOT IMU!)** |
| 0x0A | A33→GD32 | RESET_ERROR | 0 | Clear error codes |
| 0x0D | A33→GD32 | STATUS_REQUEST | 0 | Request status (may not trigger response) |
| **0x15** | **GD32→A33** | **STATUS_DATA** | **96** | **Sensor data packet** |
| 0x65 | A33→GD32 | MOTOR_CONTROL_TYPE | 1 | Set motor control mode |
| **0x66** | A33→GD32 | **HEARTBEAT** | 8 | **Heartbeat (NOT motor velocity!)** |
| 0x67 | A33→GD32 | MOTOR_SPEED | 8 | Set motor speeds |
| 0x68 | A33→GD32 | BLOWER_SPEED | 2 | Set vacuum blower speed |
| 0x69 | A33→GD32 | BRUSH_SPEED | 1 | Set side brush speed |
| 0x6A | A33→GD32 | ROLLING_SPEED | 1 | Set rolling brush speed |
| 0x78 | A33→GD32 | CLIFF_IR_CONTROL | 1 | Control cliff sensors |
| 0x79 | A33→GD32 | CLIFF_IR_DIRECTION | 1 | Set cliff sensor direction |
| 0x8D | A33→GD32 | BUTTON_LED_STATE | 1 | Control button LEDs/mode |
| 0x97 | A33→GD32 | LIDAR_POWER | 1 | Control lidar power |
| 0x99 | A33→GD32 | R16_POWER | 1 | Control GD32 power |
| 0x9A | A33→GD32 | RESTART_R16 | 0 | Restart GD32 MCU |
| 0x9B | A33→GD32 | CHARGER_POWER | 1 | Control charging |

### Key Corrections
1. **CMD 0x08**: Originally thought to be "SetIMUZero", actually the initialization/wake-up command
2. **CMD 0x66**: Originally thought to be "Motor Velocity", actually the heartbeat command
3. **CMD 0x15**: GD32 DOES send responses (bidirectional communication confirmed)

## 6. Status Packet Format (CMD=0x15)

The 99-byte status packet from GD32 contains:
- IMU data (accelerometer, gyroscope, magnetometer)
- Wheel encoder counts
- Battery voltage and current
- Bumper sensor states
- Cliff sensor readings
- Button states
- Error/fault codes

Exact byte mapping requires further analysis of captured data.

## 7. Timing Requirements

- **Initialization timeout**: Send CMD=0x08 for up to 5 seconds
- **Heartbeat interval**: 20-50ms (typically 20ms)
- **Packet timeout**: 50ms per packet
- **Status packet frequency**: ~1-2 Hz from GD32

## 8. Error Handling

If heartbeat stops for >50ms:
- GD32 may enter error state
- Red LED indication possible
- Motors may stop
- Requires re-initialization sequence

## 9. Implementation Notes

### Successful Rust Implementation
The protocol has been successfully implemented in Rust at:
`Research/Software/Firmware/auxctrl-rust/`

Key files:
- `src/gd32/packet.rs`: Packet encoding/decoding
- `src/gd32/commands.rs`: Command builders
- `src/gd32/connection.rs`: Serial communication
- `src/bin/gd32_init_test.rs`: Working initialization test

### Serial MITM Tool
A custom serial MITM proxy was developed to capture the protocol:
- Location: `src/bin/serial_mitm.rs`
- Uses PTY (pseudo-terminal) for transparent interception
- Logs all bidirectional traffic with microsecond timestamps
- Essential for discovering the initialization sequence

## 10. Historical Notes

### Evolution of Understanding
1. **Phase 1**: Binary analysis suggested one-way communication
2. **Phase 2**: Direct testing failed (wrong port, missing init sequence)
3. **Phase 3**: Serial MITM revealed bidirectional communication and correct init
4. **Phase 4**: Successful Rust implementation validates protocol

### Common Pitfalls
- Using `/dev/ttyS1` instead of `/dev/ttyS3`
- Skipping the CMD=0x08 initialization phase
- Assuming one-way communication
- Misidentifying command purposes (0x08, 0x66)

## References

### Related Documentation
- **[Serial MITM Approach](SERIAL_MITM_APPROACH.md)** - PTY-based protocol capture methodology
- **[Protocol Discovery Changelog](CHANGELOG.md)** - Evolution of understanding through 5 phases
- **[Serial Logging Guide](SERIAL_LOGGING.md)** - Tools and techniques for packet capture
- **[Test Results](TEST_RESULTS.md)** - Protocol testing outcomes
- **[AuxCtrl Binary Details](AuxCtrl-Details.md)** - Deep analysis of the AuxCtrl process
- **[Original Protocol Notes](../GD32F1/A33-GD32-Protocol.md)** - Initial binary reverse engineering (contains outdated info)
- **[CRC Algorithm Discovery](../GD32F1/CRC-Algorithm-Discovery.md)** - XOR checksum reverse engineering

### Implementation
- **[AuxCtrl-Rust Library](Firmware/auxctrl-rust/README.md)** - Open-source Rust implementation
  - Packet encoding/decoding: `Firmware/auxctrl-rust/src/gd32/packet.rs`
  - Command builders: `Firmware/auxctrl-rust/src/gd32/commands.rs`
  - Serial connection: `Firmware/auxctrl-rust/src/gd32/connection.rs`
  - Test programs: `Firmware/auxctrl-rust/src/bin/`

### Hardware References
- **[Motherboard Analysis](../Motherboard/README.md)** - Component identification and connections
- **[A33-GD32 Connections](../Motherboard/Connection_Evidence.md)** - Hardware connection evidence

### Historical Documents (Outdated)
- [Research/backup/Analysis/](../backup/README.md) - Contains outdated research files with warnings

---

**This document supersedes all previous protocol documentation and represents the verified, working protocol specification.**