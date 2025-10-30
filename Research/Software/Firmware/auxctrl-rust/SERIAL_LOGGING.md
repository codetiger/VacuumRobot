# Serial Port Logging Solutions

## Problem
We need to log all bidirectional communication between AuxCtrl and /dev/ttyS3 (GD32) without breaking timing.

## Solutions

### Solution 1: Using `socat` (if available)

```bash
# Check if socat is available
which socat

# Create virtual serial port pair and log everything
socat -d -d \
  pty,raw,echo=0,link=/tmp/vserial \
  open:/dev/ttyS3,b115200,raw,echo=0 \
  2>&1 | tee /tmp/serial.log &

# Then modify AuxCtrl to use /tmp/vserial instead of /dev/ttyS3
# Or create symlink:
mv /dev/ttyS3 /dev/ttyS3.real
ln -s /tmp/vserial /dev/ttyS3
```

### Solution 2: Kernel Debug (Simple and Non-Intrusive)

Enable kernel UART debugging:

```bash
# Enable UART driver debug output
echo 8 > /proc/sys/kernel/printk
dmesg -w | grep -i 'uart\|ttyS3' > /tmp/uart_kernel.log &

# This will log kernel-level UART events
```

### Solution 3: Modified AuxCtrl Binary (Patch)

Since we can't easily intercept the port, we can:
1. Decompile AuxCtrl
2. Find the open("/dev/ttyS3") call
3. Patch it to open a different device
4. Use our MITM on the patched version

### Solution 4: Hardware Logic Analyzer (Most Reliable)

Physical approach:
- Connect logic analyzer to UART TX/RX lines
- Capture at 115200 baud
- Tools: PulseView, sigrok

### Solution 5: Analyze Existing Logs (Simplest)

The AuxCtrl logs already show high-level protocol info:

```bash
# Monitor logs in real-time
tail -f /mnt/UDISK/log/AuxCtrl.temp &

# Trigger actions (press buttons, start cleaning, etc.)
# Correlate log entries with actions
```

## Recommended Approach for This Project

Given the constraints:
1. **No Python** on device
2. **No socat** (likely)
3. **strace breaks timing**
4. **Complex PTY creation** in Rust

**Best option: Analyze AuxCtrl logs + GPIO monitoring**

We already have:
- GPIO monitor showing reset pulses
- AuxCtrl logs showing sleep states, commands
- Understanding of packet format from reverse engineering

### What We Know from Existing Analysis:

1. **TX (AuxCtrl → GD32)** - We can capture with strace on write() briefly or our Rust test programs
2. **RX (GD32 → AuxCtrl)** - Likely minimal or none (one-way protocol suspected)
3. **State tracking** - AuxCtrl logs show "Sleep state", "lost count", etc.

### Next Steps:

1. **Test if GD32 sends responses** at all:
   - Use our `simple_test` program
   - Add read support to GD32Connection
   - Try reading after each command

2. **Capture specific sequences**:
   - Boot sequence (already partially known)
   - Return-to-dock (GPIO captured)
   - Button presses
   - Error conditions

3. **Document protocol fully** based on:
   - Reverse engineering (already done)
   - Log correlation
   - GPIO timing
   - Our test results

## Conclusion

For this vacuum robot project, **bidirectional logging may not be necessary** because:
1. Protocol appears to be primarily one-way (A33 → GD32)
2. GD32 responses are reflected in GPIO state changes (gpio-39)
3. AuxCtrl logs show high-level state ("Sleep state 0/1", "lost count", etc.)
4. We've already reverse-engineered the packet format

**Recommendation**: Focus on understanding the GD32 wakeup mechanism and sleep state management rather than capturing every byte, since we already know the command format.
