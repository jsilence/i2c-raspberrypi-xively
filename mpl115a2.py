#!/usr/bin/python

# from: http://raspberrypi.hatenablog.com/entry/2014/07/04/225802

import smbus
import time

class MPL115A2:
    """Class to read pressure from MPL115A2.
       Datasheet: http://cache.freescale.com/files/sensors/doc/data_sheet/MPL115A2.pdf
       and Martin Steppuhn's code from http://www.emsystech.de/raspi-sht21"""

    #control constants
    _I2C_ADDRESS = 0x60
    _COMMAND_START_CONVERSION = 0x12
    _COEFFICIENT_START_ADDRESS = 0x04
    _COEFFICIENT_BLOCK_LENGTH = 8
    _SENSOR_DATA_BLOCK_LENGTH = 4

    def __init__(self, bus):
        self.bus = bus

        # Coefficients for compensation calculations - will be set on first
        # attempt to read pressure or temperature
        self.a0 = None
        self.b1 = None
        self.b2 = None
        self.c12 = None

    def parse_signed(self, msb, lsb):
        combined = msb << 8 | lsb
        negative = combined & 0x8000
        if negative:
            combined ^= 0xffff
            combined *= -1
        return combined


    def read_coefficients(self):
        block = self.bus.read_i2c_block_data(self._I2C_ADDRESS, 
                                             self._COEFFICIENT_START_ADDRESS, 
                                             self._COEFFICIENT_BLOCK_LENGTH)
        
        self.a0 = float(self.parse_signed(block[0], block[1])) / 8.0
        self.b1 = float(self.parse_signed(block[2], block[3])) / 8192.0
        self.b2 = float(self.parse_signed(block[4], block[5])) / 16384.0
        self.c12 = float(self.parse_signed(block[6], block[7]) >> 2) / 4194304.0

    def read_raw_pressure(self):
        self.bus.write_byte_data(self._I2C_ADDRESS, 
                                 self._COMMAND_START_CONVERSION, 
                                 0x00)
        time.sleep(0.005) 
        rp = self.bus.read_i2c_block_data(self._I2C_ADDRESS, 
                                          0x00, 
                                          2)
        return int((rp[0] << 8 | rp[1]) >> 6)

    def read_raw_temperature(self):
        self.bus.write_byte_data(self._I2C_ADDRESS, 
                                 self._COMMAND_START_CONVERSION, 
                                 0x02) 
        time.sleep(0.005) 
        rt = self.bus.read_i2c_block_data(self._I2C_ADDRESS, 
                                          0x02, 
                                          2)
        return int((rt[0] << 8 | rt[1]) >> 6)


    @property
    def pressure(self):
        if self.a0 is None:
            self.read_coefficients()
        raw_pressure = self.read_raw_pressure()
        raw_temp = self.read_raw_temperature()
        compensated = (((self._b1 + (self._c12 * raw_temp)) * raw_pressure) + self._a0) + (self._b2 * raw_temp)
        kpa = (compensated * (65.0 / 1023.0)) + 50.0
        if self.pressure_convertor is None:
            return kpa
        return self.pressure_convertor.convert_to(kpa)

    def read_pressure(self):
        """Reads the pressure from the sensor.  Not that this call blocks
	for 5 ms to allow the sensor to return the data"""

        # make sure coefficients have been read
        if self.a0 == None:
            self.read_coefficients()

        self.bus.write_byte_data(self._I2C_ADDRESS, 
                                 self._COMMAND_START_CONVERSION, 
                                 0x01) # why 0x01?
        time.sleep(0.005) # 3ms should be sufficient, but hey...
        block = self.bus.read_i2c_block_data(self._I2C_ADDRESS, 
                                             0x00, 
                                             self._SENSOR_DATA_BLOCK_LENGTH)
        padc = (block[0] << 8 | block[1]) >> 6
        tadc = (block[2] << 8 | block[3]) >> 6

        c12x2 = self.c12 * tadc
        a1 = self.b1 + c12x2
        a1x1 = a1 * padc
        y1 = self.a0 + a1x1
        a2x2 = self.b2 * tadc
        pcomp = y1 + a2x2

        return (pcomp * 65 / 1023) + 50 # in kilopascal



    def close(self):
        """Closes the i2c connection"""
        self.i2c.close()


    def __enter__(self):
        """used to enable python's with statement support"""
        return self
        

    def __exit__(self, type, value, traceback):
        """with support"""
        self.close()


if __name__ == "__main__":
    try:
        with MPL115A2(0) as mpl115a2:
            print "Temperature: %s"%mpl115a2.read_pressure()
    except IOError, e:
        print e
        print 'Error creating connection to i2c.  This must be run as root'
