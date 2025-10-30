/*
 * GD32 Heartbeat Monitor
 *
 * Sends periodic heartbeat packets to GD32 and logs responses
 * Compile: gcc -o heartbeat_monitor heartbeat_monitor.c
 * Or for ARM: arm-linux-gnueabi-gcc -static -o heartbeat_monitor heartbeat_monitor.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <time.h>
#include <signal.h>
#include <sys/time.h>

#define SERIAL_PORT "/dev/ttyS1"
#define BAUD_RATE B115200
#define HEARTBEAT_INTERVAL_MS 50

// Protocol constants
#define SYNC1 0xFA
#define SYNC2 0xFB
#define CMD_HEARTBEAT 0x06
#define CMD_SENSOR 0x15

// Global flag for clean shutdown
volatile int running = 1;

void signal_handler(int sig) {
    printf("\n[*] Shutting down...\n");
    running = 0;
}

long long current_time_ms() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (long long)(tv.tv_sec) * 1000 + (tv.tv_usec) / 1000;
}

void print_timestamp() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    struct tm *tm_info = localtime(&tv.tv_sec);
    printf("[%02d:%02d:%02d.%03ld] ",
           tm_info->tm_hour, tm_info->tm_min, tm_info->tm_sec,
           tv.tv_usec / 1000);
}

void print_hex(const unsigned char *data, int len) {
    for (int i = 0; i < len; i++) {
        printf("%02x ", data[i]);
    }
}

int open_serial(const char *port) {
    int fd = open(port, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (fd < 0) {
        perror("open");
        return -1;
    }

    struct termios options;
    tcgetattr(fd, &options);

    // Set baud rate
    cfsetispeed(&options, BAUD_RATE);
    cfsetospeed(&options, BAUD_RATE);

    // 8N1, no flow control
    options.c_cflag &= ~PARENB;  // No parity
    options.c_cflag &= ~CSTOPB;  // 1 stop bit
    options.c_cflag &= ~CSIZE;
    options.c_cflag |= CS8;      // 8 data bits
    options.c_cflag |= (CLOCAL | CREAD);  // Enable receiver
    options.c_cflag &= ~CRTSCTS; // No hardware flow control

    // Raw input
    options.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
    options.c_iflag &= ~(IXON | IXOFF | IXANY);  // No software flow control
    options.c_oflag &= ~OPOST;  // Raw output

    // Set timeouts
    options.c_cc[VMIN] = 0;   // Non-blocking
    options.c_cc[VTIME] = 0;

    tcsetattr(fd, TCSANOW, &options);
    tcflush(fd, TCIOFLUSH);

    return fd;
}

void send_heartbeat(int fd, FILE *logfile) {
    // Heartbeat packet: FA FB 03 06 00 06
    unsigned char packet[] = {SYNC1, SYNC2, 0x03, CMD_HEARTBEAT, 0x00, 0x06};

    write(fd, packet, sizeof(packet));

    // Log TX
    if (logfile) {
        fprintf(logfile, "[");
        struct timeval tv;
        gettimeofday(&tv, NULL);
        fprintf(logfile, "%ld.%03ld", tv.tv_sec, tv.tv_usec / 1000);
        fprintf(logfile, "] TX ");
        for (int i = 0; i < sizeof(packet); i++) {
            fprintf(logfile, "%02x ", packet[i]);
        }
        fprintf(logfile, "\n");
        fflush(logfile);
    }
}

int parse_packet(const unsigned char *buffer, int buf_len, unsigned char *packet_out, int *packet_len) {
    if (buf_len < 4) return 0;

    if (buffer[0] != SYNC1 || buffer[1] != SYNC2) {
        return -1;  // Invalid sync
    }

    int length = buffer[2];
    int expected_total = 3 + length;  // SYNC1 + SYNC2 + LEN + payload

    if (buf_len < expected_total) {
        return 0;  // Incomplete packet
    }

    // Copy packet
    memcpy(packet_out, buffer, expected_total);
    *packet_len = expected_total;

    return expected_total;
}

void print_sensor_data(const unsigned char *payload, int len) {
    if (len < 97) {
        printf("  [Warning: Short payload %d bytes]\n", len);
        return;
    }

    // Print some key offsets (these are guesses based on captures)
    printf("  Offset 0-3    : %02x %02x %02x %02x\n",
           payload[0], payload[1], payload[2], payload[3]);
    printf("  Offset 12-15  : %02x %02x %02x %02x (encoder left?)\n",
           payload[12], payload[13], payload[14], payload[15]);
    printf("  Offset 20-23  : %02x %02x %02x %02x (encoder right?)\n",
           payload[20], payload[21], payload[22], payload[23]);
    printf("  Offset 40-45  : %02x %02x %02x %02x %02x %02x (IMU accel?)\n",
           payload[40], payload[41], payload[42], payload[43], payload[44], payload[45]);
    printf("  Offset 46-51  : %02x %02x %02x %02x %02x %02x (IMU gyro?)\n",
           payload[46], payload[47], payload[48], payload[49], payload[50], payload[51]);
    printf("  Offset 70-71  : %02x %02x (battery?)\n",
           payload[70], payload[71]);
    printf("  Offset 80     : %02x (bumper?)\n", payload[80]);
    printf("  Offset 82     : %02x (cliff?)\n", payload[82]);
}

int main(int argc, char *argv[]) {
    int duration = 60;  // Default 60 seconds

    if (argc > 1) {
        duration = atoi(argv[1]);
    }

    printf("================================================================================\n");
    printf("GD32 Heartbeat Monitor (C version)\n");
    printf("================================================================================\n");
    printf("Serial Port: %s\n", SERIAL_PORT);
    printf("Baud Rate: 115200\n");
    printf("Duration: %d seconds\n", duration);
    printf("Heartbeat: Every %d ms\n", HEARTBEAT_INTERVAL_MS);
    printf("\n");
    printf("Instructions:\n");
    printf("  - Move robot manually to trigger sensors\n");
    printf("  - Press bumpers, trigger cliff sensors\n");
    printf("  - Spin wheels to see encoder changes\n");
    printf("  - Press Ctrl+C to stop early\n");
    printf("\n");
    printf("Starting in 3 seconds...\n");
    printf("================================================================================\n");
    sleep(3);

    // Setup signal handler
    signal(SIGINT, signal_handler);

    // Open serial port
    int fd = open_serial(SERIAL_PORT);
    if (fd < 0) {
        printf("[!] Failed to open %s\n", SERIAL_PORT);
        printf("[!] Make sure AuxCtrl is stopped: killall AuxCtrl\n");
        return 1;
    }

    printf("[+] Serial port opened: %s\n", SERIAL_PORT);

    // Open log file
    char log_filename[256];
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    snprintf(log_filename, sizeof(log_filename),
             "/tmp/heartbeat_log_%04d%02d%02d_%02d%02d%02d.log",
             tm_info->tm_year + 1900, tm_info->tm_mon + 1, tm_info->tm_mday,
             tm_info->tm_hour, tm_info->tm_min, tm_info->tm_sec);

    FILE *logfile = fopen(log_filename, "w");
    if (logfile) {
        fprintf(logfile, "# GD32 Heartbeat Monitor Log\n");
        fprintf(logfile, "# Format: [timestamp] direction hex_bytes\n\n");
        printf("[+] Logging to: %s\n", log_filename);
    }

    printf("\n");
    printf("--------------------------------------------------------------------------------\n");
    printf("LIVE MONITORING (Ctrl+C to stop)\n");
    printf("--------------------------------------------------------------------------------\n");
    printf("\n");

    // Statistics
    int tx_count = 0;
    int rx_count = 0;
    int sensor_packets = 0;
    int other_packets = 0;

    long long start_time = current_time_ms();
    long long last_heartbeat = 0;

    unsigned char rx_buffer[4096];
    int rx_buf_len = 0;

    while (running && (current_time_ms() - start_time) < duration * 1000) {
        long long current = current_time_ms();

        // Send heartbeat every 50ms
        if (current - last_heartbeat >= HEARTBEAT_INTERVAL_MS) {
            send_heartbeat(fd, logfile);
            tx_count++;
            last_heartbeat = current;
        }

        // Read incoming data
        unsigned char temp[256];
        int n = read(fd, temp, sizeof(temp));
        if (n > 0) {
            // Append to buffer
            if (rx_buf_len + n < sizeof(rx_buffer)) {
                memcpy(rx_buffer + rx_buf_len, temp, n);
                rx_buf_len += n;
            }

            // Try to parse packets from buffer
            while (rx_buf_len >= 4) {
                unsigned char packet[512];
                int packet_len = 0;

                int result = parse_packet(rx_buffer, rx_buf_len, packet, &packet_len);

                if (result > 0) {
                    // Valid packet
                    rx_count++;

                    // Log RX
                    if (logfile) {
                        fprintf(logfile, "[");
                        struct timeval tv;
                        gettimeofday(&tv, NULL);
                        fprintf(logfile, "%ld.%03ld", tv.tv_sec, tv.tv_usec / 1000);
                        fprintf(logfile, "] RX ");
                        for (int i = 0; i < packet_len; i++) {
                            fprintf(logfile, "%02x ", packet[i]);
                        }
                        fprintf(logfile, "\n");
                        fflush(logfile);
                    }

                    // Process packet
                    int cmd_id = packet[3];

                    if (cmd_id == CMD_SENSOR) {
                        sensor_packets++;
                        print_timestamp();
                        printf("SENSOR DATA (packet #%d):\n", sensor_packets);

                        int payload_len = packet[2] - 2;  // LEN - CMD - CRC
                        print_sensor_data(packet + 4, payload_len);
                        printf("\n");
                    } else {
                        other_packets++;
                        print_timestamp();
                        printf("CMD 0x%02x (%d bytes): ", cmd_id, packet_len);
                        print_hex(packet, packet_len);
                        printf("\n");
                    }

                    // Remove parsed packet from buffer
                    memmove(rx_buffer, rx_buffer + packet_len, rx_buf_len - packet_len);
                    rx_buf_len -= packet_len;

                } else if (result < 0) {
                    // Invalid sync, skip one byte
                    memmove(rx_buffer, rx_buffer + 1, rx_buf_len - 1);
                    rx_buf_len--;
                } else {
                    // Incomplete packet, need more data
                    break;
                }
            }
        }

        usleep(1000);  // 1ms sleep to prevent CPU spinning
    }

    // Cleanup
    close(fd);
    if (logfile) fclose(logfile);

    long long elapsed = current_time_ms() - start_time;

    printf("\n");
    printf("================================================================================\n");
    printf("SESSION SUMMARY\n");
    printf("================================================================================\n");
    printf("Duration: %.1f seconds\n", elapsed / 1000.0);
    printf("TX Heartbeats: %d\n", tx_count);
    printf("RX Packets: %d\n", rx_count);
    printf("  - Sensor data (0x15): %d\n", sensor_packets);
    printf("  - Other responses: %d\n", other_packets);
    printf("\n");
    printf("Log saved to: %s\n", log_filename);
    printf("\n");
    printf("Next steps:\n");
    printf("  - Analyze log: cat %s\n", log_filename);
    printf("  - Copy to computer: scp root@vacuum:%s .\n", log_filename);
    printf("================================================================================\n");

    return 0;
}
