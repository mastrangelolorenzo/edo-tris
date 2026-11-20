# Analisi dei requisiti

L'implementazione di quanto descritto qui (architettura, distribuzione su 2 host, coordinate locali dei bracci, avvio e test) e' documentata in [implementazione.md](implementazione.md).

Il presente progetto mira allo sviluppo di un sistema software distribuito per la gestione di una partita a Tris tra un utente umano e un agente di intelligenza artificiale. L'interazione fisica sul campo di gioco è interamente affidata a due bracci robotici e.DO

Gli attori in gioco sono:
- EDO-X e EDO-Y, scritti in python, comunicano direttamente con il braccio robotico a loro associato per movimentarlo sul campo da gioco. EDO-X riceverà le indicazioni di movimento dall'umano mentre EDO-X dall'agente di intelligenza artificiale
- WINGRID, scritto in html+javascript, è l'interfaccia con cui l'utente interagisce direttamente. Visualizza il campo da gioco, raccoglie e trasmette le scelte dell'utente e mostra l'evoluzione del gioco
- BROCKER, istanza di crossbar.io, permette di sfruttare le caratteristiche del modello brocker per far comunicare le diverse entità tramite registrazione a topic o call.
- TRIS, il motore di gioco IA che comunica attraverso un socket tcp/ip, riceve la mossa effettuata dall'umano (1...9) e restituisce :
    - la mossa da fare in risposta 
    - se è finita patta (F=FLAT)
    - chi ha vinto (X oppure Y)
- BUTLER, scritto in python, che si pone come intermediario tra TRIS e BROCKER in modo da poter normalizzare le modalità di comunicazione

L'interfaccia di comunicazione tra i diversi componenti si può riassumere secondo il seguente schema:
- l'umano ha a disposizione una interfaccia grafica (WINGRID) su cui può premere la casella in cui vuole posizionare la sua pedina. l'interfaccia chiede l'esecuzione della procedura moveX(num) al BROCKER. 
- richiesta a chi si è registrato per l'esecuzione. 
- il braccio dell'umano (EDO-X) è interessato a eseguire questa azione quindi si registra per la sua esecuzione. quando ha finito chiede a BROCKER di eseguire movedX(num)
- BUTLER è interessato ad eseguire movedX quindi si registra su BROKER e l'esecuzione consiste nell'inviare a TRIS il numero richiesto
- quando BUTLER riceve da TRIS la posizione su cui spostare EDO-Y, allora chiede a BROCKER di eseguire moveY(num).
- EDO-Y è interessato a eseguire questo comando. Effettua lo spostamento e quando ha finito, chiede l'esecuzione di movedY(num) al BROCKER che viene intercettato da WINGRID che aggiorna il campo da gioco e aspetta la prossima mossa da parte dell'utente.

TRIS può inviare a BUTLER sia un numero che l'esito della partita F=Flap, X:WinnerX, Y:WinnerY

BUTLER, in base al comando ricevuto da CHESS invia a BROCKER il messaggio FLAP, WINNER-X oppure WINNER-Y

EDO-X, EDO-Y e WINGRID si registrano su questi messaggi e si comportano di conseguenza:
- EDO-X esulta per WINNER-X, si deprime per WINNER-Y e si posiziona in saluto per FLAP
- EDO-Y si comporta in modo diametralmente opposto (tranne per FLAT) rispoetto a EDO-X
- WINGRID mostra una corona di alloro per WINNER-X, diventa in tonalità di grigio per WINNER-Y, mentre mentre mostra un pollice in su in caso di FLAP

Creare i diversi attori dentro la directory actor, uno per ogni attore. 

Per TRIS crea un programma python che risponde con un numero a caso (da 1 a 9) tra quelli non ancora estratti di modo che simuli l'agente IA e che dopo aver finito la partita invii l'esito a caso (F, X, Y)

Infine scrivi il file docker-compose.yml che avvi tutti i servizi in modo da poterlo vedere all'opera
