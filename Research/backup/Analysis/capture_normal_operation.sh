#!/bin/sh
# Capture during normal operation - start vacuum FIRST, then run this script
# Uses short bursts of strace to minimize disruption

DURATION=${1:-30}  # Default 30 seconds (shorter to minimize disruption)
OUTPUT="/mnt/UDISK/serial_operation_$(date +%Y%m%d_%H%M%S).log"

echo "========================================"
echo "Normal Operation Capture"
echo "========================================"
echo ""
echo "IMPORTANT: Start the vacuum cleaning FIRST"
echo "           then run this script!"
echo ""
echo "This captures ${DURATION} seconds of communication"
echo "The vacuum may slow down or pause during capture."
echo ""
echo "Ready? Press Enter to start capture..."
read dummy

AUXCTRL_PID=$(pidof AuxCtrl)
if [ -z "$AUXCTRL_PID" ]; then
    echo "[!] AuxCtrl is not running!"
    exit 1
fi

echo "[+] AuxCtrl PID: $AUXCTRL_PID"
echo "[+] Starting capture..."
echo ""

# Attach strace briefly
strace -f -e read,write -xx -s 1000 -p $AUXCTRL_PID -o "$OUTPUT" 2>/dev/null &
STRACE_PID=$!

echo "[*] Capturing for ${DURATION} seconds..."
echo "[*] (Vacuum operation may be degraded during this time)"
echo ""

sleep $DURATION

# Stop strace
kill $STRACE_PID 2>/dev/null 2>&1
sleep 1

echo ""
echo "========================================"
echo "Capture stopped!"
echo "========================================"
echo "[+] Vacuum should resume normal operation"
ls -lh "$OUTPUT"
echo ""

# Count packets
WRITE_COUNT=$(grep -c "write" "$OUTPUT" 2>/dev/null || echo "0")
READ_COUNT=$(grep -c "read" "$OUTPUT" 2>/dev/null || echo "0")

echo "Captured:"
echo "  Write operations: $WRITE_COUNT"
echo "  Read operations: $READ_COUNT"
echo ""
echo "Download with:"
echo "  scp root@vacuum:$OUTPUT ."
