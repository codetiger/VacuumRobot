//! GD32F103 MCU Communication Module
//!
//! This module provides complete communication with the GD32F103 microcontroller
//! used in the vacuum robot for motor control, sensor management, and peripheral control.

pub mod commands;
pub mod connection;
pub mod gpio;
pub mod packet;

// Re-export commonly used items
pub use commands::{CommandId, *};
pub use connection::GD32Connection;
pub use gpio::GD32GPIO;
pub use packet::GD32Packet;
