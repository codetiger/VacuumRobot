//! GPIO Control for GD32 MCU
//!
//! This module provides GPIO control for the GD32 microcontroller,
//! including reset, power enable, and status monitoring.

use std::fs;
use std::io;
use std::path::Path;
use std::thread;
use std::time::Duration;

/// GPIO pin numbers for GD32 control
pub struct GD32GPIO {
    /// GPIO-233 (PH9): Reset or Boot mode control
    pub reset_pin: u32,
    /// GPIO-107 (PD11): Power/Enable control
    pub enable_pin: u32,
    /// GPIO-39 (PB7): Status input from GD32
    pub status_pin: u32,
}

impl GD32GPIO {
    /// Create new GPIO controller with default pins
    pub fn new() -> Self {
        Self {
            reset_pin: 233,  // PH9 - Reset/Boot control
            enable_pin: 107, // PD11 - Power/Enable
            status_pin: 39,  // PB7 - Status input
        }
    }

    /// Export a GPIO pin if not already exported
    fn export_gpio(&self, pin: u32) -> io::Result<()> {
        let gpio_path = format!("/sys/class/gpio/gpio{}", pin);

        // Check if already exported
        if Path::new(&gpio_path).exists() {
            println!("  GPIO {} already exported", pin);
            return Ok(());
        }

        println!("  Exporting GPIO {}...", pin);
        match fs::write("/sys/class/gpio/export", pin.to_string()) {
            Ok(_) => {
                // Wait for sysfs to create the directory
                thread::sleep(Duration::from_millis(100));
                Ok(())
            }
            Err(e) if e.raw_os_error() == Some(16) => {
                // EBUSY - GPIO already in use, skip it
                println!("  GPIO {} is busy (used by kernel), skipping...", pin);
                Ok(())
            }
            Err(e) => Err(e),
        }
    }

    /// Set GPIO direction (in or out)
    fn set_direction(&self, pin: u32, direction: &str) -> io::Result<()> {
        let gpio_path = format!("/sys/class/gpio/gpio{}", pin);
        if !Path::new(&gpio_path).exists() {
            // GPIO not exported to sysfs, skip
            return Ok(());
        }

        let direction_path = format!("{}/direction", gpio_path);
        fs::write(&direction_path, direction)?;
        Ok(())
    }

    /// Set GPIO value (0 or 1)
    fn set_value(&self, pin: u32, value: bool) -> io::Result<()> {
        let gpio_path = format!("/sys/class/gpio/gpio{}", pin);
        if !Path::new(&gpio_path).exists() {
            // GPIO not exported to sysfs, skip
            return Ok(());
        }

        let value_path = format!("{}/value", gpio_path);
        let value_str = if value { "1" } else { "0" };
        fs::write(&value_path, value_str)?;
        Ok(())
    }

    /// Read GPIO value
    fn read_value(&self, pin: u32) -> io::Result<bool> {
        let gpio_path = format!("/sys/class/gpio/gpio{}", pin);
        if !Path::new(&gpio_path).exists() {
            // GPIO not exported to sysfs, return false
            return Ok(false);
        }

        let value_path = format!("{}/value", gpio_path);
        let value_str = fs::read_to_string(&value_path)?.trim().to_string();
        Ok(value_str == "1")
    }

    /// Initialize all GPIO pins
    pub fn initialize(&self) -> io::Result<()> {
        println!("Initializing GD32 GPIO control pins...");

        // Export all pins
        self.export_gpio(self.reset_pin)?;
        self.export_gpio(self.enable_pin)?;
        self.export_gpio(self.status_pin)?;

        // Set directions
        println!("  Setting GPIO directions...");
        self.set_direction(self.reset_pin, "out")?;
        self.set_direction(self.enable_pin, "out")?;
        self.set_direction(self.status_pin, "in")?;

        // Ensure enable is HIGH (powered)
        self.set_value(self.enable_pin, true)?;
        println!("  GPIO {} (enable) set HIGH", self.enable_pin);

        // Ensure reset is HIGH (not in reset)
        self.set_value(self.reset_pin, true)?;
        println!("  GPIO {} (reset) set HIGH", self.reset_pin);

        Ok(())
    }

    /// Perform hardware reset of GD32
    ///
    /// Pulls reset line LOW for 100ms, then HIGH
    pub fn hardware_reset(&self) -> io::Result<()> {
        println!("Performing GD32 hardware reset...");

        // Pull reset LOW
        println!("  Pulling RESET (GPIO {}) LOW...", self.reset_pin);
        self.set_value(self.reset_pin, false)?;
        thread::sleep(Duration::from_millis(100));

        // Pull reset HIGH
        println!("  Pulling RESET (GPIO {}) HIGH...", self.reset_pin);
        self.set_value(self.reset_pin, true)?;

        // Wait for GD32 to boot
        println!("  Waiting for GD32 to boot...");
        thread::sleep(Duration::from_millis(500));

        Ok(())
    }

    /// Power cycle the GD32
    ///
    /// Pulls enable line LOW, then HIGH
    pub fn power_cycle(&self) -> io::Result<()> {
        println!("Power cycling GD32...");

        // Power OFF
        println!("  Pulling ENABLE (GPIO {}) LOW...", self.enable_pin);
        self.set_value(self.enable_pin, false)?;
        thread::sleep(Duration::from_millis(500));

        // Power ON
        println!("  Pulling ENABLE (GPIO {}) HIGH...", self.enable_pin);
        self.set_value(self.enable_pin, true)?;

        // Wait for power stabilization
        println!("  Waiting for power stabilization...");
        thread::sleep(Duration::from_millis(500));

        Ok(())
    }

    /// Read GD32 status pin
    pub fn read_status(&self) -> io::Result<bool> {
        self.read_value(self.status_pin)
    }

    /// Print current GPIO states
    pub fn print_status(&self) -> io::Result<()> {
        println!("GD32 GPIO Status:");

        let reset = self.read_value(self.reset_pin)?;
        let enable = self.read_value(self.enable_pin)?;
        let status = self.read_value(self.status_pin)?;

        println!("  GPIO {} (reset):  {}", self.reset_pin, if reset { "HIGH" } else { "LOW" });
        println!("  GPIO {} (enable): {}", self.enable_pin, if enable { "HIGH" } else { "LOW" });
        println!("  GPIO {} (status): {}", self.status_pin, if status { "HIGH" } else { "LOW" });

        Ok(())
    }
}

impl Default for GD32GPIO {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gpio_creation() {
        let gpio = GD32GPIO::new();
        assert_eq!(gpio.reset_pin, 233);
        assert_eq!(gpio.enable_pin, 107);
        assert_eq!(gpio.status_pin, 39);
    }
}
