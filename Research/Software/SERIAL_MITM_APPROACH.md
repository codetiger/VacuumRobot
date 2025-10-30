# Serial Port Man-in-the-Middle (MITM) Approach

## Overview

This document describes the approach we developed to capture bidirectional serial communication between AuxCtrl and the GD32F103 MCU without breaking timing or functionality.

## Problem Statement

**Goal**: Log all bidirectional traffic between AuxCtrl and /dev/ttyS3 (GD32 MCU) to understand the initialization sequence and protocol.

**Constraints**:
- Python not available on the device
- `strace` breaks timing and causes communication failures
- `socat` not available on the device
- Need transparent, non-intrusive logging
- Must work with existing AuxCtrl binary (no source code access)

## Solution: PTY-Based MITM Proxy in Rust

### Architecture

```
Original setup:
AuxCtrl → /dev/ttyS3 (hardware) → GD32 MCU

MITM setup:
AuxCtrl → /tmp/ttyS3_tap (virtual PTY) → serial_mitm proxy → /dev/ttyS3_hardware (real port) → GD32 MCU
                                              ↓
                                      /tmp/serial_mitm.log
```

### Implementation Details

#### 1. PTY (Pseudo-Terminal) Creation

Used `libc::openpty()` to create a pseudo-terminal pair:
- **Master side**: Controlled by the MITM proxy
- **Slave side**: Exposed as `/tmp/ttyS3_tap` for AuxCtrl to connect to

```rust
unsafe {
    let mut master: libc::c_int = 0;
    let mut slave: libc::c_int = 0;

    libc::openpty(&mut master, &mut slave,
                  std::ptr::null_mut(),
                  std::ptr::null(),
                  std::ptr::null())
}
```

**Key technical challenge**: The `ttyname_r()` function required platform-specific `libc::c_char` type instead of `u8` or `i8` for cross-compilation compatibility.

#### 2. Serial Port Configuration

Both the PTY and real serial port configured for:
- **Baud rate**: 115200
- **Mode**: 8N1 (8 data bits, no parity, 1 stop bit)
- **Flow control**: None
- **Mode**: Raw (no line processing)
- **Blocking**: Non-blocking with VMIN=0, VTIME=0

```rust
// Raw mode
libc::cfmakeraw(&mut termios);

// 115200 baud
libc::cfsetispeed(&mut termios, libc::B115200);
libc::cfsetospeed(&mut termios, libc::B115200);

// 8N1
termios.c_cflag &= !libc::PARENB;  // No parity
termios.c_cflag &= !libc::CSTOPB;  // 1 stop bit
termios.c_cflag &= !libc::CSIZE;
termios.c_cflag |= libc::CS8;      // 8 data bits
```

#### 3. Transparent Forwarding

The proxy runs a tight loop that:
1. Reads from PTY (AuxCtrl → proxy)
2. Forwards to real serial port (proxy → GD32)
3. Reads from real serial port (GD32 → proxy)
4. Forwards to PTY (proxy → AuxCtrl)
5. Logs all traffic with microsecond timestamps

```rust
loop {
    // AuxCtrl → GD32
    let n = libc::read(pty_master, pty_buf.as_mut_ptr(), pty_buf.len());
    if n > 0 {
        log_packet(&mut log_file, "TX", &pty_buf[..n]);
        libc::write(real_fd, pty_buf.as_ptr(), n);
    }

    // GD32 → AuxCtrl
    let n = libc::read(real_fd, real_buf.as_mut_ptr(), real_buf.len());
    if n > 0 {
        log_packet(&mut log_file, "RX", &real_buf[..n]);
        libc::write(pty_master, real_buf.as_ptr(), n);
    }

    thread::sleep(Duration::from_micros(100));
}
```

**Critical**: The 100µs sleep prevents busy-waiting while maintaining low latency.

#### 4. Packet Logging

Each logged entry includes:
- **Timestamp**: Microsecond precision (e.g., `[1761751538.946188]`)
- **Direction**: TX (AuxCtrl→GD32) or RX (GD32→AuxCtrl)
- **Byte count**
- **Hex dump**: All bytes in hexadecimal
- **Decoded packet**: If valid GD32 protocol packet (FA FB header)

Log format example:
```
[1761751544.235866] TX 14 bytes
  HEX: FA FB 0B 66 00 00 00 00 00 00 00 00 66 00
  PKT: CMD=0x66 LEN=11

[1761751544.236203] RX 102 bytes
  HEX: FA FB 63 15 01 06 00 0F 04 00 00 01 A6 21...
  PKT: CMD=0x15 LEN=99
```

#### 5. Device File Manipulation

To redirect AuxCtrl to the virtual port:

```bash
# 1. Stop AuxCtrl
killall AuxCtrl

# 2. Backup the real hardware port
mv /dev/ttyS3 /dev/ttyS3_hardware

# 3. Create symlink to virtual port
ln -s /tmp/ttyS3_tap /dev/ttyS3

# 4. Start MITM proxy
/tmp/serial_mitm &

# 5. Restart AuxCtrl (now connects to virtual port)
/usr/sbin/AuxCtrl &
```

## Build and Deployment

### Cross-Compilation

```bash
# Add ARM target
rustup target add armv7-unknown-linux-musleabihf

# Build for ARM
cargo build --release --target armv7-unknown-linux-musleabihf --bin serial_mitm
```

### Binary Transfer

Since the device lacks `scp`/`sftp-server`, use SSH pipe:

```bash
cat target/armv7-unknown-linux-musleabihf/release/serial_mitm | \
  sshpass -p "<your-password>" ssh root@vacuum \
  "cat > /tmp/serial_mitm && chmod +x /tmp/serial_mitm"
```

### Cargo.toml Configuration

```toml
[[bin]]
name = "serial_mitm"
path = "src/bin/serial_mitm.rs"

[dependencies]
libc = "0.2"
```

## Results

### Captured Data Statistics

From a Return2Dock operation:
- **Duration**: ~160 seconds
- **Total lines**: 91,718
- **Log size**: 4.2 MB
- **Packets captured**: Thousands of CMD=0x15 status packets and CMD=0x66 heartbeats

### Key Discoveries

1. **Initialization sequence**: Repeated CMD=0x08 packets (99 bytes) sent every ~200ms for 5 seconds
2. **Bidirectional communication**: GD32 DOES respond (contrary to initial assumptions)
3. **Status packets**: CMD=0x15 (99 bytes) contains sensor data, IMU values, encoders, battery status
4. **Heartbeat frequency**: CMD=0x66 sent every 20-50ms
5. **Version info**: Retrieved via CMD=0x07, response includes "2.0.1_19082728"

### PTY Escape Encoding Observation

The PTY implementation uses escape sequences:
- `0x5E` (`^`) is the escape character
- `0x00` becomes `5E 40` (`^@`)
- `0x0C` becomes `5E 4C` (`^L`)

This is an artifact of the PTY layer and doesn't affect the actual protocol on the hardware serial port.

## Advantages of This Approach

1. **No timing disruption**: Unlike `strace`, doesn't interfere with syscalls
2. **Transparent**: AuxCtrl operates normally, unaware of the MITM
3. **Complete capture**: Both TX and RX with precise timestamps
4. **No dependencies**: Pure Rust with only `libc`, no external tools needed
5. **Small binary**: ~334 KB stripped release build
6. **Protocol-agnostic**: Works with any serial protocol, not GD32-specific

## Limitations

1. **Requires device file manipulation**: Need root access to move/symlink `/dev/ttyS3`
2. **Manual restoration**: Must restore original setup after capture
3. **PTY escape encoding**: Adds visual noise to logs (though doesn't affect actual communication)
4. **Single session**: Each MITM session requires stopping/starting AuxCtrl

## Restoration Process

To restore the robot to normal operation:

```bash
# 1. Stop MITM proxy and AuxCtrl
killall serial_mitm AuxCtrl

# 2. Restore original device file (or reboot)
rm /dev/ttyS3
mv /dev/ttyS3_hardware /dev/ttyS3

# 3. Restart AuxCtrl
/usr/sbin/AuxCtrl &

# OR simply reboot to restore everything
sync && reboot
```

## Alternative Approaches Considered

### 1. `socat` - Not Available
```bash
socat -d -d \
  pty,raw,echo=0,link=/tmp/vserial \
  open:/dev/ttyS3,b115200,raw,echo=0 \
  2>&1 | tee /tmp/serial.log
```
**Rejected**: Not installed on device, would require cross-compilation

### 2. `strace` - Breaks Timing
```bash
strace -p $(pidof AuxCtrl) -e write,read -s 200
```
**Rejected**: Syscall tracing introduces delays that break real-time communication

### 3. Kernel UART Debug - Insufficient Detail
```bash
echo 8 > /proc/sys/kernel/printk
dmesg -w | grep -i 'uart\|ttyS3'
```
**Rejected**: Only logs kernel-level events, not application data

### 4. Hardware Logic Analyzer - Not Available
**Rejected**: Requires physical access to UART TX/RX lines and specialized hardware

## Source Code

The complete implementation is in:
- **`src/bin/serial_mitm.rs`** - Main MITM proxy
- **Cargo.toml** - Build configuration

## References

- POSIX PTY: `man openpty`
- Linux termios: `man termios`
- GD32 Protocol: `Research/GD32F1/A33-GD32-Protocol.md`
- Captured logs: `./return2dock_capture.log`

## Success Metrics

- ✅ Zero communication errors during 160+ second capture
- ✅ Robot operated normally (completed Return2Dock)
- ✅ Both TX and RX fully captured
- ✅ Discovered complete initialization sequence
- ✅ Successfully reproduced initialization in Rust firmware
- ✅ GD32 now responds to our custom Rust implementation

This approach proved essential for reverse-engineering the protocol and enabled successful custom firmware development.
