from kivy.logger import Logger
from kivy.core.audio import SoundLoader
from kivy.clock import Clock

class SoundIssuer(object):

    def __init__(self):
        self.bg_track = None
#        self.fg_objs = []

    def start_sound(self, path, volume, loop):
        sound = SoundLoader.load(path)
        if sound:
            sound.loop = loop
            sound.volume = volume
            if loop:
                # stop background track if running
                self.stop_loop()
                self.bg_track = sound
                self.bg_track.play()
            else:
                sound.play()

    def play(self, path, volume, loop, delay):
        Clock.schedule_once(lambda dt: self.start_sound(path, volume, loop), delay)

    def stop_loop(self):
        if self.bg_track is not None:
            self.bg_track.stop()
            self.bg_track.unload()
            self.bg_track = None
