# Software & Firmware Analysis

This directory contains analysis of the original firmware, system architecture, and tools for protocol reverse engineering.

## Quick Links

### Protocol Documentation (VERIFIED)
- **[GD32 Protocol - VERIFIED](GD32_PROTOCOL_FINAL.md)** ⭐ - Complete verified protocol specification (RECOMMENDED)
- **[Protocol Discovery Changelog](CHANGELOG.md)** - Evolution of understanding through 5 phases
- **[Serial MITM Approach](SERIAL_MITM_APPROACH.md)** - PTY-based protocol capture methodology
- **[Serial Logging Guide](SERIAL_LOGGING.md)** - Tools and techniques for packet capture
- **[Test Results](TEST_RESULTS.md)** - Protocol testing outcomes

### Binary Analysis
- **[AuxCtrl Details](AuxCtrl-Details.md)** - Deep analysis of the AuxCtrl process
- **[Initial Protocol Analysis](../GD32F1/A33-GD32-Protocol.md)** - Binary reverse engineering (contains some outdated info)
- **[Checksum Algorithm - VERIFIED](../GD32F1/CHECKSUM_ALGORITHM.md)** - Complete checksum algorithm (99.8% verified)

### Firmware Implementation
- **[Firmware Projects](Firmware/README.md)** - Rust-based firmware for Allwinner A33
  - [AuxCtrl-Rust](Firmware/auxctrl-rust/README.md) - Open-source GD32 communication library
  - [Lidar Reader](Firmware/lidar-reader/README.md) - Rust library for 3iRobotix Delta-2D Lidar

---

## Gaining Access to the Linux System

The device runs ADB (Android Debug Bridge) tools that allows us to communicate with the device. Though this feature is enabled by default, in production mode the device disconnects within seconds after connecting. 

## Debug Mode

So I had a few seconds window to analyse what was happeneing, and finally figured that the startup script was looking for a file in `/mnt/UDISK/debug_mode` and kicking me out after 5 seconds. And searching about this file, looks like its common practice among Vacuum devices from various vendors. 

As soon as you create this file, you are given more time to debug. The device now boots in debug mode and you get more info on logs. 

As soon as I got access, I enabled SSH on the device and connected to my home Wifi (Restricted Wifi) so its easy to continue the rest of the analysis remotely.Finally I can get rid of the USB cable and the wierd vacuum cleaner lying upside down on your work desk. 

## Logs

- The /usr/sbin/Monitor binary checks for the debug mode file
- Found references in the Monitor binary:
    - CFilePath::touchDebugMode()
    - CFilePath::deleteDebugMode()
    - CFilePath::getLogDebugMode()
- When debug mode is enabled, detailed logs are written to /mnt/UDISK/log/
- Recent logs show detailed system status:
    - Battery levels (103%)
    - Charge status (mode 0 = idle, charge 1)
    - Fault codes (2103 = low battery warning)
    - Heartbeat messages every ~5 seconds
    - Hardware driver status

Now, you have full access to the device.

## PowerOn Mode

Another file discovered in the system is `/mnt/UDISK/PowerOn`. This file is referenced in the Monitor binary and appears to control a power-related mode for the device.

### PowerOn File Details

- **Location**: `/mnt/UDISK/PowerOn`
- **Purpose**: Controls device power mode (exact behavior TBD through testing)
- **Created by**: Monitor binary has a `PowerOn()` function

### Binary References

Found in `/usr/sbin/Monitor`:
```
_Z7PowerOnv                    # PowerOn() function
/mnt/UDISK/PowerOn             # File path reference
touch /mnt/UDISK/PowerOn       # Command to create file
```

## System Architecture

The device runs several key processes managed by Monitor:
- **Monitor** (`/usr/sbin/Monitor`) - Main supervisor process
- **RobotApp** (`/usr/sbin/RobotApp`) - Main robot control application
- **AuxCtrl** (`/usr/sbin/AuxCtrl`) - Auxiliary control process
- **everest-server** (`/usr/sbin/everest-server`) - Server component
- **log-server** (`/usr/sbin/log-server`) - Logging service

All processes are forked by Monitor and run continuously. The Monitor binary checks for both `debug_mode` and `PowerOn` files during operation.