# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-pico-web-server-micropython/

# Import necessary modules
import network
import socket
import time
import random
from machine import Pin
import json # communication with esp32-cam
from mcomms2 import Qcomms
from webpage import update_from_serial, getWebCMD
# Create an LED object on pin 'LED'
led = Pin('LED', Pin.OUT)
led.value(1)
# Wi-Fi credentials


last_message = ""

# Connect to WLAN hotspot

ssid = 'MicroPython-AP'
password = '123456789'

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=ssid, password=password)

while ap.active() == False:
  pass

print('Connection successful')
print(ap.ifconfig())


#comms
comms= Qcomms(0, 19200, txPin=16, rxPin=17)
cmode= "a"
mode = 0
# data sent by motor2040
cmdSTR = {
    "command" : "stop",
    "args" : 0
    }
def sendCMD(data4TX):
    jsonmode=json.dumps(data4TX)
    comms.write(jsonmode)
    
print("starting")
# Main loop to listen for connections
while True:
        newCMD = getWebCMD() # blobking or a lrage timeout?
        
        if newCMD != "":
            led.toggle()
            cmdSTR["command"] = newCMD
            sendCMD(cmdSTR)
        
        ''' read serial comms
        '''
        cmd = comms.read()
        
        if cmd is not None and cmd.strip():
            
            update_from_serial(cmd)
