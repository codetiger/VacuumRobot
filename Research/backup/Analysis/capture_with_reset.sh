#!/bin/sh
# Restart AuxCtrl under strace AND send GD32 reset command to re-establish communication

DURATION=${1:-300}
OUTPUT="/mnt/UDISK/serial_full_$(date +%Y%m%d_%H%M%S).log"

echo "========================================"
echo "AuxCtrl Capture with GD32 Reset"
echo "========================================"
echo "Duration: ${DURATION} seconds"
echo "Output: $OUTPUT"
echo ""
echo "This script will:"
echo "1. Stop AuxCtrl"
echo "2. Send GD32 restart command"
echo "3. Start AuxCtrl under strace"
echo "4. Capture for ${DURATION} seconds"
echo ""
echo "Press Ctrl+C within 5 seconds to cancel..."
sleep 5

# Stop existing AuxCtrl
echo "[1] Stopping AuxCtrl..."
killall AuxCtrl 2>/dev/null
sleep 2

# Try to send restart command to GD32 (Command 0x9A)
echo "[2] Attempting to reset GD32..."
# Packet format: FA FB LEN CMD CRC
# CMD 0x9A (restart), no payload, LEN=2 (CMD+CRC)
# Need correct CRC - trying simple XOR: 0x02^0x9A = 0x98
echo -ne "\xFA\xFB\x02\x9A\x98" > /dev/ttyS1 2>/dev/null

sleep 1

# Start AuxCtrl under strace
echo "[3] Starting AuxCtrl with strace..."
strace -e read,write -xx -s 1000 -o "$OUTPUT" /usr/sbin/AuxCtrl &
STRACE_PID=$!

echo "[+] Capture started (PID: $STRACE_PID)"
echo ""
echo "Recording for ${DURATION} seconds..."
echo "(Operate the vacuum normally now)"
echo ""

# Wait for duration
sleep $DURATION

# Stop strace
echo ""
echo "[4] Stopping capture..."
kill $STRACE_PID 2>/dev/null
sleep 2

# Restart AuxCtrl normally
echo "[5] Restarting AuxCtrl normally..."
/usr/sbin/AuxCtrl &

echo ""
echo "========================================"
echo "Capture complete!"
echo "========================================"
ls -lh "$OUTPUT"
echo ""
echo "Check if GD32 responded:"
grep -c "read(4" "$OUTPUT" || grep -c "read(7" "$OUTPUT"
echo "read operations found"
echo ""
echo "Download with:"
echo "  scp root@vacuum:$OUTPUT ."
