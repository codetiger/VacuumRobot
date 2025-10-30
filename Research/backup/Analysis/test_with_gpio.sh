#!/bin/sh
# Test GD32 communication with GPIO 233 toggle
# Based on discovery that gpio-233 is controlled by AuxCtrl

PORT="/dev/ttyS1"
DURATION=20
LOG="/tmp/gpio_test_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================================"
echo "GD32 Communication Test with GPIO Control"
echo "================================================================================"
echo "Testing GPIO 233 (currently used by AuxCtrl)"
echo "Port: $PORT"
echo "Duration: $DURATION seconds"
echo "Log: $LOG"
echo ""

# Heartbeat packets with verified CRC
HB_06="\xFA\xFB\x03\x06\x00\x06"
HB_0D="\xFA\xFB\x03\x0D\x00\x0D"

echo "" > "$LOG"

# Start RX capture
dd if="$PORT" bs=1 count=5000 2>/dev/null | hexdump -C > "${LOG}.rx" &
RX_PID=$!

sleep 1

echo "[+] RX capture started (PID: $RX_PID)" | tee -a "$LOG"
echo ""

# GPIO 233 is already exported and set to output high
# Let's try toggling it before sending commands

echo "[*] Current GPIO 233 state:" | tee -a "$LOG"
echo "  Direction: $(cat /sys/class/gpio/gpio233/direction)" | tee -a "$LOG"
echo "  Value: $(cat /sys/class/gpio/gpio233/value)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Test 1: Try LOW then HIGH (reset pulse)
echo "[*] Test 1: Reset pulse (LOW for 100ms, then HIGH)..." | tee -a "$LOG"
echo 0 > /sys/class/gpio/gpio233/value
sleep 0.1
echo 1 > /sys/class/gpio/gpio233/value
sleep 0.5

# Send initial status requests
for i in 1 2 3 4 5; do
    echo -ne "$HB_0D" > "$PORT"
    echo "[$(date +%H:%M:%S)] TX: STATUS_REQUEST (0x0D)" >> "$LOG"
done

sleep 2

# Test 2: Keep sending heartbeats
echo "" | tee -a "$LOG"
echo "[*] Test 2: Sending heartbeats while GPIO is HIGH..." | tee -a "$LOG"
COUNT=5
START=$(date +%s)

while true; do
    CURRENT=$(date +%s)
    ELAPSED=$((CURRENT - START))

    if [ $ELAPSED -ge $DURATION ]; then
        break
    fi

    # Send 10 heartbeats
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
    echo "✅ SUCCESS: GD32 responded!" | tee -a "$LOG"
    echo "" | tee -a "$LOG"
    head -30 "${LOG}.rx" | tee -a "$LOG"
else
    echo "❌ FAILURE: No response ($RX_SIZE bytes)" | tee -a "$LOG"
    echo "" | tee -a "$LOG"
    echo "GPIO 233 toggle alone is not sufficient." | tee -a "$LOG"
    echo "Need to find additional GPIO pins or initialization steps." | tee -a "$LOG"
fi

echo "" | tee -a "$LOG"
echo "Logs saved to:" | tee -a "$LOG"
echo "  TX: $LOG" | tee -a "$LOG"
echo "  RX: ${LOG}.rx" | tee -a "$LOG"
echo "================================================================================" | tee -a "$LOG"
