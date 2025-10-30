# AuxCtrl Startup Sequence Analysis

**Analyzed File**: `serial_startup_20251028_164614.log` (8.5KB)
**Capture Date**: 2025-10-28
**Method**: strace during AuxCtrl restart

---

## Startup Timeline

### Phase 1: Library Loading (Lines 1-2)
**File Descriptor 3** - Standard ELF binary loading
- Dynamic linker loading shared libraries
- Normal startup procedure

### Phase 2: Secondary Serial Port Check (Lines 3-5)
**File Descriptor 7** = `/dev/ttyS3`

```
read(7, "\x31\x0a", 1023) = 2      # Read ASCII "1\n"
read(7, "\x31", 1023) = 1          # Read ASCII "1"
read(7, "", 1023) = 0              # EOF - no more data
```

**Analysis**:
- AuxCtrl reads from ttyS3 at startup
- Receives: `"1\n1"` (ASCII 0x31 0x0A 0x31)
- Likely a device ID or readiness check from another peripheral
- Could be factory test interface or secondary MCU

### Phase 3: GD32 Communication Loop (Lines 6-27)
**File Descriptor 4** = `/dev/ttyS1` (GD32F103)

```
write(4, "\xfa\xfb\x03\x0d\x00\x0d", 6) = 6
```
**Repeated 22 times** with no responses

#### Packet Structure:
```
FA FB 03 0D 00 0D
│  │  │  │  │  └─ CRC: 0x0D
│  │  │  │  └──── DATA: 0x00
│  │  │  └─────── CMD: 0x0D (heartbeat/status request)
│  │  └────────── LEN: 0x03 (CMD + DATA + CRC = 3 bytes)
│  └───────────── SYNC2: 0xFB
└──────────────── SYNC1: 0xFA
```

**Command 0x0D**: Heartbeat/keep-alive packet
- Sent immediately upon startup
- No initialization commands precede it
- Sent every ~50-100ms
- **No responses received from GD32**

### Phase 4: Process Termination (Lines 28-29)
```
SIGTERM (sent by PID 1 - init)
Process killed
```

---

## Critical Finding: No Initialization Sequence

### ❌ Expected Commands NOT FOUND:

Based on AuxCtrl-Details.md, these initialization commands were expected but absent:

| Command | ID | Purpose | Status |
|---------|-----|---------|--------|
| `packetR16Power()` | 0x99 | Enable GD32 power | ❌ Not sent |
| `packetRestartR16System()` | 0x9A | Reset GD32 | ❌ Not sent |
| `packetRequireSystemVersion()` | 0x07 | Request firmware version | ❌ Not sent |
| IMU calibration | 0x08, 0xA1 | Sensor initialization | ❌ Not sent |
| Motor config | 0x65 | Set control mode | ❌ Not sent |
| Peripheral power | 0x97, 0x9B | Lidar, charger | ❌ Not sent |

### ✅ What Actually Happens:

1. AuxCtrl opens `/dev/ttyS1`
2. **Immediately** starts sending heartbeat (0x0D)
3. Expects GD32 to already be running
4. No handshake protocol
5. No initialization sequence

---

## Why Restarting AuxCtrl Breaks Communication

### The Problem:

**GD32 maintains state between AuxCtrl restarts:**

1. **Normal boot sequence:**
   - Hardware powers on → GD32 boots → Loads firmware
   - Linux boots → AuxCtrl starts
   - GD32 already initialized and waiting
   - Communication begins successfully

2. **AuxCtrl restart scenario:**
   - GD32 still running from previous session
   - Expecting heartbeats every 50ms
   - AuxCtrl stops → heartbeats stop
   - GD32 timeout occurs → enters error state
   - AuxCtrl restarts → sends heartbeats
   - **GD32 doesn't respond** (stuck in error state)
   - Red LED indicates comm error

### Root Cause:

**No software reset mechanism in the protocol.**
- AuxCtrl assumes GD32 is ready
- GD32 assumes continuous operation
- Breaking the session requires hardware reset

---

## GD32 Initialization Must Happen Before AuxCtrl

### Hypothesis: Boot-time Initialization

The GD32 is likely initialized by:

1. **Hardware power sequencing**
   - PMIC (AXP223) powers GD32 rail
   - GD32 boots and loads firmware from flash
   - Auto-starts main loop

2. **Bootloader/init scripts**
   - `/etc/init.d/` scripts may control power GPIO
   - `packetR16Power(0x99)` might be called once at boot
   - Then never called again

3. **GD32 firmware design**
   - Runs independently after power-on
   - Waits for serial commands
   - No re-initialization protocol

---

## Implications for Protocol Testing

### What We Learned:

✅ **SYNC bytes confirmed**: `0xFA 0xFB`
✅ **Heartbeat command**: `0x0D`
✅ **Packet structure**: `SYNC1 SYNC2 LEN CMD DATA... CRC`
❌ **CRC algorithm**: Still unknown (0x0D appears correct for this packet)
❌ **No init handshake**: Makes testing harder

### Why Our Test Script Failed:

When we send command 0x07 (version request):
- GD32 not in correct state to respond
- Needs continuous heartbeats to stay alive
- Missing prior session context

### Next Steps for Testing:

1. **Power cycle approach:**
   - Send reset command: `packetRestartR16System(0x9A)`
   - Wait for GD32 reboot
   - Start heartbeat loop
   - Then send test commands

2. **Find CRC algorithm:**
   - Analyze more packets from working session
   - Test CRC-8 variants on known packets
   - The heartbeat packet `FA FB 03 0D 00 0D` is a good test case

3. **Capture working session:**
   - Since strace breaks timing, need alternative
   - Hardware serial tap (logic analyzer)
   - Or accept brief disruption for small captures

---

## Additional Observations

### ttyS3 Mystery Data:

```
read(7, "1\n1")
```

**Possible sources:**
- Factory test interface echo
- Secondary MCU status
- Device ID configuration
- Leftover data in buffer

Requires further investigation.

---

## Files Referenced

- **Log file**: `Research/Software/serial_startup_20251028_164614.log`
- **Protocol doc**: `Research/Software/AuxCtrl-Details.md`
- **Hardware doc**: `Research/Motherboard/README.md`
