# serial-monitor
A python script to listen to serial output from devices that auto unlocks and reconnects when the device is flashed. The intent here is to be simple and to have a way to listen to debugging serial output that I don't have to worry about colliding with when frequently flashing my device.

With this running, you can truly just leave the serial monitor active on one screen and forget about it while flashing your image on another screen.

This script has been tested against serial communication with Arduinos on a linux host. It makes use of the fuser command to check if the device is ready to accept a new connection, so is not currently directly compatible with windows.

# Features
 - Disconnects from the device when sent the signal USR1. Once this signal is caught, the script will wait for a specific amount of time and then try to reconnect once the device is available again.
 - Allows the user to format or highlight output based on a provided list of regular expressions.
 - Toggles the DTR pin to reset the device when connected.

# Use
#### To connect:
`$ ./serial-monitor.py name [options]`
#### To send a request to disconnect temporarily:
`fuser -k -USR1 $(DEVICE_NAME)`

You can put these lines in your steps for flashing an image such as in a makefile:

`fuser -k -USR1 /dev/ttyUSB0 || true
sleep 1.5s`

This will cause any serial-monitor script listening to temporarily disconnect. If none are running, it won't cause a failure. The script listens up to a second for more serial data, so it may take a second to respond to the signal and to disconnect. Considering this, wait for a second or more after sending the signal before you start flashing any images to the device.

### Options
|Parameter|Description|Default|
|---|---|---|
|name|The device name. Ex: /dev/ttyUSB0||
|-b, --baudrate|The baudrate to use.|9600|
|-r, --regexes|The optional json file to load up that contains a list of regexes to use for formatting output.||
|-s, --sleep|The amount of seconds to unlock and sleep for before retrying to connect when requested to disconnect.|5|
|-t, --timestamps|Display timestamps before each new line received.|False|

### Output Formatting
The json file provided is expected to be a list of objects that have the following properties. These are matched and applied in the same order as they are defined.

|Property Name|Description|Example|
|---|---|---|
|pattern|The regex pattern to match with|err(or)?|
|flags|The regex flags to use|si|
|prefix|The text to insert at the beginning of a match.|\\033[1m|
|suffix|The text to insert at the end of a match.|\\033[21m|

**Note:** The script attempts to allow multiple matches from multiple regexes per output line. So you can do stacking of formatting if you don't get too fancy.
