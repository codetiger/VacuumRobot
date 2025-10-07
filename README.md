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

### 🔄 In Progress
- Detailed circuit analysis and tracing
- Communication protocol analysis between MCU and main CPU

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

1. [Lidar Sensor Analysis](/Research/Lidar/README.md) - Protocol specification, pinout, and visualization tool
2. [Motherboard Analysis](/Research/Motherboard/README.md) - Component identification, connector mapping, and circuit analysis

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

## Contributing

This is a personal reverse engineering project. Documentation improvements, protocol discoveries, and hardware analysis are welcome.

## License

Apache 2.0 - See [LICENSE](/LICENSE) file for details.