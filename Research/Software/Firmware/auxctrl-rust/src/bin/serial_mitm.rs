//! Serial Man-in-the-Middle Logger
//!
//! Creates a virtual serial port at /tmp/ttyS3_tap that AuxCtrl connects to.
//! This program forwards all data between the virtual port and real /dev/ttyS3,
//! while logging everything in both directions.
//!
//! Setup:
//!   1. Stop AuxCtrl: killall AuxCtrl
//!   2. Run this program: ./serial_mitm
//!   3. Create symlink: ln -sf /tmp/ttyS3_tap /dev/ttyS3_real && mv /dev/ttyS3 /dev/ttyS3_hardware && ln -s /tmp/ttyS3_tap /dev/ttyS3
//!   4. Start AuxCtrl
//!
//! Alternative simpler approach:
//!   Use socat to create the virtual port pair

use std::fs::{File, OpenOptions};
use std::io::{self, Write};
use std::os::unix::io::{AsRawFd, RawFd};
use std::time::{SystemTime, UNIX_EPOCH};
use std::thread;

const REAL_PORT: &str = "/dev/ttyS3_hardware";
const VIRTUAL_PORT: &str = "/tmp/ttyS3_tap";
const LOG_FILE: &str = "/tmp/serial_mitm.log";

fn timestamp_micros() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_micros()
}

fn log_packet(log: &mut File, direction: &str, data: &[u8]) -> io::Result<()> {
    let ts = timestamp_micros();

    writeln!(log, "[{}.{:06}] {} {} bytes",
             ts / 1_000_000, ts % 1_000_000, direction, data.len())?;

    // Hex dump
    write!(log, "  HEX: ")?;
    for byte in data {
        write!(log, "{:02X} ", byte)?;
    }
    writeln!(log)?;

    // Try to decode as GD32 packet
    if data.len() >= 2 && data[0] == 0xFA && data[1] == 0xFB {
        if data.len() >= 3 {
            let len = data[2] as usize;
            if data.len() >= len + 3 {
                let cmd = if data.len() > 3 { data[3] } else { 0 };
                writeln!(log, "  PKT: CMD=0x{:02X} LEN={}", cmd, len)?;
            }
        }
    }

    writeln!(log)?;
    log.flush()?;
    Ok(())
}

fn configure_serial(fd: RawFd) -> io::Result<()> {
    unsafe {
        let mut termios: libc::termios = std::mem::zeroed();
        if libc::tcgetattr(fd, &mut termios) != 0 {
            return Err(io::Error::last_os_error());
        }

        // Raw mode
        libc::cfmakeraw(&mut termios);

        // 115200 baud
        libc::cfsetispeed(&mut termios, libc::B115200);
        libc::cfsetospeed(&mut termios, libc::B115200);

        // 8N1
        termios.c_cflag &= !libc::PARENB;
        termios.c_cflag &= !libc::CSTOPB;
        termios.c_cflag &= !libc::CSIZE;
        termios.c_cflag |= libc::CS8;
        termios.c_cflag |= libc::CREAD | libc::CLOCAL;

        // Non-blocking
        termios.c_cc[libc::VTIME] = 0;
        termios.c_cc[libc::VMIN] = 0;

        if libc::tcsetattr(fd, libc::TCSANOW, &termios) != 0 {
            return Err(io::Error::last_os_error());
        }
    }
    Ok(())
}

fn create_pty() -> io::Result<(RawFd, String)> {
    unsafe {
        let mut master: libc::c_int = 0;
        let mut slave: libc::c_int = 0;

        if libc::openpty(&mut master, &mut slave, std::ptr::null_mut(),
                         std::ptr::null(), std::ptr::null()) != 0 {
            return Err(io::Error::last_os_error());
        }

        // Get slave name
        let mut buf: [libc::c_char; 256] = [0; 256];
        if libc::ttyname_r(slave, buf.as_mut_ptr(), buf.len()) != 0 {
            libc::close(master);
            libc::close(slave);
            return Err(io::Error::last_os_error());
        }

        let slave_name = std::ffi::CStr::from_ptr(buf.as_ptr())
            .to_string_lossy()
            .into_owned();

        libc::close(slave);

        Ok((master, slave_name))
    }
}

fn main() -> io::Result<()> {
    println!("========================================");
    println!("  Serial Man-in-the-Middle Logger");
    println!("  Real port: {}", REAL_PORT);
    println!("  Log file: {}", LOG_FILE);
    println!("========================================\n");

    // Open log file
    let mut log_file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(LOG_FILE)?;

    writeln!(log_file, "\n=== MITM Session Started ===")?;
    writeln!(log_file, "Timestamp: {}", timestamp_micros())?;
    writeln!(log_file, "Real port: {}\n", REAL_PORT)?;
    log_file.flush()?;

    // Open real serial port
    println!("Opening real serial port {}...", REAL_PORT);
    let real_serial = OpenOptions::new()
        .read(true)
        .write(true)
        .open(REAL_PORT)?;

    let real_fd = real_serial.as_raw_fd();
    configure_serial(real_fd)?;
    println!("✓ Real port opened and configured");

    // Create pseudo-terminal
    println!("Creating virtual serial port...");
    let (pty_master, pty_slave_name) = create_pty()?;
    println!("✓ Virtual port created at: {}", pty_slave_name);

    // Create symlink
    println!("Creating symlink {} -> {}", VIRTUAL_PORT, pty_slave_name);
    let _ = std::fs::remove_file(VIRTUAL_PORT);
    std::os::unix::fs::symlink(&pty_slave_name, VIRTUAL_PORT)?;
    println!("✓ Symlink created");

    println!("\nSetup complete!");
    println!("Now run: killall AuxCtrl && mv /dev/ttyS3 /dev/ttyS3_backup && ln -s {} /dev/ttyS3 && AuxCtrl", VIRTUAL_PORT);
    println!("\nPress Ctrl+C to stop and restore...\n");

    // Proxy loop
    let mut real_buf = [0u8; 1024];
    let mut pty_buf = [0u8; 1024];

    loop {
        // Check for data from AuxCtrl (via PTY) -> Real Serial
        unsafe {
            let n = libc::read(pty_master, pty_buf.as_mut_ptr() as *mut libc::c_void, pty_buf.len());
            if n > 0 {
                let n = n as usize;

                // Log TX (AuxCtrl -> GD32)
                if let Err(e) = log_packet(&mut log_file, "TX", &pty_buf[..n]) {
                    eprintln!("Log error: {}", e);
                }

                println!("TX: {} bytes", n);

                // Forward to real serial port
                let written = libc::write(real_fd, pty_buf.as_ptr() as *const libc::c_void, n);
                if written < 0 {
                    eprintln!("Error writing to real port");
                }
            }
        }

        // Check for data from Real Serial -> AuxCtrl (via PTY)
        unsafe {
            let n = libc::read(real_fd, real_buf.as_mut_ptr() as *mut libc::c_void, real_buf.len());
            if n > 0 {
                let n = n as usize;

                // Log RX (GD32 -> AuxCtrl)
                if let Err(e) = log_packet(&mut log_file, "RX", &real_buf[..n]) {
                    eprintln!("Log error: {}", e);
                }

                println!("RX: {} bytes", n);

                // Forward to PTY (AuxCtrl)
                let written = libc::write(pty_master, real_buf.as_ptr() as *const libc::c_void, n);
                if written < 0 {
                    eprintln!("Error writing to PTY");
                }
            }
        }

        // Small sleep to prevent busy-waiting
        thread::sleep(std::time::Duration::from_micros(100));
    }
}
