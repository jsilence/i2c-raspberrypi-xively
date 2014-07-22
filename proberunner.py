#!/usr/bin/env python

import os
from sys import exit
import time
import datetime
import json

import paho.mqtt.client as mqtt
import smbus
import psutil

import sht21
import mpl115a2

# sensors and probes
bus = smbus.SMBus(1)
sht21 = sht21.SHT21(1)
mpl115a2 = mpl115a2.MPL115A2(bus)

# persistent queue with MQTT
# @todo wrap in try/catch. https://github.com/jsilence/i2c-raspberrypi-xively/issues/1
mqttc = mqtt.Client()
mqttc.will_set("jspilence/status/prober", "jspilence prober disconnected unexpectedly", 2, True )
mqttc.connect("localhost", 1883, 60)
mqttc.loop_start()

# extract debug status from environment
DEBUG = os.environ["DEBUG"] or false

# function to read load average from psutil
def read_loadavg():
  if DEBUG:
    print "Reading load average"
  return psutil.cpu_percent()

# functions to read sensors
def read_pressure():
  if DEBUG:
    print "reading barometric pressure"
  return mpl115a2.pressure(20)

def read_humidity():
  if DEBUG:
    print "reading humidity"
  return sht21.read_humidity()

def read_temperature():
  if DEBUG:
    print "reading temperature"
  return round(sht21.read_temperature(),2)

probes = {'humidity':read_humidity,
          'temperature':read_temperature, 
          'load_avg':read_loadavg, 
          'pressure':read_pressure }

# main program entry point - runs continuously updating our datastream with the
# current 1 minute load average
def main():
  print "Starting proberunner script"

  while True:
    # json encoder cant encode datetime objects. Thus converting to unix timestamp.
    now = time.mktime(datetime.datetime.utcnow().timetuple())
    if DEBUG:
      print "UNIX timestamp: %s"  % now

    try:
      # read data from probes and pipe into MQTT broker
      for probe in probes:
        datapoint = json.dumps([probe, now, probes[probe]()])
        mqttc.publish("jspilence/probedata/%s" % probe, datapoint, 0, True)
      time.sleep(36)
    except KeyboardInterrupt:
      print "exiting..."
      mqttc.disconnect()
      exit(0)

if __name__ == "__main__":
    main()

