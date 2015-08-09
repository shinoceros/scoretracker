from persistentdict import PersistentDict
import settings

class PlayerDataBase(object):

    def __init__(self):
        self.players = []
        self.rfid_map = {}

        with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as dictionary:
            self.players = dictionary.get(settings.STORAGE_PLAYERS, [])
            self.rfid_map = dictionary.get(settings.STORAGE_RFIDMAP, {})

    def get_players(self):
        return self.players

    def set_players(self, players):
        self.players = players
        # store players in file
        with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as dictionary:
            dictionary[settings.STORAGE_PLAYERS] = self.players

    def get_rfid_map(self):
        return self.rfid_map

    def add_rfid(self, rfid, player_id):
        self.rfid_map[rfid] = player_id
        self.__write_rfid_map()

    def remove_rfid(self, rfid):
        self.rfid_map.pop(rfid)
        self.__write_rfid_map()

    def __write_rfid_map(self):
        with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as dictionary:
            dictionary[settings.STORAGE_RFIDMAP] = self.rfid_map

    def get_player_by_id(self, player_id):
        return next((item for item in self.players if item["id"] == player_id), None)

    def get_player_by_name(self, player_name):
        return next((item for item in self.players if item["name"] == player_name), None)

    def get_player_by_rfid(self, rfid):
        return self.rfid_map.get(rfid, None)

PlayerData = PlayerDataBase()
