# etdo-tris

Partita a Tris umano vs. agente IA giocata da due bracci robotici e.DO. Specifiche in [doc/requisiti.md](doc/requisiti.md).

## Avvio

Il progetto si clona su entrambe le macchine; poi si imposta `config.json` e si sceglie il **profilo** da avviare.

| Scenario | Comando |
|---|---|
| Tutto su una macchina | `docker compose --profile all up --build` |
| pc1 (utente): WINGRID + EDO-X | `docker compose --profile pc1 up --build` |
| pc2: broker, BUTLER, EDO-Y, FRAME, TRIS simulato | `docker compose --profile pc2 up --build` |

Senza `--profile` non parte nulla. WINGRID: http://localhost:8880 (su pc1 o, con `all`, sulla macchina unica).

### config.json

```json
{ "broker": {"host": "localhost", "port": 8090, "realm": "realm1"},
  "tris":   {"host": "tris",      "port": 5000} }
```

- **pc1** usa `broker.host` / `broker.port`: indirizzo e porta (NAT di pc2) del broker. Li leggono sia il browser (WINGRID) sia EDO-X.
- **pc2** usa `tris.host` / `tris.port`: dove BUTLER trova il motore di gioco. `tris` = il TRIS simulato nello stesso compose; per il motore vero, il suo IP e la sua porta.
- I default (`localhost:8090`, `tris:5000`) sono quelli dell'avvio in blocco.
- Il file e' montato come volume: dopo una modifica basta riavviare i container (`docker compose --profile ... restart`), senza rebuild.
- Le variabili d'ambiente `CROSSBAR_URL`, `CROSSBAR_REALM`, `TRIS_HOST`, `TRIS_PORT` hanno la precedenza su `config.json`.

### Porte (`.env`)

Le porte *pubblicate* da Docker non possono venire da `config.json`, quindi stanno in `.env`: `BROKER_PORT` (broker su pc2, 8090) e `WINGRID_PORT` (WINGRID su pc1, 8880). `broker.port` in `config.json` e' la porta con cui pc1 vede il broker: coincide con `BROKER_PORT` salvo che il NAT la traduca.

Su pc1 e pc2 serve aprire/inoltrare la porta del broker verso pc1. All'avvio EDO-X, butler ed edo-y possono riavviarsi un paio di volte finche' il broker non e' raggiungibile (`restart: on-failure`).

## Struttura

| Cartella | Attore |
|---|---|
| `actor/wingrid` | interfaccia web (html+js, autobahn), servita da nginx su pc1 |
| `actor/frame` | conversione coordinate globali -> locali dei bracci |
| `config.json` | indirizzi di broker e motore di gioco |
| `actor/edo-x`, `actor/edo-y` | bracci robotici (python, simulati dalla classe `Arm`) |
| `actor/butler` | ponte tra crossbar e TRIS |
| `actor/tris` | motore di gioco simulato (TCP, porta 5000) |
| `broker/.crossbar` | configurazione crossbar.io (realm `realm1`) |

## Messaggi WAMP

RPC: `com.tris.moveX` (WINGRID -> EDO-X), `com.tris.movedX` (EDO-X -> BUTLER), `com.tris.moveY` (BUTLER -> EDO-Y), `com.tris.movedY` (EDO-Y -> WINGRID).
Topic: `com.tris.flap`, `com.tris.winner_x`, `com.tris.winner_y`.

Protocollo TRIS (una riga per messaggio): ricevi `1..9`; rispondi `1..9` oppure `F`/`X`/`Y`.
