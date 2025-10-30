# Research Backup - Historical Documents

**⚠️ WARNING**: This directory contains **outdated and in-progress research documents** that reflect early misunderstandings during the reverse engineering process.

## Purpose

This folder preserves the historical evolution of our understanding of the GD32 communication protocol. These documents are kept for reference only and **should not be used as accurate protocol documentation**.

## What's Here

### `/Analysis/` - Early Protocol Analysis
Contains markdown documents with early assumptions and test results that were later proven incorrect:
- Wrong serial port assumptions (`/dev/ttyS1` vs actual `/dev/ttyS3`)
- Incorrect belief that communication was one-way
- Misidentified command purposes
- Failed test attempts and their analysis

**Status**: Many documents marked with `[OUTDATED]` headers

### `/binaries/` - Analysis Scripts
Python scripts used for binary analysis and protocol extraction from the AuxCtrl binary:
- Ghidra analysis helpers
- Protocol extraction tools
- GPIO investigation scripts
- Command ID discovery tools

**Status**: Historical tools, superseded by serial MITM approach

## For Current Documentation

**DO NOT USE THIS FOLDER FOR CURRENT INFORMATION**

See the verified, working documentation at:
- **`Research/Software/Firmware/auxctrl-rust/GD32_PROTOCOL_FINAL.md`** - Complete verified protocol
- **`Research/Software/Firmware/auxctrl-rust/CHANGELOG.md`** - Evolution of understanding
- **`Research/Software/Firmware/auxctrl-rust/SERIAL_MITM_APPROACH.md`** - How we discovered the truth

## Major Errors in These Documents

If you're reading documents in this folder, be aware of these common mistakes:

| Error | Actual Truth |
|-------|--------------|
| Serial port is `/dev/ttyS1` | Actually `/dev/ttyS3` |
| One-way communication only | Bidirectional (GD32 sends CMD=0x15) |
| CMD 0x08 is "SetIMUZero" | Actually initialization/wakeup |
| CMD 0x66 is "Motor Velocity" | Actually heartbeat |
| GD32 never responds | GD32 sends status packets |
| Simple heartbeat works | Requires CMD=0x08 init sequence |

## Why Keep This?

These documents are preserved to:
1. Show the learning journey and methodology
2. Document what approaches didn't work
3. Preserve analysis scripts that might be useful for other projects
4. Demonstrate the value of direct observation (MITM) over binary analysis alone

## Cleanup Performed

- Removed large binary files (AuxCtrl executable, .asm disassembly)
- Deleted capture logs (10+ serial capture log files)
- Removed Ghidra project files
- Kept analysis scripts and markdown documentation

---

**Last Updated**: October 30, 2025
**Status**: Historical archive only