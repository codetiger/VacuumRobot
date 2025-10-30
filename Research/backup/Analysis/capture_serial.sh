#!/bin/sh
# Simple serial traffic capture - just logs data to file

DURATION=${1:-300}  # Default 5 minutes
OUTPUT="/mnt/UDISK/serial_capture_$(date +%Y%m%d_%H%M%S).log"

echo "Starting serial capture for ${DURATION} seconds..."
echo "Output: $OUTPUT"
echo ""

# Check if AuxCtrl is running
if ! pidof AuxCtrl > /dev/null; then
    echo "Starting AuxCtrl..."
    /usr/sbin/AuxCtrl &
    sleep 2
fi

AUXCTRL_PID=$(pidof AuxCtrl)
echo "AuxCtrl PID: $AUXCTRL_PID"
echo "Capturing..."
echo ""

# Capture both read and write on file descriptor 7 (ttyS1)
strace -e read,write -xx -s 1000 -p $AUXCTRL_PID 2>&1 | \
    grep -E "write\(7|read\(7" > "$OUTPUT" &

CAPTURE_PID=$!

# Wait for duration
sleep $DURATION

# Stop capture
kill $CAPTURE_PID 2>/dev/null
wait $CAPTURE_PID 2>/dev/null

echo ""
echo "Capture complete!"
echo "Log saved to: $OUTPUT"
echo ""
echo "Download with:"
echo "  scp root@vacuum:$OUTPUT ."
