//! Serial Port Logger
//!
//! Passively monitors /dev/ttyS3 to capture GD32 communication
//! without interfering with AuxCtrl timing.
//!
//! Strategy: Opens the port in read-only mode and logs all data.
//! This won't interfere with AuxCtrl's write operations.

use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};
use std::time::{SystemTime, UNIX_EPOCH};

const SERIAL_PORT: &str = "/dev/ttyS3";
const LOG_FILE: &str = "/tmp/serial_capture.log";
const BUFFER_SIZE: usize = 256;

fn timestamp_micros() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_micros()
}

fn log_packet(log: &mut File, timestamp: u128, data: &[u8]) -> io::Result<()> {
    // Write timestamp
    writeln!(log, "[{}.{:06}] RX {} bytes:",
             timestamp / 1_000_000,
             timestamp % 1_000_000,
             data.len())?;

    // Write hex dump
    write!(log, "  HEX: ")?;
    for byte in data {
        write!(log, "{:02X} ", byte)?;
    }
    writeln!(log)?;

    // Write ASCII representation
    write!(log, "  ASC: ")?;
    for byte in data {
        if *byte >= 32 && *byte < 127 {
            write!(log, " {} ", *byte as char)?;
        } else {
            write!(log, " . ")?;
        }
    }
    writeln!(log)?;
    writeln!(log)?;

    log.flush()?;
    Ok(())
}

fn main() -> io::Result<()> {
    println!("========================================");
    println!("  Serial Port Logger");
    println!("  Monitoring: {}", SERIAL_PORT);
    println!("  Log file: {}", LOG_FILE);
    println!("========================================\n");

    // Open log file
    let mut log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(LOG_FILE)?;

    writeln!(log_file, "\n=== Serial Logger Started ===")?;
    writeln!(log_file, "Timestamp: {}", timestamp_micros())?;
    writeln!(log_file, "Port: {}\n", SERIAL_PORT)?;
    log_file.flush()?;

    println!("✓ Log file opened");

    // Try to open serial port in read-only mode
    println!("Opening {} in read-only mode...", SERIAL_PORT);

    let mut serial = match OpenOptions::new()
        .read(true)
        .open(SERIAL_PORT)
    {
        Ok(file) => {
            println!("✓ Serial port opened successfully");
            println!("\nMonitoring serial traffic (Ctrl+C to stop)...\n");
            file
        }
        Err(e) => {
            eprintln!("✗ Failed to open serial port: {}", e);
            eprintln!("\nNote: Serial port may be locked by AuxCtrl.");
            eprintln!("This is expected if AuxCtrl opened it exclusively.");
            return Err(e);
        }
    };

    // Read and log data
    let mut buffer = [0u8; BUFFER_SIZE];
    let mut packet_count = 0;

    loop {
        match serial.read(&mut buffer) {
            Ok(0) => {
                // EOF - shouldn't happen with serial port
                println!("EOF reached on serial port");
                break;
            }
            Ok(n) => {
                packet_count += 1;
                let timestamp = timestamp_micros();

                // Log to file
                if let Err(e) = log_packet(&mut log_file, timestamp, &buffer[..n]) {
                    eprintln!("Error writing to log: {}", e);
                }

                // Print to console
                print!("[{}] RX {} bytes: ", packet_count, n);
                for byte in &buffer[..n] {
                    print!("{:02X} ", byte);
                }
                println!();
            }
            Err(e) if e.kind() == io::ErrorKind::WouldBlock => {
                // Non-blocking read, no data available
                std::thread::sleep(std::time::Duration::from_millis(10));
            }
            Err(e) => {
                eprintln!("Error reading from serial port: {}", e);
                return Err(e);
            }
        }
    }

    println!("\nLogger stopped. Total packets captured: {}", packet_count);
    println!("Log saved to: {}", LOG_FILE);

    Ok(())
}
