#!/usr/bin/env python

import sys
import time
import serial
import logging
from copy import copy
from mitsi_lookup import (
    POWER,
    TEMP,
    ROOM_TEMP,
    MODE,
    VANE,
    DIR,
    FAN,
    CONTROL_PACKET_VALUES,
    CONTROL_PACKET_POSITIONS,
)

HEADER_LEN = 5

log = logging.getLogger(__name__)


class HeatPump(object):
    reported_attributes = ("power", "mode", "temp", "fan", "vane", "dir", "room_temp")

    def __init__(self, port=None, **kwargs):
        self.port = port
        for item in self.reported_attributes:
            setattr(self, item, kwargs.get(item, None))
        self.dirty = True
        self.room_temp = None
        self.info_packet_index = 0
        self.last_send = 0
        self.current_packet = None
        self.packet_history = {}
        self.wanted_state = {}
        self.start_packet = Packet.build(0x5A, [0xCA, 0x01])
        self.info_packets = [
            Packet.build(0x42, [0x02] + [0x00] * 0x0F),
            Packet.build(0x42, [0x03] + [0x00] * 0x0F),
        ]

    def __setattr__(self, item, value):
        """ Set self.dirty when setting a reported attribute. Used downsteam to
            determine if there's a change in state since we last looked. """
        if item in self.reported_attributes:
            if getattr(self, item, None) != value:
                self.dirty = True
        super(HeatPump, self).__setattr__(item, value)

    def to_dict(self):
        """ Return all the heatpump's reported attributes as
            a dict. """
        d = {}
        for item in self.reported_attributes:
            d[item] = getattr(self, item)
        return d

    def from_dict(self, d):
        """ Set all the heatpump's reported attributes from
            the provided dict. """
        for item in self.reported_attributes:
            if d.get(item, None):
                setattr(self, item, d.get(item))

    @property
    def valid(self):
        """ Validates every reported attribute has been set as an
            actual HeatPump() attribute. """
        for item in self.reported_attributes:
            if getattr(self, item, None) is None:
                return False
        return True

    def connect(self):
        """ Establish a serial connection to self.port. """
        if self.port:
            self.ser = serial.Serial(
                self.port, 2400, parity=serial.PARITY_EVEN, timeout=0
            )
            self.ser.write(bytearray(self.start_packet.bytes))

    def map_set_packet_to_attributes(self):
        """ Match data in a Packet() to the relevant HeatPump() attribute. """
        result = []
        for attribute_name in self.reported_attributes:

            # Get the lookup dictonary name from the attribute name
            # e.g. 'power' -> 'POWER'
            ATTRIBUTE_NAME = attribute_name.upper()

            # See what position this attribute should be in the Packet()
            # e.g. CONTROL_PACKET_POSITIONS['POWER']
            position = CONTROL_PACKET_POSITIONS.get(ATTRIBUTE_NAME, None)

            if position:

                # Retrieve the value from the Packet()
                raw_value = self.current_packet.data[position]

                # Dynamically get the lookup dictonary for an attribute,
                # and lookup the human form of the value.
                # e.g. "POWER"
                try:
                    converted_value = globals()[ATTRIBUTE_NAME].lookup(raw_value)
                except KeyError:
                    log.error("Failed to lookup %s[%s]" % (ATTRIBUTE_NAME, raw_value))

                # Set the attribute on the HeatPump() object.
                # e.g. "self.power = 'ON'"
                setattr(self, attribute_name, converted_value)
                result.append((attribute_name, converted_value))

        log.debug("Set Packet: %s" % result)

    def loop(self):
        res = self.ser.read(22)
        for c in res:
            val = ord(c)
            if val == 0xFC:
                self.current_packet = Packet()
            if not self.current_packet:
                log.debug("No packet!")
                return
            self.current_packet.bytes.append(val)
            if len(self.current_packet.bytes) == HEADER_LEN:
                self.current_packet.data_len = val
            if self.current_packet.complete:
                if self.current_packet.valid:
                    if self.current_packet.data[0] == 0x02:  # Set Packet
                        self.map_set_packet_to_attributes()
                    if self.current_packet.data[0] == 0x03:  # Temp Packet
                        self.room_temp = ROOM_TEMP.lookup(self.current_packet.data[3])
                        log.debug("Temp Packet: %s" % self.room_temp)

                    if (
                        self.current_packet.data[0] in self.packet_history
                        and self.current_packet
                        == self.packet_history[self.current_packet.data[0]]
                    ):
                        pass
                    else:
                        log.debug(
                            "HP Packet: 0x%x : %s : 0x%x"
                            % (
                                self.current_packet.type,
                                ",".join(
                                    ["%02x" % x for x in self.current_packet.data]
                                ),
                                self.current_packet.checksum,
                            )
                        )
                    self.packet_history[
                        self.current_packet.data[0]
                    ] = self.current_packet
                    self.current_packet = None
                else:
                    log.info("HP Packet Invalid")
                    self.current_packet = None

        if time.time() - self.last_send > 1:
            # Check if our current state matches the wanted state
            if self.wanted_state:
                wanted = copy(self)
                wanted.from_dict(self.wanted_state)
                packet = self.diff(wanted)
                if packet:
                    log.debug(
                        "Sending packet: 0x%x : %s : 0x%x"
                        % (
                            packet.type,
                            ",".join(["%02x" % x for x in packet.data]),
                            packet.checksum,
                        )
                    )
                    self.ser.write(bytearray(packet.bytes))
                    self.last_send = time.time()
                    self.info_packet_index = 0
                    time.sleep(1)
                else:
                    self.wanted_state = {}

            self.ser.write(bytearray(self.info_packets[self.info_packet_index].bytes))
            self.last_send = time.time()
            self.info_packet_index += 1
            if self.info_packet_index >= len(self.info_packets):
                self.info_packet_index = 0

    def set(self, state):
        self.wanted_state.update(state)

    def diff(self, other):
        if not other:
            return
        data = [0x00] * 0x10
        data[0] = 0x01
        if self.power != other.power:
            data[1] += CONTROL_PACKET_VALUES["POWER"]
            data[CONTROL_PACKET_POSITIONS["POWER"]] = POWER[other.power]
        if self.mode != other.mode:
            data[1] += CONTROL_PACKET_VALUES["MODE"]
            data[CONTROL_PACKET_POSITIONS["MODE"]] = MODE[other.mode]
        if other.temp and self.temp != float(other.temp):
            data[1] += CONTROL_PACKET_VALUES["TEMP"]
            data[CONTROL_PACKET_POSITIONS["TEMP"]] = TEMP[float(other.temp)]
        if self.fan != other.fan:
            data[1] += CONTROL_PACKET_VALUES["FAN"]
            data[CONTROL_PACKET_POSITIONS["FAN"]] = FAN[other.fan]
        if self.vane != other.vane:
            data[1] += CONTROL_PACKET_VALUES["VANE"]
            data[CONTROL_PACKET_POSITIONS["VANE"]] = VANE[other.vane]
        if self.dir != other.dir:
            data[1] += CONTROL_PACKET_VALUES["DIR"]
            data[CONTROL_PACKET_POSITIONS["DIR"]] = DIR[other.dir]
        if data[1] > 0x00:
            return Packet.build(0x41, data)
        return None


class Packet(object):
    START_BYTE = 0xFC
    EXTRA_HEADER = [0x01, 0x30]

    def __init__(self):
        self.bytes = []
        self.data_len = None

    def __eq__(self, other):
        return self.bytes == other.bytes

    def __str__(self):
        return ",".join(["0x%02x" % x for x in self.bytes])

    @classmethod
    def build(cls, type, data):
        c = cls()
        c.bytes = [c.START_BYTE, type] + c.EXTRA_HEADER
        c.bytes.append(len(data))
        c.bytes += data
        c.bytes.append(0xFC - (sum(c.bytes) & 0xFF))
        return c

    @property
    def checksum(self):
        return 0xFC - (sum(self.bytes[0:-1]) & 0xFF)

    @property
    def type(self):
        return self.bytes[1]

    @property
    def complete(self):
        if (
            self.data_len is not None
            and len(self.bytes) == HEADER_LEN + self.data_len + 1
        ):
            return True
        return False

    @property
    def valid(self):
        if self.complete and self.checksum == self.bytes[-1]:
            return True
        return False

    @property
    def data(self):
        return self.bytes[HEADER_LEN:-1]


if __name__ == "__main__":
    log.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    log.addHandler(console)
    if len(sys.argv) >= 2:
        hp = HeatPump(sys.argv[1])
        hp.connect()

        while True:
            try:
                hp.loop()
                time.sleep(1)
            except KeyboardInterrupt:
                print("Exiting.")
                sys.exit(0)

    print("Expected the first argument to be a serial port.")
    sys.exit(1)
