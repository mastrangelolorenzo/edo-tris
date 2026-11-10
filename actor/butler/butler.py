"""BUTLER - intermediario tra TRIS (socket TCP) e BROCKER (crossbar.io).

- si registra su  com.tris.movedX(num): inoltra la mossa dell'umano a TRIS
- se TRIS risponde con un numero -> chiama com.tris.moveY(num)
- se TRIS risponde con F/X/Y     -> pubblica com.tris.flap / winner_x / winner_y
"""
import asyncio
import os

from autobahn.asyncio.wamp import ApplicationRunner, ApplicationSession

URL = os.environ.get("CROSSBAR_URL", "ws://crossbar:8080/ws")
REALM = os.environ.get("CROSSBAR_REALM", "realm1")
TRIS_HOST = os.environ.get("TRIS_HOST", "tris")
TRIS_PORT = int(os.environ.get("TRIS_PORT", "5000"))

OUTCOME_TOPIC = {
    "F": "com.tris.flap",
    "X": "com.tris.winner_x",
    "Y": "com.tris.winner_y",
}


class Butler(ApplicationSession):
    async def onJoin(self, details):
        self.lock = asyncio.Lock()
        self.reader, self.writer = await self._connect_tris()
        await self.register(self.moved_x, "com.tris.movedX")
        print("[BUTLER] pronto, registrato com.tris.movedX", flush=True)

    async def _connect_tris(self):
        while True:
            try:
                r, w = await asyncio.open_connection(TRIS_HOST, TRIS_PORT)
                print(f"[BUTLER] connesso a TRIS {TRIS_HOST}:{TRIS_PORT}", flush=True)
                return r, w
            except OSError:
                print("[BUTLER] TRIS non raggiungibile, riprovo...", flush=True)
                await asyncio.sleep(1)

    async def moved_x(self, num):
        # risponde subito al chiamante (EDO-X); il resto avviene in background
        asyncio.ensure_future(self._ask_tris(int(num)))
        return True

    async def _ask_tris(self, num):
        async with self.lock:
            print(f"[BUTLER] -> TRIS: {num}", flush=True)
            self.writer.write(f"{num}\n".encode())
            await self.writer.drain()
            line = await self.reader.readline()
            if not line:
                print("[BUTLER] connessione con TRIS persa", flush=True)
                self.reader, self.writer = await self._connect_tris()
                return
            answer = line.decode().strip().upper()
        print(f"[BUTLER] <- TRIS: {answer}", flush=True)

        if answer.isdigit():
            await self.call("com.tris.moveY", int(answer))
        elif answer in OUTCOME_TOPIC:
            await self.publish(OUTCOME_TOPIC[answer])
        else:
            print(f"[BUTLER] risposta inattesa: {answer!r}", flush=True)


if __name__ == "__main__":
    ApplicationRunner(url=URL, realm=REALM).run(Butler)
