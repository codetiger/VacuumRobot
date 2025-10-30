//! GD32 Wakeup Test Program
//!
//! Tests various strategies to wake up the GD32 from sleep mode.

use auxctrl_rust::gd32::{commands, GD32Connection, GD32GPIO};
use std::{thread, time::Duration};

fn main() -> std::io::Result<()> {
    println!("========================================");
    println!("  GD32 Wakeup Test Program");
    println!("  Testing Multiple Wakeup Strategies");
    println!("========================================\n");

    // Initialize GPIO
    println!("Step 1: Initializing GPIO...");
    let gpio = GD32GPIO::new();
    gpio.initialize()?;
    gpio.print_status()?;
    println!();

    // Open UART connection
    println!("Step 2: Opening UART connection...");
    let mut gd32 = GD32Connection::new("/dev/ttyS3")?;
    println!("✓ Connected\n");

    thread::sleep(Duration::from_millis(100));

    println!("========================================");
    println!("  Strategy 1: Hardware Reset + Wakeup");
    println!("========================================\n");

    // Try hardware reset
    gpio.hardware_reset()?;
    thread::sleep(Duration::from_millis(100));

    // Send wakeup acknowledgment
    println!("Sending Wakeup ACK (CMD 0x05)...");
    gd32.send_packet(&commands::wakeup_ack())?;
    thread::sleep(Duration::from_millis(200));

    // Check status
    let status = gpio.read_status()?;
    println!("GPIO-39 status: {}\n", if status { "HIGH ✓" } else { "LOW" });

    println!("========================================");
    println!("  Strategy 2: R16 Power Control");
    println!("========================================\n");

    // Try R16 power off then on
    println!("Sending R16 Power OFF (CMD 0x99)...");
    gd32.send_packet(&commands::r16_power(false))?;
    thread::sleep(Duration::from_millis(500));

    println!("Sending R16 Power ON (CMD 0x99)...");
    gd32.send_packet(&commands::r16_power(true))?;
    thread::sleep(Duration::from_millis(500));

    // Send wakeup ack after power on
    println!("Sending Wakeup ACK (CMD 0x05)...");
    gd32.send_packet(&commands::wakeup_ack())?;
    thread::sleep(Duration::from_millis(200));

    let status = gpio.read_status()?;
    println!("GPIO-39 status: {}\n", if status { "HIGH ✓" } else { "LOW" });

    println!("========================================");
    println!("  Strategy 3: Restart R16 System");
    println!("========================================\n");

    println!("Sending Restart R16 (CMD 0x9A)...");
    gd32.send_packet(&commands::restart_r16())?;
    thread::sleep(Duration::from_millis(1000));

    println!("Waiting for restart to complete...");
    thread::sleep(Duration::from_millis(1000));

    println!("Sending Wakeup ACK (CMD 0x05)...");
    gd32.send_packet(&commands::wakeup_ack())?;
    thread::sleep(Duration::from_millis(200));

    let status = gpio.read_status()?;
    println!("GPIO-39 status: {}\n", if status { "HIGH ✓" } else { "LOW" });

    println!("========================================");
    println!("  Strategy 4: Multiple Wakeup Commands");
    println!("========================================\n");

    // Send wakeup ack multiple times
    for i in 1..=5 {
        println!("Wakeup ACK attempt {}/5...", i);
        gd32.send_packet(&commands::wakeup_ack())?;
        thread::sleep(Duration::from_millis(100));

        let status = gpio.read_status()?;
        if status {
            println!("✓ GPIO-39 went HIGH! GD32 may be awake!");
            break;
        }
    }
    println!();

    println!("========================================");
    println!("  Strategy 5: Initialization Sequence");
    println!("========================================\n");

    // Try full initialization sequence
    println!("Sending Motor Velocity Init (CMD 0x66)...");
    gd32.send_packet(&commands::initialize())?;
    thread::sleep(Duration::from_millis(200));

    println!("Sending Heartbeat (CMD 0x06)...");
    gd32.send_packet(&commands::heartbeat())?;
    thread::sleep(Duration::from_millis(200));

    let status = gpio.read_status()?;
    println!("GPIO-39 status: {}\n", if status { "HIGH ✓" } else { "LOW" });

    println!("========================================");
    println!("  Strategy 6: Status Request Loop");
    println!("========================================\n");

    // Try sending status requests repeatedly
    for i in 1..=10 {
        println!("Status request {}/10...", i);
        gd32.send_packet(&commands::status_request())?;
        thread::sleep(Duration::from_millis(100));

        let status = gpio.read_status()?;
        if status {
            println!("✓ GPIO-39 went HIGH! GD32 may be awake!");
            break;
        }
    }
    println!();

    println!("========================================");
    println!("  Strategy 7: Version Request");
    println!("========================================\n");

    println!("Sending Version Request (CMD 0x07)...");
    gd32.send_packet(&commands::require_version())?;
    thread::sleep(Duration::from_millis(500));

    let status = gpio.read_status()?;
    println!("GPIO-39 status: {}\n", if status { "HIGH ✓" } else { "LOW" });

    println!("========================================");
    println!("  Strategy 8: Reset Error Code");
    println!("========================================\n");

    println!("Sending Reset Error Code (CMD 0x0A)...");
    gd32.send_packet(&commands::reset_error_code())?;
    thread::sleep(Duration::from_millis(200));

    let status = gpio.read_status()?;
    println!("GPIO-39 status: {}\n", if status { "HIGH ✓" } else { "LOW" });

    println!("========================================");
    println!("  Strategy 9: Lidar Power Toggle");
    println!("========================================\n");

    // Sometimes toggling peripherals can wake the MCU
    println!("Toggling Lidar Power...");
    gd32.send_packet(&commands::lidar_power(true))?;
    thread::sleep(Duration::from_millis(200));
    gd32.send_packet(&commands::lidar_power(false))?;
    thread::sleep(Duration::from_millis(200));

    let status = gpio.read_status()?;
    println!("GPIO-39 status: {}\n", if status { "HIGH ✓" } else { "LOW" });

    println!("========================================");
    println!("  Strategy 10: Combined Sequence");
    println!("========================================\n");

    println!("Trying combined wakeup sequence:");
    println!("  1. Hardware reset");
    gpio.hardware_reset()?;

    println!("  2. R16 Power ON");
    gd32.send_packet(&commands::r16_power(true))?;
    thread::sleep(Duration::from_millis(200));

    println!("  3. Wakeup ACK");
    gd32.send_packet(&commands::wakeup_ack())?;
    thread::sleep(Duration::from_millis(200));

    println!("  4. Reset Error Code");
    gd32.send_packet(&commands::reset_error_code())?;
    thread::sleep(Duration::from_millis(200));

    println!("  5. Initialize");
    gd32.send_packet(&commands::initialize())?;
    thread::sleep(Duration::from_millis(200));

    println!("  6. Heartbeat");
    gd32.send_packet(&commands::heartbeat())?;
    thread::sleep(Duration::from_millis(200));

    let status = gpio.read_status()?;
    println!("\nGPIO-39 status: {}\n", if status { "HIGH ✓" } else { "LOW" });

    println!("========================================");
    println!("  Final Status Check");
    println!("========================================\n");

    gpio.print_status()?;
    println!();

    println!("========================================");
    println!("  Test Motor Command");
    println!("========================================\n");

    println!("Sending motor speed command to test if GD32 is awake...");
    gd32.send_packet(&commands::motor_speed(30, 30))?;
    thread::sleep(Duration::from_millis(1000));
    gd32.send_packet(&commands::motor_speed(0, 0))?;

    println!("\nDid the motors move? If yes, GD32 is awake!");
    println!("If no, GD32 may still be asleep or needs different wakeup.");
    println!();

    println!("========================================");
    println!("  Wakeup Test Complete");
    println!("========================================\n");

    println!("Review the output above to see which strategy (if any) worked.");
    println!("Look for GPIO-39 changing to HIGH or physical motor movement.\n");

    Ok(())
}
