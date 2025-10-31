# Protocol Discovery Changelog

## Evolution of Understanding: A33↔GD32 Communication Protocol

This document chronicles the journey of reverse-engineering the communication protocol between the Allwinner A33 and GD32F103 MCU.

---

## Phase 1: Binary Analysis (Initial Assumptions)
**Date**: Early October 2025
**Method**: Decompiling AuxCtrl binary, string analysis

### Initial Beliefs:
- Primary serial port: `/dev/ttyS1`
- Communication model: One-way (A33→GD32 only)
- CMD 0x08: "SetIMUZero" command
- CMD 0x66: Motor velocity control
- GD32 never responds via UART

### Source Documents:
- `Research/GD32F1/A33-GD32-Protocol.md` (initial version)
- `Research/Software/AuxCtrl-Details.md`

---

## Phase 2: Direct Testing Failures
**Date**: Mid October 2025
**Method**: Direct serial port communication tests

### Tests Attempted:
- Sending heartbeat (CMD=0x06) to `/dev/ttyS1`
- Sending status request (CMD=0x0D)
- Reading from serial port

### Results:
- **FAILED**: No response from GD32
- **FAILED**: GD32 entered error state (red LED)
- Assumption: "GD32 doesn't respond, communication is one-way"

### Incorrect Conclusions:
- Believed `/dev/ttyS1` was correct
- Thought simple heartbeat would work
- Assumed no initialization needed

### Source Documents:
- `Research/backup/Analysis/TESTING.md`
- `Research/backup/Analysis/HEARTBEAT-TEST.md`

---

## Phase 3: Strace Discovery
**Date**: Late October 2025
**Method**: System call tracing of running AuxCtrl

### Key Discovery:
- AuxCtrl actually uses `/dev/ttyS3` (not `/dev/ttyS1`)
- First packet is CMD=0x66 (not heartbeat 0x06)
- Communication is event-driven (triggered by socket messages)

### Still Incorrect:
- Still believed GD32 doesn't respond
- Misidentified CMD=0x66 as motor velocity
- Didn't understand initialization sequence

### Source Documents:
- `Research/backup/Analysis/GD32_Init_Sequence.md`
- `Research/backup/Analysis/Boot-Test-Results.md`

---

## Phase 4: Serial MITM Breakthrough
**Date**: October 29-30, 2025
**Method**: Custom PTY-based serial interceptor

### Implementation:
- Built `serial_mitm.rs` using pseudo-terminal (PTY)
- Transparently intercepted `/dev/ttyS3` traffic
- Captured 160+ seconds of Return2Dock operation

### Revolutionary Discoveries:

#### 1. **GD32 DOES Respond!**
- Sends CMD=0x15 status packets (99 bytes)
- Contains sensor data, IMU, encoders, battery status
- Communication is **bidirectional**

#### 2. **Initialization Sequence Required**
- Must send CMD=0x08 repeatedly for ~5 seconds
- Pattern: `20 08 08` repeated 32 times (99 bytes total)
- GD32 wakes up and starts responding with CMD=0x15

#### 3. **Command Corrections**
- CMD=0x08: NOT "SetIMUZero" → Actually initialization/wakeup
- CMD=0x66: NOT "Motor Velocity" → Actually heartbeat
- CMD=0x15: Status response packet (previously unknown)

#### 4. **Correct Port Confirmed**
- `/dev/ttyS3` is the primary communication port
- `/dev/ttyS1` was a false lead from binary analysis

### Source Documents:
- `SERIAL_MITM_APPROACH.md`
- `return2dock_capture.log`

---

## Phase 5: Successful Implementation
**Date**: October 30, 2025
**Method**: Rust implementation based on MITM findings

### Working Code:
- `src/bin/gd32_init_test.rs` successfully communicates with GD32
- Implements correct initialization sequence
- Receives CMD=0x15 status packets
- Maintains heartbeat communication

### Validated Protocol:
1. Open `/dev/ttyS3` at 115200 baud
2. Send CMD=0x08 init packets every 200ms
3. Wait for CMD=0x15 response
4. Send CMD=0x07 (version), CMD=0x06 (wake), CMD=0x8D (mode)
5. Maintain CMD=0x66 heartbeat every 20ms
6. Receive periodic CMD=0x15 status updates

---

## Summary of Key Corrections

| Aspect | Initial Belief | Actual Reality | Discovery Method |
|--------|---------------|----------------|------------------|
| Serial Port | `/dev/ttyS1` | `/dev/ttyS3` | strace + MITM |
| Communication | One-way | Bidirectional | Serial MITM |
| GD32 Response | Never responds | CMD=0x15 status packets | Serial MITM |
| CMD 0x08 | SetIMUZero | Initialization/Wakeup | Serial MITM |
| CMD 0x66 | Motor Velocity | Heartbeat | Serial MITM |
| Initialization | Not needed | Critical (CMD=0x08 loop) | Serial MITM |
| CRC Algorithm | Unknown | 16-bit word sum + XOR | Binary decompilation |

---

## Lessons Learned

1. **Binary analysis has limitations** - String references can be misleading
2. **Direct observation beats assumptions** - Serial MITM revealed the truth
3. **Timing matters** - Initialization sequence requires patience (~5 seconds)
4. **Error states are informative** - Red LED indicated missing heartbeat
5. **Bidirectional protocols need both sides** - Must capture RX and TX

---

## Current Status

✅ **VERIFIED WORKING PROTOCOL**
- **Documentation**: **[GD32_PROTOCOL_FINAL.md](GD32_PROTOCOL_FINAL.md)** - Complete verified specification
- **Implementation**: **[auxctrl-rust/](Firmware/auxctrl-rust/README.md)** - Rust library with working code
- **Confidence**: High (based on successful communication and serial MITM capture)

The protocol is now fully understood and successfully implemented.

---

## Related Documentation

- **[GD32 Protocol - VERIFIED](GD32_PROTOCOL_FINAL.md)** - Complete protocol specification
- **[Serial MITM Approach](SERIAL_MITM_APPROACH.md)** - How we captured the traffic
- **[Test Results](TEST_RESULTS.md)** - What worked and what didn't
- **[AuxCtrl Binary Details](AuxCtrl-Details.md)** - Original binary analysis
- **[Checksum Algorithm - VERIFIED](../GD32F1/CHECKSUM_ALGORITHM.md)** - Complete checksum algorithm (99.8% verified)
- **[Hardware Connections](../Motherboard/Connection_Evidence.md)** - Physical layer evidence

### Historical Documents (Outdated)
- [Research/backup/Analysis/](../backup/README.md) - Contains outdated research files with warnings