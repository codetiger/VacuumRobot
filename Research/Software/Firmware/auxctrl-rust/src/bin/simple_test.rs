//! Simple GD32 Communication Test
//!
//! Sends a few safe commands to test if GD32 responds.
//! Does NOT perform any wakeup or reset operations.

use auxctrl_rust::gd32::{commands, GD32Connection};
use std::{thread, time::Duration};

fn main() -> std::io::Result<()> {
    println!("========================================");
    println!("  Simple GD32 Communication Test");
    println!("  Testing basic commands only");
    println!("========================================\n");

    // Open UART connection (no GPIO manipulation)
    println!("Opening GD32 UART connection on /dev/ttyS3...");
    let mut gd32 = GD32Connection::new("/dev/ttyS3")?;
    println!("✓ Connected\n");

    thread::sleep(Duration::from_millis(100));

    // Test 1: Send heartbeat
    println!("Test 1: Sending heartbeat (CMD 0x06)...");
    gd32.send_packet(&commands::heartbeat())?;
    println!("✓ Heartbeat sent");
    thread::sleep(Duration::from_millis(500));

    // Test 2: Send another heartbeat
    println!("\nTest 2: Sending second heartbeat...");
    gd32.send_packet(&commands::heartbeat())?;
    println!("✓ Second heartbeat sent");
    thread::sleep(Duration::from_millis(500));

    // Test 3: Request version
    println!("\nTest 3: Requesting version (CMD 0x07)...");
    gd32.send_packet(&commands::require_version())?;
    println!("✓ Version request sent");
    thread::sleep(Duration::from_millis(500));

    // Test 4: Request status
    println!("\nTest 4: Requesting status (CMD 0x0D)...");
    gd32.send_packet(&commands::status_request())?;
    println!("✓ Status request sent");
    thread::sleep(Duration::from_millis(500));

    // Test 5: Send one more heartbeat
    println!("\nTest 5: Final heartbeat...");
    gd32.send_packet(&commands::heartbeat())?;
    println!("✓ Final heartbeat sent");
    thread::sleep(Duration::from_millis(200));

    println!("\n========================================");
    println!("  Test Complete");
    println!("========================================\n");

    println!("Check the following to see if GD32 responded:");
    println!("  1. AuxCtrl logs: tail /mnt/UDISK/log/AuxCtrl.temp");
    println!("  2. Kernel logs: dmesg | tail -20");
    println!("  3. Did the robot make any sounds or movements?");
    println!("\nIf there are no errors, the GD32 accepted our commands!\n");

    Ok(())
}
