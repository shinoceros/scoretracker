import sys
import zmq
import threading
import time

class HardwareListener(object):

    def __init__(self):
        # Socket to talk to server
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("tcp://127.0.0.1:5555")
        self.socket.connect("tcp://127.0.0.1:5556")
        self.socket.connect("tcp://127.0.0.1:5557")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, u"")

        self.callbacks = []

        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.receive)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def register(self, cb_function):
        self.callbacks.append(cb_function)

    def receive(self):
        while not self.stop_event.is_set():
            try:
                msg = self.socket.recv_json(zmq.NOBLOCK)
                for cb_function in self.callbacks:
                    cb_function(msg)
            except zmq.ZMQError:
                time.sleep(0.05)

if __name__ == "__main__":

    def mycallback(msg):
        print "msg: {}".format(msg)

    hardwarelistener = HardwareListener()
    hardwarelistener.register(mycallback)

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        hardwarelistener.stop()
        sys.exit(0)
