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
│  ┌────────────┐    ┌──────────────┐ │
│  │ auxctrl-   │    │  Lidar       │ │
│  │ rust       │────│  Reader      │ │
│  └─────┬──────┘    └──────┬───────┘ │
│        │                  │         │
└────────┼──────────────────┼─────────┘
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

- `Research/GD32F1/CRC-Algorithm-Discovery.md` - CRC algorithm
- `Research/backup/Analysis/GD32_Init_Sequence.md` - Initialization
- `Research/backup/Analysis/Sensor_Architecture.md` - System architecture
- `Research/backup/Analysis/analyze_capture.py` - Command IDs

Key findings:
- Protocol uses simple XOR checksum (not CRC16/32)
- GD32 operates autonomously, doesn't send UART responses
- Status communicated via GPIO pins
- First command must be 0x66 (initialization)

## Testing Results

Expected behavior when running test program:

1. ✅ Program connects to `/dev/ttyS3` successfully
2. ✅ Sends initialization command (0x66)
3. ✅ Sends heartbeat (0x06)
4. 🔄 Lidar motor starts spinning (physical observation)
5. 🔄 Wheels move when motor command sent (physical observation)
6. ✅ gpio-39 may change state
7. ✅ No kernel errors in `dmesg`

## Next Steps

1. **Validate motor commands** - Observe physical movement when sending motor_speed()
2. **Lidar integration** - Integrate with lidar-reader library
3. **GPIO monitoring** - Read gpio-39 for obstacle detection
4. **Higher-level API** - Add navigation primitives (move_forward, turn_left, etc.)
5. **Robot application** - Build autonomous navigation system

## License

Open source - Use freely for research and development

## Contributing

This is a research/reverse engineering project. Contributions welcome!

See parent project: `/Users/codetiger/Development/VacuumRobot`
