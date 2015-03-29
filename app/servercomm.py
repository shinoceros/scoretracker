import urllib2
import settings
import json
from kivy.logger import Logger

class ServerComm:
    def __init__(self):
        self.baseurl = settings.SERVER_BASE_URL

    def __convertPlayerData(self, jsonstr):
        data = json.loads(jsonstr)
        players = []
        for d in data:
            if d['active'] == 1:
                players.append({'id': d['id'], 'name': d['name']})
        return players
        
    def fetchPlayers(self):
        url = self.baseurl + '/api/player'
        req = urllib2.Request(url)
        res = []
        try:
            resp = urllib2.urlopen(req, timeout=10)
            res = self.__convertPlayerData(resp.read())
        except urllib2.URLError, e:
            print e
#            Logger.info('ServerComm', e.args)
        return res
        
if __name__ == "__main__":
    sc = ServerComm()
    print(sc.fetchPlayers())