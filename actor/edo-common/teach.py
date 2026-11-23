"""Insegna i punti a un braccio e.DO.

Muovi il braccio con l'app e.DO; a ogni passo premi Invio e lo script legge
la posa dal robot (topic ROS /cartesian_pose, la stessa usata da moveCartesian).
Griglia e pedine vanno a FRAME con com.tris.saveArm, che le scrive in field.json
anche se FRAME gira sull'altro PC; quote e orientamento vanno nel config.json
di questo PC, dove li legge il braccio. Lo script non muove il robot: ascolta soltanto.

Uso: python teach.py EDO-X   (oppure EDO-Y)
"""
import asyncio
import json
import os
import sys

from autobahn.asyncio.wamp import ApplicationRunner, ApplicationSession
from autobahn.wamp.exception import ApplicationError
from autobahn.asyncio.websocket import WebSocketClientFactory, WebSocketClientProtocol

from edo import broker_address, load_config

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.environ.get("CONFIG_FILE", os.path.join(HERE, "..", "..", "config.json"))
ROSBRIDGE_PORT = 9090

STEPS = [
    ("center", "dritta verso il basso, sopra il centro della casella 5 (in mezzo)"),
    ("cell_1", "sopra il centro della casella 1"),
    *[(f"piece_{n}", f"sopra la pedina {n}") for n in range(1, 6)],
    ("pick", "giu' sulla pedina, all'altezza a cui la pinza la afferra"),
    ("place", "giu' su una casella, all'altezza a cui la pinza lascia la pedina"),
    ("safe", "in alto, a un'altezza a cui passa sopra tutto senza urtare"),
]


def arm_points(poses):
    """poses: nome passo -> [x, y, z, a, e, r]. Restituisce (grid, pieces) per FRAME."""
    xy = {name: [round(p[0], 1), round(p[1], 1)] for name, p in poses.items()}
    grid = {"center": xy["center"], "cell_1": xy["cell_1"]}
    pieces = {str(n): xy[f"piece_{n}"] for n in range(1, 6)}
    return grid, pieces


def apply_settings(config, arm, poses):
    settings = config.setdefault("edo", {}).setdefault(arm, {})
    settings["pick_z"] = round(poses["pick"][2], 1)
    settings["place_z"] = round(poses["place"][2], 1)
    settings["safe_z"] = round(poses["safe"][2], 1)
    settings["orientation"] = [round(v, 1) for v in poses["center"][3:6]]


class PoseReader(WebSocketClientProtocol):
    """Client rosbridge minimo: si abbona a /cartesian_pose e tiene l'ultima posa."""
    latest = None

    def onOpen(self):
        self.sendMessage(json.dumps({"op": "subscribe", "topic": "/cartesian_pose",
                                     "type": "edo_core_msgs/CartesianPose"}).encode())

    def onMessage(self, payload, is_binary):
        message = json.loads(payload)
        if message.get("op") == "publish":
            PoseReader.latest = [float(message["msg"][k]) for k in "xyzaer"]


async def collect(ip):
    loop = asyncio.get_running_loop()
    factory = WebSocketClientFactory(f"ws://{ip}:{ROSBRIDGE_PORT}")
    factory.protocol = PoseReader
    try:
        transport, _ = await asyncio.wait_for(loop.create_connection(factory, ip, ROSBRIDGE_PORT), 5)
    except (OSError, asyncio.TimeoutError):
        raise RuntimeError(f"robot {ip} non raggiungibile: sei sulla sua rete (Wi-Fi o cavo)?")
    await asyncio.sleep(1.5)
    if PoseReader.latest is None:
        transport.close()
        raise RuntimeError(f"nessuna posizione da {ip}: il robot e' acceso e inizializzato dall'app?")

    poses = {}
    for name, where in STEPS:
        await loop.run_in_executor(None, input, f"Porta la pinza {where}, poi premi Invio ")
        poses[name] = list(PoseReader.latest)
        print("  X {:.1f}  Y {:.1f}  Z {:.1f}  A {:.1f}  E {:.1f}  R {:.1f}".format(*poses[name]), flush=True)
    transport.close()
    return poses


class TeachSession(ApplicationSession):
    async def onJoin(self, details):
        extra = self.config.extra
        arm = extra["arm"]
        try:
            poses = await collect(extra["ip"])
            grid, pieces = arm_points(poses)
            await self.call("com.tris.saveArm", arm, grid, pieces)
            config = load_config()
            apply_settings(config, arm, poses)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                f.write("\n")
            print(f"Salvato: griglia e pedine di {arm} in field.json (FRAME), quote e orientamento in config.json")
            extra["ok"] = True
        except Exception as error:
            message = error.args[0] if isinstance(error, ApplicationError) and error.args else error
            print(f"Errore: {message}")
        self.leave()

    def onDisconnect(self):
        asyncio.get_event_loop().stop()


def main(arm):
    ip = os.environ.get("EDO_IP") or load_config().get("edo", {}).get(arm, {}).get("ip")
    if not ip:
        sys.exit(f"Manca l'IP di {arm}: scrivilo in config.json -> edo.{arm}.ip")
    url, realm = broker_address()
    extra = {"arm": arm, "ip": ip, "ok": False}
    asyncio.set_event_loop(asyncio.new_event_loop())
    try:
        ApplicationRunner(url=url, realm=realm, extra=extra).run(TeachSession)
    except OSError:
        sys.exit(f"Broker {url} non raggiungibile: il PC2 e' avviato?")
    if not extra["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("EDO-X", "EDO-Y"):
        sys.exit("Uso: python teach.py EDO-X   (oppure EDO-Y)")
    main(sys.argv[1])
