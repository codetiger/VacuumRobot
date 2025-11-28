# Firmware Projects

This directory contains early Rust-based firmware experiments for the vacuum robot's Allwinner A33 processor.

> **Note**: These experiments have evolved into a complete firmware implementation: **[VacuumTiger](https://github.com/codetiger/VacuumTiger)** - an open-source firmware platform for autonomous vacuum robots featuring SangamIO daemon, Drishti diagnostic UI, and a generic TCP protocol for SLAM integration.

## Prerequisites

### Required Tools
- **Rust toolchain**: Install from https://rustup.rs/
- **ARM cross-compilation target**: `rustup target add armv7-unknown-linux-musleabihf`
- **ARM GNU toolchain** (macOS): `brew tap messense/macos-cross-toolchains && brew install armv7-unknown-linux-musleabihf`

### Target Platform
- **Architecture**: ARM Cortex-A7 (ARMv7)
- **Processor**: Allwinner A33 Quad-Core
- **OS**: Tina Linux (custom OpenWrt-based)
- **Compilation Target**: `armv7-unknown-linux-musleabihf` (hard-float, musl libc)

## Projects

### helloworld
Simple Hello World program demonstrating the build and deployment workflow.

**Build:**
```bash
cd helloworld
cargo build --release
```

**Deploy and Run:**
```bash
# Transfer binary and execute (device doesn't have scp)
cat target/armv7-unknown-linux-musleabihf/release/hello_vacuum | \
  sshpass -p "<your-password>" ssh root@vacuum \
  "cat > /tmp/hello_vacuum && chmod +x /tmp/hello_vacuum && /tmp/hello_vacuum"
```

### lidar-reader
Rust library for interfacing with the 3iRobotix Delta-2D Lidar sensor. Implements the complete UART protocol for reading distance and angle measurements.

**Features:**
- Full protocol implementation (health and measurement packets)
- Power on/off control
- Structured data types (Scan, Measurement)
- Example scanner application
- Designed for integration into larger robot applications

**Build Library:**
```bash
cd lidar-reader
cargo build --release
```

**Build and Run Example:**
```bash
cd lidar-reader
cargo build --release --example scan

# Transfer and run on device
cat target/armv7-unknown-linux-musleabihf/release/examples/scan | \
  sshpass -p "<your-password>" ssh root@vacuum \
  "cat > /tmp/scan && chmod +x /tmp/scan && /tmp/scan /dev/ttyS1 107"
```

**Library Usage:**
```rust
use lidar_reader::Lidar;

// GPIO 107 is a candidate for Lidar motor control (hardware-dependent)
let mut lidar = Lidar::new("/dev/ttyS1", 107)?;
lidar.power_on()?;

loop {
    if let Ok(Some(scan)) = lidar.read_scan() {
        for measurement in scan.measurements {
            println!("{:.2}° -> {:.2}mm", measurement.angle, measurement.distance);
        }
    }
}
```

See `lidar-reader/README.md` for detailed documentation.

## Building Binaries

Each project contains a `.cargo/config.toml` that configures:
- Default target architecture: `armv7-unknown-linux-musleabihf`
- Custom linker: `armv7-unknown-linux-musleabihf-gcc`

All binaries are statically linked with musl libc, requiring no external dependencies on the target device.

## Development Notes

- Binary size: ~485KB for minimal Hello World (statically linked)
- The device has limited storage, optimize binary size when possible
- Use `cargo build --release` for optimized binaries
- The device doesn't have Python or many standard Linux utilities
