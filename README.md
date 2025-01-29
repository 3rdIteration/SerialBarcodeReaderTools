# GM65 Barcode Scanner

# Setup
## Requirements
This module uses pyserial, so that needs to be installed via pip

## Enabling USB Virtual Serial Port
You can either connect the barcode scanner via a serial port or use the built-in virtual serial port function.

To use this function, you need to scan the following QR code. (You may need to manually trigger scanning the first time to do this, but once enabled, this setting is persistant until reset)
![](utility_qr_codes/enable_virtual_usb.png)

## Factory Reset the Scanner
To reset all of the settings back to their defaults, scan this code.

![](utility_qr_codes/factory_reset.png)

# Usage
Connect GM65 with your computer using USB (Or a USB-Serial Interface), and make sure you are using the right port name in the gm65.py file.

usage: gm65.py [-h] [--hw-version] [--sw-version] [--sw-year] [--capture] port

Argument Parser

positional arguments:
  port          Serial port to use

options:
  -h, --help    show this help message and exit
  --hw-version  Report hardware version and exit
  --sw-version  Report software version and exit
  --sw-year     Report software year and exit
  --capture     Read a QR Code and Exit (Also default behavior if no other command given)

# User Manual

http://www.microtechnica.tv/support/manual/brm65_man.pdf





