#!/usr/bin/env python

import os
import xively
import subprocess
from time import sleep
import datetime
import requests

# i2c sensors
import smbus

bus = smbus.SMBus(1)


# extract feed_id and api_key from environment variables
FEED_ID = os.environ["FEED_ID"]
API_KEY = os.environ["API_KEY"]
DEBUG = os.environ["DEBUG"] or false

# initialize api client
api = xively.XivelyAPIClient(API_KEY)

# function to read 1 minute load average from system uptime command
def read_loadavg():
  if DEBUG:
    print "Reading load average"
  return subprocess.check_output(["awk '{print $1}' /proc/loadavg"], shell=True)

# function to read sensor
def read_sensor():
    bus.write_i2c_block_data(0x60, 0x12, [0x01])
    sleep(2)
    bus.write_byte(0x60, 0x00)
    reading1 = bus.read_i2c_block_data(0x60, 0x00)
    pressure = ((reading1[0]<<2)+((reading1[1] & 0xc0) >> 6))
    pressure = ((65.0/1023.0)*pressure)+50
    tempC = (((reading1[2]<<2) + ((reading1[3] & 0xc0)>>6)) -510.0) / -5.35 + 25.0
    return (tempC, pressure)

# function to return a datastream object. This either creates a new datastream,
# or returns an existing one
def get_datastream(feed):
  try:
    datastream = feed.datastreams.get("load_avg")
    if DEBUG:
      print "Found existing datastream"
    return datastream
  except:
    if DEBUG:
      print "Creating new datastream"
    datastream = feed.datastreams.create("load_avg", tags="load_01")
    return datastream


# main program entry point - runs continuously updating our datastream with the
# current 1 minute load average
def run():
  print "Starting Xively tutorial script"

  feed = api.feeds.get(FEED_ID)

  datastream = get_datastream(feed)
  datastream.max_value = None
  datastream.min_value = None

  while True:
    load_avg = read_loadavg()

    if DEBUG:
      print "Updating Xively feed with value: %s" % load_avg

    datastream.current_value = load_avg
    datastream.at = datetime.datetime.utcnow()
    try:
      datastream.update()
    except requests.HTTPError as e:
      print "HTTPError({0}): {1}".format(e.errno, e.strerror)

    time.sleep(10)

run()
