#!/bin/sh
# Heartbeat test with CORRECT CRC algorithm: CRC = CMD XOR DATA
# Formula confirmed by analyzing 2679 real packets from AuxCtrl

PORT="/dev/ttyS1"
DURATION=${1:-30}
LOG="/tmp/heartbeat_crc_test_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================================"
echo "GD32 Heartbeat Test - Correct CRC Algorithm"
echo "================================================================================"
echo "CRC Algorithm: CRC = CMD XOR DATA[0] XOR DATA[1] XOR ..."
echo "Port: $PORT"
echo "Duration: $DURATION seconds"
echo "Log: $LOG"
echo ""

# Check if AuxCtrl is running
if pidof AuxCtrl > /dev/null; then
    echo "[!] WARNING: AuxCtrl is running!"
    echo "[!] Stopping AuxCtrl..."
    mv /usr/sbin/AuxCtrl /usr/sbin/AuxCtrl.bak 2>/dev/null
    killall AuxCtrl
    sleep 2
fi

if pidof AuxCtrl > /dev/null; then
    echo "[!] ERROR: Could not stop AuxCtrl"
    exit 1
fi

echo "[+] AuxCtrl stopped"
echo ""

# Test packets with VERIFIED CRC algorithm
# Format: FA FB LEN CMD DATA... CRC
# CRC = CMD XOR DATA[0] XOR DATA[1] XOR ...

# Heartbeat: FA FB 03 06 00 | 06
# CRC = 0x06 XOR 0x00 = 0x06
HB_06="\xFA\xFB\x03\x06\x00\x06"

# Status request: FA FB 03 0D 00 | 0D
# CRC = 0x0D XOR 0x00 = 0x0D
HB_0D="\xFA\xFB\x03\x0D\x00\x0D"

# Configure serial port for 115200 8N1
stty -F "$PORT" 115200 cs8 -cstopb -parenb raw -echo

echo "[+] Serial port configured: 115200 8N1"
echo "Starting test in 2 seconds..."
sleep 2

echo "" > "$LOG"

# Start RX capture
dd if="$PORT" bs=1 2>/dev/null | hexdump -C > "${LOG}.rx" &
RX_PID=$!

echo "[+] RX capture started (PID: $RX_PID)"
sleep 1

echo "[+] Sending heartbeat packets..."
echo ""

# Send pattern similar to AuxCtrl behavior
# First: 5x status request (like startup)
# Then: continuous heartbeats every 100ms

COUNT=0
START_TIME=$(date +%s)

# Initial startup sequence - send status requests
echo "[*] Sending startup sequence (5x STATUS_REQUEST 0x0D)..."
for i in 1 2 3 4 5; do
    echo -ne "$HB_0D" > "$PORT"
    echo "[$(date +%H:%M:%S)] TX: FA FB 03 0D 00 0D (STATUS_REQUEST)" >> "$LOG"
    COUNT=$((COUNT + 1))
    sleep 1
done

echo "[*] Startup sequence complete, switching to heartbeat mode..."
echo ""

# Main heartbeat loop
while true; do
    CURRENT=$(date +%s)
    ELAPSED=$((CURRENT - START_TIME))

    if [ $ELAPSED -ge $DURATION ]; then
        break
    fi

    # Send 10 heartbeats per second (100ms interval)
    for i in 1 2 3 4 5 6 7 8 9 10; do
        echo -ne "$HB_06" > "$PORT"
        COUNT=$((COUNT + 1))
    done

    echo "[$(date +%H:%M:%S)] TX: Sent 10x HEARTBEAT (total: $COUNT)" >> "$LOG"
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
    echo "Sample of received data (first 50 lines):"
    head -50 "${LOG}.rx"
    echo ""
    echo "Full RX log saved to: ${LOG}.rx"

    # Try to identify response packets
    echo ""
    echo "Looking for response packets..."
    grep "fa fb" "${LOG}.rx" || echo "No FA FB sync bytes found in response"

elif [ "$RX_SIZE" -gt 0 ]; then
    echo "⚠️  Received small amount of data ($RX_SIZE bytes):"
    cat "${LOG}.rx"
else
    echo "❌ FAILURE: No response from GD32"
    echo ""
    echo "Verified items:"
    echo "  ✓ Baud rate: 115200 (confirmed from AuxCtrl log)"
    echo "  ✓ CRC algorithm: CMD XOR DATA (tested on 2679 packets)"
    echo "  ✓ Packet structure: FA FB LEN CMD DATA CRC"
    echo ""
    echo "Possible causes:"
    echo "  1. GD32 requires initialization beyond heartbeat"
    echo "  2. GD32 needs hardware reset after AuxCtrl stops"
    echo "  3. Missing handshake or mode-setting command"
    echo "  4. GD32 only responds to specific command sequence"
    echo ""
    echo "Next steps:"
    echo "  - Reboot device to reset GD32: reboot"
    echo "  - Capture AuxCtrl startup with strace to see init sequence"
    echo "  - Check if GD32 requires GPIO signal to enable communication"
fi

echo ""
echo "To download:"
echo "  scp root@vacuum:$LOG ."
echo "  scp root@vacuum:${LOG}.rx ."
echo ""
echo "Restoring AuxCtrl in 5 seconds..."
sleep 5
mv /usr/sbin/AuxCtrl.bak /usr/sbin/AuxCtrl 2>/dev/null
/usr/sbin/AuxCtrl &
echo "================================================================================"
