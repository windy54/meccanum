# task and queue comms
from  _thread import allocate_lock, start_new_thread
from machine import UART, Pin
import time

class Qcomms:
    rxData = None
    txData = ""
    rx_lock = allocate_lock()
    tx_lock = allocate_lock()
    
    
    def __init__(self, uart_id:int, baud_rate:int=None, txPin:int=16, rxPin:int=17):
        if baud_rate:
            self.baud_rate = baud_rate
        self.uart = UART(uart_id, self.baud_rate, tx=Pin(txPin), rx=Pin(rxPin))
        self.uart.init()
        self.run = True
        start_new_thread(self.core1_task,())
        
    def core1_task(self):
        rx_buf = ""
        while self.run:

            data = self.read_available()
            if data:
                rx_buf += data
                while '\n' in rx_buf:
                    line, rx_buf = rx_buf.split('\n', 1)
                    line = line.strip()
                    if line:
                        self.rx_lock.acquire(False)
                        self.rxData =line
                        self.rx_lock.release()
            time.sleep_ms(1)

    def read(self):
        self.rx_lock.acquire(False)
        line = self.rxData
        self.rxData =None
        self.rx_lock.release()
        #print("line=",line)
        return line
        
    def write(self,message):
        self.send(message)
        

    def send(self, message:str):
        if not message.endswith('\n'):
            message += '\n'
        self.uart.write(message.encode('utf-8'))

    def read_available(self):
        if self.uart.any():
            data = self.uart.read()
            if data:
                return data.decode('utf-8')
        return ""

if __name__ =='__main__':
    import json
    from time import sleep
    test= Qcomms(0, 19200, txPin=16, rxPin=17)
    led = Pin("LED", Pin.OUT, value=0)
    testMessage = {"command":"hello from pico", "args":"on"}
    json_string=json.dumps(testMessage)
    msgCount = 0

    while True:
        sleep(1)
        message = test.read()
        print("rxd=",message,":")
        test.write(json_string)
   
