from kivy.clock import Clock
from soundmanager import SoundManager, Trigger
from playerdata import PlayerData
import subprocess

class NetworkInfoBase(object):

    def __init__(self):
        self.state = None
        self.ip_address = None
        self.id_str = None
        self.player = None
        self.connected = False
        self.callbacks = []

    def start_polling(self):
        Clock.schedule_interval(self.__fetch_data, 1.0)

    def stop_polling(self):
        Clock.unschedule(self.__fetch_data)

    def register(self, cb_function):
        self.callbacks.append(cb_function)
        # initially send current network info to new client
        cb_function(self.get_data())

    def __fetch_data(self, dt):
        cmd = 'wpa_cli status | egrep "(wpa_state|id_str|ip_address)"'
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        entries = {}
        for line in iter(proc.stdout.readline, ''):
            line = line.strip()
            if '=' in line:
                (key, value) = line.split('=')
                entries[key] = value

        self.state = entries.get('wpa_state', 'DISCONNECTED')
        self.ip_address = entries.get('ip_address', '')
        self.id_str = entries.get('id_str', '')

        connected = (self.state == 'COMPLETED' and self.ip_address != '')
        if connected != self.connected:
            self.connected = connected
            if self.connected:
                try:
                    player_id = int(self.id_str)
                    self.player = PlayerData.get_player_by_id(player_id)
                except Exception, e:
                    print e
                    self.player = None
            else:
                self.player = None

            self.say_connection_status()

            # notify all registered clients
            for cb_function in self.callbacks:
                cb_function(self.get_data())

    def get_data(self): 
        if self.player is not None:
            hostname = self.player['name']
        else:
            hostname = self.id_str
        return {'connected': self.connected, 'ip_address': self.ip_address, 'hostname': hostname}

    def say_connection_status(self):
        if self.connected:
            SoundManager.play(Trigger.HOTSPOT_CONNECT, self.player)
        else:
            SoundManager.play(Trigger.HOTSPOT_DISCONNECT)

NetworkInfo = NetworkInfoBase()
