import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frame"))

from frame import Field, teach_arm
from teach import apply_heights, arm_points

FIELD = {
    "cells": {str(n): [100 + 100 * ((n - 1) % 3), 400 - 100 * ((n - 1) // 3)] for n in range(1, 10)},
    "arms": {
        "EDO-X": {"origin": [200, 0], "left": [150, 0], "right": [250, 0],
                  "pieces": {str(n): [50 * n, 80] for n in range(1, 6)}},
        "EDO-Y": {"origin": [200, 600], "left": [250, 600], "right": [150, 600],
                  "pieces": {str(n): [400 - 50 * n, 520] for n in range(1, 6)}},
    },
}


def robot_poses(field, arm, z=120):
    """Le pose che il robot leggerebbe durante il setup (base e.DO: x avanti, y a sinistra)."""
    def pose(p):
        return [p[1], -p[0], z, 0, 180, 0]
    poses = {f"cell_{n}": pose(field.local_cell(arm, n)) for n in range(1, 10)}
    poses.update({f"piece_{n}": pose(field.local_piece(arm, n)) for n in range(1, 6)})
    poses.update(pick=[0, 0, 18.04, 0, 180, 0], place=[0, 0, 26, 0, 180, 0], safe=[0, 0, 160, 0, 180, 0])
    return poses


class SetupTest(unittest.TestCase):
    def test_heights_go_to_config(self):
        config = {"edo": {"EDO-X": {"ip": "10.42.0.49", "speed": 30}}}
        apply_heights(config, "EDO-X", robot_poses(Field(FIELD), "EDO-X"))
        self.assertEqual(config["edo"]["EDO-X"],
                         {"ip": "10.42.0.49", "speed": 30, "pick_z": 18.0, "place_z": 26, "safe_z": 160})

    def test_robots_go_back_to_taught_points(self):
        import edo
        layout = Field(FIELD)
        config = {"cells": {str(n): [0, 0] for n in range(1, 10)}, "arms": FIELD["arms"]}
        config["cells"] = {str(n): [n * 10, n * n] for n in range(1, 10)}
        for arm in ("EDO-X", "EDO-Y"):
            config, _ = teach_arm(config, arm, *arm_points(robot_poses(layout, arm)))
        field = Field(config)
        sent = []
        robot = edo.Robot.__new__(edo.Robot)
        robot.edo = type("Fake", (), {"moveCartesian": lambda _, *a: sent.append(a)})()
        for arm in ("EDO-X", "EDO-Y"):
            taught = robot_poses(layout, arm)
            for n in range(1, 10):
                robot._move(field.local_cell(arm, n), 50)
                self.assertLess(math.dist(sent[-1][:2], taught[f"cell_{n}"][:2]), 0.2)
            for n in range(1, 6):
                robot._move(field.local_piece(arm, n), 50)
                self.assertLess(math.dist(sent[-1][:2], taught[f"piece_{n}"][:2]), 0.2)


if __name__ == "__main__":
    unittest.main()
