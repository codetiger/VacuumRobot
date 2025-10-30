# AuxCtrl-Rust

Open-source firmware library for vacuum robot GD32 communication, written in Rust.

## Overview

This library replaces the proprietary `AuxCtrl` binary with a clean, open-source Rust implementation that communicates with the GD32F103 microcontroller.

### Features

- ✅ Complete GD32 protocol implementation
- ✅ XOR-based CRC checksum (reverse engineered)
- ✅ 25+ command builders (motors, lidar, sensors, LEDs)
- ✅ Cross-compiled for ARM (Allwinner A33)
- ✅ Comprehensive unit tests
- ✅ Example test program included

## Architecture

```
┌──────────────────────────────────────┐
│       Allwinner A33 (Tina Linux)     │
│                                      │
│  ┌────────────┐    ┌──────────────┐  │
│  │ auxctrl-   │    │  Lidar       │  │
│  │ rust       │────│  Reader      │  │
│  └─────┬──────┘    └──────┬───────┘  │
│        │                  │          │
└────────┼──────────────────┼──────────┘
         │                  │
         │ /dev/ttyS3       │ /dev/ttyS1
         │ 115200 baud      │ 115200 baud
         ↓                  ↓
  ┌──────────────┐    ┌─────────────┐
  │  GD32F103    │    │  3iRobotix  │
  │  MCU         │    │  Lidar      │
  └──────────────┘    └─────────────┘
```

## Protocol

### Packet Structure

```
[SYNC1: 0xFA] [SYNC2: 0xFB] [LEN] [CMD] [DATA...] [CRC]
```

- **SYNC1, SYNC2**: Fixed sync bytes
- **LEN**: Length of remaining packet (CMD + DATA + CRC)
- **CMD**: Command ID (see commands.rs for full list)
- **DATA**: Variable length payload
- **CRC**: Simple XOR checksum: `CMD ⊕ DATA[0] ⊕ DATA[1] ⊕ ...`

### Communication Model

- **Bidirectional UART**: A33 sends commands to GD32, GD32 responds with status packets
- **Status packets**: GD32 sends CMD=0x15 (99 bytes) containing sensor data
- **Heartbeat required**: A33 must send CMD=0x66 every 20-50ms
- **Autonomous operation**: GD32 handles real-time control independently

## Building

### Prerequisites

```bash
# Install ARM cross-compilation target
rustup target add armv7-unknown-linux-musleabihf

# Install ARM GNU toolchain (macOS)
brew tap messense/macos-cross-toolchains
brew install armv7-unknown-linux-musleabihf
```

### Build for ARM

```bash
cd auxctrl-rust
cargo build --release
```

Binary will be at: `target/armv7-unknown-linux-musleabihf/release/auxctrl`

### Run Tests

```bash
cargo test
```

## Usage

### As a Library

```rust
use auxctrl_rust::gd32::{GD32Connection, commands};
use std::{thread, time::Duration};

fn main() -> std::io::Result<()> {
    // Open connection
    let mut gd32 = GD32Connection::new("/dev/ttyS3")?;

    // Initialize
    gd32.send_packet(&commands::initialize())?;
    thread::sleep(Duration::from_millis(100));

    // Turn on lidar
    gd32.send_packet(&commands::lidar_power(true))?;

    // Control motors
    gd32.send_packet(&commands::motor_speed(100, 100))?;

    // Keep alive
    loop {
        gd32.send_packet(&commands::heartbeat())?;
        thread::sleep(Duration::from_millis(500));
    }
}
```

### Testing on Device

```bash
# Stop original AuxCtrl
ssh root@vacuum "killall -9 AuxCtrl"

# Deploy and run
cat target/armv7-unknown-linux-musleabihf/release/auxctrl | \
  ssh root@vacuum "cat > /tmp/auxctrl && chmod +x /tmp/auxctrl && /tmp/auxctrl"
```

## Available Commands

| Command | ID | Description |
|---------|-----|-------------|
| `initialize()` | 0x66 | Must be sent first |
| `heartbeat()` | 0x06 | Keep-alive signal |
| `motor_speed(left, right)` | 0x67 | Set wheel motor speeds |
| `motor_velocity(data)` | 0x66 | Set velocity parameters |
| `lidar_power(bool)` | 0x97 | Control lidar motor |
| `blower_speed(speed)` | 0x68 | Control suction fan |
| `brush_speed(speed)` | 0x69 | Control side brush |
| `rolling_speed(speed)` | 0x6A | Control rolling brush |
| `button_led_state(state)` | 0x8D | Control button LEDs |
| `require_version()` | 0x07 | Request firmware version |
| `restart_r16()` | 0x9A | Restart GD32 MCU |

See `src/gd32/commands.rs` for complete list (25+ commands).

## Research & Reverse Engineering

This implementation is based on extensive reverse engineering documented in:

### Primary Documentation (Verified)
- **[GD32 Protocol - VERIFIED](../../GD32_PROTOCOL_FINAL.md)** ⭐ - Complete verified protocol specification
- **[Protocol Discovery Changelog](../../CHANGELOG.md)** - Evolution of understanding through 5 phases
- **[Serial MITM Approach](../../SERIAL_MITM_APPROACH.md)** - PTY-based protocol capture methodology
- **[CRC Algorithm Discovery](../../../GD32F1/CRC-Algorithm-Discovery.md)** - XOR checksum reverse engineering
- **[Test Results](../../TEST_RESULTS.md)** - Protocol testing outcomes

### Supporting Documentation
- **[AuxCtrl Binary Details](../../AuxCtrl-Details.md)** - Deep analysis of the AuxCtrl process
- **[Initial Protocol Analysis](../../../GD32F1/A33-GD32-Protocol.md)** - Binary reverse engineering (contains some outdated info)
- **[Hardware Connections](../../../Motherboard/Connection_Evidence.md)** - A33-GD32 physical connections

Key findings (CORRECTED):
- Protocol uses simple XOR checksum (not CRC16/32)
- **GD32 DOES respond** with CMD=0x15 status packets (bidirectional communication)
- Serial port: `/dev/ttyS3` (not `/dev/ttyS1`)
- Initialization: CMD=0x08 (repeated for ~5 seconds)
- Heartbeat: CMD=0x66 (every 20-50ms)

## Testing Results

Expected behavior when running test program:

1. ✅ Program connects to `/dev/ttyS3` successfully
2. ✅ Sends initialization command (0x66)
3. ✅ Sends heartbeat (0x06)
4. 🔄 Lidar motor starts spinning (physical observation)
5. 🔄 Wheels move when motor command sent (physical observation)
6. ✅ gpio-39 may change state
7. ✅ No kernel errors in `dmesg`

