import serial
import time
import argparse
import struct
import binascii

# Settings for different scanner type
scanner_module_data = {
    "GM65": {
        "tx_header_0": b'7e00',
        "tx_checksum_bytes": 'compute_crc',
        "rx_header_ok": b'020000',
        "rx_header_struct_fmt": "3sB",
        "cmd_get_hw_version": b'070100e101',
        "cmd_get_sw_version": b'070100e201',
        "cmd_get_sw_year": b'070100e301',
        "cmd_get_settings": b'0701000001',
        "cmd_set_settings": b'08010000',
        "cmd_save_settings": b'0901000000',
        "cmd_start_cont_scan": b'0801000201',
    },
    "M3Y-W": {
        "tx_header_0": b'7e00',
        "tx_checksum_bytes": 'compute_bcc',
        "rx_header_ok": b'020000',
        "rx_header_struct_fmt": "3sB",
        "cmd_get_hw_version": b'070100e101',
        "cmd_get_sw_version": b'070100e201',
        "cmd_get_sw_year": b'070100e301',
        "cmd_start_cont_scan": b'0801000201',
    },
}

# Some GM65 (and compatible readers) can't correctly/reliabily read binary QR codes. This seems to follow SW version
gm65_known_bad_sw_versions = [69]
gm65_known_good_sw_version = [87]
gm65_known_good_sw_year = [87]

parser=argparse.ArgumentParser(description="Argument Parser")
parser.add_argument("port", help="Serial port to use")
parser.add_argument("--hw-version", action='store_true', help="Report hardware version and exit")
parser.add_argument("--sw-version", action='store_true', help="Report software version and exit")
parser.add_argument("--sw-year", action='store_true', help="Report software year and exit")
parser.add_argument("--get-settings", action='store_true', help="Get the settings (Aim Light, Beep, Illumination Light) and exit")
parser.add_argument("--set-settings", help="Set the settings byte (Aim Light, Beep, Illumination Light) and exit")
parser.add_argument("--save-settings", action='store_true', help="Save the settings byte to EEPROM (Aim Light, Beep, Illumination Light) and exit")
parser.add_argument("--capture", action='store_true', help="Scan QR Codes for 10 seconds and Exit (Also default behavior if no other command given)")
args=parser.parse_args()

# Thanks ChatGPT ;)
def compute_crc16_xmodem(data: bytes) -> bytes:
    """
    Calculate the CRC-16 checksum for the given data using a bitwise method.

    This function computes a 16-bit CRC checksum based on the CRC-16-CCITT (XModem)
    polynomial (0x1021). It processes the data byte by byte, shifting and applying
    the CRC polynomial bitwise to calculate the checksum.

    Parameters:
    - data (bytes): The input data for which the CRC is to be calculated.
      The data is a sequence of bytes (e.g., b'Hello').

    Returns:
    - bytes: A 2-byte checksum in big-endian format representing the CRC-16
      checksum of the input data. The result will be a byte array with
      the high byte first and the low byte second.

    Process:
    - For each byte in the input data:
        - The CRC is shifted left by 1 bit.
        - If the high bit of the CRC is set (i.e., overflow occurs),
          the polynomial 0x11021 is XORed with the CRC.
        - The bits of the current byte are processed from the highest to
          the lowest bit (bit 7 to bit 0), and if the bit is set, the
          polynomial 0x1021 is XORed with the CRC.
    - The final CRC is returned as a 2-byte value in big-endian order.

    Example:
    #>>> data = b"Hello"
    #>>> compute_crc16_xmodem(data)
    b'\xee\x8a'  # Returns the calculated CRC as a 2-byte big-endian value
    """
    crc = 0
    for byte in data:
        for i in range(7, -1, -1):  # From bit 7 (MSB) to bit 0 (LSB)
            crc *= 2
            if (crc & 0x10000) != 0:
                crc ^= 0x11021
            if (byte & (1 << i)) != 0:
                crc ^= 0x1021
    crc &= 0xFFFF  # Trim to 16 bits
    return crc.to_bytes(2, byteorder='big')  # Return as big-endian bytes


def check_crc16_xmodem(data_with_crc: bytes) -> bool:
    """
    Check if the CRC of the data (with CRC appended) is correct.

    Arguments:
    - data_with_crc: bytes - the data with the CRC appended at the end.

    Returns:
    - True if the CRC is valid, False if the CRC is invalid.
    """
    if len(data_with_crc) < 3:
        raise ValueError("Data must include at least one byte of data plus two CRC bytes.")

    # Separate the data and the CRC
    data = data_with_crc[:-2]
    received_crc = data_with_crc[-2:]

    # Calculate CRC for the data
    calculated_crc = compute_crc16_xmodem(data)

    # Check if the calculated CRC matches the received CRC
    return received_crc == calculated_crc

# Thanks ChatGPT ;)
def compute_bcc(data: bytes) -> int:
    """Compute the Block Check Character (BCC) using XOR."""
    bcc = 0
    for byte in data:
        bcc ^= byte
    return bcc

def check_bcc(data_with_bcc: bytes) -> bool:
    """Check if the BCC is correct. Assumes the last byte is the BCC."""
    if len(data_with_bcc) < 2:
        raise ValueError("Input must include at least one byte of data and one byte for BCC.")

    data = data_with_bcc[:-1]
    received_bcc = data_with_bcc[-1]
    calculated_bcc = compute_bcc(data)

    return received_bcc == calculated_bcc

def create_tx(reader, command, value = b''):
    reader_info = scanner_module_data[reader]
    if reader_info["tx_checksum_bytes"] == "compute_crc":
        checksum = (compute_crc16_xmodem(binascii.unhexlify(reader_info[command] + value)))
    elif reader_info["tx_checksum_bytes"] == "compute_bcc":
        checksum = (compute_bcc(binascii.unhexlify(reader_info[command] + value)))
    return binascii.unhexlify(reader_info["tx_header_0"] + reader_info[command] + value) + checksum

def parse_rx(reader, data):
    reader_info = scanner_module_data[reader]
    header_len = struct.calcsize(reader_info["rx_header_struct_fmt"])
    header, data_len = struct.unpack(reader_info["rx_header_struct_fmt"], data[:header_len])

    if header.hex() in reader_info["rx_header_ok"].decode():
        if check_crc16_xmodem(data[1:header_len + data_len + 2]):
            return data[header_len:header_len + data_len], data[header_len + data_len + 2:]
    else:
        return None

ser = serial.Serial(args.port, 9600, timeout=0.5)

# Determine the reader type
for test_reader in scanner_module_data.keys():
    print("Looking for", test_reader)
    ser.write(create_tx(test_reader,"cmd_get_sw_version")) # This command is available on most readers
    if parse_rx(test_reader,ser.read(64)): # This will return none readers like the M3Y-W
        print("Identified Reader:", test_reader)
        reader = test_reader
        break

if not reader:
    exit("No supported reader found...")

# Sets how long to wait for data from the scanner (Can be really short when just querying for settings)
scan_duration = 0.5

if args.hw_version:
    print("Getting Hardware Version...")
    scan_command = create_tx(reader,"cmd_get_hw_version")
elif args.sw_version:
    print("Getting Software Version...")
    scan_command = create_tx(reader,"cmd_get_sw_version")
elif args.sw_year:
    print("Getting Software Year...")
    scan_command = create_tx(reader,"cmd_get_sw_year")
elif args.get_settings:
    print("Getting Settings Year...")
    scan_command = create_tx(reader,"cmd_get_settings")
elif args.set_settings:
    print("Setting Settings...")
    scan_command = create_tx(reader,"cmd_set_settings", args.set_settings.encode())
elif args.save_settings:
    print("Saving Settings...")
    scan_command = create_tx(reader,"cmd_save_settings")
else:
    print("Scanning...")
    # Scan command for normal continious read
    scan_command = create_tx(reader, "cmd_start_cont_scan")
    scan_duration = 10

print("Sending:", scan_command, ", AsHex:", binascii.hexlify(scan_command))
ser.write(scan_command)

start_time = time.time()
rx_data = b''

while (time.time() - start_time) <= scan_duration:
    byte = ser.read(1024)
    rx_data += byte

print("Got Raw Data:",rx_data, ", AsHex:", binascii.hexlify(rx_data))

# Process data a bit
reply, extra_data = parse_rx(reader,rx_data)

print("Reply Data:", reply.hex())
print("Extra Data:", extra_data.hex())
