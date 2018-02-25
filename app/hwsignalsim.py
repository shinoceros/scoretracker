import os
import sys
import zmq
import thread
import time
import random
import string
from persistentdict import PersistentDict

try:
    from msvcrt import getch
except ImportError:
    def getch():
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

def send_msg(trigger, data):
    global socket
    msg = {'trigger': trigger, 'data': data}
    sys.stdout.write("\r%s\r%s" % (" " * 60, msg))
    socket.send_json(msg)

################################################

os.system('clear')
print "HW Signal Simulator\n\nUse the following keys:\n(1) goal home\n(2) goal away\n(3) RFID tag\n(x) Exit Simulator\n"
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind('tcp://127.0.0.1:5557')

# read RFID map
with PersistentDict('players.json', 'c', format='json') as d:
    rfidMap = d.get('rfidmap', {})
    lenMap = rfidMap.__len__()

while True:
    char = getch()
    if char == 'x':
        sys.stdout.write("\r%s\r" % " " * 30)
        break;
    elif char == '1':
        send_msg('goal', '0')
    elif char == '2':
        send_msg('goal', '1')
    elif char == '3' :
        if lenMap == 0:
            rfid = "".join([random.choice(string.digits) for i in xrange(8)])
        else:
            idx = random.randint(0, lenMap - 1)
            rfid = rfidMap.keys()[idx]
        send_msg('rfid', rfid)
    else:
        pass

