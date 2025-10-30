//! # AuxCtrl-Rust: Open-Source Vacuum Robot Firmware Library
//!
//! This library provides complete communication with the vacuum robot's hardware:
//! - **GD32F103 MCU**: Motor control, sensors, IMU, buttons, LEDs
//! - **3iRobotix Lidar**: Distance/angle measurements (via lidar-reader crate)
//!
//! ## Architecture
//!
//! The vacuum robot uses a distributed architecture:
//! - **Allwinner A33** (this code): High-level control, navigation, Wi-Fi
//! - **GD32F103 MCU**: Real-time motor control, safety sensors
//! - **3iRobotix Lidar**: 360° distance scanning
//!
//! ## Communication
//!
//! - **A33 → GD32**: One-way UART commands over `/dev/ttyS3` at 115200 baud
//! - **GD32 → A33**: Status via GPIO pins (gpio-39)
//! - **Lidar → A33**: UART data over `/dev/ttyS1` at 115200 baud
//!
//! ## Quick Start
//!
//! ```no_run
//! use auxctrl_rust::gd32::{GD32Connection, commands};
//! use std::thread;
//! use std::time::Duration;
//!
//! fn main() -> std::io::Result<()> {
//!     // Connect to GD32
//!     let mut gd32 = GD32Connection::new("/dev/ttyS3")?;
//!
//!     // Initialize communication
//!     gd32.send_packet(&commands::initialize())?;
//!     thread::sleep(Duration::from_millis(100));
//!
//!     // Turn on lidar
//!     gd32.send_packet(&commands::lidar_power(true))?;
//!
//!     // Send heartbeat
//!     gd32.send_packet(&commands::heartbeat())?;
//!
//!     Ok(())
//! }
//! ```

pub mod gd32;

// Re-export for convenience
pub use gd32::GD32Connection;
