
# Import required libraries
from datetime import datetime
from picamera2 import Picamera2
import cv2
import os
import signal
import sys


# Hyper parameters
WIDTH, HEIGHT, FPS = 640, 480, 30
# Define parameters where the real-time streaming will be saved
IMG_PATH = os.environ['XDG_RUNTIME_DIR'] + '/robot_stream.jpg'
TMP_PATH = os.environ['XDG_RUNTIME_DIR'] + '/robot_stream_tmp.jpg'

_running = True

def _handle_signal(sig, frame):
    global _running
    _running = False

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def init_camera():
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    return picam2


def save_frames(picam2):
    count = 0
    while _running:
        count += 1
        frame = picam2.capture_array()
        # flip the frame (our camera is upside down)
        frame = cv2.flip(frame, -1)
        cv2.imwrite(TMP_PATH, frame)
        os.replace(TMP_PATH, IMG_PATH)
        print('processing frames:', count, end='\r', flush=True)


def main():

    picam2 = init_camera()

    save_frames(picam2)
 
    picam2.stop()
 




if __name__ == "__main__":
    main()
