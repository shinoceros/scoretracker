import urllib

def goal(idx):
    if idx == 0:
        send('goal_home')
    elif idx == 1:
        send('goal_away')

def rfid(rfid):
    send('rfid', rfid)

def send(triggerType, parameter=None):
    paramsDict = {'trigger': triggerType}
    if parameter != None:
        paramsDict['param'] = parameter
    params = urllib.urlencode(paramsDict)
    try:
        f = urllib.urlopen("http://localhost:5000/notify", params)
        print f.read()
    except IOError:
        pass

