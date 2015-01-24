# -*- coding: utf-8 -*-
import kivy
import settings
kivy.require(settings.KIVY_VERSION_REQUIRE)
from kivy.config import Config
Config.set('graphics', 'width', settings.KIVY_GRAPHICS_WIDTH)
Config.set('graphics', 'height', settings.KIVY_GRAPHICS_HEIGHT)
Config.set('kivy', 'log_level', settings.KIVY_LOG_LEVEL)

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.factory import Factory
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, NoTransition
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ObjectProperty, BooleanProperty, ListProperty, StringProperty
from kivy.animation import Animation
from kivy.logger import Logger
from kivy.clock import Clock, mainthread
from kivy.core.audio import SoundLoader
from functools import partial
from random import randint
import threading
import time

from hardwarelistener import HardwareListener
from soundmanager import SoundManager
from onpropertyanimationmixin import OnPropertyAnimationMixin
from persistentdict import PersistentDict
from servercomm import ServerComm

# GLOBALS
gPlayers = []
gRfidMap = {}

def getPlayerById(players, id):
    return next((item for item in players if item["id"] == id), None)
    
def getPlayerByName(players, name):
    return next((item for item in players if item["name"] == name), None)


class BackgroundScreenManager(ScreenManager):

    def __init__(self, **kwargs):
        super(BackgroundScreenManager, self).__init__(**kwargs)
        self.transition = FadeTransition(duration=0.2)
        #self.transition = NoTransition()

        # setup hardware listener
        self.hwlistener = HardwareListener()
        Clock.schedule_interval(self.callback, 1/30.0)

        # setup storage
        with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as d:
            global gPlayers
            global gRfidMap
            gPlayers = d.get(settings.STORAGE_PLAYERS, [])
            gRfidMap = d.get(settings.STORAGE_RFIDMAP, {})

        # setup screens
        self.add_widget(MenuScreen(name='menu'))
        self.add_widget(RfidSetupScreen(name='rfid-setup'))
        self.add_widget(SettingsScreen(name='settings'))
        self.add_widget(LoungeScreen(name='lounge'))
        self.add_widget(MatchScreen(name='match'))

        # fancy animation
#        anim = Animation(opacity=1.0, t='out_cubic', d=1.0).start(self)
#        anim.bind(on_complete=self.fade_in_done)
#        anim.start(self)
                
#    def fade_in_done(self, anim, obj):
#        Logger.info('value = %s' % value)
#        anim = Animation(d=2.0)
#        anim += Animation(opacity=0, d=1.0)
#        anim.start(self.btn)

    def callback(self, dt):
        msg = self.hwlistener.read()
        if msg != None:
            if 'trigger' in msg and 'data' in msg:
                self.current_screen.processMessage(msg)
    

class TopBar(BoxLayout):
    has_back = BooleanProperty(True)
    is_back_enabled = BooleanProperty(True)
    has_next = BooleanProperty(False)
    is_next_enabled = BooleanProperty(False)
    rect_x = NumericProperty(0.0)
    rect_y = NumericProperty(0.0)
    rect_w = NumericProperty(0.0)
    rect_h = NumericProperty(0.0)


class BaseScreen(Screen, OnPropertyAnimationMixin):

    def __init__(self, **kwargs):
        super(BaseScreen, self).__init__(**kwargs)

    def processMessage(self, msg):
        self.denied()
        
    # 'Back' pressed
    def on_back(self):
        self.manager.current = 'menu'

    # 'Next' pressed
    def on_next(self):
        pass
        
    def denied(self):
        SoundManager.play('chime_down')

        
class MenuScreen(BaseScreen, OnPropertyAnimationMixin):

    fadeopacity = NumericProperty(1.0)
    
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        # initial fade in
        self.fadeopacity = 0.0
        
    def shutdown(self):
        # final fade out
        self.fadeopacity = 1.0
        Clock.schedule_once(App.get_running_app().stop, 2.0)


class RfidSetupScreen(BaseScreen):

    numPlayers = NumericProperty(0)

    def __init__(self, **kwargs):
        super(RfidSetupScreen, self).__init__(**kwargs)
        self.ids.topbar.title = 'RFID Setup'

    def on_enter(self):
        self.__updateNumPlayers()

    def updatePlayersList(self):
        WaitingOverlay(self, self.__fetchPlayersListThread, "Daten werden geladen")

    def __updateNumPlayers(self):
        self.numPlayers = gPlayers.__len__()

    def __fetchPlayersListThread(self):
        # fetch players list from remote server
        sc = ServerComm()
        global gPlayers
        players = sc.fetchPlayers()
        if players.__len__() > 0:
            gPlayers = players
            # store players in file
            with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as d:
                d[settings.STORAGE_PLAYERS] = gPlayers
        self.__updateNumPlayers()
        # generate missing player names
        for p in players:
            SoundManager.createPlayerSound(p)

    def __storeRfidMap(self):
        with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as d:
            d[settings.STORAGE_RFIDMAP] = gRfidMap
        
    
class SettingsScreen(BaseScreen):

    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.ids.topbar.title = 'Einstellungen'
        

class WaitingOverlay(Widget, OnPropertyAnimationMixin):

    opacity = NumericProperty(0.0)
    text = StringProperty("")
    angle = NumericProperty(0.0)
    dotsCount = NumericProperty(0)
    
    def __init__(self, caller, callback, text, **kwargs):
        super(WaitingOverlay, self).__init__(**kwargs)
        self.caller = caller
        self.callback = callback
        self.caller.add_widget(self)
        self.text = text
        self.opacity = 1.0
        self.dotsCount = 0
        Clock.schedule_once(self.__startThread, self.duration)
        Clock.schedule_interval(self.__rotateIcon, 0.03)
        Clock.schedule_interval(self.__cycleDots, 0.3)

    def __startThread(self, dt):
        self.thread = threading.Thread(target=self.callback)
        self.thread.start()
        Clock.schedule_once(self.__checkThread, 0)

    def __checkThread(self, dt):
        if self.thread.is_alive():
            # still working...
            Clock.schedule_once(self.__checkThread, 0.25)
        else:
            # finished!
            self.opacity = 0.0
            Clock.schedule_once(lambda dt: Clock.unschedule(self.__rotateIcon), self.duration)
            Clock.schedule_once(lambda dt: Clock.unschedule(self.__cycleDots), self.duration)
            Clock.schedule_once(lambda dt: self.caller.remove_widget(self), self.duration)

    @mainthread
    def __rotateIcon(self, dt):
        self.angle -= 10
 
    @mainthread
    def __cycleDots(self, dt):
        self.dotsCount = (self.dotsCount + 1 ) % 4
 
class HighlightOverlay(object):
    
    def __init__(self, origObj, parent, **kwargs):
        self.origObj = origObj
        self.parent = parent
        self.kwargs = kwargs

    def animate(self, **animProps):
        clsSpec = {'cls': self.origObj.__class__}
        Factory.register('HighLightObj', **clsSpec)
        hlObj = Factory.HighLightObj(text=self.origObj.text, pos=(self.origObj.center_x - self.parent.center_x, self.origObj.center_y - self.parent.center_y), size=self.origObj.size, font_size=self.origObj.font_size, **self.kwargs)
        self.parent.add_widget(hlObj)
        if 'd' not in animProps:
            animProps['d'] = 1.0
        if 't' not in animProps:
            animProps['t'] = 'out_cubic'
        Animation(**animProps).start(hlObj)
        Clock.schedule_once(lambda dt: self.parent.remove_widget(hlObj), animProps['d'])
        Factory.unregister('HighLightObj')
        

class LoungeScreen(BaseScreen):

    currentPlayerId = NumericProperty(0)
    players = ListProperty([{}] * 4)

    def __init__(self, **kwargs):
        super(LoungeScreen, self).__init__(**kwargs)
        self.ids.topbar.title = 'Aufstellung'
        self.ids.topbar.has_next = True
        self.__reset()
        
    def on_enter(self):
        self.__reset()

    def on_next(self):
        self.manager.current = 'match'

    def __reset(self):
        self.players = [{}] * 4
        self.currentPlayerId = 0
#        for p in self.players:
#            p.availplayers = [str(i) for i in range(100)]

    def on_players(self, instance, value):
        countPlayers = 0
        for p in self.players:
            countPlayers = countPlayers + (1 if p else 0)
        self.ids.topbar.is_next_enabled = (countPlayers == 4)

    def click_player_selection(self, id):
        # first click on player block: simply activate
        if id != self.currentPlayerId:
            self.currentPlayerId = id
            # highlight icon
            obj = self.ids['p' + str(id)].ids.icon
            HighlightOverlay(origObj=obj, parent=self, active=True).animate(font_size=160, color=(1, 1, 1, 0))
        # second click on player block
        else:
            Logger.info('TODO: make dropdown work!')
            # TEST
            obj = self.ids['p' + str((id + 2 ) % 4)]
            self.dd = DropDown()
            for i in range(20):
                btn = Button(text=str(i), size_hint_y=None, height=44)
                btn.bind(on_release=lambda btn: dd.select(btn.text))
                self.dd.add_widget(btn)
            #dd.bind(on_select=lambda instance, x: setattr(mainbutton, 'text', x))
            self.dd.bind(on_select=lambda instance, x: Logger.info(x))
            self.dd.open(obj)
        
    def __handleRfid(self, rfid):
        Logger.info('ScoreTracker: RFID: %s' % rfid)
        # RFID --> player ID
        id = gRfidMap.get(rfid, None)
        Logger.info('ScoreTracker: ID: %s' % id)
        # player ID --> player dict
        player = getPlayerById(gPlayers, id)
        Logger.info('ScoreTracker: Player: %s' % player)
        # player does not exist
        if player == None:
            self.denied()
        # player does exist
        else:
            # player has already been set before
            if player in self.players:
                # remove player's position
                self.players = [{} if p == player else p for p in self.players]
            # set, highlight and say player name
            self.players[self.currentPlayerId] = player
            obj = self.ids['p' + str(self.currentPlayerId)].ids.playerName
            HighlightOverlay(origObj=obj, parent=self, active=True, bold=True).animate(font_size=80, color=(1, 1, 1, 0))
            SoundManager.play('chime_up')
            SoundManager.playName(player, 0.4)
            # advance to next player block
            self.currentPlayerId = (self.currentPlayerId + 1) % 4

    def processMessage(self, msg):
        if msg['trigger'] == 'rfid':
            self.__handleRfid(msg['data'])
        else:
            self.denied()


class MatchScreen(BaseScreen):

    score_home = NumericProperty(0)
    score_away = NumericProperty(0)
    scoreboard = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(MatchScreen, self).__init__(**kwargs)
        self.ids.topbar.title = 'Spiel'
        self.__reset()

    def __reset(self):
        self.score_home = 0
        self.score_away = 0
#        self.playersSpinOpt = SpinnerOption

    def __setTitle(self, text):
        self.ids.topbar.title = text
        
    def __handleGoal(self, team):
        self.__setTitle("Goal for %s team" % team)
        if team == 'home':
            self.score_home += 1
            obj = self.ids.labelHome
        elif team == 'away':
            self.score_away += 1
            obj = self.ids.labelAway
        HighlightOverlay(origObj=obj, parent=self).animate(font_size=500, color=(1, 1, 1, 0))
        i = randint(1,7)
        SoundManager.play('tor%d' % i)

    def processMessage(self, msg):
        if msg['trigger'] == 'goal':
            self.__handleGoal(msg['data'])
        else:
            self.denied()


class ScoreTrackerApp(App):

    def build(self):
        # register fonts
        for font in settings.KIVY_FONTS:  
            LabelBase.register(**font)
        
        self.bsm = BackgroundScreenManager()
        return self.bsm

    def on_stop(self):
        pass

    
if __name__ == '__main__':
    ScoreTrackerApp().run()
    
