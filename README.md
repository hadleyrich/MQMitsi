MQMitsi
=======
Copyright 2015-2017 Hadley Rich  
Website: <http://nice.net.nz>

Python scripts to interface with a Mitsubishi Heat Pump / Air Conditioner

Includes a module for UART communication with the unit itself, and also a module for interfacing through MQTT.

A work in progress. There are a couple of issues and missing things.

Example Usage
-------------


On its own, `mitsi.py` doesn't do a lot. Invoking it directly will enabled `DEBUG` logging, and simply output the details of any messages received from the heatpump.

```bash
~: ./miysi.py /dev/ttyAMA0
HP Packet: 0x7a : 00 : 0x54
Temp packet: 20
HP Packet: 0x62 : 03,00,00,0a,00,00,a8,00,00,00,00,00,00,00,00,00 : 0xa8
Set Packet: [('power', 'ON'), ('mode', 'COOL'), ('temp', 20), ('fan', 'AUTO'), ('vane', 'AUTO'), ('dir', '|')]
HP Packet: 0x62 : 02,00,00,01,03,0b,00,00,00,00,03,a8,00,00,00,00 : 0xa1
Temp packet: 20
Set Packet: [('power', 'ON'), ('mode', 'COOL'), ('temp', 20), ('fan', 'AUTO'), ('vane', 'AUTO'), ('dir', '|')]
Temp packet: 20
Set Packet: [('power', 'ON'), ('mode', 'COOL'), ('temp', 20), ('fan', 'AUTO'), ('vane', 'AUTO'), ('dir', '|')]
Temp packet: 20
Set Packet: [('power', 'ON'), ('mode', 'COOL'), ('temp', 20), ('fan', 'AUTO'), ('vane', 'AUTO'), ('dir', '|')]
Temp packet: 20
^CExiting.
```

`mitsi.py` is best used as a library in other scripts. Here's a basic example of connecting to the heatpump, then watching & modifying its state.

```python
from mitsi import HeatPump
from time import sleep

# Create our HeatPump object, and start the serial connection
heatpump = HeatPump('/dev/ttyAMA0')
heatpump.connect()

# Function to watch the heatpump for 10 seconds, and print the current state
# when a valid packet is found.
def watch_heatpump():
  for i in range(10):
      heatpump.loop()
      if heatpump.valid:
          print(heatpump.to_dict())
      sleep(1)

# Let's see the current state of the heatpump.
watch_heatpump()

# Now set the heatpump's target temperature to 22, and the fan to cooling mode.
heatpump.set({'temp':'22', 'mode': 'COOL'})

# Check the changes have taken effect.
watch_heatpump()

# Now switch off the heatpump.
heatpump.set({'power': 'OFF'})

# And watch for the heatpump to switch off.
watch_heatpump()
```

### MQTT Bridge ###

`mqmitsi` is a bridge between an MQTT broker and the `mitsi.py` library. It publishes the current state of the heatpump to the broker, and listens for state change requests. It's a very simple way of remotely controlling the heatpump.

```bash
# Example bridge between /dev/ttyAMA0 and the local MQTT broker.
~: ./mqmitsi --serial-port /dev/ttyAMA0 --mqtt-host localhost --mqtt-prefix 'heatpump' --log DEBUG
2017-06-07 04:23:05,927 INFO     Connected to MQTT broker: hassbian
2017-06-07 04:23:06,944 DEBUG    HP Packet: 0x7a : 00 : 0x54
2017-06-07 04:23:07,959 DEBUG    Temp Packet: 21
2017-06-07 04:23:07,962 DEBUG    HP Packet: 0x62 : 03,00,00,0b,00,00,aa,00,00,00,00,00,00,00,00,00 : 0xa5
2017-06-07 04:23:08,979 DEBUG    Set Packet: [('power', 'OFF'), ('mode', 'COOL'), ('temp', 22), ('fan', 'AUTO'), ('vane', 'AUTO'), ('dir', '|')]  
2017-06-07 04:23:08,996 DEBUG    HP Packet: 0x62 : 02,00,00,00,03,09,00,00,00,00,03,ac,00,00,00,00 : 0xa0
2017-06-07 04:23:10,020 DEBUG    Temp Packet: 21
2017-06-07 04:23:11,028 DEBUG    Set Packet: [('power', 'OFF'), ('mode', 'COOL'), ('temp', 22), ('fan', 'AUTO'), ('vane', 'AUTO'), ('dir', '|')]  
2017-06-07 04:23:12,034 DEBUG    Temp Packet: 21
2017-06-07 04:23:13,041 DEBUG    Set Packet: [('power', 'OFF'), ('mode', 'COOL'), ('temp', 22), ('fan', 'AUTO'), ('vane', 'AUTO'), ('dir', '|')]  
2017-06-07 04:23:14,047 DEBUG    Temp Packet: 21
2017-06-07 04:23:15,055 DEBUG    Set Packet: [('power', 'OFF'), ('mode', 'COOL'), ('temp', 22), ('fan', 'AUTO'), ('vane', 'AUTO'), ('dir', '|')]
^C2017-06-07 04:23:15,912 WARNING  Disonnected from MQTT broker: hassbian
```

#### Quick MQTT Introduction ####


If you're not familiar with MQTT, it's very easy to get started with. You can be up and running in 5 minutes, remotely controlling your heatpump. Firstly install the mosquitto mqtt broker server & cli tools.

```bash
# On Debian & Ubuntu
~: sudo apt install mosquitto mosquitto-clients
```

**Note:** by default mosquitto will bind to `*:1883`, so make sure you don't accidentally expose it to the internet.

##### Subscribing to Current State #####


The `mosquitto_sub` command let you subscribe to a specific mqtt topic, just like `mqmitsi` does internally. There are two topics:

 - **$prefix/connected** - is the bridge actively connected to the heatpump (*bool*).
 - **$prefix/state** - the data the heatpump is announcing (*json string*).

`$prefix` will match whatever `--mqtt-prefix` value you gave `mqmitsi`.

```bash
~: mosquitto_sub -t heatpump/state
{"power": "ON", "temp": 18.5, "vane": "AUTO", "mode": "COOL", "fan": "AUTO", "dir": "|", "room_temp": 17}
```

For development and troubleshooting is useful to subscribe to all topics the broker has. This can be done using the "#" topic name.

```bash
~: mosquitto_sub -t "#" -v
heatpump_upstairs/connected 1
heatpump_upstairs/state {"power": "ON", "temp": 18.5, "vane": "AUTO", "mode": "COOL", "fan": "AUTO", "dir": "|", "room_temp": 17}
```

##### Changing State #####

To issue a command to the heatpump, you can use `mosquitto_pub` to manually publish a command to the topic. There's just a single topic to do this:

 - **$prefix/command/state** - new values to set (*json string*).

```bash
~: mosquitto_pub -h localhost -t "heatpump/command/state" -m '{"power":"ON", "temp": 16, "mode": "COOL"}
```

When in debug mode, the log of `mqmitsi` will show:
```bash
[...]
2017-06-07 04:27:51,711 DEBUG    MQTT Message: heatpump/command/state : {"power": "ON", "temp": "18.0"}
2017-06-07 04:27:52,826 DEBUG    Sending packet: 0x41 : 01,04,00,00,00,0d,00,00,00,00,00,00,00,00,00,00 : 0x6c
[...]
```

*Note:* Any values you don't provide will remain as they currently are.

Issues
------

- I haven't yet figured out the codes for horizontal air direction vanes.
- Reconnection to the MQTT broker isn't always handled correctly.
- Due to the way that the heat pump communicates (slowly) you may not see a result from sending a command for a few seconds.
- There are others I haven't thought of yet - it's only been tested on two models under our own use cases.


Wanted / TODO
-------------

- More robust reconnection to MQTT broker.
- Figure out the codes for horizontal vanes.
- Implement more MQTT connection options
- CLI script for sending commands.
- Web interface example.
- Alternative MQTT protocol standards such as Homie.
- Python packaging.

LICENSE
-------
BSD - See LICENSE file
