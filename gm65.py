import serial
import time
import argparse

parser=argparse.ArgumentParser(description="Argument Parser")
parser.add_argument("port", help="Serial port to use")
parser.add_argument("--hw-version", action='store_true', help="Report hardware version and exit")
parser.add_argument("--sw-version", action='store_true', help="Report software version and exit")
parser.add_argument("--sw-year", action='store_true', help="Report software year and exit")
parser.add_argument("--capture", action='store_true', help="Read a QR Code and Exit (Also default behavior if no other command given)")
args=parser.parse_args()

ser = serial.Serial(args.port, 9600, timeout=0)

# Sets how long to wait for data from the scanner (Can be really short when just querying for settings)
scan_duration = 0.5

if args.hw_version:
    # Command to read hardware version
    scan_command = b'\x7E\x00\x07\x01\x00\xE1\x01\xAB\xCD'
elif args.sw_version:
    # Command to read software version
    scan_command = b'\x7E\x00\x07\x01\x00\xE2\x01\xAB\xCD'
elif args.sw_year:
    # Command to read Software Year
    scan_command = b'\x7E\x00\x07\x01\x00\xE3\x01\xAB\xCD'
else:
    # Scan command for normal continious read read
    scan_command = b'\x7E\x00\x08\x01\x00\x02\x01\xAB\xCD'
    scan_duration = 10

ser.write(scan_command)

time.sleep(0.1)

start_time = time.time()
data = ''

while (time.time() - start_time) <= scan_duration:
    byte = ser.read().hex()
    data += byte

# Process data a bit

# Check for successful read and remove that code and the length info
success = False
if '0200' in data[:4]:
    success = True
    data = data[8:]

# Remove data header for scanning
if '003331' in data[:6]:
    data = data[6:]

if success and len(data) > 0:
    print("Data:",data)
else:
    print("No data to display")