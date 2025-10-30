# Sensor Architecture Analysis

## The Question

"If the GD32 only receives commands and gives status back via GPIO, how does the A33 read sensor information from bumpers, buttons, IR sensors, and ground clearance sensors?"

## Answer: Multi-Channel Architecture

The vacuum robot uses a **distributed sensor architecture** where sensors are divided between:
1. **Real-time safety sensors** → handled by GD32
2. **Navigation sensors** → handled directly by A33
3. **Status sensors** → simple GPIO or ADC

## Detailed Breakdown

### 1. GD32-Connected Sensors (Real-Time Processing)

**Connectors J25 & J26** (16-pin each):
- Left/Right wheel encoders
- Left/Right side fall detect IR (cliff sensors)
- Left/Right hit detect sensors (bumpers)
- Sweeper motor control
- Dustbox power

**Why GD32 Handles These:**
- **Real-time requirements**: Motor control needs microsecond-level encoder feedback
- **Safety critical**: Cliff detection must immediately stop motors
- **Interrupt-driven**: Bumper hits need instant response
- **PWM generation**: Motor speed control requires hardware timers

**How A33 Gets This Data:**
The GD32 processes these sensors locally and provides **high-level status** to A33:
- **GPIO status line** (gpio-39 / PB7): Binary status (obstacle detected, cliff detected, etc.)
- **Command-based polling**: A33 may send query commands and GD32 might encode status in future UART responses (not currently implemented)
- **Autonomous operation**: GD32 handles emergency stops without waiting for A33

### 2. A33-Connected Sensors (Direct Connection)

#### Lidar (J17 - 5 pins)
- **Connection**: UART1 (ttyS1) via PG6/PG7 (with hardware flow control PG8/PG9)
- **Protocol**: Custom serial protocol at 115200 baud
- **Purpose**: 360° distance measurements for SLAM/mapping
- **Evidence**: We have working `scan.py` that reads from `/dev/ttyS1`

#### Simple Status Sensors
Likely connected directly to A33 GPIO or ADC:
- **Dust box sensor** (J48): Detect if dust container installed
- **Water box detector** (J48): Detect if mop attachment installed
- **Mop pad sensor** (J34): Detect if mop pad attached
- **Buttons**: Power, home, spot clean buttons

**Why A33 Handles These:**
- Not time-critical
- Simple on/off detection
- Can be polled at low frequency (10-100 Hz)
- No safety implications if delayed

### 3. Communication Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      Allwinner A33                           │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │   Lidar     │  │  Status      │  │   GD32 Control      │  │
│  │  (UART1)    │  │  Sensors     │  │   (UART3)           │  │
│  │  ttyS1      │  │  (GPIO/ADC)  │  │   ttyS3             │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────────────┘  │
│         │                │                 │                 │
└─────────┼────────────────┼─────────────────┼─────────────────┘
          │                │                 │
          │                │                 │ Commands only
          ↓                ↓                 ↓ (one-way UART)
    ┌─────────┐      ┌──────────┐     ┌──────────────────────┐
    │  Lidar  │      │  Dust    │     │   GD32 MCU           │
    │  Sensor │      │  Water   │     │                      │
    │ (J17)   │      │  Mop     │     │  ┌────────────────┐  │
    └─────────┘      │  Buttons │     │  │ Motor Control  │  │
                     └──────────┘     │  │ + Encoder      │  │
                                      │  └────────────────┘  │
                                      │  ┌────────────────┐  │
                                      │  │ Cliff Sensors  │  │
                                      │  │ (Fall Detect)  │  │
                                      │  └────────────────┘  │
                                      │  ┌────────────────┐  │
                                      │  │ Bumper Sensors │  │
                                      │  │ (Hit Detect)   │  │
                                      │  └────────────────┘  │
                                      │         │            │
                                      └─────────┼────────────┘
                                                │
                                                │ Status GPIO
                                                ↓
                                      A33 PB7 (gpio-39)
```

## Evidence from Analysis

### 1. UART Ports Usage
From kernel pinmux analysis:
```
UART0 (ttyS0): PF2, PF4 - Debug/console secondary?
UART1 (ttyS1): PG6, PG7, PG8, PG9 - Lidar (confirmed working)
UART2 (ttyS2): PB0, PB1 - Main console
UART3 (ttyS3): PH6, PH7 - GD32 commands (TX only used)
```

### 2. strace Evidence
```
- FD 4 (/dev/ttyS3): Write-only, sends commands to GD32
- FD 5 (/dev/ttyS1): Monitored with select(), likely Lidar data
- 0 reads from FD 4: Confirms GD32 doesn't send UART responses
```

### 3. GPIO Evidence
```
gpio-39 (PB7):   INPUT,  LOW  - Status from GD32
gpio-107 (PD11): OUTPUT, HIGH - Enable/power to GD32
gpio-233 (PH9):  OUTPUT, HIGH - Reset/boot control for GD32
```

## Sensor Data Flow Models

### Model A: Pure One-Way + GPIO Status (Current Evidence)
```
A33 → [UART CMD] → GD32
A33 ← [GPIO bit] ← GD32
```
- A33 sends motor commands
- GD32 executes and monitors sensors
- GD32 sets GPIO high/low for critical events only
- A33 polls GPIO at high frequency

**Limitations**: Only 1-bit of information per GPIO line

### Model B: Command-Response (Future/Undiscovered)
```
A33 → [UART CMD 0x66 + query] → GD32
A33 ← [Embedded status in cmd?] ← GD32
```
- Maybe sensor data is encoded in the CMD 0x66 packet data?
- The 8 data bytes could contain bit-packed sensor states
- Not UART responses, but "echo back" in future commands

### Model C: Interrupt-Driven (Likely for Safety)
```
A33 ← [GPIO pulse/interrupt] ← GD32
```
- gpio-39 might trigger interrupts on edge
- GD32 pulses the line when bumper hit or cliff detected
- A33 interrupt handler immediately sends stop command

## Hypothesis: The Real Architecture

**Most Likely Scenario:**

1. **GD32 operates autonomously** for motor control:
   - Reads encoders continuously
   - Adjusts motor speeds via PID control
   - Monitors cliff/bumper sensors
   - Executes emergency stops independently

2. **A33 sends high-level commands**:
   - "Move forward at 0.5 m/s"
   - "Turn left 90 degrees"
   - "Stop"

3. **GD32 reports minimal status**:
   - gpio-39 LOW = Normal operation
   - gpio-39 HIGH = Obstacle/cliff detected (motors stopped)
   - Or vice versa (depends on active high/low)

4. **A33 handles navigation**:
   - Reads Lidar from UART1
   - Creates map using SLAM
   - Plans path
   - Sends waypoint commands to GD32

## Testing Strategy to Confirm

### Test 1: Monitor gpio-39 During Operation
```bash
# Watch for changes while running motors
watch -n 0.1 'cat /sys/class/gpio/gpio39/value'
```

### Test 2: Monitor ttyS1 for Lidar Data
```bash
# Capture Lidar data
dd if=/dev/ttyS1 bs=1 count=1000 | hexdump -C
```

### Test 3: Send Motor Commands and Observe
```bash
# Send CMD 0x66 with different data bytes
# Observe if motors respond
# Monitor gpio-39 for status changes
```

### Test 4: Check Kernel Logs for Interrupts
```bash
# See if gpio-39 is registered as interrupt
cat /proc/interrupts | grep -i gpio
```

## Conclusion

**The GD32 does NOT send sensor data over UART to the A33.**

Instead, the architecture uses:
1. **GD32 autonomous operation** - handles real-time sensors and motor control locally
2. **GPIO status signaling** - reports critical events (obstacles, cliffs) via gpio-39
3. **Direct A33 connections** - Lidar and status sensors bypass GD32 entirely
4. **Command-only UART** - A33 sends high-level motion commands to GD32

This is a classic **distributed embedded system architecture** where:
- **Real-time MCU (GD32)**: Handles deterministic tasks (motor control, safety sensors)
- **Application processor (A33)**: Handles complex tasks (navigation, Wi-Fi, UI)
- **Minimal coupling**: Only high-level commands and status flags exchanged

The key insight is that **the A33 doesn't need detailed sensor data from GD32** - it only needs to know "can I move?" or "obstacle detected". The GD32 handles all the low-level details autonomously.
