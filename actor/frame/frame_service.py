"""FRAME - servizio di conversione coordinate globali -> locali del braccio.

Legge la configurazione (griglia e pedine di ogni braccio, vedi frame.py)
e registra:
  - com.tris.localCell(arm, num)  -> [x, y] locali della cella num
  - com.tris.localPiece(arm, num) -> [x, y] locali della pedina num
  - com.tris.saveArm(arm, grid, pieces) -> scrive in field.json i punti insegnati con teach.py
La configurazione viene riletta a ogni richiesta: spostare un braccio
richiede solo di modificare il file, senza riavviare nulla.
"""
import json
import os

from autobahn.asyncio.wamp import ApplicationRunner, ApplicationSession

from frame import Field, check_arm

URL = os.environ.get("CROSSBAR_URL", "ws://crossbar:8080/ws")
REALM = os.environ.get("CROSSBAR_REALM", "realm1")
CONFIG = os.environ.get("FIELD_CONFIG", "/app/field.json")
NAME = "FRAME"


def load_field():
    with open(CONFIG, encoding="utf-8") as f:
        return Field(json.load(f))


class FrameService(ApplicationSession):
    async def onJoin(self, details):
        load_field()  # fallisce subito se la configurazione e' errata
        await self.register(self.local_cell, "com.tris.localCell")
        await self.register(self.local_piece, "com.tris.localPiece")
        await self.register(self.save_arm, "com.tris.saveArm")
        print(f"[{NAME}] pronto (config: {CONFIG})", flush=True)

    async def local_cell(self, arm, num):
        x, y = load_field().local_cell(arm, int(num))
        print(f"[{NAME}] {arm}: cella {num} -> ({x:.1f}, {y:.1f})", flush=True)
        return [x, y]

    async def local_piece(self, arm, num):
        x, y = load_field().local_piece(arm, int(num))
        print(f"[{NAME}] {arm}: pedina {num} -> ({x:.1f}, {y:.1f})", flush=True)
        return [x, y]

    async def save_arm(self, arm, grid, pieces):
        if arm not in ("EDO-X", "EDO-Y"):
            raise ValueError(f"braccio sconosciuto: {arm}")
        with open(CONFIG, encoding="utf-8") as f:
            config = json.load(f)
        config.setdefault("arms", {})[arm] = check_arm(grid, pieces)
        Field(config)
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"[{NAME}] {arm}: punti insegnati salvati", flush=True)
        return True


if __name__ == "__main__":
    ApplicationRunner(url=URL, realm=REALM).run(FrameService)
