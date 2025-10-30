# GD32F1 MCU Protocol Analysis

## Overview

This directory contains research and documentation for reverse engineering the communication protocol between the Allwinner A33 main processor and the GigaDevice GD32F103VCT6 microcontroller in the 3irobotix CRL-200S vacuum robot.

## 📚 Protocol Documentation

### Primary (Verified)
- **[GD32 Protocol - VERIFIED](../Software/GD32_PROTOCOL_FINAL.md)** ⭐ - Complete verified protocol specification
- **[Protocol Discovery Changelog](../Software/CHANGELOG.md)** - Evolution of understanding through 5 phases
- **[CRC Algorithm Discovery](CRC-Algorithm-Discovery.md)** - XOR checksum reverse engineering

### Supporting Documentation
- **[Initial Protocol Analysis](A33-GD32-Protocol.md)** - Binary reverse engineering (⚠️ contains some outdated info)
- **[AuxCtrl Binary Details](../Software/AuxCtrl-Details.md)** - Deep analysis of the AuxCtrl process
- **[Serial MITM Approach](../Software/SERIAL_MITM_APPROACH.md)** - PTY-based protocol capture methodology

### Implementation
- **[AuxCtrl-Rust](../Software/Firmware/auxctrl-rust/README.md)** - Open-source Rust implementation

## Hardware Details

### GD32F103VCT6 MCU
- **Core**: ARM Cortex-M3 @ 108 MHz
- **RAM**: 48 KB
- **Flash**: 256 KB
- **Location**: U1 on motherboard
- **Datasheet**: [GigaDevice GD32F103](https://www.gigadevice.com/product/mcu/mcus-product-selector/gd32f103vct6)

### Allwinner A33 SoC
- **Core**: ARM Cortex-A7 Quad-Core
- **Interfaces**: 5x UART, 4x I2C (TWI), SPI, PWM
- **Location**: U23 on motherboard
- **Datasheet**: [Allwinner A33](https://linux-sunxi.org/A33)

## Communication Interface (VERIFIED)

**Protocol**: UART (verified via serial MITM capture)
- **Port**: `/dev/ttyS3` (UART3 on A33)
- **Baud Rate**: 115200
- **Format**: 8N1 (8 data bits, no parity, 1 stop bit)
- **Mode**: Bidirectional (A33↔GD32)
- **Packet Format**: `FA FB [LEN] [CMD] [DATA...] [CRC]`

See **[Connection Evidence](../Motherboard/Connection_Evidence.md)** for hardware connection analysis.

## References

### Hardware
- **[Motherboard Documentation](../Motherboard/README.md)** - Component identification
- **[Component Diagram](../Motherboard/Component_Diagram.md)** - Detailed connections
- **[Connection Evidence](../Motherboard/Connection_Evidence.md)** - A33-GD32 physical connections

### Software
- **[Software Analysis](../Software/README.md)** - Firmware analysis and system architecture
