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
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, NoTransition
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ObjectProperty, BooleanProperty, ListProperty, StringProperty, DictProperty
from kivy.animation import Animation
from kivy.logger import Logger
from kivy.clock import Clock, mainthread
from kivy.core.audio import SoundLoader
from functools import partial
from random import randint
import threading
import time
import os

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
    hasBack = BooleanProperty(True)
    isBackEnabled = BooleanProperty(True)
    hasNext = BooleanProperty(False)
    isNextEnabled = BooleanProperty(False)
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
        SoundManager.play('chime_down2')

    def setTitle(self, text):
        self.ids.topbar.title = text

    def setCustomText(self, text):
        self.ids.topbar.customtext = text

        
class MenuScreen(BaseScreen, OnPropertyAnimationMixin):

    fadeopacity = NumericProperty(1.0)
    
    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        # initial fade in
        self.fadeopacity = 0.0
        
    def shutdown(self):
        # final fade out
        self.fadeopacity = 1.0
        Clock.schedule_once(self.shutdown_delayed, 2.0)
        
    def shutdown_delayed(self, dt):
        #App.get_running_app().stop()
        os.system("sudo shutdown -h 0")


class PlayerButton(Button):
    data = DictProperty({})
    
    def __init__(self, data, **kwargs):
        self.data = data
        super(PlayerButton, self).__init__(**kwargs)
        
        
class RfidSetupScreen(BaseScreen):

    numPlayers = NumericProperty()
    currentRfid = StringProperty()
    currentPlayer = DictProperty()
    dropdownPlayer = ObjectProperty()
    teaching = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super(RfidSetupScreen, self).__init__(**kwargs)
        self.setTitle('RFID Setup')

    def __setupPlayerDropdown(self):
        self.dropdownPlayer = DropDown()
        self.dropdownPlayer.bind(on_select=self.onPlayerSelect)
        
        players = sorted(gPlayers, key=lambda player: player['name'])
        for p in players:
            btn = PlayerButton(data = p)
            btn.bind(on_release=lambda btn: self.dropdownPlayer.select(btn.data))
            self.dropdownPlayer.add_widget(btn)

    # player was selected from dropdown list
    def onPlayerSelect(self, instance, data):
        self.currentPlayer = data

    # current player object changed
    def on_currentPlayer(self, instance, value):
        self.ids.btnPlayer.iconText = self.currentPlayer.get('name', u'---')
        SoundManager.playName(self.currentPlayer)
        # enable "accept" button if current player is set and was not stored before
        self.ids.btnAccept.disabled = not (self.currentPlayer.has_key('id') and self.currentPlayer.get('id') != gRfidMap.get(self.currentRfid))

    # current rfid object changed
    def on_currentRfid(self, instance, value):
        # enable "remove" button if rfid mapping exists
        self.ids.btnClear.disabled = not gRfidMap.has_key(self.currentRfid)
        # disable player selection box if no RFID is set
        self.ids.btnPlayer.disabled = not self.currentRfid
        self.teaching = True if self.currentRfid else False
        
    def on_enter(self):
        self.__updateNumPlayers()
        Clock.schedule_interval(self.__highlightRfid, 2.0)
        self.__setupPlayerDropdown()

    def on_leave(self):
        Clock.unschedule(self.__highlightRfid)
        self.__reset()
        
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
        for p in gPlayers:
            SoundManager.createPlayerSound(p)
        # update dropdown list
        self.__setupPlayerDropdown()

    def __storeRfidMap(self):
        with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as d:
            d[settings.STORAGE_RFIDMAP] = gRfidMap
    
    def __highlightRfid(self, dt):
        obj = self.ids.iconRfid
        if not self.teaching:
            HighlightOverlay(origObj=obj, parent=self, duration=2.0).animate(font_size=180, color=(1, 1, 1, 0))

    def processMessage(self, msg):
        if msg['trigger'] == 'rfid':
            self.__handleRfid(msg['data'])
        else:
            self.denied()

    def __handleRfid(self, rfid):
        self.currentRfid = rfid
        SoundManager.play('chime_up3')
        # RFID --> player ID
        id = gRfidMap.get(rfid, None)
        # player ID --> player dict
        player = getPlayerById(gPlayers, id)
        if player:
            time.sleep(0.4)
            self.currentPlayer = player
        else:
            self.currentPlayer = {}

    def confirmRemove(self):
        # ask for confirmation if RFID map entry deletion is requested
        view = ModalView(size_hint=(None, None), size=(600, 400), auto_dismiss=False)
        content = Factory.STModalView(title='RFID-Eintrag löschen', text='Soll der RFID-Eintrag wirklich gelöscht werden?', callback=self.removeEntry)
        view.add_widget(content)
        view.open()

    def addEntry(self):
        global gRfidMap
        gRfidMap[self.currentRfid] = self.currentPlayer.get('id')
        self.__storeRfidMap()
        self.__reset()
        
    def removeEntry(self):
        global gRfidMap
        gRfidMap.pop(self.currentRfid)
        self.__storeRfidMap()
        self.__reset()
     
    def __reset(self):
        self.currentPlayer = {}
        self.currentRfid = ''
        self.teaching = False
        
    
class SettingsScreen(BaseScreen):

    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.setTitle('Einstellungen')
        

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
        self.setTitle('Aufstellung')
        self.ids.topbar.hasNext = True
        self.__reset()
        
    def on_enter(self):
        pass

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
        self.ids.topbar.isNextEnabled = (countPlayers == 4)

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
        # RFID --> player ID
        id = gRfidMap.get(rfid, None)
        # player ID --> player dict
        player = getPlayerById(gPlayers, id)
        Logger.info('ScoreTracker: RFID: {0} - ID: {1} - Player: {2}'.format(rfid, id, player))
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
            SoundManager.play('chime_up3')
            SoundManager.playName(player, 0.4)
            # advance to next player block
            self.currentPlayerId = (self.currentPlayerId + 1) % 4

    def processMessage(self, msg):
        if msg['trigger'] == 'rfid':
            self.__handleRfid(msg['data'])
        else:
            self.denied()

class STModalView(BoxLayout):
    title = StringProperty("")
    text = StringProperty("")
    
    def __init__(self, title, text, callback, **kwargs):
        super(STModalView, self).__init__(**kwargs)
        self.title = title
        self.text = text
        self.callback = callback
        
    def on_yes(self):
        self.parent.dismiss()
        self.callback()
        
    def on_no(self):
        self.parent.dismiss()
        

class MatchScreen(BaseScreen):

    score = ListProperty([0, 0])
    
    MAX_GOALS = 6
    MIN_SCORE_MOVE_PX = 100
    
    def __init__(self, **kwargs):
        super(MatchScreen, self).__init__(**kwargs)
        self.scoreObjs = [self.ids.labelHome, self.ids.labelAway]
        self.setTitle('Spiel')

    def on_enter(self):
        self.__reset()
        self.running = True
        self.startTime = time.time()
        Clock.schedule_interval(self.__updateMatchTimer, 0.5)
        SoundManager.play('whistle_medium')

    def on_leave(self):
        self.__reset()
        
    def on_back(self):
        if self.running:
            # game still running, ask for user confirmation
            view = ModalView(size_hint=(None, None), size=(600, 400), auto_dismiss=False)
            content = Factory.STModalView(title = 'Spiel abbrechen', text='Das Spiel ist noch nicht beendet.\nWirklich abbrechen?', callback=self.cancelMatch)
            view.add_widget(content)
            view.open()
        else:
            # game not running anymore
            if not self.submitted:
                view = ModalView(size_hint=(None, None), size=(600, 400), auto_dismiss=False)
                content = Factory.STModalView(title = 'Spiel abbrechen', text='Das Ergebnis wurde noch nicht hochgeladen.\nWirklich abbrechen?', callback=self.cancelMatch)
                view.add_widget(content)
                view.open()
            else:
                self.manager.current = 'lounge'

    def on_score(self, instance, value):
        if value[0] >= self.MAX_GOALS or value[1] >= self.MAX_GOALS:
            self.endGame()

    def endGame(self):
        self.running = False
        SoundManager.play('whistle_medium')
            
    def __reset(self):
        self.score = [0, 0]
        self.setCustomText('00:00')
        self.ids.topbar.customlabel.opacity = 1
        self.submitted = False
        self.scoreTouch = None
        Clock.unschedule(self.__updateMatchTimer)

    def __handleGoal(self, team):
        if team == '1':
            self.score[0] += 1
            obj = self.ids.labelHome
        else:
            self.score[1] += 1
            obj = self.ids.labelAway

        HighlightOverlay(origObj=obj, parent=self).animate(font_size=500, color=(1, 1, 1, 0))
        i = randint(1,7)
        SoundManager.play('tor%d' % i)

    def processMessage(self, msg):
        if msg['trigger'] == 'goal' and self.running:
            self.__handleGoal(msg['data'])
        else:
            self.denied()

    def handleScoreTouchDown(self, event):
        if self.running:
            for i in range(0, 2):
                obj = self.scoreObjs[i]
                collide = obj.collide_point(event.pos[0], event.pos[1])
                if collide:
                    self.scoreTouch = {'id': i, 'startPos': event.pos[1]}

    def handleScoreTouchMove(self, event):
        if self.scoreTouch and self.running:
            obj = self.scoreObjs[self.scoreTouch['id']]
            ratio = min(1.0, abs(event.pos[1] - self.scoreTouch['startPos']) / self.MIN_SCORE_MOVE_PX)
            color = self.interpolateColor((1, 1, 1, 1), (1, 0.8, 0, 1), ratio)
            obj.color = color
        
    def handleScoreTouchUp(self, event):
        if self.scoreTouch and self.running:
            id = self.scoreTouch['id']
            dist = event.pos[1] - self.scoreTouch['startPos']
            if abs(dist) > self.MIN_SCORE_MOVE_PX:
                scoreDiff = 1 if dist > 0 else -1;
                self.score[id] = max(0, min(self.score[id] + scoreDiff, self.MAX_GOALS))
                HighlightOverlay(origObj=self.scoreObjs[id], parent=self).animate(font_size=500, color=(1, 1, 1, 0))
                SoundManager.play('chime_medium1')
            self.scoreObjs[id].color = (1, 1, 1, 1)
        self.scoreTouch = None

    def interpolateColor(self, colA, colB, ratio):
        listColA = list(colA)
        listColB = list(colB)
        listColRes = []
        for i in range(0, len(listColA)):
            listColRes.append(listColA[i] + (listColB[i] - listColA[i]) * ratio)
        return tuple(listColRes)
            
    def __updateMatchTimer(self, dt):
        if self.running:
            elapsed = int(time.time() - self.startTime)
            self.setCustomText('{:02d}:{:02d}'.format(elapsed / 60, elapsed % 60))
        else:
            self.ids.topbar.customlabel.opacity = 1 - self.ids.topbar.customlabel.opacity
        
    def cancelMatch(self):
        self.manager.current = 'lounge'
        

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
    
