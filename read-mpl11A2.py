#!/usr/bin/python

import smbus
from time import sleep
bus = smbus.SMBus(1)

while (0==0):
    bus.write_i2c_block_data(0x60, 0x12, [0x01])
    sleep(2)
    bus.write_byte(0x60, 0x00)
    reading1 = bus.read_i2c_block_data(0x60, 0x00)
    pressure = ((reading1[0]<<2)+((reading1[1] & 0xc0) >> 6))
    pressure = ((65.0/1023.0)*pressure)+50
    tempC = (((reading1[2]<<2) + ((reading1[3] & 0xc0)>>6)) -510.0) / -5.35 + 25.0
    print 'Temp %.1f C - Luftdruck %.1f kPa' % (tempC,pressure)
