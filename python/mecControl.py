import time

from pimoroni import Analog, AnalogMux, Button
from motor import motor2040 # for access tosensors on motor2040 board
from plasma import WS2812 # for on board led control
from hcsro4 import HCSR04 # range finder
from machine import  Pin  # serial
from mecRobot import Meccanum  # motor control
import json # communication with esp32-cam
from easy_comms import Easy_comms
import _thread

frontSonar = HCSR04(trigger_pin=21, echo_pin=20, echo_timeout_us=10000)
myRobot = Meccanum()


UPDATES = 100                           # How many times to update the motor per second
UPDATE_RATE = 1 / UPDATES
TIME_FOR_EACH_MOVE = 2                  # The time to travel between each value
UPDATES_PER_MOVE = TIME_FOR_EACH_MOVE * UPDATES
PRINT_DIVIDER = 4                       # How many of the updates should be printed (i.e. 2 would be every other update)
'''
queue defintions
'''
def core1_task(_):
    rx_buf = ""

    while True:
        if status_queue:
            s = q_get(status_queue, status_lock)
            if s is not None:
                comms.send(s)

        data = comms.read_available()
        if data:
            rx_buf += data
            while '\n' in rx_buf:
                line, rx_buf = rx_buf.split('\n', 1)
                line = line.strip()
                if line:
                    q_put(cmd_queue, cmd_lock, line)

        time.sleep_ms(1)



def q_get_nowait(q, lock):
    if lock.acquire(False):          # try to take lock, but don’t block
        try:
            if q:
                return q.pop(0)
            else:
                return None
        finally:
            lock.release()
    else:
        # someone else is using the queue; treat as empty for now
        return None

def q_put(q, lock, item):
    while True:
        if lock.acquire(False):
            q.append(item)
            lock.release()
            return
        time.sleep_ms(1)

def q_get(q, lock):
    while True:
        if lock.acquire(False):
            if q:
                item = q.pop(0)
                lock.release()
                return item
            lock.release()
        time.sleep_ms(1)


cmd_queue = []
status_queue = []
cmd_lock = _thread.allocate_lock()
status_lock = _thread.allocate_lock()
#
comms = Easy_comms(0, 19200, txPin=16, rxPin=17)
_thread.start_new_thread(core1_task, (None,))
'''
'''
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
led.set_rgb(0, 255, 255, 255)
time.sleep(1)
myRobot.stop()
led.set_rgb(0, 255, 0, 0)
time.sleep(1)
cmode = "s"
modeSTR = {
    "status" : cmode,
    "autostatus" : mode,
    "range" : 0,
    "volts" : 0
    }
def sendMode(mode):
    jsonmode=json.dumps(mode)
    q_put(status_queue, status_lock, jsonmode)
    #print(jsonmode)


            
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
led.set_rgb(0, 0, 255, 0)
time.sleep(1)
while not user_sw.raw():
    timeStart = time.ticks_ms()
    # get new command
    cmd = q_get_nowait(cmd_queue, cmd_lock)
    #print(f'message: {cmd}')
    if cmd is not None :
        #print(f'message: {cmd}')
        try:
            command = json.loads(cmd)
            #print(f'json: {command}')
            if command['command'] == 'forwards':
                cmode = "f"
                #print(cmode)
                r, g, b = colours[cmode]
                myRobot.drive_forward(1.0)
            elif command['command'] == 'left':
                cmode = "l"
                r, g, b = colours[cmode]
                myRobot.turn_left(1.0)
            elif command['command'] == 'right':
                cmode = "r"
                r, g, b = colours[cmode]
                myRobot.turn_right(1.0)
            elif command['command'] == 'back':
                cmode = "b"
                r, g, b = colours[cmode]
                myRobot.drive_forward(-1.0)
            elif command['command'] == 'stop':
                cmode = "s"
                r, g, b = colours[cmode]
                myRobot.drive_forward(0)
            elif command['command'] == 'auto':
                cmode = "a"
                r, g, b = colours[cmode]
                mode = 1
                myRobot.drive_forward(1.0)
                mode =switch_mode_dict(mode)(frontDistance)
            elif command['command'] == 'line':
                cmode = "li"
            
            time.sleep(0.1)
        except Exception as e:
            print(f'error: {e} {cmd}')
            print("xx")
            
    frontDistance = frontSonar.distance_cm()
    rangeCount+=1
    if rangeCount > 50:
        rangeCount=0
        
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
        #print(delayTime)
        time.sleep_ms(delayTime)
#print("stop")    
myRobot.disable()
print(timeSlots)

led.clear()
while True:
    time.sleep(1)
    pass

#print("done")