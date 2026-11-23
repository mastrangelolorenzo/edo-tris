"""BUTLER - intermediario tra TRIS (socket TCP) e BROCKER (crossbar.io).

- si registra su  com.tris.movedX(num): inoltra la mossa dell'umano a TRIS
- se TRIS risponde con un numero  -> chiama com.tris.moveY(num)
- se TRIS risponde con F/X/Y      -> pubblica com.tris.flap / winner_x / winner_y
- se TRIS risponde "num F|Y"      -> chiama moveY(num) e pubblica l'esito con
                                     argomento num (la mossa di Y che chiude la partita)
- su com.tris.new_game si ricollega a TRIS, che cosi' inizia una partita nuova
"""
import asyncio
import json
import os

from autobahn.asyncio.wamp import ApplicationRunner, ApplicationSession

URL = os.environ.get("CROSSBAR_URL", "ws://crossbar:8080/ws")
REALM = os.environ.get("CROSSBAR_REALM", "realm1")


def load_config():
    """config.json: CONFIG_FILE, /app/config.json, oppure la radice del repo."""
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.environ.get("CONFIG_FILE"), "/app/config.json",
                 os.path.join(here, "..", "..", "config.json")):
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


_tris = load_config().get("tris", {})
# precedenza: variabile d'ambiente > config.json > default
TRIS_HOST = os.environ.get("TRIS_HOST") or _tris.get("host", "tris")
TRIS_PORT = int(os.environ.get("TRIS_PORT") or _tris.get("port", 5000))

OUTCOME_TOPIC = {
    "F": "com.tris.flap",
    "X": "com.tris.winner_x",
    "Y": "com.tris.winner_y",
}


class Butler(ApplicationSession):
    async def onJoin(self, details):
        self.lock = asyncio.Lock()
        self.writer = None
        await self._connect_tris()
        await self.register(self.moved_x, "com.tris.movedX")
        await self.subscribe(self.new_game, "com.tris.new_game")
        print("[BUTLER] pronto, registrato com.tris.movedX", flush=True)

    async def _connect_tris(self):
        if self.writer:
            self.writer.close()
        while True:
            try:
                self.reader, self.writer = await asyncio.open_connection(TRIS_HOST, TRIS_PORT)
                print(f"[BUTLER] connesso a TRIS {TRIS_HOST}:{TRIS_PORT}", flush=True)
                return
            except OSError:
                print("[BUTLER] TRIS non raggiungibile, riprovo...", flush=True)
                await asyncio.sleep(1)

    async def new_game(self):
        async with self.lock:
            print("[BUTLER] nuova partita", flush=True)
            await self._connect_tris()

    async def moved_x(self, num):
        # risponde subito al chiamante (EDO-X); il resto avviene in background
        asyncio.ensure_future(self._ask_tris(int(num)))
        return True

    async def _ask_tris(self, num):
        try:
            async with self.lock:
                print(f"[BUTLER] -> TRIS: {num}", flush=True)
                self.writer.write(f"{num}\n".encode())
                await self.writer.drain()
                line = await self.reader.readline()
                if not line:
                    print("[BUTLER] connessione con TRIS persa", flush=True)
                    await self._connect_tris()
                    return
                answer = line.decode().strip().upper()
            print(f"[BUTLER] <- TRIS: {answer}", flush=True)
            await self._forward(answer)
        except Exception as error:
            print(f"[BUTLER] errore sulla mossa {num}: {error!r}", flush=True)

    async def _forward(self, answer):
        parts = answer.split()
        if len(parts) == 1 and parts[0].isdigit():
            await self.call("com.tris.moveY", int(parts[0]))
        elif len(parts) == 1 and parts[0] in OUTCOME_TOPIC:
            self.publish(OUTCOME_TOPIC[parts[0]])
        elif len(parts) == 2 and parts[0].isdigit() and parts[1] in OUTCOME_TOPIC:
            await self.call("com.tris.moveY", int(parts[0]))
            self.publish(OUTCOME_TOPIC[parts[1]], int(parts[0]))
        else:
            print(f"[BUTLER] risposta inattesa: {answer!r}", flush=True)


if __name__ == "__main__":
    ApplicationRunner(url=URL, realm=REALM).run(Butler)
