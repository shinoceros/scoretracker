from kivy.logger import Logger
from kivy.clock import Clock
import subprocess
import shlex
import os.path

class SoundManagerBase(object):

    def __fileExists(self, path):
        if not os.path.isfile(path):
            Logger.warning('ScoreTracker: Sound file not found: %s' % path)
            return False
        return True

    def __runExternalCmd(self, path):
        cmd = "mpg321 -q \"%s\"" % path
        subprocess.Popen(shlex.split(cmd))

    def play(self, filename):
        path = "./assets/sounds/%s.mp3" % filename
        if self.__fileExists(path):
            self.__runExternalCmd(path)

    def __getPlayerSoundPath(self, player):
        path = "./assets/sounds/tts/{}.mp3".format(player.get('id'))
        return path

    def createPlayerSound(self, player):
        path = self.__getPlayerSoundPath(player)
        if not self.__fileExists(path):
            # create TTS file
            cmd = "espeak -s110 -v%s \"%s\" --stdout | avconv -i - -ar 44100 -ac 2 -ab 192k -f mp3 \"%s\"" % ("mb-de7", player['name'], path)
            subprocess.call(cmd, shell=True)
            Logger.info("ScoreTracker: TTS file generated: %s" % path)

    def playName(self, player, delay=0.0):
        try:
            path = self.__getPlayerSoundPath(player)
            Clock.schedule_once(lambda dt: self.__runExternalCmd(path), delay)
        except:
            pass

SoundManager = SoundManagerBase()