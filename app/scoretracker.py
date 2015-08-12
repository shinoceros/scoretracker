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
from kivy.uix.behaviors import ButtonBehavior
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
import threading
import time
import os
import math
import alsaaudio

from hardwarelistener import HardwareListener
from soundmanager import SoundManager, Trigger
from onpropertyanimationmixin import OnPropertyAnimationMixin
from servercom import ServerCom
from networkinfo import NetworkInfo
from gamedata import GameData
from playerdata import PlayerData
import icons

class BackgroundScreenManager(ScreenManager):

    def __init__(self, **kwargs):
        super(BackgroundScreenManager, self).__init__(**kwargs)
        self.transition = FadeTransition(duration=0.2)

        # setup hardware listener
        self.hwlistener = HardwareListener()
        self.hwlistener.register(self.receive_msg)

        # setup network status
        NetworkInfo.start_polling()

        # setup screens
        self.add_widget(MenuScreen(name='menu'))
        self.add_widget(RfidSetupScreen(name='rfid-setup'))
        self.add_widget(SettingsScreen(name='settings'))
        self.add_widget(LoungeScreen(name='lounge'))
        self.add_widget(MatchScreen(name='match'))

        SoundManager.play(Trigger.INTRO)

    def receive_msg(self, msg):
        if 'trigger' in msg and 'data' in msg:
            self.current_screen.process_message(msg)

    def stop(self):
        self.hwlistener.stop()


class TopBar(BoxLayout):
    hasBack = BooleanProperty(True)
    isBackEnabled = BooleanProperty(True)
    hasNext = BooleanProperty(False)
    isNextEnabled = BooleanProperty(False)
    rect_x = NumericProperty(0.0)
    rect_y = NumericProperty(0.0)
    rect_w = NumericProperty(0.0)
    rect_h = NumericProperty(0.0)
    network_info = DictProperty({'connected': False})

    def network_info_pressed(self):
        NetworkInfo.say_connection_status()

class ButtonSound(ButtonBehavior):
    pass

class SoundButton(Button, ButtonSound):
    pass

class IconButton(SoundButton):
    icon = StringProperty('')
    icon_angle = NumericProperty(0.0)
    blocking = BooleanProperty(False)
    reset_icon_when_done = True
    last_icon = ''

    def on_blocking(self, instance, block):
        if block:
            self.disabled = True
            self.last_icon = self.icon
            self.icon = icons.refresh
            Clock.schedule_interval(self.__rotate, 0.03)
        else:
            Clock.unschedule(self.__rotate)
            self.icon_angle = 0
            if self.reset_icon_when_done:
                self.icon = self.last_icon
            self.disabled = False

    def __rotate(self, dt):
        self.icon_angle -= 5


class BaseScreen(Screen, OnPropertyAnimationMixin):

    def __init__(self, **kwargs):
        super(BaseScreen, self).__init__(**kwargs)
        NetworkInfo.register(self.__update_network_info)

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

    def __update_network_info(self, nwinfo):
        if 'topbar' in self.ids:
            self.ids.topbar.network_info = nwinfo

    def set_title(self, text):
        self.ids.topbar.title = text

    def set_custom_text(self, text):
        self.ids.topbar.customtext = text

class MenuScreen(BaseScreen, OnPropertyAnimationMixin):

    fadeopacity = NumericProperty(1.0)
    network_str = StringProperty()

    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        # initial fade in
        self.fadeopacity = 0.0
        NetworkInfo.register(self.__update_network_info)

    def on_enter(self):
        pass

    def on_leave(self):
        pass

    def __update_network_info(self, nwinfo):
        #state = nwinfo.get('state', 'DISCONNECTED')
        connected = nwinfo.get('connected', False)

        if connected:
            ip_address = nwinfo.get('ip_address', '')
            hostname = nwinfo.get('hostname', '')
            self.network_str = 'connected: {} ({})'.format(ip_address, hostname)
        else:
            self.network_str = 'not connected'

        
#        if state == 'SCANNING':
#            self.network_str = 'scanning for networks...'
#        elif state == 'ASSOCIATED' or (state == 'COMPLETED' and ip_address == ''):
#            self.network_str = 'connected, fetching IP...'
#        elif state == 'COMPLETED' and ip_address != '':
#            self.network_str = 'connected: {} ({})'.format(ip_address, hostname)
#        else:
#            self.network_str = 'not connected'

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
        self.__setup_player_dropdown()
        self.thread = None

    def __setup_player_dropdown(self):
        self.dropdown_player = DropDown()
        self.dropdown_player.bind(on_select=self.on_player_select)

        players = sorted(PlayerData.get_players(), key=lambda player: player['name'])
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
        self.ids.btnAccept.disabled = not (self.current_player.has_key('id') and self.current_player.get('id') != PlayerData.get_rfid_map().get(self.current_rfid))

    # current rfid object changed
    def on_current_rfid(self, instance, value):
        # enable "remove" button if rfid mapping exists
        self.ids.btnClear.disabled = not PlayerData.get_rfid_map().has_key(self.current_rfid)
        # disable player selection box if no RFID is set
        self.ids.btnPlayer.disabled = not self.current_rfid
        self.teaching = True if self.current_rfid else False

    def on_enter(self):
        self.__updatenum_players()
        Clock.schedule_interval(self.__highlight_rfid, 1.5)

    def on_leave(self):
        Clock.unschedule(self.__highlight_rfid)
        self.__reset()

    def update_players_list(self):
        Clock.unschedule(self.__highlight_rfid)
        self.ids.btnUpdate.blocking = True
        self.thread = threading.Thread(target=self.__fetch_players_list_thread)
        self.thread.start()
        Clock.schedule_once(self.__check_thread, 0)

    def __check_thread(self, dt):
        if self.thread.is_alive():
            # still working...
            Clock.schedule_once(self.__check_thread, 0.25)
        else:
            # finished!
            self.ids.btnUpdate.blocking = False
            # update dropdown list
            self.__setup_player_dropdown()
            Clock.schedule_interval(self.__highlight_rfid, 1.5)

    def __updatenum_players(self):
        self.num_players = PlayerData.get_players().__len__()

    def __fetch_players_list_thread(self):
        # fetch players list from remote server
        players = ServerCom.fetch_players()
        if players.__len__() > 0:
            PlayerData.setPlayers(players)
        self.__updatenum_players()
        # generate missing player names
        for player in players:
            SoundManager.create_player_sound(player)

    def __highlight_rfid(self, dt):
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
        player_id = PlayerData.get_player_by_rfid(rfid)
        # player ID --> player dict
        player = PlayerData.get_player_by_id(player_id)
        if player:
            time.sleep(0.5)
            self.current_player = player
        else:
            self.current_player = {}

    def confirm_remove(self):
        # ask for confirmation if RFID map entry deletion is requested
        view = ModalView(size_hint=(None, None), size=(600, 400), auto_dismiss=False)
        content = Factory.STModalView(title='RFID-Eintrag l�schen', text='Soll der RFID-Eintrag wirklich gel�scht werden?', cb_yes=self.remove_entry)
        view.add_widget(content)
        view.open()

    def add_entry(self):
        PlayerData.add_rfid(self.current_rfid, self.current_player.get('id'))
        self.__reset()

    def remove_entry(self):
        PlayerData.remove_rfid(self.current_rfid)
        self.__reset()

    def __reset(self):
        self.current_player = {}
        self.current_rfid = ''
        self.teaching = False


class SettingsScreen(BaseScreen):
    volume = NumericProperty(0)

    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)
        self.set_title('Einstellungen')
        self.mixer = alsaaudio.Mixer(u'PCM')
        self.volume = self.mixer.getvolume()[0]
        self.ids.volslider.bind(value=self.on_volume)

    def on_volume(self, instance, value):
        self.mixer.setvolume(int(value))

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
        self.dots_count = (self.dots_count + 1) % 4

class HighlightOverlay(object):

    def __init__(self, orig_obj, parent, **kwargs):
        self.orig_obj = orig_obj
        self.parent = parent
        self.kwargs = kwargs

    def animate(self, **animProps):
        class_spec = {'cls': self.orig_obj.__class__}
        Factory.register('HighLightObj', **class_spec)
        highlight_obj = Factory.HighLightObj(text=self.orig_obj.text, padding=self.orig_obj.padding, pos=(self.orig_obj.center_x - self.parent.center_x, self.orig_obj.center_y - self.parent.center_y), size=self.orig_obj.size, font_size=self.orig_obj.font_size, **self.kwargs)
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
    drag_start_id = NumericProperty(-1)
    drag_stop_id = NumericProperty(-1)
    dragging = BooleanProperty()

    def __init__(self, **kwargs):
        super(LoungeScreen, self).__init__(**kwargs)
        self.set_title('Aufstellung')
        self.ids.topbar.hasNext = True
        self.is_dropdown_open = False
        self.slot_touch = None

        self.__reset()

    def on_enter(self):
        Clock.schedule_once(lambda dt: self.__setup_player_dropdown(), 0.2)
        self.current_player_slot = 0

    def on_leave(self):
        self.close_dropdown()

    def on_next(self):
        self.manager.current = 'match'

    def __reset(self):
        self.players = [{}] * 4
        self.current_player_slot = 0

    def __setup_player_dropdown(self):
        # only create if not existing
        if not self.dropdown_player:
            self.dropdown_player = DropDown(auto_dismiss=False)
            self.dropdown_player.bind(on_select=self.on_player_select)
            self.dropdown_player.bind(on_dismiss=self.on_dropdown_dismiss)

            players = sorted(PlayerData.get_players(), key=lambda player: player['name'])
            for player in players:
                btn = PlayerButton(data=player)
                btn.bind(on_release=lambda btn: self.dropdown_player.select(btn.data))
                self.dropdown_player.add_widget(btn)

    def on_dropdown_dismiss(self, instance):
        self.is_dropdown_open = False

    def open_dropdown(self, slot_id):
        if not self.is_dropdown_open:
            obj = self.ids['p' + str(slot_id)]
            self.dropdown_player.open(obj)
            self.is_dropdown_open = True

    def close_dropdown(self):
        if self.is_dropdown_open:
            self.dropdown_player.dismiss()

    def on_player_select(self, instance, data):
        # player was selected from dropdown list
        self.dropdown_player.dismiss()
        self.set_player(data)

    def on_players(self, instance, value):
        GameData.set_players(value)
        count_players = 0
        for player in self.players:
            count_players = count_players + (1 if player else 0)
        self.ids.topbar.isNextEnabled = (count_players == 4)

    def click_player_slot(self, player_slot):
        pass

    def __handle_rfid(self, rfid):
        # RFID --> player ID
        player_id = PlayerData.get_player_by_rfid(rfid)
        # player ID --> player dict
        player = PlayerData.get_player_by_id(player_id)
        Logger.info('ScoreTracker: RFID: {0} - ID: {1} - Player: {2}'.format(rfid, player_id, player))
        # player does not exist
        if player == None:
            self.denied()
        # player does exist
        else:
            if self.dropdown_player:
                self.dropdown_player.dismiss()
            self.set_player(player)

    def highlight_player(self, slot_id):
        obj = self.ids['p' + str(slot_id)].ids.playerName
        HighlightOverlay(orig_obj=obj, parent=self, active=True, bold=True).animate(font_size=80, color=(1, 1, 1, 0))

    def switch_players(self, slot_id_1, slot_id_2):
        self.players[slot_id_1], self.players[slot_id_2] = self.players[slot_id_2], self.players[slot_id_1]
        for player_id in [slot_id_1, slot_id_2]:
            self.highlight_player(player_id)
        SoundManager.play(Trigger.PLAYERS_SWITCHED)

    def get_slot_collision(self, event):
        slot_id = None
        colliding = False
        for i in range(0, 4):
            obj = self.ids['p' + str(i)]
            collide = obj.collide_point(event.pos[0], event.pos[1])
            if collide:
                slot_id = i
        return slot_id
        
    def handle_slot_touch_down(self, event):
        # check if slot was pressed
        colliding_slot_id = self.get_slot_collision(event)
        if colliding_slot_id is not None:
            self.slot_touch = {'source_id': colliding_slot_id, 'source_pos': event.pos, 'target_id': colliding_slot_id, 'dist': 0.0}
            self.drag_start_id = colliding_slot_id
            self.dragging = False
            #print 'down', self.slot_touch

    def handle_slot_touch_move(self, event):
        # a slot was dragged
        if self.slot_touch:
            dx = abs(self.slot_touch['source_pos'][0] - event.pos[0])
            dy = abs(self.slot_touch['source_pos'][1] - event.pos[1])
            dist = math.sqrt(dx * dx + dy * dy)
            self.slot_touch['dist'] = dist
            self.dragging = (dist > 10.0)
            # check collision
            colliding_slot_id = self.get_slot_collision(event)
            if colliding_slot_id is not None:
                self.slot_touch['target_id'] = colliding_slot_id
                self.drag_stop_id = colliding_slot_id
            else:
                self.slot_touch['target_id'] = None
                self.drag_stop_id = -1

            #print 'move', self.slot_touch

    # a slot was released
    def handle_slot_touch_up(self, event):
        if self.slot_touch:
            #print 'up', self.slot_touch
            # release on same slot
            if self.slot_touch['source_id'] == self.slot_touch['target_id']:
                # started in this slot: toggle dropdown
                if self.slot_touch['source_id'] == self.current_player_slot:
                    if self.is_dropdown_open:
                        self.close_dropdown()
                    else:
                        self.open_dropdown(self.slot_touch['target_id'])
                # activate
                else:
                    self.current_player_slot = self.slot_touch['source_id']
                    self.close_dropdown()
                    # highlight icon
                    obj = self.ids['p' + str(self.current_player_slot)].ids.icon
                    HighlightOverlay(orig_obj=obj, parent=self, active=True).animate(font_size=160, color=(1, 1, 1, 0))
            # dragged to another slot
            else:
                if self.slot_touch['target_id'] is not None:
                    self.switch_players(self.slot_touch['source_id'], self.slot_touch['target_id'])

            self.slot_touch = None
            self.drag_start_id = -1
            self.drag_stop_id = -1

    def set_player(self, player):
        # check if player has already been set before
        try:
            idx_already_set = self.players.index(player)
        except ValueError, e:
            # player is not in any team yet
            self.players[self.current_player_slot] = player
            self.highlight_player(self.current_player_slot)
            SoundManager.play(Trigger.PLAYER_JOINED, player)
        else:
            # only switch position if new player is not already in current slot
            if idx_already_set != self.current_player_slot:
                # switch slots
                self.players[idx_already_set] = self.players[self.current_player_slot]
                self.players[self.current_player_slot] = player
                self.highlight_player(self.current_player_slot)
                # check if target slot was empty
                if self.players[idx_already_set] == {}:
                    # player is moved to empty slot
                    SoundManager.play(Trigger.PLAYER_MOVED)
                else:
                    # player switches position with another player
                    SoundManager.play(Trigger.PLAYERS_SWITCHED)
                    self.highlight_player(idx_already_set)
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

    def __init__(self, title, text, cb_yes=None, cb_no=None, **kwargs):
        super(STModalView, self).__init__(**kwargs)
        self.title = title
        self.text = text
        self.cb_yes = cb_yes
        self.cb_no = cb_no

    def on_yes(self):
        self.parent.dismiss()
        if self.cb_yes:
            self.cb_yes()

    def on_no(self):
        self.parent.dismiss()
        if self.cb_no:
            self.cb_no()


class MatchScreen(BaseScreen):

    score = ListProperty([0, 0])
    state = StringProperty('')
    players = ListProperty([{}] * 4)
    elo = NumericProperty(0.0)
    kickoff_team = NumericProperty(-1)
    kickoff_angle = NumericProperty(0)

    MAX_GOALS = 6
    MIN_SCORE_MOVE_PX = 100

    def __init__(self, **kwargs):
        super(MatchScreen, self).__init__(**kwargs)
        self.score_objects = [self.ids.labelHome, self.ids.labelAway]
        self.set_title('Spiel')
        self.score_touch = None
        self.start_time = 0.0
        self.submit_success = None
        self.thread = None
        self.__reset()

    def __set_submit_icon(self, icon):
        self.ids.btnSubmit.icon = icon
        
    def on_enter(self):
        self.__reset()
        self.state = 'running'
        self.start_time = time.time()
        self.players = GameData.get_players()
        self.__set_submit_icon(icons.cloud_upload)
        Clock.schedule_interval(self.__update_match_timer, 1.0)
        self.handle_kickoff(True)

    def handle_kickoff(self, say_player):
        if not GameData.is_match_finished():
            delay = 1.0
            Clock.schedule_once(self.__animate_kickoff, delay)
            if say_player:
                SoundManager.play(Trigger.GAME_START, self.players[GameData.get_kickoff_team() * 2])

    def __animate_kickoff(self, dt):
        # animate ball
        obj = self.ids['kickoff_ball']
        x_current = obj.pos[0]
        x_target = obj.parent.x + (0.0 if GameData.get_kickoff_team() == 0 else obj.parent.width)
        y_high = obj.parent.y + 1.5 * obj.parent.height
        y_low = obj.parent.y + obj.parent.height / 2.0

        uptime_ratio = 0.3
        duration = 1.5
        duration_up = uptime_ratio * duration
        duration_down = (1.0 - uptime_ratio) * duration
        anim = Animation(x=x_current + uptime_ratio * (x_target - x_current), d=duration_up, t='linear') & Animation(y=y_high, d=duration_up, t='out_quad')
        anim += Animation(x=x_target, d=duration_down, t='out_quad') & Animation(y=y_low, d=duration_down, t='out_bounce')
        anim.start(obj)
        Clock.schedule_once(self.__animate_rotation, 0)
        Clock.schedule_once(lambda dt: Clock.unschedule(self.__animate_rotation), duration)

    def __animate_rotation(self, dt):
        direction = 1.0 if GameData.get_kickoff_team() == 0 else -1.0
        self.kickoff_angle += 15.0 * direction
        Clock.schedule_once(self.__animate_rotation, 0.04)

    def on_leave(self):
        self.__reset()

    def on_back(self):
        # game still running, ask for user confirmation
        if self.state == 'running':
            SoundManager.play(Trigger.GAME_PAUSE)
            view = ModalView(size_hint=(None, None), size=(600, 400), auto_dismiss=False)
            content = Factory.STModalView(title='Spiel abbrechen', text='Das Spiel ist noch nicht beendet.\nWirklich abbrechen?', cb_yes=self.cancel_match, cb_no=self.resume_match)
            view.add_widget(content)
            view.open()
        # game not running anymore
        elif self.state in ['finished', 'submitting', 'submit_failed']:
            view = ModalView(size_hint=(None, None), size=(600, 400), auto_dismiss=False)
            content = Factory.STModalView(title='Spiel abbrechen', text='Das Ergebnis wurde noch nicht hochgeladen.\nWirklich abbrechen?', cb_yes=self.cancel_match)
            view.add_widget(content)
            view.open()
        else:
            self.manager.current = 'lounge'

    def on_score(self, instance, value):
        # update kickoff information
        self.handle_kickoff(False)
        # check max goal during match
        if self.state == 'running':
            if GameData.is_match_finished():
                self.state = 'finished'
                SoundManager.play(Trigger.GAME_END)
        # manual swiping can resume a finished match
        elif self.state == 'finished':
            self.state = 'running'
            SoundManager.play(Trigger.GAME_RESUME)

    def __reset(self):
        self.state = ''
        GameData.reset_match()
        self.score = GameData.get_score()
        self.set_custom_text('00:00')
        self.ids.topbar.customlabel.opacity = 1
        self.ids.btnSubmit.blocking = False
        container = self.ids.kickoff_ball.parent
        self.ids.kickoff_ball.pos = (container.x + container.width / 2.0, container.y + container.height)
        self.score_touch = None
        self.players = [{}] * 4
        self.kickoff_team = -1
        self.elo = 0.0
        Clock.unschedule(self.__update_match_timer)
        Clock.unschedule(self.__animate_kickoff)

    def __handle_goal(self, team):
        if team == '1':
            GameData.add_goal(0)
            obj = self.ids.labelHome
        else:
            GameData.add_goal(1)
            obj = self.ids.labelAway

        self.score = GameData.get_score()
        HighlightOverlay(orig_obj=obj, parent=self).animate(font_size=500, color=(1, 1, 1, 0), d=2.0)
        SoundManager.play(Trigger.GOAL)

    def process_message(self, msg):
        if msg['trigger'] == 'goal' and self.state == 'running':
            self.__handle_goal(msg['data'])
        else:
            self.denied()

    # manual score editing methods
    def handle_score_touch_down(self, event):
        if self.state not in ['running', 'finished']:
            return
        for i in range(0, 2):
            obj = self.score_objects[i]
            collide = obj.collide_point(event.pos[0], event.pos[1])
            if collide:
                self.score_touch = {'id': i, 'startPos': event.pos[1]}

    def handle_score_touch_move(self, event):
        if self.state not in ['running', 'finished']:
            return
        if self.score_touch:
            obj = self.score_objects[self.score_touch['id']]
            ratio = min(1.0, abs(event.pos[1] - self.score_touch['startPos']) / self.MIN_SCORE_MOVE_PX)
            color = self.interpolate_color((1, 1, 1, 1), (1, 0.8, 0, 1), ratio)
            obj.color = color

    def handle_score_touch_up(self, event):
        if self.state not in ['running', 'finished']:
            return
        if self.score_touch:
            score_id = self.score_touch['id']
            dist = event.pos[1] - self.score_touch['startPos']
            if abs(dist) > self.MIN_SCORE_MOVE_PX:
                goal_up = dist > 0
                if goal_up:
                    swipe_allowed = GameData.add_goal(score_id)
                else:
                    swipe_allowed = GameData.revoke_goal(score_id)
                if swipe_allowed:
                    self.score = GameData.get_score()
                    HighlightOverlay(orig_obj=self.score_objects[score_id], parent=self).animate(font_size=500, color=(1, 1, 1, 0))
                    if goal_up:
                        SoundManager.play(Trigger.GOAL)
                    else:
                        SoundManager.play(Trigger.OFFSIDE)
                else:
                    # TODO: "Rote Karte"
                    pass
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
        if self.state == 'running':
            elapsed = int(time.time() - self.start_time)
            self.ids.topbar.customlabel.opacity = 1
            self.set_custom_text('{:02d}:{:02d}'.format(elapsed / 60, elapsed % 60))
        else:
            self.ids.topbar.customlabel.opacity = 1 - self.ids.topbar.customlabel.opacity

    def cancel_match(self):
        SoundManager.play(Trigger.MENU)
        self.manager.current = 'lounge'

    def resume_match(self):
        SoundManager.play(Trigger.GAME_RESUME)

    def submit_score(self):
        self.state = 'submitting'
        self.ids.btnSubmit.blocking = True
        self.thread = threading.Thread(target=self.__submit_score_thread)
        self.thread.start()
        Clock.schedule_once(self.__check_thread, 0)

    def __check_thread(self, dt):
        if self.thread.is_alive():
            # still working...
            Clock.schedule_once(self.__check_thread, 0.25)
        else:
            # finished!
            self.ids.btnSubmit.reset_icon_when_done = False
            self.ids.btnSubmit.blocking = False
            if self.submit_success:
                self.state = 'submit_success'
                self.__set_submit_icon(icons.check)
                Clock.schedule_once(lambda dt: self.show_elo(), 1.0)

            else:
                self.state = 'submit_failed'
                self.__set_submit_icon(icons.remove)

    def show_elo(self):
        self.state = 'elo'

    def __submit_score_thread(self):
        # submit score to remote server
        (error, elo) = ServerCom.submit_score(self.players, GameData.get_score())
        if error is None:
            self.submit_success = True
            self.elo = elo
            Logger.info('{}'.format(self.elo))

        else:
            self.submit_success = False
            self.elo = 0.0

class ScoreTrackerApp(App):

    def __init__(self, **kwargs):
        super(ScoreTrackerApp, self).__init__(**kwargs)
        self.bsm = None

    def build(self):
        # register fonts
        for font in settings.KIVY_FONTS:
            LabelBase.register(**font)

        self.bsm = BackgroundScreenManager()
        return self.bsm

    def on_stop(self):
        self.bsm.stop()


if __name__ == '__main__':
    ScoreTrackerApp().run()
