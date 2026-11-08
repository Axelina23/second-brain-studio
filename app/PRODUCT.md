# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

(Desktop Windows: pagine HTML/CSS/JS dentro una finestra pywebview/WebView2, impacchettata come .exe. Versione Mac prevista più avanti.)

## Stack

delegated: Python 3.14 + pywebview (WebView2) per la finestra, pywinpty + websockets per il terminale, xterm.js per disegnarlo, Preact + htm senza build step per l'interfaccia, PyInstaller per l'eseguibile. Scelto perché riusa la logica Python del motore (`motore/`) e pesa poco anche su un portatile modesto (i3, 8 GB); Electron scartato per il peso.

## Users

Chi usa Claude Code ogni giorno e tiene un second brain di file Markdown: studenti, sviluppatori, chi lavora in proprio. Spesso su più PC Windows (un fisso e un portatile) e in futuro un Mac. Apre l'app quasi sempre per riprendere una chat di Claude Code o iniziarne una nuova, e per vedere a colpo d'occhio cosa è cambiato o rimasto indietro.

## Product Purpose

Una casa per il second brain: in una finestra sola vede appunti, avvisi e stato, e lavora con Claude Code (il CLI vero, con il suo abbonamento, niente API key) in un terminale incorporato. Successo = apre l'app, riconosce subito la chat da riprendere, non perde più chat chiuse senza salvare gli appunti, e legge o corregge un appunto senza aprire altri programmi.

## Positioning

Non è un'app di note né un client di chat: è il cruscotto di un second brain gestito da Claude Code. Gli appunti li scrive soprattutto Claude; l'app li mostra, segnala quelli vecchi e le chat non salvate, e porta dentro il terminale vero di Claude Code con mod, hook e pannello.

## Operating Context

- Cartella del second brain: scelta al primo avvio (proposta `~/Second Brain`), sincronizzata con GitHub dall'app e dagli hook di Claude Code (pull a inizio sessione, push a fine).
- Struttura tipica: `Io/`, `Progetti/<Nome>/CLAUDE.md`, aree scelte nel questionario (studio, lavoro, vita…), `Sistema/`, `Archivio/Registro.md`, `Inbox/`, `INDICE.md`.
- Chat di Claude Code: trascrizioni `.jsonl` in `~/.claude/projects/<cartella>/`; parole chiave generate da Haiku; segni di salvataggio in `~/.claude/second-brain/segni/`.
- Comandi ricorrenti: "briefing", "revisione", "smista l'inbox".
- Scadenze estratte dai file di stato degli appunti.
- Spesso ci sono giochi o altre app a schermo intero aperti in parallelo (da qui il silenzio delle notifiche).

## Capabilities and Constraints

- Funzioni confermate (dalla pagina iniziale in Textual): semaforo di sincronizzazione, riga "oggi" (eventi + scadenze), elenco chat con parole chiave e stato di salvataggio, nuova chat, ripresa, briefing/revisione/smista inbox, nota al volo in `Inbox/` con nome scelto da Haiku, pagina Appunti con età dei file, chat chiuse senza salvare con proposta di salvarle.
- Confermato il 2026-11-07: appunti leggibili formattati e modificabili al volo nell'app (le modifiche grosse le fa Claude).
- Confermato il 2026-11-07: chiudendo la finestra l'app resta nell'area di notifica, manda notifiche di Windows e parte con Windows.
- Terminale: deve far girare `claude.exe` con fedeltà piena (colori, Shift+Invio, mod con pannello laterale, statusline).
- Leggerezza: deve stare comoda sul portatile da 8 GB.
- Mai scrivere segreti negli appunti.

## Brand Commitments

Nome: "Second Brain Studio". Lingua dell'interfaccia: italiano e inglese. Il terminale usa JetBrains Mono Nerd Font (installato sui PC); nell'app i suoi colori sono intonati allo smalto del Chiostro, mentre WezTerm resta in Catppuccin Mocha.

## Evidence on Hand

Dati inventati nel banco di prova (`app/web/prova.html`): persone, progetti e chat di esempio. Icona dell'app: "Sinapsi" (`app/web/icona.svg`).

## Product Principles

1. Riprendere il lavoro in un gesto: la chat giusta deve essere riconoscibile e a un clic.
2. Niente si perde in silenzio: chat non salvate, appunti fermi, sync rotta si vedono subito.
3. Claude Code resta il vero motore: l'app lo ospita, non lo imita.
4. Calma: è uno strumento che si apre ogni giorno, non deve gridare.
