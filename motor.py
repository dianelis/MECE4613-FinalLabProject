#!/usr/bin/env python3

"""
A sample library to move robot.
"""


# Import required libraries
from adafruit_crickit import crickit as ck
import time
import os
from functools import partial




# Hyper parameters
SyncForwardR = 0.95    # the right motor's sync coefficient when it moves forward
SyncBackwardR = 0.95   # the right motor's sync coefficient when it moves backward
MOTOR = {'R': ck.dc_motor_1, 'L': ck.dc_motor_2}
THROTTLE_SPEED = {0: 0, 1: 0.35, 2: 0.5, 3: 0.7, 4: 0.9}





def set_throttle(motor_name, speed, factor=1):
    """
    Args:
        - motor_name: 'R' or 'L'
        - speed: the throttle speed from the THROTTLE_SPEED dictionary's keys
        - factor: 1 or -1 showing forward or backward motionsc
    Output:
        - applies current to the dc motors wrt the SyncForwardR or SyncBackwardR
    """
    if motor_name == 'R':
        if factor > 0:
            sync = SyncForwardR
        else:
            sync = SyncBackwardR
    else:
        sync = 1.0
    if motor_name == 'R':
        factor = -factor
    MOTOR[motor_name].throttle = THROTTLE_SPEED[speed] * sync * factor
 


def move(duration=0.3, speed=2, factor_r=1, factor_l=1):
    """
    Args:
        - duration: the time that the motion will be executed
        - speed: the motor speed from THROTTLE_SPEED dictionary
        - factor_r, factor_l: 1 or -1 : show which direction the motor should rotate
    Output:
        - the motors' rotation
    """
    set_throttle('R', speed, factor_r)
    set_throttle('L', speed, factor_l)
    time.sleep(duration)
    set_throttle('R', 0)
    set_throttle('L', 0)
 

# expand move() to define forward, backward, right, left, spin_right and spin_left functions
forward = partial(move)
backward = partial(move, factor_r=-1, factor_l=-1)
right = partial(move, factor_l=0.5)
left = partial(move, factor_r=0.5)
spin_right = partial(move, factor_r=1, factor_l=-1)
spin_left = partial(move, factor_r=-1, factor_l=1)
noop = lambda: None
