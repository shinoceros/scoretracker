from kivy.logger import Logger
from kivy.clock import Clock
import subprocess
import shlex
import os
from enum import Enum
from threading import Thread
#from queue import Queue
import glob
import random
from collections import deque
from soundissuer import SoundIssuer
from functools import partial

class Trigger(Enum):
    MENU = 0
    GAME_START = 1
    GAME_END = 2
    GOAL = 3 # data: goals1, goals2
    DENIED = 4
    RFID = 5
    PLAYER_JOINED = 6 # data: player dict
    BUTTON = 7
    BACK = 8
    EXIT = 9
    SWIPE = 10
    PLAYER_SELECTED = 11 # data: player dict

class SoundManagerBase(object):

    BASEPATH = './assets/sounds/'
    EXT = '.mp3'

    def __init__(self):
        self.si = SoundIssuer()
        #self.queue = Queue()
        self.stopped = False

        self.map_sound_files = {
            'menu':    { 'type': 'random', 'path': 'menu/*' },
            'whistle': { 'type': 'fixed', 'path': 'whistle_medium' },
            'goal':    { 'type': 'random', 'path': 'goal/*' },
            'stadium': { 'type': 'random', 'path': 'stadium/*' },
            'denied':  { 'type': 'fixed', 'path': 'chime_down2' },
            'button':  { 'type': 'fixed', 'path': 'chime_medium1' },
            'back':    { 'type': 'fixed', 'path': 'chime_low1' },
            'exit':    { 'type': 'fixed', 'path': 'chime_down3' },
            'rfid':    { 'type': 'fixed', 'path': 'chime_up3' },
            'player':  { 'type': 'indexed', 'path': 'players/*' }
        }

        # read sound files
        for key in self.map_sound_files:
            entry = self.map_sound_files[key]
            files = glob.glob(self.BASEPATH + entry['path'] + self.EXT)
            if entry['type'] == 'indexed':
                self.map_sound_files[key]['map'] = {}
                for f in files:
                    (name, ext) = os.path.splitext(os.path.basename(f))
                    self.map_sound_files[key]['map'][int(name)] = f
            else:
                random.shuffle(files)
                self.map_sound_files[key]['files'] = deque(files)

        self.map_trigger = {
            Trigger.MENU:           [{ 'sound': 'menu',    'volume': 20,  'loop': True , 'delay': 0.0 }],
            Trigger.GAME_START:     [
                                        { 'sound': 'whistle', 'volume': 100, 'loop': False, 'delay': 0.0 },
                                        { 'sound': 'stadium', 'volume': 50, 'loop': True, 'delay': 0.0 }
                                    ],
            Trigger.GAME_END:       [
                                        { 'sound': 'whistle', 'volume': 100, 'loop': False, 'delay': 0.0 },
                                        { 'sound': 'menu',    'volume': 50,  'loop': True , 'delay': 0.0 }
                                    ],
            Trigger.GOAL:           [{ 'sound': 'goal',    'volume': 100, 'loop': False, 'delay': 0.0 }],
            Trigger.DENIED:         [{ 'sound': 'denied',  'volume': 100, 'loop': False, 'delay': 0.0 }],
            Trigger.RFID:           [{ 'sound': 'rfid',    'volume': 100, 'loop': False, 'delay': 0.0 }],
            Trigger.BUTTON:         [{ 'sound': 'button',  'volume': 100, 'loop': False, 'delay': 0.0 }],
            Trigger.BACK:           [{ 'sound': 'back',    'volume': 100, 'loop': False, 'delay': 0.0 }],
            Trigger.EXIT:           [{ 'sound': 'exit',    'volume': 100, 'loop': False, 'delay': 0.0 }],
            Trigger.SWIPE:          [{ 'sound': 'button',  'volume': 100, 'loop': False, 'delay': 0.0 }],
            Trigger.PLAYER_JOINED:  [
                                        { 'sound': 'rfid',    'volume': 100, 'loop': False, 'delay': 0.0 },
                                        { 'sound': 'player',  'volume': 100, 'loop': False, 'delay': 0.5 }
                                    ],
            Trigger.PLAYER_SELECTED:  [{ 'sound': 'player',  'volume': 100, 'loop': False, 'delay': 0.0 }]
        }

        self.thread = Thread(target=self.__thread)
        self.thread.start()

    def play(self, trigger, param=None):
        if trigger in self.map_trigger:
            commands = self.map_trigger[trigger]
            for command in commands:
                sound_conf = self.map_sound_files[command['sound']]
                path = ''

                if sound_conf['type'] == 'random':
                    if len(sound_conf['files']):
                        path = sound_conf['files'][0]
                        sound_conf['files'].rotate(1)
                elif sound_conf['type'] == 'fixed':
                    if len(sound_conf['files']):
                        path = sound_conf['files'][0]
                elif sound_conf['type'] == 'indexed':
                    # ayayay....
                    if 'id' in param and param['id'] in sound_conf['map']:
                        path = sound_conf['map'][param['id']]

                if path != '':
                    self.si.play(path, command['volume'], command['loop'], command['delay'])

    def __thread(self):
        pass

    def create_player_sound(self, player):
        if 'id' in player:
            id = player['id']
            if id in self.map_sound_files['player']['map']:
                path = self.map_sound_files['player']['map'][id]
                if not os.path.isfile(path):
                    # create TTS file
                    cmd = "espeak -s110 -v%s \"%s\" --stdout | avconv -i - -ar 44100 " \
                    "-ac 2 -ab 192k -f mp3 \"%s\"" % ("mb-de7", player['name'], path)
                    subprocess.call(cmd, shell=True)
                    Logger.info("ScoreTracker: TTS file generated: %s" % path)

SoundManager = SoundManagerBase()
