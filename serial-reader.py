import serial
import time
import argparse
import struct
import binascii
from abc import ABC, abstractmethod

# ------------------------
# Useful constants
# ------------------------
# Not exhaustive, but supported by both the M3Y and GM65
common_baud_rates = [
    '9600',
    '14400',
    '19200',
    '38400',
    '57600',
    '115200',
]

# ------------------------
# Utility Functions
# ------------------------
def compute_crc16_xmodem(data: bytes) -> bytes:
    crc = 0
    for byte in data:
        for i in range(7, -1, -1):
            crc *= 2
            if (crc & 0x10000) != 0:
                crc ^= 0x11021
            if (byte & (1 << i)) != 0:
                crc ^= 0x1021
    crc &= 0xFFFF
    return crc.to_bytes(2, byteorder='big')

def check_crc16_xmodem(data_with_crc: bytes) -> bool:
    if len(data_with_crc) < 3:
        return False
    data = data_with_crc[:-2]
    received_crc = data_with_crc[-2:]
    calculated_crc = compute_crc16_xmodem(data)
    return received_crc == calculated_crc

def compute_bcc(data: bytes) -> bytes:
    bcc = 0
    for byte in data:
        bcc ^= byte
    return bytes([bcc])

def check_bcc(data_with_bcc: bytes) -> bool:
    if len(data_with_bcc) < 2:
        return False
    data = data_with_bcc[:-1]
    received_bcc = data_with_bcc[-1:]
    calculated_bcc = compute_bcc(data)
    return received_bcc == calculated_bcc

def set_bit(val, bit): return val | (1 << bit)
def clear_bit(val, bit): return val & ~(1 << bit)
def toggle_bit(val, bit): return val ^ (1 << bit)
def check_bit(val, bit): return (val >> bit) & 1

# ------------------------
# Abstract Scanner Class
# ------------------------
class BaseScanner(ABC):
    def __init__(self, serial_port):
        self.serial_port = serial_port
        self.commands = {}

    @abstractmethod
    def tx_header(self) -> bytes:
        pass

    @abstractmethod
    def compute_checksum(self, data: bytes) -> bytes:
        pass

    @abstractmethod
    def check_checksum(self, data: bytes) -> bool:
        pass

    @abstractmethod
    def header_ok(self) -> bytes:
        pass

    @abstractmethod
    def rx_struct_fmt(self) -> str:
        pass

    @abstractmethod
    def create_tx(self, command: bytes, value: bytes = b'') -> bytes:
        pass

    @abstractmethod
    def parse_rx(self, data: bytes):
        pass

    @abstractmethod
    def cmd_send_raw(self, value: str = ''):
        pass

    @abstractmethod
    def cmd_set_baudrate(self, value: int = 9600):
        pass

    @abstractmethod
    def get_safe_for_binaryqr(self):
        pass

    def etx_bytes(self) -> bytes:
        pass

    def send_and_parse(self, tx_data):
        print("Sent (Raw):", tx_data, "AsHex:", binascii.hexlify(tx_data))
        self.serial_port.write(tx_data)
        rx_data = self.serial_port.read(1024)
        print("Got (Raw):", rx_data, "AsHex:", binascii.hexlify(rx_data))
        reply, extra = self.parse_rx(rx_data)
        if reply:
            print("Reply:", reply, "AsHex:", binascii.hexlify(reply))
            print("Extra:", extra, "AsHex:", binascii.hexlify(extra))
        return reply, extra

    # Placeholder command methods
    def cmd_get_hw_version(self):
        raise NotImplementedError("cmd_get_hw_version not implemented for this reader")

    def cmd_get_sw_version(self):
        raise NotImplementedError("cmd_get_sw_version not implemented for this reader")

    def cmd_get_sw_year(self):
        raise NotImplementedError("cmd_get_sw_year not implemented for this reader")

    def cmd_get_settings(self):
        raise NotImplementedError("cmd_get_settings not implemented for this reader")

    def cmd_set_settings(self, value: bytes = b''):
        raise NotImplementedError("cmd_set_settings not implemented for this reader")

    def cmd_save_settings(self):
        raise NotImplementedError("cmd_save_settings not implemented for this reader")

    def cmd_set_continuous_mode(self):
        raise NotImplementedError("cmd_set_continuous_mode not implemented for this reader")

    def cmd_set_command_mode(self):
        raise NotImplementedError("cmd_set_command_mode not implemented for this reader")

    def cmd_set_illumination(self, value: int = 0):
        raise NotImplementedError("cmd_set_illumination not implemented for this reader")

    def cmd_set_aimer(self, value: int = 0):
        raise NotImplementedError("cmd_set_aimer not implemented for this reader")

    def cmd_set_beeper(self, value: int = 0):
        raise NotImplementedError("cmd_set_beeper not implemented for this reader")

    def cmd_set_read_interval(self, value: float = 0):
        raise NotImplementedError("cmd_set_read_interval not implemented for this reader")

    def cmd_set_same_barcode_delay(self, value: float = 0):
        raise NotImplementedError("cmd_set_same_barcode_delay not implemented for this reader")

    def test_baudrates(self):
        for baudrate in common_baud_rates + list(reversed(common_baud_rates)):
            works, _ = self.cmd_set_baudrate(int(baudrate))
            if works:
                print(baudrate, "Success")
            else:
                print(baudrate, "Failed")

    def find_baudrate(self):
        for baudrate in common_baud_rates:
            print("Checking at...", baudrate)
            self.serial_port.baudrate = int(baudrate)
            reply, _ = self.cmd_get_sw_version()
            if reply:
                return baudrate

        return None

# ------------------------
# GM65 Scanner
# ------------------------
class GM65Scanner(BaseScanner):
    def __init__(self, serial_port):
        super().__init__(serial_port)

    def tx_header(self):
        return binascii.unhexlify('7e00')

    def compute_checksum(self, data: bytes) -> bytes:
        return compute_crc16_xmodem(data)

    def check_checksum(self, data: bytes) -> bool:
        return check_crc16_xmodem(data)

    def header_ok(self):
        return b'020000'

    def rx_struct_fmt(self):
        return "3sB"

    def create_tx(self, command: bytes, value: bytes = b'') -> bytes:
        raw_data = self.tx_header() + command + value
        checksum = self.compute_checksum(command + value)
        return raw_data + checksum

    def parse_rx(self, data: bytes):
        header_len = struct.calcsize(self.rx_struct_fmt())
        try:
            header, data_len = struct.unpack(self.rx_struct_fmt(), data[:header_len])
        except struct.error:
            return None, b''

        if header.hex() in self.header_ok().decode():
            if self.check_checksum(data[1:header_len + data_len + 2]):
                return data[header_len:header_len + data_len], data[header_len + data_len + 2:]
        return None, b''

    # Command functions for GM65 that directly create the command and send
    def cmd_get_hw_version(self):
        command = binascii.unhexlify('070100e101')
        return self.send_and_parse(self.create_tx(command))

    def cmd_get_sw_version(self):
        command = binascii.unhexlify('070100e201')
        return self.send_and_parse(self.create_tx(command))

    def cmd_get_sw_year(self):
        command = binascii.unhexlify('070100e301')
        return self.send_and_parse(self.create_tx(command))

    def cmd_get_settings(self):
        command = binascii.unhexlify('0701000001')
        return self.send_and_parse(self.create_tx(command))

    def cmd_set_settings(self, value: bytes = b''):
        command = binascii.unhexlify('08010000')
        return self.send_and_parse(self.create_tx(command, value))

    def cmd_save_settings(self):
        command = binascii.unhexlify('0901000000')
        return self.send_and_parse(self.create_tx(command))

    def cmd_set_continuous_mode(self):
        settings, extra = self.cmd_get_settings()
        settings_int = settings[0]
        settings_int = set_bit(settings_int, 1)
        settings_int = clear_bit(settings_int, 0)
        self.cmd_set_settings(bytes([settings_int]))
        self.cmd_save_settings()
        return True, None

    def cmd_set_command_mode(self):
        settings, extra = self.cmd_get_settings()
        settings_int = settings[0]
        settings_int = set_bit(settings_int, 0)
        settings_int = clear_bit(settings_int, 1)
        self.cmd_set_settings(bytes([settings_int]))
        self.cmd_save_settings()
        return True, None

    # Always Off   (Value = -1)
    # Normal Mode  (Value = 0)
    # Always On    (Value = 1)
    def cmd_set_illumination(self, value: int = 0):
        settings, extra = self.cmd_get_settings()
        settings_int = settings[0]
        if value < 0:
            settings_int = clear_bit(settings_int, 3)
            settings_int = clear_bit(settings_int, 2)
        elif value == 0:
            settings_int = set_bit(settings_int, 2)
            settings_int = clear_bit(settings_int, 3)
        elif value > 0:
            settings_int = set_bit(settings_int, 3)
            settings_int = set_bit(settings_int, 2)
        self.cmd_set_settings(bytes([settings_int]))
        self.cmd_save_settings()
        return True, None

    # Always Off   (Value = -1)
    # Normal Mode  (Value = 0)
    # Always On    (Value = 1)
    def cmd_set_aimer(self, value: int = 0):
        settings, extra = self.cmd_get_settings()
        settings_int = settings[0]
        if value < 0:
            settings_int = clear_bit(settings_int, 5)
            settings_int = clear_bit(settings_int, 4)
        elif value == 0:
            settings_int = set_bit(settings_int, 4)
            settings_int = clear_bit(settings_int, 5)
        elif value > 0:
            settings_int = set_bit(settings_int, 5)
            settings_int = set_bit(settings_int, 4)
        self.cmd_set_settings(bytes([settings_int]))
        self.cmd_save_settings()
        return True, None

    # Muted  (Value = -1)
    # On     (Value = 1)
    def cmd_set_beeper(self, value: int = 0):
        settings, extra = self.cmd_get_settings()
        settings_int = settings[0]
        if value < 0:
            settings_int = clear_bit(settings_int, 6)
        elif value == 0:
            raise NotImplementedError
        elif value > 0:
            settings_int = set_bit(settings_int, 6)
        self.cmd_set_settings(bytes([settings_int]))
        self.cmd_save_settings()
        return True, None

    def cmd_set_read_interval(self, value: float = 0):
        command = binascii.unhexlify('08010005')
        value = (round(value * 10)).to_bytes(1)
        return self.send_and_parse(self.create_tx(command, value))

    def cmd_set_same_barcode_delay(self, value: float = 0):
        if value > 12.7: # Value needs to be below 12.7s as bit7 is used for enable/disable the feature
            raise ValueError
        command = binascii.unhexlify('08010013')
        value = (round(value * 10)).to_bytes(1)
        value = set_bit(value[0], 7)
        return self.send_and_parse(self.create_tx(command, bytes([value])))

    def cmd_send_raw(self, value: str = ''):
        command = binascii.unhexlify(value)
        return self.send_and_parse(self.create_tx(command))


    def cmd_set_baudrate(self, value: int = 9600):
        baudvalues = { # Note that byte order here is reversed compared to what is in the datasheet...
            9600: b'3901',
            14400: b'd000',
            19200: b'9c00',
            38400: b'4e00',
            57600: b'3400',
            115200: b'1a00'
        }
        command = binascii.unhexlify('0802002A')
        reply, extra = self.send_and_parse(self.create_tx(command, binascii.unhexlify(baudvalues[value])))
        self.serial_port.baudrate = value
        # Test to see if everything worked...
        reply, extra = self.cmd_get_sw_version()
        if reply:
            return True, None
        else:
            return False, None

    def get_safe_for_binaryqr(self):
        gm65_known_bad_sw_versions = [b'69'] # Versions known to scan binaryQR codes unreliably
        gm65_known_good_sw_version = [b'87', b'af'] # Versions known to be work correctly
        version, extra = self.cmd_get_sw_version()
        version = binascii.hexlify(version)
        print("Got Software Version:", version, "Checking...")
        if version in gm65_known_bad_sw_versions:
            return False
        elif version in gm65_known_good_sw_version:
            return True
        else:
            return None

# ------------------------
# M3Y-W Scanner
# ------------------------
class M3YWScanner(BaseScanner):
    def __init__(self, serial_port):
        super().__init__(serial_port)

    def tx_header(self):
        return binascii.unhexlify('5a00')

    def compute_checksum(self, data: bytes) -> bytes:
        return compute_bcc(data)

    def check_checksum(self, data: bytes) -> bool:
        return check_bcc(data)

    def header_ok(self):
        return b'5a01'

    def rx_struct_fmt(self):
        return ">2sH"

    def etx_bytes(self):
        return binascii.unhexlify('a5')

    def create_tx(self, command: bytes, value: bytes = b'') -> bytes:
        # Value not used here in this reader
        command_len = len(command).to_bytes(2, byteorder='big')
        raw_data = self.tx_header() + command_len + command
        checksum = self.compute_checksum(command_len + command)
        return raw_data + checksum + self.etx_bytes()

    def parse_rx(self, data: bytes):
        header_len = struct.calcsize(self.rx_struct_fmt())
        try:
            header, data_len = struct.unpack(self.rx_struct_fmt(), data[:header_len])
        except struct.error:
            return None, b''

        if header.hex() in self.header_ok().decode():
            if self.check_checksum(data[header_len - 3:header_len + data_len + 1]):
                return data[header_len:header_len + data_len], data[header_len + data_len + 2:]
        return None, b''

    # Command functions for M3YW that directly create the command and send
    def cmd_get_sw_version(self):
        command = b'T_OUT_CVER'
        return self.send_and_parse(self.create_tx(command))

    def cmd_set_continuous_mode(self):
        command = b'S_CMD_020E'
        return self.send_and_parse(self.create_tx(command))

    def cmd_set_command_mode(self):
        command = b'S_CMD_020D'
        return self.send_and_parse(self.create_tx(command))

    # Command functions for M3YW that directly create the command and send
    # Always Off  S_CMD_03L0 (Value = -1)
    # Normal Mode S_CMD_03L2 (Value = 0)
    # Always On   S_CMD_03L1 (Value = 1)
    def cmd_set_illumination(self, value: int = 0):
        if value < 0:
            command = b'S_CMD_03L0'
        elif value == 0:
            command = b'S_CMD_03L2'
        elif value > 0:
            command = b'S_CMD_03L1'
        return self.send_and_parse(self.create_tx(command))

    # Always Off  S_CMD_03A0 (Value = -1)
    # Normal Mode S_CMD_03A2 (Value = 0)
    # Always On S_CMD_03A1 (Value = 1)
    def cmd_set_aimer(self, value: int = 0):
        if value < 0:
            command = b'S_CMD_03A0'
        elif value == 0:
            command = b'S_CMD_03A2'
        elif value > 0:
            command = b'S_CMD_03A1'

        return self.send_and_parse(self.create_tx(command))

    # Mute all        S_CMD_04F0 (Value = -1)
    # Unmute all      S_CMD_04F1 (Value = 1)
    def cmd_set_beeper(self, value: int = 0):
        if value < 0:
            command = b'S_CMD_04F0'
        elif value == 0:
            raise NotImplementedError
        elif value > 0:
            command = b'S_CMD_04F1'
        return self.send_and_parse(self.create_tx(command))

    def cmd_set_read_interval(self, value: float = 0):
        command = b'S_CMD_MARR' + str(round(value*1000)).encode()
        return self.send_and_parse(self.create_tx(command))

    def cmd_set_same_barcode_delay(self, value: float = 0):
        command = b'S_CMD_MA31'
        self.send_and_parse(self.create_tx(command))
        command = b'S_CMD_MA41'
        self.send_and_parse(self.create_tx(command))
        command = b'S_CMD_MARI' + str(round(value*1000)).encode()
        return self.send_and_parse(self.create_tx(command))

    def cmd_send_raw(self, value: str = ''):
        command = value.encode()
        return self.send_and_parse(self.create_tx(command))

    def cmd_set_baudrate(self, value: int = 9600):
        command = b'S_CMD_H3BR' + str(value).encode()
        reply, extra = self.send_and_parse(self.create_tx(command, value))
        self.serial_port.baudrate = value
        # Test to see if everything worked...
        reply, extra = self.cmd_get_sw_version()
        if reply:
            return True, None
        else:
            return False, None

    def get_safe_for_binaryqr(self):
        return True

# ------------------------
# Scanner Factory
# ------------------------
def detect_scanner(serial_port) -> BaseScanner:
    """
    Identify the scanner by sending a request for its software version.
    """
    for scanner in [GM65Scanner, M3YWScanner]:
        scanner = scanner(serial_port)
        print("Trying", scanner.__class__.__name__)
        foundbaud = scanner.find_baudrate()
        if foundbaud:
            print("Identified Scanner:", scanner.__class__.__name__, "at baudrate:", foundbaud)
            return scanner
        else:
            print(scanner.__class__.__name__, "not detected")

    raise RuntimeError("No supported scanner found")

# ------------------------
# Main Script
# ------------------------
parser = argparse.ArgumentParser(description="Scanner Interface")
parser.add_argument("port", help="Serial port to use")
parser.add_argument("--scanner", type=str, help="Scanner type (gm65 or m3y)")
parser.add_argument("--hw-version", action='store_true', help="Query the device for the hardware version")
parser.add_argument("--sw-version", action='store_true', help="Query the device for the software version")
parser.add_argument("--sw-year", action='store_true', help="Query the device for the software year")
parser.add_argument("--get-settings", action='store_true', help="Get the settings zome (GM65) and represent as hex")
parser.add_argument("--get-safe-for-binary-qr", help="Check if the connected reader is know to be safe for binary QR scanning")
parser.add_argument("--set-settings", help="Save the supplied byte to the settings zone (GM65)")
parser.add_argument("--set-illumination", type=int, help="Adjust the illumination light. -1 = always off, 0 = On while scanning, 1 = always on")
parser.add_argument("--set-aimer", type=int, help="Adjust the aiming light. -1 = always off, 0 = On while scanning, 1 = always on")
parser.add_argument("--set-beeper", type=int, help="Adjust the beeper. -1 = muted, 1 = on")
parser.add_argument("--set-read-interval", type=float, help="Adjust the minimum time between QR code reads")
parser.add_argument("--set-same-barcode-delay", type=float, help="Adjust the minimumt ime between re-reading the same QR code")
parser.add_argument("--send-raw-cmd", type=str, help="Send a raw command to the reader")
parser.add_argument("--save-settings", action='store_true', help="Save settings to EEPROM (Required for GM65 to persist settings across reboots)")
parser.add_argument("--set-continuous-mode", action='store_true', help="Put scanner in continious mode")
parser.add_argument("--set-command-mode", action='store_true', help="Put scanner in command mode (will stop continious mode)")
parser.add_argument("--set-baudrate", choices=common_baud_rates, help="Changes the scanners baudrate and checks if this was successful")
parser.add_argument("--baudrate", choices=common_baud_rates, help="Sets the baudrate that this tool will use (Default 9600)")
parser.add_argument("--test-baudrates", action='store_true', help="Runs through a list of common baud rates to see what your device supports (Or finds out what BAUD it is currently using)")

args = parser.parse_args()

baudrate = 9600
if args.baudrate:
    baudrate = args.baudrate

ser = serial.Serial(args.port, baudrate, timeout=1)

if args.scanner:
    if "gm65" in args.scanner.lower():
        scanner = GM65Scanner(ser)
    elif "m3y" in args.scanner.lower():
        scanner = M3YWScanner(ser)
else:
    scanner = detect_scanner(ser)

scan_duration = 1
if args.hw_version:
    reply, extra = scanner.cmd_get_hw_version()
elif args.sw_version:
    reply, extra = scanner.cmd_get_sw_version()
elif args.sw_year:
    reply, extra = scanner.cmd_get_sw_year()
elif args.get_settings:
    reply, extra = scanner.cmd_get_settings()
elif args.set_settings:
    reply, extra = scanner.cmd_set_settings(args.set_settings.encode())
elif args.save_settings:
    reply, extra = scanner.cmd_save_settings()
elif args.set_illumination is not None:
    print("Setting Illumination")
    reply, extra = scanner.cmd_set_illumination(args.set_illumination)
elif args.set_aimer is not None:
    print("Setting Aimer")
    reply, extra = scanner.cmd_set_aimer(args.set_aimer)
elif args.set_beeper is not None:
    print("Setting Beeper")
    reply, extra = scanner.cmd_set_beeper(args.set_beeper)
elif args.set_read_interval is not None:
    print("Setting Read Interval")
    reply, extra = scanner.cmd_set_read_interval(args.set_read_interval)
elif args.set_same_barcode_delay is not None:
    print("Setting Same Barcode Delay")
    reply, extra = scanner.cmd_set_same_barcode_delay(args.set_same_barcode_delay)
elif args.send_raw_cmd:
    print("Sending raw command")
    reply, extra = scanner.cmd_send_raw(args.send_raw_cmd)
elif args.set_continuous_mode:
    print("Setting Continuous Mode")
    reply, extra = scanner.cmd_set_continuous_mode()
elif args.set_command_mode:
    print("Setting Command Mode")
    reply, extra = scanner.cmd_set_command_mode()
elif args.set_baudrate is not None:
    print("Setting Baud Rate")
    reply, extra = scanner.cmd_set_baudrate(int(args.set_baudrate))
    if reply:
        print("Baudrate Changed Successfully!")
    else:
        print("Baudrate Change Failed...")
elif args.test_baudrates:
    scanner.test_baudrates()
elif args.get_safe_for_binary_qr:
    safe = scanner.get_safe_for_binaryqr()
    if safe is not None:
        if safe:
            print("Good News: Safe to use")
        else:
            print("WARNING: Known to be unsafe for binary QR scanning")
    else:
        print("Unsure... Unable to match software version as known-good or known-bad...")

else:
    print("Setting Continuous Mode")
    reply, extra = scanner.cmd_set_continuous_mode()

    print("Scanning for 10 Seconds")
    scan_duration = 10
    # Keep scanning
    start = time.time()
    rx_data = b''
    while (time.time() - start) <= scan_duration:
        rx_data += ser.read(1024)

    print("Setting Command Mode")
    reply, extra = scanner.cmd_set_command_mode()
    print("Got:", rx_data, "AsHex:", binascii.hexlify(rx_data))

ser.close()
