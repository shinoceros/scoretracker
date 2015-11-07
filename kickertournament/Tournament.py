from collections import namedtuple
PlayerData = namedtuple("Playerdata", "playerid games points goaldifference") #Spieler mit Punkten, Tordifferenz
GameData = namedtuple("GameData", "gameid playerids played")#game_id, status ob gespielt oder nicht  
class Tournament:
    def __init__(self, players):  # # [ player_id ]
        if len(players) < 4:
            raise ValueError('Not enough players.')
        self.players = players
        self.currentGameId = 0
        self.games = []
        self.playermatrix = []
        self.resulttable = []   
        for playerid in players:
            playerdata = PlayerData(playerid, 0, 0, 0)
            self.resulttable.append(playerdata)
        return None
    def new_round(self):
        sortedplayers = sorted(self.resulttable, key=lambda PlayerData:PlayerData.games)
        if len(sortedplayers) < 4:
            raise ValueError('Not enough players.')
        games = [];
        players = [];
        for i in range(0, 4):
            players.append(sortedplayers[i].playerid)  
        game = GameData(self.get_gameId(), players, False)
        self.games.append(game)
        games.append(game)
        return games
    def add_results(self, gameresults):  # # { game_id: gid, result: bool FirstTeamWins }
        return None
    def final(self, rounds):  # #returns:  [ { game_id: gid, players: [ player_id ] } ]
        return None
    def get_table(self):
        return self.resulttable
    def get_games(self):
        return self.games
    def get_gameId(self):
        id = self.currentGameId
        self.currentGameId = self.currentGameId + 1 
        return id