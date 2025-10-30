# [OUTDATED] GD32 Initialization Sequence Analysis

**⚠️ OUTDATED**: This document contains incorrect information. See `Research/Software/Firmware/auxctrl-rust/GD32_PROTOCOL_FINAL.md` for verified protocol information.

**Key errors in this document**:
- Wrong serial port (/dev/ttyS3 is correct, not /dev/ttyS1)
- Incorrect assumption that GD32 doesn't respond (it does with CMD=0x15)
- CMD=0x66 is heartbeat, not motor velocity
- CMD=0x08 is initialization, not IMU zero

## Key Discovery: Communication Triggered by External Event

AuxCtrl does NOT immediately communicate with GD32 after opening the serial port. Instead:

1. Opens `/dev/ttyS3` (FD 4) - **NOT /dev/ttyS1!**
2. Configures terminal settings
3. **Waits for external trigger** (36,000+ lines of strace between open and first write)
4. External trigger: `recvfrom(8, ...)` receives 46 bytes from socket FD 8
5. **Then** sends first packet to GD32

## Complete Initialization Sequence

### 1. Serial Port Opening
```
open("/dev/ttyS3", O_RDWR|O_NONBLOCK|O_LARGEFILE) = 4
```

### 2. Terminal Configuration
```
ioctl(4, TCGETS, {B115200 -opost -isig -icanon -echo ...}) = 0
ioctl(4, TCFLSH, 0) = 0  # Flush both input and output queues
ioctl(4, TCSETS, {B115200 -opost -isig -icanon -echo ...}) = 0
```

**Terminal Settings** (abbreviated by strace):
- Baud rate: `B115200` (115200 bps)
- Output processing: `-opost` (no output processing)
- Signal generation: `-isig` (no signal generation for special chars)
- Canonical mode: `-icanon` (raw mode, no line buffering)
- Echo: `-echo` (no echo)

### 3. Wait for Trigger
- After serial port setup, AuxCtrl waits
- Monitoring multiple file descriptors with `select()`
- Receives trigger from FD 8 (probably network socket - robot control commands)

### 4. First Packet Sent to GD32
```
recvfrom(8, "\260\251gXX\2\0\0\16\0\0\0...", 46, 0, NULL, NULL) = 46
write(4, "\372\373\vf\0\0\0\0\0\0\0\0f\0", 14) = 14
```

**First Packet Breakdown**:
- `FA FB` - Sync bytes
- `0B` - Length (11 bytes: CMD + DATA + CRC)
- `66` - CMD ID (new command, not seen before)
- `00 00 00 00 00 00 00 00 66` - 9 bytes data
- `00` - CRC (verified correct: 0x66 XOR 8x0x00 XOR 0x66 = 0x00)

Note: There's likely a 14th byte at the end that might be a terminator.

## Why Our Tests Failed

### Problem 1: Wrong Port
- We were using `/dev/ttyS1`
- Correct port is `/dev/ttyS3`

### Problem 2: No Trigger/Context
- GD32 communication is **event-driven**, not autonomous
- Just sending heartbeats isn't enough
- First packet (CMD 0x66) appears to be triggered by external command
- This might be setting up motor control or sensor parameters

### Problem 3: Missing Initialization Command
- We tried heartbeat (0x06) and status request (0x0D)
- But the FIRST command is actually 0x66
- This might be required to "wake up" or configure the GD32

## CRITICAL DISCOVERY: GD32 Does NOT Respond!

### Test Results Summary

**Test 1**: Sent CMD 0x66 initialization + heartbeats
- Result: 0 bytes received
- Conclusion: GD32 does not respond to our commands

**Test 2**: Analyzed AuxCtrl's own strace
- Result: ALL `select(5, [4], ...)` calls timeout with `= 0 (Timeout)`
- Result: NO reads from FD 4 (ttyS3) ever succeed
- **SHOCKING CONCLUSION**: **GD32 does NOT respond even to AuxCtrl!**

### What This Means

The communication with GD32 appears to be **ONE-WAY ONLY**:
- AuxCtrl sends commands to GD32 via /dev/ttyS3
- GD32 does NOT send responses back
- GD32 likely:
  - Receives commands and executes them
  - Controls motors/sensors based on commands
  - But provides NO feedback over UART

This explains:
1. Why we never received responses in our tests
2. Why AuxCtrl has select() calls that always timeout
3. Why there are no read() calls from FD 4 in strace

### Architectural Hypothesis

The vacuum robot likely uses a different communication model:
- **Command Path**: A33 → UART → GD32 (motor control commands)
- **Feedback Path**: GD32 → ??? → A33 (possibly different interface)

Possible feedback mechanisms:
1. **Separate serial port**: GD32 TX might be on different ttyS port
2. **GPIO-based signaling**: Status via GPIO pins (gpio-39, gpio-107, gpio-233)
3. **No feedback**: GD32 is fully autonomous, no status reporting
4. **Shared memory**: Using SPI or I2C for status (not UART)

### Evidence for One-Way Communication

1. **strace shows**: Write-only pattern to FD 4
2. **No read syscalls**: No `read(4, ...)` in entire strace
3. **Select always times out**: GD32 TX line appears inactive
4. **GPIO usage**: gpio-233 exported by sysfs - might be status signal

## Next Steps

### Option 1: Find GD32 Feedback Mechanism ✅ PRIORITY
1. Check if there's another ttyS port for GD32 RX data
2. Monitor ALL GPIO pins during motor operation
3. Check for SPI/I2C communication channels
4. Look for shared memory or message queues

### Option 2: Test Motor Control Commands
Since GD32 appears to accept commands without responding:
1. Send motor control commands from captured protocol
2. Observe physical motor behavior
3. Monitor GPIO pins for status changes
4. This would prove one-way communication works

### Option 3: Analyze GPIO During Operation
- Monitor gpio-39 (input, LOW)
- Monitor gpio-107 (output, HIGH)
- Monitor gpio-233 (sysfs-controlled, HIGH)
- Check if these change during motor operations
- These might be: RESET, ENABLE, STATUS_READY, etc.

### Option 4: Search for Other UART Ports
```bash
# Check all ttyS ports
ls -la /dev/ttyS*
# Monitor all for activity
dd if=/dev/ttyS0 bs=1 | hexdump -C &
dd if=/dev/ttyS1 bs=1 | hexdump -C &
dd if=/dev/ttyS2 bs=1 | hexdump -C &
# ttyS3 is already known for TX to GD32
```

## Terminal Configuration Details

From strace (abbreviated):
```
ioctl(4, TCGETS, {B115200 -opost -isig -icanon -echo ...}) = 0
ioctl(4, TCFLSH, 0) = 0
ioctl(4, TCSETS, {B115200 -opost -isig -icanon -echo ...}) = 0
```

This is raw mode configuration - standard for binary protocol communication.
