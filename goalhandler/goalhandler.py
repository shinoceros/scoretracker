import RPi.GPIO as GPIO
import sys
import time
import zmq

class GoalHandler:

    GPIO_GOAL0 = 25
    GPIO_GOAL1 = 23
    TIMEOUT = 2000 # in ms

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(True)
        GPIO.setup(self.GPIO_GOAL0, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.GPIO_GOAL1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.GPIO_GOAL0, GPIO.FALLING, callback=self.callback, bouncetime=self.TIMEOUT)
        GPIO.add_event_detect(self.GPIO_GOAL1, GPIO.FALLING, callback=self.callback, bouncetime=self.TIMEOUT)
        
        context = zmq.Context()
        self.socket = context.socket(zmq.PUB)
        self.socket.bind('tcp://127.0.0.1:5555')

    def callback(self, channel):
        data = "0" if channel == self.GPIO_GOAL0 else "1";
        msg = {'trigger': 'goal', 'data': data}
        self.socket.send_json(msg)
        print msg

if __name__ == "__main__":

    g = GoalHandler()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        GPIO.cleanup()
        sys.exit
