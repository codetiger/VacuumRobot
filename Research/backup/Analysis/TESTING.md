# Testing the GD32 Communication Protocol

## Preparation

### 1. Copy test script to the vacuum device
```bash
# On your computer
scp Research/Software/test_version_request.py root@vacuum:/mnt/UDISK/
```

### 2. SSH into the vacuum
```bash
ssh root@vacuum
# Password: <your-password>
```

### 3. Stop AuxCtrl to avoid conflicts
```bash
# Check if it's running
ps aux | grep AuxCtrl

# Stop it
killall AuxCtrl

# Verify it's stopped
ps aux | grep AuxCtrl
```

## Running the Test

### Option 1: Automated Testing (Try all combinations)
```bash
cd /mnt/UDISK
python3 test_version_request.py
```

This will systematically test:
- 5 different baud rates (115200, 230400, 460800, 57600, 9600)
- 4 sync byte combinations (0xFA/0xFB, 0xAA/0x55, 0xFA/0xAF, 0x5A/0xA5)
- 3 CRC algorithms (SUM, CRC16-CCITT, CRC16-MODBUS)

### Option 2: Manual Testing with Known Parameters
If you already know the parameters from packet capture:

```python
import serial

# Adjust these based on your capture
SYNC1 = 0xFA
SYNC2 = 0xFB
BAUD = 115200

ser = serial.Serial('/dev/ttyS1', BAUD, timeout=0.5)

# Version request packet (update with correct CRC)
packet = bytes([SYNC1, SYNC2, 0x00, 0x07, 0x??, 0x??])  # Add CRC

ser.write(packet)
response = ser.read(100)
print(response.hex(' '))
```

## What to Look For

### Success Indicators
1. **Any response received** - even if malformed, means we're on the right track
2. **Response starts with same sync bytes** - confirms protocol match
3. **Response command ID != 0x07** - likely a response command (maybe 0x07 echo or different ID)
4. **Response length > 6 bytes** - contains actual version data

### Expected Response Format
```
SYNC1 SYNC2 LENGTH CMD_ID [VERSION_DATA...] CRC_HI CRC_LO
```

Version data might be:
- ASCII string (e.g., "v1.0.3")
- Binary version (e.g., major.minor.patch as bytes)
- Multiple fields (MCU version, protocol version, etc.)

## Capturing Live Traffic

If automated test doesn't work, capture real AuxCtrl traffic:

```bash
# Start AuxCtrl back up
/usr/sbin/AuxCtrl &

# Monitor what it sends to ttyS1
strace -e write -s 1000 -p $(pidof AuxCtrl) 2>&1 | grep ttyS1

# Or use hexdump
cat /dev/ttyS1 | hexdump -C
```

Look for:
- Repeating patterns (heartbeat/status packets)
- Sync bytes at start of packets
- Packet structure matching our expected format

## Troubleshooting

### No response at all
1. Check port is correct: `ls -la /dev/ttyS*`
2. Verify GD32 is powered: Check if you see any traffic with `cat /dev/ttyS1 | hexdump -C`
3. Try different baud rates
4. Check if AuxCtrl is still running: `ps aux | grep Aux`

### Garbage/corrupted response
1. Wrong baud rate - try others
2. Wrong sync bytes - try different combinations
3. Timing issue - add delays between packets

### Port busy error
```bash
killall -9 AuxCtrl
# Wait a few seconds
python3 test_version_request.py
```

## After Testing

### Restart normal operation
```bash
# Restart AuxCtrl
/usr/sbin/AuxCtrl &

# Or reboot
reboot
```

## Recording Results

Document your findings:
```
Baud Rate: _______
SYNC1: 0x__
SYNC2: 0x__
CRC Algorithm: _______

Request sent:
[hex dump]

Response received:
[hex dump]

Observations:
- Response command ID: 0x__
- Version data: _______
- Notes: _______
```
