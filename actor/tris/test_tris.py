import unittest
from unittest import mock

from tris import Game


class GameTest(unittest.TestCase):
    def play(self, x_moves, y_moves):
        game = Game()
        replies = []
        with mock.patch("tris.random.choice", side_effect=y_moves):
            for move in x_moves:
                replies.append(game.play(move))
        return replies

    def test_reply_is_a_free_cell(self):
        self.assertEqual(self.play([5], [1]), ["1"])

    def test_x_wins(self):
        self.assertEqual(self.play([1, 2, 3], [4, 5]), ["4", "5", "X"])

    def test_y_wins_with_its_move(self):
        self.assertEqual(self.play([1, 2, 9], [4, 5, 6]), ["4", "5", "6 Y"])

    def test_draw_when_board_is_full(self):
        replies = self.play([1, 3, 4, 8, 9], [2, 5, 6, 7])
        self.assertEqual(replies, ["2", "5", "6", "7", "F"])

    def test_invalid_moves(self):
        game = Game()
        with mock.patch("tris.random.choice", return_value=2):
            game.play(1)
        self.assertEqual(game.play(1), "ERR")
        self.assertEqual(game.play(2), "ERR")
        self.assertEqual(game.play(10), "ERR")


if __name__ == "__main__":
    unittest.main()
