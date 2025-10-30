#!/bin/sh
# GD32 Heartbeat Monitor v2
# Better handling of serial communication

DURATION=${1:-60}
PORT="/dev/ttyS1"
LOG="/tmp/heartbeat_log_$(date +%Y%m%d_%H%M%S).log"
TX_LOG="/tmp/heartbeat_tx_$(date +%Y%m%d_%H%M%S).log"
RX_LOG="/tmp/heartbeat_rx_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================================"
echo "GD32 Heartbeat Monitor v2"
echo "================================================================================"
echo "Port: $PORT"
echo "Duration: $DURATION seconds"
echo "TX Log: $TX_LOG"
echo "RX Log: $RX_LOG"
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Heartbeat packet: FA FB 03 06 00 06
HEARTBEAT="\xFA\xFB\x03\x06\x00\x06"

echo ""
echo "[+] Opening serial port for reading..."

# Start RX capture in background
(
    dd if="$PORT" bs=1 2>/dev/null | hexdump -C > "$RX_LOG" &
    RX_PID=$!

    # Wait for duration or until parent dies
    COUNT=0
    while [ $COUNT -lt $DURATION ]; do
        sleep 1
        COUNT=$((COUNT + 1))

        # Check if parent still alive
        if ! kill -0 $$ 2>/dev/null; then
            break
        fi
    done

    kill $RX_PID 2>/dev/null
) &
RX_MONITOR_PID=$!

sleep 1

echo "[+] Starting TX heartbeat sender..."
echo "" > "$TX_LOG"

# Send heartbeats
TX_COUNT=0
START_TIME=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    if [ $ELAPSED -ge $DURATION ]; then
        break
    fi

    # Send heartbeat burst (10 per second)
    for i in 1 2 3 4 5 6 7 8 9 10; do
        echo -ne "$HEARTBEAT" > "$PORT"
        TX_COUNT=$((TX_COUNT + 1))
    done

    # Log every 10 heartbeats
    echo "[$(date +%H:%M:%S)] TX count: $TX_COUNT" >> "$TX_LOG"

    sleep 1
done

echo ""
echo "[+] Stopping RX monitor..."
kill $RX_MONITOR_PID 2>/dev/null
wait $RX_MONITOR_PID 2>/dev/null

echo ""
echo "================================================================================"
echo "SESSION COMPLETE"
echo "================================================================================"
echo "TX Heartbeats sent: $TX_COUNT"
echo "TX Log: $TX_LOG"
echo "RX Log: $RX_LOG"
echo ""

# Check if we received any data
RX_SIZE=$(wc -c < "$RX_LOG" 2>/dev/null || echo 0)
echo "RX data captured: $RX_SIZE bytes"

if [ "$RX_SIZE" -gt 0 ]; then
    echo ""
    echo "Sample of received data (first 50 lines):"
    head -50 "$RX_LOG"
else
    echo ""
    echo "[!] WARNING: No RX data captured!"
    echo "[!] Possible issues:"
    echo "    - GD32 not responding"
    echo "    - Port already in use"
    echo "    - GD32 needs reset"
fi

echo ""
echo "To download:"
echo "  scp root@vacuum:$RX_LOG ."
echo "  scp root@vacuum:$TX_LOG ."
echo "================================================================================"
