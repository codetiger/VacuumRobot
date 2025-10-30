//! GD32 Initialization Test
//!
//! Tests the proper initialization sequence discovered from log analysis.
//! This implements the exact sequence that AuxCtrl uses to wake up the GD32.

use auxctrl_rust::gd32::{commands, GD32Connection};
use std::io;
use std::thread;
use std::time::Duration;

fn main() -> io::Result<()> {
    println!("========================================");
    println!("  GD32 Initialization Test");
    println!("  Following discovered init sequence");
    println!("========================================\n");

    // Open connection
    println!("Opening /dev/ttyS3...");
    let mut gd32 = GD32Connection::new("/dev/ttyS3")?;
    println!("✓ Connected\n");

    // Phase 1: Send repeated CMD=0x08 initialization packets
    println!("PHASE 1: Sending CMD=0x08 initialization packets...");
    let init_packet = commands::init_cmd_0x08();

    let mut got_response = false;
    for i in 0..25 {
        println!("[{}] Sending CMD=0x08 (init)...", i + 1);
        gd32.send_packet(&init_packet)?;

        // Wait 200ms
        thread::sleep(Duration::from_millis(200));

        // Try to read response
        match gd32.try_read() {
            Ok((n, data)) if n > 0 => {
                println!("  ✓ Got response! {} bytes", n);

                // Check if it's a CMD=0x15 status packet
                if data.len() >= 4 && data[0] == 0xFA && data[1] == 0xFB && data[3] == 0x15 {
                    println!("  ✓ Detected CMD=0x15 status response!");
                    got_response = true;
                    break;
                }
            }
            Ok(_) => {
                // No response yet
                print!(".");
            }
            Err(e) => {
                eprintln!("  Error reading: {}", e);
            }
        }
    }

    if !got_response {
        println!("\n⚠ Warning: No CMD=0x15 response detected after 25 attempts");
        println!("Continuing anyway...\n");
    } else {
        println!("\n✓ GD32 is responding!\n");
    }

    // Phase 2: Send CMD=0x07 (get version)
    println!("PHASE 2: Requesting firmware version (CMD=0x07)...");
    gd32.send_packet(&commands::get_version())?;
    thread::sleep(Duration::from_millis(50));

    if let Ok((n, data)) = gd32.try_read() {
        if n > 0 {
            println!("  Response: {} bytes", n);

            // Look for version string
            if let Some(pos) = data.windows(8).position(|w| w.starts_with(b"2.0.")) {
                let version = String::from_utf8_lossy(&data[pos..pos.min(data.len()).min(pos + 20)]);
                println!("  ✓ Version: {}", version);
            }
        }
    }
    println!();

    // Phase 3: Send CMD=0x06 (wake/enable)
    println!("PHASE 3: Sending wake command (CMD=0x06)...");
    gd32.send_packet(&commands::wake())?;
    thread::sleep(Duration::from_millis(50));

    if let Ok((n, _)) = gd32.try_read() {
        if n > 0 {
            println!("  ✓ Got {} byte response", n);
        }
    }
    println!();

    // Phase 4: Send CMD=0x8D (set control mode)
    println!("PHASE 4: Setting control mode (CMD=0x8D)...");
    gd32.send_packet(&commands::set_control_mode(0x01))?;
    thread::sleep(Duration::from_millis(50));

    if let Ok((n, _)) = gd32.try_read() {
        if n > 0 {
            println!("  ✓ Got {} byte response", n);
        }
    }
    println!();

    // Phase 5: Enter heartbeat loop
    println!("PHASE 5: Starting heartbeat loop (CMD=0x66)...");
    println!("Will send 50 heartbeats with 20ms interval...\n");

    let heartbeat = commands::heartbeat();
    let mut status_count = 0;

    for i in 0..50 {
        gd32.send_packet(&heartbeat)?;

        // Wait 20ms
        thread::sleep(Duration::from_millis(20));

        // Try to read CMD=0x15 status response
        if let Ok((n, data)) = gd32.try_read() {
            if n > 0 {
                // Check if it's CMD=0x15 status packet (should be 102 bytes total: FA FB 63 15 ...)
                if data.len() >= 4 && data[0] == 0xFA && data[1] == 0xFB && data[3] == 0x15 {
                    status_count += 1;
                    if status_count % 10 == 0 {
                        println!("[Beat {}] ✓ Received {} CMD=0x15 status packets so far", i + 1, status_count);
                    }
                }
            }
        }
    }

    println!("\n========================================");
    println!("  Test Complete!");
    println!("  Received {} CMD=0x15 status packets", status_count);

    if status_count > 0 {
        println!("  ✓ SUCCESS: GD32 is responding to our commands!");
    } else {
        println!("  ⚠ WARNING: No status packets received");
    }
    println!("========================================");

    Ok(())
}
