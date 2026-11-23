import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frame"))

from frame import Field, check_arm
from teach import apply_settings, arm_points

POSES = {
    "center": [300, 0, 120, 1, 179, 2],
    "cell_1": [400, 100, 120, 0, 180, 0],
    **{f"piece_{n}": [100, 250 - 50 * n, 120, 0, 180, 0] for n in range(1, 6)},
    "pick": [100, 200, 18.04, 0, 180, 0],
    "place": [300, 0, 26, 0, 180, 0],
    "safe": [300, 0, 160, 0, 180, 0],
}


class ApplyPosesTest(unittest.TestCase):
    def setUp(self):
        grid, pieces = arm_points(POSES)
        self.field = {"arms": {"EDO-X": check_arm(grid, pieces)}}
        self.config = {"edo": {"EDO-X": {"ip": "10.42.0.49", "speed": 30}}}
        apply_settings(self.config, "EDO-X", POSES)

    def test_writes_grid_pieces_and_heights(self):
        arm = self.field["arms"]["EDO-X"]
        self.assertEqual(arm["grid"], {"center": [300, 0], "cell_1": [400, 100]})
        self.assertEqual(arm["pieces"]["1"], [100, 200])
        self.assertEqual(arm["pieces"]["5"], [100, 0])
        settings = self.config["edo"]["EDO-X"]
        self.assertEqual(settings["ip"], "10.42.0.49")
        self.assertEqual((settings["pick_z"], settings["place_z"], settings["safe_z"]), (18.0, 26, 160))
        self.assertEqual(settings["orientation"], [1, 179, 2])

    def test_robot_goes_back_to_taught_points(self):
        import edo
        sent = []
        robot = edo.Robot.__new__(edo.Robot)
        robot.edo = type("Fake", (), {"moveCartesian": lambda _, *a: sent.append(a)})()
        robot.orientation = (0, 180, 0)
        field = Field(self.field)
        for cell, taught in ((5, [300, 0]), (1, [400, 100])):
            robot._move(field.local_cell("EDO-X", cell), 50)
            self.assertAlmostEqual(sent[-1][0], taught[0])
            self.assertAlmostEqual(sent[-1][1], taught[1])
        robot._move(field.local_piece("EDO-X", 3), 50)
        self.assertEqual(sent[-1][:2], (100, 100))


if __name__ == "__main__":
    unittest.main()
