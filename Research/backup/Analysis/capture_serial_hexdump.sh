#!/bin/sh
# Alternative capture method using hexdump/cat to monitor serial port
# This won't capture what AuxCtrl sends, only what it receives

DURATION=${1:-300}
OUTPUT="/mnt/UDISK/serial_rx_$(date +%Y%m%d_%H%M%S).log"

echo "Starting RX-only capture for ${DURATION} seconds..."
echo "Output: $OUTPUT"
echo "Note: This only captures data received from GD32, not what AuxCtrl sends"
echo ""

# Try to read from ttyS1 (this may not work if AuxCtrl has exclusive access)
( cat /dev/ttyS1 | hexdump -C > "$OUTPUT" ) &
CAT_PID=$!

sleep $DURATION

kill $CAT_PID 2>/dev/null
wait $CAT_PID 2>/dev/null

echo "Capture complete: $OUTPUT"
ls -lh "$OUTPUT"
