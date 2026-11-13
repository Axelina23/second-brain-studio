# IA locali: contratto funzionale per l'interfaccia

Backend e interfaccia sono collegati: selettore "Claude locale" / "Codex locale" nel pannello
della chat nuova (`app/web/ia-locali.mjs`, `SceltaLocale`) e pagina Impostazioni -> IA locale
(`ImpostazioniLocali`). I test non caricano GPU o modelli; il collaudo reale si fa con
`Sistema/ia-locali/collaudo-studio.py` del second brain.

Aggiunte rispetto alla prima base: catalogo dinamico dei GGUF nelle `cartelle_modelli`,
`richiedi_chat_locale` (avvia il motore se serve ed emette `chat-locale-pronta`), stato `riposo`
(riposo nativo di llama.cpp con `--sleep-idle-seconds`: scarica pesi e contesto anche a chat
aperta, la richiesta successiva li ricarica), limiti configurabili (cache, checkpoint, cache KV,
layer GPU, mmap) e `ia_locale_scegli_percorso`.

## Architettura

- Un `GestoreLocale` per l'app (`app/ia_locali.py`), un solo processo llama.cpp su loopback.
- La costruzione dell'app non avvia il server. Avvio e cambio modello sono azioni esplicite.
- Il processo parte in background con stdin/stdout/stderr espliciti. Solo il processo
  creato da questo gestore viene arrestato; una porta occupata da altri produce un errore.
- Claude Code e Codex restano i client reali nei terminali ConPTY gia presenti.
- Codex locale usa una propria `CODEX_HOME`, senza cambiare il profilo cloud.
- Claude locale riceve un ambiente per processo e un file settings dedicato. Il ponte
  Anthropic dell'app riordina i messaggi system/developer e mantiene lo streaming.
- Comandi e skill di Claude Code sono abilitati, incluse le fonti user/project/local
  e gli strumenti per file, terminale, Skill e Agent. Il catalogo delle
  skill ha un budget di 3000 caratteri; il testo completo si carica all'invocazione.
- `mcp_claude=false` esclude i server MCP configurati senza disabilitare skill o
  comandi. L'opzione nella pagina IA locale li riabilita dalla riapertura della chat.
  Gli hook automatici restano disattivati per evitare il worker cloud degli appunti.
  Servizi ospitati, browser e skill con dipendenze esterne richiedono comunque i loro
  strumenti e account: un modello locale non li sostituisce automaticamente.
- `strumenti_estesi_claude=false` evita di caricare tutti i tool nativi del client:
  il profilo completo nella prova utente occupava 34k token di soli strumenti.
  Il profilo mirato misurato sul server Qwen occupa circa 15120 token iniziali
  (istruzioni, memoria, skill e strumenti compresi). I comandi slash rimangono attivi.
  Abilitare gli strumenti estesi richiede nuovo margine di contesto; con MCP attivo
  viene incluso anche ToolSearch. Il dato iniziale non include la cronologia esistente.
- I percorsi di ogni GGUF sono indipendenti: principale su SSD e alternative su HDD
  sono possibili senza spostare file automaticamente. Nessun percorso personale nel codice.

## API pywebview

Tutte restituiscono dati JSON; gli errori applicativi hanno la forma `{errore: messaggio}`.

| Metodo | Contratto |
|---|---|
| `ia_locale_catalogo()` | configurazione, modelli e disponibilita; capacita non ancora collegate indicate come tali |
| `ia_locale_configura(configurazione)` | salva eseguibile, porta, catalogo e inattivita; vietato con server attivo |
| `ia_locale_stato()` | stato, PID, modello, contesto, DFlash, visione, client e URL |
| `ia_locale_avvia(modello, contesto=8192, dflash=true, visione=false)` | avvia e restituisce subito lo stato di caricamento; nessun cambio implicito di profilo |
| `ia_locale_arresta(forza=false)` | ferma il processo posseduto; con chat aperte richiede `forza=true` |
| `apri_chat_locale(assistente='claude', cartella=null, prompt=null, titolo=null, sessione=null)` | apre il client solo se il motore e pronto; assistenti ammessi: claude, codex |

Evento **`ia-locale`**: stesso payload di `ia_locale_stato()`. Stati: `spento`,
`caricamento`, `pronto`, `errore`. In caso di errore sono disponibili messaggio e log.
Le schede e le chat aggiungono il campo `locale`, con il profilo di origine.

Configurazione in `<cache dell'app>/ia-locali/config.json`:

```json
{
  "eseguibile": "C:/strumenti/llama/llama-server.exe",
  "porta": 8087,
  "inattivita_secondi": 300,
  "modelli": {
    "principale": {
      "nome": "Modello principale",
      "file": "C:/modelli/principale.gguf",
      "draft": "D:/modelli/draft.gguf",
      "proiettore": "D:/modelli/mmproj.gguf"
    }
  }
}
```

Il catalogo non scarica ne esegue file. All'avvio si verificano i percorsi richiesti;
il proiettore e necessario solo per `visione=true`, il draft solo per `dflash=true`.

## Memoria e ciclo di vita

- Un solo slot, cache conversazioni fino a 512 MiB e al massimo due checkpoint.
- Questo **non e un limite alla RAM totale**: restano mapping dei pesi, buffer e memoria
  dei client. Il contesto usa altra VRAM. Un SSD velocizza il caricamento, non riduce
  automaticamente la RAM necessaria.
- Dopo cinque minuti senza client locali, il server si arresta. Una chat aperta impedisce
  lo scaricamento automatico; il comando esplicito di arresto rimane disponibile.
- L'uscita dall'app chiude prima i terminali, poi il modello e il ponte.
- Un errore del backend non fa ripiegare il client su un modello cloud.

## Conversazioni e salvataggi

- Le sessioni locali conservano assistente e profilo in `ia-locali/sessioni.json`.
  La ripresa mantiene modello, assistente e visione originali, adotta la preferenza
  attuale DFlash e gli aumenti di contesto. Non riduce mai il contesto storico.
  Il profilo viene registrato dopo l'apertura del terminale; un altro client con
  profilo diverso continua a impedire il cambio. Riaprire le chat dopo le modifiche.
- Default delle nuove installazioni: 32768 token, DFlash spento, cache KV q8_0.
  `compattazione_automatica=false` disabilita l'auto-compattazione solo per Claude
  locale (`DISABLE_AUTO_COMPACT=1`), conservando `/compact` manuale. Al limite serve
  compattare o aprire una nuova chat: disattivare l'automatismo non aumenta il contesto.
  L'opzione in Impostazioni -> IA locale vale dalla riapertura del client.
- Il ripristino Codex con `--no-daemon` mantiene anche l'ambiente locale e CODEX_HOME.
- Le sessioni Codex locali vengono lette anche dal loro archivio separato.
- La generazione automatica dei titoli e il worker cloud degli appunti non vengono
  lanciati per queste chat. Il titolo richiesto esplicitamente usa il backend locale.
- Salvataggio manuale e automatico alla chiusura della scheda usano un worker Python
  locale (`app/appunti_locali.py`), il client originale e lo stesso modello locale.
  L'automatico rispetta `appunti_auto` e la soglia; il manuale funziona anche se spento.
  Nessun worker cloud, nemmeno se la preferenza globale degli appunti indica un cloud.
- Il worker estrae messaggi e risposte, escludendo output degli strumenti, in uno
  snapshot limitato a 35000 caratteri (con avviso se tagliato). Lavora in una nuova
  esecuzione, senza riprendere la chat eventualmente piena. Per Claude gli strumenti
  del worker sono Read/Edit/Write/Glob/Grep; per Codex il profilo e workspace-write.
- I segni `in-corso`, `salvata`, `errore` aggiornano lo stato dell'interfaccia. Successo
  solo con uscita 0 e conferma finale `SB_NOTES_OK`; errori/timeout rimangono riprovabili.
  Log e snapshot privati in `<cache>/salvataggi-locali/<id>/`. I worker locali sono
  serializzati e trattengono il client del motore fino al completamento.
- Il salvataggio locale richiede che SBS rimanga in esecuzione: uscire completamente
  o forzare l'arresto del motore interrompe il servizio. Chiudere la finestra in tray
  non termina SBS. La sincronizzazione Git continua a essere gestita dall'app.

## Funzioni successive

1. Ricerca web e lettura pagine tramite strumenti del client: CPU/RAM e rete;
   il testo recuperato aumenta anche il contesto elaborato dal modello.
2. Browser controllato: soprattutto RAM, con eventuale VRAM per accelerazione grafica.
3. Immagini: proiettore visivo, buffer e token immagine; collaudare il margine con DFlash
   e prevedere un profilo senza draft se serve liberare VRAM.
4. Contesti maggiori: misurare pesi, cache KV, stato ricorrente, buffer e memoria del
   desktop sul modello e sull'hardware effettivi prima di scegliere un limite.

## Velocita

Il footer distingue lettura del prompt (`in`) e generazione (`out`). Sono i tempi
del motore dell'ultima richiesta completata, non i token visibili divisi per il tempo
totale dell'agente. Avvio, ricarica dopo il riposo, prompt iniziale, strumenti e
compattazione aumentano l'attesa. Il motore e condiviso: anche richieste di altre chat
o titoli espliciti possono aggiornare il dato. Il confronto DFlash richiede stesso
modello, prompt e contesto: l'accettazione del drafter cambia con il contenuto.

La disposizione dei controlli, le etichette e il flusso visuale si decidono con l'utente.
