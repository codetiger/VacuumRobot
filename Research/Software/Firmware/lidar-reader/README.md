# Lidar Reader

Rust library for interfacing with the 3iRobotix Delta-2D Lidar sensor used in the vacuum robot.

## Overview

This library provides a clean, idiomatic Rust interface for reading distance and angle measurements from the Lidar sensor. It implements the full UART protocol for the 3iRobotix Delta-2D Lidar.

## Hardware Connection

The Lidar connects via UART at 115200 baud:

| Pin | Function | Notes |
|-----|----------|-------|
| 1-2 | Motor Power | Can be controlled via GPIO |
| 3-4 | VCC/GND | Power for electronics |
| 5   | TX | UART transmit (connect to device RX) |

On the vacuum robot, the Lidar is connected to `/dev/ttyS1` (UART1, pins PG6/PG7).

### GPIO Power Control

The Lidar motor power (pins 1-2) requires control via a GPIO pin. The exact GPIO pin number is hardware-dependent and needs to be determined experimentally. The library uses the Linux sysfs GPIO interface.

**Note**: On the vacuum robot hardware, the Lidar motor control GPIO is not yet definitively identified. Possible candidates include:
- GPIO 107 (currently HIGH on device)
- Motor may be controlled through GD32 MCU commands instead of direct GPIO

## Library Structure

### Core Types

- **`Lidar`**: Main interface for Lidar communication
  - `new(port)`: Create new instance without GPIO control
  - `with_power_pin(port, gpio)`: Create instance with GPIO power control
  - `power_on()`: Enable motor (controls GPIO if configured)
  - `power_off()`: Disable motor (controls GPIO if configured)
  - `read_scan()`: Read one scan packet

- **`Scan`**: Complete scan data packet
  - `motor_rpm`: Current motor speed
  - `offset_angle`: Offset angle in degrees
  - `start_angle`: Starting angle for this packet
  - `measurements`: Vec of individual measurements

- **`Measurement`**: Single distance reading
  - `angle`: Angle in degrees (0-360)
  - `distance`: Distance in millimeters
  - `signal_quality`: Signal quality (0-255)

### Protocol Implementation

The library fully implements the Lidar's binary protocol:

```
[Header: 8 bytes]
- Chunk Header (1 byte)
- Chunk Length (2 bytes, big-endian)
- Chunk Version (1 byte)
- Chunk Type (1 byte)
- Command Type (1 byte): 0xAE=health, 0xAD=measurement
- Payload Length (2 bytes, big-endian)

[Payload: variable]
- Motor RPM (1 byte, multiply by 3)
- Offset Angle (2 bytes, multiply by 0.01 for degrees)
- Start Angle (2 bytes, multiply by 0.01 for degrees)
- Measurements: 3 bytes each
  - Signal Quality (1 byte)
  - Distance (2 bytes, multiply by 0.25 for mm)

[Footer: 2 bytes]
- CRC (2 bytes, big-endian)
```

## Building

```bash
cd lidar-reader
cargo build --release
```

The binary will be cross-compiled for ARM (armv7-unknown-linux-musleabihf) by default.

## Examples

### Basic Scan Example

```bash
# Build the example
cargo build --release --example scan

# Transfer to device and run (GPIO pin needs to be determined for your hardware)
cat target/armv7-unknown-linux-musleabihf/release/examples/scan | \
  sshpass -p "<your-password>" ssh root@vacuum \
  "cat > /tmp/scan && chmod +x /tmp/scan && /tmp/scan /dev/ttyS1 107"
```

### Library Usage

```rust
use lidar_reader::Lidar;

// GPIO pin number is hardware-dependent (e.g., 107 on vacuum robot)
let mut lidar = Lidar::new("/dev/ttyS1", 107)?;

// This will set the GPIO pin HIGH to power on the motor
lidar.power_on()?;

loop {
    if let Ok(Some(scan)) = lidar.read_scan() {
        println!("Motor: {} RPM", scan.motor_rpm);
        for m in scan.measurements {
            println!("  {:.2}° -> {:.2}mm", m.angle, m.distance);
        }
    }
}

// When dropped, the GPIO pin will be set LOW and unexported
```

## Integration with Robot App

This library is designed to be integrated into a larger robot application. Example integration:

```rust
// In your robot application
mod navigation {
    use lidar_reader::{Lidar, Scan};

    pub struct Navigator {
        lidar: Lidar,
        obstacle_map: HashMap<i32, f32>,
    }

    impl Navigator {
        pub fn new(gpio_pin: u64) -> io::Result<Self> {
            let lidar = Lidar::new("/dev/ttyS1", gpio_pin)?;
            Ok(Navigator {
                lidar,
                obstacle_map: HashMap::new(),
            })
        }

        pub fn update(&mut self) -> io::Result<()> {
            if let Ok(Some(scan)) = self.lidar.read_scan() {
                for m in scan.measurements {
                    self.obstacle_map.insert(
                        m.angle.round() as i32,
                        m.distance
                    );
                }
            }
            Ok(())
        }

        pub fn is_path_clear(&self, angle: f32, min_distance: f32) -> bool {
            self.obstacle_map
                .get(&(angle.round() as i32))
                .map(|&d| d > min_distance)
                .unwrap_or(true)
        }
    }
}
```

## Future Enhancements

Potential additions for robot integration:

1. **Data Filtering**: Implement Kalman filters for noise reduction
2. **SLAM Integration**: Add simultaneous localization and mapping
3. **Obstacle Detection**: Higher-level API for obstacle detection
4. **Performance Metrics**: Track scan rate, data quality metrics
5. **Motor Control**: Interface for controlling Lidar motor speed

## References

- Original Python implementation: `../../Lidar/scan.py`
- Protocol documentation: `../../Lidar/README.md`
- Hardware photos and pinout: `../../Lidar/`
