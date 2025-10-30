#!/bin/sh
# Passive capture by reading serial port settings and monitoring with cat
# This runs ALONGSIDE AuxCtrl without disrupting it

DURATION=${1:-300}
OUTPUT="/mnt/UDISK/serial_passive_$(date +%Y%m%d_%H%M%S).log"

echo "========================================"
echo "Passive Serial Monitor"
echo "========================================"
echo "Duration: ${DURATION} seconds"
echo "Output: $OUTPUT"
echo ""

# Get current PID of AuxCtrl
AUXCTRL_PID=$(pidof AuxCtrl)
if [ -z "$AUXCTRL_PID" ]; then
    echo "[!] AuxCtrl is not running!"
    exit 1
fi

echo "[+] AuxCtrl PID: $AUXCTRL_PID"

# Find which serial port AuxCtrl is using
echo "[*] Checking AuxCtrl serial port usage..."
ls -l /proc/$AUXCTRL_PID/fd/ | grep ttyS

# Get serial port settings from the open file descriptor
echo ""
echo "[*] Current serial port settings:"
stty -F /dev/ttyS1 -a 2>/dev/null || echo "Cannot read settings"

echo ""
echo "========================================"
echo "Alternative: Use LD_PRELOAD to intercept calls"
echo "========================================"
echo ""
echo "Since we cannot passively monitor the serial port"
echo "while AuxCtrl has it open, we need a different approach."
echo ""
echo "Options:"
echo "1. Create LD_PRELOAD library to intercept read/write"
echo "2. Use kernel tracing (ftrace) if available"
echo "3. Modify approach to work with strace restart"
echo ""
echo "The issue: When AuxCtrl opens /dev/ttyS1 exclusively,"
echo "no other process can read from it simultaneously."
echo ""
