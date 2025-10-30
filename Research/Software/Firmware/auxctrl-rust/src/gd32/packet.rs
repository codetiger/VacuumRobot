//! GD32 Communication Protocol Packet Implementation
//!
//! Packet Structure:
//! ```
//! [SYNC1: 0xFA] [SYNC2: 0xFB] [LEN] [CMD] [DATA...] [CRC]
//! ```
//!
//! Where:
//! - SYNC1, SYNC2: Fixed sync bytes (0xFA, 0xFB)
//! - LEN: Length of remaining packet (CMD + DATA + CRC)
//! - CMD: Command ID
//! - DATA: Variable length data (can be 0 bytes)
//! - CRC: Checksum = CMD XOR DATA[0] XOR DATA[1] XOR ...

/// GD32 protocol packet
#[derive(Debug, Clone)]
pub struct GD32Packet {
    pub command_id: u8,
    pub data: Vec<u8>,
}

impl GD32Packet {
    /// Create a new packet
    pub fn new(command_id: u8, data: Vec<u8>) -> Self {
        Self { command_id, data }
    }

    /// Encode packet to bytes ready for transmission
    pub fn encode(&self) -> Vec<u8> {
        let mut packet = Vec::with_capacity(4 + self.data.len());

        // Sync bytes
        packet.push(0xFA);
        packet.push(0xFB);

        // Length (CMD + DATA + CRC)
        let len = 1 + self.data.len() + 1;
        packet.push(len as u8);

        // Command
        packet.push(self.command_id);

        // Data
        packet.extend_from_slice(&self.data);

        // CRC (XOR of CMD and all DATA bytes)
        let crc = self.calculate_crc();
        packet.push(crc);

        packet
    }

    /// Calculate CRC checksum
    fn calculate_crc(&self) -> u8 {
        let mut crc = self.command_id;
        for byte in &self.data {
            crc ^= byte;
        }
        crc
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heartbeat_packet() {
        // Heartbeat: FA FB 03 06 00 06
        let packet = GD32Packet::new(0x06, vec![0x00]);
        let encoded = packet.encode();
        assert_eq!(encoded, vec![0xFA, 0xFB, 0x03, 0x06, 0x00, 0x06]);
    }

    #[test]
    fn test_status_request_packet() {
        // Status Request: FA FB 03 0D 00 0D
        let packet = GD32Packet::new(0x0D, vec![0x00]);
        let encoded = packet.encode();
        assert_eq!(encoded, vec![0xFA, 0xFB, 0x03, 0x0D, 0x00, 0x0D]);
    }

    #[test]
    fn test_init_packet() {
        // Init CMD 0x66: FA FB 0B 66 00 00 00 00 00 00 00 00 66 00
        let packet = GD32Packet::new(0x66, vec![0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x66]);
        let encoded = packet.encode();
        assert_eq!(
            encoded,
            vec![0xFA, 0xFB, 0x0B, 0x66, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x66, 0x00]
        );
    }

    #[test]
    fn test_crc_calculation() {
        // Test CRC: CMD 0x0C with data [01, 0C] should give CRC = 0x01
        let packet = GD32Packet::new(0x0C, vec![0x01, 0x0C]);
        assert_eq!(packet.calculate_crc(), 0x01);
    }

    #[test]
    fn test_empty_data_packet() {
        // Packet with no data
        let packet = GD32Packet::new(0x42, vec![]);
        let encoded = packet.encode();
        // FA FB 02 42 42 (LEN=2: CMD+CRC, CRC=0x42)
        assert_eq!(encoded, vec![0xFA, 0xFB, 0x02, 0x42, 0x42]);
    }
}
