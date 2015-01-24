import urllib2
import settings
import json

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
        req = urllib2.Request(self.baseurl + '/api/player')
        resp = urllib2.urlopen(req, timeout=10)
        return self.__convertPlayerData(resp.read())
        
if __name__ == "__main__":
    sc = ServerComm()
    print(sc.fetchPlayers())