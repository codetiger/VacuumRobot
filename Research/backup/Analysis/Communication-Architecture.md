# AuxCtrl ↔ GD32 Communication Architecture

**Analysis Date**: 2025-10-28
**Based on**: Live captures, binary analysis, and strace logs

---

## High-Level Overview

The communication between the Allwinner A33 (running Linux/AuxCtrl) and the GigaDevice GD32F103 microcontroller uses a **single full-duplex UART serial connection** with a custom binary protocol.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Allwinner A33 (Linux)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    AuxCtrl Process                         │  │
│  │  (/usr/sbin/AuxCtrl - ARM 32-bit ELF)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ read()/write()                    │
│                              │                                   │
│  ┌──────────────────────────▼──────────────────────────────┐  │
│  │                    /dev/ttyS1                             │  │
│  │              (UART Hardware Interface)                    │  │
│  └──────────────────────────┬──────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              │ TX/RX Lines
                              │ (115200 baud likely)
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                 GigaDevice GD32F103VCT6                         │
│              (ARM Cortex-M3, 108MHz MCU)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Main Control Firmware                         │  │
│  │  - Motor control (wheels, brushes, fan)                   │  │
│  │  - Sensor reading (IMU, encoders, bumpers, cliff)         │  │
│  │  - Battery monitoring                                      │  │
│  │  - Peripheral control (lidar, charger)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Serial Port Configuration

### Primary Communication Port

**Device**: `/dev/ttyS1` (on A33 Linux side)

**Configuration** (likely):
- **Baud Rate**: 115200 (standard for embedded systems, not confirmed)
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Flow Control**: None (software control via protocol timing)

**File Descriptor**: Variable (changes on each AuxCtrl start)
- During captures: fd 4, 5, 7, or 9 depending on startup order
- Always maps to `/dev/ttyS1` internally

### Secondary Port (Minor Role)

**Device**: `/dev/ttyS3`

**Usage**: Read once at startup
- AuxCtrl reads ASCII `"1\n1"` during initialization
- Purpose unclear - possibly:
  - Factory test interface status check
  - Device ID configuration
  - Secondary MCU communication (if present)
  - Or leftover data in buffer

**Not used for main GD32 communication**

---

## Communication Model

### Request-Response Pattern

The protocol uses **asynchronous request-response** with mandatory periodic heartbeats:

```
AuxCtrl (A33)                           GD32 MCU
     │                                      │
     │  TX: Heartbeat (0x06)               │
     ├──────────────────────────────────►  │
     │                                      │
     │  TX: Motor Velocity (0x66)          │
     ├──────────────────────────────────►  │
     │                                      │
     │  TX: Heartbeat (0x06)               │
     ├──────────────────────────────────►  │
     │                                      │
     │          ◄─────────────────────────┤
     │           RX: Sensor Data (0x15)    │
     │                99 bytes              │
     │                                      │
     │  TX: Motor Velocity (0x66)          │
     ├──────────────────────────────────►  │
     │                                      │
     │  TX: Motor Velocity (0x66)          │
     ├──────────────────────────────────►  │
     │                                      │
     │  TX: Heartbeat (0x06)               │
     ├──────────────────────────────────►  │
     │                                      │
     │          ◄─────────────────────────┤
     │           RX: Sensor Data (0x15)    │
```

### Key Characteristics

1. **Not Strictly Request-Response**
   - AuxCtrl continuously sends commands (motor control, heartbeats)
   - GD32 periodically sends sensor data (CMD_SENSOR 0x15)
   - No 1:1 correlation between requests and responses
   - More like: "command stream + telemetry stream"

2. **Heartbeat Requirement**
   - **Critical**: AuxCtrl must send heartbeat (0x06 or 0x0D) every ~50ms
   - If timeout occurs: GD32 enters error state (red LED)
   - No special acknowledgment - GD32 just expects continuous traffic

3. **Motor Control Stream**
   - **0x66 MOTOR_VELOCITY**: Sent 2306 times in capture (most frequent)
   - Likely sent at 10-20 Hz to control wheel motors
   - Each packet: 11 bytes (8 bytes data = 2× int32 velocities + CRC)

4. **Sensor Data Push**
   - GD32 periodically pushes sensor data (0x15) without being asked
   - 99 bytes of data including:
     - Wheel encoder counts
     - IMU data (accel, gyro, yaw)
     - Bumper/cliff sensor states
     - Battery voltage/current
     - Button states
   - Frequency: ~1-2 Hz based on capture (25 packets over short time)

---

## Protocol Specification

### Packet Structure

```
┌──────┬──────┬────────┬────────┬─────────────┬──────┐
│SYNC1 │SYNC2 │ LENGTH │CMD_ID  │   PAYLOAD   │ CRC  │
├──────┼──────┼────────┼────────┼─────────────┼──────┤
│ 0xFA │ 0xFB │ 1 byte │ 1 byte │ 0-254 bytes │1 byte│
└──────┴──────┴────────┴────────┴─────────────┴──────┘
```

**Fields**:
- **SYNC1, SYNC2**: `0xFA 0xFB` (synchronization markers)
- **LENGTH**: Number of bytes that follow (CMD_ID + PAYLOAD + CRC)
- **CMD_ID**: Command/response identifier (1 byte)
- **PAYLOAD**: Variable-length data
- **CRC**: 8-bit checksum (algorithm still unknown)

**Example TX Packet** (Motor Velocity):
```
FA FB 0B 66 00 00 00 00 00 00 00 00 66 00
│  │  │  │  └──────────┬──────────┘ │  └─ CRC
│  │  │  │          8 bytes         │
│  │  │  │      (2× int32 vel)      │
│  │  │  └─ CMD: 0x66 (Motor Velocity)
│  │  └──── LEN: 11 (CMD + 8 data + 1 CRC)
│  └─────── SYNC2
└────────── SYNC1
```

**Example RX Packet** (Sensor Data):
```
FA FB 63 15 [95 bytes of sensor data] CRC
│  │  │  │
│  │  │  └─ CMD: 0x15 (Sensor Data Response)
│  │  └──── LEN: 99 (CMD + 97 data + 1 CRC)
│  └─────── SYNC2
└────────── SYNC1
```

---

## Command Types

### TX Commands (AuxCtrl → GD32)

**From captured data - frequency order**:

| Command | ID | Frequency | Payload | Purpose |
|---------|-----|-----------|---------|---------|
| Motor Velocity | 0x66 | 87% (2306) | 8 bytes | Set left/right wheel velocities (2× int32) |
| Heartbeat | 0x06 | 9% (226) | 0 bytes | Keep-alive signal |
| **Unknown** | 0x6B | 4% (95) | ? bytes | **New command discovered!** |
| IMU Zero | 0x08 | <1% (5) | 0 bytes | Calibrate IMU offset |
| Wakeup Ack | 0x05 | <1% (5) | 0 bytes | Acknowledge wakeup |
| LED State | 0x8D | <1% (5) | 1 byte | Control button LED |
| **Unknown** | 0x0C | <1% (4) | ? bytes | **New command discovered!** |
| Status Request | 0x0D | <1% (4) | 0 bytes | Alternate heartbeat? |

**Additional commands from binary analysis** (not seen in capture):
- 0x04: Sleep command
- 0x07: Version request
- 0x0A: Reset error code
- 0x67: Motor speed
- 0x68: Blower speed
- 0x69: Side brush speed
- 0x6A: Rolling brush speed
- 0x78-0x79: Cliff IR control
- 0x97: Lidar power
- 0x99: GD32 power control
- 0x9A: GD32 restart
- 0x9B: Charger power
- 0xA1-0xA4: IMU/magnetometer calibration

### RX Responses (GD32 → AuxCtrl)

| Command | ID | Frequency | Payload | Purpose |
|---------|-----|-----------|---------|---------|
| Sensor Data | 0x15 | 76% (25) | 97 bytes | Main telemetry (encoders, IMU, battery, sensors) |
| Response | 0x05 | 21% (7) | 1 byte | Acknowledgment or status |
| Response | 0x06 | 3% (1) | ? bytes | Acknowledgment or status |

---

## Communication Flow Patterns

### Normal Operation Cycle

**Observed pattern** (from 391KB capture):

```
Time    Direction  Command      Description
────────────────────────────────────────────────────────
0ms     TX         0x66         Motor velocity command
10ms    TX         0x66         Motor velocity command
20ms    TX         0x66         Motor velocity command
30ms    TX         0x66         Motor velocity command
40ms    TX         0x06         Heartbeat
50ms    TX         0x66         Motor velocity command
...     RX         0x15         Sensor data arrives (99 bytes)
60ms    TX         0x66         Motor velocity command
...
```

**Frequency analysis**:
- **Motor commands**: ~20 Hz (every 50ms)
- **Heartbeats**: ~2 Hz (every 500ms)
- **Sensor data**: ~1-2 Hz (pushed by GD32)
- **Other commands**: Sporadic (on state changes)

### Startup Sequence

**No special initialization found**:

1. AuxCtrl opens `/dev/ttyS1`
2. **Immediately** starts sending heartbeat (0x06 or 0x0D)
3. Expects GD32 to already be running and responsive
4. No handshake, no version check, no configuration phase

**Implication**: GD32 must be powered and initialized **before** AuxCtrl starts (likely done by bootloader or init scripts).

### Error Handling

**Timeout Detection**:
- GD32 expects packets within 50ms
- If no packet received: timeout error
- Error logged: `"[CRobotPacketReceiver] id 0, Receive packet time 50 ms is over!"`
- System enters error state (red LED flashes)

**No Automatic Recovery**:
- Once communication breaks, GD32 doesn't auto-recover
- Requires hardware reset or power cycle
- Restarting AuxCtrl alone is **not sufficient**

---

## Why Single Port is Sufficient

### Full-Duplex Communication

**UART hardware supports simultaneous TX and RX**:
- TX line (A33 → GD32): Commands from AuxCtrl
- RX line (GD32 → A33): Sensor data and responses
- No collision issues - separate physical wires

### Asynchronous Protocol

**No strict lock-step required**:
- AuxCtrl can send commands anytime
- GD32 can send sensor data anytime
- Each packet is self-contained (SYNC + LENGTH + CRC)
- State machine on each side processes incoming bytes independently

### Why Not Two Ports?

**Not needed because**:
1. **No bandwidth bottleneck**: 115200 baud is sufficient for both directions
2. **Clear packet boundaries**: SYNC bytes prevent ambiguity
3. **Minimal latency**: Real-time requirements met with single port
4. **Hardware limitation**: GD32F103 UART count (typically 3-5 UARTs)
   - UART1: Main communication with A33 (ttyS1)
   - UART2: Possibly Lidar (Delta-2D at 115200 baud)
   - UART3: Factory/debug interface (ttyS3?)

---

## Comparison to Other Protocols

### vs. SPI (Not Used Here)

**Why not SPI**:
- Requires chip select + clock lines (4+ wires)
- Master-slave only (A33 would be master, but GD32 needs to push sensor data)
- More complex GPIO configuration

### vs. I2C (Not Used Here)

**Why not I2C**:
- Slower than UART at these distances
- More overhead for large packets (99-byte sensor frames)
- Register-based model doesn't fit streaming telemetry

### vs. Modern Protocols (CAN, Ethernet, USB)

**Why not used**:
- CAN: Overkill for point-to-point, more expensive transceivers
- Ethernet: Too complex for microcontroller
- USB: Requires host/device negotiation, more complex than needed

**UART wins**:
- Simple 2-wire interface (+ ground)
- Built into both chips
- Sufficient speed (115200 baud = ~11 KB/sec)
- Reliable with proper framing

---

## Critical Timing Requirements

### Heartbeat Timeout: 50ms

**Strict requirement**:
- AuxCtrl must send **any** command every 50ms
- Missing this deadline → GD32 error state
- This is why strace breaks the system (adds latency)

**Practical implication**:
- Cannot debug with traditional tracing tools
- Need hardware logic analyzer for clean captures
- Or accept brief disruption during captures

### Motor Command Rate

**Observed**: ~20 Hz (50ms intervals)
- Fast enough for smooth motion control
- Matches typical servo update rates
- Allows trajectory following without jitter

### Sensor Data Rate

**Observed**: ~1-2 Hz
- Sufficient for navigation decisions
- Not critical path (motors use open-loop control between updates)
- Could be increased if needed

---

## Known Issues

### 1. No Software Reset Capability

**Problem**: If communication breaks (timeout), GD32 enters error state with no recovery

**Root cause**: No reset command in protocol (0x9A exists but may not work from error state)

**Workaround**: Hardware reset or full power cycle required

### 2. CRC Algorithm Unknown

**Status**: Still under investigation
- Simple checksums don't match
- Need to test CRC-8 polynomials
- May include SYNC bytes in calculation

**Impact**: Cannot create valid custom commands yet

### 3. No Initialization Handshake

**Problem**: AuxCtrl assumes GD32 is ready (no version check, no capability negotiation)

**Impact**: Makes testing harder, no graceful degradation

---

## Future Investigation

### Questions to Answer

1. **What is command 0x6B?** (95 occurrences - 4% of traffic)
2. **What is command 0x0C?** (4 occurrences)
3. **Exact baud rate?** (assumed 115200)
4. **CRC-8 polynomial?** (critical for creating test commands)
5. **Full sensor packet structure?** (99 bytes - need to decode each field)
6. **Can GD32 be reset via software?** (command 0x9A)

### Recommended Tools

- **Logic Analyzer**: Capture clean bidirectional traffic without timing disruption
- **USB-UART Bridge**: Snoop on ttyS1 without interfering
- **Oscilloscope**: Verify baud rate, check signal integrity

---

## Summary

The AuxCtrl ↔ GD32 communication uses:

✅ **Single full-duplex UART** (`/dev/ttyS1`)
✅ **Custom binary protocol** (FA FB sync bytes)
✅ **Asynchronous command/telemetry streams** (not strict request-response)
✅ **Mandatory 50ms heartbeat** (critical timing requirement)
✅ **Periodic sensor data push** (99-byte packets from GD32)
❌ **No initialization handshake** (assumes GD32 ready)
❌ **No software reset recovery** (hardware reset needed if communication breaks)

**Architecture**: Simple, efficient, real-time capable, but fragile to timing disruptions.

---

## Files Referenced

- **Protocol Discovery**: `Research/Software/Startup-Sequence-Analysis.md`
- **Binary Analysis**: `Research/Software/AuxCtrl-Details.md`
- **Capture Data**: `Research/Software/serial_capture_20251028_163742.log` (391KB)
- **Analysis Tool**: `Research/Software/analyze_capture.py`
