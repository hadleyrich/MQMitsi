GerbLook
=======
Copyright 2015 Hadley Rich  
Website: <http://nice.net.nz>

Python scripts to interface with a Mitsubishi Heat Pump / Air Conditioner

Includes a module for UART communication with the unit itself, and also a module for interfacing through MQTT.

A work in progress. There are a couple of issues and missing things.

Issues
------

- I haven't yet figured out the codes for horizontal air direction vanes.
- Reconnection to the MQTT broker isn't always handled correctly.
- Due to the way that the heat pump communicates (slowly) you may not see a result from sending a command for a few seconds.
- There are others I haven't thought of yet - it's only been tested on two models under our own use cases.

Wanted / TODO
-------------

- Documentation and examples.
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

