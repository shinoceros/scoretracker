import notifier
from  threading import Thread

import random
import string
from  time import sleep

class RfidMonitor(Thread):
    def run(self):
        while True:
		    # create dummy events for now
            chars = "".join([random.choice(string.letters) for i in xrange(16)])
            notifier.rfid(chars)
            sleep(random.uniform(2.0, 5.0))

class GoalMonitor(Thread):
    def run(self):
        while True:
		    # create dummy events for now
            notifier.goal(random.randint(0,1))
            sleep(random.uniform(1.0, 4.0))

r = RfidMonitor()
r.daemon = True
r.start()

g = GoalMonitor()
g.daemon = True
g.start()

while True:
    sleep(1)
