# Heartbeat Monitor Test Instructions

## Purpose

This test validates our protocol understanding by:
1. Keeping GD32 alive with heartbeat packets (every 50ms)
2. Recording all sensor data responses from GD32
3. Allowing manual manipulation to see sensor reactions

## Setup

### 1. SSH into the device

```bash
ssh root@vacuum
# Password: <your-password>
```

### 2. Stop AuxCtrl

```bash
killall AuxCtrl
```

**Important**: Verify it's stopped:
```bash
ps aux | grep AuxCtrl | grep -v grep
```
Should return nothing.

### 3. Run the heartbeat monitor

**For 60 seconds (default)**:
```bash
cd /mnt/UDISK
./heartbeat_monitor.sh
```

**For custom duration** (e.g., 120 seconds):
```bash
./heartbeat_monitor.sh 120
```

## During the Test

While the script is running, try these actions:

### Sensor Tests

1. **Wheel Encoders**:
   - Spin left wheel forward → should see encoder_left value increase
   - Spin right wheel forward → should see encoder_right value increase
   - Spin backwards → values should decrease

2. **Bumpers**:
   - Press front bumper → bumper field should change
   - Release → should return to original value

3. **Cliff Sensors**:
   - Lift robot off ground → cliff sensors should trigger
   - Place back down → should clear

4. **IMU (Accelerometer/Gyro)**:
   - Tilt robot → accel values should change
   - Rotate robot → gyro values should change
   - Keep still → values should stabilize

5. **Battery** (if accessible):
   - Note battery voltage reading
   - Compare to actual battery level

## Expected Output

### Console Display

```
================================================================================
GD32 Heartbeat Monitor
================================================================================
Serial Port: /dev/ttyS1
Baud Rate: 115200
Duration: 60 seconds
Heartbeat: Every 50ms

Starting in 3 seconds...
================================================================================
[+] Serial port opened: /dev/ttyS1
[+] Logging to: /tmp/heartbeat_log_20251028_143022.log

--------------------------------------------------------------------------------
LIVE MONITORING (Ctrl+C to stop)
--------------------------------------------------------------------------------

[14:30:25.123] SENSOR DATA (packet #1):
  timestamp_offset_0  : 12345
  encoder_left?       : 26997
  encoder_right?      : 26999
  imu_accel_x?        : -30
  imu_accel_y?        : 22
  imu_accel_z?        : 41
  bumper?             : 0
  cliff?              : 0

[14:30:26.234] SENSOR DATA (packet #2):
  timestamp_offset_0  : 12356
  encoder_left?       : 27150  ← Changed! (wheel moved)
  encoder_right?      : 26999
  ...
```

### What to Look For

✅ **Success Indicators**:
- Sensor packets (0x15) arrive periodically (~1-2 per second)
- No errors or timeouts
- Values change when you manipulate sensors
- Script runs for full duration without crashing

❌ **Failure Indicators**:
- No sensor packets received
- "Receive packet time 50 ms is over!" errors
- Red LED flashing on device
- Script crashes with serial errors

## After the Test

### 1. Review the output

The script shows real-time sensor changes. Note which fields changed when you:
- Moved wheels
- Pressed bumpers
- Tilted/rotated robot

### 2. Copy the log file

```bash
# On the device, note the log filename shown at the end
# Example: /tmp/heartbeat_log_20251028_143022.log

# From your computer:
scp root@vacuum:/tmp/heartbeat_log_20251028_143022.log .
```

### 3. Restart AuxCtrl

```bash
/usr/sbin/AuxCtrl &
```

Or simply reboot:
```bash
reboot
```

## Troubleshooting

### "Permission denied" on /dev/ttyS1

```bash
# Check if AuxCtrl is still running
ps aux | grep AuxCtrl

# Force kill if needed
killall -9 AuxCtrl

# Retry
python3 heartbeat_monitor.py
```

### No sensor data received

**Possible causes**:
1. GD32 not responding (check power, LEDs)
2. Wrong heartbeat packet format
3. Serial port configuration mismatch
4. GD32 in error state (needs hardware reset)

**Try**:
```bash
# Reboot the device to reset GD32
reboot
```

### "ImportError: No module named serial"

Python serial library missing (unlikely on this device):
```bash
pip3 install pyserial
```

### Script exits immediately

Check Python version:
```bash
python3 --version
```
Should be Python 3.x

## Analysis Goals

After collecting data, we want to determine:

1. **Sensor Packet Structure** (99 bytes):
   - Where are wheel encoder counts? (4 bytes each? signed/unsigned?)
   - Where is IMU data? (6× int16 values?)
   - Where are bumper bits? (bitmask?)
   - Where are cliff sensor bits?
   - Where is battery voltage? (int16? float?)
   - Where is timestamp?

2. **Response Frequency**:
   - How often does GD32 send sensor data?
   - Is it periodic or event-driven?

3. **Protocol Validation**:
   - Does GD32 respond to heartbeats consistently?
   - Do we get timeouts?
   - Is our heartbeat packet correct?

4. **CRC Pattern**:
   - Collect multiple valid packets
   - Try to reverse-engineer CRC algorithm

## Expected Results

If our understanding is correct:
- ✅ GD32 accepts our heartbeat packets (0x06)
- ✅ GD32 sends sensor data periodically (0x15)
- ✅ Sensor values change when we manipulate hardware
- ✅ No timeouts or errors
- ✅ Script runs for full duration

This validates:
- SYNC bytes (0xFA 0xFB)
- Packet structure (LEN, CMD, DATA, CRC)
- Heartbeat command (0x06)
- Sensor response command (0x15)
- Timing requirements (50ms heartbeat)

## Next Steps After Validation

Once we confirm the protocol works:

1. **Decode sensor packet structure completely**
2. **Test other commands** (motor control, LED, etc.)
3. **Reverse-engineer CRC algorithm**
4. **Build custom control software**
5. **Replace AuxCtrl with our own implementation**

---

**Ready to run?**

```bash
ssh root@vacuum
killall AuxCtrl
cd /mnt/UDISK
python3 heartbeat_monitor.py 60
```

Then manipulate the robot and observe the sensor changes!
