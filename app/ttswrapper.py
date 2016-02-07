import settings
import subprocess
from servercom import ServerCom

class TtsWrapper(object):

    def __init__(self, **kwargs):
        self.mode = settings.TTS_MODE

    def __create_offline(self, player, path):
        cmd = "espeak -s110 -v{} \"{}\" --stdout | " \
        "sox --norm --type wav - --type mp3 --rate 44100 --channels 2 " \
        "--compression 192 \"{}\"".format("mb-de7", player['name'], path)
        subprocess.call(cmd, shell=True)
        # TODO: SoundManager: add new sound to pool
        #self.map_sound_files['player']['map'][player_id] = path

    def __create_online(self, text, path):
        tmp_path = "/tmp/tts.mp3"
        url = settings.TTS_ONLINE_URL.format(key=settings.TTS_ONLINE_KEY, text=text, lang=settings.TTS_ONLINE_LANG)
        ServerCom.fetch_and_store(url, tmp_path)
        cmd = "sox --norm \"{}\" \"{}\"".format(tmp_path, path)
        subprocess.call(cmd, shell=True)

    def create_audio(self, text, path):
        res = False
        if self.mode == 'offline':
            res = self.__create_offline(text, path)
        elif self.mode == 'online':
            res = self.__create_online(text, path)
        else:
            res = False
        return res
