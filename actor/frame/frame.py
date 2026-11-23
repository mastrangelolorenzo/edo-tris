"""Geometria: dal piano globale al piano locale di un braccio.

Il sistema locale di un braccio e' definito da 3 punti fissi, dati in
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


class Field:
    """Configurazione: celle e pedine nel piano globale, bracci con i loro 3 punti."""

    def __init__(self, config):
        self.cells = {int(k): tuple(v) for k, v in config["cells"].items()}
        self.arms = {}
        for name, arm in config["arms"].items():
            self.arms[name] = {
                "frame": Frame(arm["origin"], arm["left"], arm["right"]),
                "pieces": {int(k): tuple(v) for k, v in arm["pieces"].items()},
            }

    def _arm(self, arm):
        if arm not in self.arms:
            raise KeyError(f"braccio sconosciuto: {arm}")
        return self.arms[arm]

    def local_cell(self, arm, num):
        if num not in self.cells:
            raise KeyError(f"cella sconosciuta: {num}")
        return self._arm(arm)["frame"].to_local(self.cells[num])

    def local_piece(self, arm, num):
        a = self._arm(arm)
        if num not in a["pieces"]:
            raise KeyError(f"pedina sconosciuta per {arm}: {num}")
        return a["frame"].to_local(a["pieces"][num])
