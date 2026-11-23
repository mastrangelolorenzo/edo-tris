import unittest

from frame import grid_cells

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


if __name__ == "__main__":
    unittest.main()
