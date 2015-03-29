from kivy.logger import Logger
from kivy.clock import Clock
import subprocess
import shlex
import os.path

class SoundIssuer(object):

    def __init__(self):
        self.loop_obj = None

    def play(self, path, volume, loop, delay):
        if not os.path.isfile(path):
            Logger.warning('SoundIssuer: Sound file not found: %s' % path)
        else:
            self.__runExternalCmd(path, volume, loop, delay)

    def stop_loop(self):
        if self.loop_obj:
            self.loop_obj.kill()
            self.loop_obj.wait()
            self.loop_obj = None

    def __runExternalCmd(self, path, volume, loop, delay):
        if loop:
            self.stop_loop()
            cmd = "mpg321 -q --loop 0 -g {} \"{}\"".format(volume, path)
        else:
            cmd = "mpg321 -q -g {} \"{}\"".format(volume, path)
        p = subprocess.Popen(shlex.split(cmd))
        if loop:
            self.loop_obj = p
