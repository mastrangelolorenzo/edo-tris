"""Geometria: celle e pedine nel piano locale di un braccio.

Il piano locale ha l'origine al centro della base del braccio, x verso la sua destra
e y in avanti (verso dove punta in home). I punti si leggono dall'app e.DO portando
la pinza sopra ciascuno (X in avanti, Y a sinistra), oppure si misurano nel piano
globale del tavolo e si convertono.

Nel secondo caso il sistema locale di un braccio e' definito da 3 punti fissi, dati in
coordinate globali:
  - origin: l'origine (0, 0) locale
  - left:   spigolo sinistro
  - right:  spigolo destro

Convenzione (visti dal braccio, rivolto verso il campo):
  - asse x locale = direzione left -> right
  - asse y locale = x ruotato di +90 (antiorario), cioe' "in avanti"
Il sistema e' rigido (solo rotazione + traslazione, stessa unita' di misura).
"""
import math


class Frame:
    def __init__(self, origin, left, right):
        self.origin = tuple(map(float, origin))
        dx = right[0] - left[0]
        dy = right[1] - left[1]
        width = math.hypot(dx, dy)
        if width == 0:
            raise ValueError("left e right coincidono: asse x indefinito")
        self.width = width
        self.ux = (dx / width, dy / width)          # versore asse x locale
        self.uy = (-self.ux[1], self.ux[0])         # versore asse y locale

    def to_local(self, point):
        """Coordinate globali (x, y) -> coordinate locali del braccio."""
        px = point[0] - self.origin[0]
        py = point[1] - self.origin[1]
        return (px * self.ux[0] + py * self.ux[1],
                px * self.uy[0] + py * self.uy[1])

    def to_global(self, point):
        """Coordinate locali -> coordinate globali (inversa di to_local)."""
        return (self.origin[0] + point[0] * self.ux[0] + point[1] * self.uy[0],
                self.origin[1] + point[0] * self.ux[1] + point[1] * self.uy[1])


def grid_cells(center, cell_1):
    """Le 9 celle di una griglia quadrata dal centro (casella 5) e dal centro della casella 1.

    Con x verso destra e y in avanti, la 1 e' in alto a sinistra, la 2 alla sua destra, la 4 sotto.
    """
    wx, wy = center[0] - cell_1[0], center[1] - cell_1[1]
    right = ((wx - wy) / 2, (wx + wy) / 2)
    down = ((wx + wy) / 2, (wy - wx) / 2)
    return {n: (cell_1[0] + (n - 1) % 3 * right[0] + (n - 1) // 3 * down[0],
                cell_1[1] + (n - 1) % 3 * right[1] + (n - 1) // 3 * down[1])
            for n in range(1, 10)}


def edo_to_local(point):
    """Base e.DO (x in avanti, y a sinistra) -> piano locale (x a destra, y in avanti)."""
    return (-point[1], point[0])


def global_cells(config):
    if "cells" in config:
        return {int(k): tuple(v) for k, v in config["cells"].items()}
    return grid_cells(config["grid"]["center"], config["grid"]["cell_1"])


REACH = 480  # portata massima dichiarata di e.DO, in mm


def check_arm(grid, pieces):
    """Punti di un braccio inviati da teach.py: il broker e' aperto, quindi si validano."""
    try:
        points = {"center": grid["center"], "cell_1": grid["cell_1"],
                  **{str(n): pieces[str(n)] for n in range(1, 6)}}
        clean = {k: [float(p[0]), float(p[1])] for k, p in points.items() if len(p) == 2}
    except (KeyError, TypeError, ValueError, IndexError):
        raise ValueError("servono grid.center, grid.cell_1 e le pedine 1-5, ciascuno [x, y]")
    if len(clean) != len(points):
        raise ValueError("ogni punto deve essere [x, y] in mm")
    if clean["center"] == clean["cell_1"]:
        raise ValueError("center e cell_1 coincidono")
    cells = grid_cells(edo_to_local(clean["center"]), edo_to_local(clean["cell_1"]))
    targets = [*cells.values(), *(clean[str(n)] for n in range(1, 6))]
    if not all(math.hypot(*t) <= REACH for t in targets):
        raise ValueError(f"caselle e pedine devono stare entro {REACH} mm dalla base (portata e.DO)")
    return {"grid": {"center": clean["center"], "cell_1": clean["cell_1"]},
            "pieces": {str(n): clean[str(n)] for n in range(1, 6)}}


class Field:
    """Celle e pedine di ogni braccio nelle sue coordinate locali.

    Formato per braccio: grid (center, cell_1) e pieces con le X, Y lette dall'app e.DO.
    Formato globale: cells o grid a livello radice, e per ogni braccio origin/left/right e pieces globali.
    """

    def __init__(self, config):
        self.arms = {}
        for name, arm in config["arms"].items():
            pieces = {int(k): tuple(v) for k, v in arm["pieces"].items()}
            if "grid" in arm:
                cells = grid_cells(edo_to_local(arm["grid"]["center"]), edo_to_local(arm["grid"]["cell_1"]))
                pieces = {n: edo_to_local(p) for n, p in pieces.items()}
            else:
                frame = Frame(arm["origin"], arm["left"], arm["right"])
                cells = {n: frame.to_local(p) for n, p in global_cells(config).items()}
                pieces = {n: frame.to_local(p) for n, p in pieces.items()}
            self.arms[name] = {"cells": cells, "pieces": pieces}

    def _arm(self, arm):
        if arm not in self.arms:
            raise KeyError(f"braccio sconosciuto: {arm}")
        return self.arms[arm]

    def local_cell(self, arm, num):
        cells = self._arm(arm)["cells"]
        if num not in cells:
            raise KeyError(f"cella sconosciuta: {num}")
        return cells[num]

    def local_piece(self, arm, num):
        pieces = self._arm(arm)["pieces"]
        if num not in pieces:
            raise KeyError(f"pedina sconosciuta per {arm}: {num}")
        return pieces[num]
