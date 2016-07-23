from kivy.logger import Logger
from kivy.core.audio import SoundLoader
from kivy.clock import Clock

# sound rules:
# if loop shall be played: stop current loop sound (there can be only one)
# if new 'stoppable' sound shall be played: stop current stoppable sounds

class SoundIssuer(object):

    def __init__(self):
        self.now_playing = []

    def start_sound(self, path, volume, loop, stoppable):
        sound = SoundLoader.load(path)
        if sound:
            sound.loop = loop
            sound.volume = volume
            if loop:
                self.stop_loop()

            if stoppable:
                self.stop_stoppables()
                    
            sound.bind(on_stop=self._sound_stopped)
            sound.play()
            self.now_playing.append((sound, stoppable))

    def play(self, path, volume, loop, stoppable, delay):
        Clock.schedule_once(lambda dt: self.start_sound(path, volume, loop, stoppable), delay)

    def _sound_stopped(self, stopped_sound):
        if stopped_sound:
            self.now_playing = [(now_playing, stoppable) for (now_playing, stoppable) in self.now_playing if now_playing != stopped_sound]
            stopped_sound.unload()

    def stop_loop(self):
        for (sound, stoppable) in self.now_playing:
            if sound.loop:
                # stop background track if running
                sound.stop()

    def stop_stoppables(self):
        for (sound, stoppable) in self.now_playing:
            if stoppable:
                # stop background track if running
                sound.stop()
