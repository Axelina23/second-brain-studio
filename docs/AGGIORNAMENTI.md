# Aggiornamenti dell'app senza rompere niente

Regole nate dai guasti del 2026-11-08. Valgono per chi modifica l'app (Claude compreso):
leggile prima di pubblicare una versione.

## Perché si rompeva
Un difetto che compare **solo nella versione riaperta dall'installer** non si vede provando
l'app aperta a mano. Il 2026-11-08 la 1240, riaperta dall'installer, aveva canali standard non
validi e ogni comando esterno falliva con `[WinError 6] Handle non valido`. Risultato:
"Nessun repository per il second brain", semaforo grigio e pulsante "Aggiornamento pronto"
che non partiva. In più la chiave GitHub dell'app era stata revocata senza che l'app se ne
accorgesse, e il semaforo usava il gestore credenziali di Windows, che apriva il login nel
browser.

## Regole per il codice
1. **Comandi esterni**: `canali.sistema()` va chiamato all'avvio di `main.py`, prima di ogni
   `subprocess`, e non va tolto. Nell'app installata mette **sempre** i tre canali su NUL: un
   controllo di validità non basta, perché quello della 1346 si faceva ingannare dal canale
   passato dall'installer. Nei comandi nuovi passa comunque `stdin=subprocess.DEVNULL`, oppure
   tutti e tre i canali se non catturi l'output.
1b. **Avvio dell'aggiornamento**: solo con `aggiornamenti.avvia_staccato()`, che prova WMI, poi
   un processo staccato fuori dal job, poi staccato semplice, sempre con canali espliciti. Lo
   script parte **prima** della chiusura dell'app: se non parte, l'app resta aperta e mostra
   l'errore. `App.aggiorna()` ha un blocco e lo script un mutex
   (`Local\SecondBrainStudioAggiornamento`): con un doppio clic parte un solo installer.
   Prima, con tre clic, partivano tre installer e due fallivano con codice 1.
2. **Git dall'app**: sempre con `ambiente_git(token)` (`motore/sync.py`), mai il gestore
   credenziali di Windows, che da un processo senza finestre resta appeso.
3. **Chiave GitHub**: una risposta 401 vuol dire chiave revocata. Va chiamato `github.rifiutato()`,
   che la cancella, avvisa e mostra "Ricollega GitHub". Non ingoiare mai l'errore.
4. **Errori**: tutto finisce in `~/.claude/second-brain/app-errori.log`. È il primo posto da guardare.

## Prima di pubblicare (`build.ps1 -Pubblica`)
1. `python -m pytest -q` dalla radice del repo: tutti verdi.
2. `powershell -ExecutionPolicy Bypass -File app\build.ps1`, senza pubblicare.
3. Nell'app premi **"Aggiornamento pronto"** e controlla che si installi e si riapra da sola.
4. **Nella versione appena riaperta dall'installer** (è il punto che conta) controlla:
   - semaforo a colori, non grigio;
   - Impostazioni → GitHub: repository visibile, "Collegato come @...";
   - Sincronizza: messaggio "Sincronizzato" e nessun login nel browser;
   - `app-errori.log` senza errori nuovi.
5. Rifai `build.ps1` e premi di nuovo "Aggiornamento pronto" **da quella versione**: il
   pulsante deve funzionare anche dalla versione che è stata aggiornata, non solo da quella
   aperta a mano.
6. Solo allora `build.ps1 -Pubblica`. Crea una **pre-release**, che ricevono solo le app con
   "Anche le versioni di prova" attivo (dal 2026-11-08 è spento di default, `impostazioni.py`:
   sui PC di chi sviluppa va acceso a mano). Entro 6 ore, o subito con "Cerca aggiornamenti",
   la scaricano, verificano lo sha256 e mostrano il pulsante.
   Per una versione per tutti: aggiungi in cima a `CHANGELOG.md` una sezione `## ...` con le
   novità (in inglese) e usa `build.ps1 -Stabile`: release vera, con quelle note e l'avviso
   su SmartScreen.
7. Verifica come da un altro PC: `aggiornamenti.controlla("<versione vecchia>", True, chiave, <cartella temporanea>)`
   deve scaricare la nuova release e superare il controllo dello sha256.

## Altri PC e altri utenti
- Si installa per utente in `%LOCALAPPDATA%\Programs\Second Brain Studio`, senza diritti di
  amministratore, e nessun percorso dipende da questo PC (dati in `~/.claude/second-brain`).
- Finché il repository `second-brain-studio` è **privato**, solo chi collega un account GitHub
  con accesso al repo riceve gli aggiornamenti. Per gli altri utenti va reso pubblico, dopo
  aver ripulito la cronologia (vedi `Progetti/Second Brain/CLAUDE.md`).
- Se su un PC la chiave GitHub dell'app è stata revocata, il controllo riceve 401 e l'app
  chiede di ricollegare GitHub: senza chiave l'aggiornamento non arriva.
- Le versioni fino alla 1346 hanno il pulsante difettoso. Su quei PC la prima volta si aggiorna
  a mano (recupero qui sotto), oppure chiudendo con Esci e riaprendo l'app a mano prima di premere il pulsante.

## Se il pulsante non parte (recupero)
1. Chiudi l'app con **Esci** dall'icona vicino all'orologio. Chiudere la finestra non basta.
2. Apri a mano l'ultimo installer: `app\dist\Second Brain Studio Setup <versione>.exe`,
   oppure scaricalo dalle release di `Axelina23/second-brain-studio`.
3. Leggi `aggiornamento.log`, `setup-ultimo.log` e `app-errori.log` in `~/.claude/second-brain/`.
