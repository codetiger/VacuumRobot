//! # 3iRobotix Delta-2D Lidar Reader
//!
//! This library provides a Rust interface for the 3iRobotix Delta-2D Lidar sensor.
//! It implements the UART protocol for reading distance and angle measurements.
//!
//! ## Protocol Overview
//!
//! The Lidar communicates via UART at 115200 baud with the following packet structure:
//! - Chunk Header (1 byte)
//! - Chunk Length (2 bytes, big-endian)
//! - Chunk Version (1 byte)
//! - Chunk Type (1 byte)
//! - Command Type (1 byte): 0xAE (health) or 0xAD (measurement)
//! - Payload Length (2 bytes, big-endian)
//! - Payload Data (variable length)
//! - Payload CRC (2 bytes, big-endian)
//!
//! ## Example
//!
//! ```no_run
//! use lidar_reader::Lidar;
//!
//! // GPIO pin 123 controls the Lidar motor power
//! let mut lidar = Lidar::new("/dev/ttyS2", 123).expect("Failed to open Lidar");
//! lidar.power_on().expect("Failed to power on");
//!
//! loop {
//!     if let Ok(Some(scan)) = lidar.read_scan() {
//!         println!("Motor RPM: {}", scan.motor_rpm);
//!         for measurement in scan.measurements {
//!             println!("Angle: {:.2}°, Distance: {:.2}mm",
//!                      measurement.angle, measurement.distance);
//!         }
//!     }
//! }
//! ```

use serialport::SerialPort;
use std::io::{self, Read};
use std::time::Duration;
use sysfs_gpio::{Direction, Pin};

/// Command types sent by the Lidar
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommandType {
    /// Health check data (0xAE)
    Health = 0xAE,
    /// Measurement data with angles and distances (0xAD)
    Measurement = 0xAD,
}

impl CommandType {
    fn from_u8(value: u8) -> Option<Self> {
        match value {
            0xAE => Some(CommandType::Health),
            0xAD => Some(CommandType::Measurement),
            _ => None,
        }
    }
}

/// A single distance measurement at a specific angle
#[derive(Debug, Clone)]
pub struct Measurement {
    /// Angle in degrees (0-360)
    pub angle: f32,
    /// Distance in millimeters
    pub distance: f32,
    /// Signal quality (0-255)
    pub signal_quality: u8,
}

/// A complete scan containing multiple measurements
#[derive(Debug, Clone)]
pub struct Scan {
    /// Motor rotation speed in RPM
    pub motor_rpm: u16,
    /// Offset angle in degrees
    pub offset_angle: f32,
    /// Starting angle of this scan packet
    pub start_angle: f32,
    /// Individual measurements in this scan
    pub measurements: Vec<Measurement>,
}

/// Packet header received from the Lidar
#[derive(Debug)]
struct PacketHeader {
    _chunk_header: u8,
    _chunk_length: u16,
    _chunk_version: u8,
    _chunk_type: u8,
    command_type: CommandType,
    payload_length: u16,
}

/// Main Lidar interface
pub struct Lidar {
    port: Box<dyn SerialPort>,
    power_pin: Pin,
}

impl Lidar {
    /// Create a new Lidar instance with GPIO power control
    ///
    /// # Arguments
    /// * `port_name` - Serial port path (e.g., "/dev/ttyS2" on Linux)
    /// * `gpio_pin` - GPIO pin number for power control (e.g., 123)
    ///
    /// # Returns
    /// A new Lidar instance or an error if the port/GPIO cannot be opened
    ///
    /// # Example
    /// ```no_run
    /// use lidar_reader::Lidar;
    ///
    /// // Lidar power controlled by GPIO pin 123
    /// let mut lidar = Lidar::new("/dev/ttyS2", 123)?;
    /// lidar.power_on()?; // This will set GPIO pin 123 to high
    /// # Ok::<(), std::io::Error>(())
    /// ```
    pub fn new(port_name: &str, gpio_pin: u64) -> io::Result<Self> {
        let port = serialport::new(port_name, 115200)
            .timeout(Duration::from_millis(100))
            .open()
            .map_err(|e| io::Error::new(io::ErrorKind::Other, e))?;

        let power_pin = Pin::new(gpio_pin);
        power_pin.export()
            .map_err(|e| io::Error::new(io::ErrorKind::Other, format!("Failed to export GPIO pin {}: {}", gpio_pin, e)))?;
        power_pin.set_direction(Direction::Out)
            .map_err(|e| io::Error::new(io::ErrorKind::Other, format!("Failed to set GPIO pin {} direction: {}", gpio_pin, e)))?;

        Ok(Lidar {
            port,
            power_pin,
        })
    }

    /// Power on the Lidar motor
    ///
    /// Sets the GPIO pin HIGH to enable motor power.
    pub fn power_on(&mut self) -> io::Result<()> {
        self.power_pin.set_value(1)
            .map_err(|e| io::Error::new(io::ErrorKind::Other, format!("Failed to set GPIO pin high: {}", e)))
    }

    /// Power off the Lidar motor
    ///
    /// Sets the GPIO pin LOW to disable motor power.
    pub fn power_off(&mut self) -> io::Result<()> {
        self.power_pin.set_value(0)
            .map_err(|e| io::Error::new(io::ErrorKind::Other, format!("Failed to set GPIO pin low: {}", e)))
    }

    /// Check if the Lidar is powered on
    ///
    /// Reads the current GPIO pin state directly from hardware.
    pub fn is_powered(&self) -> io::Result<bool> {
        self.power_pin.get_value()
            .map(|v| v != 0)
            .map_err(|e| io::Error::new(io::ErrorKind::Other, format!("Failed to read GPIO pin value: {}", e)))
    }

    /// Read a packet header from the serial port
    fn read_header(&mut self) -> io::Result<PacketHeader> {
        let mut header_buf = [0u8; 8];
        self.port.read_exact(&mut header_buf)?;

        let chunk_header = header_buf[0];
        let chunk_length = u16::from_be_bytes([header_buf[1], header_buf[2]]);
        let chunk_version = header_buf[3];
        let chunk_type = header_buf[4];
        let command_type_raw = header_buf[5];
        let payload_length = u16::from_be_bytes([header_buf[6], header_buf[7]]);

        let command_type = CommandType::from_u8(command_type_raw)
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "Unknown command type"))?;

        Ok(PacketHeader {
            _chunk_header: chunk_header,
            _chunk_length: chunk_length,
            _chunk_version: chunk_version,
            _chunk_type: chunk_type,
            command_type,
            payload_length,
        })
    }

    /// Parse measurement data from the payload
    fn parse_measurement(&self, payload: &[u8]) -> io::Result<Scan> {
        if payload.len() < 5 {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "Payload too short",
            ));
        }

        let motor_rpm = (payload[0] as u16) * 3;
        let offset_angle = u16::from_be_bytes([payload[1], payload[2]]) as f32 * 0.01;
        let start_angle = u16::from_be_bytes([payload[3], payload[4]]) as f32 * 0.01;

        let sample_count = (payload.len() - 5) / 3;
        let mut measurements = Vec::with_capacity(sample_count);

        for i in 0..sample_count {
            let base = 5 + i * 3;
            if base + 3 > payload.len() {
                break;
            }

            let signal_quality = payload[base];
            let distance = u16::from_be_bytes([payload[base + 1], payload[base + 2]]) as f32 * 0.25;
            let angle = start_angle + (i as f32) * (360.0 / (16.0 * sample_count as f32));

            measurements.push(Measurement {
                angle,
                distance,
                signal_quality,
            });
        }

        Ok(Scan {
            motor_rpm,
            offset_angle,
            start_angle,
            measurements,
        })
    }

    /// Read a single scan from the Lidar
    ///
    /// This function reads one packet from the Lidar. It may contain health data
    /// or measurement data. Returns `Ok(None)` if health data is received.
    ///
    /// # Returns
    /// - `Ok(Some(Scan))` - A complete scan with measurements
    /// - `Ok(None)` - Health packet received (no measurements)
    /// - `Err(_)` - Read error or invalid data
    pub fn read_scan(&mut self) -> io::Result<Option<Scan>> {
        let header = self.read_header()?;

        let mut payload = vec![0u8; header.payload_length as usize];
        self.port.read_exact(&mut payload)?;

        let mut crc_buf = [0u8; 2];
        self.port.read_exact(&mut crc_buf)?;
        let _payload_crc = u16::from_be_bytes(crc_buf);

        match header.command_type {
            CommandType::Measurement => {
                let scan = self.parse_measurement(&payload)?;
                Ok(Some(scan))
            }
            CommandType::Health => {
                // Health packets don't contain scan data
                Ok(None)
            }
        }
    }

    /// Get the number of bytes available to read
    pub fn bytes_available(&mut self) -> io::Result<u32> {
        self.port
            .bytes_to_read()
            .map_err(|e| io::Error::new(io::ErrorKind::Other, e))
    }
}

impl Drop for Lidar {
    fn drop(&mut self) {
        // Power off the motor
        let _ = self.power_off();

        // Unexport GPIO pin
        let _ = self.power_pin.unexport();
    }
}
