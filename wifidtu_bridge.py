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
from tcpcam2cloud import *

import mqtt.publish as publish
import mqtt.client as mqtt

#-------------------
# global variable
#-------------------
jpg_bin = ''
status = 0
ALL_CLIENT = []


#-------------------
# global setting
#-------------------
GRANT_MAC_LIST = ['\xac\xcf\x23\x52\xbb\x94','\xff\xff\xff\xff\xff\xff']
CAPTURE_INTERVAL = 60
BASE_FOLDER = '/usr/share/nginx/www/img/'
#BASE_FOLDER = ''
#HEADER_ID_TYPE = 'macaddr'
HEADER_ID_TYPE = 'id'

MQTT_SERVER = 'test.mosquitto.org'
MQTT_PORT = 1883
MQTT_TOPIC_BASE = 'WTwSD234Sdf/'
MQTT_TOPIC_BROADCAST = MQTT_TOPIC_BASE + 'INFO'
MQTT_TOPIC_A = MQTT_TOPIC_BASE + 'A/'
MQTT_TOPIC_B = MQTT_TOPIC_BASE + 'B/'
#MQTT_SECURITY_KEY = '23afsdr23'

#-------------------
# writefile2
#-------------------
def writefile2(filename,content):
    f = file(filename,'ab')
    fs = f.write(content)
    f.close()
    return
  
    
# Define tcp handler for a thread...
def myTcpHandler(client, addr, mqttc):
    global ALL_CLIENT
    global jpg_bin
    global BASE_FOLDER
    global status
    
    mac_addr = ''
    client.setblocking(0)

    ALL_CLIENT.append({
        'fd': client,
        'addr': addr,
        'closed': False
    });

    print 'thread started for ', addr
    data=''
    jpg_bin = ''
    c1 = ''
    while True:
        # avoid cpu loading too hight
        time.sleep(1)
        try:
            msg = client.recv(1024*64)
            if HEADER_ID_TYPE == 'id':
                mac_addr = msg[0:4].encode('hex')
                print 'id:',mac_addr
                c1 += msg[4:]

            elif HEADER_ID_TYPE == 'macaddr':
                mac_addr = msg[0:6].encode('hex')
                print 'id:',mac_addr
                c1 += msg[6:]

        except socket.error as e:
            if c1 != '':
                #print 'recv %d bytes' % (len(c1
                # recognize jpg header & tail            === start
                i = c1.find('\xff\xd8')
                if  i>= 0:
                    jpg_bin = c1[i:]
                    status = 1
                    print '[JPG'
                    #continue

                    j = jpg_bin.find('\xff\xd9')                        
                    if j > 0:
                        print '--JPG]'                        
                        jpg_bin = jpg_bin[:j+2]
                        #s = BASE_FOLDER + mac_addr + '#' + filename_from_time()
                        #print s
                        #writefile(s,jpg_bin)
                        
                        # prepare mqtt publish
                        s = jpg_bin.encode('hex')
                        print 'MQTT DTA:' + s
                        publish.single(MQTT_TOPIC_BASE + 'A/' + str(mac_addr), s, hostname=MQTT_SERVER) 
                        
                        jpg_bin = ''
                        c1 = ''

                        time.sleep(CAPTURE_INTERVAL)                        
                        client.close()
                        break
                        
                    
                j = c1.find('\xff\xd9')                        
                if j >= 0:
                    if status == 1:
                        print 'JPG]'                        
                        jpg_bin += c1[:j+2]
                        
                        #s = BASE_FOLDER + mac_addr + '#' + filename_from_time()
                        #print s
                        #writefile(s,jpg_bin)
                        
                        # prepare mqtt publish                      
                        s = jpg_bin.encode('hex')
                        print 'MQTT DTA:' + s
                        publish.single(MQTT_TOPIC_B + str(mac_addr), s, hostname=MQTT_SERVER)                        
                        
                        jpg_bin = ''
                        c1 = ''
                        
                        time.sleep(CAPTURE_INTERVAL)
                        client.close()
                        break
                        
                else:
                    if status == 1:
                        jpg_bin += c1

                # recognize jpg header & tail            === end
                
            continue
        except Exception as e:
            print 'Server get a error fd: ', e
            client.close()            
            break


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

    print 'step 2. create mqtt mainloop'
    threading.Thread(target=my_mqtt_mainloop, args=(mqttc,)).start()
    
    print 'step 3. create tcp server socket'
    
    while True:
        try:
            server = socket.socket()
            host = socket.gethostname()
            port = 8899
            server.bind(('', port))
            server.listen(5)
            print 'Server FD No: ', server.fileno()
            break
            
        except:
            time.sleep(3)

    print 'step 4. create loop'
    
    while True:
        try:
            client, addr = server.accept()
            print 'Got connection from', addr, ' time:', format_time_from_linuxtime(time.time())
            #header = client.recv(32)
            #h_s = header.encode('hex')
            #print 'header:', h_s
            s = 'new connection from %s, time: %s\r\n' % (str(addr),str(format_time_from_linuxtime(time.time())))
            writefile2('log.txt',s)
            
            #if (header in GRANT_MAC_LIST):
            #    print 'new thread created! for addr:',addr
            module_reset(client)
            time.sleep(1)
            module_snapshot(client)
            time.sleep(0.5)
            jpg_size = get_jpg_size(client)
            print 'jpg size:',jpg_size
            if (jpg_size == 0):
                module_read_pic_data2(client,32000)
            else:
                module_read_pic_data2(client,jpg_size)
            
            s = 'connected ' + str(addr)
            publish.single(MQTT_TOPIC_BROADCAST, s, hostname=MQTT_SERVER)
            
            threading.Thread(target=myTcpHandler, args=(client, addr, mqttc)).start()
            
        except:
            print 'except, try again.'
            s = 'disconnected ' + str(addr)
            publish.single(MQTT_TOPIC_BROADCAST, s, hostname=MQTT_SERVER)
            
            time.sleep(3)

