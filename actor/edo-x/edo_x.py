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
PIECES = 5


class Arm:
    """Simulazione del braccio e.DO."""

    async def place_piece(self, piece, piece_xy, cell, cell_xy):
        """piece_xy e cell_xy sono coordinate LOCALI del braccio."""
        print(f"[{NAME}] prelevo la pedina {piece} in ({piece_xy[0]:.1f}, {piece_xy[1]:.1f}) "
              f"e la poso sulla casella {cell} in ({cell_xy[0]:.1f}, {cell_xy[1]:.1f})", flush=True)
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
        self.used = 0  # pedine gia' usate (le pedine sono 1..PIECES, poi si ricomincia)
        await self.register(self.move_x, "com.tris.moveX")
        await self.subscribe(lambda: self.arm.celebrate(), "com.tris.winner_x")
        await self.subscribe(lambda: self.arm.sad(), "com.tris.winner_y")
        await self.subscribe(lambda: self.arm.salute(), "com.tris.flap")
        print(f"[{NAME}] pronto", flush=True)

    async def move_x(self, num):
        asyncio.ensure_future(self._execute(int(num)))
        return True

    async def _execute(self, num):
        piece = self.used % PIECES + 1
        self.used += 1
        piece_xy = await self.call("com.tris.localPiece", NAME, piece)
        cell_xy = await self.call("com.tris.localCell", NAME, num)
        await self.arm.place_piece(piece, piece_xy, num, cell_xy)
        await self.call("com.tris.movedX", num)


if __name__ == "__main__":
    ApplicationRunner(url=URL, realm=REALM).run(EdoX)
