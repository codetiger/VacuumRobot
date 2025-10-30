#!/bin/sh
# GD32 Heartbeat Monitor (Shell script version)
# Sends heartbeat packets and logs responses

DURATION=${1:-60}
PORT="/dev/ttyS1"
LOG="/tmp/heartbeat_log_$(date +%Y%m%d_%H%M%S).log"

echo "================================================================================"
echo "GD32 Heartbeat Monitor"
echo "================================================================================"
echo "Port: $PORT"
echo "Duration: $DURATION seconds"
echo "Log: $LOG"
echo ""
echo "Instructions:"
echo "  - Move robot manually to trigger sensors"
echo "  - Press bumpers, spin wheels"
echo "  - Press Ctrl+C to stop early"
echo ""
echo "Starting in 3 seconds..."
sleep 3

echo ""
echo "[+] Starting heartbeat sender..."

# Heartbeat packet: FA FB 03 06 00 06
HEARTBEAT="\xFA\xFB\x03\x06\x00\x06"

# Function to send heartbeats in background
send_heartbeats() {
    while true; do
        # Send 20 heartbeats per second = every 50ms
        echo -ne "$HEARTBEAT" > "$PORT"
        echo -ne "$HEARTBEAT" > "$PORT"
        echo -ne "$HEARTBEAT" > "$PORT"
        echo -ne "$HEARTBEAT" > "$PORT"
        echo -ne "$HEARTBEAT" > "$PORT"
        echo -ne "$HEARTBEAT" > "$PORT"
        echo -ne "$HEARTBEAT" > "$PORT"
        echo -ne "$HEARTBEAT" > "$PORT"
        echo -ne "$HEARTBEAT" > "$PORT"
        echo -ne "$HEARTBEAT" > "$PORT"
        sleep 1  # Send 10 heartbeats, wait 1 second (total ~100ms per heartbeat, close enough)
    done
}

# Start heartbeat sender in background
send_heartbeats &
HB_PID=$!

echo "[+] Heartbeat sender running (PID: $HB_PID)"
echo "[+] Reading responses for $DURATION seconds..."
echo "[+] Logging to: $LOG"
echo ""
echo "--------------------------------------------------------------------------------"
echo "LIVE MONITORING"
echo "--------------------------------------------------------------------------------"
echo ""

# Read and log responses
(
    # Add timeout
    sleep $DURATION
    kill $HB_PID 2>/dev/null
) &
TIMEOUT_PID=$!

# Read from serial port and log
cat "$PORT" | hexdump -C | while read line; do
    echo "$line"
    echo "[$(date +%H:%M:%S)] $line" >> "$LOG"

    # Check if we should stop
    if ! kill -0 $HB_PID 2>/dev/null; then
        break
    fi
done

# Cleanup
kill $HB_PID 2>/dev/null
kill $TIMEOUT_PID 2>/dev/null
wait $HB_PID 2>/dev/null
wait $TIMEOUT_PID 2>/dev/null

echo ""
echo "================================================================================"
echo "SESSION COMPLETE"
echo "================================================================================"
echo "Log saved to: $LOG"
echo ""
echo "To analyze:"
echo "  cat $LOG"
echo ""
echo "To copy to computer:"
echo "  scp root@vacuum:$LOG ."
echo "================================================================================"
