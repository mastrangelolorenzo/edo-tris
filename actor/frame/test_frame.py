import math
import unittest

from frame import Field, Frame, fit_frame, teach_arm

CONFIG = {
    "cells": {"1": [200, 400], "2": [300, 400], "3": [400, 400],
              "4": [200, 300], "5": [300, 300], "6": [400, 300],
              "7": [200, 200], "8": [300, 200], "9": [400, 200]},
    "arms": {
        "EDO-X": {"origin": [300, 0], "left": [250, 0], "right": [350, 0],
                  "pieces": {str(n): [50 + 50 * n, 100] for n in range(1, 6)}},
        "EDO-Y": {"origin": [300, 600], "left": [350, 600], "right": [250, 600],
                  "pieces": {str(n): [550 - 50 * n, 500] for n in range(1, 6)}},
    },
}


def as_robot(field, arm):
    """Punti come li leggerebbe il robot: base e.DO, x in avanti e y a sinistra."""
    def edo(p):
        return [p[1], -p[0]]
    cells = {str(n): edo(field.local_cell(arm, n)) for n in range(1, 10)}
    pieces = {str(n): edo(field.local_piece(arm, n)) for n in range(1, 6)}
    return cells, pieces


class FitFrameTest(unittest.TestCase):
    def test_recovers_rotation_and_translation(self):
        real = Frame([120, -40], [120 - 30, -40 - 40], [120 + 30, -40 + 40])
        local = [(0, 100), (100, 300), (-80, 250), (40, 180)]
        origin, left, right = fit_frame(local, [real.to_global(p) for p in local])
        fitted = Frame(origin, left, right)
        for p in local:
            for a, b in zip(fitted.to_global(p), real.to_global(p)):
                self.assertAlmostEqual(a, b, places=6)


class TeachArmTest(unittest.TestCase):
    def test_teaching_both_arms_keeps_every_point(self):
        layout = Field(CONFIG)
        config = CONFIG
        for arm in ("EDO-X", "EDO-Y"):
            cells, pieces = as_robot(layout, arm)
            config, worst = teach_arm(config, arm, cells, pieces)
        self.assertLess(worst, 1e-6)
        taught = Field(config)
        for arm in ("EDO-X", "EDO-Y"):
            for n in range(1, 10):
                self.assertLess(math.dist(taught.local_cell(arm, n), layout.local_cell(arm, n)), 0.2)
            for n in range(1, 6):
                self.assertLess(math.dist(taught.local_piece(arm, n), layout.local_piece(arm, n)), 0.2)

    def test_rejects_bad_points(self):
        cells, pieces = as_robot(Field(CONFIG), "EDO-X")
        bad = [
            ("EDO-Z", cells, pieces),
            ("EDO-X", {k: v for k, v in cells.items() if k != "9"}, pieces),
            ("EDO-X", {**cells, "5": [300, "x"]}, pieces),
            ("EDO-X", {**cells, "5": [300, 0, 1]}, pieces),
            ("EDO-X", cells, {**pieces, "3": [0, 900]}),
        ]
        for arm, c, p in bad:
            with self.assertRaises(ValueError):
                teach_arm(CONFIG, arm, c, p)


if __name__ == "__main__":
    unittest.main()
