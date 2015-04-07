import requests
import json
import settings
from kivy.logger import Logger

class ServerComBase:
    def __init__(self):
        self.base_url = settings.SERVER_BASE_URL
        self.user_id = settings.SERVER_USER_ID
        self.user_pin = settings.SERVER_USER_PIN
        self.session = requests.Session()

    def __login(self):
        url = self.base_url + '/auth/login'
        data = {
            'userId': self.user_id,
            'pin': self.user_pin
        }
        return self.session.post(url, json.dumps(data))

    def __submit_score(self, players, goals1, goals2):
        url = self.base_url + '/match'
        data = {
            'f1': players[0]['id'],
            'b1': players[1]['id'],
            'f2': players[2]['id'],
            'b2': players[3]['id'],
            'goals1': goals1,
            'goals2': goals2
        }
        return self.session.post(url, json.dumps(data))

    def __logout(self):
        url = self.base_url + '/auth/logout'
        return self.session.post(url)

    def __convertPlayerData(self, resp):
        players = []
        if resp.status_code == 200:
            try:
                data = resp.json()
                for d in data:
                    if d['active'] == 1:
                        players.append({'id': d['id'], 'name': d['name']})
            except ValueError, e:
                print e

        return players
        
    def fetch_players(self):
        url = self.base_url + '/player'
        r = self.session.get(url)
        return self.__convertPlayerData(r)

    def submit_score(self, players, goals1, goals2):
        try:
            # 1. login
            if self.__login().status_code != 200:
                return False
                
            # 2. submit
            if self.__submit_score(players, goals1, goals2).status_code != 200:
                return False
            pass

            # 3, logout
            if self.__logout().status_code != 200:
                return False
        except requests.ConnectionError, e:
            print e
            return False

        return True

ServerCom = ServerComBase()

if __name__ == "__main__":
    print(ServerCom.fetch_players())