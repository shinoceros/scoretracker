from persistentdict import PersistentDict

class PlayerDataBase(object):

    def __init__(self):
        self.players = []
        self.rfid_map = {}
        self.ranking = {'attacker': {}, 'defender': {}}
        # min and max values among all players' elo
        self.ranges = {'attacker': {'min': 0, 'max': 2000}, 'defender': {'min': 0, 'max': 2000}}
        
        self.STORAGE_FILE = 'players.json'
        
        self.STORAGE_PLAYERS = 'players'
        self.STORAGE_RFIDMAP = 'rfidmap'
        self.STORAGE_RANKING_ATTACKER = 'ranking_attacker'
        self.STORAGE_RANKING_DEFENDER = 'ranking_defender'
        
        self.__reload()

    def __reload(self):
        with PersistentDict(self.STORAGE_FILE, 'c', format='json') as dictionary:
            self.players = dictionary.get(self.STORAGE_PLAYERS, [])
            self.rfid_map = dictionary.get(self.STORAGE_RFIDMAP, {})
            self.ranking['attacker'] = dictionary.get(self.STORAGE_RANKING_ATTACKER, {})
            self.ranking['defender'] = dictionary.get(self.STORAGE_RANKING_DEFENDER, {})

        self.__calc_statistics()
        
    def get_players(self):
        # copy player array
        retval = self.players[:]
        # add ranking info
        for player in retval:
            player = self.__combine_data(player)
        return retval

    def set_players(self, players):
        self.players = players
        # store players in file
        with PersistentDict(self.STORAGE_FILE, 'c', format='json') as dictionary:
            dictionary[self.STORAGE_PLAYERS] = self.players

    def set_ranking(self, type, data):
        if type == 'attacker':
            ranking_key = self.STORAGE_RANKING_ATTACKER
        elif type == 'defender':
            ranking_key = self.STORAGE_RANKING_DEFENDER
        else:
            return
        self.ranking[type] = data
        self.__calc_statistics()
        # store ranking in file
        with PersistentDict(self.STORAGE_FILE, 'c', format='json') as dictionary:
            dictionary[ranking_key] = data
        
        self.__reload()
            
    def get_rfid_map(self):
        return self.rfid_map

    def add_rfid(self, rfid, player_id):
        self.rfid_map[rfid] = player_id
        self.__write_rfid_map()

    def remove_rfid(self, rfid):
        self.rfid_map.pop(rfid)
        self.__write_rfid_map()

    def __write_rfid_map(self):
        with PersistentDict(self.STORAGE_FILE, 'c', format='json') as dictionary:
            dictionary[self.STORAGE_RFIDMAP] = self.rfid_map

    def get_player_by_id(self, player_id):
        for player in self.players:
            if player['id'] == player_id:
                return self.__combine_data(player);
        return None

    def get_player_by_rfid(self, rfid):
        return self.rfid_map.get(rfid, None)
        
    def __combine_data(self, player):
        id = str(player['id'])
        # fallback
        player[u'attacker'] = {'elo': 1200.0}
        player[u'defender'] = {'elo': 1200.0}
        if id in self.ranking['attacker']:
            player[u'attacker'] = self.ranking['attacker'][id]
        if id in self.ranking['defender']:
            player[u'defender'] = self.ranking['defender'][id]
        return player
        
    def __calc_statistics(self):
        self.ranges = {'min': 999999, 'max': -999999}

        for i in self.ranking['attacker']:
            elo = self.ranking['attacker'][i]['elo']
            self.ranges['min'] = min(self.ranges['min'], elo)
            self.ranges['max'] = max(self.ranges['max'], elo)
            
        for i in self.ranking['defender']:
            elo = self.ranking['defender'][i]['elo']
            self.ranges['min'] = min(self.ranges['min'], elo)
            self.ranges['max'] = max(self.ranges['max'], elo)

    def get_ranges(self):
        return self.ranges
            
PlayerData = PlayerDataBase()

if __name__ == '__main__':
    #print PlayerData.get_players()
    print PlayerData.get_player_by_id(12)
    