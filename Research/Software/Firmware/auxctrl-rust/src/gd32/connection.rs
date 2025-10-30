//! GD32 Serial Connection Handler
//!
//! Manages bidirectional serial port communication with the GD32F103 MCU.
//! GD32 responds with CMD=0x15 status packets (99 bytes) containing sensor data.

use super::packet::GD32Packet;
use serialport::SerialPort;
use std::io::{self, Read, Write};
use std::time::Duration;

/// GD32 serial connection
pub struct GD32Connection {
    port: Box<dyn SerialPort>,
}

impl GD32Connection {
    /// Open connection to GD32 on specified serial port
    ///
    /// # Arguments
    /// * `port_path` - Serial port path (e.g., "/dev/ttyS3")
    ///
    /// # Example
    /// ```no_run
    /// use auxctrl_rust::gd32::GD32Connection;
    ///
    /// let mut conn = GD32Connection::new("/dev/ttyS3")?;
    /// # Ok::<(), std::io::Error>(())
    /// ```
    pub fn new(port_path: &str) -> io::Result<Self> {
        println!("Opening {} at 115200 baud...", port_path);

        let port = serialport::new(port_path, 115200)
            .timeout(Duration::from_millis(10))
            .open()
            .map_err(|e| io::Error::new(io::ErrorKind::Other, format!("Failed to open port: {}", e)))?;

        println!("✓ Port opened successfully");

        Ok(Self { port })
    }

    /// Send a packet to GD32
    ///
    /// # Arguments
    /// * `packet` - The packet to send
    ///
    /// # Returns
    /// Number of bytes written
    pub fn send_packet(&mut self, packet: &GD32Packet) -> io::Result<usize> {
        let bytes = packet.encode();

        // Debug output
        print!("TX: ");
        for byte in &bytes {
            print!("{:02X} ", byte);
        }
        println!();

        // Write to serial port
        let written = self.port.write(&bytes)?;
        self.port.flush()?;

        if written != bytes.len() {
            return Err(io::Error::new(
                io::ErrorKind::WriteZero,
                format!("Incomplete write: {} of {} bytes", written, bytes.len())
            ));
        }

        Ok(written)
    }

    /// Send raw bytes to GD32 (for debugging)
    pub fn send_raw(&mut self, bytes: &[u8]) -> io::Result<usize> {
        print!("TX (raw): ");
        for byte in bytes {
            print!("{:02X} ", byte);
        }
        println!();

        let written = self.port.write(bytes)?;
        self.port.flush()?;
        Ok(written)
    }

    /// Try to read response from GD32 (non-blocking)
    ///
    /// Returns the number of bytes read and the data.
    /// Returns Ok(0, vec![]) if no data available.
    pub fn try_read(&mut self) -> io::Result<(usize, Vec<u8>)> {
        let mut buf = vec![0u8; 512];

        match self.port.read(&mut buf) {
            Ok(n) if n > 0 => {
                buf.truncate(n);

                // Debug output
                print!("RX: ");
                for byte in &buf[..n] {
                    print!("{:02X} ", byte);
                }
                println!();

                Ok((n, buf))
            }
            Ok(_) => Ok((0, vec![])),
            Err(ref e) if e.kind() == io::ErrorKind::TimedOut => Ok((0, vec![])),
            Err(e) => Err(e),
        }
    }

    /// Read and wait for a specific amount of data
    ///
    /// Blocks until the requested number of bytes is received or timeout.
    pub fn read_exact(&mut self, len: usize) -> io::Result<Vec<u8>> {
        let mut buf = vec![0u8; len];
        self.port.read_exact(&mut buf)?;

        print!("RX: ");
        for byte in &buf {
            print!("{:02X} ", byte);
        }
        println!();

        Ok(buf)
    }

    /// Get the underlying serial port (for advanced use)
    pub fn port_mut(&mut self) -> &mut Box<dyn SerialPort> {
        &mut self.port
    }
}

impl Drop for GD32Connection {
    fn drop(&mut self) {
        println!("Closing GD32 connection...");
    }
}
