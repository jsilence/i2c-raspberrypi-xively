#!/usr/bin/env python

import os
import xively
import time
import datetime
import requests
import json

import pika

# persistent queue with rabbitMQ
# @todo: wrap in try/except
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
mqchannel = connection.channel()
# @todo: split into different MQ channels for each probe
mqchannel.queue_declare(queue='probedata')

# extract feed_id and api_key from environment variables
FEED_ID = os.environ["FEED_ID"]
API_KEY = os.environ["API_KEY"]
DEBUG = os.environ["DEBUG"] or false

# initialize api client
api = xively.XivelyAPIClient(API_KEY)
datastreams = {}

# function to return a datastream object. This either creates a new datastream,
# or returns an existing one
def get_datastream(feed, channel):
  try:
    datastream = feed.datastreams.get(channel)
    if DEBUG:
      print "Found existing datastream %s" % channel
    return datastream
  except:
    if DEBUG:
      print "Creating new datastream %s" % channel
    datastream = feed.datastreams.create(channel, tags="autogenerated")
    return datastream

def mqcallback(ch, method, properties, body):
    """Callback function reads json encoded datapoints from RabbitMQ queue.
    Documentation: http://www.rabbitmq.com/tutorials/tutorial-one-python.html
    The default json encoder can not encode datetime.datetime objects, thus the date
    is converted to UNIX timestamps."""

    # data comes in order: channel, timestamp, value
    datapoint = json.loads(body)
    if DEBUG:
        print "received %s %s %s " % (datapoint[0], datapoint[1], datapoint[2])
    datastreams[datapoint[0]].current_value = datapoint[2]
    datastreams[datapoint[0]].at = datetime.datetime.fromtimestamp(datapoint[1])
    try:
        datastreams[datapoint[0]].update()
    except requests.HTTPError as e:
        print "HTTPError({0}): {1}".format(e.errno, e.strerror)

# main program entry point - runs continuously 
def main():
  print "Starting Xively upload script"
	
  feed = api.feeds.get(FEED_ID)

  # setting up datastreams
  channels = ['load_avg', 'pressure', 'temperature']
  for channel in channels:
    datastreams[channel] = get_datastream(feed, channel)
    datastreams[channel].max_value = None
    datastreams[channel].min_value = None

  # @todo: use delivery confirmations: 
  # http://pika.readthedocs.org/en/latest/examples/blocking_delivery_confirmations.html
  mqchannel.basic_consume(mqcallback, queue='probedata', no_ack=True)

  try:
    mqchannel.start_consuming()
  except KeyboardInterrupt:
    mqchannel.stop_consuming()
  connection.close()

if __name__ == "__main__":
    main()
