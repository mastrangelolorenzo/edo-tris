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


REACH = 480  # portata massima dichiarata di e.DO, in mm


def edo_to_local(point):
    """Base e.DO (x in avanti, y a sinistra) -> piano locale (x a destra, y in avanti)."""
    return (-float(point[1]), float(point[0]))


def fit_frame(local_points, global_points):
    """origin, left, right della posa rigida che porta i punti locali sui globali (minimi quadrati)."""
    n = len(local_points)
    lcx = sum(p[0] for p in local_points) / n
    lcy = sum(p[1] for p in local_points) / n
    gcx = sum(p[0] for p in global_points) / n
    gcy = sum(p[1] for p in global_points) / n
    dot = cross = 0.0
    for (lx, ly), (gx, gy) in zip(local_points, global_points):
        lx, ly, gx, gy = lx - lcx, ly - lcy, gx - gcx, gy - gcy
        dot += lx * gx + ly * gy
        cross += lx * gy - ly * gx
    angle = math.atan2(cross, dot)
    c, s = math.cos(angle), math.sin(angle)
    origin = (gcx - (c * lcx - s * lcy), gcy - (s * lcx + c * lcy))
    left = (origin[0] - 50 * c, origin[1] - 50 * s)
    right = (origin[0] + 50 * c, origin[1] + 50 * s)
    return origin, left, right


def _taught_points(points, count, what):
    try:
        clean = {n: (float(points[str(n)][0]), float(points[str(n)][1])) for n in range(1, count + 1)
                 if len(points[str(n)]) == 2}
    except (KeyError, TypeError, ValueError, IndexError):
        clean = {}
    if len(clean) != count:
        raise ValueError(f"servono {what} 1-{count}, ciascuna [x, y] in mm")
    if not all(math.hypot(*p) <= REACH for p in clean.values()):
        raise ValueError(f"{what} oltre {REACH} mm dalla base: fuori dalla portata di e.DO")
    return clean


def teach_arm(config, arm, cells, pieces):
    """Nuova configurazione con i punti letti dal robot arm (coordinate della base e.DO).

    Il piano globale diventa quello del braccio insegnato: le sue celle diventano le celle
    del campo. Gli altri bracci vengono riposizionati facendo combaciare le loro celle con
    quelle nuove; restituisce anche lo scarto massimo (mm) di quell'adattamento.
    """
    if arm not in config["arms"]:
        raise ValueError(f"braccio sconosciuto: {arm}")
    taught_cells = {n: edo_to_local(p) for n, p in _taught_points(cells, 9, "caselle").items()}
    taught_pieces = {n: edo_to_local(p) for n, p in _taught_points(pieces, 5, "pedine").items()}
    old = Field(config)
    new = dict(config, arms=dict(config["arms"]))
    new["cells"] = {str(n): [round(v, 1) for v in p] for n, p in taught_cells.items()}
    new["arms"][arm] = {"origin": [0, 0], "left": [-50, 0], "right": [50, 0],
                        "pieces": {str(n): [round(v, 1) for v in p] for n, p in taught_pieces.items()}}
    worst = 0.0
    for other in config["arms"]:
        if other == arm:
            continue
        other_cells = [old.local_cell(other, n) for n in range(1, 10)]
        origin, left, right = fit_frame(other_cells, [taught_cells[n] for n in range(1, 10)])
        frame = Frame(origin, left, right)
        worst = max(worst, max(math.dist(frame.to_local(taught_cells[n]), other_cells[n - 1])
                               for n in range(1, 10)))
        new["arms"][other] = {
            "origin": [round(v, 2) for v in origin],
            "left": [round(v, 2) for v in left],
            "right": [round(v, 2) for v in right],
            "pieces": {str(n): [round(v, 1) for v in frame.to_global(old.local_piece(other, n))]
                       for n in old.arms[other]["pieces"]},
        }
    Field(new)
    return new, worst
