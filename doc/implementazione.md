# Report di implementazione

Realizzazione di quanto descritto in [README.md](README.md): una partita a Tris tra un utente e un agente IA (simulato), giocata fisicamente da due bracci robotici e.DO (simulati).

## 1. Elementi in gioco

![Architettura](architettura.svg)

| Elemento | Cartella | Tecnologia | Ruolo |
|---|---|---|---|
| **WINGRID** | `actor/wingrid` | HTML + JavaScript, `autobahn.min.js` (incluso nel repo) | Mostra il campo, raccoglie la mossa dell'utente, mostra l'esito (corona di alloro, grigio, pollice in su). Servito da un nginx su pc1; legge l'indirizzo del broker da `config.json`. |
| **BROCKER** | `broker/.crossbar` | crossbar.io (immagine `crossbario/crossbar`) | Router WAMP: instrada chiamate (RPC) e messaggi (pub/sub) tra gli attori. Un solo realm, `realm1`, ruolo `anonymous` con tutti i permessi. |
| **EDO-X** | `actor/edo-x` | Python 3.12, autobahn (asyncio) | Braccio dell'umano. Esegue `moveX`: chiede a FRAME le coordinate locali di pedina e cella, sposta la pedina, poi chiama `movedX`. Reagisce agli esiti. |
| **EDO-Y** | `actor/edo-y` | Python 3.12, autobahn (asyncio) | Braccio dell'agente. Esegue `moveY` (stessa sequenza con FRAME), poi chiama `movedY`. Reazioni opposte a EDO-X (tranne la patta). |
| **BUTLER** | `actor/butler` | Python 3.12, autobahn + asyncio streams | Traduce tra WAMP e il socket TCP di TRIS. |
| **FRAME** | `actor/frame` | Python 3.12, autobahn | Servizio accessorio: converte le coordinate globali di celle e pedine nelle coordinate locali di ciascun braccio. Configurazione in `field.json`. |
| **TRIS** | `actor/tris` | Python 3.12, asyncio (solo libreria standard) | Motore di gioco simulato: risponde con una casella libera a caso; a campo pieno invia un esito a caso (F, X, Y). |

Su pc1 girano WINGRID ed EDO-X, su pc2 il resto (oppure tutto su una macchina, vedi *Distribuzione su 2 host*). Il tutto e' orchestrato da [docker-compose.yml](../docker-compose.yml) (7 container con il profilo `all`: crossbar, tris, butler, edo-y, frame, wingrid, edo-x-local).

## 2. Pattern e scelte implementative

- **Broker / WAMP (RPC + publish/subscribe).** Nessun attore conosce gli altri: tutti parlano solo con crossbar. Chi vuole eseguire un'azione la *registra* (`register`), chi la vuole richiedere la *chiama* (`call`). Gli esiti di fine partita sono eventi (`publish`/`subscribe`) perche' interessano a piu' attori contemporaneamente.
- **Chi registra cosa** (ogni procedura ha un solo esecutore):

  | Procedura | Registrata da | Chiamata da |
  |---|---|---|
  | `com.tris.moveX(n)` | EDO-X | WINGRID |
  | `com.tris.movedX(n)` | BUTLER | EDO-X |
  | `com.tris.moveY(n)` | EDO-Y | BUTLER |
  | `com.tris.movedY(n)` | WINGRID | EDO-Y |
  | `com.tris.localCell(arm, n)` | FRAME | EDO-X, EDO-Y |
  | `com.tris.localPiece(arm, n)` | FRAME | EDO-X, EDO-Y |

  | Topic | Pubblicato da | Sottoscritto da |
  |---|---|---|
  | `com.tris.flap`, `com.tris.winner_x`, `com.tris.winner_y` | BUTLER | WINGRID, EDO-X, EDO-Y |

- **Handler "risposta subito, lavoro dopo".** `moveX`, `moveY` e `movedX` rispondono immediatamente al chiamante e avviano il lavoro vero (movimento del braccio, interrogazione di TRIS) in un task asincrono (`asyncio.ensure_future`). In questo modo nessuna `call` resta appesa per tutta la durata di un movimento e non si hanno timeout di RPC.
- **Adapter / ponte (BUTLER).** Isola il protocollo di TRIS (testo su TCP) dal resto del sistema, che parla solo WAMP. Un `asyncio.Lock` serializza le richieste verso TRIS.
- **Protocollo TRIS.** Una riga di testo per messaggio. Ricevi `1..9`; rispondi `1..9` oppure `F` / `X` / `Y`. Una mossa non valida riceve `ERR`.
- **Coordinate locali.** I bracci non conoscono il piano globale: per ogni mossa chiedono a FRAME le coordinate locali di pedina e cella (vedi *Coordinate locali*).
- **Simulazione dei robot.** Ogni attore EDO ha una classe `Arm` con i metodi `place_piece` (riceve gia' le coordinate locali), `celebrate`, `sad`, `salute` che stampano nel log e attendono 2 secondi. Per usare i robot reali basta implementare questi metodi con l'SDK e.DO (la variabile `EDO_IP` e' gia' letta ma non ancora usata).
- **Avvio ordinato.** crossbar ha un `healthcheck` (porta 8080 in ascolto); butler, edo-y e frame (e, nel profilo `all`, edo-x-local) partono solo quando e' `healthy`. Su pc1 EDO-X non puo' aspettarlo (il broker e' su un altro host): `restart: on-failure` lo rilancia finche' il broker non e' raggiungibile. Vale anche per gli altri attori se la connessione cade all'avvio.
- **Librerie.** `autobahn[asyncio]==24.4.2` (client WAMP Python, backend asyncio); `autobahn-browser 22.10.1` (client WAMP nel browser); `asyncio` della libreria standard per TCP e concorrenza.

### Coordinate locali (FRAME)

`actor/frame/field.json` contiene, in coordinate **globali** (mm): le 9 celle, e per ogni braccio le sue pedine e i 3 punti fissi `origin`, `left`, `right`. Convenzione: asse x locale = direzione left -> right; asse y locale = x ruotato di 90 gradi antiorario (in avanti, visto dal braccio rivolto al campo); origine locale = `origin`. Il file e' montato come volume e riletto a ogni richiesta: per spostare un braccio basta modificarlo.

Su `moveX(3)` EDO-X: sceglie la prossima pedina (1..5), chiede `localPiece("EDO-X", p)` e `localCell("EDO-X", 3)`, sposta la pedina, poi chiama `movedX(3)`. La geometria pura e' in `actor/frame/frame.py` (classi `Frame`, `Field`).

### Distribuzione su 2 host

| Host | Attori | Profilo compose |
|---|---|---|
| pc1 (utente) | WINGRID (nginx, porta 8880), EDO-X | `pc1` |
| pc2 | crossbar, BUTLER, EDO-Y, FRAME, TRIS | `pc2` |
| unico | tutti | `all` (EDO-X diventa `edo-x-local`, che raggiunge il broker nella rete compose) |

Gli unici collegamenti tra host sono: pc1 -> broker (WebSocket, dal browser e da EDO-X) e pc2 -> motore di gioco (TCP, da BUTLER). I loro indirizzi stanno in `config.json` (sezioni `broker` e `tris`), vedi [README](../README.md). BUTLER parla o con il TRIS simulato (container su pc2, `tris.host: "tris"`) o con un motore esterno su un'altra macchina (`tris.host` / `tris.port` = IP e porta del motore; per non avviare il simulatore: `--scale tris=0`). Nel grafico l'alternativa e' il blocco tratteggiato "TRIS esterno". WINGRID non e' piu' servita da crossbar ma da un nginx su pc1, che pubblica anche `config.json` perche' il browser sappia dove collegarsi.

## 3. Come avviare il test

Prerequisito: Docker con Compose.

```
docker compose --profile all up --build
```

(per i due host: `--profile pc1` e `--profile pc2`, vedi README). Poi aprire WINGRID nel browser: **http://localhost:8880** (`WINGRID_PORT` in `.env`). Il broker e' pubblicato su `BROKER_PORT` (8090): se la porta e' occupata da un altro crossbar si ottiene "No Such Resource"; cambiare `BROKER_PORT` e `broker.port` in `config.json`.

Svolgimento:

1. Clicca una casella: compare una `X` sbiadita mentre EDO-X "posa" la pedina (2 s).
2. Dopo circa altri 2 s EDO-Y posa la sua pedina e compare una `Y`.
3. Si ripete finche' il campo e' pieno (l'utente fa 5 mosse): TRIS invia un esito a caso e WINGRID mostra corona di alloro (X), grigio (Y) o pollice in su (patta); i robot reagiscono nei log.
4. "Nuova partita" azzera il campo (TRIS si e' gia' azzerato da solo).

Per fermare tutto: `docker compose down`.

## 4. Come seguire il passaggio delle informazioni

### Log di tutti gli attori insieme

```
docker compose --profile all logs -f edo-x-local butler tris edo-y frame
```

Con l'avvio su 2 host: su pc1 `docker compose --profile pc1 logs -f edo-x`, su pc2 `docker compose --profile pc2 logs -f butler tris edo-y frame`.

Per una mossa dell'utente sulla casella 5 si vede, nell'ordine (numeri del grafico):

```
frame   | [FRAME] EDO-X: pedina 1 -> (-200.0, 100.0)               <- 2-3 (moveX ricevuta, EDO-X chiede a FRAME la pedina)
frame   | [FRAME] EDO-X: cella 5 -> (0.0, 300.0)                    <- 3 (e la cella)
edo-x   | [EDO-X] prelevo la pedina 1 in (...) e la poso sulla casella 5 in (...)   <- 3 (movimento eseguito)
edo-x   | [EDO-X] pedina posata in 5, torno a riposo
butler  | [BUTLER] -> TRIS: 5                                       <- 4-5 (movedX -> BUTLER)
tris    | [TRIS] umano (X) -> 5                                    <- 6
tris    | [TRIS] agente (Y) -> 2
butler  | [BUTLER] <- TRIS: 2                                       <- 7
frame   | [FRAME] EDO-Y: pedina 1 -> (...) / cella 2 -> (...)       <- 8-10 (moveY, poi EDO-Y chiede a FRAME pedina e cella)
edo-y   | [EDO-Y] prelevo la pedina 1 in (...) e la poso sulla casella 2 in (...)
edo-y   | [EDO-Y] pedina posata in 2, torno a riposo               <- 11 (poi movedY -> WINGRID, 12)
```

A fine partita `[TRIS] partita finita, esito: ...`, poi `[BUTLER] <- TRIS: F|X|Y` e le reazioni `ESULTO` / `mi deprimo` / `saluto` dei due bracci.

### Console del browser

Aprire gli strumenti di sviluppo (F12) sulla pagina WINGRID: la scheda *Network → WS* mostra i messaggi WAMP scambiati (`CALL`, `INVOCATION`, `RESULT`, `EVENT`...). La scheda *Console* mostra eventuali errori (per esempio `no_such_procedure` se un attore non e' ancora registrato).

### Log del broker

```
docker compose logs -f crossbar
```

Mostra le sessioni collegate (una per WINGRID, EDO-X, EDO-Y, BUTLER, FRAME).

### Chiamare il sistema senza interfaccia

Si puo' simulare l'utente senza browser chiamando `com.tris.moveX` da un qualunque client WAMP sul realm `realm1` all'indirizzo `ws://localhost:<BROKER_PORT>/ws`; il resto della catena si osserva nei log come sopra.

## 5. Limiti noti

- TRIS e' una simulazione casuale: non riconosce le vittorie reali e l'esito arriva solo a campo pieno.
- I bracci e.DO sono simulati; manca l'integrazione con l'SDK reale.
- Il broker e' aperto (ruolo `anonymous` con tutti i permessi): adatto a una dimostrazione locale, non a un ambiente esposto.
- WINGRID si collega con `ws://` (non `wss://`) all'indirizzo di `config.json`: nessuna cifratura sul tratto pc1 -> pc2.
- La geometria dei bracci (`field.json`) e' un modello rigido: 3 punti fissi, solo rotazione e traslazione, nessuna correzione di scala.
- Il numero di pedine per braccio e' fisso a 5 (`PIECES` in `edo_x.py` / `edo_y.py`).
