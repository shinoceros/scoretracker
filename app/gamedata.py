import randomhelper

from kivy.properties import ListProperty
from kivy.event import EventDispatcher

class GameDataBase(EventDispatcher):
    score = [0, 0]
    history = ListProperty([])
    players = [{}] * 4
    MAX_GOALS = 6

    def __init__(self, **kwargs):
        super(GameDataBase, self).__init__(**kwargs)
        self.initial_kickoff_team = 0
        self.reset_match()

    # if history changes recalculate score
    def on_history(self, instance, value):
        self.score = [self.history.count(0), self.history.count(1)]

    def set_players(self, players):
        self.players = players

    def get_players(self):
        return self.players

    def add_goal(self, team_id):
        if self.score[0] < self.MAX_GOALS and self.score[1] < self.MAX_GOALS:
            self.history.append(team_id)
            return True
        return False

    def revoke_goal(self, team_id):
        # for manual score correction
        if self.history and team_id == self.history[-1]:
            del self.history[-1]
            return True
        return False

    def get_score(self):
        return self.score

    def is_match_finished(self):
        return self.MAX_GOALS in self.score

    def is_almost_tie(self):
        almost_tie = False
        if self.history:
            score_diff = self.score[0] - self.score[1]
            last_scorer = self.history[-1]
            almost_tie = (score_diff == 1 and last_scorer == 1 or score_diff == -1 and last_scorer == 0)
        return almost_tie

    def is_tie(self):
        score_diff = self.score[0] - self.score[1]
        return score_diff == 0

    def get_kickoff_team(self):
        if self.history:
            return 1 - self.history[-1]
        return self.initial_kickoff_team

    def reset_match(self):
        self.history = []
        self.initial_kickoff_team = randomhelper.get_int(0, 1)

GameData = GameDataBase()
