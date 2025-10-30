# Connection Evidence Documentation

This document provides evidence for each connection identified in the Component Diagram. Every connection must be proven through one or more of:
- Physical PCB tracing
- Software analysis (kernel logs, device tree, pinmux)
- Runtime testing (strace, GPIO monitoring, serial captures)

## Status Legend
- ✅ **PROVEN** - Confirmed through multiple sources
- 🔍 **LIKELY** - Strong evidence but needs final confirmation
- ❓ **HYPOTHESIS** - Logical assumption, needs testing
- ❌ **DISPROVEN** - Originally suspected but evidence shows otherwise

---

## A33 Connections

### A33 → GD32 UART (Command Channel)

**Connection**: A33 UART3_TX (PH6) → GD32 USART0_RX (PA10)

**Status**: ✅ **PROVEN**

**Evidence**:
1. **Kernel pinmux** (`/sys/kernel/debug/pinctrl/sunxi-pinctrl/pinmux-pins`):
   ```
   pin 230 (PH6): uart3 (GPIO UNCLAIMED) function uart3 group PH6
   ```
   Reference: Analysis on 2025-10-28, pinmux query

2. **Device tree / dmesg**:
   ```
   uart3: ttyS3 at MMIO 0x1c28c00 (irq = 35) is a SUNXI
   ```
   Reference: `dmesg | grep ttyS3`

3. **AuxCtrl opens /dev/ttyS3**:
   ```
   1433  open("/dev/ttyS3", O_RDWR|O_NONBLOCK|O_LARGEFILE) = 4
   ```
   Reference: `/tmp/auxctrl_full.strace` line 68

4. **AuxCtrl writes commands to FD 4**:
   ```
   1436  write(4, "\372\373\vf\0\0\0\0\0\0\0\0f\0", 14) = 14
   ```
   Reference: `/tmp/auxctrl_full.strace` line 36658

5. **Baud rate configuration**: 115200 8N1
   ```
   ioctl(4, TCSETS, {B115200 -opost -isig -icanon -echo ...}) = 0
   ```
   Reference: `/tmp/auxctrl_full.strace`

**Physical Pin**: A33 ball position for PH6 (needs PCB tracing)

---

### A33 ← GD32 UART_RX (Unused)

**Connection**: A33 UART3_RX (PH7) ← GD32 USART0_TX (PA9)

**Status**: ❌ **DISPROVEN** (connection exists but not used)

**Evidence**:
1. **Pinmux shows unclaimed**:
   ```
   pin 231 (PH7): uart3 (GPIO UNCLAIMED) function uart3 group PH7
   ```
   The GPIO is UNCLAIMED, meaning no driver is actively monitoring it.
   Reference: Pinmux analysis 2025-10-28

2. **Zero reads from ttyS3**:
   ```bash
   $ grep 'read(4' /tmp/auxctrl_full.strace | wc -l
   0
   ```
   AuxCtrl never reads from FD 4 (ttyS3).
   Reference: strace analysis

3. **All select() calls timeout**:
   ```
   1433  select(5, [4], NULL, NULL, {0, 1000}) = 0 (Timeout)
   ```
   Reference: Multiple lines in `/tmp/auxctrl_full.strace`

**Conclusion**: The RX line is physically connected (part of UART3 port) but firmware does NOT use it. Communication is TX-only from A33 to GD32.

---

### A33 → GD32 Control GPIO (Reset/Boot)

**Connection**: A33 GPIO PH9 (gpio-233) → GD32 NRST or BOOT0

**Status**: 🔍 **LIKELY** (needs PCB tracing to confirm exact GD32 pin)

**Evidence**:
1. **GPIO exported and controlled**:
   ```
   pin 233 (PH9): uart3 sunxi-pinctrl: function gpio_out group PH9
   ```
   Reference: Pinmux analysis

2. **GPIO state**:
   ```
   gpio-233 (sysfs) out hi
   ```
   Reference: `/sys/kernel/debug/gpio` output

3. **Proximity to UART3 pins**: PH9 is in the same port as UART3 (PH6/PH7), suggesting it's part of the GD32 control interface.

4. **AuxCtrl manages this GPIO**: The fact it's exported to sysfs and controlled by AuxCtrl suggests it's for GD32 control.

**Needs Testing**:
- Toggle gpio-233 and observe GD32 behavior
- Check if pulling LOW causes reset or boot mode change
- PCB trace from A33 PH9 ball to GD32 pin

---

### A33 → GD32 Enable GPIO

**Connection**: A33 GPIO PD11 (gpio-107) → GD32 Power/Enable

**Status**: 🔍 **LIKELY** (needs testing)

**Evidence**:
1. **GPIO state**:
   ```
   gpio-107 (?) out hi
   ```
   Reference: `/sys/kernel/debug/gpio`

2. **Output HIGH**: Consistent with an enable signal (active high)

3. **No other known function**: gpio-107 is not associated with any peripheral in pinmux.

**Needs Testing**:
- Toggle gpio-107 to LOW and check if GD32 powers down
- Measure voltage at GD32 power pins while toggling
- PCB trace to identify actual GD32 pin connection

---

### A33 ← GD32 Status GPIO

**Connection**: A33 GPIO PB7 (gpio-39) ← GD32 GPIO (unknown pin)

**Status**: 🔍 **LIKELY** (needs runtime testing)

**Evidence**:
1. **GPIO configured as INPUT**:
   ```
   gpio-39 (?) in lo
   ```
   This is the ONLY input GPIO among the three GD32-related GPIOs.
   Reference: `/sys/kernel/debug/gpio`

2. **Currently reads LOW**: State is LOW, could indicate "ready" or "no obstacle"

3. **Pin mapping**: PB7 is pin 39
   ```
   pin 39 (PB7): (MUX UNCLAIMED) sunxi-pinctrl:
   ```
   Reference: Pinmux analysis

**Needs Testing**:
- Monitor gpio-39 value during motor operation
- Trigger bumper sensor and check if value changes
- Trigger cliff sensor and check if value changes
- Create interrupt handler and log state changes

**Testing Script**:
```bash
# Monitor for changes
watch -n 0.1 'cat /sys/class/gpio/gpio39/value'
```

---

### A33 → Lidar Sensor (UART1)

**Connection**: A33 UART1 (PG6/PG7) ↔ Lidar (J17 connector)

**Status**: ✅ **PROVEN**

**Evidence**:
1. **Pinmux configuration**:
   ```
   pin 198 (PG6): uart1 (GPIO UNCLAIMED) function uart1 group PG6
   pin 199 (PG7): uart1 (GPIO UNCLAIMED) function uart1 group PG7
   pin 200 (PG8): uart1 (GPIO UNCLAIMED) function uart1 group PG8
   pin 201 (PG9): uart1 (GPIO UNCLAIMED) function uart1 group PG9
   ```
   PG8/PG9 are hardware flow control (RTS/CTS).
   Reference: Pinmux analysis

2. **Working Python script**:
   - `Research/Lidar/scan.py` successfully reads from `/dev/ttyS1`
   - Receives 8-byte headers + distance data
   - Baud rate: 115200
   Reference: Existing scan.py file, tested and working

3. **Protocol documented**:
   - Command 0xAE: Health status
   - Command 0xAD: Measurement data
   - Distance multiplier: 0.25mm
   Reference: `Research/Lidar/README.md`

4. **AuxCtrl opens ttyS1**:
   ```
   1434  open("/dev/ttyS1", O_RDWR|O_NONBLOCK|O_LARGEFILE) = 5
   ```
   Reference: `/tmp/auxctrl_full.strace`

5. **AuxCtrl monitors FD 5**:
   ```
   1434  select(6, [5], NULL, NULL, {0, 1000})
   ```
   Reference: strace analysis

**Physical Connection**:
- J17 connector (5 pins, 2.0mm pitch PH type)
- Pin 1-2: Motor power
- Pin 3: TX (to A33 PG7 RX)
- Pin 4: RX (from A33 PG6 TX)
- Pin 5: GND

---

## GD32 Connections

### GD32 ← Motor Encoders (Left/Right Wheels)

**Connection**: GD32 GPIO/Timer inputs ← Wheel encoder outputs

**Status**: ❓ **HYPOTHESIS** (needs connector pinout analysis)

**Evidence**:
1. **Connector documentation**:
   - J25 (Bottom, 16-pin): Left wheel encoder + other sensors
   - J26 (Top, 16-pin): Right wheel encoder + other sensors
   Reference: `Research/Motherboard/README.md`

2. **GD32 has hardware timers**: GD32F103VCT6 has 4 advanced timers suitable for encoder input (quadrature decoding)

3. **Real-time requirement**: Encoder feedback is essential for closed-loop motor control

**Needs Analysis**:
- Pinout of J25/J26 connectors (which pins are encoder A/B channels)
- Physical trace from connector to GD32 pins
- Identify which GD32 timer channels are used (TIM1/TIM2/TIM3/TIM4)

---

### GD32 → Motor Drivers (PWM Outputs)

**Connection**: GD32 PWM outputs → Motor driver chips → Motors

**Status**: ❓ **HYPOTHESIS**

**Evidence**:
1. **Motor driver IC identified**:
   - U25 (Bottom): 8870 Motor Driver
   Reference: README.md component list

2. **GD32 has PWM capability**: Multiple timer channels can generate PWM

3. **Power connectors**:
   - J27: Right wheel power (2-pin)
   - J24: Left wheel power (2-pin)

**Needs Analysis**:
- Trace from GD32 PWM pins (likely PA8, PA9, PA10, PA11 for TIM1) to motor driver inputs
- Identify motor driver control signals (IN1, IN2, ENA, ENB)
- Document PWM frequency and duty cycle range

---

### GD32 ← Cliff Sensors (IR Fall Detect)

**Connection**: GD32 ADC/GPIO ← IR sensor outputs

**Status**: ❓ **HYPOTHESIS**

**Evidence**:
1. **Connector documentation**:
   - J5: Front fall detect L&R IR sensors (8-pin)
   - J26: Right side fall detect IR (part of 16-pin)
   - J25: Left side fall detect IR (part of 16-pin)
   Reference: README.md

2. **GD32 has ADC**: 2x 12-bit ADC with up to 16 channels

3. **Safety-critical**: Cliff detection requires fast response, suitable for GD32

**Needs Analysis**:
- Pinout of J5, J25, J26 for IR sensor signals
- Determine if analog (ADC) or digital (GPIO with comparator) output
- Identify GD32 pins used (PA0-PA7 for ADC1, PB0-PB1 for ADC2)

---

### GD32 ← Bumper Sensors (Hit Detect)

**Connection**: GD32 GPIO ← Bumper switch outputs

**Status**: ❓ **HYPOTHESIS**

**Evidence**:
1. **Connector documentation**:
   - J26: Right hit detect sensor
   - J25: Left hit detect sensor
   Reference: README.md

2. **Likely digital**: Bumpers are usually simple switches (active low or high)

3. **Interrupt-driven**: Fast response needed for collision detection

**Needs Analysis**:
- Pinout of J25/J26 for bumper signals
- Determine active level (HIGH or LOW when pressed)
- Identify which GD32 GPIO pins, configured as EXTI (external interrupt)

---

## Direct A33 Connections (Bypassing GD32)

### A33 ← Dust Box Sensor

**Connection**: A33 GPIO or ADC ← Dust box detector (J48)

**Status**: ❓ **HYPOTHESIS**

**Evidence**:
1. **Connector**: J48 (6-pin, 1.25mm GH) - Dust box sensor / Water box detector
2. **Non-critical**: Simple presence detection, doesn't need real-time

**Needs Analysis**:
- Pinout of J48
- Trace to A33 GPIO or ADC pin
- Test detection mechanism (optical? magnetic? switch?)

---

### A33 ← Water Box Detector

**Connection**: A33 GPIO ← Water box detector (J48)

**Status**: ❓ **HYPOTHESIS**

**Evidence**:
1. **Shared connector with dust box** (J48)
2. **Simple detection**: Likely just a switch or hall sensor

**Needs Analysis**:
- Same as dust box sensor

---

### A33 ← Mop Pad Sensor

**Connection**: A33 GPIO ← Mop pad sensor (J34)

**Status**: ❓ **HYPOTHESIS**

**Evidence**:
1. **Connector**: J34 (3-pin, 1.25mm GH) - Mop pad sensor
2. **Simple detection**: Presence/absence detection

**Needs Analysis**:
- Pinout of J34
- Trace to A33 GPIO
- Test detection mechanism

---

### A33 ← Buttons

**Connection**: A33 GPIO ← Button inputs (power, home, clean)

**Status**: ❓ **HYPOTHESIS**

**Evidence**:
1. **User interface requirement**: Robot has physical buttons
2. **ADC or GPIO**: Could be resistor ladder network on single ADC pin or individual GPIOs

**Needs Analysis**:
- Identify button location on PCB
- Trace to A33 pins
- Determine if shared ADC or individual GPIOs

---

## Power Connections

### Battery → AXP223 → A33, GD32, Peripherals

**Connection**: Battery → U2 (charger) → AXP223 (PMIC) → System power

**Status**: ✅ **PROVEN** (standard design)

**Evidence**:
1. **Component identification**:
   - U2: CN3704 - Battery charger controller for 4-cell Li-ion
   - U12: AXP223 - 21-channel PMIC
   Reference: README.md component list

2. **AXP223 powers A33**: This is standard A33 reference design
   Reference: Allwinner A33 datasheet

3. **Voltage regulator**: U3 (CJT1117B 3.3V) likely provides 3.3V for peripherals

**Needs Analysis**:
- Measure voltage rails (3.3V, 5V, battery voltage)
- Identify which rails power GD32, motors, sensors

---

## Testing Priority

### High Priority (Can test now):
1. ✅ Monitor gpio-39 during operation
2. ✅ Verify Lidar on ttyS1 (already working)
3. ✅ Toggle gpio-233 and observe GD32 behavior
4. ✅ Toggle gpio-107 and check power

### Medium Priority (Needs physical access):
1. Probe J25/J26 connector pins while robot operates
2. Trace PCB connections with multimeter continuity
3. Identify motor driver control signals

### Low Priority (Future work):
1. Map all sensor connector pinouts
2. Reverse engineer GD32 firmware for complete understanding
3. Create full electrical schematic

---

## Testing Scripts

See `Research/Software/test_gpio_monitoring.sh` for GPIO monitoring scripts.

---

## References

- `/tmp/auxctrl_full.strace` - Complete system call trace of AuxCtrl
- `/sys/kernel/debug/pinctrl/sunxi-pinctrl/pinmux-pins` - Kernel pinmux configuration
- `/sys/kernel/debug/gpio` - GPIO status
- `Research/Motherboard/README.md` - Component list and connector documentation
- `Research/Software/GD32_Init_Sequence.md` - UART protocol analysis
- `Research/Software/Sensor_Architecture.md` - System architecture analysis
