import unittest
from Tournament import Tournament

class TestTournament(unittest.TestCase):

    def test_init(self):
        players = [0, 1, 2, 3] 
        t = Tournament(players)
        self.assertNotEqual(None, t)
        table = t.get_table()
        self.assertEqual(4, len(table))
        self.assertEqual(1, table[1].playerid)
        self.assertEqual(0, table[1].games)
        self.assertEqual(0, table[1].points)
        self.assertEqual(0, table[1].goaldifference)
        
        self.assertEqual(0, len(t.get_games()))
    def test_init_error(self):
        players = [0, 1, 2] 
        with self.assertRaisesRegexp(ValueError, 'Not enough players'):
            Tournament(players) 
    def test_new_round(self):
        players = [0, 1, 2, 3] 
        t = Tournament(players)  
        games = t.new_round()
        self.assertEqual(1, len(games)) 
        self.assertEqual(0, games[0].gameid) 
        self.assertEqual([0, 1, 2, 3], games[0].playerids) 
        
if __name__ == '__main__':
    unittest.main()
