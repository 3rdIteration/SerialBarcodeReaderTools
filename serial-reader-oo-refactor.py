import serial
import time
import argparse
import struct
import binascii
from abc import ABC, abstractmethod

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
    def etx_bytes(self) -> bytes:
        pass

    @abstractmethod
    def create_tx(self, command: bytes, value: bytes = b'') -> bytes:
        pass

    @abstractmethod
    def parse_rx(self, data: bytes):
        pass

    def send_and_parse(self, cmd_function, value: bytes = b''):
        tx_data = cmd_function(value)
        print("Sent:", tx_data, "AsHex:", binascii.hexlify(tx_data))
        self.serial_port.write(tx_data)
        rx_data = self.serial_port.read(1024)
        print("Got:", rx_data, "AsHex:", binascii.hexlify(rx_data))
        reply, extra = self.parse_rx(rx_data)
        print("Reply:", reply, "AsHex:", binascii.hexlify(reply))
        print("Extra:", extra, "AsHex:", binascii.hexlify(extra))
        return reply, extra

    # Placeholder command methods
    def cmd_get_hw_version(self, value: bytes = b''):
        raise NotImplementedError("cmd_get_hw_version not implemented for this reader")

    def cmd_get_sw_version(self, value: bytes = b''):
        raise NotImplementedError("cmd_get_sw_version not implemented for this reader")

    def cmd_get_sw_year(self, value: bytes = b''):
        raise NotImplementedError("cmd_get_sw_year not implemented for this reader")

    def cmd_get_settings(self, value: bytes = b''):
        raise NotImplementedError("cmd_get_settings not implemented for this reader")

    def cmd_set_settings(self, value: bytes = b''):
        raise NotImplementedError("cmd_set_settings not implemented for this reader")

    def cmd_save_settings(self, value: bytes = b''):
        raise NotImplementedError("cmd_save_settings not implemented for this reader")

    def cmd_start_cont_scan(self, value: bytes = b''):
        raise NotImplementedError("cmd_start_cont_scan not implemented for this reader")

    def cmd_stop_scan(self, value: bytes = b''):
        raise NotImplementedError("cmd_stop_scan not implemented for this reader")

    def cmd_set_illumination(self, value: int = 0):
        raise NotImplementedError("cmd_set_illumination not implemented for this reader")

    def cmd_set_aimer(self, value: int = 0):
        raise NotImplementedError("cmd_set_aimer not implemented for this reader")

    def cmd_set_beeper(self, value: int = 0):
        raise NotImplementedError("cmd_set_beeper not implemented for this reader")


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

    def etx_bytes(self):
        return b''

    def create_tx(self, command: bytes, value: bytes = b'') -> bytes:
        raw_data = self.tx_header() + command + value
        checksum = self.compute_checksum(command + value)
        return raw_data + checksum + self.etx_bytes()

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
    def cmd_get_hw_version(self, value: bytes = b''):
        command = binascii.unhexlify('070100e101')
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

    def cmd_get_sw_version(self, value: bytes = b''):
        command = binascii.unhexlify('070100e201')
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

    def cmd_get_sw_year(self, value: bytes = b''):
        command = binascii.unhexlify('070100e301')
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

    def cmd_get_settings(self, value: bytes = b''):
        command = binascii.unhexlify('0701000001')
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

    def cmd_set_settings(self, value: bytes = b''):
        command = binascii.unhexlify('08010000')
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

    def cmd_save_settings(self, value: bytes = b''):
        command = binascii.unhexlify('0901000000')
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

    def cmd_start_cont_scan(self, value: bytes = b''):
        command = binascii.unhexlify('0801000201')
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

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
        command_len = len(command).to_bytes(2, byteorder='big')
        raw_data = self.tx_header() + command_len + command + value
        checksum = self.compute_checksum(command_len + command + value)
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
    def cmd_get_sw_version(self, value: bytes = b''):
        command = b'T_OUT_CVER'
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

    def cmd_start_cont_scan(self, value: bytes = b''):
        command = b'S_CMD_020E'
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

    def cmd_stop_scan(self, value: bytes = b''):
        command = b'S_CMD_020D'
        return self.send_and_parse(lambda value: self.create_tx(command, value), value)

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
        return self.send_and_parse(lambda value: self.create_tx(command), value)

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

        return self.send_and_parse(lambda value: self.create_tx(command), value)

    # Mute all        S_CMD_04F0 (Value = -1)
    # Unmute all      S_CMD_04F1 (Value = 1)
    def cmd_set_beeper(self, value: int = 0):
        if value < 0:
            command = b'S_CMD_04F0'
        elif value == 0:
            raise NotImplementedError
        elif value > 0:
            command = b'S_CMD_04F1'
        return self.send_and_parse(lambda value: self.create_tx(command), value)

# ------------------------
# Scanner Factory
# ------------------------
def detect_scanner(serial_port) -> BaseScanner:
    """
    Identify the scanner by sending a request for its software version.
    Uses send_and_parse directly for each scanner type.
    """
    gm65_scanner = GM65Scanner(serial_port)
    m3yw_scanner = M3YWScanner(serial_port)

    # Try GM65 scanner
    try:
        reply, _ = gm65_scanner.cmd_get_sw_version()
        if reply:
            print("Identified Scanner: GM65Scanner")
            return gm65_scanner
    except Exception as e:
        print("GM65Scanner not detected")

    # Try M3YW scanner
    try:
        reply, _ = m3yw_scanner.cmd_get_sw_version()
        if reply:
            print("Identified Scanner: M3YWScanner")
            return m3yw_scanner
    except Exception as e:
        print("M3YWScanner not detected")

    raise RuntimeError("No supported scanner found")

# ------------------------
# Main Script
# ------------------------
parser = argparse.ArgumentParser(description="Scanner Interface")
parser.add_argument("port", help="Serial port to use")
parser.add_argument("--hw-version", action='store_true')
parser.add_argument("--sw-version", action='store_true')
parser.add_argument("--sw-year", action='store_true')
parser.add_argument("--get-settings", action='store_true')
parser.add_argument("--set-settings")
parser.add_argument("--set-illumination", type=int)
parser.add_argument("--set-aimer", type=int)
parser.add_argument("--set-beeper", type=int)
parser.add_argument("--save-settings", action='store_true')
parser.add_argument("--start-capture", action='store_true')
parser.add_argument("--stop-capture", action='store_true')
args = parser.parse_args()

ser = serial.Serial(args.port, 9600, timeout=1)
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
elif args.stop_capture:
    print("Setting Beeper")
    reply, extra = scanner.cmd_stop_scan()
else:
    reply, extra = scanner.cmd_start_cont_scan()
    scan_duration = 10

# Keep scanning
start = time.time()
rx_data = b''
while (time.time() - start) <= scan_duration:
    rx_data += ser.read(1024)

try:
    scanner.cmd_stop_scan()
except:
    pass

ser.close()
