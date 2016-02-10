#---------------------------------------------------------------------------------------
# wifidtu_bridge
# -- a python service to accept wifi-cam connection and capture image from wifi-cam
# Physical connection
# [serial interface camera] <---> [WiFi DTU] <-----> [TCP Server] <------> [MQTT broker]
#
# BSD 3-clause license is applied to this code
# Copyright(c) 2015 by Aixi Wang <aixi.wang@hotmail.com>
#----------------------------------------------------------------------------------------
#!/usr/bin/python

import socket
import threading               # Import socket module
import time
import os,sys
from mqtt_cam import *

import mqtt.publish as publish
import mqtt.client as mqtt

#-------------------
# global variable
#-------------------
jpg_bin = ''
status = 0
ALL_CLIENT = []
TCP_ID_PAIR = {}

#-------------------
# global setting
#-------------------
GRANT_MAC_LIST = ['accf2352bb94']
CAPTURE_INTERVAL = 3600
BASE_FOLDER = '/usr/share/nginx/www/img/'
#BASE_FOLDER = ''
#HEADER_ID_TYPE = 'macaddr'
HEADER_ID_TYPE = 'id'

MQTT_SERVER = 'test.mosquitto.org'
MQTT_PORT = 1883
MQTT_TOPIC_BASE = 'WTwSD234Sdf/'

MQTT_TOPIC_BROADCAST = MQTT_TOPIC_BASE + 'INFO/'

MQTT_TOPIC_A = MQTT_TOPIC_BASE + 'A/'
MQTT_TOPIC_B = MQTT_TOPIC_BASE + 'B/'
MQTT_TOPIC_B_BROADCAST = MQTT_TOPIC_B + 'ALL/'
#MQTT_SECURITY_KEY = '23afsdr23'

#-------------------
# writefile2
#-------------------
def writefile2(filename,content):
    f = file(filename,'ab')
    fs = f.write(content)
    f.close()
    return

#-------------------
# add_id_tcp_pair
#-------------------    
def add_id_tcp_pair(id,client):
    global TCP_ID_PAIR
    print 'add_id_tcp_pair:',id
    
    TCP_ID_PAIR[id] = client
    return

#-------------------
# get_id_tcp_pair
#-------------------    
def get_id_tcp_pair(id):
    global TCP_ID_PAIR
    if TCP_ID_PAIR.has_key(id):
        return TCP_ID_PAIR[id]
    else:
        None

#-------------------
# remove_id_tcp_pair
#-------------------
def remove_id_tcp_pair(id):
    global TCP_ID_PAIR
    del TCP_ID_PAIR[id]
    return

#----------------------
# mqtt my_mqtt_mainloop
#----------------------
def my_mqtt_mainloop(mqttc):
    mqttc.loop_forever()

#----------------------
# mqtt on_message
#----------------------
def on_message(mosq, obj, msg):
    print("MESSAGE: "+msg.topic+" "+str(msg.qos)+" "+str(msg.payload))
    
    id = msg.topic[len(MQTT_TOPIC_B):].rstrip('/')
    print 'id:',id
    
    f = id + '#' + filename_from_time()
    writefile2(f,msg.payload.decode('hex'))
    print 'write file :',f
    
    
    
#----------------------
# myTask
#----------------------
def myTask(mqttc):
    while True:

        time.sleep(30)
            
        #except:
        #    time.sleep(5)
        #    print 'myTask exception'
#----------------------
# main
#----------------------
if __name__ == "__main__":
    print 'step 1. create mqtt'
    mqttc = mqtt.Client()

    # Add message callbacks that will only trigger on a specific subscription match.
    mqttc.on_message = on_message
    mqttc.connect(MQTT_SERVER, MQTT_PORT, 60)
    mqttc.subscribe(MQTT_TOPIC_A + '#', 0)
    
    module_reset(MQTT_TOPIC_B_BROADCAST)
    print 'step 2. create mqtt mainloop'
    threading.Thread(target=my_mqtt_mainloop, args=(mqttc,)).start()
    
    print 'step 3. create myTask thread'

    threading.Thread(target=myTask, args=(mqttc,)).start()
    time.sleep(3)

