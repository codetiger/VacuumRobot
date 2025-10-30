# VacuumRobot

Reverse engineering project for the 3irobotix CRL-200S robotic vacuum cleaner. This repository documents the hardware architecture, communication protocols, and component specifications with the goal of understanding and potentially rebuilding the robot's functionality from scratch.

## Project Goals

- **Hardware Reverse Engineering**: Document PCB layout, identify components, and map connector pinouts
- **Protocol Analysis**: Decode communication protocols for sensors and peripherals
- **Firmware Development**: Build custom firmware to control the hardware (future goal)
- **Software Reimplementation**: Create navigation and control algorithms (future goal)

## Current Progress

### ✅ Completed
- Lidar sensor protocol decoded and documented
- Real-time Lidar visualization tool (Python)
- Main motherboard component identification
- Connector pinout mapping and documentation
- A33-GD32F103 communication protocol reverse engineered
- Original firmware binary analysis (AuxCtrl process)
- Device access methods (SSH, debug mode) documented

### 🔄 In Progress
- Detailed circuit analysis and tracing
- Complete command ID mapping for MCU protocol

### 📋 Planned
- Firmware development for GD32F1 MCU
- Motor control implementation
- Navigation algorithm development
- Integration with custom control software

## Hardware Overview

The 3irobotix CRL-200S uses a dual-processor architecture:

- **Main CPU**: Allwinner A33 (ARM Cortex-A7 Quad-Core) - likely handles high-level logic, WiFi, and user interface
- **Motor Control MCU**: GigaDevice GD32F103VCT6 (ARM Cortex-M3) - handles real-time motor control and sensor interfacing
- **Lidar**: 3irobotix Delta-2D with UART interface
- **Memory**: 4Gbit DDR3L RAM, 2Gbit NAND Flash
- **Power**: X-Powers AXP223 PMIC, 4-cell Li-ion battery with CN3704 charge controller
- **Connectivity**: Realtek RTL8189ETV WiFi module

## Documentation

### Hardware Documentation
1. **[Lidar Sensor Analysis](/Research/Lidar/README.md)** - Protocol specification, pinout, and visualization tool
2. **[Motherboard Analysis](/Research/Motherboard/README.md)** - Component identification, connector mapping, and circuit analysis
   - [Component Diagram](/Research/Motherboard/Component_Diagram.md) - Detailed component identification and connections
   - [Connection Evidence](/Research/Motherboard/Connection_Evidence.md) - A33-GD32 hardware connection analysis

### Protocol & Communication
3. **[GD32F1 MCU Protocol](/Research/GD32F1/README.md)** - Communication protocol between A33 and GD32F103
   - **[GD32 Protocol - VERIFIED](/Research/Software/GD32_PROTOCOL_FINAL.md)** ⭐ - Complete verified protocol specification (RECOMMENDED)
   - [Protocol Discovery Changelog](/Research/Software/CHANGELOG.md) - Evolution of understanding through 5 phases
   - [CRC Algorithm Discovery](/Research/GD32F1/CRC-Algorithm-Discovery.md) - XOR checksum reverse engineering
   - [Initial Protocol Analysis](/Research/GD32F1/A33-GD32-Protocol.md) - Binary reverse engineering (contains outdated info, see notes)

### Software & Firmware
4. **[Software & Firmware Analysis](/Research/Software/README.md)** - Original firmware analysis, system architecture, and device access methods
   - [AuxCtrl Binary Details](/Research/Software/AuxCtrl-Details.md) - Deep analysis of the AuxCtrl process
   - [Serial MITM Approach](/Research/Software/SERIAL_MITM_APPROACH.md) - PTY-based protocol capture method
   - [Serial Logging Guide](/Research/Software/SERIAL_LOGGING.md) - Tools and techniques for packet capture
   - [Test Results](/Research/Software/TEST_RESULTS.md) - Protocol testing outcomes

### Firmware Implementation
5. **[Firmware Projects](/Research/Software/Firmware/README.md)** - Rust-based firmware for Allwinner A33
   - [AuxCtrl-Rust](/Research/Software/Firmware/auxctrl-rust/README.md) - Open-source GD32 communication library
   - [Lidar Reader](/Research/Software/Firmware/lidar-reader/README.md) - Rust library for 3iRobotix Delta-2D Lidar

## Tools

### Lidar Visualization (`Research/Lidar/scan.py`)

Real-time visualization tool for the 3irobotix Delta-2D Lidar sensor.

**Requirements:**
```bash
pip install pyserial matplotlib
```

**Usage:**
1. Connect Lidar to USB-UART adapter
2. Update serial port in `scan.py` (line 5)
3. Run: `python Research/Lidar/scan.py`

The tool displays a real-time polar plot showing distance measurements at 360 degrees.

### Debug Mode
To enable extended debugging and logging:
1. Create file `/mnt/UDISK/debug_mode` on the device
2. Reboot or restart the Monitor process
3. Logs will be written to `/mnt/UDISK/log/`

See [Software Analysis](/Research/Software/README.md) for more details on the system architecture.

## Contributing

This is a personal reverse engineering project. Documentation improvements, protocol discoveries, and hardware analysis are welcome.

## License

Apache 2.0 - See [LICENSE](/LICENSE) file for details.