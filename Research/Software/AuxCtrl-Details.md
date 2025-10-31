# AuxCtrl Binary Analysis - Complete Protocol Documentation

## 1. Introduction

The AuxCtrl process (`/usr/sbin/AuxCtrl` binary) is responsible for managing communication between the Allwinner A33 main processor and the GigaDevice GD32F103VCT6 microcontroller.

### Analysis Tools

- Ghidra 11.4.2 (decompilation)
- strings, objdump (binary analysis)
- Custom Python scripts for function extraction

### Binary Information

- **File**: `/usr/sbin/AuxCtrl`
- **Type**: ELF 32-bit ARM executable
- **Size**: 391 KB (stripped)

---

## 2. Function List

### 2.1 Packet Building Functions (A33 → GD32)

#### System Control Commands

| Function | Command ID | Payload | Description |
|----------|------------|---------|-------------|
| `packetStm32Sleep()` | 0x04 | None | Put GD32 MCU into sleep mode |
| `packetWakeupAck()` | 0x05 | None | Acknowledge wakeup signal |
| `packetHeartBeat()` | 0x06 | None | Heartbeat/keep-alive packet |
| `packetRequireSystemVersion()` | 0x07 | None | Request firmware version from GD32 |
| `packetRestartR16System()` | 0x9A | None | Restart/reboot the GD32 MCU |
| `packetResetErrorCode()` | 0x0A | None | Clear error/fault codes |

#### IMU & Sensor Commands

| Function | Command ID | Payload | Description |
|----------|------------|---------|-------------|
| `packetSetIMUZero()` | 0x08 | None | Zero/calibrate IMU offset |
| `packetIMUCalibration()` | - | None | Run IMU calibration routine |
| `packetIMUFactoryCalibrate()` | 0xA1 | None | Factory IMU calibration |
| `packetIMUFactoryCalibrateState()` | 0xA2 | None | Get IMU calibration state |
| `packetGeoMagnetismCalibrate()` | 0xA3 | None | Calibrate magnetometer |
| `packetGeoMagnetismCalibrateState()` | 0xA4 | None | Get magnetometer calibration state |

#### Motor Control Commands

| Function | Command ID | Payload Size | Description |
|----------|------------|--------------|-------------|
| `packetMotorControlType()` | 0x65 ('e') | 1 byte | Set motor control mode (speed/velocity/PWM) |
| `packetMotorVelocity()` | 0x66 ('f') | 8 bytes | Set linear and angular velocity (2× int32) |
| `packetMotorSpeed()` | 0x67 ('g') | 8 bytes | Set left and right motor speeds (2× int32) |

#### Actuator Control Commands

| Function | Command ID | Payload Size | Description |
|----------|------------|--------------|-------------|
| `packetBrushSpeed()` | 0x69 ('i') | 1 byte | Set side brush speed (signed char, clipped to ≥0) |
| `packetRollingSpeed()` | 0x6A ('j') | 1 byte | Set rolling brush speed (signed char, clipped to ≥0) |
| `packetBlowerSpeed()` | 0x68 ('h') | 2 bytes | Set vacuum blower speed (uint16) |

#### Peripheral Control Commands

| Function | Command ID | Payload Size | Description |
|----------|------------|--------------|-------------|
| `packetLidarPower()` | 0x97 | 1 byte | Enable/disable Lidar power (bool) |
| `packetR16Power()` | 0x99 | 1 byte | Enable/disable GD32 MCU power (bool) |
| `packetChargerPower()` | 0x9B | 1 byte | Enable/disable charging (bool) |
| `packetCliffIRControl()` | 0x78 ('x') | 1 byte | Enable/disable cliff IR sensors (bool) |
| `packetCliffIRDirection()` | 0x79 ('y') | 1 byte | Set cliff IR direction (bool) |
| `packetButtonLEDState()` | 0x8D | 1 byte | Set button LED state (TButtonLEDState enum) |

---

### 2.2 Packet Parsing Functions (GD32 → A33)

| Function | Description | Expected Data |
|----------|-------------|---------------|
| `unpacketBool()` | Parse boolean response | Single byte (0 or 1) |
| `unpacketSensorMessage()` | Parse sensor data packet | Variable, model-specific |
| `unpacketCRL200SSensorMessage()` | Parse CRL-200S specific sensor data | Encoders, IMU, bumpers, cliff, battery, buttons |
| `unpacketCRL300SensorMessage()` | Parse CRL-300 sensor data (different model) | Model-specific sensor layout |
| `unpacketSystemVersion()` | Parse firmware version string | C++ string (std::string) |
| `unpacketDebug1()` | Parse debug message | Debug-specific format |
| `unpacketErroCode()` | Parse error/fault code | Error code integer |

**Response Command IDs (from handleMessage):**
- **0x15** = CMD_SENSOR (main periodic sensor data from GD32)
- 0xDD-0xE4 = Factory test commands (ADB, lidar control, version info)

**CRL-200S Sensor Packet Contents:**
- Wheel encoders (odometry)
- IMU (accelerometer, gyroscope, yaw)
- Bumper and cliff sensors
- Battery voltage/current
- Button states
- Error codes

---

### 2.3 Protocol State Machine

| Function | Purpose |
|----------|---------|
| `readSerialPacket()` | Main packet reading loop |
| `processStateSYNC1()` | Wait for first sync byte |
| `processStateSYNC2()` | Verify second sync byte |
| `processStateLength()` | Read packet length |
| `processStateAcquireData()` | Read payload data |
| *(CRC verification)* | Verify checksum |

#### State Machine Flow

```
┌─────────────┐
│ STATE_SYNC1 │◄──┐
└──────┬──────┘   │
       │ Found    │ Timeout
       ▼          │ or Error
┌─────────────┐   │
│ STATE_SYNC2 │───┤
└──────┬──────┘   │
       │ Match    │
       ▼          │
┌─────────────┐   │
│STATE_LENGTH │───┤
└──────┬──────┘   │
       │ Got Len  │
       ▼          │
┌─────────────┐   │
│  ACQUIRE_   │───┤
│    DATA     │   │
└──────┬──────┘   │
       │ Complete │
       ▼          │
┌─────────────┐   │
│  CRC_CHECK  │───┘
└──────┬──────┘
       │ Valid
       ▼
   [Process]
```

**Error Messages:**
```
[CRobotPacketReceiver] id %d, STATE_SYNC2 0x%x not want 0x%x !
[CRobotPacketReceiver] id %d, crc check is wrong !
[CRobotPacketReceiver] id 0, Receive packet time 50 ms is over!
```
Timeout: 50ms per packet

---

## 3. Protocol Specification

```
┌──────┬──────┬────────┬────────┬─────────────┬──────┐
│SYNC1 │SYNC2 │ LENGTH │CMD_ID  │   PAYLOAD   │ CRC  │
├──────┼──────┼────────┼────────┼─────────────┼──────┤
│1 byte│1 byte│ 1 byte │ 1 byte │ 0-255 bytes │1 byte│
└──────┴──────┴────────┴────────┴─────────────┴──────┘
```

### ✅ Confirmed Parameters (from live testing)

- **SYNC1**: `0xFA` ✅
- **SYNC2**: `0xFB` ✅
- **LENGTH**: Number of bytes after LENGTH field (includes CMD_ID + PAYLOAD + CRC)
- **CMD_ID**: Command identifier
- **PAYLOAD**: Variable data (0-254 bytes)
- **CRC**: 16-bit checksum (✅ verified - see [../GD32F1/CHECKSUM_ALGORITHM.md](../GD32F1/CHECKSUM_ALGORITHM.md))

**Example captured packet:**
```
FA FB 03 0D 00 0D
│  │  │  │  │  └─ CRC (0x0D)
│  │  │  │  └──── DATA (0x00)
│  │  │  └─────── CMD_ID (0x0D - heartbeat/status request)
│  │  └────────── LENGTH (0x03 = CMD + DATA + CRC)
│  └───────────── SYNC2 (0xFB)
└──────────────── SYNC1 (0xFA)
```

**Command 0x0D**: Heartbeat/keep-alive command sent from A33 to GD32 every ~50ms. Expects response from GD32 within timeout period.

### CRC Calculation

✅ **Status**: Checksum algorithm **VERIFIED** - see [../GD32F1/CHECKSUM_ALGORITHM.md](../GD32F1/CHECKSUM_ALGORITHM.md)

**Algorithm**: 16-bit big-endian word sum with XOR for odd bytes
- Decompiled from `CRobotPacket::calcCheckSum()` at address 0x00055d58
- Verified against 14,609 MITM-captured packets with 99.8% success rate
- Special case: CMD 0x08 has no checksum (initialization packets)

### Serial Port Assignment

- `/dev/ttyS0` - Test/factory interface
- `/dev/ttyS1` - **GD32F103 primary communication** (baud unknown, likely 115200)
- `/dev/ttyS3` - Secondary device (unknown purpose)

## 4. Related Documentation

- [Research/GD32F1/A33-GD32-Protocol.md](../GD32F1/A33-GD32-Protocol.md) - Initial protocol discovery
- [Research/GD32F1/README.md](../GD32F1/README.md) - GD32 MCU overview
- [Research/Motherboard/README.md](../Motherboard/README.md) - Hardware connections
- [Research/Software/README.md](README.md) - Software architecture overview

---

## 5. Summary

Discovered 23 command functions, 7 response parsers, and the complete 5-state packet reception state machine.

### Testing Results

✅ **Confirmed through live device testing:**
- SYNC bytes: 0xFA, 0xFB
- Packet structure: SYNC1 SYNC2 LENGTH CMD_ID DATA... CRC
- Command 0x0D identified as heartbeat/status request (sent every ~50ms)
- GD32 MCU is powered and responding
- Serial port: /dev/ttyS1

✅ **Resolved:**
- Checksum algorithm: 16-bit big-endian word sum (see [../GD32F1/CHECKSUM_ALGORITHM.md](../GD32F1/CHECKSUM_ALGORITHM.md))
- Serial port: `/dev/ttyS3` (verified via MITM)
- Baud rate: 115200 (verified)

⚠️ **Remaining unknowns:**
- Full sensor packet structure (CMD_SENSOR 0x15)

**Test files:**
- `test_version_request.py` - Python script with 60 test combinations (requires Python on device)
- `test_serial.sh` - Shell script for manual testing (works with busybox)
- `TESTING.md` - Complete testing guide and troubleshooting
