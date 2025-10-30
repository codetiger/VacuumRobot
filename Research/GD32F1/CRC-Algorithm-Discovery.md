# CRC Algorithm Discovery

## Summary

Successfully reverse-engineered the CRC algorithm used for GD32 communication protocol by analyzing 2,679 captured packets from AuxCtrl.

## CRC Algorithm

```
CRC = CMD_ID XOR DATA[0] XOR DATA[1] XOR ... XOR DATA[n]
```

**Formula**: XOR of command ID and all data bytes.

## Packet Structure

```
[SYNC1] [SYNC2] [LEN] [CMD] [DATA...] [CRC]
  0xFA    0xFB
```

Where:
- **SYNC1, SYNC2**: Fixed sync bytes (0xFA, 0xFB)
- **LEN**: Length of remaining packet (CMD + DATA + CRC)
- **CMD**: Command ID
- **DATA**: Variable length data (can be 0 bytes)
- **CRC**: Checksum calculated as `CMD XOR DATA[0] XOR DATA[1] XOR ...`

## Verified Examples

### Heartbeat (CMD 0x06)
```
FA FB 03 06 00 06
```
- LEN = 0x03 (3 bytes: CMD + DATA + CRC)
- CMD = 0x06
- DATA = 0x00 (1 byte)
- CRC = 0x06 XOR 0x00 = **0x06** ✓

### Status Request (CMD 0x0D)
```
FA FB 03 0D 00 0D
```
- LEN = 0x03
- CMD = 0x0D
- DATA = 0x00
- CRC = 0x0D XOR 0x00 = **0x0D** ✓

### Multi-byte Data Example (CMD 0x0C)
```
FA FB 04 0C 01 0C 01
```
- LEN = 0x04 (4 bytes)
- CMD = 0x0C
- DATA = 0x01, 0x0C (2 bytes)
- CRC = 0x0C XOR 0x01 XOR 0x0C = **0x01** ✓

### Complex Example (CMD 0x66)
```
FA FB 0B 66 00 00 00 00 00 00 00 00 66 00
```
- LEN = 0x0B (11 bytes)
- CMD = 0x66
- DATA = 00 00 00 00 00 00 00 00 66 (9 bytes)
- CRC = 0x66 XOR 0x00 XOR 0x00 XOR 0x00 XOR 0x00 XOR 0x00 XOR 0x00 XOR 0x00 XOR 0x00 XOR 0x66 = **0x00** ✓
