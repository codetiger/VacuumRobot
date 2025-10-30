//! Heartbeat Logger
//!
//! Sends periodic heartbeat commands while logging ALL serial traffic.
//! This replaces AuxCtrl temporarily to capture the communication.

use auxctrl_rust::gd32::{commands, GD32Connection};
use std::fs::OpenOptions;
use std::io::{self, Write};
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use std::thread;

const LOG_FILE: &str = "/tmp/heartbeat_capture.log";
const HEARTBEAT_INTERVAL_MS: u64 = 200; // 200ms = 5Hz

fn timestamp_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis()
}

fn main() -> io::Result<()> {
    println!("========================================");
    println!("  GD32 Heartbeat Logger");
    println!("  Sends heartbeats while capturing traffic");
    println!("========================================\n");

    // Open log file
    let mut log = OpenOptions::new()
        .create(true)
        .append(true)
        .open(LOG_FILE)?;

    writeln!(log, "\n=== Heartbeat Logger Session ===")?;
    writeln!(log, "Start time: {}\n", timestamp_ms())?;
    log.flush()?;

    println!("Opening /dev/ttyS3...");
    let mut gd32 = GD32Connection::new("/dev/ttyS3")?;
    println!("✓ Connected\n");

    println!("Sending heartbeats every {}ms...", HEARTBEAT_INTERVAL_MS);
    println!("Press Ctrl+C to stop\n");

    let mut count = 0;

    loop {
        count += 1;
        let ts = timestamp_ms();

        // Create heartbeat packet
        let packet = commands::heartbeat();

        // Log what we're sending
        writeln!(log, "[{}.{:03}] TX Heartbeat #{}: {:02X?}",
                 ts / 1000, ts % 1000, count, packet)?;
        log.flush()?;

        // Send it
        if let Err(e) = gd32.send_packet(&packet) {
            eprintln!("Error sending: {}", e);
            writeln!(log, "ERROR: {}", e)?;
            log.flush()?;
        } else {
            println!("[{}] Sent heartbeat #{}", count, count);
        }

        // Wait
        thread::sleep(Duration::from_millis(HEARTBEAT_INTERVAL_MS));

        // Try to read response (if any)
        // Note: Our current GD32Connection doesn't have read support,
        // but we can add it or just log what we send
    }
}
