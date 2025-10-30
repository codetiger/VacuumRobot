# A33 to GD32F103 Communication Protocol - Reverse Engineering

**⚠️ IMPORTANT**: This document contains initial analysis with some INCORRECT information.

**For the verified, working protocol specification, see:**
- **[GD32 Protocol - VERIFIED](../Software/GD32_PROTOCOL_FINAL.md)** ⭐ - Complete verified protocol (RECOMMENDED)
- **[Protocol Discovery Changelog](../Software/CHANGELOG.md)** - How we corrected these initial assumptions

**Key Corrections**:
- Serial port: `/dev/ttyS3` (NOT `/dev/ttyS1` as stated below)
- Communication: Bidirectional (GD32 DOES respond with CMD=0x15)
- CMD 0x08: Initialization/wakeup (NOT SetIMUZero)
- CMD 0x66: Heartbeat (NOT motor velocity)

## Config & Static Analysis of Binary

- **Identified Devices**:
  - `/dev/ttyS0` - UART0
  - `/dev/ttyS1` - Initially thought to be primary (INCORRECT)
  - `/dev/ttyS2` - Console (115200 baud)
  - `/dev/ttyS3` - **PRIMARY A33↔GD32 communication** (VERIFIED via serial MITM)

## Software Architecture
```
Monitor (supervisor)
├── RobotApp (main robot control)
├── AuxCtrl (auxiliary control - HANDLES SERIAL COMM)
├── everest-server (mapping/navigation)
└── log-server (logging)
```

**Key Binary**: `/usr/sbin/AuxCtrl` - This is the primary process managing communication with the GD32F103

## Binary Decompiling

I am going to skip any info about how to decompile the binary in this article. There are lot of places you can get good information about this. Am going to focus on what I've found. 

### Binary Information

**File**: `/usr/sbin/AuxCtrl`
**Type**: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV)
**Arch**: ARM (32-bit)
**Interpreter**: `/lib/ld-musl-armhf.so.1`
**Size**: 391 KB
**Stripped**: Yes (no section header)

**Library**: `/usr/lib/libmrpt-hwdrivers.so`
**Size**: 142 KB

### Serial Ports

The AuxCtrl binary references multiple serial ports:

- **Primary**: `/dev/ttyS3` - Main A33↔GD32 communication (VERIFIED)
- **Secondary**: `/dev/ttyS1` - Initially thought to be primary (INCORRECT)
- **Tertiary**: `/dev/ttyS0` - Alternative port (referenced but may not be used)

**UPDATE**: Serial MITM capture proved `/dev/ttyS3` is the actual communication port with GD32.

### Baud Rate Configuration

Functions found:
- `CSerialConnection::baudToRate(int)` - Convert baud to rate value
- `CSerialConnection::rateToBaud` - Convert rate to baud value

### Key Classes

#### 1. CRobotPacket

**Methods**:
- `getBuf()` - Get buffer pointer
- `readPacket(char*, char)` - Read packet from buffer
- `resetRead()` - Reset read position
- `isNextGood(int)` - Validate next bytes
- `hasWriteCapacity(int)` - Check write space
- `byte4ToBuf(int)` - Write 4-byte value
- `uByte2ToBuf(unsigned short)` - Write 2-byte value
- `bufToByte4()` - Read 4-byte value
- `getLength()` - Get packet length
- `setLength(char)` - Set packet length
- `getDataLength()` - Get payload length
- `getDataReadLength()` - Get bytes read so far
- `getHeaderLength()` - Get header size
- `getFooterLength()` - Get footer/checksum size
- `getReadLength()` - Total bytes read

#### 2. CSerialMessagePacket (Command Builder)

**Motor Control**:
- `packetMotorSpeed(double, double)` - Set motor speeds
- `packetMotorVelocity(double, double)` - Set motor velocities
- `packetMotorControlType(TMotorControlType)` - Set control mode
- `packetRollingSpeed(signed char)` - Set rolling brush speed

**IMU/Sensor Commands**:
- `packetSetIMUZero()` - Calibrate/zero IMU
- `packetIMUFactoryCalibrate()` - Factory IMU calibration
- `packetIMUFactoryCalibrateState()` - Get calibration state
- `packetIMUCalibration()` - Run IMU calibration

**System Commands**:
- `packetRestartR16System()` - Restart GD32 MCU
- `packetStm32Sleep()` - Put MCU to sleep
- `packetResetErrorCode()` - Clear error codes

**UI/LED**:
- `packetButtonLEDState(TButtonLEDState)` - Control button LEDs

#### 3. CSerialMessageUnpacket (Response Parser)

**Methods**:
- `unpacketBool(CRobotPacket*)` - Parse boolean value
- `unpacketSensorMessage(CRobotPacket*)` - Parse sensor data
- `unpacketCRL200SSensorMessage(CRobotPacket*)` - Parse CRL-200S specific sensors
- `unpacketCRL300SensorMessage(CRobotPacket*)` - Parse CRL-300 sensors (different model)

#### 4. CRobotPacketSender

**Methods**:
- `sendCommand(char)` - Send command with ID
- `sendBuf(char*, int)` - Send raw buffer
- `getDeviceConnection()` - Get serial connection
- `setDeviceConnection(CDeviceConnection*)` - Set serial connection

#### 5. CRobotPacketReceiver

**Methods**:
- `readSerialPacket(CRobotPacket*, char)` - Read packet from serial
- `getDeviceConnection()` - Get serial connection
- **State Machine Methods**:
  - `processStateSYNC1(CRobotPacket*, char)` - Process first sync byte
  - `processStateSYNC2(CRobotPacket*, char)` - Process second sync byte
  - `processStateLength(CRobotPacket*, char)` - Process length field
  - `processStateAcquireData(CRobotPacket*, char)` - Read payload data


### Protocol State Machine

The protocol uses a state machine for packet reception:

```
STATE_SYNC1 → STATE_SYNC2 → STATE_LENGTH → STATE_ACQUIRE_DATA → CRC_CHECK
```

**States**:
1. **STATE_SYNC1**: Wait for first synchronization byte
2. **STATE_SYNC2**: Verify second synchronization byte
3. **STATE_LENGTH**: Read packet length field
4. **STATE_ACQUIRE_DATA**: Read payload data
5. **CRC_CHECK**: Verify checksum/CRC

**Error Messages**:
```
[CRobotPacketReceiver] id %d, STATE_SYNC2 0x%x not want 0x%x !
[CRobotPacketReceiver] id %d, crc check is wrong !
```

This indicates:
- **Two sync bytes** (SYNC1 and SYNC2)
- **Expected values** are checked ("not want" means mismatch)
- **CRC verification** at the end

#### Timing Requirements

From logs:
```
[CRobotPacketReceiver] id 0, Receive packet time 50 ms is over!
```

- **Timeout**: 50ms per packet
- **Packet ID**: Used for tracking (seen as "id 0", "id %d")

#### Checksum/CRC

- `CLidarPacket::calcCheckSumCRC(char*, char)` - Calculate CRC for lidar packets

**Error Messages**:
```
[CLidarPacketReceiver] CRC verify wrong! CHECK_NUMBER_SUM
[CLidarPacketReceiver] CRC verify wrong! CHECK_NUMBER_CRC
[CRobotPacketReceiver] id %d, crc check is wrong !
```

**Indicates**:
- Two checksum types: **CHECK_NUMBER_SUM** (simple sum) and **CHECK_NUMBER_CRC** (CRC)
- Likely CRC16 or CRC8 (common for embedded protocols)

#### Command IDs Discovered

| Command Name | Direction | Purpose |
|--------------|-----------|---------|
| `CMD_RESTART_R16_SYSTEM` | A33→GD32 | Restart/reboot the GD32 MCU |
| `CMD_SENSOR` | GD32→A33 | Sensor data packet |
| `CMD_R16_INTOTEST` | A33→GD32 | Enter test/factory mode |
| Motor commands | A33→GD32 | Motor speed/velocity control |
| IMU commands | A33→GD32 | IMU calibration and control |
| LED commands | A33→GD32 | Button LED state control |

#### Global State Variables

```c
g_stm32_serial_state       // Serial connection state
g_request_stm32_version    // Version request flag
g_receive_stm32_data       // Received data buffer/flag
g_receive_restart_system_cmd // Restart command received
g_test_sensor_packet       // Test sensor packet
g_test_cliff_ir           // Test cliff sensor IR
```

#### Header/Footer Methods

The presence of these methods confirms the structure:
- `getHeaderLength()` - Returns header size (likely 4 bytes: SYNC1 + SYNC2 + LENGTH + CMD_ID)
- `getFooterLength()` - Returns footer size (likely 1-2 bytes for CRC)

### Sensor Data Format

#### CRL-200S Sensor Packet

Function: `unpacketCRL200SSensorMessage(CRobotPacket*)`

This function parses sensor data from the GD32, likely including:
- **IMU data** (accelerometer, gyroscope)
- **Wheel encoders** (odometry)
- **Buttons** (power, home, etc.)
- **Cliff sensors** (IR drop detection)
- **Bumper sensors** (collision detection)
- **Battery status** (voltage, current, charge state)
- **Fault codes** (error status)

#### Motor Control Types

Enum: `TMotorControlType`

Likely values:
- **Speed mode**: Set RPM directly
- **Velocity mode**: Set linear/angular velocity
- **PWM mode**: Direct PWM control

#### Lidar Communication

The binary also handles the 3irobotix lidar separately:

CLidarPacket / CLidarPacketReceiver

**Methods**:
- `analysisLidarVersion(CLidarPacket&)` - Parse lidar version
- `analysisLidarSpeed(CLidarPacket&)` - Parse lidar RPM
- `unpacketLidarScan(CLidarPacket&)` - Parse lidar scan data
- `unpacketNewLidarScanHasSingal(CLidarPacket&)` - Parse newer scan format
- `unpacketHealthInfo(CLidarPacket&)` - Parse lidar health status

**Error Messages**:
```
[C3iroboticsLidar] Special command id %d!
[CLidarPacketReceiver] Find erro header2 %d!
[CLidarPacketReceiver] Find erro length is %d!
[CLidarPacketReceiver] CRC verify wrong! CHECK_NUMBER_SUM
[CLidarPacketReceiver] CRC verify wrong! CHECK_NUMBER_CRC
```

**Note**: The lidar has its own protocol (And matched my previous findings documented in `Research/Lidar/README.md`)

