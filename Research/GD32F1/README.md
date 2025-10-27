# GD32F1 MCU Protocol Analysis

## Overview

This directory contains research and documentation for reverse engineering the communication protocol between the Allwinner A33 main processor and the GigaDevice GD32F103VCT6 microcontroller in the 3irobotix CRL-200S vacuum robot.

## Hardware Details

### GD32F103VCT6 MCU
- **Core**: ARM Cortex-M3 @ 108 MHz
- **RAM**: 48 KB
- **Flash**: 256 KB
- **Location**: U1 on motherboard

### Allwinner A33 SoC
- **Core**: ARM Cortex-A7 Quad-Core
- **Interfaces**: 5x UART, 4x I2C (TWI), SPI, PWM
- **Location**: U23 on motherboard

## Likely Communication Interface

The A33 and GD32F1 most likely communicate via:
1. **UART** (most common for MCU-CPU communication)
2. **SPI** (higher speed alternative)
3. **I2C** (less likely for primary communication)

## References

- [Motherboard Documentation](../Motherboard/README.md)
- [Allwinner A33 Datasheet](https://linux-sunxi.org/A33)
- [GD32F103 Datasheet](https://www.gigadevice.com/product/mcu/mcus-product-selector/gd32f103vct6)
