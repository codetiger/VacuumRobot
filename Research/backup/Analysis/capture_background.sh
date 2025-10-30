#!/bin/sh
# Start strace in background to capture ongoing AuxCtrl communication
# Uses -f (follow forks) and runs detached

DURATION=${1:-300}
OUTPUT="/mnt/UDISK/serial_capture_$(date +%Y%m%d_%H%M%S).log"

echo "========================================"
echo "Background Serial Capture"
echo "========================================"

# Get AuxCtrl PID
AUXCTRL_PID=$(pidof AuxCtrl)
if [ -z "$AUXCTRL_PID" ]; then
    echo "[!] AuxCtrl is not running. Starting it..."
    /usr/sbin/AuxCtrl &
    sleep 3
    AUXCTRL_PID=$(pidof AuxCtrl)
fi

echo "[+] AuxCtrl PID: $AUXCTRL_PID"
echo "[+] Duration: ${DURATION}s"
echo "[+] Output: $OUTPUT"
echo ""

# Try strace with -f option and detach
echo "[*] Attempting to attach strace..."
strace -f -e read,write -xx -s 1000 -p $AUXCTRL_PID -o "$OUTPUT" 2>/dev/null &
STRACE_PID=$!

sleep 2

# Check if strace is actually running
if kill -0 $STRACE_PID 2>/dev/null; then
    echo "[+] Strace attached successfully!"
    echo "[+] Strace PID: $STRACE_PID"
    echo ""
    echo "Now start the vacuum cleaning..."
    echo "Recording for ${DURATION} seconds..."
    echo ""

    sleep $DURATION

    echo "[*] Stopping capture..."
    kill $STRACE_PID 2>/dev/null
    sleep 1

    echo ""
    echo "Capture complete!"
    ls -lh "$OUTPUT"
else
    echo "[!] Strace failed to attach (Operation not permitted)"
    echo ""
    echo "This is likely due to kernel security (Yama ptrace_scope)"
    echo ""
    echo "Alternative: The only way to capture is to restart AuxCtrl under strace,"
    echo "but this breaks GD32 communication."
    echo ""
    echo "Workaround: We need to capture BEFORE the issue, during normal operation."
    echo "Let me check if we can enable ptrace..."
    echo ""
    cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo "Yama not available"
fi
