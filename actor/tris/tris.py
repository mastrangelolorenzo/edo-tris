"""TRIS - motore di gioco simulato (finto agente IA).

Protocollo TCP, una riga di testo per messaggio:
  client -> TRIS : "<1..9>\n"        mossa dell'umano (X)
  TRIS -> client : "<1..9>\n"        mossa di risposta (Y)
                   "X\n" | "F\n"     la mossa dell'umano chiude la partita (vince X / patta)
                   "<1..9> Y\n"      mossa di Y che vince la partita
                   "<1..9> F\n"      mossa di Y che chiude in patta
                   "ERR\n"           mossa non valida

Ogni connessione e' una partita: per ricominciare il client si ricollega.
L'agente sceglie a caso tra le caselle libere; vittorie e patta sono quelle reali.
"""
import asyncio
import os
import random

HOST = os.environ.get("TRIS_HOST", "0.0.0.0")
PORT = int(os.environ.get("TRIS_PORT", "5000"))

WIN_LINES = (
    (1, 2, 3), (4, 5, 6), (7, 8, 9),
    (1, 4, 7), (2, 5, 8), (3, 6, 9),
    (1, 5, 9), (3, 5, 7),
)


def wins(cells):
    return any(all(c in cells for c in line) for line in WIN_LINES)


class Game:
    def __init__(self):
        self.x = set()
        self.y = set()

    @property
    def free(self):
        return set(range(1, 10)) - self.x - self.y

    def outcome(self):
        if wins(self.x):
            return "X"
        if wins(self.y):
            return "Y"
        if not self.free:
            return "F"
        return None

    def play(self, move):
        """Applica la mossa di X e restituisce la risposta da inviare."""
        if self.outcome() or move not in self.free:
            return "ERR"
        self.x.add(move)
        print(f"[TRIS] umano (X) -> {move}", flush=True)
        if self.outcome():
            return self.outcome()

        answer = random.choice(sorted(self.free))
        self.y.add(answer)
        print(f"[TRIS] agente (Y) -> {answer}", flush=True)
        if self.outcome():
            return f"{answer} {self.outcome()}"
        return str(answer)


async def handle(reader, writer):
    peer = writer.get_extra_info("peername")
    print(f"[TRIS] connesso {peer}: nuova partita", flush=True)
    game = Game()

    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            text = line.decode().strip()
            reply = game.play(int(text)) if text.isdigit() else "ERR"
            if reply == "ERR":
                print(f"[TRIS] mossa non valida: {text!r}", flush=True)
            elif not reply.isdigit():
                print(f"[TRIS] partita finita, esito: {reply[-1]}", flush=True)
            writer.write(f"{reply}\n".encode())
            await writer.drain()
    finally:
        writer.close()
        print(f"[TRIS] disconnesso {peer}", flush=True)


async def main():
    server = await asyncio.start_server(handle, HOST, PORT)
    print(f"[TRIS] in ascolto su {HOST}:{PORT}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
