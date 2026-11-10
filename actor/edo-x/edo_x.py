"""EDO-X - braccio robotico dell'umano.

- si registra su com.tris.moveX(num): sposta il braccio sulla casella num
  e, a movimento finito, chiama com.tris.movedX(num)
- reagisce agli esiti: esulta (WINNER-X), si deprime (WINNER-Y), saluta (FLAP)

La classe Arm simula il robot e.DO: per pilotare quello reale basta
implementare i metodi con le chiamate dell'SDK (vedi EDO_IP).
"""
import asyncio
import os

from autobahn.asyncio.wamp import ApplicationRunner, ApplicationSession

URL = os.environ.get("CROSSBAR_URL", "ws://crossbar:8080/ws")
REALM = os.environ.get("CROSSBAR_REALM", "realm1")
EDO_IP = os.environ.get("EDO_IP", "")  # IP del robot reale (vuoto = simulato)
NAME = "EDO-X"


class Arm:
    """Simulazione del braccio e.DO."""

    async def place_piece(self, cell):
        print(f"[{NAME}] prelevo la pedina e la poso sulla casella {cell}", flush=True)
        await asyncio.sleep(2)
        print(f"[{NAME}] pedina posata in {cell}, torno a riposo", flush=True)

    async def celebrate(self):
        print(f"[{NAME}] \\o/ ESULTO!", flush=True)
        await asyncio.sleep(2)

    async def sad(self):
        print(f"[{NAME}] :( mi deprimo...", flush=True)
        await asyncio.sleep(2)

    async def salute(self):
        print(f"[{NAME}] o/ saluto (patta)", flush=True)
        await asyncio.sleep(2)


class EdoX(ApplicationSession):
    async def onJoin(self, details):
        self.arm = Arm()
        await self.register(self.move_x, "com.tris.moveX")
        await self.subscribe(lambda: self.arm.celebrate(), "com.tris.winner_x")
        await self.subscribe(lambda: self.arm.sad(), "com.tris.winner_y")
        await self.subscribe(lambda: self.arm.salute(), "com.tris.flap")
        print(f"[{NAME}] pronto", flush=True)

    async def move_x(self, num):
        asyncio.ensure_future(self._execute(int(num)))
        return True

    async def _execute(self, num):
        await self.arm.place_piece(num)
        await self.call("com.tris.movedX", num)


if __name__ == "__main__":
    ApplicationRunner(url=URL, realm=REALM).run(EdoX)
