# Serial Barcode Reader Tools
This repository is a collection of tools and information that are useful when using common serial barcode scanners. The goal is to serve a reference implmenentation of sorts to make it easier to add support for these in other DIY projects.

It is not supposed to be exhaustive, but rather to demonstrate a basic set of functionality to get you started with the device.

Supported Readers:
* GM65 (and GM65S) 
* GM805
* M3Y-W
_All of the commands below first attempt to auto-detect the reader you are using..._

There are also some manuals for these devices in the manuals folder of this repository.

# Setup
## Requirements
This module uses pyserial, so that needs to be installed via pip

You will also need to connect the reader to a serial port on your device. (Any USB/Serial device will generally work)

## Usage
usage: serial-reader.py [-h] [--hw-version] [--sw-version] [--sw-year] [--capture] port

positional arguments:

  port          Serial port to use

options:

  -h, --help    show this help message and exit
  
  --hw-version  Report hardware version and exit
  
  --sw-version  Report software version and exit
  
  --sw-year     Report software year and exit
  
  --capture     Read a QR Code and Exit (Also default behavior if no other command given)

## GM65 & GM805 Barcode Scanner Specific Options

### Enabling USB Virtual Serial Port
You can either connect the barcode scanner via a serial port or use the built-in virtual serial port function.

To use this function, you need to scan the following QR code. (You may need to manually trigger scanning the first time to do this, but once enabled, this setting is persistant until reset)

![](utility_qr_codes/gm65/enable_virtual_usb.png)

### Factory Reset the Scanner
To reset all of the settings back to their defaults, scan this code.

![](utility_qr_codes/gm65/factory_reset.png)
