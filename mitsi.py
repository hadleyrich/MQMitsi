#!/usr/bin/env python

import sys
import time
import serial
import logging
from copy import copy

HEADER_LEN = 5

log = logging.getLogger(__name__)


class LookupDict(dict):
    def lookup(self, value):
        return [k for k, v in self.items() if v == value][0]

POWER = LookupDict({
    'OFF': 0x00,
    'ON': 0x01,
})

TEMP = LookupDict({
    31: 0x00,
    30: 0x01,
    29: 0x02,
    28: 0x03,
    27: 0x04,
    26: 0x05,
    25: 0x06,
    24: 0x07,
    23: 0x08,
    22: 0x09,
    21: 0x0a,
    20: 0x0b,
    19: 0x0c,
    18: 0x0d,
    17: 0x0e,
    16: 0x0f,
})

ROOM_TEMP = LookupDict({
    10: 0x00,
    11: 0x01,
    12: 0x02,
    13: 0x03,
    14: 0x04,
    15: 0x05,
    16: 0x06,
    17: 0x07,
    18: 0x08,
    19: 0x09,
    20: 0x0a,
    21: 0x0b,
    22: 0x0c,
    23: 0x0d,
    24: 0x0e,
    25: 0x0f,
    26: 0x10,
    27: 0x11,
    28: 0x12,
    29: 0x13,
    30: 0x14,
    31: 0x15,
    32: 0x16,
    33: 0x17,
    34: 0x18,
    35: 0x19,
    36: 0x1a,
    37: 0x1b,
    38: 0x1c,
    39: 0x1d,
    40: 0x1e,
    41: 0x1f,
})

MODE = LookupDict({
    'HEAT': 0x01,
    'DRY': 0x02,
    'COOL': 0x03,
    'FAN': 0x07,
    'AUTO': 0x08,
})

VANE = LookupDict({
    'AUTO': 0x00,
    '1': 0x01,
    '2': 0x02,
    '3': 0x03,
    '4': 0x04,
    '5': 0x05,
    'SWING': 0x07,
})

DIR = LookupDict({
    '<<': 0x01,
    '<': 0x02,
    '|': 0x03,
    '>': 0x04,
    '>>': 0x05,
    '<>': 0x08,
    'SWING': 0x0c,
})

FAN = LookupDict({
    'AUTO': 0x00,
    'QUIET': 0x01,
    '1': 0x02,
    '2': 0x03,
    '3': 0x05,
    '4': 0x06,
})

CONTROL_PACKET_VALUES = LookupDict({
    'POWER': 0x01,
    'MODE': 0x02,
    'TEMP': 0x04,
    'FAN': 0x08,
    'VANE': 0x10,
    'DIR': 0x80,
})

CONTROL_PACKET_POSITIONS = LookupDict({
    'POWER': 3,
    'MODE': 4,
    'TEMP': 5,
    'FAN': 6,
    'VANE': 7,
    'DIR': 10,
})


class HeatPump(object):
    attributes = ('power', 'mode', 'temp', 'fan', 'vane', 'dir', 'room_temp')

    def __init__(self, port=None, **kwargs):
        self.port = port
        for item in self.attributes:
            setattr(self, item, kwargs.get(item, None))
        self.dirty = True
        self.room_temp = None
        self.info_packet_index = 0
        self.last_send = 0
        self.current_packet = None
        self.packet_history = {}
        self.wanted_state = {}
        self.start_packet = Packet.build(0x5a, [0xca, 0x01])
        self.info_packets = [
            Packet.build(0x42, [0x02] + [0x00] * 0x0f),
            Packet.build(0x42, [0x03] + [0x00] * 0x0f),
        ]

    def __setattr__(self, item, value):
        if item in self.attributes:
            if getattr(self, item, None) != value:
                self.dirty = True
        super(HeatPump, self).__setattr__(item, value)

    def to_dict(self):
        d = {}
        for item in self.attributes:
            d[item] = getattr(self, item)
        return d

    def from_dict(self, d):
        for item in self.attributes:
            if d.get(item, None):
                setattr(self, item, d.get(item))

    @property
    def valid(self):
        for item in self.attributes:
            if getattr(self, item, None) is None:
                return False
        return True

    def connect(self):
        if self.port:
            self.ser = serial.Serial(
                self.port, 2400, parity=serial.PARITY_EVEN, timeout=0)
            self.ser.write(bytearray(self.start_packet.bytes))

    def loop(self):
        res = self.ser.read(22)
        for c in res:
            val = ord(c)
            if val == 0xFC:
                self.current_packet = Packet()
            if not self.current_packet:
                log.debug('No packet!')
                return
            self.current_packet.bytes.append(val)
            if len(self.current_packet.bytes) == HEADER_LEN:
                self.current_packet.data_len = val
            if self.current_packet.complete:
                if self.current_packet.valid:
                    if self.current_packet.data[0] == 0x02:  # Set Packet
                        self.power = POWER.lookup(self.current_packet.data[3])
                        self.mode = MODE.lookup(self.current_packet.data[4])
                        self.temp = TEMP.lookup(self.current_packet.data[5])
                        self.fan = FAN.lookup(self.current_packet.data[6])
                        self.vane = VANE.lookup(self.current_packet.data[7])
                        self.dir = DIR.lookup(self.current_packet.data[10])
                    if self.current_packet.data[0] == 0x03:  # Temp Packet
                        self.room_temp = ROOM_TEMP.lookup(
                            self.current_packet.data[3])

                    if self.current_packet.data[0] in self.packet_history and \
                       self.current_packet == self.packet_history[
                       self.current_packet.data[0]]:
                        pass
                    else:
                        log.debug('HP Packet: 0x%x : %s : 0x%x' % (
                            self.current_packet.type, ','.join(
                                ['%02x' % x for x in self.current_packet.data]),
                            self.current_packet.checksum))
                    self.packet_history[
                        self.current_packet.data[0]] = self.current_packet
                    self.current_packet = None
                else:
                    log.info('HP Packet Invalid')
                    self.current_packet = None

        if time.time() - self.last_send > 1:
            # Check if our current state matches the wanted state
            if self.wanted_state:
                wanted = copy(self)
                wanted.from_dict(self.wanted_state)
                packet = self.diff(wanted)
                if packet:
                    log.debug('Sending packet: 0x%x : %s : 0x%x' % (
                              packet.type,
                              ','.join(['%02x' % x for x in packet.data]),
                              packet.checksum))
                    self.ser.write(bytearray(packet.bytes))
                    self.last_send = time.time()
                    self.info_packet_index = 0
                    time.sleep(1)
                else:
                    self.wanted_state = {}

            self.ser.write(bytearray(
                self.info_packets[self.info_packet_index].bytes))
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
            data[1] += CONTROL_PACKET_VALUES['POWER']
            data[CONTROL_PACKET_POSITIONS['POWER']] = POWER[other.power]
        if self.mode != other.mode:
            data[1] += CONTROL_PACKET_VALUES['MODE']
            data[CONTROL_PACKET_POSITIONS['MODE']] = MODE[other.mode]
        if other.temp and self.temp != int(other.temp):
            data[1] += CONTROL_PACKET_VALUES['TEMP']
            data[CONTROL_PACKET_POSITIONS['TEMP']] = TEMP[int(other.temp)]
        if self.fan != other.fan:
            data[1] += CONTROL_PACKET_VALUES['FAN']
            data[CONTROL_PACKET_POSITIONS['FAN']] = FAN[other.fan]
        if self.vane != other.vane:
            data[1] += CONTROL_PACKET_VALUES['VANE']
            data[CONTROL_PACKET_POSITIONS['VANE']] = VANE[other.vane]
        if self.dir != other.dir:
            data[1] += CONTROL_PACKET_VALUES['DIR']
            data[CONTROL_PACKET_POSITIONS['DIR']] = DIR[other.dir]
        if data[1] > 0x00:
            return Packet.build(0x41, data)
        return None


class Packet(object):
    START_BYTE = 0xfc
    EXTRA_HEADER = [0x01, 0x30]

    def __init__(self):
        self.bytes = []
        self.data_len = None

    def __eq__(self, other):
        return self.bytes == other.bytes

    def __str__(self):
        return ','.join(['0x%02x' % x for x in self.bytes])

    @classmethod
    def build(cls, type, data):
        c = cls()
        c.bytes = [c.START_BYTE, type] + c.EXTRA_HEADER
        c.bytes.append(len(data))
        c.bytes += data
        c.bytes.append(0xfc - (sum(c.bytes) & 0xff))
        return c

    @property
    def checksum(self):
        return 0xfc - (sum(self.bytes[0:-1]) & 0xff)

    @property
    def type(self):
        return self.bytes[1]

    @property
    def complete(self):
        if self.data_len is not None and \
           len(self.bytes) == HEADER_LEN + self.data_len + 1:
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

if __name__ == '__main__':
    hp = HeatPump(sys.argv[1])
    hp.connect()

    while True:
        try:
            hp.loop()
            time.sleep(1)
        except KeyboardInterrupt:
            break
