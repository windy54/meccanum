import time

from pimoroni import Analog, AnalogMux, Button
from motor import motor2040 # for access tosensors on motor2040 board
from plasma import WS2812 # for on board led control
from hcsro4 import HCSR04 # range finder
from machine import  Pin  # serial
from mecRobot import Meccanum  # motor control
from  json import dumps, loads # communication with esp32-cam
from mcomms2 import Qcomms

from  math import sqrt
import os

led = WS2812(motor2040.NUM_LEDS, 1, 0, motor2040.LED_DATA, rgbw=True)
led.start()
led.set_rgb(0, 255, 0, 0)



frontSonar = HCSR04(trigger_pin=21, echo_pin=20, echo_timeout_us=10000)
myRobot = Meccanum()

# file operations
debug = True
if (debug):
    try:
        os.rename("demands.csv","demandsold.csv")
    except:
        pass
    debugFile= open('demands.csv','w')
# How many of the updates should be printed (i.e. 2 would be every other update)


# monitoring
sen_adc = Analog(motor2040.SHARED_ADC)
vol_adc = Analog(motor2040.SHARED_ADC, motor2040.VOLTAGE_GAIN)
cur_adc = Analog(motor2040.SHARED_ADC, motor2040.CURRENT_GAIN,
                 motor2040.SHUNT_RESISTOR, motor2040.CURRENT_OFFSET)

mux = AnalogMux(motor2040.ADC_ADDR_0, motor2040.ADC_ADDR_1, motor2040.ADC_ADDR_2)

# control functions
mode = 0
modeCount= 0
minFrontDistance = 10.0

comms = Qcomms(0, 19200, txPin=16, rxPin=17)
# command fot automatic mode where it attempts to move forward, starfingto the right when it finds a wall
####################################################################
def mode_forwards(range):
    global modeCount
    mode =  1
    if range < minFrontDistance:
        myRobot.strafe_right(1.)
        mode = 2
        modeCount=0
        modeSTR["autostatus"]= "a2"
        sendMode(modeSTR)
    return mode

# this gets called when the robot is to close to the wall so moves to the right
# sometimes it moves forward diagonally, if this happens and the range gets less than 2 it backs
## off nd strts again.
# need to isnert a delay between getting a range > 10 and switching to forward mode
# to ensure the robot left hand side is clear of the obstruction

def mode_strafe_right(range):
    global modeCount
    mode =  2
    if range > minFrontDistance:
        modeCount+=1
        if modeCount > 60:
            myRobot.drive_forward(motorSpeed)
            mode =1
            modeSTR["autostatus"]= "a1"
            sendMode(modeSTR)
    elif range < 2:
        # reverse because too close
        myRobot.drive_forward(-motorSpeed)
        mode = 3
        modeSTR["autostatus"]= "a3"
        sendMode(modeSTR)
    return mode

def mode_back_up(range):
    mode = 3
    if range > minFrontDistance:
        myRobot.strafe_right(1.)
        mode =2
        modeSTR["autostatus"]= "a2"
        sendMode(modeSTR)
    return mode

def default_option(range):
    myRobot.stop()
    return 4
# an attempt at a case statement
switch_dict={
    1: mode_forwards,
    2: mode_strafe_right,
    3: mode_back_up
    }

def switch_mode_dict(value):
    func = switch_dict.get(value, default_option)
    return func
#end of automatic mode functions
#####################################################

# Create the user button
user_sw = Button(motor2040.USER_SW)

timeSlots = [0 for i in range(11)]
# everything based on cycle time
UPDATES = 100     # How many times to update the motor per second
UPDATE_RATE = 1 / UPDATES
UPDATE_RATE_MSECS = 1000 * UPDATE_RATE


print("go")
led.set_rgb(0, 255, 255, 255)
time.sleep(1)
myRobot.stop()
led.set_rgb(0, 255, 0, 0)
time.sleep(1)
cmode = "s"
# struccture to send data back to pico w
modeSTR = {
    "status" : cmode,
    "autostatus" : mode,
    "range" : 0,
    "volts" : 0
    }
def sendMode(mode):
    jsonmode = dumps(mode)
    comms.write(jsonmode)
    

#ledcolours to indicate mode
colours = { "s" : [255, 0, 0],
            "f" : [0, 255, 0],
            "b" : [0, 0, 255],
            "l" : [255, 0, 255],
            "r" : [255, 255, 0],
            "a" : [255, 255, 255],
            "sl" : [128, 0, 128],
            "sr" : [128, 128, 0]
            }
r, g, b = colours[cmode]
ledFlashCount = 0
ledFlashMax = 100
rangeCount = 0
myRobot.enable()


led.set_rgb(0, 0, 255, 0)
time.sleep(1)
motorSpeed = 1.0

while not user_sw.raw():
    timeStart = time.ticks_ms()
    # get new command
    cmd = comms.read()

    if cmd is not None and cmd.strip():

        try:
            command = loads(cmd)

            if command['command'] == 'forwards':
                cmode = "f"
                r, g, b = colours[cmode]
                myRobot.drive_forward(motorSpeed)
            elif command['command'] == 'left':
                cmode = "l"
                r, g, b = colours[cmode]
                myRobot.turn_left(motorSpeed)
            elif command['command'] == 'right':
                cmode = "r"
                r, g, b = colours[cmode]
                myRobot.turn_right(motorSpeed)
            elif command['command'] == 'back':
                cmode = "b"
                r, g, b = colours[cmode]
                myRobot.drive_forward(-motorSpeed)
            elif command['command'] == 'stop':
                cmode = "s"
                r, g, b = colours[cmode]
                myRobot.drive_forward(0)
            elif command['command'] == "sl":
                myRobot.strafe_left(motorSpeed)
                cmode = "sl"
            elif command['command'] == "sr":
                myRobot.strafe_right(motorSpeed)
                cmode = "sr"
            elif command['command'] == 'auto':
                cmode = "a"
                r, g, b = colours[cmode]
                mode = 1
                myRobot.drive_forward(motorSpeed)
                modeSTR["autostatus"]= "a1"
                sendMode(modeSTR)
                mode =switch_mode_dict(mode)(frontDistance)
            time.sleep(0.1)
        except Exception as e:
            print(f'error: {e} {cmd}')
            print("xx")
        cmd =None

    frontDistance = frontSonar.distance_cm()

    rangeCount+=1
    if rangeCount > 50:
        rangeCount=0

        modeSTR["range"] =round(frontDistance,1)


        a2d=[]
        mux.select(motor2040.VOLTAGE_SENSE_ADDR)
        volts = vol_adc.read_voltage()
        a2d.append(volts )

        for addr in range(motor2040.NUM_MOTORS):
            mux.select(addr + motor2040.CURRENT_SENSE_A_ADDR)

        modeSTR["volts"] = round(volts,2)
        modeSTR["status"] = cmode
        sendMode(modeSTR)


    if cmode == "a":
        mode =switch_mode_dict(mode)(frontDistance)
    elif cmode == "f":

        if frontDistance < minFrontDistance:
            cmode ="s"
            myRobot.stop()

    ledFlashCount +=1
    if ledFlashCount > 2 * ledFlashMax:
        led.set_rgb(0, r, g, b)
        ledFlashCount = 0
    elif ledFlashCount > ledFlashMax:
        led.set_rgb(0, 0, 0, 0)


    # calculate cycle delay
    iterTime = time.ticks_diff(time.ticks_ms() , timeStart )
    # determine processing time as multiples of 1 mSec from 1 to 10
    intTime = int(iterTime)
    if intTime > 10:
        intTime = 10
    timeSlots[intTime]+=1
    delayTime = int(UPDATE_RATE_MSECS - iterTime)
    if delayTime > 0 :
        time.sleep_ms(delayTime)

myRobot.disable()
comms.run = False
print(timeSlots)
debugFile.close()
led.clear()
while True:
    time.sleep(1)
    pass
