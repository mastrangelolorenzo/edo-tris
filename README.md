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

### config.json

```json
{ "broker": {"host": "localhost", "port": 8090, "realm": "realm1"},
  "tris":   {"host": "tris",      "port": 5000},
  "edo":    {"EDO-X": {"ip": "", "speed": 30, "safe_z": 150, "pick_z": 20, "place_z": 25, "orientation": [0, 180, 0]},
             "EDO-Y": {"ip": "", "speed": 30, "safe_z": 150, "pick_z": 20, "place_z": 25, "orientation": [0, 180, 0]}} }
```

- **pc1** usa `broker.host` / `broker.port`: indirizzo e porta (NAT di pc2) del broker. Li leggono sia il browser (WINGRID) sia EDO-X.
- **pc2** usa `tris.host` / `tris.port`: dove BUTLER trova il motore di gioco. `tris` = il TRIS simulato nello stesso compose; per il motore vero, il suo IP e la sua porta.
- **edo** configura i bracci: `ip` vuoto = braccio simulato (solo log); con l'IP del robot (`192.168.12.1` via Wi-Fi, `10.42.0.49` via cavo) l'attore lo pilota con l'SDK `pyedo`. `speed` e' la velocita' in percentuale, `safe_z` / `pick_z` / `place_z` le quote in mm per spostarsi, prendere e posare la pedina, `orientation` gli angoli A, E, R della pinza rivolta in basso. EDO-X legge la sezione su pc1, EDO-Y su pc2.
- I default (`localhost:8090`, `tris:5000`, bracci simulati) sono quelli dell'avvio in blocco.
- Il file e' montato come volume: dopo una modifica basta riavviare i container (`docker compose --profile ... restart`), senza rebuild.
- Le variabili d'ambiente `CROSSBAR_URL`, `CROSSBAR_REALM`, `TRIS_HOST`, `TRIS_PORT`, `EDO_IP` hanno la precedenza su `config.json`.

### Su due PC con i file .bat

| PC | Prima | Avvio | Setup (una volta, o quando si sposta qualcosa) |
|---|---|---|---|
| PC2 (AI) | `config.json`: `edo.EDO-Y.ip` | `avvia-pc2.bat` (mostra l'IP da dare al PC1) | `setup-pc2.bat` |
| PC1 (giocatore) | `config.json`: `broker.host` = IP del PC2, `edo.EDO-X.ip` | `avvia-pc1.bat` (apre il gioco a schermo intero in Edge; Alt+F4 per uscire) | `setup-pc1.bat` |

Si avvia prima il PC2, poi il PC1. Sul PC2 il firewall di Windows deve lasciar entrare la porta del broker (`BROKER_PORT`, 8090).

Il setup insegna i punti al robot collegato a quel PC con `actor/edo-common/teach.py`: si muove la pinza con l'app e.DO e a ogni passo si preme Invio (casella 5, casella 1, pedine 1-5, altezza di presa, di rilascio, di sicurezza). Lo script non muove il robot: legge la posa da rosbridge (`/cartesian_pose`). Griglia e pedine vanno a FRAME con `com.tris.saveArm`, che le scrive in `actor/frame/field.json` anche se FRAME e' sull'altro PC; quote e orientamento vanno nel `config.json` del PC del robot. Senza i .bat: `docker compose --profile pc2 run --rm --no-deps -v .:/repo -e CONFIG_FILE=/repo/config.json edo-y python teach.py EDO-Y`.

### Porte (`.env`)

Le porte *pubblicate* da Docker non possono venire da `config.json`, quindi stanno in `.env`: `BROKER_PORT` (broker su pc2, 8090) e `WINGRID_PORT` (WINGRID su pc1, 8880). `broker.port` in `config.json` e' la porta con cui pc1 vede il broker: coincide con `BROKER_PORT` salvo che il NAT la traduca.

Su pc1 e pc2 serve aprire/inoltrare la porta del broker verso pc1. All'avvio EDO-X, butler ed edo-y possono riavviarsi un paio di volte finche' il broker non e' raggiungibile (`restart: on-failure`).

## Struttura

| Cartella | Attore |
|---|---|
| `actor/wingrid` | interfaccia web (html+js, autobahn), servita da nginx su pc1 |
| `actor/frame` | coordinate di celle e pedine per ogni braccio (`field.json`) |
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
