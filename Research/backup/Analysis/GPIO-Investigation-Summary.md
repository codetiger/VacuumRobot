# GPIO Investigation Summary

## Date
October 28, 2025

## Objective
Determine if GPIO pins are required for GD32 communication and identify which pins/configuration is needed.

## Key Discoveries

### 1. CGpioControl Class Found
AuxCtrl binary contains a `CGpioControl` class with methods:
- `CGpioControl::GpioInit()`
- `CGpioControl::GpioSetDirection()`
- `CGpioControl::GpioExport()`
- `CGpioControl::GpioUnexport()`

### 2. Sysfs GPIO Access Confirmed
Strings found in binary:
```
/sys/class/gpio/export
/sys/class/gpio/unexport
/sys/class/gpio/gpio%d/direction
/sys/class/gpio/gpio%d/value
```

AuxCtrl uses standard Linux sysfs GPIO interface.

### 3. Active GPIO Pins Identified

From `/sys/kernel/debug/gpio`:
```
GPIOs 0-383, platform/sunxi-pinctrl, sunxi-pinctrl:
 gpio-39  (?                   ) in  lo
 gpio-107 (?                   ) out hi
 gpio-233 (sysfs               ) out hi  <-- Exported by AuxCtrl!
```

**GPIO 233** is actively controlled by AuxCtrl:
- Direction: Output
- Value: High (1)
- Exported via sysfs (confirmed by "sysfs" label)

### 4. STM32 References
Binary refers to the GD32 as "STM32" (compatible microcontroller family):
- `enableStm32ReceiveData()`
- `getStm32ReceiveData()`
- `packetStm32Sleep()`
- `g_stm32_status`
- `g_stm32_serial_state`

### 5. Multiple Serial Ports
Found device paths:
- `/dev/ttyS1` - GD32 communication (confirmed)
- `/dev/ttyS3` - Purpose unknown
- `/dev/ttyS0` - Console

## Test Results

### Test 1: GPIO 233 Toggle with Heartbeat
**Method**:
1. Stopped AuxCtrl
2. Toggled GPIO 233 LOW for 100ms then back HIGH (reset pulse)
3. Sent STATUS_REQUEST (0x0D) and HEARTBEAT (0x06) packets
4. Total: 175 packets over 20 seconds

**Result**: ❌ FAILURE - 0 bytes received

**Conclusion**: GPIO 233 toggle alone is NOT sufficient to enable GD32 communication.

## Analysis

### What We Know
✓ Correct baud rate: 115200
✓ Correct CRC: CMD XOR DATA
✓ Correct packet structure: FA FB LEN CMD DATA CRC
✓ GPIO 233 is controlled by AuxCtrl (output high)
✗ GPIO 233 alone doesn't enable communication

### What's Missing
One or more of:
1. **Additional GPIO pins** (gpio-39, gpio-107, or others not yet exported)
2. **Specific GPIO initialization sequence** (timing, order of operations)
3. **Other hardware initialization** (memory-mapped registers, clock configuration)
4. **Serial port configuration beyond standard settings** (special ioctl calls)

## GPIO Pin Analysis

### GPIO 233
- **State**: Output, HIGH
- **Control**: Exported by AuxCtrl via sysfs
- **Purpose**: Unknown (power enable? communication enable? chip select?)
- **Test Result**: Toggling alone doesn't work

### GPIO 107
- **State**: Output, HIGH
- **Control**: Not exported (direct kernel driver?)
- **Purpose**: Unknown
- **Action Needed**: Try controlling this pin

### GPIO 39
- **State**: Input, LOW
- **Control**: Not exported
- **Purpose**: Unknown (handshake? ready signal?)
- **Action Needed**: Monitor if it changes when AuxCtrl runs

## Motherboard Reference

From `Research/Motherboard/README.md`, GD32F103VCT6 connections:
- Serial communication via USART (likely USART1 = /dev/ttyS1)
- Multiple GPIO pins available on 100-pin package
- Possible control pins: RESET (NRST), BOOT0, BOOT1

## Next Investigation Steps

### Priority 1: Find ALL GPIO Initialization
**Method**: Analyze AuxCtrl binary in Ghidra
- Decompile `CGpioControl::GpioInit()`
- Find all GPIO numbers used (look for constants 39, 107, 233, etc.)
- Identify initialization sequence and timing

**Tools**:
- Ghidra scripts: `FindGPIOInit.py`, `AnalyzeGPIO.py`
- Search for hex values: 0x27 (39), 0x6B (107), 0xE9 (233)

### Priority 2: Monitor GPIO Changes During AuxCtrl Startup
**Method**: Capture GPIO state before and during AuxCtrl execution
```bash
# Before
cat /sys/kernel/debug/gpio > gpio_before.txt

# Start AuxCtrl

# After (immediately)
cat /sys/kernel/debug/gpio > gpio_after.txt

# Compare
diff gpio_before.txt gpio_after.txt
```

### Priority 3: Full System Call Trace
**Method**: Capture ALL system calls when AuxCtrl starts
```bash
strace -f -e trace=all -o /tmp/auxctrl_full.strace /usr/sbin/AuxCtrl
```

Look for:
- `open()` calls to `/sys/class/gpio/*`
- `write()` calls with GPIO numbers
- `ioctl()` calls (hardware control)
- `mmap()` calls (memory-mapped I/O)

### Priority 4: Try Controlling GPIO 107 and 39
**Method**: Test if additional GPIO pins are required
```bash
# Export and test GPIO 107
echo 107 > /sys/class/gpio/export
echo out > /sys/class/gpio/gpio107/direction

# Try different combinations
echo 1 > /sys/class/gpio/gpio107/value
# ... send heartbeats ...

echo 0 > /sys/class/gpio/gpio107/value
# ... send heartbeats ...
```

### Priority 5: Hardware Analysis
If software analysis fails:
- Use logic analyzer on GD32 pins
- Monitor RESET, BOOT0, BOOT1 pins
- Check power rails
- Verify clock signals

## Code Locations

### Binary Analysis
- **AuxCtrl binary**: `/Users/codetiger/Development/VacuumRobot/Research/backup/binaries/AuxCtrl`
- **GPIO strings**: Found at offsets 0x2960, 0x8010, etc.
- **CGpioControl class**: Multiple member functions identified

### Ghidra Scripts Created
- `AnalyzeGPIO.py` - Analyze GPIO and STM32 control functions
- `FindGPIOInit.py` - Find GPIO initialization and pin numbers
- `FindBaudRate.py` - Analyze baud rate configuration (completed)
- `FindCRC.py` - Analyze CRC calculation (completed)

### Test Scripts Created
- `test_with_gpio.sh` - Test communication with GPIO 233 toggle
- `boot_test_gd32.sh` - Test at boot before AuxCtrl
- `heartbeat_correct_crc.sh` - Test with verified CRC algorithm

## Hardware Details

### Allwinner A33 (Main SoC)
- **GPIO Banks**: Multiple banks (PA, PB, PC, PD, PE, PF, PG)
- **GPIO Numbering**: Bank offset + pin number
  - Example: PH9 = GPIO 233 (H bank starts at 224, +9 = 233)
- **Control**: `/sys/class/gpio/` (sysfs) or `/dev/mem` (direct)

### GD32F103VCT6 (Secondary MCU)
- **Family**: ARM Cortex-M3 (STM32-compatible)
- **Package**: LQFP100 (100 pins)
- **USART**: Multiple (likely USART1 for communication)
- **Control Pins**:
  - NRST: Reset (active low)
  - BOOT0, BOOT1: Boot mode selection

## Hypothesis

**Most Likely Scenario**:
AuxCtrl performs the following initialization sequence:
1. Export and configure GPIO 233 (confirmed - already done)
2. Export and configure GPIO 107 (hypothesis - needs testing)
3. Possibly toggle RESET pin (could be gpio-39 or another pin)
4. Wait for GD32 to boot/initialize
5. Begin serial communication

**Alternative Scenarios**:
- GPIO pins control power domains or voltage regulators for GD32
- Special ioctl configuration of UART beyond standard 115200 8N1
- Memory-mapped register configuration for UART muxing/routing
- GD32 requires specific boot sequence (BOOT0/BOOT1 pin control)

## Critical Question

**What is the exact sequence of GPIO operations that AuxCtrl performs before opening /dev/ttyS1?**

This can be answered by:
1. Decompiling CGpioControl::GpioInit() in Ghidra
2. Running full strace on AuxCtrl from start
3. Comparing GPIO states before/after AuxCtrl starts

## Conclusion

GPIO control is clearly part of the initialization process (CGpioControl class exists, GPIO 233 is actively used), but:
- GPIO 233 alone is insufficient
- Need to identify complete GPIO initialization sequence
- Likely requires multiple pins in specific order/timing
- Decompilation of CGpioControl functions is the most direct path forward

**Recommendation**: Prioritize Ghidra analysis of CGpioControl::GpioInit() to extract the complete initialization sequence.
