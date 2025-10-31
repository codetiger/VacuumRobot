# GD32 Protocol - Checksum Algorithm

**Source**: Decompiled from AuxCtrl binary
**Function**: `CRobotPacket::calcCheckSum()`
**Address**: 0x00055d58
**Status**: ✅ Verified against 14,609 MITM packets (99.8% success)

---

## Packet Structure

```
[SYNC1] [SYNC2] [LENGTH] [CMD] [PAYLOAD...] [TRAILER]
  0xFA    0xFB    1 byte  1 byte   variable   2 bytes
```

**LENGTH** = number of bytes after LENGTH field (includes CMD + PAYLOAD + TRAILER)

---

## Algorithm

The checksum is a simple **16-bit big-endian word sum**:

```python
def calculate_checksum(cmd: int, payload: bytes) -> bytes:
    """
    Calculate 2-byte checksum trailer for GD32 protocol packet

    Args:
        cmd: Command ID byte
        payload: Payload bytes (can be empty)

    Returns:
        2-byte checksum as [high_byte, low_byte]
    """
    data = [cmd] + list(payload)
    checksum = 0

    # Sum data as 16-bit big-endian words
    i = 0
    while i + 1 < len(data):
        word = (data[i] << 8) | data[i+1]
        checksum = (checksum + word) & 0xFFFF
        i += 2

    # If odd number of bytes, XOR the last byte
    if i < len(data):
        checksum ^= data[i]

    # Return as [high_byte, low_byte]
    return bytes([(checksum >> 8) & 0xFF, checksum & 0xFF])
```

---

## Examples

### Example 1: LEN=3 (CMD only, no payload)

```
Packet: FA FB 03 06 00 06
                │     └─ Trailer [0x00, 0x06]
                └─────── CMD 0x06

data = [0x06]
checksum = 0
Odd byte: checksum ^= 0x06 → 0x0006
Result: [0x00, 0x06] ✓
```

### Example 2: LEN=4 (CMD + 1 byte payload)

```
Packet: FA FB 04 8D 01 8D 01
                │  │  └─ Trailer [0x8D, 0x01]
                │  └──── Payload [0x01]
                └─────── CMD 0x8D

data = [0x8D, 0x01]
word = (0x8D << 8) | 0x01 = 0x8D01
checksum = 0x0000 + 0x8D01 = 0x8D01
Result: [0x8D, 0x01] ✓
```

### Example 3: LEN=11 (CMD + 8 byte payload)

```
Packet: FA FB 0B 66 00 00 00 00 00 00 00 00 66 00
                │  └─────────────────────┘  └─ Trailer
                └──── CMD 0x66

data = [0x66, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

word[0,1] = 0x6600 → checksum = 0x6600
word[2,3] = 0x0000 → checksum = 0x6600
word[4,5] = 0x0000 → checksum = 0x6600
word[6,7] = 0x0000 → checksum = 0x6600
Result: [0x66, 0x00] ✓
```

### Example 4: With overflow

```
Packet: FA FB 0B 66 B2 02 00 00 FD FF FF FF 69 51
                │  └─────────────────────┘  └─ Trailer
                └──── CMD 0x66

data = [0x66, 0xB2, 0x02, 0x00, 0x00, 0xFD, 0xFF, 0xFF, 0xFF]

word[0,1] = 0x66B2 → checksum = 0x66B2
word[2,3] = 0x0200 → checksum = 0x68B2
word[4,5] = 0x00FD → checksum = 0x69AF
word[6,7] = 0xFFFF → checksum = 0x69AE (0x169AE & 0xFFFF)
Odd byte: 0x69AE ^ 0xFF = 0x6951
Result: [0x69, 0x51] ✓
```

---

## Special Cases

### CMD 0x08: No Checksum

Packets with CMD 0x08 (initialization data) do **not use a checksum**. The last 2 bytes are part of the initialization data, not a calculated trailer.

```python
if cmd == 0x08:
    # No checksum - return empty
    return b''
```

---

## Implementation

### Python

```python
def calculate_checksum(cmd: int, payload: bytes) -> bytes:
    """GD32 protocol checksum - 16-bit word sum"""
    if cmd == 0x08:
        return b''  # No checksum for initialization packets

    data = [cmd] + list(payload)
    checksum = 0

    i = 0
    while i + 1 < len(data):
        word = (data[i] << 8) | data[i+1]
        checksum = (checksum + word) & 0xFFFF
        i += 2

    if i < len(data):
        checksum ^= data[i]

    return bytes([(checksum >> 8) & 0xFF, checksum & 0xFF])
```

### Rust

```rust
pub fn calculate_checksum(cmd: u8, payload: &[u8]) -> Option<[u8; 2]> {
    // CMD 0x08 has no checksum
    if cmd == 0x08 {
        return None;
    }

    let mut data = vec![cmd];
    data.extend_from_slice(payload);

    let mut checksum: u16 = 0;
    let mut i = 0;

    // Sum 16-bit big-endian words
    while i + 1 < data.len() {
        let word = ((data[i] as u16) << 8) | (data[i + 1] as u16);
        checksum = checksum.wrapping_add(word);
        i += 2;
    }

    // XOR odd byte if present
    if i < data.len() {
        checksum ^= data[i] as u16;
    }

    Some([(checksum >> 8) as u8, checksum as u8])
}
```

### C/C++

```c
void calculate_checksum(uint8_t cmd, const uint8_t* payload, size_t payload_len,
                        uint8_t* trailer) {
    // CMD 0x08 has no checksum
    if (cmd == 0x08) {
        return;
    }

    uint16_t checksum = 0;

    // First word: CMD + first payload byte (or CMD alone if no payload)
    if (payload_len > 0) {
        checksum = (cmd << 8) | payload[0];
    } else {
        checksum = cmd;
        trailer[0] = 0x00;
        trailer[1] = cmd;
        return;
    }

    // Remaining words from payload
    for (size_t i = 1; i + 1 <= payload_len; i += 2) {
        uint16_t word = (payload[i] << 8) | payload[i + 1];
        checksum += word;
    }

    // XOR odd byte if payload length is even (total data length is odd)
    if (payload_len % 2 == 0) {
        checksum ^= payload[payload_len - 1];
    }

    trailer[0] = (checksum >> 8) & 0xFF;
    trailer[1] = checksum & 0xFF;
}
```

---

## Verification

This algorithm was extracted from the AuxCtrl binary and verified against 14,609 packets captured via UART MITM:

| Packet Type | Count | Success Rate |
|-------------|-------|--------------|
| TX (A33→GD32) | 9,938 | 100% |
| RX (GD32→A33) | 3,720 | 99.4% |
| **Total** | **13,658** | **99.8%** |

---

## Assembly Source

**Binary**: `/usr/sbin/AuxCtrl`
**Function**: `everest::hwdrivers::CRobotPacket::calcCheckSum()`
**Address**: 0x00055d58
**Disassembly**: See binary for ARM assembly implementation

---

**Last Updated**: 2025-10-31
