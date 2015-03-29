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
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.screenmanager import Screen
from kivy.uix.screenmanager import FadeTransition
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ObjectProperty, BooleanProperty, ListProperty, StringProperty, DictProperty
from kivy.animation import Animation
from kivy.logger import Logger
from kivy.clock import Clock, mainthread
from random import randint
import threading
import time
import os

from hardwarelistener import HardwareListener
from soundmanager import SoundManager, Trigger
from onpropertyanimationmixin import OnPropertyAnimationMixin
from persistentdict import PersistentDict
from servercomm import ServerComm
import networkinfo

# GLOBALS
g_players = []
g_rfid_map = {}

def get_player_by_id(players, player_id):
    return next((item for item in players if item["id"] == player_id), None)

def get_player_by_name(players, player_name):
    return next((item for item in players if item["name"] == player_name), None)


class BackgroundScreenManager(ScreenManager):

    def __init__(self, **kwargs):
        super(BackgroundScreenManager, self).__init__(**kwargs)
        self.transition = FadeTransition(duration=0.2)

        # setup hardware listener
        self.hwlistener = HardwareListener()
        Clock.schedule_interval(self.callback, 1/30.0)

        # setup storage
        with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as dictionary:
            global g_players
            global g_rfid_map
            g_players = dictionary.get(settings.STORAGE_PLAYERS, [])
            g_rfid_map = dictionary.get(settings.STORAGE_RFIDMAP, {})

        # setup screens
        self.add_widget(MenuScreen(name='menu'))
        self.add_widget(RfidSetupScreen(name='rfid-setup'))
        self.add_widget(SettingsScreen(name='settings'))
        self.add_widget(LoungeScreen(name='lounge'))
        self.add_widget(MatchScreen(name='match'))

        SoundManager.play(Trigger.MENU)

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
                self.current_screen.process_message(msg)


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

    def process_message(self, msg):
        self.denied()

    # 'Back' pressed
    def on_back(self):
        self.manager.current = 'menu'

    # 'Next' pressed
    def on_next(self):
        pass

    def denied(self):
        SoundManager.play(Trigger.DENIED)

    def set_title(self, text):
        self.ids.topbar.title = text

    def set_custom_text(self, text):
        self.ids.topbar.customtext = text


class MenuScreen(BaseScreen, OnPropertyAnimationMixin):

    fadeopacity = NumericProperty(1.0)
    ip_addr = StringProperty()

    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        # initial fade in
        self.fadeopacity = 0.0
        Clock.schedule_once(self.fetch_ip, 0.0)

    def fetch_ip(self, dt):
        interfaces = ['eth0', 'wlan0']
        for interface in interfaces:
            addr = networkinfo.get_ip_address(interface)
            if addr is not None:
                break
        if addr is None:
            self.ip_addr = 'not connected'
        else:
            self.ip_addr = "{} ({})".format(addr, interface)
        Clock.schedule_once(self.fetch_ip, 5.0)
        
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

    num_players = NumericProperty()
    current_rfid = StringProperty()
    current_player = DictProperty()
    dropdown_player = ObjectProperty()
    teaching = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(RfidSetupScreen, self).__init__(**kwargs)
        self.set_title('RFID Setup')

    def __setup_player_dropdown(self):
        self.dropdown_player = DropDown()
        self.dropdown_player.bind(on_select=self.on_player_select)

        players = sorted(g_players, key=lambda player: player['name'])
        for player in players:
            btn = PlayerButton(data=player)
            btn.bind(on_release=lambda btn: self.dropdown_player.select(btn.data))
            self.dropdown_player.add_widget(btn)

    # player was selected from dropdown list
    def on_player_select(self, instance, data):
        self.current_player = data

    # current player object changed
    def on_current_player(self, instance, value):
        self.ids.btnPlayer.iconText = self.current_player.get('name', u'---')
        SoundManager.play(Trigger.PLAYER_SELECTED, self.current_player)
        # enable "accept" button if current player is set and was not stored before
        self.ids.btnAccept.disabled = not (self.current_player.has_key('id') and self.current_player.get('id') != g_rfid_map.get(self.current_rfid))

    # current rfid object changed
    def on_current_rfid(self, instance, value):
        # enable "remove" button if rfid mapping exists
        self.ids.btnClear.disabled = not g_rfid_map.has_key(self.current_rfid)
        # disable player selection box if no RFID is set
        self.ids.btnPlayer.disabled = not self.current_rfid
        self.teaching = True if self.current_rfid else False

    def on_enter(self):
        self.__updatenum_players()
        Clock.schedule_interval(self.__highligh_rfid, 1.5)
        self.__setup_player_dropdown()

    def on_leave(self):
        Clock.unschedule(self.__highligh_rfid)
        self.__reset()

    def update_players_list(self):
        WaitingOverlay(self, self.__fetch_players_list_thread, "Daten werden geladen")

    def __updatenum_players(self):
        self.num_players = g_players.__len__()

    def __fetch_players_list_thread(self):
        # fetch players list from remote server
        server_comm = ServerComm()
        global g_players
        players = server_comm.fetchPlayers()
        if players.__len__() > 0:
            g_players = players
            # store players in file
            with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as dictionary:
                dictionary[settings.STORAGE_PLAYERS] = g_players
        self.__updatenum_players()
        # generate missing player names
        for player in g_players:
            SoundManager.create_player_sound(player)
        # update dropdown list
        self.__setup_player_dropdown()

    def __store_rfid_map(self):
        with PersistentDict(settings.STORAGE_FILE, 'c', format='json') as dictionary:
            dictionary[settings.STORAGE_RFIDMAP] = g_rfid_map

    def __highligh_rfid(self, dt):
        obj = self.ids.iconRfid
        if not self.teaching:
            HighlightOverlay(orig_obj=obj, parent=self, duration=2.0).animate(font_size=180, color=(1, 1, 1, 0))

    def process_message(self, msg):
        if msg['trigger'] == 'rfid':
            self.__handle_rfid(msg['data'])
        else:
            self.denied()

    def __handle_rfid(self, rfid):
        self.current_rfid = rfid
        SoundManager.play(Trigger.RFID)
        # RFID --> player ID
        player_id = g_rfid_map.get(rfid, None)
        # player ID --> player dict
        player = get_player_by_id(g_players, player_id)
        if player:
            time.sleep(0.5)
            self.current_player = player
        else:
            self.current_player = {}

    def confirm_remove(self):
        # ask for confirmation if RFID map entry deletion is requested
        view = ModalView(size_hint=(None, None), size=(600, 400), auto_dismiss=False)
        content = Factory.STModalView(title='RFID-Eintrag löschen', text='Soll der RFID-Eintrag wirklich gelöscht werden?', callback=self.remove_entry)
        view.add_widget(content)
        view.open()

    def add_entry(self):
        global g_rfid_map
        g_rfid_map[self.current_rfid] = self.current_player.get('id')
        self.__store_rfid_map()
        self.__reset()

    def remove_entry(self):
        global g_rfid_map
        g_rfid_map.pop(self.current_rfid)
        self.__store_rfid_map()
        self.__reset()

    def __reset(self):
        self.current_player = {}
        self.current_rfid = ''
        self.teaching = False


class SettingsScreen(BaseScreen):

    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.set_title('Einstellungen')


class WaitingOverlay(Widget, OnPropertyAnimationMixin):

    opacity = NumericProperty(0.0)
    text = StringProperty("")
    angle = NumericProperty(0.0)
    dots_count = NumericProperty(0)

    def __init__(self, caller, callback, text, **kwargs):
        super(WaitingOverlay, self).__init__(**kwargs)
        self.caller = caller
        self.callback = callback
        self.caller.add_widget(self)
        self.text = text
        self.opacity = 1.0
        self.dots_count = 0
        self.thread = None
        Clock.schedule_once(self.__start_thread, self.duration)
        Clock.schedule_interval(self.__rotate_icon, 0.03)
        Clock.schedule_interval(self.__cycle_dots, 0.3)

    def __start_thread(self, dt):
        self.thread = threading.Thread(target=self.callback)
        self.thread.start()
        Clock.schedule_once(self.__check_thread, 0)

    def __check_thread(self, dt):
        if self.thread.is_alive():
            # still working...
            Clock.schedule_once(self.__check_thread, 0.25)
        else:
            # finished!
            self.opacity = 0.0
            Clock.schedule_once(lambda dt: Clock.unschedule(self.__rotate_icon), self.duration)
            Clock.schedule_once(lambda dt: Clock.unschedule(self.__cycle_dots), self.duration)
            Clock.schedule_once(lambda dt: self.caller.remove_widget(self), self.duration)

    @mainthread
    def __rotate_icon(self, dt):
        self.angle -= 10

    @mainthread
    def __cycle_dots(self, dt):
        self.dots_count = (self.dots_count + 1 ) % 4

class HighlightOverlay(object):

    def __init__(self, orig_obj, parent, **kwargs):
        self.orig_obj = orig_obj
        self.parent = parent
        self.kwargs = kwargs

    def animate(self, **animProps):
        class_spec = {'cls': self.orig_obj.__class__}
        Factory.register('HighLightObj', **class_spec)
        highlight_obj = Factory.HighLightObj(text=self.orig_obj.text, pos=(self.orig_obj.center_x - self.parent.center_x, self.orig_obj.center_y - self.parent.center_y), size=self.orig_obj.size, font_size=self.orig_obj.font_size, **self.kwargs)
        self.parent.add_widget(highlight_obj)
        if 'd' not in animProps:
            animProps['d'] = 1.0
        if 't' not in animProps:
            animProps['t'] = 'out_cubic'
        Animation(**animProps).start(highlight_obj)
        Clock.schedule_once(lambda dt: self.parent.remove_widget(highlight_obj), animProps['d'])
        Factory.unregister('HighLightObj')


class LoungeScreen(BaseScreen):

    current_player_slot = NumericProperty(0)
    players = ListProperty([{}] * 4)
    dropdown_player = ObjectProperty()

    def __init__(self, **kwargs):
        super(LoungeScreen, self).__init__(**kwargs)
        self.set_title('Aufstellung')
        self.ids.topbar.hasNext = True
        self.__reset()

    def on_enter(self):
        self.__setup_player_dropdown()

    def on_next(self):
        self.manager.current = 'match'

    def __reset(self):
        self.players = [{}] * 4
        self.current_player_slot = 0

    def __setup_player_dropdown(self):
        self.dropdown_player = DropDown()
        self.dropdown_player.bind(on_select=self.on_player_select)

        players = sorted(g_players, key=lambda player: player['name'])
        for player in players:
            btn = PlayerButton(data=player)
            btn.bind(on_release=lambda btn: self.dropdown_player.select(btn.data))
            self.dropdown_player.add_widget(btn)

    # player was selected from dropdown list
    def on_player_select(self, instance, data):
        self.set_player(data)

    def on_players(self, instance, value):
        count_players = 0
        for player in self.players:
            count_players = count_players + (1 if player else 0)
        self.ids.topbar.isNextEnabled = (count_players == 4)

    def click_player_slot(self, player_slot):
        # first click on player slot: simply activate
        if player_slot != self.current_player_slot:
            self.current_player_slot = player_slot
            # highlight icon
            obj = self.ids['p' + str(player_slot)].ids.icon
            HighlightOverlay(orig_obj=obj, parent=self, active=True).animate(font_size=160, color=(1, 1, 1, 0))
        # second click on player slot
        else:
            obj = self.ids['p' + str(player_slot)]
            self.dropdown_player.open(obj)

    def __handle_rfid(self, rfid):
        # RFID --> player ID
        player_id = g_rfid_map.get(rfid, None)
        # player ID --> player dict
        player = get_player_by_id(g_players, player_id)
        Logger.info('ScoreTracker: RFID: {0} - ID: {1} - Player: {2}'.format(rfid, player_id, player))
        # player does not exist
        if player == None:
            self.denied()
        # player does exist
        else:
            self.set_player(player)

    def set_player(self, player):
        # player has already been set before
        if player in self.players:
            # remove player's position
            self.players = [{} if p == player else p for p in self.players]
        # set, highlight and say player name
        self.players[self.current_player_slot] = player
        obj = self.ids['p' + str(self.current_player_slot)].ids.playerName
        HighlightOverlay(orig_obj=obj, parent=self, active=True, bold=True).animate(font_size=80, color=(1, 1, 1, 0))
        SoundManager.play(Trigger.PLAYER_JOINED, player)
        # advance to next player block
        self.current_player_slot = (self.current_player_slot + 1) % 4

    def process_message(self, msg):
        if msg['trigger'] == 'rfid':
            self.__handle_rfid(msg['data'])
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
        self.score_objects = [self.ids.labelHome, self.ids.labelAway]
        self.set_title('Spiel')
        self.running = False
        self.submitted = False
        self.score_touch = None
        self.start_time = 0.0

    def on_enter(self):
        self.__reset()
        self.running = True
        self.start_time = time.time()
        Clock.schedule_interval(self.__update_match_timer, 0.5)
        SoundManager.play(Trigger.GAME_START)

    def on_leave(self):
        self.__reset()

    def on_back(self):
        if self.running:
            # game still running, ask for user confirmation
            view = ModalView(size_hint=(None, None), size=(600, 400), auto_dismiss=False)
            content = Factory.STModalView(title='Spiel abbrechen', text='Das Spiel ist noch nicht beendet.\nWirklich abbrechen?', callback=self.cancel_match)
            view.add_widget(content)
            view.open()
        else:
            # game not running anymore
            if not self.submitted:
                view = ModalView(size_hint=(None, None), size=(600, 400), auto_dismiss=False)
                content = Factory.STModalView(title='Spiel abbrechen', text='Das Ergebnis wurde noch nicht hochgeladen.\nWirklich abbrechen?', callback=self.cancel_match)
                view.add_widget(content)
                view.open()
            else:
                self.manager.current = 'lounge'

    def on_score(self, instance, value):
        if value[0] >= self.MAX_GOALS or value[1] >= self.MAX_GOALS:
            self.running = False
            SoundManager.play(Trigger.GAME_END)
        else:
            self.running = True

    def __reset(self):
        self.score = [0, 0]
        self.set_custom_text('00:00')
        self.ids.topbar.customlabel.opacity = 1
        self.submitted = False
        self.score_touch = None
        Clock.unschedule(self.__update_match_timer)

    def __handle_goal(self, team):
        if team == '1':
            self.score[0] += 1
            obj = self.ids.labelHome
        else:
            self.score[1] += 1
            obj = self.ids.labelAway

        HighlightOverlay(orig_obj=obj, parent=self).animate(font_size=500, color=(1, 1, 1, 0))
        SoundManager.play(Trigger.GOAL)

    def process_message(self, msg):
        if msg['trigger'] == 'goal' and self.running:
            self.__handle_goal(msg['data'])
        else:
            self.denied()

    # manual score editing methods
    def handle_score_touch_down(self, event):
        for i in range(0, 2):
            obj = self.score_objects[i]
            collide = obj.collide_point(event.pos[0], event.pos[1])
            if collide:
                self.score_touch = {'id': i, 'startPos': event.pos[1]}

    def handle_score_touch_move(self, event):
        if self.score_touch:
            obj = self.score_objects[self.score_touch['id']]
            ratio = min(1.0, abs(event.pos[1] - self.score_touch['startPos']) / self.MIN_SCORE_MOVE_PX)
            color = self.interpolate_color((1, 1, 1, 1), (1, 0.8, 0, 1), ratio)
            obj.color = color

    def handle_score_touch_up(self, event):
        if self.score_touch:
            score_id = self.score_touch['id']
            dist = event.pos[1] - self.score_touch['startPos']
            if abs(dist) > self.MIN_SCORE_MOVE_PX:
                score_diff = 1 if dist > 0 else -1;
                self.score[score_id] = max(0, min(self.score[score_id] + score_diff, self.MAX_GOALS))
                HighlightOverlay(orig_obj=self.score_objects[score_id], parent=self).animate(font_size=500, color=(1, 1, 1, 0))
                SoundManager.play(Trigger.SWIPE)
            self.score_objects[score_id].color = (1, 1, 1, 1)
        self.score_touch = None

    def interpolate_color(self, color_start, color_end, ratio):
        list_color_start = list(color_start)
        list_color_end = list(color_end)
        list_color_result = []
        for i in range(0, len(list_color_start)):
            list_color_result.append(list_color_start[i] + (list_color_end[i] - list_color_start[i]) * ratio)
        return tuple(list_color_result)

    def __update_match_timer(self, dt):
        if self.running:
            elapsed = int(time.time() - self.start_time)
            self.ids.topbar.customlabel.opacity = 1
            self.set_custom_text('{:02d}:{:02d}'.format(elapsed / 60, elapsed % 60))
        else:
            self.ids.topbar.customlabel.opacity = 1 - self.ids.topbar.customlabel.opacity

    def cancel_match(self):
        self.manager.current = 'lounge'


class ScoreTrackerApp(App):

    def build(self):
        # register fonts
        for font in settings.KIVY_FONTS:
            LabelBase.register(**font)

        return BackgroundScreenManager()

    def on_stop(self):
        pass


if __name__ == '__main__':
    ScoreTrackerApp().run()
