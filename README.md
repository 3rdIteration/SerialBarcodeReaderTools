# Serial Barcode Reader Tools
This repository is a collection of tools and information that are useful when using common serial barcode scanners. The goal is to serve a reference implmenentation of sorts to make it easier to add support for these in other DIY projects.

This script is quite chatty in the console, to let you see exactly what is going on and also to make it easy to do things like test/edit certain commands and then just copy the resultant hex output for use on smaller/simpler systems.

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

usage: serial-reader.py [--options] port

_If you don't supply any set/query commands, the scanner will start scanning for 10 seconds_

positional arguments:

  port                  Serial port to use

options:

  -h, --help                                            show this help message and exit

  --scanner SCANNER                                     Scanner type (gm65 or m3y)

  --hw-version                                          Query the device for the hardware version

  --sw-version                                          Query the device for the software version

  --sw-year                                             Query the device for the software year

  --get-settings                                        Get the settings zome (GM65) and represent as hex

  --set-settings SET_SETTINGS                           Save the supplied byte to the settings zone (GM65)

  --set-illumination SET_ILLUMINATION                   Adjust the illumination light. -1 = always off, 0 = On while scanning, 1 = always on

  --set-aimer SET_AIMER                                 Adjust the aiming light. -1 = always off, 0 = On while scanning, 1 = always on

  --set-beeper SET_BEEPER                               Adjust the beeper. -1 = muted, 1 = on

  --set-read-interval SET_READ_INTERVAL                 Adjust the minimum time between QR code reads

  --set-same-barcode-delay SET_SAME_BARCODE_DELAY       Adjust the minimumt ime between re-reading the same QR code

  --send-raw-cmd SEND_RAW_CMD                           Send a raw command to the reader

  --save-settings                                       Save settings to EEPROM (Required for GM65 to persist settings across reboots)

  --set-continuous-mode                                 Put scanner in continious mode

  --set-command-mode                                    Put scanner in command mode (will stop continious mode)

  --set-baudrate {9600,14400,19200,38400,57600,115200}  Changes the scanners baudrate and checks if this was successful

  --baudrate {9600,14400,19200,38400,57600,115200}      Sets the baudrate that this tool will use (Default 9600)

  --test-baudrates                                      Runs through a list of common baud rates to see what your device supports (Or finds out what BAUD it is currently using)


## GM65 & GM805 Barcode Scanner Specific Options

### Enabling USB Virtual Serial Port
You can either connect the barcode scanner via a serial port or use the built-in virtual serial port function.

To use this function, you need to scan the following QR code. (You may need to manually trigger scanning the first time to do this, but once enabled, this setting is persistant until reset)

![](utility_qr_codes/gm65/enable_virtual_usb.png)

### Factory Reset the Scanner
To reset all of the settings back to their defaults, scan this code.

![](utility_qr_codes/gm65/factory_reset.png)
