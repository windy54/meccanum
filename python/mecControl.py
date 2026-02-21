import time

from pimoroni import Analog, AnalogMux, Button
from motor import motor2040 # for access tosensors on motor2040 board
from plasma import WS2812 # for on board led control
from hcsro4 import HCSR04 # range finder
from machine import UART, Pin  # serial
from mecRobot import Meccanum  # motor control
import json # communication with esp32-cam
uart = UART(0, baudrate=9600, tx=Pin(16), rx=Pin(17))
uart.init(bits=8, parity=None, stop=2)


frontSonar = HCSR04(trigger_pin=21, echo_pin=20, echo_timeout_us=10000)
myRobot = Meccanum()


UPDATES = 100                           # How many times to update the motor per second
UPDATE_RATE = 1 / UPDATES
TIME_FOR_EACH_MOVE = 2                  # The time to travel between each value
UPDATES_PER_MOVE = TIME_FOR_EACH_MOVE * UPDATES
PRINT_DIVIDER = 4                       # How many of the updates should be printed (i.e. 2 would be every other update)


# monitoring
sen_adc = Analog(motor2040.SHARED_ADC)
vol_adc = Analog(motor2040.SHARED_ADC, motor2040.VOLTAGE_GAIN)
cur_adc = Analog(motor2040.SHARED_ADC, motor2040.CURRENT_GAIN,
                 motor2040.SHUNT_RESISTOR, motor2040.CURRENT_OFFSET)

mux = AnalogMux(motor2040.ADC_ADDR_0, motor2040.ADC_ADDR_1, motor2040.ADC_ADDR_2)

# control functions
mode=1 # forward
modeCount= 0
minFrontDistance = 10.0
def mode_forwards(range):
    global modeCount
    mode= 1
    if range < minFrontDistance:
        myRobot.strafe_right(1.)
        mode = 2
        modeCount=0
        #print("forwards ",mode)
        modeSTR["autostatus"]= "a2"
        #print(modeSTR)
        sendMode(modeSTR)
    return mode

# this gets called when the robot is to close to the wall so moves to the right
# sometimes it moves forward diagonally, if this happens and the range gets less than 2 it backs
## off nd strts again.
# need to isnert a delay between getting a range > 10 and switching to forward mode
# to ensure the robot left hand side is clear of the obstruction

def mode_strafe_right(range):
    global modeCount
    mode= 2
    if range > minFrontDistance:
        modeCount+=1
        if modeCount > 60:
            myRobot.drive_forward(1.0)
            mode =1
            sendMode(modeSTR)
            modeSTR["autostatus"]= "a1"
            #print(modeSTR)
        #print("strafe right ",mode)
    elif range < 2:
        # reverse because too close
        myRobot.drive_forward(-1.0)
        mode=3
        #print("strafe right ",mode)
        modeSTR["autostatus"]= "a3"
        #print(modeSTR)
        sendMode(modeSTR)
    return mode

def mode_back_up(range):
    mode=3
    if range > minFrontDistance:
        myRobot.strafe_right(1.)
        mode =2
        #print("back up ",mode)
        modeSTR["autostatus"]= "a2"
        #print(modeSTR)
        sendMode(modeSTR)
    return mode

def default_option():
    stop()
    return 4

switch_dict={
    1: mode_forwards,
    2: mode_strafe_right,
    3: mode_back_up
    }

def switch_mode_dict(value):
    func = switch_dict.get(value, default_option)
    return func




# Create the user button
user_sw = Button(motor2040.USER_SW)
timedelay = 5

led = WS2812(motor2040.NUM_LEDS, 1, 0, motor2040.LED_DATA, rgbw=True)
led.start()

timeSlots = [0 for i in range(11)]
# everything based on cycle time
UPDATES = 100     # How many times to update the motor per second
UPDATE_RATE = 1 / UPDATES
UPDATE_RATE_MSECS = 1000 * UPDATE_RATE

led.set_rgb(0, 255, 0, 0)

print("go")
myRobot.stop()
cmode = "s"
modeSTR = {
    "status" : cmode,
    "autostatus" : mode,
    "range" : 0,
    "volts" : 0
    }
def sendMode(mode):
    jsonmode=json.dumps(mode)
    uart.write(jsonmode)
    uart.write("\n")
    #print(jsonmode)

def decodeUartdata(cmode):
    if uart.any(): # update mode if received a comman
        data = uart.readline()
        print(data[0])
        if data[0]==  102: # f
            cmode = "f"
            r, g, b = colours[cmode]
            myRobot.drive_forward(1.0)
            modeSTR["status"]= cmode
            sendMode(modeSTR)
            #print(modeSTR)
        elif data[0]== 98: #b
            cmode= "b"
            r, g, b = colours[cmode]
            myRobot.drive_forward(-1.0)
            modeSTR["status"]= cmode
            #print(modeSTR)
            sendMode(modeSTR)
        elif data[0]== 108: #l
            cmode ="l"
            r, g, b = colours[cmode]
            modeSTR["status"]= cmode
            #print(modeSTR)
            myRobot.turn_left(1.0)
            sendMode(modeSTR)
        elif data[0]== 114: #r
            cmode = "r"
            r, g, b = colours[cmode]
            myRobot.turn_right(1.0)
            modeSTR["status"]= cmode
            #print(modeSTR)
            sendMode(modeSTR)
        elif data[0]== 115: #s
            cmode ="s"
            r, g, b = colours[cmode]
            modeSTR["status"]= cmode
            #print(modeSTR)
            myRobot.stop()
            sendMode(modeSTR)
        elif data[0] == 97: #a
            cmode= "a"
            r, g, b = colours[cmode]
            mode = 1
            myRobot.drive_forward(1.0)
            mode =switch_mode_dict(mode)(frontDistance)
            modeSTR["status"]= cmode
            modeSTR["autostatus"]= "??"
            #print(modeSTR)
            sendMode(modeSTR)
            
    return cmode
            
oldcmode= "s"  #mode received over serial link
# Continually move the motor until the user button is pressed
colours = { "s" : [255, 0, 0],
            "f" : [0, 255, 0],
            "b" : [0, 0, 255],
            "l" : [255, 0, 255],
            "r" : [255, 255, 0],
            "a" : [255, 255, 255]}
r, g, b = colours[cmode]
ledFlashCount = 0
ledFlashMax = 100
rangeCount = 0
myRobot.enable()

while not user_sw.raw():
    timeStart = time.ticks_ms()
    frontDistance = frontSonar.distance_cm()
    rangeCount+=1
    if rangeCount > 50:
        rangeCount=0
        rangeSTR = str(round(frontDistance, 1)) + " " + cmode + str(mode) + " \n"
        #print(rangeSTR)
        modeSTR["range"] =frontDistance
        #print(modeSTR)
       
        a2d=[]
        '''
        for addr in range(motor2040.NUM_SENSORS):
            mux.select(addr + motor2040.SENSOR_1_ADDR)
            a2d.append(sen_adc.read_voltage() )
            #print("Sensor", addr + 1, "=", sen_adc.read_voltage())
        '''
        mux.select(motor2040.VOLTAGE_SENSE_ADDR)
        volts = vol_adc.read_voltage()
        a2d.append(volts )
        #print("Voltage =", vol_adc.read_voltage(), "V")

        for addr in range(motor2040.NUM_MOTORS):
            mux.select(addr + motor2040.CURRENT_SENSE_A_ADDR)
            a2d.append(cur_adc.read_voltage() )
            #print("Current", addr + 1, "=", cur_adc.read_current(), "A")
        #print(a2d)
        modeSTR["volts"] = volts
        sendMode(modeSTR)

    cmode = decodeUartdata(cmode)
    #print(cmode)
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
#print("stop")    
myRobot.disable()
print(timeSlots)

led.clear()
while True:
    time.sleep(1)
    pass

#print("done")