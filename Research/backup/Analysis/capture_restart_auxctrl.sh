#!/bin/sh
# Restart AuxCtrl under strace to capture all serial communication

DURATION=${1:-300}
OUTPUT="/mnt/UDISK/serial_full_$(date +%Y%m%d_%H%M%S).log"

echo "========================================"
echo "AuxCtrl Serial Capture (with restart)"
echo "========================================"
echo "Duration: ${DURATION} seconds"
echo "Output: $OUTPUT"
echo ""
echo "WARNING: This will restart AuxCtrl!"
echo "Press Ctrl+C within 5 seconds to cancel..."
sleep 5

# Stop existing AuxCtrl
echo "Stopping AuxCtrl..."
killall AuxCtrl 2>/dev/null
sleep 2

# Start AuxCtrl under strace
echo "Starting AuxCtrl with strace..."
strace -e read,write -xx -s 1000 -o "$OUTPUT" /usr/sbin/AuxCtrl &
STRACE_PID=$!

echo "Capture started (PID: $STRACE_PID)"
echo "AuxCtrl is now running under strace"
echo ""
echo "Recording for ${DURATION} seconds..."
echo "(You can now operate the vacuum normally)"
echo ""

# Wait for duration
sleep $DURATION

# Stop strace (which will stop AuxCtrl)
echo ""
echo "Stopping capture..."
kill $STRACE_PID 2>/dev/null
sleep 2

# Restart AuxCtrl normally
echo "Restarting AuxCtrl normally..."
/usr/sbin/AuxCtrl &

echo ""
echo "========================================"
echo "Capture complete!"
echo "========================================"
ls -lh "$OUTPUT"
echo ""
echo "Lines captured:"
wc -l "$OUTPUT"
echo ""
echo "Download with:"
echo "  scp root@vacuum:$OUTPUT ."
