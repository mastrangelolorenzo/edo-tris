import unittest

import json
import os

from frame import Field, check_arm, grid_cells

EXPLICIT = {
    1: (200, 400), 2: (300, 400), 3: (400, 400),
    4: (200, 300), 5: (300, 300), 6: (400, 300),
    7: (200, 200), 8: (300, 200), 9: (400, 200),
}


class GridCellsTest(unittest.TestCase):
    def test_matches_explicit_cells(self):
        cells = grid_cells([300, 300], [200, 400])
        for n, (x, y) in EXPLICIT.items():
            self.assertAlmostEqual(cells[n][0], x)
            self.assertAlmostEqual(cells[n][1], y)

    def test_rotated_grid_keeps_spacing(self):
        cells = grid_cells([0, 0], [0, 100])
        self.assertAlmostEqual(cells[5][0], 0)
        self.assertAlmostEqual(cells[5][1], 0)
        self.assertAlmostEqual(cells[9][0], 0)
        self.assertAlmostEqual(cells[9][1], -100)
        self.assertAlmostEqual(cells[3][0], 100)
        self.assertAlmostEqual(cells[3][1], 0)


GLOBAL_CONFIG = {
    "grid": {"center": [300, 300], "cell_1": [200, 400]},
    "arms": {
        "EDO-X": {"origin": [300, 0], "left": [250, 0], "right": [350, 0],
                  "pieces": {"1": [100, 100], "5": [300, 100]}},
        "EDO-Y": {"origin": [300, 600], "left": [350, 600], "right": [250, 600],
                  "pieces": {"1": [500, 500], "5": [300, 500]}},
    },
}


class FieldTest(unittest.TestCase):
    def test_local_config_matches_global_config(self):
        with open(os.path.join(os.path.dirname(__file__), "field.json"), encoding="utf-8") as f:
            local = Field(json.load(f))
        measured = Field(GLOBAL_CONFIG)
        for arm in ("EDO-X", "EDO-Y"):
            for n in range(1, 10):
                for a, b in zip(local.local_cell(arm, n), measured.local_cell(arm, n)):
                    self.assertAlmostEqual(a, b)
            for n in (1, 5):
                for a, b in zip(local.local_piece(arm, n), measured.local_piece(arm, n)):
                    self.assertAlmostEqual(a, b)


PIECES_OK = {str(n): [100, 50 * n] for n in range(1, 6)}


class CheckArmTest(unittest.TestCase):
    PIECES = {str(n): [100, 50 * n] for n in range(1, 6)}

    def test_accepts_valid_points(self):
        arm = check_arm({"center": [300, 0], "cell_1": [400, 100]}, self.PIECES)
        self.assertEqual(arm["grid"]["cell_1"], [400.0, 100.0])
        self.assertEqual(arm["pieces"]["5"], [100.0, 250.0])

    def test_rejects_bad_points(self):
        bad = [
            ({"center": [300, 0]}, self.PIECES),
            ({"center": [300, 0], "cell_1": [300, 0]}, self.PIECES),
            ({"center": [300, 0], "cell_1": [400, "x"]}, self.PIECES),
            ({"center": [300, 0], "cell_1": [400, 100, 5]}, self.PIECES),
            ({"center": [300, 0], "cell_1": [99999, 100]}, self.PIECES),
            ({"center": [400, 0], "cell_1": [400, 100]}, self.PIECES),
            ({"center": [300, 0], "cell_1": [400, 100]}, {**PIECES_OK, "3": [0, 500]}),
            ({"center": [300, 0], "cell_1": [400, 100]}, {"1": [1, 2]}),
        ]
        for grid, pieces in bad:
            with self.assertRaises(ValueError):
                check_arm(grid, pieces)


if __name__ == "__main__":
    unittest.main()
