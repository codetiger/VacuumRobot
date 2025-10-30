//! GD32 Command Builders
//!
//! Provides convenient functions to build command packets for the GD32 MCU.
//! Command IDs extracted from reverse engineering the original AuxCtrl binary.

use super::packet::GD32Packet;

/// Command IDs for GD32 communication (from log analysis)
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum CommandId {
    Stm32Sleep = 0x04,
    WakeupAck = 0x05,
    Wake = 0x06,           // CMD=0x06: Wake/enable motors (VERIFIED)
    RequireVersion = 0x07, // CMD=0x07: Request firmware version (VERIFIED)
    Initialize = 0x08,     // CMD=0x08: Initialization/wakeup command (99 bytes) - NOT IMU! (VERIFIED)
    ResetErrorCode = 0x0A,
    StatusRequest = 0x0D,
    StatusResponse = 0x15, // CMD=0x15: Status response from GD32 (99 bytes) - GD32 DOES respond! (VERIFIED)
    MotorControlType = 0x65,
    Heartbeat = 0x66,      // CMD=0x66: Heartbeat (11 bytes) - NOT motor velocity! (VERIFIED)
    MotorSpeed = 0x67,
    BlowerSpeed = 0x68,
    BrushSpeed = 0x69,
    RollingSpeed = 0x6A,
    CliffIrControl = 0x78,
    CliffIrDirection = 0x79,
    ButtonLedState = 0x8D, // CMD=0x8D: Button LED state control
    LidarPower = 0x97,
    R16Power = 0x99,
    RestartR16 = 0x9A,
    ChargerPower = 0x9B,
    ImuFactoryCalibrate = 0xA1,
    ImuFactoryState = 0xA2,
    GeoMagnetismCalibrate = 0xA3,
    GeoMagnetismState = 0xA4,
}

// ============================================================================
// INITIALIZATION COMMANDS
// ============================================================================

/// CMD=0x08: Initialize/Wakeup GD32
///
/// Based on log analysis, this is sent repeatedly (every ~200ms) during startup
/// until GD32 responds with CMD=0x15 status packets.
///
/// Packet structure: 99 bytes with repeating pattern
/// Example from log: FA FB 63 08 20 08 08 20 08 08 20 08 08 20 08 ...
pub fn init_cmd_0x08() -> GD32Packet {
    // Create 99-byte initialization packet with the repeating pattern
    let mut data = Vec::with_capacity(96);

    // Fill with the repeating pattern seen in the log: 20 08 08
    for _ in 0..32 {
        data.push(0x20);
        data.push(0x08);
        data.push(0x08);
    }

    GD32Packet::new(CommandId::Initialize as u8, data)
}

/// CMD=0x07: Request firmware version
///
/// Packet: FA FB 03 07 00 07
/// Response contains version string like "2.0.1_19082728"
pub fn get_version() -> GD32Packet {
    GD32Packet::new(CommandId::RequireVersion as u8, vec![0x00])
}

/// CMD=0x06: Wake/Enable motors
///
/// Packet: FA FB 03 06 00 06
pub fn wake() -> GD32Packet {
    GD32Packet::new(CommandId::Wake as u8, vec![0x00])
}

// ============================================================================
// KEEP-ALIVE / STATUS COMMANDS
// ============================================================================

/// CMD=0x66: Heartbeat command
///
/// Sent every ~20-50ms to keep the GD32 alive.
/// Packet: FA FB 0B 66 00 00 00 00 00 00 00 00 66 00 (11 bytes + header)
/// GD32 responds with CMD=0x15 status packets (99 bytes)
pub fn heartbeat() -> GD32Packet {
    GD32Packet::new(CommandId::Heartbeat as u8, vec![0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
}

/// Status request command
///
/// Requests status from GD32 (though GD32 doesn't respond via UART).
pub fn status_request() -> GD32Packet {
    GD32Packet::new(CommandId::StatusRequest as u8, vec![0x00])
}

// ============================================================================
// MOTOR CONTROL COMMANDS
// ============================================================================

/// Set motor speeds (direct speed control)
///
/// # Arguments
/// * `left_speed` - Left motor speed (-32768 to 32767)
/// * `right_speed` - Right motor speed (-32768 to 32767)
///
/// Note: Exact encoding TBD from traffic analysis
pub fn motor_speed(left_speed: i16, right_speed: i16) -> GD32Packet {
    let mut data = Vec::new();
    data.extend_from_slice(&left_speed.to_le_bytes());
    data.extend_from_slice(&right_speed.to_le_bytes());
    GD32Packet::new(CommandId::MotorSpeed as u8, data)
}

/// Set motor control type
///
/// # Arguments
/// * `control_type` - 0=speed mode, 1=velocity mode, etc.
pub fn motor_control_type(control_type: u8) -> GD32Packet {
    GD32Packet::new(CommandId::MotorControlType as u8, vec![control_type])
}

// ============================================================================
// BRUSH/BLOWER CONTROL
// ============================================================================

/// Control rolling brush speed
///
/// # Arguments
/// * `speed` - Brush speed (0-100 or similar range)
pub fn rolling_speed(speed: i8) -> GD32Packet {
    GD32Packet::new(CommandId::RollingSpeed as u8, vec![speed as u8])
}

/// Control side brush speed
///
/// # Arguments
/// * `speed` - Brush speed (0-100 or similar range)
pub fn brush_speed(speed: i8) -> GD32Packet {
    GD32Packet::new(CommandId::BrushSpeed as u8, vec![speed as u8])
}

/// Control blower/suction fan speed
///
/// # Arguments
/// * `speed` - Fan speed (0-100 or similar range)
pub fn blower_speed(speed: i8) -> GD32Packet {
    GD32Packet::new(CommandId::BlowerSpeed as u8, vec![speed as u8])
}

// ============================================================================
// LIDAR CONTROL
// ============================================================================

/// Control lidar motor power
///
/// # Arguments
/// * `enabled` - true to turn on, false to turn off
///
/// This controls the lidar motor via the GD32, which then controls
/// the actual GPIO/PWM to the lidar hardware.
pub fn lidar_power(enabled: bool) -> GD32Packet {
    let value = if enabled { 0x01 } else { 0x00 };
    GD32Packet::new(CommandId::LidarPower as u8, vec![value])
}

// ============================================================================
// SENSOR CONTROL
// ============================================================================

/// Control cliff sensor IR LEDs
///
/// # Arguments
/// * `enabled` - true to enable IR LEDs, false to disable
pub fn cliff_ir_control(enabled: bool) -> GD32Packet {
    let value = if enabled { 0x01 } else { 0x00 };
    GD32Packet::new(CommandId::CliffIrControl as u8, vec![value])
}

/// Set cliff sensor IR direction
pub fn cliff_ir_direction(direction: u8) -> GD32Packet {
    GD32Packet::new(CommandId::CliffIrDirection as u8, vec![direction])
}

// ============================================================================
// UI CONTROL
// ============================================================================

/// CMD=0x8D: Control button LED states / Set control mode
///
/// Packet: FA FB 04 8D 01 8D 01 (4 bytes + header)
/// Parameter 0x01 sets control mode
/// Response includes firmware version string
pub fn set_control_mode(mode: u8) -> GD32Packet {
    GD32Packet::new(CommandId::ButtonLedState as u8, vec![mode])
}

// ============================================================================
// IMU CALIBRATION
// ============================================================================

/// Set IMU zero point (CMD=0x08 was repurposed for initialization)
pub fn set_imu_zero() -> GD32Packet {
    // Note: CMD=0x08 is now used for initialization, not IMU zero
    GD32Packet::new(0x08, vec![])
}

/// Start IMU factory calibration
pub fn imu_factory_calibrate() -> GD32Packet {
    GD32Packet::new(CommandId::ImuFactoryCalibrate as u8, vec![])
}

/// Request IMU factory calibration state
pub fn imu_factory_state() -> GD32Packet {
    GD32Packet::new(CommandId::ImuFactoryState as u8, vec![])
}

/// Start geo-magnetism calibration
pub fn geo_magnetism_calibrate() -> GD32Packet {
    GD32Packet::new(CommandId::GeoMagnetismCalibrate as u8, vec![])
}

/// Request geo-magnetism calibration state
pub fn geo_magnetism_state() -> GD32Packet {
    GD32Packet::new(CommandId::GeoMagnetismState as u8, vec![])
}

// ============================================================================
// SYSTEM CONTROL
// ============================================================================

/// Reset error codes
pub fn reset_error_code() -> GD32Packet {
    GD32Packet::new(CommandId::ResetErrorCode as u8, vec![])
}

/// Put GD32 to sleep mode
pub fn stm32_sleep() -> GD32Packet {
    GD32Packet::new(CommandId::Stm32Sleep as u8, vec![])
}

/// Acknowledge wakeup
pub fn wakeup_ack() -> GD32Packet {
    GD32Packet::new(CommandId::WakeupAck as u8, vec![])
}

/// Restart GD32 MCU
pub fn restart_r16() -> GD32Packet {
    GD32Packet::new(CommandId::RestartR16 as u8, vec![])
}

/// Control R16 (GD32) power
pub fn r16_power(enabled: bool) -> GD32Packet {
    let value = if enabled { 0x01 } else { 0x00 };
    GD32Packet::new(CommandId::R16Power as u8, vec![value])
}

/// Control charger power
pub fn charger_power(enabled: bool) -> GD32Packet {
    let value = if enabled { 0x01 } else { 0x00 };
    GD32Packet::new(CommandId::ChargerPower as u8, vec![value])
}

/// Request GD32 firmware version
pub fn require_version() -> GD32Packet {
    GD32Packet::new(CommandId::RequireVersion as u8, vec![])
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heartbeat_command() {
        let cmd = heartbeat();
        assert_eq!(cmd.command_id, 0x06);
        assert_eq!(cmd.data, vec![0x00]);
    }

    #[test]
    fn test_lidar_power_on() {
        let cmd = lidar_power(true);
        assert_eq!(cmd.command_id, 0x97);
        assert_eq!(cmd.data, vec![0x01]);
    }

    #[test]
    fn test_lidar_power_off() {
        let cmd = lidar_power(false);
        assert_eq!(cmd.command_id, 0x97);
        assert_eq!(cmd.data, vec![0x00]);
    }

    #[test]
    fn test_motor_speed() {
        let cmd = motor_speed(100, -50);
        assert_eq!(cmd.command_id, 0x67);
        // 100 = 0x64 0x00 (little-endian)
        // -50 = 0xCE 0xFF (little-endian)
        assert_eq!(cmd.data, vec![0x64, 0x00, 0xCE, 0xFF]);
    }
}
