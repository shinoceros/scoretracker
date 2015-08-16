import zmq

class HardwareListener(object):

    def __init__(self):
        # Socket to talk to server
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect("tcp://127.0.0.1:5555")
        self.socket.connect("tcp://127.0.0.1:5556")
        self.socket.connect("tcp://127.0.0.1:5557")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, u"")

    def read(self):
        try:
            return self.socket.recv_json(zmq.NOBLOCK)
        except zmq.ZMQError:
            return None

if __name__ == "__main__":
    hwl = HardwareListener()

    while True:
        msg = hwl.read()
        if msg == None:
            pass
        else:
            if 'trigger' in msg and 'data' in msg:
                print "%s: %s" % (msg['trigger'], msg['data'])
