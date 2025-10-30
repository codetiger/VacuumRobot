#!/bin/sh
# Test both heartbeat commands (0x06 and 0x0D)
# Run immediately after stopping AuxCtrl

PORT="/dev/ttyS1"
DURATION=${1:-30}
LOG="/tmp/heartbeat_test_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================================"
echo "GD32 Heartbeat Test - Both Commands"
echo "================================================================================"
echo "Testing: 0x06 (HEARTBEAT) and 0x0D (STATUS_REQUEST)"
echo "Port: $PORT"
echo "Duration: $DURATION seconds"
echo "Log: $LOG"
echo ""

# Check if AuxCtrl is running
if pidof AuxCtrl > /dev/null; then
    echo "[!] WARNING: AuxCtrl is running!"
    echo "[!] Stopping AuxCtrl..."
    killall AuxCtrl
    sleep 2
fi

if pidof AuxCtrl > /dev/null; then
    echo "[!] ERROR: Could not stop AuxCtrl"
    exit 1
fi

echo "[+] AuxCtrl stopped"
echo ""
echo "Starting test in 2 seconds..."
sleep 2

# Test packets
HB_06="\xFA\xFB\x03\x06\x00\x06"  # Heartbeat 0x06
HB_0D="\xFA\xFB\x03\x0D\x00\x0D"  # Status request 0x0D (used at startup)

echo "" > "$LOG"

# Start RX capture
dd if="$PORT" bs=1 2>/dev/null | hexdump -C > "${LOG}.rx" &
RX_PID=$!

echo "[+] RX capture started (PID: $RX_PID)"
sleep 1

echo "[+] Sending test packets..."
echo ""

# Send pattern: 5x 0x0D, 5x 0x06, repeat
COUNT=0
START_TIME=$(date +%s)

while true; do
    CURRENT=$(date +%s)
    ELAPSED=$((CURRENT - START_TIME))

    if [ $ELAPSED -ge $DURATION ]; then
        break
    fi

    # Send 5x status request (0x0D) - like startup
    for i in 1 2 3 4 5; do
        echo -ne "$HB_0D" > "$PORT"
        echo "[$(date +%H:%M:%S.%N | cut -c1-12)] TX: fa fb 03 0d 00 0d (0x0D)" >> "$LOG"
        COUNT=$((COUNT + 1))
    done

    # Send 5x heartbeat (0x06) - like normal operation
    for i in 1 2 3 4 5; do
        echo -ne "$HB_06" > "$PORT"
        echo "[$(date +%H:%M:%S.%N | cut -c1-12)] TX: fa fb 03 06 00 06 (0x06)" >> "$LOG"
        COUNT=$((COUNT + 1))
    done

    # Show progress
    echo -ne "\r[$(date +%H:%M:%S)] Sent: $COUNT packets"

    sleep 1
done

echo ""
echo ""
echo "[+] Stopping RX capture..."
kill $RX_PID 2>/dev/null
wait $RX_PID 2>/dev/null

echo ""
echo "================================================================================"
echo "TEST COMPLETE"
echo "================================================================================"
echo "Total packets sent: $COUNT"
echo ""

# Check results
RX_SIZE=$(wc -c < "${LOG}.rx" 2>/dev/null || echo 0)
TX_SIZE=$(wc -c < "$LOG" 2>/dev/null || echo 0)

echo "TX log: $LOG ($TX_SIZE bytes)"
echo "RX log: ${LOG}.rx ($RX_SIZE bytes)"
echo ""

if [ "$RX_SIZE" -gt 100 ]; then
    echo "✅ SUCCESS: Received $RX_SIZE bytes from GD32!"
    echo ""
    echo "Sample of received data (first 30 lines):"
    head -30 "${LOG}.rx"
    echo ""
    echo "Full RX log saved to: ${LOG}.rx"
elif [ "$RX_SIZE" -gt 0 ]; then
    echo "⚠️  Received small amount of data ($RX_SIZE bytes):"
    cat "${LOG}.rx"
else
    echo "❌ FAILURE: No response from GD32"
    echo ""
    echo "Possible causes:"
    echo "  1. GD32 in error state - needs hardware reset"
    echo "  2. Wrong CRC algorithm in our packets"
    echo "  3. Port configuration mismatch (baud rate?)"
    echo "  4. GD32 not powered"
    echo ""
    echo "Try:"
    echo "  - Reboot device: reboot"
    echo "  - Check GD32 power/LEDs"
    echo "  - Try different baud rates"
fi

echo ""
echo "To download:"
echo "  scp root@vacuum:$LOG ."
echo "  scp root@vacuum:${LOG}.rx ."
echo ""
echo "Restarting AuxCtrl in 5 seconds..."
sleep 5
/usr/sbin/AuxCtrl &
echo "================================================================================"
