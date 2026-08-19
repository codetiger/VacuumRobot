//! AuxCtrl-Rust Test Program
//!
//! Tests GD32 communication by sending initialization, heartbeat,
//! and basic control commands with GPIO-based wakeup sequences.

use auxctrl_rust::gd32::{commands, GD32Connection, GD32GPIO};
use std::{thread, time::Duration};

fn main() -> std::io::Result<()> {
    println!("========================================");
    println!("  AuxCtrl-Rust: GD32 Communication Test");
    println!("  With GPIO Control & Wakeup Sequences");
    println!("========================================\n");

    // Step 1: Initialize GPIO control
    println!("Step 1: Initializing GPIO control...");
    let gpio = GD32GPIO::new();
    gpio.initialize()?;
    gpio.print_status()?;
    println!("✓ GPIO initialized\n");

    thread::sleep(Duration::from_millis(100));

    // Step 2: Perform hardware reset
    println!("Step 2: Performing GD32 hardware reset via GPIO...");
    gpio.hardware_reset()?;
    gpio.print_status()?;
    println!("✓ Hardware reset complete\n");

    thread::sleep(Duration::from_millis(100));

    // Step 3: Open UART connection
    println!("Step 3: Opening GD32 UART connection...");
    let mut gd32 = GD32Connection::new("/dev/ttyS3")?;
    println!("✓ Connected to /dev/ttyS3\n");

    thread::sleep(Duration::from_millis(100));

    // Step 4: Try wakeup acknowledgment
    println!("Step 4: Sending wakeup acknowledgment (CMD 0x05)...");
    gd32.send_packet(&commands::wakeup_ack())?;
    println!("✓ Wakeup ACK sent\n");

    thread::sleep(Duration::from_millis(200));

    // Check status after wakeup
    let status = gpio.read_status()?;
    println!("  GD32 status pin: {}\n", if status { "HIGH" } else { "LOW" });

    // Step 5: Send initialization command
    println!("Step 5: Sending initialization command (CMD 0x08)...");
    gd32.send_packet(&commands::init_cmd_0x08())?;
    println!("✓ Initialization sent\n");

    thread::sleep(Duration::from_millis(500));

    // Step 6: Send heartbeat
    println!("Step 6: Sending heartbeat (CMD 0x06)...");
    gd32.send_packet(&commands::heartbeat())?;
    println!("✓ Heartbeat sent\n");

    thread::sleep(Duration::from_millis(100));

    // Step 7: Try lidar power on
    println!("Step 7: Turning on lidar motor (CMD 0x97)...");
    gd32.send_packet(&commands::lidar_power(true))?;
    println!("✓ Lidar power ON command sent\n");

    thread::sleep(Duration::from_millis(500));

    // Check status after lidar command
    let status = gpio.read_status()?;
    println!("  GD32 status pin: {}\n", if status { "HIGH" } else { "LOW" });

    // Step 8: Send periodic heartbeats
    println!("Step 8: Sending periodic heartbeats...");
    for i in 1..=5 {
        gd32.send_packet(&commands::heartbeat())?;
        println!("  Heartbeat {}/5", i);
        thread::sleep(Duration::from_millis(200));
    }
    println!("✓ Heartbeats complete\n");

    // Step 9: Try motor command
    println!("Step 9: Testing motor speed command (CMD 0x67)...");
    gd32.send_packet(&commands::motor_speed(50, 50))?;
    println!("✓ Motor speed command sent (50, 50)\n");

    thread::sleep(Duration::from_millis(1000));

    // Step 10: Stop motors
    println!("Step 10: Stopping motors...");
    gd32.send_packet(&commands::motor_speed(0, 0))?;
    println!("✓ Motors stopped\n");

    thread::sleep(Duration::from_millis(100));

    // Step 11: Turn off lidar
    println!("Step 11: Turning off lidar motor...");
    gd32.send_packet(&commands::lidar_power(false))?;
    println!("✓ Lidar power OFF command sent\n");

    // Final GPIO status check
    println!("========================================");
    println!("  Test Complete!");
    println!("========================================\n");

    println!("Final GPIO Status:");
    gpio.print_status()?;
    println!();

    println!("What to check:");
    println!("  1. Did the lidar motor start spinning? (Step 7)");
    println!("  2. Did the wheels move? (Step 9)");
    println!("  3. Did GPIO-39 (status) change during operation?");
    println!("  4. Check kernel log: dmesg | tail -20");
    println!();

    println!("If GD32 still doesn't respond:");
    println!("  - Try running original AuxCtrl to compare GPIO states");
    println!("  - Check if gpio-107 needs to be toggled");
    println!("  - Monitor gpio-39 for changes during operation");
    println!();

    Ok(())
}
