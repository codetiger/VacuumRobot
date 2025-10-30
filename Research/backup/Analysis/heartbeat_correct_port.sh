#!/bin/sh
# Heartbeat test on CORRECT port - /dev/ttyS3!
# Discovery: AuxCtrl uses /dev/ttyS3 for GD32, NOT /dev/ttyS1!

PORT="/dev/ttyS3"  # CORRECT PORT!
DURATION=${1:-20}
LOG="/tmp/heartbeat_ttyS3_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================================"
echo "GD32 Heartbeat Test - CORRECT PORT (/dev/ttyS3)"
echo "================================================================================"
echo "DISCOVERY: GD32 is on /dev/ttyS3, not /dev/ttyS1!"
echo "Port: $PORT"
echo "Duration: $DURATION seconds"
echo ""

# Heartbeat packets with verified CRC
HB_06="\xFA\xFB\x03\x06\x00\x06"
HB_0D="\xFA\xFB\x03\x0D\x00\x0D"

echo "" > "$LOG"

# Start RX capture
dd if="$PORT" bs=1 count=10000 2>/dev/null | hexdump -C > "${LOG}.rx" &
RX_PID=$!

sleep 1

echo "[+] RX capture started (PID: $RX_PID)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Send startup sequence
echo "[*] Sending startup sequence (10x STATUS_REQUEST 0x0D)..." | tee -a "$LOG"
for i in 1 2 3 4 5 6 7 8 9 10; do
    echo -ne "$HB_0D" > "$PORT"
    echo "[$(date +%H:%M:%S)] TX: STATUS_REQUEST (0x0D)" >> "$LOG"
done

sleep 2

# Send heartbeats
echo "" | tee -a "$LOG"
echo "[*] Sending heartbeats (0x06)..." | tee -a "$LOG"
COUNT=10
START=$(date +%s)

while true; do
    CURRENT=$(date +%s)
    ELAPSED=$((CURRENT - START))

    if [ $ELAPSED -ge $DURATION ]; then
        break
    fi

    # Send 10 heartbeats per second
    for i in 1 2 3 4 5 6 7 8 9 10; do
        echo -ne "$HB_06" > "$PORT"
        COUNT=$((COUNT + 1))
    done

    echo -ne "\r[$(date +%H:%M:%S)] Sent: $COUNT packets"
    echo "[$(date +%H:%M:%S)] Sent: $COUNT packets" >> "$LOG"

    sleep 1
done

echo ""
echo ""
echo "[+] Stopping RX capture..." | tee -a "$LOG"
kill $RX_PID 2>/dev/null
wait $RX_PID 2>/dev/null

echo "" | tee -a "$LOG"
echo "================================================================================" | tee -a "$LOG"
echo "TEST COMPLETE" | tee -a "$LOG"
echo "================================================================================" | tee -a "$LOG"
echo "Total packets sent: $COUNT" | tee -a "$LOG"

# Check results
RX_SIZE=$(wc -c < "${LOG}.rx" 2>/dev/null || echo 0)

echo "RX data received: $RX_SIZE bytes" | tee -a "$LOG"
echo "" | tee -a "$LOG"

if [ "$RX_SIZE" -gt 100 ]; then
    echo "✅ ✅ ✅ SUCCESS! GD32 RESPONDED! ✅ ✅ ✅" | tee -a "$LOG"
    echo "" | tee -a "$LOG"
    echo "First 50 lines of response:" | tee -a "$LOG"
    head -50 "${LOG}.rx" | tee -a "$LOG"
    echo "" | tee -a "$LOG"
    echo "This confirms /dev/ttyS3 is the correct port for GD32!" | tee -a "$LOG"
elif [ "$RX_SIZE" -gt 0 ]; then
    echo "⚠️  Received $RX_SIZE bytes:" | tee -a "$LOG"
    cat "${LOG}.rx" | tee -a "$LOG"
else
    echo "❌ No response ($RX_SIZE bytes)" | tee -a "$LOG"
    echo "" | tee -a "$LOG"
    echo "Even with correct port, no response. May still need GPIO init." | tee -a "$LOG"
fi

echo "" | tee -a "$LOG"
echo "Logs saved to:" | tee -a "$LOG"
echo "  TX: $LOG" | tee -a "$LOG"
echo "  RX: ${LOG}.rx" | tee -a "$LOG"
echo "================================================================================" | tee -a "$LOG"
