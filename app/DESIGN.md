---
name: Second Brain
description: Il chiostro di Santa Chiara di notte, guscio da lavoro per il second brain e Claude Code
colors:
  notte: "#0e1a22"
  notte-2: "#0b151c"
  pannello: "#13242f"
  pannello-2: "#182c39"
  pannello-3: "#1d3443"
  cucitura: "#22394a"
  cucitura-2: "#2c4659"
  cucitura-viva: "#3b5a70"
  term: "#081016"
  cobalto: "#1f4fa3"
  cobalto-chiaro: "#4f7fd0"
  limone: "#f2c94c"
  limone-acceso: "#f7d76a"
  limone-scuro: "#d9ad2b"
  verderame: "#6fa287"
  verderame-chiaro: "#8cc29a"
  terracotta: "#c8643b"
  terracotta-chiaro: "#e08460"
  terracotta-cupa: "#7a3a22"
  errore-fondo: "#3a1f14"
  errore-testo: "#f3c3ad"
  testo: "#f1ece0"
  testo-2: "#b9c4c8"
  muto: "#8ea0a8"
  inchiostro: "#1a1606"
typography:
  headline:
    fontFamily: "Figtree, Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "28px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  headline-piccolo:
    fontFamily: "Figtree, Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "24px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Figtree, Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "17px"
    fontWeight: 650
    lineHeight: 1.3
  title-blocco:
    fontFamily: "Figtree, Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 650
    lineHeight: 1.5
  body:
    fontFamily: "Figtree, Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  body-lettura:
    fontFamily: "Figtree, Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Figtree, Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "12.5px"
    fontWeight: 500
    lineHeight: 1.4
  mono:
    fontFamily: "JetBrainsMono Nerd Font, JetBrains Mono, Cascadia Mono, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
  mono-terminale:
    fontFamily: "JetBrainsMono Nerd Font, JetBrains Mono, Cascadia Mono, Consolas, monospace"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.15
rounded:
  targhetta: "4px"
  piastrella: "5px"
  controllo: "6px"
  scheda: "8px"
  dialogo: "10px"
  pillola: "99px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "22px"
  xl: "36px"
components:
  button-primario:
    backgroundColor: "{colors.limone}"
    textColor: "{colors.inchiostro}"
    rounded: "{rounded.controllo}"
    padding: "0 14px"
    height: "36px"
  button-primario-hover:
    backgroundColor: "{colors.limone-acceso}"
  button-secondario:
    backgroundColor: "{colors.pannello}"
    textColor: "{colors.testo}"
    rounded: "{rounded.controllo}"
    padding: "0 14px"
    height: "36px"
  button-secondario-hover:
    backgroundColor: "{colors.pannello-2}"
  button-fantasma:
    backgroundColor: "transparent"
    textColor: "{colors.testo-2}"
    rounded: "{rounded.controllo}"
    padding: "0 14px"
    height: "36px"
  button-piccolo:
    rounded: "{rounded.controllo}"
    padding: "0 11px"
    height: "28px"
  campo:
    backgroundColor: "{colors.pannello}"
    textColor: "{colors.testo}"
    rounded: "{rounded.controllo}"
    padding: "0 14px"
    height: "40px"
  nav-voce:
    backgroundColor: "transparent"
    textColor: "{colors.testo-2}"
    rounded: "{rounded.controllo}"
    padding: "0 10px"
    height: "36px"
  nav-voce-attiva:
    backgroundColor: "{colors.cobalto}"
    textColor: "#ffffff"
  scheda:
    backgroundColor: "{colors.pannello}"
    rounded: "{rounded.scheda}"
  timbro-salvata:
    textColor: "{colors.verderame-chiaro}"
    rounded: "{rounded.pillola}"
    padding: "3px 9px 3px 8px"
  timbro-non-salvata:
    textColor: "{colors.terracotta-chiaro}"
    rounded: "{rounded.pillola}"
    padding: "3px 9px 3px 8px"
  piastrella:
    textColor: "#ffffff"
    rounded: "{rounded.piastrella}"
    width: "104px"
  linguetta-attiva:
    backgroundColor: "{colors.term}"
    textColor: "{colors.testo}"
    height: "40px"
  barra-stato:
    backgroundColor: "{colors.notte-2}"
    textColor: "{colors.testo-2}"
    typography: "{typography.mono}"
    height: "28px"
---

# Design System: Second Brain

## Overview

**Creative North Star: "Il chiostro di Santa Chiara di notte"**

Il second brain è il chiostro delle Clarisse visto dopo il tramonto: un fondo di smalto scuro e calmo, pannelli appena sollevati divisi da cuciture sottili, e in mezzo la panchina di maioliche, dove ogni progetto è una piastrella dipinta. Lo smalto di una piastrella resta vivo finché i suoi appunti sono freschi, poi sbiadisce e si crepa man mano che invecchiano. È l'unico punto del mondo dove il colore è abbondante; tutto il resto è guscio di lavoro, denso e silenzioso, perché l'app si apre ogni giorno e non deve gridare.

La densità è da strumento: righe da 32 a 50px, testo base a 14px, numeri e orari in mono. Il colore porta significato e mai decorazione: cobalto vuol dire "sei qui", limone vuol dire "agisci" o "attenzione", verderame vuol dire "salvato, fresco", terracotta vuol dire "non salvato, fermo". Il terminale di Claude Code vive in una colonna a destra, più scura del fondo, come una nicchia nel muro del chiostro.

Rifiuto confermato: il cruscotto amministrativo grigio con un solo colore d'accento.

**Key Characteristics:**
- Fondo smalto notte con tre livelli di pannello e cuciture da 1px al posto delle ombre.
- Colori di stato fissi: verderame = salvato/fresco, terracotta = non salvato/fermo, limone = in corso/da fare.
- Piastrelle di maiolica con emblema dipinto per progetto; l'età degli appunti agisce solo sullo smalto.
- Figtree per l'interfaccia, JetBrains Mono per terminale, orari, età e barra di stato.
- Icone disegnate a mano in SVG a tratto 1.6, mai glifi o font di icone.

## Colors

Una notte di smalto blu-verde con quattro colori d'invetriatura napoletana, ognuno legato a un solo significato.

### Primary
- **Limone di chiostro** (`limone`): l'azione principale della schermata ("Nuova chat", "Smista l'inbox"), con testo `inchiostro` sopra. Fa anche da segnale d'attenzione: anello di focus, cursore del testo e del terminale, bordo del campo attivo, timbro "in corso", pallino di sincronizzazione che pulsa, arco evidenziato sulla mappa. Al passaggio del mouse diventa `limone-acceso`; `limone-scuro` resta per i punti degli elenchi nel testo letto.

### Secondary
- **Cobalto di Capodimonte** (`cobalto`): la selezione e la navigazione. Voce attiva della barra laterale, filtro attivo, maniglia del terminale al passaggio del mouse. Testo bianco puro sopra. `cobalto-chiaro` segna la linguetta attiva del terminale (filo di 2px in alto) e i link.

### Tertiary
- **Verderame** (`verderame`, `verderame-chiaro`): salvato e fresco. Pallino "Sincronizzato", timbro "salvata" (testo `verderame-chiaro`, bordo `#3e6b55`).
- **Terracotta** (`terracotta`, `terracotta-chiaro`, `terracotta-cupa`): non salvato e fermo. Contatore dell'Inbox, timbro "non salvata", età della piastrella più vecchia, bottone di pericolo. Gli errori usano `errore-fondo` con bordo `terracotta-cupa` e testo `errore-testo`.

### Neutral
- **Notte** (`notte`): fondo della pagina principale.
- **Notte profonda** (`notte-2`): barra laterale, striscia delle linguette, barra di stato: le cornici del guscio.
- **Pannello, Pannello 2, Pannello 3** (`pannello`, `pannello-2`, `pannello-3`): tre gradini di sollevamento. Schede e bottoni a riposo, poi hover e selezione, poi avvisi a comparsa.
- **Cucitura** (`cucitura`, `cucitura-2`, `cucitura-viva`): le fughe tra le piastrelle. 1px per dividere righe e colonne, `cucitura-2` per i bordi dei controlli, `cucitura-viva` per il bordo al passaggio del mouse.
- **Nicchia del terminale** (`term`): fondo del terminale, dell'editor degli appunti e dei blocchi di codice. Il punto più scuro dell'app.
- **Bianco di smalto** (`testo`): testo principale, caldo e non bianco puro. `testo-2` per il secondario, `muto` per etichette e date.

### Smalti delle piastrelle
Ogni progetto ha un suo smalto di quattro colori (fondo, tinta, seconda, contorno), definito in `SMALTI` dentro `web/icone.mjs`. Le tinte vengono dalla stessa tavolozza del mondo (cobalto, limone, terracotta, bianco di smalto, verderame chiaro) su fondi profondi propri del progetto: verde bottiglia, prugna, petrolio, vinaccia. Un progetto nuovo riceve uno smalto nuovo in quella tabella; quelli senza corrispondenza ricadono sulla stella a otto punte su `#245a7a`.

### Named Rules
**La regola del significato unico.** Ogni colore d'invetriatura dice una cosa sola. Il verderame non decora mai e la terracotta non diventa mai un accento: se qualcosa è terracotta, chi la usa deve intervenire.

**La regola dello smalto, non del testo.** L'età degli appunti sbiadisce il fondo, toglie saturazione all'emblema e fa comparire le crepe, ma non tocca mai il nome del progetto né la sua età, che restano bianchi e leggibili su ogni piastrella.

## Typography

**Display Font:** Figtree (con Segoe UI Variable Text, Segoe UI)
**Body Font:** Figtree (con Segoe UI Variable Text, Segoe UI)
**Label/Mono Font:** JetBrains Mono Nerd Font (con JetBrains Mono, Cascadia Mono, Consolas)

**Character:** Figtree a peso variabile, inclusa nell'app, dà un'interfaccia morbida e geometrica che regge bene la densità; il mono porta tutto ciò che è numero, orario o macchina, così l'occhio distingue a colpo d'occhio cosa è tuo e cosa è del sistema.

### Hierarchy
- **Headline** (650, 28px, 1.2, -0.015em): il saluto della pagina Oggi. 24px per i titoli delle altre pagine (Mappa, Inbox) e 26px per il titolo di un appunto aperto.
- **Title** (650, 17px): titoli di dialoghi e del terminale vuoto. 18px e 15px per i sottotitoli degli appunti.
- **Title di blocco** (650, 14px): "Avvisi", "Progetti", "Chat da riprendere", sempre seguito da un dettaglio a 12.5px in `muto`.
- **Body** (400, 14px, 1.5): tutta l'interfaccia. Il testo letto degli appunti passa a 1.65 di interlinea e si ferma a 74ch.
- **Label** (500–600, 12–12.5px): etichette della striscia, date, gruppi di giorno, sezioni della barra laterale. Mai maiuscolo, mai spaziato.
- **Mono** (400–500, 11.5–12px): orari delle chat, età delle piastrelle e degli appunti, percorsi, barra di stato. Il terminale usa 13.5px con interlinea 1.15.

### Named Rules
**La regola dei pesi intermedi.** Figtree è variabile e il sistema usa i gradini intermedi: 450 per il testo attenuato, 550 per i titoli delle righe, 650 per titoli e azione primaria. Il 700 resta al marchio, al contatore e ai nodi principali della mappa.

**La regola della macchina in mono.** Se un valore viene dal sistema (ora, giorni, ramo git, file da caricare), è in mono. Le parole scritte per chi la usa sono in Figtree.

## Layout

Il guscio è una griglia fissa a quattro colonne e due righe: barra laterale da 224px, area principale fluida, maniglia da 6px, colonna del terminale larga `clamp(460px, 36vw, 680px)` e ridimensionabile; sotto, una barra di stato da 28px su tutta la larghezza. Il terminale può allargarsi a tutto lo spazio (l'area principale si nasconde) o chiudersi del tutto.

La pagina principale ha un margine di 28px sopra e 36px ai lati, larghezza massima 1380px. La pagina Oggi mette in testa data e saluto con le azioni a destra, poi la striscia di tre colonne (calendario, prossima scadenza, poi), poi una griglia 0.85fr / 1.15fr: a sinistra Avvisi sopra Progetti, a destra Chat da riprendere con la nota al volo. Il ritmo verticale tra i blocchi è 22px; dentro le schede le righe sono divise da cuciture, non da spazio.

La risposta ai cambi di larghezza è per contenitore, non per finestra: sotto gli 860px dell'area principale la griglia diventa una colonna sola e la panchina si stringe su una riga sola con tutte le piastrelle; sotto i 760px l'elenco degli appunti scende a 220px.

## Elevation & Depth

Il mondo è piatto e fatto a strati di tono: la profondità viene dai tre gradini di pannello e dalle cuciture da 1px, non dalle ombre. Le ombre esistono solo per ciò che galleggia sopra il guscio (avvisi a comparsa, dialoghi, il riquadro "chat chiusa senza salvare" sopra il terminale) e per le piastrelle, che hanno un loro rilievo di ceramica.

### Shadow Vocabulary
- **Galleggiante** (`box-shadow: 0 10px 30px -12px rgba(0,0,0,.55), 0 2px 6px -2px rgba(0,0,0,.35)`): avvisi a comparsa, dialoghi, riquadro di fine chat.
- **Piastrella a riposo** (`box-shadow: inset 0 0 0 1px rgba(255,255,255,.09), 0 1px 0 rgba(0,0,0,.45)`): bordo di smalto interno e un filo di spessore sotto.
- **Piastrella sollevata** (`box-shadow: inset 0 0 0 1px rgba(255,255,255,.16), 0 10px 22px -10px rgba(0,0,0,.7)`): al passaggio del mouse, insieme a uno spostamento di 2px verso l'alto.

### Named Rules
**La regola delle fughe.** Le schede appoggiate sul fondo non hanno ombra: hanno un bordo `cucitura` da 1px. L'ombra spetta solo a ciò che sta sopra il guscio.

## Shapes

Angoli morbidi e piccoli, coerenti con la ceramica: 4px per targhette, tasti icona interni e codice; 5px per le piastrelle; 6px per bottoni, campi, voci di navigazione e righe; 8px per schede, striscia, editor e avvisi; 10px per i dialoghi; pillola piena solo per i timbri di stato e i contatori. Tutti i bordi sono da 1px; l'unica linea più spessa è il filo cobalto da 2px sopra la linguetta attiva del terminale. Le piastrelle sono quadrate (rapporto 1) e portano un riflesso di smalto in alto a sinistra e un'ombra in basso a destra dipinti con gradienti.

## Components

### Buttons
Compatti e piani, con un solo bottone giallo per schermata.
- **Shape:** angoli da 6px, altezza 36px (28px nella variante piccola).
- **Primario:** fondo `limone`, testo `inchiostro`, peso 650. Al passaggio del mouse `limone-acceso`.
- **Secondario:** fondo `pannello`, bordo `cucitura-2`, testo `testo`, peso 500, icona a tratto a sinistra. Al passaggio del mouse fondo `pannello-2` e bordo `cucitura-viva`; alla pressione scende di 1px.
- **Fantasma:** senza fondo né bordo, testo `testo-2`; si accende su `pannello` al passaggio del mouse. Usato per le azioni secondarie dentro le righe ("Apri").
- **Pericolo:** come il secondario con bordo `terracotta-cupa` e testo `terracotta-chiaro`.
- **Focus:** anello `limone` da 2px staccato di 2px, su tutti gli elementi interattivi.

### Chips
- **Timbri di stato:** pillole con bordo da 1px e testo colorato, senza fondo pieno. "salvata" in verderame, "non salvata" in terracotta, "in corso" e "aperta" in limone, "breve" in `muto`.
- **Contatore:** pillola piena `terracotta` con cifra bianca a 11px, nella barra laterale. Sulla voce attiva diventa bianco al 22%.
- **Filtri:** gruppo segmentato su `pannello` con bordo `cucitura`; il segmento attivo è `cobalto` con testo bianco.

### Cards / Containers
- **Corner Style:** 8px.
- **Background:** `pannello`.
- **Shadow Strategy:** nessuna, vedi La regola delle fughe.
- **Border:** 1px `cucitura`, e le righe interne divise da una cucitura in alto.
- **Internal Padding:** 8–14px per le righe (avvisi alti almeno 48px, chat almeno 50px), 14–16px per le voci dell'Inbox.

### Inputs / Fields
- **Style:** fondo `pannello`, bordo 1px `cucitura-2`, angoli 6px, altezza 40px (36px nei filtri), segnaposto in `muto`, cursore `limone`.
- **Focus:** il bordo diventa `limone` e il fondo sale a `pannello-2`. L'editor degli appunti usa il fondo `term`, il testo mono a 13.5px e lo stesso focus limone.

### Navigation
- **Barra laterale:** fondo `notte-2` con cucitura a destra. In alto il marchio (piastrella cobalto con quarto di limone e foglia verderame) e il nome; poi le cinque voci con icona a tratto, alte 36px, testo `testo-2` a peso 500. Hover su `pannello`, voce attiva piena `cobalto` con testo bianco. Sotto, "Chat aperte" a 12px in `muto` con le chat in righe da 32px; in fondo, sopra una cucitura, sincronizzazione e dispositivo con pallino di stato.
- **Linguette del terminale:** striscia alta 40px su `notte-2`; ogni linguetta in `muto` con cucitura a destra; quella attiva prende il fondo `term`, testo `testo` e il filo `cobalto-chiaro` in alto.
- **Barra di stato:** 28px, `notte-2`, tutto in mono 12px `testo-2`; il lavoro in corso è in `limone`.

### Piastrella di maiolica (componente firma)
La panchina dei progetti: griglia di quadrati da almeno 104px con 10px di fuga. Ogni piastrella ha il fondo del suo smalto, l'emblema dipinto al 44% della larghezza in alto, il nome del progetto in bianco a 13.5px peso 650 e l'età in mono 11.5px su una targhetta scura. Tre gradini d'età: sbiadito 22%, 48%, 74% verso il grigio `#4e5a62`, con crepe a opacità 0.25, 0.5, 0.85 e saturazione dell'emblema in calo; al terzo gradino la targhetta dell'età diventa `terracotta`. All'apertura ogni piastrella nasce fresca e invecchia fino al suo stato in 1.4s: è l'unico momento decorativo animato del mondo.

### Mappa
Grafo degli appunti su fondo `notte`: nodi pieni colorati per area (Io in limone, Università in terracotta chiaro, Progetti in cobalto chiaro, Vita in verderame chiaro, Sistema `#7cc4c4`, Generali in bianco di smalto), nodi d'area più grandi con anello, appunti fermi da oltre due settimane come cerchi vuoti. Archi da 1.2px in `cucitura-2`, accesi in limone al passaggio del mouse.

### Terminale
xterm.js su `term` con una tavolozza propria intonata al mondo (cursore limone, selezione cobalto al 40%, verde verderame chiaro, giallo limone); la tabella completa è `TEMA` in `web/terminale.mjs`. Quando una chat si chiude senza salvare, compare sopra il terminale un riquadro galleggiante su `pannello-2` con il bottone "Salva appunti".

## Do's and Don'ts

### Do:
- **Do** tenere un solo bottone `limone` per schermata: l'azione principale e basta.
- **Do** usare verderame per salvato/fresco e terracotta per non salvato/fermo, sempre, in timbri, pallini, contatori e targhette.
- **Do** separare righe e colonne con cuciture da 1px (`cucitura`) e appoggiare le schede sul fondo senza ombra.
- **Do** scrivere orari, età, percorsi e stato della macchina in mono; il resto in Figtree.
- **Do** disegnare ogni nuova icona come SVG a tratto 1.6 con estremi arrotondati in `currentColor`, e ogni nuovo progetto come emblema pieno con il suo smalto di quattro colori.
- **Do** far agire l'età solo sullo smalto della piastrella (fondo, emblema, crepe), lasciando nome ed età bianchi e leggibili.
- **Do** rispettare `prefers-reduced-motion`: tutte le animazioni e transizioni si spengono.

### Don't:
- **Don't** costruire il cruscotto amministrativo grigio con un solo colore d'accento: è il rifiuto di fondo di questo mondo.
- **Don't** usare cobalto per un'azione o limone per una selezione: cobalto dice dove sei, limone dice cosa fare.
- **Don't** usare il bianco puro per il testo corrente: il testo è `testo`, caldo; il bianco puro resta per il testo su cobalto e sulle piastrelle.
- **Don't** aggiungere animazioni decorative oltre all'invecchiamento delle piastrelle: le altre (entrata della pagina, pallino che pulsa, caricamento) sono funzionali e brevi.
- **Don't** mettere etichette in maiuscolo spaziato sopra i titoli: le sezioni si nominano con il titolo di blocco e un dettaglio in `muto`.
