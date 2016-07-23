from kivy.logger import Logger
from kivy.clock import Clock
import subprocess
import os
from enum import Enum
import glob
import random
from collections import deque
from soundissuer import SoundIssuer
from ttswrapper import TtsWrapper
from mutagen.mp3 import MP3
from gamedata import GameData

class Trigger(Enum):
    MENU = 0
    GAME_START = 1
    GAME_END = 2
    GAME_PAUSE = 3
    GAME_RESUME = 4
    GOAL = 5 # data: goals1, goals2
    DENIED = 6
    RFID = 7
    PLAYER_JOINED = 8 # data: player dict
    PLAYERS_SWITCH = 9
    PLAYER_MOVED = 10
    BUTTON = 11
    BACK = 12
    EXIT = 13
    OFFSIDE = 14
    PLAYER_SELECTED = 15 # data: player dict
    INTRO = 16
    HOTSPOT_CONNECT = 17
    HOTSPOT_DISCONNECT = 18
    PLAYERS_SHUFFLE = 19
    TRASH = 20

class SoundManagerBase(object):

    BASEPATH = './assets/sounds/'
    EXT = '.mp3'
	
    def __init__(self):
        self.sound_issuer = SoundIssuer()
        #self.queue = Queue()
        self.stopped = False

        self.map_sound_files = {
            'intro':            {'type': 'random', 'path': 'intro', 'volume': 0.7},
            'menu':             {'type': 'random', 'path': 'menu/*', 'volume': 0.7},
            'whistle':          {'type': 'random', 'path': 'whistle_medium', 'volume': 0.8},
            'kickoff':          {'type': 'random', 'path': 'kickoff', 'volume': 1.0},
            'goal':             {'type': 'random', 'path': 'goal/*', 'volume': 1.0},
            'goal-almost-tie':  {'type': 'random', 'path': 'goal/almost-tie/*', 'volume': 1.0},
            'goal-tie':         {'type': 'random', 'path': 'goal/tie/*', 'volume': 1.0},
            'offside':          {'type': 'random', 'path': 'offside/*', 'volume': 1.0},
            'stadium':          {'type': 'random', 'path': 'stadium/*', 'volume': 0.5},
            'denied':           {'type': 'random', 'path': 'chime_down2', 'volume': 1.0},
            'button':           {'type': 'random', 'path': 'chime_medium1', 'volume': 1.0},
            'back':             {'type': 'random', 'path': 'chime_low1', 'volume': 1.0},
            'exit':             {'type': 'random', 'path': 'shutdown/*', 'volume': 1.0},
            'rfid':             {'type': 'random', 'path': 'chime_up3', 'volume': 1.0},
            'scratch':          {'type': 'random', 'path': 'scratch', 'volume': 0.8},
            'player':           {'type': 'indexed', 'path': 'players/*', 'volume': 1.0},
            'players_switch':   {'type': 'random', 'path': 'players_switch', 'volume': 1.0},
            'player_moved':     {'type': 'random', 'path': 'player_moved', 'volume': 1.0},
            'players_shuffle':  {'type': 'random', 'path': 'players_shuffle', 'volume': 1.0},
            'hotspot_connect':  {'type': 'random', 'path': 'hotspot', 'volume': 1.0},
            'hotspot_disconnect':  {'type': 'random', 'path': 'no_hotspot', 'volume': 1.0},
            'trash':            {'type': 'random', 'path': 'trash/*', 'volume': 1.0}
        }

        # add config for absolute score announcements
        for i in range(0, 6):
            for j in range(0, 6):
                key = 'goal-{}-{}'.format(i, j)
                path = 'goal/{}/{}/*'.format(i, j)
                self.map_sound_files[key] = {'type': 'random', 'path': path, 'volume': 1.0}

        self.map_trigger = {
            Trigger.INTRO:          [
                                        {'sound': 'intro'},
                                        {'sound': 'menu', 'loop': True}
                                    ],
            Trigger.MENU:           [
                                        {'sound': 'menu', 'loop': True}
                                    ],
            Trigger.GAME_START:     [
                                        {'sound': 'stadium', 'loop': True},
                                        {'sound': 'kickoff'},
                                        {'sound': 'player', 'overlap': 0.5},
                                        {'sound': 'whistle', 'overlap': 0.5}
                                    ],
            Trigger.GAME_END:       [
                                        {'sound': 'whistle'},
                                        {'sound': 'menu', 'loop': True}
                                    ],
            Trigger.GAME_PAUSE:     [
                                        {'stoploop': True},
                                        {'sound': 'scratch'}
                                    ],
            Trigger.GAME_RESUME:    [
                                        {'sound': 'stadium', 'loop': True},
                                        {'sound': 'whistle'}
                                    ],
            Trigger.GOAL:           [
                                        {'sound': 'goal', 'stoppable': True}
                                    ],
            Trigger.TRASH:           [
                                        {'sound': 'trash', 'stoppable': True}
                                    ],
            Trigger.DENIED:         [
                                        {'sound': 'denied'}
                                    ],
            Trigger.RFID:           [
                                        {'sound': 'rfid'}
                                    ],
            Trigger.BUTTON:         [
                                        {'sound': 'button'}
                                    ],
            Trigger.BACK:           [
                                        {'sound': 'back'}
                                    ],
            Trigger.EXIT:           [
                                        {'stoploop': True},
                                        {'sound': 'exit'}
                                    ],
            Trigger.OFFSIDE:        [
                                        {'sound': 'offside', 'stoppable': True}
                                    ],
            Trigger.PLAYER_JOINED:  [
                                        {'sound': 'rfid'},
                                        {'sound': 'player', 'overlap': 0.5}
                                    ],
            Trigger.PLAYERS_SWITCH: [
                                        {'sound': 'players_switch'}
                                    ],
            Trigger.PLAYER_MOVED:   [
                                        {'sound': 'player_moved'}
                                    ],
            Trigger.PLAYERS_SHUFFLE:   [
                                        {'sound': 'players_shuffle'}
                                    ],
            Trigger.PLAYER_SELECTED:  [
                                        {'sound': 'player'}
                                    ],
            Trigger.HOTSPOT_CONNECT: [
                                        {'sound': 'hotspot_connect'},
                                        {'sound': 'player'}
                                    ],
            Trigger.HOTSPOT_DISCONNECT: [
                                        {'sound': 'hotspot_disconnect'}
                                    ]
        }

    def init(self, theme):
        self.theme = theme
        self._read_sound_files()

    def _read_sound_files(self):
        # read sound files
        for key in self.map_sound_files:
            entry = self.map_sound_files[key]
            files = glob.glob(self.BASEPATH + entry['path'] + self.EXT)
            if entry['type'] == 'indexed':
                self.map_sound_files[key]['map'] = {}
                for sound_file in files:
                    (name, ext) = os.path.splitext(os.path.basename(sound_file))
                    self.map_sound_files[key]['map'][int(name)] = {'path': sound_file, 'length': self._get_length(sound_file)}
            else:
                random.shuffle(files)
                fileinfo = [{'path': f, 'length': self._get_length(f)} for f in files]
                self.map_sound_files[key]['files'] = deque(fileinfo)
        
    def _get_length(self, filename):
        f = MP3(filename)
        return f.info.length
        
    def play(self, trigger, param=None):
        if trigger in self.map_trigger:
            self.handle_trash_talk(trigger)
            commands = self.map_trigger[trigger]
            delay = 0.0
            add_delay = 0.0
            for command in commands:
                if 'sound' in command:
                    sound_type = self.preprocess_command(command['sound'])
                    sound_conf = self.map_sound_files[sound_type]
                    volume = sound_conf.get('volume', 1.0)
                    loop = command.get('loop', False)
                    stoppable = command.get('stoppable', False)
                    path = ''
                    overlap = command.get('overlap', 0.0)

                    if sound_conf['type'] == 'random':
                        if len(sound_conf['files']):
                            path = sound_conf['files'][0]['path']
                            add_delay = sound_conf['files'][0]['length'] if not loop else 0.0
                            sound_conf['files'].rotate(1)
                    elif sound_conf['type'] == 'indexed':
                        # ayayay....
                        if param and 'id' in param and param['id'] in sound_conf['map']:
                            path = sound_conf['map'][param['id']]['path']
                            add_delay = sound_conf['map'][param['id']]['length']

                    if path != '':
                        delay -= overlap
                        self.sound_issuer.play(path, volume, loop, stoppable, delay)
                        delay += add_delay
                elif 'stoploop' in command:
                    self.sound_issuer.stop_loop()

    def preprocess_command(self, sound_type):
        ''' special handling for goal sounds'''
        # skip unless goal
        if sound_type != 'goal':
            return sound_type

        # check tie
        new_type = 'goal-tie'
        if GameData.is_tie() and self.has_files_for(new_type) and random.random() < 0.3:
            return new_type
        # check almost tie
        new_type = 'goal-almost-tie'
        if GameData.is_almost_tie() and self.has_files_for(new_type) and random.random() < 0.3:
            return new_type
        # check absolute score
        score = GameData.get_score()
        new_type = 'goal-{}-{}'.format(score[0], score[1])
        if self.has_files_for(new_type) and random.random() < 0.3:
            return new_type
        # default
        return 'goal'
        
    def has_files_for(self, sound_type):
        retval = False
        if sound_type in self.map_sound_files:
            if 'files' in self.map_sound_files[sound_type]:
                retVal = True if self.map_sound_files[sound_type]['files'] else False
        return retVal

    def create_player_sound(self, player):
        if 'id' in player:
            player_id = int(player['id'])
            path = "{base_path}players/{id}.mp3".format(base_path=self.BASEPATH, id=player_id)
            if not os.path.isfile(path):
                tts = TtsWrapper()
                tts.create_audio(player['name'], path)
        
    def player_sound_exists(self, player_id):
        return 
        
    def handle_trash_talk(self, trigger):
        if trigger in [Trigger.GAME_END, Trigger.GAME_PAUSE]:
            Clock.unschedule(self.trash)

        if trigger in [Trigger.GAME_START, Trigger.GAME_RESUME, Trigger.GOAL]:
            Clock.unschedule(self.trash)
            Clock.schedule_interval(self.trash, random.randint(60, 120))
            
    def trash(self, dt):
        self.play(Trigger.TRASH)
                    
SoundManager = SoundManagerBase()
