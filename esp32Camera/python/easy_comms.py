from machine import UART, Pin
import time

class Easy_comms:
    baud_rate = 9600

    def __init__(self, uart_id:int, baud_rate:int=None, txPin:int=16, rxPin:int=17):
        if baud_rate:
            self.baud_rate = baud_rate
        self.uart = UART(uart_id, self.baud_rate, tx=Pin(txPin), rx=Pin(rxPin))
        self.uart.init()

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
