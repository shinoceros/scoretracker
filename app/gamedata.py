from random import randint

class GameDataBase(object):
    def __init__(self):
        self.history = []
        self.initial_kickoff_team = 0
        self.MAX_GOALS = 6
        self.reset_match()
        self.players = [{}] * 4
    
    def set_players(self, players):
        self.players = players

    def get_players(self):
        return self.players

    def add_goal(self, team_id):
        score = self.get_score()
        if score[0] < self.MAX_GOALS and score[1] < self.MAX_GOALS:
            self.history.append(team_id)
            return True
        return False

    def revoke_goal(self, team_id):
        # for manual score correction
        if self.history and team_id == self.history[-1]:
            del(self.history[-1])
            return True
        return False

    def get_score(self):
        return [self.history.count(0), self.history.count(1)]

    def is_match_finished(self):
        return self.MAX_GOALS in self.get_score()
        
    def get_kickoff_team(self):
        if self.history:
            return 1 - self.history[-1]
        else:
            return self.initial_kickoff_team

    def reset_match(self):
        self.history = []
        self.initial_kickoff_team = randint(0, 1)

GameData = GameDataBase()