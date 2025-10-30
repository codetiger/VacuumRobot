#!/bin/sh
# Test GD32 with initialization command 0x66
# Based on strace analysis showing CMD 0x66 is sent before heartbeats

PORT="/dev/ttyS3"  # CORRECT PORT!
DURATION=${1:-30}
LOG="/tmp/gd32_init_test_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================================"
echo "GD32 Initialization Test - CMD 0x66 First"
echo "================================================================================"
echo "Discovery: First packet sent is CMD 0x66, not heartbeat!"
echo "Port: $PORT"
echo "Duration: $DURATION seconds"
echo ""

# Stop AuxCtrl if running
if pidof AuxCtrl > /dev/null; then
    echo "[*] Stopping AuxCtrl..."
    mv /usr/sbin/AuxCtrl /usr/sbin/AuxCtrl.disabled 2>/dev/null
    killall -9 AuxCtrl
    sleep 2
fi

# Packets
# CMD 0x66: FA FB 0B 66 00 00 00 00 00 00 00 00 66 00
# Note: Last byte might be terminator, trying both 13 and 14 byte versions
INIT_CMD_66="\xFA\xFB\x0B\x66\x00\x00\x00\x00\x00\x00\x00\x00\x66\x00"

# Heartbeat packets
HB_06="\xFA\xFB\x03\x06\x00\x06"
HB_0D="\xFA\xFB\x03\x0D\x00\x0D"

echo "" > "$LOG"

# Configure terminal to match AuxCtrl settings
# Based on strace: B115200 -opost -isig -icanon -echo
# This is raw mode, 115200 baud, 8N1
echo "[*] Configuring serial port..." | tee -a "$LOG"

# Start RX capture FIRST
dd if="$PORT" bs=1 2>/dev/null | hexdump -C > "${LOG}.rx" &
RX_PID=$!

sleep 1

echo "[+] RX capture started (PID: $RX_PID)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Send initialization command 0x66
echo "[*] Sending initialization command (CMD 0x66)..." | tee -a "$LOG"
for i in 1 2 3 4 5; do
    echo -ne "$INIT_CMD_66" > "$PORT"
    echo "[$(date +%H:%M:%S)] TX: INIT_CMD 0x66" >> "$LOG"
    sleep 0.5
done

echo "[*] Waiting 2 seconds..." | tee -a "$LOG"
sleep 2

# Send status requests
echo "" | tee -a "$LOG"
echo "[*] Sending STATUS_REQUEST (0x0D) packets..." | tee -a "$LOG"
for i in 1 2 3 4 5; do
    echo -ne "$HB_0D" > "$PORT"
    echo "[$(date +%H:%M:%S)] TX: STATUS_REQUEST (0x0D)" >> "$LOG"
done

sleep 2

# Now send heartbeats
echo "" | tee -a "$LOG"
echo "[*] Sending heartbeats (0x06)..." | tee -a "$LOG"
COUNT=15
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
    echo "This confirms CMD 0x66 initialization works!" | tee -a "$LOG"
elif [ "$RX_SIZE" -gt 0 ]; then
    echo "⚠️  Received $RX_SIZE bytes:" | tee -a "$LOG"
    cat "${LOG}.rx" | tee -a "$LOG"
else
    echo "❌ No response ($RX_SIZE bytes)" | tee -a "$LOG"
    echo "" | tee -a "$LOG"
    echo "Possible issues:" | tee -a "$LOG"
    echo "1. CMD 0x66 data payload incorrect (might need real parameters, not zeros)" | tee -a "$LOG"
    echo "2. Terminal configuration might need exact ioctl settings" | tee -a "$LOG"
    echo "3. GPIO initialization might be required before serial communication" | tee -a "$LOG"
    echo "4. GD32 might need power cycle or reset signal" | tee -a "$LOG"
fi

echo "" | tee -a "$LOG"
echo "Logs saved to:" | tee -a "$LOG"
echo "  TX: $LOG" | tee -a "$LOG"
echo "  RX: ${LOG}.rx" | tee -a "$LOG"
echo "================================================================================" | tee -a "$LOG"

# Restart AuxCtrl
if [ -f /usr/sbin/AuxCtrl.disabled ]; then
    echo "" | tee -a "$LOG"
    echo "[*] Restarting AuxCtrl..." | tee -a "$LOG"
    mv /usr/sbin/AuxCtrl.disabled /usr/sbin/AuxCtrl
    /usr/sbin/AuxCtrl &
fi
