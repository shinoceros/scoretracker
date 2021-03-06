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
from kivy.uix.screenmanager import FadeTransition, NoTransition
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
import randomhelper
import itertools

from hardwarelistener import HardwareListener
from soundmanager import SoundManager, Trigger
from thememanager import ThemeManager
from onpropertyanimationmixin import OnPropertyAnimationMixin
from servercom import ServerCom
from networkinfo import NetworkInfo
from gamedata import GameData
from playerdata import PlayerData
import icons

class BackgroundScreenManager(ScreenManager):

    def __init__(self, **kwargs):
        super(BackgroundScreenManager, self).__init__(**kwargs)
        #self.transition = FadeTransition(duration=0.2)
        self.transition = NoTransition()

        # setup hardware listener
        self.hwlistener = HardwareListener()
        Clock.schedule_interval(self.callback, 1/30.0)

        # setup network status
        NetworkInfo.start_polling()

        # setup screens
        self.add_widget(MenuScreen(name='menu'))
        self.add_widget(RfidSetupScreen(name='rfid-setup'))
        self.add_widget(SettingsScreen(name='settings'))
        self.add_widget(LineupScreen(name='lineup'))
        self.add_widget(MatchScreen(name='match'))

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
    network_info = DictProperty({'connected': False})

    def __init__(self, **kwargs):
        super(TopBar, self).__init__(**kwargs)
        self.network_btn_long_press = False

    def __network_btn_long_press(self, dt):
        self.network_btn_long_press = True
        NetworkInfo.reconnect()

    def check_network_button_collision(self, event):
        obj = self.ids['btn_network']
        return obj.collide_point(event.pos[0], event.pos[1])

    def handle_touch_down(self, event):
        if self.check_network_button_collision(event):
            Clock.unschedule(self.__network_btn_long_press)
            Clock.schedule_once(self.__network_btn_long_press, 1.0)

    def handle_touch_up(self, event):
        if self.check_network_button_collision(event):
            Clock.unschedule(self.__network_btn_long_press)

    def network_btn_pressed(self):
        if not self.network_btn_long_press:
            NetworkInfo.say_connection_status()
        else:
            self.network_btn_long_press = False

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
    def on_back_btn_pressed(self):
        self.manager.current = 'menu'

    # Next or custom pressed - stacked buttons are tricky!
    def on_right_btn_pressed(self):
        if self.ids.topbar.hasNext and self.ids.topbar.isNextEnabled:
            self.on_next_btn_pressed()
        else:
            self.on_custom_btn_pressed()
        
    def on_custom_btn_pressed(self):
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

    def set_custom_text_opacity(self, opacity):
        self.ids.topbar.customlabel.opacity = opacity

    def toggle_custom_text_opacity(self):
        self.ids.topbar.customlabel.opacity = 1 - self.ids.topbar.customlabel.opacity

    def set_custom_icon(self, icon_text):
        self.ids.topbar.customicontext = icon_text

    def set_custom_icon_opacity(self, opacity):
        self.ids.topbar.customicon.opacity = opacity

class MenuScreen(BaseScreen, OnPropertyAnimationMixin):

    fadeopacity = NumericProperty(1.0)
    network_str = StringProperty()

    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)
        # initial fade in
        self.fadeopacity = 0.0
        NetworkInfo.register(self.__update_network_info)
        SoundManager.play(Trigger.INTRO)

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

    def shutdown(self):
        # final fade out
        self.fadeopacity = 1.0
        Clock.schedule_once(self.shutdown_delayed, 2.0)

    def shutdown_delayed(self, dt):
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
        if players:
            PlayerData.set_players(players)
        self.__updatenum_players()
        # generate missing player names
        for player in players:
            SoundManager.create_player_sound(player)
        # fetch ranking
        ranking_attacker = ServerCom.fetch_ranking('attacker')
        if ranking_attacker:
            PlayerData.set_ranking('attacker', ranking_attacker)
        ranking_defender = ServerCom.fetch_ranking('defender')
        if ranking_defender:
            PlayerData.set_ranking('defender', ranking_defender)

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
        try:
            self.mixer = alsaaudio.Mixer(settings.ALSA_DEVICE)
        except alsaaudio.ALSAAudioError:
            self.mixer = alsaaudio.Mixer()
        self.volume = self.mixer.getvolume()[0]
        self.ids.volslider.bind(value=self.on_volume)

    def on_volume(self, instance, value):
        if value > 0:
            log_arg = int(25.4850887934 * math.log(value) - 16.4675854274)
            log_arg = max(0, min(100, log_arg))
        else:
            log_arg = 0
        self.mixer.setvolume(log_arg)

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


class LineupScreen(BaseScreen):

    current_player_slot = NumericProperty(0)
    players = ListProperty([{}] * 4)
    dropdown_player = ObjectProperty()
    drag_start_id = NumericProperty(-1)
    drag_stop_id = NumericProperty(-1)
    dragging = BooleanProperty()
    allPlayersSet = BooleanProperty()
    switching_locked = BooleanProperty()
    elo_ranges = DictProperty({'min': 0, 'max': 2000})

    def __init__(self, **kwargs):
        super(LineupScreen, self).__init__(**kwargs)
        self.set_title('Aufstellung')
        self.ids.topbar.hasNext = True
        self.is_dropdown_open = False
        self.slot_touch = None
        self.allPlayersSet = False
        self.switching_locked = False
        self.all_players = None

        self.__reset()

    def on_enter(self):
        self.all_players = PlayerData.get_players()
        self.elo_ranges = PlayerData.get_ranges()
        Clock.schedule_once(lambda dt: self.__setup_player_dropdown(), 0.2)
        self.current_player_slot = 0
        
        for (i, val) in enumerate(self.players):
            for p in self.all_players:
                if p['id'] == self.players[i].get('id', 0):
                    self.players[i] = p

    def on_leave(self):
        self.close_dropdown()

    def on_next_btn_pressed(self):
        self.manager.current = 'match'

    def __reset(self):
        self.players = [{}] * 4
        self.current_player_slot = 0

    def __setup_player_dropdown(self):
        self.dropdown_player = DropDown(auto_dismiss=False)
        self.dropdown_player.bind(on_select=self.on_player_select)
        self.dropdown_player.bind(on_dismiss=self.on_dropdown_dismiss)

        players = sorted(self.all_players, key=lambda player: player['name'])
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
        self.allPlayersSet = (count_players == 4)
        self.ids.topbar.isNextEnabled = self.allPlayersSet

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
        obj = self.ids['p' + str(slot_id)].ids.name
        HighlightOverlay(orig_obj=obj, parent=self, active=True, bold=True).animate(font_size=80, color=(1, 1, 1, 0))

    def switch_players(self, slot_id_1, slot_id_2):
        self.players[slot_id_1], self.players[slot_id_2] = self.players[slot_id_2], self.players[slot_id_1]
        for player_id in [slot_id_1, slot_id_2]:
            self.highlight_player(player_id)
        SoundManager.play(Trigger.PLAYERS_SWITCH)

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

    # a slot was released
    def handle_slot_touch_up(self, event):
        if self.slot_touch:
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
                    if not self.switching_locked:
                        self.switch_players(self.slot_touch['source_id'], self.slot_touch['target_id'])
                    else:
                        self.denied()

            self.slot_touch = None
            self.drag_start_id = -1
            self.drag_stop_id = -1
        else:
            self.close_dropdown()

    def set_player(self, player):
        # check if player has already been set before
        try:
            idx_already_set = self.players.index(player)
        except ValueError, e:
            # player is not in any team yet
            self.players[self.current_player_slot] = player
            self.highlight_player(self.current_player_slot)
            SoundManager.play(Trigger.PLAYER_JOINED, player)
            self.switching_locked = False

        else:
            # only switch position if new player is not already in current slot
            if idx_already_set != self.current_player_slot:
                if not self.switching_locked:
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
                        SoundManager.play(Trigger.PLAYERS_SWITCH)
                        self.highlight_player(idx_already_set)
                #locked
                else:
                    self.denied()
                    return
        # advance to next player block
        self.current_player_slot = (self.current_player_slot + 1) % 4

    def check_positions(self, players):
        if players[0]['id'] != self.players[0]['id'] and players[0]['id'] != self.players[1]['id']:
            # switch sides
            players[0], players[2] = players[2], players[0]
            players[1], players[3] = players[3], players[1]
        return players

    def randomize_players(self):
        self.set_switching_lock(settings.LOCK_LINEUP_ON_DECISION)
        players_copy = self.players[:]
        while players_copy == self.players:
            randomhelper.shuffle(players_copy)
        self.players = players_copy
        SoundManager.play(Trigger.PLAYERS_SHUFFLE)

    def equalize_players(self):
        self.set_switching_lock(settings.LOCK_LINEUP_ON_DECISION)
        # get min team elo lineup
        permutations = list(itertools.permutations(self.players))
        team_elo_list = [[i, abs(a['attacker']['elo'] + b['defender']['elo'] - c['attacker']['elo'] - d['defender']['elo'])] for i, (a, b, c, d) in enumerate(permutations)]
        team_elo_list = sorted(team_elo_list, key=lambda x: x[1])
        equal_lineup = list(permutations[team_elo_list[0][0]])
        # check positions
        self.players = self.check_positions(equal_lineup)
        SoundManager.play(Trigger.PLAYERS_EQUALIZE)
        
    def set_switching_lock(self, state):
        self.switching_locked = state

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
    timer_mode_elapsed_time = BooleanProperty(True)
    timer_toggle_state = False

    def __init__(self, **kwargs):
        super(MatchScreen, self).__init__(**kwargs)
        self.score_objects = [self.ids.labelHome, self.ids.labelAway]
        self.set_title('Spiel')
        self.score_touch = None
        self.start_time = 0.0
        self.stop_time = 0.0
        self.timer_event = None
        self.submit_success = None
        self.thread = None
        self.__reset()
        NetworkInfo.register(self.__callback_check_failed_submission)

    def __reset(self):
        self.state = ''
        GameData.reset_match()
        self.update_match()
        self.set_custom_text('')
        self.timer_mode_elapsed_time = True
        self.ids.btnSubmit.blocking = False
        container = self.ids.kickoff_ball.parent
        self.ids.kickoff_ball.pos = (container.x + container.width / 2.0, container.y + container.height)
        self.score_touch = None
        self.players = [{}] * 4
        self.kickoff_team = -1
        self.elo = 0.0
        Clock.unschedule(self.__update_timer_view)
        Clock.unschedule(self.__animate_kickoff)

    def __set_submit_icon(self, icon):
        self.ids.btnSubmit.icon = icon

    def restart_timer(self):
        if self.timer_event:
            self.timer_event.cancel()
        self.timer_toggle_state = False
        self.timer_event = Clock.schedule_interval(self.__update_timer_view, 1.0 if self.timer_mode_elapsed_time else 0.5)
        Clock.schedule_once(self.__update_timer_view)
        
    def on_enter(self):
        # reset and start match
        self.__reset()
        self.state = 'running'
        self.start_time = self.get_time()
        self.players = GameData.get_players()
        self.__set_submit_icon(icons.cloud_upload)
        self.restart_timer()
        self.handle_kickoff(True)

    def on_leave(self):
        self.__reset()

    def get_time(self):
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            return uptime_seconds

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

    def on_back_btn_pressed(self):
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
            self.manager.get_screen('lineup').set_switching_lock(False)
            self.manager.current = 'lineup'
        
    def on_custom_btn_pressed(self):
        self.timer_mode_elapsed_time = not self.timer_mode_elapsed_time
        self.restart_timer()

    def update_match(self):
        # fetch score from GameData
        self.score = GameData.get_score()
        # update kickoff information
        self.handle_kickoff(False)
        # check max goal during match
        if self.state == 'running':
            if GameData.is_match_finished():
                self.state = 'finished'
                self.stop_time = self.get_time()
                SoundManager.play(Trigger.GAME_END)
        # manual swiping can resume a finished match
        elif self.state == 'finished' and not GameData.is_match_finished():
            self.state = 'running'
            SoundManager.play(Trigger.GAME_RESUME)

    def __handle_goal(self, data):
        # 0 : home, 1: away
        if data in ["0", "1"]:
            team_id = int(data)
            GameData.add_goal(team_id)
            # play goal sound
            SoundManager.play(Trigger.GOAL)
            # update local match data
            self.update_match()
            # highlight score board
            HighlightOverlay(orig_obj=self.score_objects[team_id], parent=self).animate(font_size=500, color=(1, 1, 1, 0), d=2.0)

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
            ratio = min(1.0, abs(event.pos[1] - self.score_touch['startPos']) / settings.SCORE_SWIPE_DISTANCE)
            color = self.interpolate_color((1, 1, 1, 1), (1, 0.8, 0, 1), ratio)
            obj.color = color

    def handle_score_touch_up(self, event):
        if self.state not in ['running', 'finished']:
            return
        if self.score_touch:
            score_id = self.score_touch['id']
            dist = event.pos[1] - self.score_touch['startPos']
            if abs(dist) > settings.SCORE_SWIPE_DISTANCE:
                goal_up = dist > 0
                if goal_up:
                    swipe_allowed = GameData.add_goal(score_id)
                else:
                    swipe_allowed = GameData.revoke_goal(score_id)
                if swipe_allowed:
                    self.update_match()
                    HighlightOverlay(orig_obj=self.score_objects[score_id], parent=self).animate(font_size=500, color=(1, 1, 1, 0))
                    if goal_up:
                        SoundManager.play(Trigger.GOAL)
                    else:
                        SoundManager.play(Trigger.OFFSIDE)
                else:
                    self.denied()

            self.score_objects[score_id].color = (1, 1, 1, 1)
        self.score_touch = None

    def interpolate_color(self, color_start, color_end, ratio):
        list_color_start = list(color_start)
        list_color_end = list(color_end)
        list_color_result = []
        for i in range(0, len(list_color_start)):
            list_color_result.append(list_color_start[i] + (list_color_end[i] - list_color_start[i]) * ratio)
        return tuple(list_color_result)

    def __update_timer_view(self, dt):
        self.timer_toggle_state = not self.timer_toggle_state
        # show match timer
        if self.timer_mode_elapsed_time:
            if self.state == 'running':
                elapsed = int(self.get_time() - self.start_time)
                self.set_custom_text_opacity(1)
            else:
                elapsed = int(self.stop_time - self.start_time)
                self.set_custom_text_opacity(1 if self.timer_toggle_state else 0)
            
            self.set_custom_text('{:02d}:{:02d}'.format(elapsed / 60, elapsed % 60))
            self.set_custom_icon(icons.stopwatch)
        # show current time
        else:
            timetext = time.strftime('%H:%M')
            if not self.timer_toggle_state:
                timetext = timetext.replace(':', ' ')
            self.set_custom_text(timetext)
            self.set_custom_icon(icons.clock)
            self.set_custom_text_opacity(1)

    def cancel_match(self):
        SoundManager.play(Trigger.MENU)
        self.manager.get_screen('lineup').set_switching_lock(False)
        self.manager.current = 'lineup'

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
            self.__set_elo(elo)
            # fetch ranking
            ranking_attacker = ServerCom.fetch_ranking('attacker')
            if ranking_attacker:
                PlayerData.set_ranking('attacker', ranking_attacker)
            ranking_defender = ServerCom.fetch_ranking('defender')
            if ranking_defender:
                PlayerData.set_ranking('defender', ranking_defender)
        else:
            self.submit_success = False

    def __callback_check_failed_submission(self, nwinfo):
        if self.state == 'submit_failed':
            if nwinfo.get('connected', False):
                self.submit_score()

    @mainthread
    def __set_elo(self, elo):
        self.elo = elo

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
        pass


if __name__ == '__main__':
    ScoreTrackerApp().run()
