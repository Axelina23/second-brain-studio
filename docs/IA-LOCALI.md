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
  La ripresa richiede lo stesso profilo e non torna al provider cloud.
- Le sessioni Codex locali vengono lette anche dal loro archivio separato.
- La generazione automatica dei titoli e il worker cloud degli appunti non vengono
  lanciati per queste chat. Il titolo richiesto esplicitamente usa il backend locale.
- Il salvataggio manuale riapre il client locale con la richiesta di aggiornare gli
  appunti. Gli hook Claude del profilo locale sono disattivati per evitare il worker
  cloud legacy; notifiche e automazioni locali dedicate sono un passaggio successivo.

## Funzioni successive

1. Ricerca web e lettura pagine tramite strumenti del client: CPU/RAM e rete;
   il testo recuperato aumenta anche il contesto elaborato dal modello.
2. Browser controllato: soprattutto RAM, con eventuale VRAM per accelerazione grafica.
3. Immagini: proiettore visivo, buffer e token immagine; collaudare il margine con DFlash
   e prevedere un profilo senza draft se serve liberare VRAM.
4. Contesti 16k/32k e prompt completi dei client: ammessi dal contratto ma ancora da
   misurare sulla macchina. Il primo profilo reale verificato e quello da 8k.

La disposizione dei controlli, le etichette e il flusso visuale si decidono con l'utente.
