use lidar_reader::Lidar;
use std::collections::HashMap;

fn main() {
    println!("3iRobotix Delta-2D Lidar Scanner");
    println!("================================\n");

    // Parse command line arguments
    let args: Vec<String> = std::env::args().collect();
    let port = args.get(1).map(|s| s.as_str()).unwrap_or("/dev/ttyS2");
    let gpio_pin = match args.get(2).and_then(|s| s.parse::<u64>().ok()) {
        Some(pin) => pin,
        None => {
            eprintln!("Error: GPIO pin number is required");
            eprintln!("\nUsage: scan <serial_port> <gpio_pin>");
            eprintln!("Example: scan /dev/ttyS2 123");
            std::process::exit(1);
        }
    };

    println!("Opening Lidar on port: {}", port);
    println!("Using GPIO pin {} for power control", gpio_pin);

    // Initialize Lidar with GPIO power control
    let mut lidar = match Lidar::new(port, gpio_pin) {
        Ok(l) => l,
        Err(e) => {
            eprintln!("Error: Failed to open Lidar: {}", e);
            std::process::exit(1);
        }
    };

    // Power on the Lidar
    println!("Powering on Lidar...");
    if let Err(e) = lidar.power_on() {
        eprintln!("Error: Failed to power on Lidar: {}", e);
        std::process::exit(1);
    }

    println!("Reading scans... (Press Ctrl+C to stop)\n");

    let mut scan_count = 0;
    let mut angle_distance_map: HashMap<i32, f32> = HashMap::new();

    loop {
        match lidar.read_scan() {
            Ok(Some(scan)) => {
                scan_count += 1;

                // Update the angle-distance map with new measurements
                for measurement in &scan.measurements {
                    let angle_key = measurement.angle.round() as i32;
                    angle_distance_map.insert(angle_key, measurement.distance);
                }

                // Print summary every 10 scans
                if scan_count % 10 == 0 {
                    println!("Scan #{}", scan_count);
                    println!("  Motor RPM: {}", scan.motor_rpm);
                    println!(
                        "  Offset Angle: {:.2}°, Start Angle: {:.2}°",
                        scan.offset_angle, scan.start_angle
                    );
                    println!("  Measurements in packet: {}", scan.measurements.len());
                    println!("  Total unique angles: {}", angle_distance_map.len());

                    // Show a few sample measurements
                    println!("  Sample measurements:");
                    for (i, measurement) in scan.measurements.iter().take(3).enumerate() {
                        println!(
                            "    [{}/{}] Angle: {:6.2}°, Distance: {:7.2}mm, Quality: {}",
                            i + 1,
                            scan.measurements.len(),
                            measurement.angle,
                            measurement.distance,
                            measurement.signal_quality
                        );
                    }
                    println!();
                }
            }
            Ok(None) => {
                // Health packet received, no measurements
            }
            Err(e) => {
                eprintln!("Error reading scan: {}", e);
                // Continue reading despite errors
            }
        }
    }
}
