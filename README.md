# etdo-tris

Partita a Tris umano vs. agente IA giocata da due bracci robotici e.DO. Specifiche in [doc/requisiti.md](doc/requisiti.md).

## Avvio

```
docker compose up --build
```

Poi aprire http://localhost:8080 (WINGRID e' servito da crossbar). Se la porta 8080 e' occupata: `WINGRID_PORT=8090 docker compose up --build`.
All'avvio butler/edo-x/edo-y possono riavviarsi un paio di volte finche' crossbar non e' pronto (`restart: on-failure`).

## Struttura

| Cartella | Attore |
|---|---|
| `actor/wingrid` | interfaccia web (html+js, autobahn) |
| `actor/edo-x`, `actor/edo-y` | bracci robotici (python, simulati dalla classe `Arm`) |
| `actor/butler` | ponte tra crossbar e TRIS |
| `actor/tris` | motore di gioco simulato (TCP, porta 5000) |
| `broker/.crossbar` | configurazione crossbar.io (realm `realm1`) |

## Messaggi WAMP

RPC: `com.tris.moveX` (WINGRID -> EDO-X), `com.tris.movedX` (EDO-X -> BUTLER), `com.tris.moveY` (BUTLER -> EDO-Y), `com.tris.movedY` (EDO-Y -> WINGRID).
Topic: `com.tris.flap`, `com.tris.winner_x`, `com.tris.winner_y`.

Protocollo TRIS (una riga per messaggio): ricevi `1..9`; rispondi `1..9` oppure `F`/`X`/`Y`.
