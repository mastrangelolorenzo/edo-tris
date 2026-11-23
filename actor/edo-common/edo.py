"""Parte comune di EDO-X ed EDO-Y: braccio e.DO e sessione WAMP.

EDO-<me> (me = "X" oppure "Y"):
- si registra su com.tris.move<me>(num): chiede a FRAME le coordinate locali di
  pedina e cella, sposta la pedina e, a movimento finito, chiama com.tris.moved<me>(num)
- reagisce agli esiti: esulta se vince, si deprime se perde, saluta per la patta
- su com.tris.new_game ricomincia dalla pedina 1

Il braccio e' reale se ha un IP (config.json -> edo.EDO-<me>.ip, oppure la
variabile EDO_IP), altrimenti e' simulato e scrive solo nel log.
Le azioni del braccio sono eseguite una alla volta, nell'ordine in cui arrivano.
"""
import asyncio
import json
import os

from autobahn.asyncio.wamp import ApplicationRunner, ApplicationSession

PIECES = 5
OTHER = {"X": "Y", "Y": "X"}


def load_config():
    """config.json: CONFIG_FILE, /app/config.json, oppure la radice del repo."""
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.environ.get("CONFIG_FILE"), "/app/config.json",
                 os.path.join(here, "..", "..", "config.json")):
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


class Robot:
    """Movimenti del braccio reale con l'SDK pyedo (chiamate bloccanti)."""

    ORIENTATION = (0, 180, 0)  # pinza rivolta verso il basso

    def __init__(self, ip, settings):
        from pyedo import eduedo

        self.edo = eduedo(ip)
        self.edo.setSpeed(settings.get("speed", 30))
        self.safe_z = settings.get("safe_z", 150)
        self.pick_z = settings.get("pick_z", 20)
        self.place_z = settings.get("place_z", 25)
        self.orientation = tuple(settings.get("orientation", self.ORIENTATION))
        self.home()

    def home(self):
        self.edo.moveToHome()

    def place_piece(self, piece_xy, cell_xy):
        self.edo.gripperOpen()
        self._visit(piece_xy, self.pick_z, self.edo.gripperClose)
        self._visit(cell_xy, self.place_z, self.edo.gripperOpen)
        self.home()

    def celebrate(self):
        self._gesture([(0, 0, 0, 0, 45, 0), (0, 0, 0, 0, -45, 0)] * 2)

    def sad(self):
        self._gesture([(0, 30, 60, 0, 60, 0)])

    def salute(self):
        self._gesture([(30, 0, -45, 0, 0, 0), (-30, 0, -45, 0, 0, 0)] * 2)

    def _visit(self, xy, z, grip):
        self._move(xy, self.safe_z)
        self._move(xy, z)
        grip()
        self._move(xy, self.safe_z)

    def _move(self, xy, z):
        # piano locale di FRAME: x verso destra, y in avanti; base e.DO: x in avanti, y a sinistra
        self.edo.moveCartesian(xy[1], -xy[0], z, *self.orientation)

    def _gesture(self, poses):
        for pose in poses:
            self.edo.moveJoints(*pose)
        self.home()


class Arm:
    """Il braccio visto dalla sessione: reale se c'e' un Robot, altrimenti simulato."""

    def __init__(self, name, settings):
        self.name = name
        self.settings = settings
        self.robot = None

    async def connect(self):
        ip = os.environ.get("EDO_IP") or self.settings.get("ip")
        if not ip:
            self.log("nessun IP configurato: braccio simulato")
            return
        self.log(f"collegamento a e.DO {ip}...")
        self.robot = await asyncio.to_thread(Robot, ip, self.settings)
        self.log("e.DO pronto")

    async def place_piece(self, piece, piece_xy, cell, cell_xy):
        self.log(f"prelevo la pedina {piece} in ({piece_xy[0]:.1f}, {piece_xy[1]:.1f}) "
                 f"e la poso sulla casella {cell} in ({cell_xy[0]:.1f}, {cell_xy[1]:.1f})")
        await self._run(lambda robot: robot.place_piece(piece_xy, cell_xy))
        self.log(f"pedina posata in {cell}, torno a riposo")

    async def celebrate(self):
        self.log("\\o/ ESULTO!")
        await self._run(Robot.celebrate)

    async def sad(self):
        self.log(":( mi deprimo...")
        await self._run(Robot.sad)

    async def salute(self):
        self.log("o/ saluto (patta)")
        await self._run(Robot.salute)

    async def _run(self, action):
        if self.robot:
            await asyncio.to_thread(action, self.robot)
        else:
            await asyncio.sleep(2)

    def log(self, message):
        print(f"[{self.name}] {message}", flush=True)


class EdoSession(ApplicationSession):
    async def onJoin(self, details):
        self.me = self.config.extra["me"]
        self.name = f"EDO-{self.me}"
        self.busy = asyncio.Lock()
        self.used = 0  # pedine gia' usate (le pedine sono 1..PIECES)

        self.arm = Arm(self.name, load_config().get("edo", {}).get(self.name, {}))
        await self.arm.connect()

        await self.register(self.move, f"com.tris.move{self.me}")
        await self.subscribe(lambda *_: self.react(self.arm.celebrate), f"com.tris.winner_{self.me.lower()}")
        await self.subscribe(lambda *_: self.react(self.arm.sad), f"com.tris.winner_{OTHER[self.me].lower()}")
        await self.subscribe(lambda *_: self.react(self.arm.salute), "com.tris.flap")
        await self.subscribe(self.new_game, "com.tris.new_game")
        print(f"[{self.name}] pronto", flush=True)

    async def move(self, num):
        # risponde subito al chiamante; il movimento avviene in background
        asyncio.ensure_future(self._execute(int(num)))
        return True

    async def _execute(self, num):
        async with self.busy:
            try:
                piece = self.used % PIECES + 1
                self.used += 1
                piece_xy = await self.call("com.tris.localPiece", self.name, piece)
                cell_xy = await self.call("com.tris.localCell", self.name, num)
                await self.arm.place_piece(piece, piece_xy, num, cell_xy)
                await self.call(f"com.tris.moved{self.me}", num)
            except Exception as error:
                print(f"[{self.name}] errore sulla mossa {num}: {error!r}", flush=True)

    async def react(self, action):
        async with self.busy:
            await action()

    def new_game(self):
        self.used = 0


def broker_address():
    broker = load_config().get("broker", {})
    # precedenza: variabile d'ambiente > config.json > default
    url = os.environ.get("CROSSBAR_URL") or \
        f"ws://{broker.get('host', 'crossbar')}:{broker.get('port', 8080)}/ws"
    realm = os.environ.get("CROSSBAR_REALM") or broker.get("realm", "realm1")
    return url, realm


def run(me):
    url, realm = broker_address()
    ApplicationRunner(url=url, realm=realm, extra={"me": me}).run(EdoSession)
