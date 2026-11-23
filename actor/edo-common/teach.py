"""Insegna i punti a un braccio e.DO.

Muovi il braccio con l'app e.DO; a ogni passo premi Invio e lo script legge
la posa dal robot (topic /cartesian_pose, la stessa usata da moveCartesian)
e la scrive in field.json (griglia e pedine) e config.json (quote e orientamento).
Lo script non muove il robot: ascolta soltanto.

Uso: python teach.py EDO-X   (oppure EDO-Y)
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.environ.get("CONFIG_FILE", os.path.join(HERE, "..", "..", "config.json"))
FIELD_FILE = os.environ.get("FIELD_FILE", os.path.join(HERE, "..", "frame", "field.json"))

STEPS = [
    ("center", "pinza dritta verso il basso, sopra il centro della casella 5 (in mezzo)"),
    ("cell_1", "sopra il centro della casella 1"),
    *[(f"piece_{n}", f"sopra la pedina {n}") for n in range(1, 6)],
    ("pick", "giu' sulla pedina, all'altezza a cui la pinza la afferra"),
    ("place", "giu' su una casella, all'altezza a cui la pinza lascia la pedina"),
    ("safe", "in alto, a un'altezza a cui passa sopra tutto senza urtare"),
]


def apply_poses(field, config, arm, poses):
    """poses: nome passo -> [x, y, z, a, e, r]. Aggiorna field e config sul posto."""
    xy = {name: [round(p[0], 1), round(p[1], 1)] for name, p in poses.items()}
    field.setdefault("arms", {})[arm] = {
        "grid": {"center": xy["center"], "cell_1": xy["cell_1"]},
        "pieces": {str(n): xy[f"piece_{n}"] for n in range(1, 6)},
    }
    settings = config.setdefault("edo", {}).setdefault(arm, {})
    settings["pick_z"] = round(poses["pick"][2], 1)
    settings["place_z"] = round(poses["place"][2], 1)
    settings["safe_z"] = round(poses["safe"][2], 1)
    settings["orientation"] = [round(v, 1) for v in poses["center"][3:6]]


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main(arm):
    import roslibpy  # qui e non in cima: roslibpy fissa twisted, edo.py usa asyncio

    config = read_json(CONFIG_FILE)
    ip = os.environ.get("EDO_IP") or config.get("edo", {}).get(arm, {}).get("ip")
    if not ip:
        sys.exit(f"Manca l'IP di {arm}: scrivilo in config.json -> edo.{arm}.ip")

    ros = roslibpy.Ros(host=ip, port=9090)
    try:
        ros.run()
    except roslibpy.core.RosTimeoutError:
        sys.exit(f"Robot {ip} non raggiungibile: sei sulla sua rete (Wi-Fi o cavo)?")
    latest = {}
    topic = roslibpy.Topic(ros, "/cartesian_pose", "edo_core_msgs/CartesianPose")
    topic.subscribe(lambda m: latest.update(pose=[m[k] for k in "xyzaer"]))
    time.sleep(1)
    if "pose" not in latest:
        sys.exit(f"Nessuna posizione da {ip}: il robot e' acceso e inizializzato dall'app?")

    poses = {}
    for name, where in STEPS:
        input(f"Porta la pinza {where}, poi premi Invio ")
        poses[name] = list(latest["pose"])
        print("  X {:.1f}  Y {:.1f}  Z {:.1f}  A {:.1f}  E {:.1f}  R {:.1f}".format(*poses[name]))

    topic.unsubscribe()
    ros.terminate()

    field = read_json(FIELD_FILE)
    apply_poses(field, config, arm, poses)
    write_json(FIELD_FILE, field)
    write_json(CONFIG_FILE, config)
    print(f"Salvato: {FIELD_FILE} e {CONFIG_FILE}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("EDO-X", "EDO-Y"):
        sys.exit("Uso: python teach.py EDO-X   (oppure EDO-Y)")
    main(sys.argv[1])
