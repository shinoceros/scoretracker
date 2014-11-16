from flask import Flask, Response, request, send_from_directory
import os
import gevent
from gevent.wsgi import WSGIServer
from gevent.queue import Queue
import time
import json

app = Flask(__name__)
subscriptions = []

# SSE "protocol" is described here: http://mzl.la/UPFyxY
class ServerSentEvent(object):

    def __init__(self, data):
        self.data = data
        self.desc_map = {
            self.data : "data",
        }

    def encode(self):
        if not self.data:
            return ""
        lines = ["%s: %s" % (v, k) 
                 for k, v in self.desc_map.iteritems() if k]
        
        return "%s\n\n" % "\n".join(lines)

@app.route("/")
def index():
    debug_template = """
     <html>
       <head>
       </head>
       <body>
         <h1>Server sent events</h1>
         <div id="event"></div>
         <script type="text/javascript">

         var eventOutputContainer = document.getElementById("event");
         var evtSrc = new EventSource("/listen");

         evtSrc.onmessage = function(e) {
             console.log(e);
             eventOutputContainer.innerHTML = e.data;
         };

         </script>
       </body>
     </html>
    """
    return(debug_template)

@app.route("/debug")
def debug():
    return "Currently %d subscriptions" % len(subscriptions)

@app.route('/notify', methods=['POST'])
def notify_handler():
    def notify(msg):
        for sub in subscriptions[:]:
            sub.put(msg)
    
    trigger = request.form.get('trigger', 'invalid')
    param = request.form.get('param', '')
    data = {'trigger': trigger}
    if len(param) > 0:
        data['param'] = param
    msg = json.dumps(data)
    gevent.spawn(notify, msg)
    
    return msg

@app.route("/listen")
def listen_data():
    def gen():
        q = Queue()
        subscriptions.append(q)
        try:
            while True:
                result = q.get()
                ev = ServerSentEvent(str(result))
                yield ev.encode()
        except GeneratorExit: # Or maybe use flask signals
            subscriptions.remove(q)

    return Response(gen(), mimetype="text/event-stream")

@app.route('/ui/')
@app.route('/ui/<path:filename>')
def ui_proxy(filename = 'index.html'):
    """static ui frontend files are served from here"""
    return send_from_directory('ui', filename)

if __name__ == '__main__':
    app.debug = True
    server = WSGIServer(("", 5000), app)
    server.serve_forever()
