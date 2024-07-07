import serial, time
import matplotlib.pyplot as plt
import math

ser = serial.Serial(port="/dev/cu.usbserial-0001", baudrate=115200, bytesize=8, timeout=0, stopbits=serial.STOPBITS_ONE)

figure = plt.figure()
x_data, y_data = [], []
line, = plt.plot(x_data, y_data, 'o')

angle_distance_cache = {}

CMDTYPE_HEALTH = 0xAE
CMDTYPE_MEASUREMENT = 0xAD

while True:
    if ser.in_waiting > 8:
        data = ser.read(8)
        chunk_header = data[:1]
        chunk_length = int.from_bytes(data[1:3], byteorder='big')
        chunk_version = data[3:4]
        chunk_type = data[4:5]
        command_type = int.from_bytes(data[5:6], byteorder='big')
        payload_length = int.from_bytes(data[6:8], byteorder='big')
        while ser.in_waiting < payload_length + 2:
            pass
        payload_data = ser.read(payload_length)
        payload_crc = int.from_bytes(ser.read(2), byteorder='big')
        motor_rpm = int.from_bytes(payload_data[0:1], byteorder='big') * 3
        print("Header: 0x{}, Length: {}, Version: 0x{}, Type: 0x{}, Command: 0x{}, Payload Length: {}, CRC: {}, Motor RPM: {}".format(chunk_header.hex(), chunk_length, chunk_version.hex(), chunk_type.hex(), hex(command_type), payload_length, payload_crc, motor_rpm))

        if command_type == CMDTYPE_MEASUREMENT:
            offset_angle = int.from_bytes(payload_data[1:3], byteorder='big') * 0.01
            start_angle = int.from_bytes(payload_data[3:5], byteorder='big') * 0.01
            sample_count = int((payload_length - 5) / 3)
            # print("Offset Angle: {}, Start Angle: {}, Sample Count: {}".format(offset_angle, start_angle, sample_count))
            for i in range(sample_count):
                signal_quality = int.from_bytes(payload_data[5+i*3:5+i*3+1], byteorder='big')
                angle = start_angle + i * (360/ (16 * sample_count))
                distance = int.from_bytes(payload_data[5+i*3+1:5+i*3+3], byteorder='big') * 0.25
                angle_distance_cache[round(angle)] = round(distance)
                # print("No: {}/{}, Sig Quality: {}, Angle: {}, Distance: {}".format(i, sample_count, signal_quality, angle, distance))
            
        x_data, y_data = [], []
        for angle, distance in angle_distance_cache.items():
            x_data.append(distance * math.sin(angle * math.pi / 180))
            y_data.append(distance * math.cos(angle * math.pi / 180))

        line.set_data(x_data, y_data)
        figure.gca().relim()
        figure.gca().autoscale_view()
        figure.show()
        plt.pause(0.0001)

ser.close()