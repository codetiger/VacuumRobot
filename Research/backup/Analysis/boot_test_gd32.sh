#!/bin/sh
# Boot-time GD32 communication test
# This runs BEFORE AuxCtrl to test if fresh GD32 responds

PORT="/dev/ttyS1"
DURATION=20
LOG="/tmp/boot_gd32_test_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================================" > "$LOG"
echo "GD32 Boot-Time Communication Test" >> "$LOG"
echo "================================================================================" >> "$LOG"
echo "This test runs BEFORE AuxCtrl to catch GD32 in fresh state" >> "$LOG"
echo "Time: $(date)" >> "$LOG"
echo "Port: $PORT" >> "$LOG"
echo "Duration: $DURATION seconds" >> "$LOG"
echo "" >> "$LOG"

# Wait a bit for system to stabilize
sleep 2

# Heartbeat packets with verified CRC
HB_06="\xFA\xFB\x03\x06\x00\x06"  # Heartbeat
HB_0D="\xFA\xFB\x03\x0D\x00\x0D"  # Status request

echo "[+] Starting RX capture..." >> "$LOG"

# Start RX capture
dd if="$PORT" bs=1 count=10000 2>/dev/null | hexdump -C > "${LOG}.rx" &
RX_PID=$!

sleep 1

echo "[+] RX capture started (PID: $RX_PID)" >> "$LOG"
echo "[+] Sending test sequence..." >> "$LOG"
echo "" >> "$LOG"

# Send startup sequence - 10x STATUS_REQUEST
echo "[*] Phase 1: Sending 10x STATUS_REQUEST (0x0D)..." >> "$LOG"
for i in 1 2 3 4 5 6 7 8 9 10; do
    echo -ne "$HB_0D" > "$PORT"
    echo "[$(date +%H:%M:%S)] TX: FA FB 03 0D 00 0D (STATUS_REQUEST)" >> "$LOG"
    sleep 1
done

# Send heartbeats
echo "" >> "$LOG"
echo "[*] Phase 2: Sending heartbeats (0x06)..." >> "$LOG"
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

    echo "[$(date +%H:%M:%S)] Sent: $COUNT packets" >> "$LOG"
    sleep 1
done

echo "" >> "$LOG"
echo "[+] Stopping RX capture..." >> "$LOG"
kill $RX_PID 2>/dev/null
wait $RX_PID 2>/dev/null

echo "" >> "$LOG"
echo "================================================================================" >> "$LOG"
echo "TEST COMPLETE" >> "$LOG"
echo "================================================================================" >> "$LOG"
echo "Total packets sent: $COUNT" >> "$LOG"

# Check results
RX_SIZE=$(wc -c < "${LOG}.rx" 2>/dev/null || echo 0)

echo "RX data received: $RX_SIZE bytes" >> "$LOG"
echo "" >> "$LOG"

if [ "$RX_SIZE" -gt 100 ]; then
    echo "✅ SUCCESS: GD32 responded with $RX_SIZE bytes!" >> "$LOG"
    echo "" >> "$LOG"
    echo "First 50 lines of response:" >> "$LOG"
    head -50 "${LOG}.rx" >> "$LOG"
else
    echo "❌ FAILURE: No response from GD32 ($RX_SIZE bytes)" >> "$LOG"
    echo "" >> "$LOG"
    echo "Even at boot, GD32 did not respond." >> "$LOG"
    echo "This suggests:" >> "$LOG"
    echo "  1. GD32 requires hardware initialization (GPIO/reset)" >> "$LOG"
    echo "  2. Wrong baud rate (unlikely - confirmed 115200)" >> "$LOG"
    echo "  3. GD32 only accepts commands from specific source" >> "$LOG"
fi

echo "" >> "$LOG"
echo "Logs saved to:" >> "$LOG"
echo "  TX: $LOG" >> "$LOG"
echo "  RX: ${LOG}.rx" >> "$LOG"
echo "================================================================================" >> "$LOG"

# Also output to console
cat "$LOG"
