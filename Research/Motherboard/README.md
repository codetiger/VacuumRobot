# Reverse Engineering Motherboard

## 1. Challenges of Using Flatbed Scanners for PCB Reverse Engineering

Many articles on reverse engineering PCBs suggest starting with a flatbed scanner to capture images of the board. However, if you are trying to understand a PCB with components, flatbed scanners may not be the best option.

The primary issue is that flatbed scanners focus on objects that are directly in contact with the scanner bed, losing focus on parts that are slightly elevated. This shallow depth of field means that components, which are not perfectly flat, appear blurry and indistinct in the scanned image. As a result, it’s difficult to get a clear, detailed view of the PCB and its components using this method.

For those aiming to reverse engineer a PCB with components, alternative approaches may be more effective.

## 2. Picture

After putting a few hours of effort, I found a way to take a good picture of the motherboard PCB. I used an iPhone 15 camera and tried various angles and finally settled with the best picture I can do. You can use the magnifier app in iOS to find the part numbers of each component.

## Main Components

| Part No | Manufacturer | Model            |
|---------|--------------|------------------|
| U23     | AllWinner    | A33              |
| DU1     | Nanya Tech   | NT5CC256M16EP-EK |
| U13     | Macronix     | MX30LF2G18AC-TI  |
| U12     | X-Powers     | AXP223           |
| U16     | Realtek      | RTL8189ETV       |
| U1      | GigaDevice   | GD32F103VCT6     |

### Description

* A33 - Allwinner
    * ARM Cortex-A7 Quad-Core CPU
    * ARM Mali400 MP2 Dual-Core GPU
    * DDR3/DDR3L controller
    * NAND Flash controller and 64-bit ECC

* SDRAM - Nanya Tech 
    * 4 GBits DDR3L
    * 933 MHz Maximum Clock Rate
    * 1866 Mbps Data Rate

* Flash Memory - Macronix
    * 2 Gbits NAND

* AXP223 - X-Powers
    * Power Management IC
    * 21 Channel power output
    * 12-bit ADC
    * Voltage/Current/Temperature monitoring

* Realtex WiFi module
    * 802.11n Wireless LAN 

* GD32F1 MCU - GigaDevice
    * 108 MHz ARM Cortex-M3 core
    * 48 KB RAM
    * 256 KB Flash memory


## Circuit (Highlevel) 

### Connectors

| Part No | side   | Pins | Rows | Type  | Pitch  | Component 
|---------|--------|------|------|-------|--------|-----------
| J48     | Top    | 6    | 1    | GH    | 1.25mm | Dust box sensor / Water box detector
| J15     | Top    | 2    | 1    | XH    | 2.5mm  | Rolling brush power 
| J5      | Top    | 8    | 1    | GH    | 1.25mm | Front fall detect R & L IR sensor
| J17     | Top    | 5    | 1    | PH    | 2.0mm  | Lidar sensor 
| J34     | Top    | 3    | 1    | GH    | 1.25mm | Mop pad sensor *
| J27     | Top    | 2    | 1    | PH    | 2.0mm  | Right wheel power 
| J26     | Top    | 16   | 2    | SHD   | 1.0mm  | Right wheel encoder / Sweeper motor power / Right side fall detect IR / Right hit detect sensor
| J50     | Top    | 5    | 1    | SHD   | 1.0mm  | Debug pins for Micro-USB
| J18     | Top    | 2    | 1    | GH    | 1.25mm | Speaker
| J45     | Top    | 3    | 1    | GH    | 1.25mm | Proscenic M6 Remote Board (TS-Y430-01C)
| J2*     | Top    | 2    | 1    | PH    | 2.0mm  | Power-In from dock station connection
| J16     | Top    | 4    | 1    | PH    | 2.0mm  | Vacuum pump
| J24     | Bottom | 2    | 1    | PH    | 2.0mm  | Left wheel power
| J25     | Bottom | 16   | 2    | SHD   | 1.0mm  | Left wheel encoder / Dustbox power / Left side fall detect IR / Left hit detect sensor
| J36     | Top    | 3    | 1    | GH    | 1.25mm |
(* indicates that its a guess) 

### Other Components

| Part No | side   | Component    | Purpose   
|---------|--------|--------------|-----------
| Q4      | Top    | NCE30P30K    | 
| Q5      | Top    | NCE30P30K    | 
| Q24     | Top    | UTT30P06L    | 
| Q23     | Top    | D444         | 
| U31     | Bottom | XPT4871      | Audio Power Amplifier
| U2      | Top    | CN3704       | Battery charger controller for 4 cell li-ion battery
| U10     | Top    | 74HC14D      | Inverter Schmitt trigger
| U3      | Top    | CJT1117B 3.3 | Voltage regulator
| U25     | Bottom | 8870         | Motor Driver