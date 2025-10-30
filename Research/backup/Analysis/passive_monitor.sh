#!/bin/sh
# Passive Serial Monitor
# Just reads from serial port while AuxCtrl is running
# Uses a separate read-only file descriptor

DURATION=${1:-30}
OUTPUT="/tmp/passive_capture_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================================"
echo "Passive Serial Monitor"
echo "================================================================================"
echo "Duration: $DURATION seconds"
echo "Output: $OUTPUT"
echo ""
echo "This captures data from /dev/ttyS1 while AuxCtrl is running"
echo "(May miss some data due to AuxCtrl consuming it)"
echo ""
echo "Starting in 2 seconds..."
sleep 2

# Try to open port for reading in non-blocking mode
echo "[+] Attempting to read from /dev/ttyS1..."
echo "" > "$OUTPUT"

dd if=/dev/ttyS1 bs=1 count=$((DURATION * 1000)) 2>/dev/null | hexdump -C > "$OUTPUT" &
DD_PID=$!

echo "[+] Capture started (PID: $DD_PID)"
echo "[*] Recording for $DURATION seconds..."
echo ""

# Wait for duration
sleep $DURATION

# Stop capture
kill $DD_PID 2>/dev/null
wait $DD_PID 2>/dev/null

echo ""
echo "================================================================================"
echo "CAPTURE COMPLETE"
echo "================================================================================"

SIZE=$(wc -c < "$OUTPUT")
LINES=$(wc -l < "$OUTPUT")

echo "Captured: $SIZE bytes ($LINES lines)"
echo "File: $OUTPUT"
echo ""

if [ "$SIZE" -gt 100 ]; then
    echo "✅ Data captured! Sample:"
    head -20 "$OUTPUT"
else
    echo "⚠️  No data captured"
    echo ""
    echo "This is normal - AuxCtrl consumes the data before we can read it"
    echo ""
    echo "Alternative approach needed:"
    echo "  - Use hardware serial tap (logic analyzer)"
    echo "  - Or compile custom version of AuxCtrl with logging"
fi

echo ""
echo "To download:"
echo "  scp root@vacuum:$OUTPUT ."
echo "================================================================================"
