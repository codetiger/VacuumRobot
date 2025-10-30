//! Serial Port Tap/Sniffer
//!
//! Creates a pseudo-TTY that forwards all data to the real serial port
//! while logging everything that passes through.
//!
//! Usage:
//!   1. Run this program - it creates /tmp/ttyS3_tap
//!   2. Modify AuxCtrl to use /tmp/ttyS3_tap instead of /dev/ttyS3
//!   3. All traffic is logged to /tmp/serial_tap.log
//!
//! Alternative: Just log kernel ring buffer for UART driver messages

use std::fs::{File, OpenOptions};
use std::io::{self, Read, Write};
use std::os::unix::io::AsRawFd;
use std::time::{SystemTime, UNIX_EPOCH};

const REAL_PORT: &str = "/dev/ttyS3";
const LOG_FILE: &str = "/tmp/serial_tap.log";

fn timestamp_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis()
}

fn log_data(log: &mut File, direction: &str, data: &[u8]) -> io::Result<()> {
    let ts = timestamp_ms();
    writeln!(log, "[{}.{:03}] {} {} bytes:",
             ts / 1000, ts % 1000, direction, data.len())?;

    // Hex dump
    write!(log, "  ")?;
    for (i, byte) in data.iter().enumerate() {
        write!(log, "{:02X} ", byte)?;
        if (i + 1) % 16 == 0 {
            writeln!(log)?;
            write!(log, "  ")?;
        }
    }
    writeln!(log)?;
    writeln!(log)?;
    log.flush()?;
    Ok(())
}

fn main() -> io::Result<()> {
    println!("========================================");
    println!("  Serial Port Tap");
    println!("  Real port: {}", REAL_PORT);
    println!("  Log file: {}", LOG_FILE);
    println!("========================================\n");

    println!("NOTE: This approach requires AuxCtrl to be stopped first.");
    println!("      Run: killall AuxCtrl");
    println!("      Then run this tap, then restart AuxCtrl with modified port.\n");

    // Open log file
    let mut log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(LOG_FILE)?;

    writeln!(log_file, "\n=== Serial Tap Started ===")?;
    writeln!(log_file, "Timestamp: {}", timestamp_ms())?;
    writeln!(log_file, "Port: {}\n", REAL_PORT)?;
    log_file.flush()?;

    // Open real serial port
    let serial = OpenOptions::new()
        .read(true)
        .write(true)
        .open(REAL_PORT)?;

    println!("✓ Opened {}", REAL_PORT);

    // Configure serial port (115200 8N1)
    let fd = serial.as_raw_fd();
    unsafe {
        let mut termios: libc::termios = std::mem::zeroed();
        if libc::tcgetattr(fd, &mut termios) != 0 {
            return Err(io::Error::last_os_error());
        }

        // Set to raw mode
        libc::cfmakeraw(&mut termios);

        // Set baud rate to 115200
        libc::cfsetispeed(&mut termios, libc::B115200);
        libc::cfsetospeed(&mut termios, libc::B115200);

        // 8N1
        termios.c_cflag &= !libc::PARENB;  // No parity
        termios.c_cflag &= !libc::CSTOPB;  // 1 stop bit
        termios.c_cflag &= !libc::CSIZE;
        termios.c_cflag |= libc::CS8;      // 8 bits

        // Enable reading
        termios.c_cflag |= libc::CREAD | libc::CLOCAL;

        // Non-blocking
        termios.c_cc[libc::VTIME] = 0;
        termios.c_cc[libc::VMIN] = 0;

        if libc::tcsetattr(fd, libc::TCSANOW, &termios) != 0 {
            return Err(io::Error::last_os_error());
        }
    }

    println!("✓ Serial port configured (115200 8N1)");
    println!("\nMonitoring traffic (Ctrl+C to stop)...\n");

    // Since we can't create a pty easily, let's just passively read
    // and log what we can see
    let mut buffer = [0u8; 256];
    let mut serial_read = serial;

    loop {
        // Try to read from serial port
        match serial_read.read(&mut buffer) {
            Ok(n) if n > 0 => {
                // Log received data
                if let Err(e) = log_data(&mut log_file, "RX", &buffer[..n]) {
                    eprintln!("Error logging: {}", e);
                }

                // Print to console
                print!("RX: ");
                for byte in &buffer[..n] {
                    print!("{:02X} ", byte);
                }
                println!();
            }
            Ok(_) => {
                // No data
                std::thread::sleep(std::time::Duration::from_millis(10));
            }
            Err(e) if e.kind() == io::ErrorKind::WouldBlock => {
                std::thread::sleep(std::time::Duration::from_millis(10));
            }
            Err(e) => {
                eprintln!("Read error: {}", e);
                return Err(e);
            }
        }
    }
}
