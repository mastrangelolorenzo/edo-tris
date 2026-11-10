"""TRIS - motore di gioco simulato (finto agente IA).

Protocollo TCP, una riga di testo per messaggio:
  client -> TRIS : "<1..9>\n"   mossa dell'umano (X)
  TRIS -> client : "<1..9>\n"   mossa di risposta (Y)
                   oppure "F\n" | "X\n" | "Y\n"   esito della partita
                   (F = FLAT/patta, X = vince X, Y = vince Y)

Risponde con un numero a caso tra le caselle libere; quando il campo e' pieno
invia un esito a caso (F, X, Y) e la partita ricomincia da zero.
"""
import asyncio
import os
import random

HOST = os.environ.get("TRIS_HOST", "0.0.0.0")
PORT = int(os.environ.get("TRIS_PORT", "5000"))


async def handle(reader, writer):
    peer = writer.get_extra_info("peername")
    print(f"[TRIS] connesso {peer}", flush=True)
    free = set(range(1, 10))

    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            text = line.decode().strip()
            if not text.isdigit() or int(text) not in free:
                print(f"[TRIS] mossa non valida: {text!r}", flush=True)
                writer.write(b"ERR\n")
                await writer.drain()
                continue

            move = int(text)
            free.discard(move)
            print(f"[TRIS] umano (X) -> {move}", flush=True)

            if not free:
                outcome = random.choice("FXY")
                print(f"[TRIS] partita finita, esito: {outcome}", flush=True)
                reply = outcome
                free = set(range(1, 10))  # nuova partita
            else:
                answer = random.choice(sorted(free))
                free.discard(answer)
                print(f"[TRIS] agente (Y) -> {answer}", flush=True)
                reply = str(answer)

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
