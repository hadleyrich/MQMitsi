
class LookupDict(dict):
    def __init__(self, d, name='unknown'):
        super(self.__class__, self).__init__(d)
        self.name = name

    def lookup(self, value):
        try:
            ret = [k for k, v in self.items() if v == value][0]
        except:
            ret = None
            log.error('Failed to lookup %s from %s' % (value, self.name))
        return ret

POWER = LookupDict({
    'OFF': 0x00,
    'ON': 0x01,
}, 'POWER')

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
    16.5: 0x1f,
    17.5: 0x1e,
    18.5: 0x1d,
    19.5: 0x1c,
    20.5: 0x1b,
    21.5: 0x1a,
    22.5: 0x19,
    23.5: 0x18,
    24.5: 0x17,
    25.5: 0x16,
    26.5: 0x15,
    27.5: 0x14,
    28.5: 0x13,
    29.5: 0x12,
    30.5: 0x11,
    31.5: 0x10,
}, 'TEMP')

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
}, 'ROOM_TEMP')

MODE = LookupDict({
    'HEAT': 0x01,
    'DRY': 0x02,
    'COOL': 0x03,
    'FAN': 0x07,
    'AUTO': 0x08,
}, 'MODE')

VANE = LookupDict({
    'AUTO': 0x00,
    '1': 0x01,
    '2': 0x02,
    '3': 0x03,
    '4': 0x04,
    '5': 0x05,
    'SWING': 0x07,
}, 'VANE')

DIR = LookupDict({
    '<<': 0x01,
    '<': 0x02,
    '|': 0x03,
    '>': 0x04,
    '>>': 0x05,
    '<>': 0x08,
    'SWING': 0x0c,
}, 'DIR')

FAN = LookupDict({
    'AUTO': 0x00,
    'QUIET': 0x01,
    '1': 0x02,
    '2': 0x03,
    '3': 0x05,
    '4': 0x06,
}, 'FAN')

CONTROL_PACKET_VALUES = LookupDict({
    'POWER': 0x01,
    'MODE': 0x02,
    'TEMP': 0x04,
    'FAN': 0x08,
    'VANE': 0x10,
    'DIR': 0x80,
}, 'CONTROL_PACKET_VALUES')

CONTROL_PACKET_POSITIONS = LookupDict({
    'POWER': 3,
    'MODE': 4,
    'TEMP': 5,
    'FAN': 6,
    'VANE': 7,
    'DIR': 10,
}, 'CONTROL_PACKET_POSITIONS')
