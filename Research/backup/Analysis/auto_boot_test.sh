#!/bin/sh
# Auto-run boot test and restore AuxCtrl
# Place this in /etc/rc.local or run via cron @reboot

# Wait for system to fully boot
sleep 5

# Run the GD32 test
/tmp/boot_test_gd32.sh

# Wait for test to complete
sleep 35

# Restore AuxCtrl
if [ -f /usr/sbin/AuxCtrl.disabled ]; then
    mv /usr/sbin/AuxCtrl.disabled /usr/sbin/AuxCtrl
fi

# Start AuxCtrl
/usr/sbin/AuxCtrl &

# Remove this script so it only runs once
rm -f /etc/rc.local
