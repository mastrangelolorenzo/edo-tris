"""FRAME - servizio di conversione coordinate globali -> locali del braccio.

Legge la configurazione (celle, pedine e posizione dei bracci nel piano
globale) e registra:
  - com.tris.localCell(arm, num)  -> [x, y] locali della cella num
  - com.tris.localPiece(arm, num) -> [x, y] locali della pedina num
  - com.tris.saveArm(arm, cells, pieces) -> salva in field.json i punti letti dal robot (setup)
La configurazione viene riletta a ogni richiesta: spostare un braccio
richiede solo di modificare il file, senza riavviare nulla.
"""
import json
import os

from autobahn.asyncio.wamp import ApplicationRunner, ApplicationSession

from frame import Field, teach_arm

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

    async def save_arm(self, arm, cells, pieces):
        with open(CONFIG, encoding="utf-8") as f:
            config = json.load(f)
        config, worst = teach_arm(config, arm, cells, pieces)
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"[{NAME}] {arm}: punti del setup salvati (scarto altri bracci {worst:.1f} mm)", flush=True)
        return round(worst, 1)


if __name__ == "__main__":
    ApplicationRunner(url=URL, realm=REALM).run(FrameService)
