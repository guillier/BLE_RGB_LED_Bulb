#!/usr/bin/env python3
"""

Driver for LEDE RGB LED Bulb

Copyright © 2015 François GUILLIER
"""

from btle import UUID, Peripheral, DefaultDelegate, AssignedNumbers, helperExe
import binascii
import random
import struct
import sys
import time

class LEDE:

    def __init__(self, addr):
        self.conn = Peripheral(addr)
        self.conn.discoverServices()  # To avoid bug(?) in getServiceByUUID
        self.info = None
        self.writeHnd = None

    def _read_info(self, service, characteristics_uuid):
        ch = service.getCharacteristics(characteristics_uuid)
        name = AssignedNumbers.getCommonName(ch[0].uuid)
        self.info[name] = ch[0].read().decode()

    def get_info(self):
        if self.info:
            return self.info

        self.info = {}
        svc = self.conn.getServiceByUUID('180A')  # Device Information
        self._read_info(svc, '2a24')
        self._read_info(svc, '2a26')
        self._read_info(svc, '2a27')
        self._read_info(svc, '2a29')
        return self.info

    def _random(self):
        return random.randrange(256)

    def _checksum(self, cmd):
        s = 28
        for i in cmd:
            s += i
        return s&255

    def _pack_data(self, cmd, rdcs):
        cmd = list(cmd)
        if rdcs:
            cmd.append(self._random())
            cmd.append(self._checksum(cmd))
        cmd.append(0xd)
        return binascii.a2b_hex('aa0afc3a8601' + ''.join('%02X'%x for x in cmd))

    def write(self, cmd, rdcs = True):
        if self.writeHnd is None:
            svc = self.conn.getServiceByUUID('fff0')  # Control
            self.writeHnd = svc.getCharacteristics('fff1')[0]  # Aka Handle 0x21
        self.writeHnd.write(self._pack_data(cmd, rdcs))
        time.sleep(.2)

    def disconnect(self):
        self.conn.disconnect()

    def command_on(self):
        """Switch the light on"""
        self.write((0x0a, 0x01, 0x01, 0x00, 0x28), False)
        
    def command_off(self):
        """Switch the light off"""
        self.write((0x0a, 0x01, 0x00, 0x01, 0x28), False)
        
    def command_white_reset(self):
        """Switch to White Mode"""
        self.write((0x0d, 0x06, 0x02, 0x80, 0x80, 0x80, 0x80, 0x80))

    def command_set_brightness(self, value):
        """Set Brightness (value between 0 and 9)"""
        if value >= 0 and value <= 9:
            self.write((0x0c, 0x01, value + 2))

    def command_set_cct(self, value):
        """Set Colour Temperature (value between 0 and 9)"""
        if value >= 0 and value <= 9:
            self.write((0x0e, 0x01, value + 2))

    def command_rgb(self, red, green, blue):
        """Set RGB Colour"""
        self.write((0x0d, 0x06, 0x01, red&255, green&255, blue&255, 0x80, 0x80))

    def command_preset(self, value):
        """Use Preset (value between 1 and 10)"""
        if value >= 0 and value <= 10:
            self.write((0x0b, 0x01, value))

    def command_night_mode(self):
        """Start Night Mode (20 minutes)"""
        self.write((0x10, 0x02, 0x03, 0x01))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit("Usage:\n  %s <mac-address>" % sys.argv[0])

    import os
    if not os.path.isfile(helperExe):
        raise ImportError("Cannot find required executable '%s'" % helperExe)

    lede = LEDE(sys.argv[1])
    for val in lede.get_info().items():
        print("%s = %s" % val)
    print('------------')
    print('On')
    lede.command_on()
    time.sleep(3)
    print('White mode, minimum brightness, Cold')
    lede.command_white_reset()
    lede.command_set_brightness(0)
    lede.command_set_cct(0)
    time.sleep(3)
    print('Maximum brightness')
    lede.command_set_brightness(9)
    time.sleep(3)
    print('Warm')
    lede.command_set_cct(9)
    time.sleep(3)
    for i in range(1, 11):
        print('Preset %u' % i)
        lede.command_preset(i)
        time.sleep(5)
    for i in range(1, 20):
        r = lede._random()
        g = lede._random()
        b = lede._random()
        print('Random colour : (%u, %u, %u)' % (r, g, b))
        lede.command_rgb(r, g, b)
    print('Off')
    lede.command_off()
