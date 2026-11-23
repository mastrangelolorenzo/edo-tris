# etdo-tris

Partita a Tris umano vs. agente IA giocata da due bracci robotici e.DO. Specifiche in [doc/README.md](doc/README.md), implementazione in [doc/implementazione.md](doc/implementazione.md).

## Avvio

Il progetto si clona su entrambe le macchine; poi si imposta `config.json` e si sceglie il **profilo** da avviare.

| Scenario | Comando |
|---|---|
| Tutto su una macchina | `docker compose --profile all up --build` |
| pc1 (utente): WINGRID + EDO-X | `docker compose --profile pc1 up --build` |
| pc2: broker, BUTLER, EDO-Y, FRAME, TRIS simulato | `docker compose --profile pc2 up --build` |

Senza `--profile` non parte nulla. WINGRID: http://localhost:8880 (su pc1 o, con `all`, sulla macchina unica).

Su Windows si puo' fare doppio clic: `avvia-pc2.bat` (avvia pc2 e mostra l'IP da mettere in `broker.host` sul pc1), poi `avvia-pc1.bat` (avvia pc1 e apre WINGRID a schermo intero in Edge; Alt+F4 per uscire).

**Setup dei bracci** (la prima volta, o quando si sposta qualcosa): con il pc2 avviato, `setup-pc2.bat` sul pc2 e `setup-pc1.bat` sul pc1, ognuno per il robot collegato a lui. Si muove la pinza con l'app e.DO e a ogni passo si preme Invio: le 9 caselle, le 5 pedine, poi le altezze di presa, rilascio e sicurezza. Lo script (`actor/edo-common/teach.py`) non muove il robot: legge la posa da rosbridge (`/cartesian_pose`). Caselle e pedine vanno a FRAME con `com.tris.saveArm`, che le scrive in `field.json` nel formato di sempre; le quote vanno nel `config.json` del pc del robot.

### config.json

```json
{ "broker": {"host": "localhost", "port": 8090, "realm": "realm1"},
  "tris":   {"host": "tris",      "port": 5000},
  "edo":    {"EDO-X": {"ip": "", "speed": 30, "safe_z": 150, "pick_z": 20, "place_z": 25},
             "EDO-Y": {"ip": "", "speed": 30, "safe_z": 150, "pick_z": 20, "place_z": 25}} }
```

- **pc1** usa `broker.host` / `broker.port`: indirizzo e porta (NAT di pc2) del broker. Li leggono sia il browser (WINGRID) sia EDO-X.
- **pc2** usa `tris.host` / `tris.port`: dove BUTLER trova il motore di gioco. `tris` = il TRIS simulato nello stesso compose; per il motore vero, il suo IP e la sua porta.
- **edo** configura i bracci: `ip` vuoto = braccio simulato (solo log); con l'IP del robot (`192.168.12.1` via Wi-Fi, `10.42.0.49` via cavo) l'attore lo pilota con l'SDK `pyedo`. `speed` e' la velocita' in percentuale, `safe_z` / `pick_z` / `place_z` le quote in mm per spostarsi, prendere e posare la pedina. EDO-X legge la sezione su pc1, EDO-Y su pc2.
- I default (`localhost:8090`, `tris:5000`, bracci simulati) sono quelli dell'avvio in blocco.
- Il file e' montato come volume: dopo una modifica basta riavviare i container (`docker compose --profile ... restart`), senza rebuild.
- Le variabili d'ambiente `CROSSBAR_URL`, `CROSSBAR_REALM`, `TRIS_HOST`, `TRIS_PORT`, `EDO_IP` hanno la precedenza su `config.json`.

### Porte (`.env`)

Le porte *pubblicate* da Docker non possono venire da `config.json`, quindi stanno in `.env`: `BROKER_PORT` (broker su pc2, 8090) e `WINGRID_PORT` (WINGRID su pc1, 8880). `broker.port` in `config.json` e' la porta con cui pc1 vede il broker: coincide con `BROKER_PORT` salvo che il NAT la traduca.

Su pc1 e pc2 serve aprire/inoltrare la porta del broker verso pc1. All'avvio EDO-X, butler ed edo-y possono riavviarsi un paio di volte finche' il broker non e' raggiungibile (`restart: on-failure`).

## Struttura

| Cartella | Attore |
|---|---|
| `actor/wingrid` | interfaccia web (html+js, autobahn), servita da nginx su pc1 |
| `actor/frame` | conversione coordinate globali -> locali dei bracci |
| `config.json` | indirizzi di broker e motore di gioco |
| `actor/edo-x`, `actor/edo-y` | bracci robotici (python): entry point dei due attori |
| `actor/edo-common` | codice comune dei bracci: sessione WAMP, braccio reale (`pyedo`) o simulato |
| `actor/butler` | ponte tra crossbar e TRIS |
| `actor/tris` | motore di gioco simulato (TCP, porta 5000) |
| `broker/.crossbar` | configurazione crossbar.io (realm `realm1`) |

## Messaggi WAMP

RPC: `com.tris.moveX` (WINGRID -> EDO-X), `com.tris.movedX` (EDO-X -> BUTLER), `com.tris.moveY` (BUTLER -> EDO-Y), `com.tris.movedY` (EDO-Y -> WINGRID).
Topic: `com.tris.flap`, `com.tris.winner_x`, `com.tris.winner_y` (con argomento `n` se la partita e' chiusa dalla mossa `n` di Y), `com.tris.new_game` (WINGRID -> BUTLER, EDO-X, EDO-Y).

Protocollo TRIS (una riga per messaggio): ricevi `1..9`; rispondi `1..9` (mossa di Y), `X`/`F` (la mossa dell'umano chiude la partita), `n Y`/`n F` (la mossa `n` di Y chiude la partita) oppure `ERR`. Ogni connessione TCP e' una partita: per una nuova partita BUTLER si ricollega.
