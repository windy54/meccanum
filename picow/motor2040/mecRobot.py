from motor import Motor, motor2040
from encoder import Encoder, MMME_CPR
from pimoroni import Button, REVERSED_DIR
import time
import gc
class Meccanum:
    GEAR_RATIO = 50                         # The gear ratio of the motors
    OTHER_GEAR_RATIO = 298                  # The gear ratio of the problem motor
    COUNTS_PER_REV = MMME_CPR * GEAR_RATIO  # The counts per revolution of each motor's output shaft
    SPEED_SCALE = 5.4                       # The scaling to apply to each motor's rspeed to match its real-world rspeed
    OTHER_SPEED_SCALE = SPEED_SCALE * (GEAR_RATIO / OTHER_GEAR_RATIO)
        # Wheel friendly names
    FL = 0 #A
    FR = 2 #c
    RL = 3 #d
    RR = 1 #b
    motorList =["FL","RR","FR","RR"]

    def __init__(self):

        # Create a list of motors with a given rspeed scale
    
        self.motors = [Motor(motor2040.MOTOR_A, speed_scale=self.SPEED_SCALE),
                  Motor(motor2040.MOTOR_B, speed_scale=self.SPEED_SCALE),
                  Motor(motor2040.MOTOR_C, speed_scale=self.SPEED_SCALE),
                  Motor(motor2040.MOTOR_D, speed_scale=self.SPEED_SCALE)]
        gc.collect()
        '''
        self.encoders = [Encoder(0, 0, motor2040.ENCODER_A, counts_per_rev=self.COUNTS_PER_REV, count_microsteps=True),
            Encoder(0, 1, motor2040.ENCODER_B, counts_per_rev=self.COUNTS_PER_REV, count_microsteps=True),
            Encoder(0, 2, motor2040.ENCODER_C, counts_per_rev=self.COUNTS_PER_REV, count_microsteps=True),
            Encoder(0, 3, motor2040.ENCODER_D, counts_per_rev=self.COUNTS_PER_REV, count_microsteps=True)]
        '''
        # Reverse the direction of the B and D motors and encoders
        self.motors[self.FL].direction(REVERSED_DIR)
        self.motors[self.RL].direction(REVERSED_DIR)
        '''
        self.encoders[self.FL].direction(REVERSED_DIR)
        self.encoders[self.RL].direction(REVERSED_DIR)
        '''
        
        self.captures = [None] * motor2040.NUM_MOTORS
        
    # Helper functions for driving in common directions
    def drive_backward(self,rspeed):
        for m in self.motors:
            m.speed(-rspeed)

    def drive_forward(self, rspeed):
        for m in self.motors:
            m.speed(rspeed)


    def turn_right(self, rspeed):
        self.motors[self.FL].speed(rspeed)
        self.motors[self.FR].speed(-rspeed)
        self.motors[self.RL].speed(rspeed)
        self.motors[self.RR].speed(-rspeed)

    def turn_left(self,rspeed):
        self.motors[self.FL].speed(-rspeed)
        self.motors[self.FR].speed(rspeed)
        self.motors[self.RL].speed(-rspeed)
        self.motors[self.RR].speed(rspeed)


    def strafe_left(self, rspeed):
        self.motors[self.FL].speed(-rspeed)
        self.motors[self.FR].speed(rspeed)
        self.motors[self.RL].speed(rspeed)
        self.motors[self.RR].speed(-rspeed)


    def strafe_right(self, rspeed):
        self.motors[self.FL].speed(rspeed)
        self.motors[self.FR].speed(-rspeed)
        self.motors[self.RL].speed(-rspeed)
        self.motors[self.RR].speed(rspeed)

    def stop(self ):
        for m in self.motors:
            m.speed(0)
    def enable(self ):
        # Enable the motor to get started
        for m in self.motors:
            m.enable()
            
    def disable(self):
        for m in self.motors:
            m.disable()
    
    def get_positions(self):
        for i in range(motor2040.NUM_MOTORS):
            self.captures[i] = self.encoders[i].capture()

if __name__ == '__main__':
    mine=Meccanum()
    print(mine.COUNTS_PER_REV)
    mine.enable()
    mine.get_positions()
    for i in range(4):
        print(mine.motorList[i],mine.captures[i].count, mine.captures[i].degrees)
    mine.drive_forward(1.0)
    time.sleep_ms(1145)
    mine.get_positions()
    for i in range(4):
        print(mine.motorList[i],mine.captures[i].count, mine.captures[i].degrees)
    mine.disable()
