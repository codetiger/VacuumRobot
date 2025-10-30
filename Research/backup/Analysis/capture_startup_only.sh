#!/bin/sh
# Capture ONLY the first 10 seconds of startup, then detach strace
# This gets us initialization sequences without disrupting normal operation

OUTPUT="/mnt/UDISK/serial_startup_$(date +%Y%m%d_%H%M%S).log"

echo "========================================"
echo "Startup Sequence Capture"
echo "========================================"
echo ""
echo "This will:"
echo "1. Stop AuxCtrl"
echo "2. Start AuxCtrl under strace"
echo "3. Capture for 10 seconds"
echo "4. Detach strace"
echo "5. Let AuxCtrl run normally"
echo ""
echo "Press Ctrl+C within 3 seconds to cancel..."
sleep 3

# Stop AuxCtrl
echo "[1] Stopping AuxCtrl..."
killall AuxCtrl 2>/dev/null
sleep 2

# Start under strace
echo "[2] Starting AuxCtrl with strace..."
strace -e read,write -xx -s 1000 -o "$OUTPUT" /usr/sbin/AuxCtrl &
STRACE_PID=$!
AUXCTRL_PID=$(pidof AuxCtrl)

echo "[+] Strace PID: $STRACE_PID"
echo "[+] AuxCtrl PID: $AUXCTRL_PID"
echo ""
echo "[3] Capturing startup for 10 seconds..."

sleep 10

# Kill strace but let AuxCtrl continue
echo "[4] Detaching strace (AuxCtrl will continue)..."
kill $STRACE_PID 2>/dev/null
sleep 1

# AuxCtrl should still be running
if pidof AuxCtrl > /dev/null; then
    echo "[+] AuxCtrl is still running normally"
    echo "[+] Vacuum should work now"
else
    echo "[!] AuxCtrl died, restarting..."
    /usr/sbin/AuxCtrl &
fi

echo ""
echo "========================================"
echo "Startup capture complete!"
echo "========================================"
ls -lh "$OUTPUT"
echo ""
echo "Now you can:"
echo "1. Start vacuum cleaning (it should work normally)"
echo "2. Run capture_normal_operation.sh to get 5min of working data"
echo ""
echo "Download startup log:"
echo "  scp root@vacuum:$OUTPUT ."
