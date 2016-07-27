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

    def __get(self, url, data):
        response = self.session.get(url, timeout=7)
        return response

    def __submit_with_login(self, url, data, fn):
        try:
            response = fn(url, data)
            if response.status_code == 401:
                # on fail try to login first
                if self.__login().status_code != 200:
                    return (False, 'Login failed')
                # login successful -> send again
                response = fn(url, data)
        except requests.exceptions.ConnectionError as e:
            Logger.error('Connection error: {}'.format(url))
            return None
        except requests.exceptions.Timeout as e:
            Logger.error('Timeout error: {}'.format(url))
            return None

        return response

    def __login(self):
        url = self.base_url + '/auth/login'
        data = {
            'userId': self.user_id,
            'pin': self.user_pin
        }
        return self.__post(url, data)
        
    def fetch_players(self):
        url = self.base_url + '/player'
        data = {}
        response = self.__submit_with_login(url, data, self.__get)
        players = []
        if response and response.status_code == 200:
            try:
                data = response.json()
                for d in data:
                    if d['active'] == 1:
                        players.append({'id': d['id'], 'name': d['name']})
            except ValueError, e:
                print e

        return players

    def fetch_ranking(self, type):
        url = self.base_url + '/ranking/' + type
        data = {}
        response = self.__submit_with_login(url, data, self.__get)
        ranking = {}
        if response and response.status_code == 200:
            try:
                data = response.json()
                for d in data:
                    ranking[d['id']] = {'elo': d['elo']}
            except ValueError, e:
                print e

        return ranking

    def submit_score(self, players, goals):
        url = self.base_url + '/match'
        data = {
            'f1': players[0]['id'],
            'b1': players[1]['id'],
            'f2': players[2]['id'],
            'b2': players[3]['id'],
            'goals1': goals[0],
            'goals2': goals[1]
        }
        response = self.__submit_with_login(url, data, self.__post)

        if response and response.status_code == 200:
            data = response.json()
            elo = data.get('deltaelo', 0.0)
            return (None, elo)
        else:
            return ('Submit failed', None)

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
    #print(ServerCom.submit_score([{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}], [6, 3]))
    #print(ServerCom.fetch_players())
    print(ServerCom.fetch_ranking('attacker'))
    #print(ServerCom.fetch_ranking('defender'))