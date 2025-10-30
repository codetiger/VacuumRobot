#!/bin/sh
# Capture complete GPIO initialization sequence
# Run this at boot BEFORE any process starts

LOG="/tmp/gpio_init_capture_$(date +%Y%m%d_%H%M%S).log"

echo "GPIO Initialization Capture" | tee "$LOG"
echo "=============================" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Capture initial state
echo "[INITIAL STATE]" | tee -a "$LOG"
ls -la /sys/class/gpio/ | tee -a "$LOG"
cat /sys/kernel/debug/gpio | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Monitor /sys/class/gpio for new exports
echo "[MONITORING GPIO EXPORTS...]" | tee -a "$LOG"

# Use inotifywait if available, otherwise poll
if command -v inotifywait >/dev/null 2>&1; then
    inotifywait -m -e create /sys/class/gpio 2>&1 | tee -a "$LOG" &
    WATCH_PID=$!
else
    # Polling fallback
    while true; do
        NEW_GPIO=$(ls /sys/class/gpio/ | grep -E '^gpio[0-9]+$')
        if [ ! -z "$NEW_GPIO" ]; then
            echo "[$(date +%H:%M:%S)] New GPIO detected: $NEW_GPIO" | tee -a "$LOG"
            for gpio in $NEW_GPIO; do
                if [ -d "/sys/class/gpio/$gpio" ]; then
                    echo "  Direction: $(cat /sys/class/gpio/$gpio/direction 2>/dev/null)" | tee -a "$LOG"
                    echo "  Value: $(cat /sys/class/gpio/$gpio/value 2>/dev/null)" | tee -a "$LOG"
                fi
            done
        fi
        sleep 0.5
    done &
    WATCH_PID=$!
fi

# Wait for AuxCtrl to start
sleep 10

# Kill monitor
kill $WATCH_PID 2>/dev/null

echo "" | tee -a "$LOG"
echo "[FINAL STATE AFTER 10s]" | tee -a "$LOG"
ls -la /sys/class/gpio/ | tee -a "$LOG"
cat /sys/kernel/debug/gpio | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "Capture saved to: $LOG" | tee -a "$LOG"
