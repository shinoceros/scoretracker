import requests
import shutil
import json
import settings
from kivy.logger import Logger

class ServerComBase:
    def __init__(self):
        self.base_url = settings.SERVER_BASE_URL
        self.user_id = settings.SERVER_USER_ID
        self.user_pin = settings.SERVER_USER_PIN
        self.session = requests.Session()

    def __post(self, url, data):
        response = self.session.post(url, data=json.dumps(data), timeout=7)
        return response

    def __login(self):
        url = self.base_url + '/auth/login'
        data = {
            'userId': self.user_id,
            'pin': self.user_pin
        }
        return self.__post(url, data)

    def __submit_score(self, players, goals):
        url = self.base_url + '/match'
        data = {
            'f1': players[0]['id'],
            'b1': players[1]['id'],
            'f2': players[2]['id'],
            'b2': players[3]['id'],
            'goals1': goals[0],
            'goals2': goals[1]
        }
        return self.__post(url, data)

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

    def submit_score(self, players, goals):
        try:
            # try to submit score
            response = self.__submit_score(players, goals)
            if response.status_code == 401:
                # on fail try to login first
                if self.__login().status_code != 200:
                    return ('Login failed', None)
                # login successful -> submit again
                response = self.__submit_score(players, goals)
            
            if response.status_code == 200:
                data = response.json()
                elo = data.get('deltaelo', 0.0)
                return (None, elo)
            else:
                return ('Submit failed', None)

        except requests.exceptions.ConnectionError as e:
            print e
            return ('Connection error', None)
        except requests.exceptions.Timeout as e:
            print e
            return ('Timeout error', None)

    def fetch_and_store(self, url, path):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(path, 'wb') as fd:            
                    response.raw.decode_content = True
                    shutil.copyfileobj(response.raw, fd)
                return (None, response.raw)
            else:
                return ('Invalid return code: {}'.format(response.status_code), None)
        except requests.exceptions.ConnectionError as e:
            print e
            return ('Connection error', None)
        except requests.exceptions.Timeout as e:
            print e
            return ('Timeout error', None)

ServerCom = ServerComBase()

if __name__ == "__main__":
    print(ServerCom.fetch_players())