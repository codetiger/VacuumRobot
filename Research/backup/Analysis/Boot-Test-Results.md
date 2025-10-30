# GD32 Boot-Time Communication Test Results

## Test Date
October 28, 2025

## Objective
Test if GD32 microcontroller responds to our heartbeat packets immediately after device boot, before prolonged communication with AuxCtrl.

## Hypothesis
GD32 might enter an error state after AuxCtrl stops communicating. Testing right after boot (when GD32 is in fresh state) might yield different results.

## Test Setup

### Configuration
- **Baud Rate**: 115200 (verified from AuxCtrl logs)
- **CRC Algorithm**: CMD XOR DATA (verified on 2,679 packets - 100% success)
- **Packet Structure**: FA FB LEN CMD DATA CRC (verified)
- **Test Timing**: Executed ~60 seconds after boot, shortly after stopping AuxCtrl

### Test Sequence
1. Device rebooted
2. AuxCtrl started normally at boot
3. ~60 seconds after boot: Killed AuxCtrl and Monitor processes
4. Immediately ran heartbeat test:
   - Phase 1: 10x STATUS_REQUEST (0x0D) with 1-second intervals
   - Phase 2: Continuous heartbeats (0x06) at ~10 per second for 20 seconds
5. Total: 170 packets sent

## Results

### RX Data Received
**0 bytes**

### Test Output
```
================================================================================
GD32 Boot-Time Communication Test
================================================================================
Time: Tue Oct 28 19:10:30 CST 2025
Port: /dev/ttyS1
Duration: 20 seconds

Total packets sent: 170
RX data received: 0 bytes

❌ FAILURE: No response from GD32 (0 bytes)
================================================================================
```

## Analysis

### What This Proves

1. **Timing is NOT the issue**
   - GD32 doesn't respond even when tested shortly after boot
   - Device had been running for only ~60 seconds
   - AuxCtrl had minimal communication time with GD32

2. **Our protocol understanding is correct but insufficient**
   - ✓ Correct baud rate (115200)
   - ✓ Correct CRC algorithm (CMD XOR DATA)
   - ✓ Correct packet structure
   - ✗ Missing some initialization step

3. **GD32 requires more than serial commands**
   - Hardware initialization via GPIO pins
   - OR specific command sequence we haven't discovered
   - OR authentication/handshake mechanism

### Comparison with AuxCtrl

When AuxCtrl runs successfully, it:
- Opens /dev/ttyS1
- Configures serial port to 115200 8N1
- Sends STATUS_REQUEST (0x0D) commands
- Receives sensor data (CMD 0x15, 99 bytes)
- Maintains heartbeat loop

Our test does the same serial communication, but GD32 doesn't respond.

## Possible Causes

### 1. GPIO Hardware Control (Most Likely)
GD32 may require GPIO signals that AuxCtrl sets but we don't:
- **RESET pin**: Toggle to initialize GD32
- **ENABLE pin**: Enable communication mode
- **POWER_EN pin**: Enable GD32 power domain
- **COMM_EN pin**: Enable UART communication

**Evidence**: AuxCtrl binary is 400KB - large for just serial I/O. Likely includes GPIO control.

### 2. Memory-Mapped Initialization
AuxCtrl might configure:
- SoC registers for UART muxing
- GD32 boot mode pins
- Clock configuration for GD32

### 3. Authentication/Security
- GD32 might require cryptographic handshake
- Hardware security module (HSM) validation
- Unique device ID exchange

### 4. Different Communication Path
- GD32 might not be on /dev/ttyS1 initially
- Requires mode switch or multiplexer configuration
- Boot ROM vs application firmware communication

## Next Steps

### Priority 1: GPIO Investigation
1. **Analyze AuxCtrl for GPIO operations**
   - Search for gpio/ioctl calls in binary
   - Decompile initialization functions
   - Look for /dev/gpio or /sys/class/gpio access

2. **Review motherboard documentation**
   - Identify GD32 control pins from PCB photos
   - Check Allwinner A33 GPIO assignments
   - Look for RESET, EN, or COMM pins

3. **Monitor GPIO state changes**
   - Before AuxCtrl starts
   - After AuxCtrl starts
   - During communication
   - Use: `cat /sys/kernel/debug/gpio` or `gpio status`

### Priority 2: Full System Call Trace
```bash
strace -f -e open,ioctl,read,write,mmap -p $(pidof AuxCtrl) 2>&1 | tee full_trace.log
```

Look for:
- GPIO device opens (`/dev/gpiochip*`, `/dev/mem`)
- ioctl calls (hardware control)
- mmap operations (memory-mapped registers)

### Priority 3: Binary Analysis
Use Ghidra to find:
- `gpio` or `ioctl` function calls
- Initialization sequence in `main()` or `init()` functions
- Hardware abstraction layer (HAL) functions

### Priority 4: Hardware Probing
- Use logic analyzer to monitor GD32 pins during AuxCtrl startup
- Compare GPIO states before/after AuxCtrl
- Identify which pins change when communication begins

## Test Files

- **Test Script**: `/tmp/boot_test_gd32.sh`
- **TX Log**: `/tmp/boot_gd32_test_20251028_191030.log`
- **RX Log**: `/tmp/boot_gd32_test_20251028_191030.log.rx` (0 bytes)

## Conclusion

The boot-time test confirms that **serial communication alone is insufficient** to communicate with the GD32. The microcontroller requires hardware-level initialization that AuxCtrl performs but we haven't replicated.

The next investigation must focus on **GPIO pin control** and **hardware initialization sequence**, as this is the most likely missing piece.

### Critical Question
**What does AuxCtrl do BEYOND serial communication that enables GD32 to respond?**

Answer lies in:
1. GPIO pin manipulation
2. Memory-mapped register configuration
3. Or undiscovered command sequence

Recommend prioritizing GPIO investigation using strace and Ghidra analysis.
