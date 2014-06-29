#!/usr/bin/env python

import os
import time
import datetime
import json

import smbus
import psutil

import pika

# sensors and probes
bus = smbus.SMBus(1)

# persistent queue with rabbitMQ
# @todo wrap in try/catch
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
mqchannel = connection.channel()
mqchannel.queue_declare(queue='probedata')

# extract feed_id and api_key from environment variables
DEBUG = os.environ["DEBUG"] or false


# function to read load average from psutil
def read_loadavg():
  if DEBUG:
    print "Reading load average"
  return psutil.cpu_percent()

# function to read sensor
def read_barometric_sensor():
  if DEBUG:
    print "Waking pressure sensor"
  bus.write_i2c_block_data(0x60, 0x12, [0x01])
  time.sleep(2)
  if DEBUG:
    print "Reading temperature and pressure data"
  bus.write_byte(0x60, 0x00)
  reading1 = bus.read_i2c_block_data(0x60, 0x00)
  pressure = ((reading1[0]<<2)+((reading1[1] & 0xc0) >> 6))
  pressure = ((65.0/1023.0)*pressure)+50
  tempC = (((reading1[2]<<2) + ((reading1[3] & 0xc0)>>6)) -510.0) / -5.35 + 25.0
  return (tempC, pressure)

def read_pressure():
  (temp, press) = read_barometric_sensor()
  return round(press, 2)

def read_temperature():
  (temp, press) = read_barometric_sensor()
  return round(temp, 2)

probes = {'load_avg':read_loadavg, 'pressure':read_pressure, 'temperature':read_temperature }

# main program entry point - runs continuously updating our datastream with the
# current 1 minute load average
def main():
  print "Starting proberunner script"

  while True:
    # json encoder cant encode datetime objects. Thus converting to unix timestamp.
    now = time.mktime(datetime.datetime.utcnow().timetuple())
    if DEBUG:
      print "UNIX timestamp: %s"  % now

    # read data from probes and pipe into RabbitMQ
    for probe in probes:
      datapoint = json.dumps([probe, now, probes[probe]()])
      mqchannel.basic_publish(exchange='', routing_key='probedata', body=datapoint)

    time.sleep(6)

if __name__ == "__main__":
    main()

