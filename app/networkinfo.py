from kivy.clock import Clock
from soundmanager import SoundManager, Trigger
import subprocess

class NetworkInfoBase(object):

    def __init__(self, **kwargs):
        self.state = None
        self.ip_address = None
        self.id_str = None
        self.is_connected = False
        
    def start_polling(self):
        Clock.schedule_interval(self.__fetch_data, 1.0)

    def stop_polling(self):
        Clock.unschedule(self.__fetch_data)
        
    def __fetch_data(self, dt):
        cmd = 'wpa_cli status | egrep "(wpa_state|id_str|ip_address)"'
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
        entries = {}
        for line in iter(proc.stdout.readline, ''):
            line = line.strip()
            if '=' in line:
                (k, v) = line.split('=')
                entries[k] = v

        self.state = entries.get('wpa_state', 'DISCONNECTED')
        self.ip_address = entries.get('ip_address', '')
        self.id_str = entries.get('id_str', '')

        try:
            self.id_str = int(self.id_str)
        except:
            pass

        connected = (self.state == 'COMPLETED' and self.ip_address != '')
        if connected != self.is_connected:
            if connected:
                data = {'id': self.id_str}
                SoundManager.play(Trigger.HOTSPOT_CONNECT, data)
            else:
                SoundManager.play(Trigger.HOTSPOT_DISCONNECT)
            self.is_connected = connected
                
    def get_data(self):
        return {'state': self.state, 'ip_address': self.ip_address, 'id_str': self.id_str}

NetworkInfo = NetworkInfoBase()
