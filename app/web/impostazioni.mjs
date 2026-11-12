// Finestra Impostazioni: sezioni a sinistra, voci a destra. Ogni modifica si salva subito
// (main.py > impostazioni.py, in ~/.claude/second-brain/config.json) e si applica dal vivo.
// applicaAspetto() mette tema, colore, dimensione del testo e animazioni sulla pagina.
import { html, useState, useEffect } from "./vendor/preact-htm.mjs";
import { Icona } from "./icone.mjs";
import { impostaLingua } from "./lingua.mjs";

export const COLORI = {
  limone: ["#f2c94c", "#1a1606", "Limone"], cobalto: ["#7aa2ec", "#08162e", "Cobalto"],
  verderame: ["#86c5a1", "#0b2016", "Verderame"], terracotta: ["#e8906a", "#2a0f04", "Terracotta"],
  viola: ["#b9a2f2", "#1b1033", "Viola"], rosa: ["#f2a3c4", "#33101f", "Rosa"],
};

// pagina Ko-fi per le donazioni: l'unico punto dove sta il nome utente
export const KOFI = "https://ko-fi.com/francescocinquegrana";

const scuroDiSistema =() => !window.matchMedia || !window.matchMedia("(prefers-color-scheme: light)").matches;

export function applicaAspetto(imp) {
  if (!imp) return;
  const r = document.documentElement;
  const tema = imp.tema === "sistema" ? (scuroDiSistema() ? "scuro" : "chiaro") : imp.tema;
  r.dataset.tema = tema;
  impostaLingua(imp.lingua);
  const [c, ink] = COLORI[imp.colore] || COLORI.limone;
  r.style.setProperty("--limone", c); r.style.setProperty("--limone-scuro", c); r.style.setProperty("--inchiostro", ink);
  document.body.style.zoom = String((imp.testo || 100) / 100);
  r.style.setProperty("--ui-zoom", String((imp.testo || 100) / 100));
  r.dataset.animazioni = imp.animazioni ? "si" : "no";
  window.sbTerminale = { testo: imp.terminale_testo, carattere: imp.terminale_carattere,
    interlinea: imp.terminale_interlinea, cursore: imp.terminale_cursore, lampeggio: imp.terminale_lampeggio,
    righe: imp.terminale_righe, fluido: imp.terminale_scorrimento_fluido, incollaDestro: imp.terminale_incolla_destro, tema: imp.terminale_tema };
  r.style.setProperty("--terminale-bg", imp.terminale_tema === "chiaro" ? "#f5f2e9" : imp.terminale_tema === "contrasto" ? "#000000" : "#081016");
  window.dispatchEvent(new Event("sb-terminale"));
}

const SEZIONI = [["generale", "Generale", "oggi"], ["aspetto", "Aspetto", "mappa"], ["notifiche", "Notifiche", "chat"],
  ["account", "Account assistenti", "briefing"], ["terminale", "Terminale", "allarga"], ["appunti", "Appunti automatici", "appunti"],
  ["agenti", "Agenti", "chat"],
  ["github", "GitHub", "github"], ["scorciatoie", "Scorciatoie", "riprendi"], ["dati", "Dati e manutenzione", "cartella"],
  ["info", "Informazioni", "esterno"]];

function Interruttore({ valore, cambia, titolo, testo, disabilitato }) {
  return html`<label class=${`imp-voce imp-int ${disabilitato ? "spenta" : ""}`}>
    <span class="imp-testi"><b>${titolo}</b>${testo && html`<span>${testo}</span>`}</span>
    <input type="checkbox" role="switch" checked=${!!valore} disabled=${disabilitato} onChange=${(e) => cambia(e.target.checked)} />
    <span class="imp-levetta" aria-hidden="true"></span></label>`;
}

function Voce({ titolo, testo, children }) {
  return html`<div class="imp-voce"><span class="imp-testi"><b>${titolo}</b>${testo && html`<span>${testo}</span>`}</span>
    <span class="imp-comando">${children}</span></div>`;
}

function SezioneAgente({ agente, imp, metti }) {
  const modi = {
    claude: [["predefinito", "Predefinita"], ["manual", "Chiedi conferma"], ["auto", "Auto"], ["acceptEdits", "Accetta modifiche"], ["plan", "Pianifica"], ["bypassPermissions", "Accesso completo, senza conferme"]],
    codex: [["predefinito", "Predefinita"], ["standard", "Standard"], ["auto", "Auto"], ["lettura", "Sola lettura"], ["completa", "Accesso completo, senza conferme"]],
    agy: [["predefinito", "Predefinita"], ["auto", "Auto"], ["accept-edits", "Accetta modifiche"], ["plan", "Pianifica"], ["completa", "Accesso completo, senza conferme"]],
  };
  const chiave = CHIAVE_MODELLO[agente];
  const scegli = (key, opzioni) => html`<select class="campo imp-sel" value=${imp[key] || "predefinito"} onChange=${(e) => metti(key, e.target.value)}>${opzioni.map(([v, n]) => html`<option value=${v}>${n}</option>`)}</select>`;
  const livelli = [["predefinito", "Predefinito"], ["low", "Basso"], ["medium", "Medio"], ["high", "Alto"], ["xhigh", "Molto alto"], ...(agente === "codex" ? [] : [["max", "Massimo"]])];
  return html`<${Voce} titolo="Modello"><${SceltaModello} agente=${agente} valore=${imp[chiave]} cambia=${(v) => metti(chiave, v)} /></${Voce}>
    <${Voce} titolo="Modalità permessi">${scegli(`modalita_${agente}`, modi[agente])}</${Voce}>
    <${Voce} titolo="Livello di ragionamento" testo="I livelli disponibili dipendono dal modello. Predefinito usa la scelta dell'assistente.">${scegli(`impegno_${agente}`, livelli)}</${Voce}>`;
}

function Segmenti({ valore, cambia, opzioni }) {
  return html`<span class="imp-seg" role="radiogroup">${opzioni.map(([v, n, off]) => html`<button role="radio" aria-checked=${valore === v}
    class=${valore === v ? "scelto" : ""} disabled=${off} title=${off ? "In arrivo" : ""} onClick=${() => cambia(v)}>${n}</button>`)}</span>`;
}

// Ogni famiglia usa l'ultima versione verificata, senza un secondo selettore.
export const FAMIGLIE_CODEX = [
  ["predefinito", "Predefinito"], ["gpt-6-luna", "Luna"], ["gpt-6.1-terra", "Terra"],
  ["gpt-6.1-sol", "Sol"], ["gpt-6-astra", "Astra"],
];

export function SceltaCodex({ valore, cambia }) {
  const scelto = FAMIGLIE_CODEX.find(([id]) => id === valore || (id !== "predefinito" && String(valore || "").endsWith("-" + id.split("-").at(-1))))?.[0] || "predefinito";
  return html`<span class="imp-seg" role="radiogroup" aria-label="Modello">${FAMIGLIE_CODEX.map(([id, nome]) => html`<button role="radio"
      aria-checked=${id === scelto} class=${id === scelto ? "scelto" : ""} onClick=${() => cambia(id)}>${nome}</button>`)}</span>`;
}

// Il modello si sceglie sempre con lo stesso selettore, per ogni assistente
// (pagina Agenti e pannello delle chat nuove); permessi e ragionamento restano a tendina.
export const MODELLI = {
  claude: [["predefinito", "Predefinito"], ["fable", "Fable"], ["opus", "Opus"], ["sonnet", "Sonnet"], ["haiku", "Haiku"]],
  agy: [["predefinito", "Predefinito"], ["gemini-4-argon-high", "Argon High"], ["gemini-4-argon-medium", "Argon Med"], ["gemini-4-argon-low", "Argon Low"], ["gemini-3.8-flash-high", "Flash High"], ["gemini-3.8-flash-low", "Flash Low"]],
};
export const CHIAVE_MODELLO = { claude: "modello_chat", codex: "modello_codex", agy: "modello_agy" };

export function SceltaModello({ agente, valore, cambia }) {
  if (agente === "codex") return html`<${SceltaCodex} valore=${valore || "predefinito"} cambia=${cambia} />`;
  const mod = valore || "predefinito";
  return html`<span class="imp-seg" role="radiogroup" aria-label="Modello">${(MODELLI[agente] || MODELLI.claude).map(([v, n]) => html`<button role="radio"
    aria-checked=${mod === v} class=${mod === v ? "scelto" : ""} onClick=${() => cambia(v)}>${n}</button>`)}</span>`;
}

// chat eliminate (tasto destro > Elimina): restano qui per un mese, poi spariscono da sole
function CestinoChat({ api, avvisa }) {
  const [d, setD] = useState(null);
  const [svuota, setSvuota] = useState(false);
  const carica = async () => { const r = await api("cestino_chat"); if (!r.errore) setD(r); };
  useEffect(() => { carica(); }, []);
  const fai = async (nome, msg, ...a) => { const r = await api(nome, ...a); if (r && r.errore) avvisa(r.errore, "errore"); else if (msg) avvisa(msg); carica(); };
  const data = (iso) => new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short" });
  if (!d) return null;
  return html`<div class="imp-voce imp-cestino"><span class="imp-testi"><b>Chat eliminate</b>
      <span>${d.cestino.length ? `Restano qui ${d.giorni} giorni, poi vengono cancellate per sempre.` : "Il cestino è vuoto. Le chat si eliminano col tasto destro nelle pagine Oggi e Chat."}</span></span>
    ${d.cestino.length > 0 && html`<span class="imp-comando">${svuota
      ? html`<button class="btn piccolo fantasma" onClick=${() => setSvuota(false)}>Annulla</button>
        <button class="btn piccolo pericolo" onClick=${() => { setSvuota(false); fai("svuota_cestino_chat", "Cestino svuotato"); }}>Sì, cancella tutto</button>`
      : html`<button class="btn piccolo" onClick=${() => setSvuota(true)}>Svuota</button>`}</span>`}
    ${d.cestino.length > 0 && html`<ul class="cestino-elenco">${d.cestino.map((c) => html`<li>
      <span class="cestino-nome"><b title=${c.etichetta}>${c.etichetta}</b><span>chat del ${data(c.ultima)} · eliminata il ${data(c.eliminata)} · ancora ${c.giorni_rimasti} g</span></span>
      <button class="btn piccolo" onClick=${() => fai("ripristina_chat", "Chat ripristinata", c.id)}>Ripristina</button>
      <button class="btn piccolo fantasma" title="Cancella per sempre" aria-label="Cancella per sempre" onClick=${() => fai("elimina_per_sempre", "Chat cancellata per sempre", c.id)}>${Icona.cestino()}</button>
    </li>`)}</ul>`}</div>`;
}

export function Impostazioni({ api, chiudi, avvisa, gh, accediGh, sincronizzaGh, aggiornaGh, cambiate, primoAvvio }) {
  const [sez, setSez] = useState(() => { const s = localStorage.getItem("impSezione"); return ["claude", "codex", "agy"].includes(s) ? "agenti" : SEZIONI.some(([k]) => k === s) ? s : "generale"; });
  const [d, setD] = useState(null);
  const [cerco, setCerco] = useState(false);
  const carica = async () => { const x = await api("impostazioni"); if (!x.errore) setD(x); };
  useEffect(() => { carica(); }, []);
  useEffect(() => { localStorage.setItem("impSezione", sez); }, [sez]);
  useEffect(() => { const f = (e) => e.key === "Escape" && chiudi(); window.addEventListener("keydown", f); return () => window.removeEventListener("keydown", f); }, []);
  if (!d) return null;
  const imp = d.impostazioni;
  const metti = async (k, v) => {
    const nuove = { ...imp, [k]: v };
    setD((x) => ({ ...x, impostazioni: nuove })); cambiate(nuove);
    const r = await api("salva_impostazioni", { [k]: v });
    if (r.errore || (r.scartate && r.scartate.length)) { avvisa("Valore non valido", "errore"); carica(); }
  };
  const azione = async (nome, ok, ...a) => { const r = await api(nome, ...a); if (r && r.errore) avvisa(r.errore, "errore"); else if (ok) avvisa(typeof ok === "function" ? ok(r) : ok); carica(); return r; };
  const acc = d.account || {};

  const corpo = {
    agenti: html`
      <${Voce} titolo="Assistente delle chat nuove" testo="Codex e Antigravity devono essere installati; usano il loro modello e il loro abbonamento.">
        <${Segmenti} valore=${imp.assistente_chat} cambia=${(v) => metti("assistente_chat", v)} opzioni=${[["claude", "Claude"], ["codex", "Codex"], ["agy", "Antigravity"]]} /></${Voce}>
      <p class="imp-nota">Si applicano alle chat nuove e alle chat riprese. Le chat già aperte mantengono la modalità in uso.</p>
      ${[["claude", "Claude"], ["codex", "Codex"], ["agy", "Antigravity"]].map(([id, nome]) => html`
        <section class="imp-agente" data-agente=${id} aria-label=${nome}><h3>${nome}</h3>
          <${SezioneAgente} agente=${id} imp=${imp} metti=${metti} /></section>`)}`,
    generale: html`
      <${Voce} titolo="Lingua" testo="Lingua dell'interfaccia. Quella delle risposte di Claude sta nelle tue Regole.">
        <${Segmenti} valore=${imp.lingua} cambia=${(v) => metti("lingua", v)} opzioni=${[["it", "Italiano"], ["en", "English"]]} /></${Voce}>
      <${Voce} titolo="Pagina all'apertura">
        <select data-traduci class="campo imp-sel" value=${imp.pagina_iniziale} onChange=${(e) => metti("pagina_iniziale", e.target.value)}>
          ${[["oggi", "Oggi"], ["chat", "Chat"], ["appunti", "Appunti"], ["mappa", "Mappa"], ["inbox", "Inbox"]].map(([v, n]) => html`<option value=${v}>${n}</option>`)}</select></${Voce}>
      <${Interruttore} titolo="Avvia con Windows" testo="Parte nascosta vicino all'orologio, pronta per notifiche e scorciatoia."
        valore=${d.avvio} disabilitato=${!d.installata} cambia=${(v) => azione("imposta_avvio", v ? "Partirà con Windows" : "Non partirà più con Windows", v)} />
      ${!d.installata && html`<p class="imp-nota">Si imposta dall'app installata.</p>`}
      <div class="imp-gruppo">Aggiornamenti</div>
      <${Interruttore} titolo="Cerca gli aggiornamenti da solo" testo="All'avvio e ogni 6 ore, dalle release su GitHub. Quando è pronto compare il pulsante in basso."
        valore=${imp.aggiornamenti_auto} cambia=${(v) => metti("aggiornamenti_auto", v)} />
      <${Interruttore} titolo="Anche le versioni di prova" testo="Arrivano prima, a volte con qualche difetto." valore=${imp.aggiornamenti_prova} cambia=${(v) => metti("aggiornamenti_prova", v)} />
      <${Voce} titolo="Versione in uso" testo=${d.versione}>
        <button class="btn piccolo" disabled=${cerco} onClick=${async () => { setCerco(true); const r = await api("cerca_aggiornamenti"); setCerco(false);
          if (r.errore) avvisa(r.errore, "errore"); else avvisa(r.nuova ? `Versione ${r.nuova} pronta: premi "Aggiornamento pronto" in basso` : "Hai già l'ultima versione"); }}>
          ${cerco ? "Cerco…" : "Cerca adesso"}</button></${Voce}>`,

    aspetto: html`
      <${Voce} titolo="Tema"><${Segmenti} valore=${imp.tema} cambia=${(v) => metti("tema", v)} opzioni=${[["scuro", "Scuro"], ["chiaro", "Chiaro"], ["sistema", "Come Windows"]]} /></${Voce}>
      <${Voce} titolo="Colore principale" testo="Pulsanti principali e selezioni.">
        <span class="imp-colori">${Object.entries(COLORI).map(([k, [c, , n]]) => html`<button class=${`imp-colore ${imp.colore === k ? "scelto" : ""}`}
          style=${`background:${c}`} title=${n} aria-label=${n} aria-pressed=${imp.colore === k} onClick=${() => metti("colore", k)}></button>`)}</span></${Voce}>
      <${Voce} titolo="Dimensione del testo" testo=${`${imp.testo}%`}>
        <input type="range" min="85" max="130" step="5" value=${imp.testo} onChange=${(e) => metti("testo", +e.target.value)} /></${Voce}>
      <${Interruttore} titolo="Animazioni" testo="Spegnile se preferisci un'interfaccia ferma." valore=${imp.animazioni} cambia=${(v) => metti("animazioni", v)} />`,

    notifiche: html`
      ${!d.avvisi && html`<div class="imp-riquadro"><b>Avvisi di Claude non collegati</b>
        <span>Per sapere quando Claude ha finito o aspetta un permesso, l'app aggiunge due avvisi alle impostazioni di Claude Code (con copia di sicurezza).</span>
        <button class="btn primario piccolo" onClick=${() => azione("collega_avvisi", "Avvisi collegati: valgono dalle prossime chat")}>Collega gli avvisi</button></div>`}
      <div class="imp-gruppo">Quando avvisarti</div>
      <${Interruttore} titolo="Claude ha finito di rispondere" testo="Con progetto, chat e un'anteprima della risposta." valore=${imp.notifica_risposta} cambia=${(v) => metti("notifica_risposta", v)} />
      <${Interruttore} titolo="Claude aspetta un tuo permesso" valore=${imp.notifica_permesso} cambia=${(v) => metti("notifica_permesso", v)} />
      <${Interruttore} titolo="Chat chiuse senza salvare gli appunti" valore=${imp.notifica_non_salvate} cambia=${(v) => metti("notifica_non_salvate", v)} />
      <${Interruttore} titolo="Scadenze vicine" valore=${imp.notifica_scadenze} cambia=${(v) => metti("notifica_scadenze", v)} />
      <${Interruttore} titolo="Note da smistare in Inbox" valore=${imp.notifica_inbox} cambia=${(v) => metti("notifica_inbox", v)} />
      <${Interruttore} titolo="Sincronizzazione ferma" valore=${imp.notifica_sync} cambia=${(v) => metti("notifica_sync", v)} />
      <div class="imp-gruppo">Come</div>
      <${Interruttore} titolo="Mostra l'anteprima della risposta" valore=${imp.anteprima} cambia=${(v) => metti("anteprima", v)} />
      <${Interruttore} titolo="Anche per le chat fuori dall'app" testo="Terminale, VS Code: ogni chat di Claude su questo PC." valore=${imp.notifica_fuori_app} cambia=${(v) => metti("notifica_fuori_app", v)} />
      <${Interruttore} titolo="Silenzio mentre giochi o presenti" testo="Niente notifiche con un'app a schermo intero." valore=${imp.silenzio_gioco} cambia=${(v) => metti("silenzio_gioco", v)} />
      <${Interruttore} titolo="Non disturbare" valore=${imp.silenzio_attivo} cambia=${(v) => metti("silenzio_attivo", v)} />
      ${imp.silenzio_attivo && html`<${Voce} titolo="Fascia oraria">
        <span class="imp-ore"><input type="time" class="campo" value=${imp.silenzio_da} onChange=${(e) => metti("silenzio_da", e.target.value)} />
        <span>–</span><input type="time" class="campo" value=${imp.silenzio_a} onChange=${(e) => metti("silenzio_a", e.target.value)} /></span></${Voce}>`}`,

    account: html`
      <div class="imp-gruppo">Claude</div>
      <div class="imp-riquadro"><b>${acc.testo || "Non collegato"}</b>
        ${acc.email && html`<span>${acc.email}${acc.organizzazione ? ` · ${acc.organizzazione}` : ""}</span>`}
        <span>L'accesso è quello di Claude Code: vale nell'app, nel terminale e in VS Code.</span>
        <button class="btn piccolo" onClick=${() => { chiudi(); api("accedi_claude_terminale"); }}>Accedi o cambia account</button></div>
      <div class="imp-gruppo">Chiave API o Bedrock/Vertex</div>
      <p class="imp-nota">Se usi una chiave API, impostala nelle variabili d'ambiente di Windows (Impostazioni di sistema → "Modifica le variabili d'ambiente per l'account" → nuova variabile <code>ANTHROPIC_API_KEY</code>). L'app la legge da sola, anche senza riavviarla. Per Amazon Bedrock o Google Vertex vale lo stesso con le loro variabili (<code>CLAUDE_CODE_USE_BEDROCK</code>, <code>CLAUDE_CODE_USE_VERTEX</code>).</p>
      <div class="imp-gruppo">Codex</div>
      <div class="imp-riquadro"><span>Accedi a Codex con il tuo account ChatGPT nel browser. L'accesso viene gestito da Codex.</span>
        <button class="btn piccolo" onClick=${async () => { const r = await api("accedi_codex"); if (r.errore) avvisa(r.errore, "errore"); else chiudi(); }}>Accedi a Codex</button></div>`,

    terminale: html`
      <div class="imp-gruppo">Disposizione</div>
      <${Voce} titolo="Posizione del terminale" testo="Automatico lo sposta sotto il contenuto quando la finestra è stretta.">
        <${Segmenti} valore=${imp.terminale_posizione || "auto"} cambia=${(v) => metti("terminale_posizione", v)} opzioni=${[["auto", "Automatico"], ["destra", "A destra"], ["sotto", "In basso"]]} /></${Voce}>
      <${Voce} titolo="Dimensioni dei pannelli" testo="Trascina i divisori per ridimensionare. Un doppio clic ripristina le proporzioni iniziali.">
        <button class="btn piccolo" onClick=${() => { ["termRatio", "termRatioH", "appuntiRatio", "appuntiRatioH", "termW"].forEach((k) => localStorage.removeItem(k)); window.dispatchEvent(new Event("resize")); }}>Ripristina dimensioni</button></${Voce}>
      <div class="imp-gruppo">Leggibilità</div>
      <${Voce} titolo="Carattere">
        <select class="campo imp-sel" value=${imp.terminale_carattere} onChange=${(e) => metti("terminale_carattere", e.target.value)}>
          ${["JetBrains Mono", "Cascadia Mono", "Consolas"].map((v) => html`<option value=${v}>${v}</option>`)}</select></${Voce}>
      <${Voce} titolo="Dimensione" testo=${`${imp.terminale_testo} pt`}>
        <input type="range" min="10" max="20" step="0.5" value=${imp.terminale_testo} onChange=${(e) => metti("terminale_testo", +e.target.value)} /></${Voce}>
      <${Voce} titolo="Interlinea" testo=${`${Number(imp.terminale_interlinea || 1.15).toFixed(2)}×`}>
        <input type="range" min="1" max="1.8" step="0.05" value=${imp.terminale_interlinea || 1.15} onChange=${(e) => metti("terminale_interlinea", +e.target.value)} /></${Voce}>
      <${Voce} titolo="Colori del terminale">
        <${Segmenti} valore=${imp.terminale_tema || "notte"} cambia=${(v) => metti("terminale_tema", v)} opzioni=${[["notte", "Notte"], ["contrasto", "Contrasto alto"], ["chiaro", "Chiaro"]]} /></${Voce}>
      <div class="imp-gruppo">Cursore</div>
      <${Voce} titolo="Forma del cursore">
        <${Segmenti} valore=${imp.terminale_cursore || "block"} cambia=${(v) => metti("terminale_cursore", v)} opzioni=${[["block", "Blocco"], ["bar", "Barra"], ["underline", "Sottolineato"]]} /></${Voce}>
      <${Interruttore} titolo="Cursore lampeggiante" valore=${imp.terminale_lampeggio !== false} cambia=${(v) => metti("terminale_lampeggio", v)} />
      <div class="imp-gruppo">Scorrimento e appunti di Windows</div>
      <${Voce} titolo="Righe conservate" testo="Quante righe precedenti puoi ritrovare scorrendo verso l'alto.">
        <select class="campo imp-sel" value=${imp.terminale_righe || 10000} onChange=${(e) => metti("terminale_righe", +e.target.value)}>
          ${[1000, 5000, 10000, 25000, 50000].map((n) => html`<option value=${n}>${n.toLocaleString()}</option>`)}</select></${Voce}>
      <${Interruttore} titolo="Scorrimento fluido" valore=${imp.terminale_scorrimento_fluido} cambia=${(v) => metti("terminale_scorrimento_fluido", v)} />
      <${Interruttore} titolo="Incolla con il tasto destro" testo="Puoi usare Ctrl+V anche quando questa opzione è disattivata." valore=${imp.terminale_incolla_destro !== false} cambia=${(v) => metti("terminale_incolla_destro", v)} />
      <p class="imp-nota">Modello, modalità e ragionamento si configurano nella pagina Agenti.</p>`,

    appunti: html`
      <${Interruttore} titolo="Aggiorna gli appunti a fine chat" testo="L'assistente riassume la chat e aggiorna Registro e file di stato in background." valore=${imp.appunti_auto} cambia=${(v) => metti("appunti_auto", v)} />
      <${Voce} titolo="Chi scrive gli appunti" testo="'Quello della chat' fa lavorare ogni assistente sulle proprie chat, senza consumare Claude.">
        <${Segmenti} valore=${imp.assistente_appunti} cambia=${(v) => metti("assistente_appunti", v)} opzioni=${[["chat", "Quello della chat"], ["claude", "Claude"], ["codex", "Codex"], ["agy", "Antigravity"]]} /></${Voce}>
      <${Voce} titolo="Modello appunti di Claude" testo="Sonnet è il più accurato, Haiku consuma meno.">
        <${Segmenti} valore=${imp.modello_appunti} cambia=${(v) => metti("modello_appunti", v)} opzioni=${[["sonnet", "Sonnet"], ["haiku", "Haiku"], ["opus", "Opus"]]} /></${Voce}>
      <${Voce} titolo="Modello appunti di Codex" testo="Predefinito = quello configurato in Codex.">
        <${SceltaCodex} valore=${imp.modello_appunti_codex} cambia=${(v) => metti("modello_appunti_codex", v)} /></${Voce}>
      <${Voce} titolo="Modello appunti di Antigravity" testo="Flash è veloce e leggero; Argon è più approfondito.">
        <${Segmenti} valore=${imp.modello_appunti_agy} cambia=${(v) => metti("modello_appunti_agy", v)} opzioni=${[["gemini-3.8-flash-high", "Flash High"], ["gemini-3.8-flash-low", "Flash Low"], ["gemini-4-argon-low", "Argon Low"], ["gemini-4-argon-medium", "Argon Med"], ["gemini-4-argon-high", "Argon High"]]} /></${Voce}>
      <${Voce} titolo="Chat troppo corte" testo=${`Sotto ${imp.soglia_kb} KB di trascrizione non si aggiornano gli appunti.`}>
        <input type="range" min="5" max="200" step="5" value=${imp.soglia_kb} onChange=${(e) => metti("soglia_kb", +e.target.value)} /></${Voce}>
      <p class="imp-nota">Valgono per gli hook installati dall'app (primo avvio). Se usi hook tuoi, restano i tuoi.</p>`,

    github: html`
      <div class="imp-riquadro"><b>${gh && gh.collegato ? `Collegato${gh.utente ? ` come @${gh.utente}` : ""}` : gh && gh.scaduto ? "Accesso a GitHub scaduto: ricollegalo" : "GitHub non collegato"}</b>
        <span>${gh && gh.repo ? `Repository: ${gh.repo}` : "Nessun repository per il second brain."}</span>
        <span class="imp-bottoni">${gh && gh.collegato
          ? html`<button class="btn piccolo" onClick=${sincronizzaGh} disabled=${!gh.repo}>Sincronizza ora</button>
              ${gh.repo && html`<button class="btn piccolo fantasma" onClick=${() => api("apri_github", `https://github.com/${gh.repo}`)}>Apri su GitHub</button>`}
              <button class="btn piccolo pericolo" onClick=${async () => { await api("github_scollega"); aggiornaGh(); avvisa("GitHub scollegato"); }}>Scollega</button>`
          : html`<button class="btn piccolo primario" onClick=${() => { chiudi(); accediGh(); }}>Collega GitHub</button>`}</span></div>
      <${Voce} titolo="Sincronizzazione automatica" testo="Salva e carica il second brain da sola, anche senza Claude.">
        <${Segmenti} valore=${imp.sync_minuti} cambia=${(v) => metti("sync_minuti", v)} opzioni=${[[0, "Spenta"], [15, "15 min"], [30, "30 min"], [60, "1 ora"]]} /></${Voce}>
      <${Interruttore} titolo="Chat degli altri PC" testo="Ogni PC pubblica nel repository (ramo stato/<PC>) l'elenco delle sue chat: parole chiave, orari e stato, mai i messaggi. Nella pagina Chat vedi quelle degli altri PC, quasi in tempo reale."
        valore=${imp.chat_altri_pc} cambia=${(v) => metti("chat_altri_pc", v)} />`,

    scorciatoie: html`
      <${Interruttore} titolo="Ctrl+Alt+Spazio da qualunque programma" testo="Mostra Second Brain Studio anche se è nascosta." valore=${imp.scorciatoia_globale} cambia=${(v) => metti("scorciatoia_globale", v)} />
      <div class="imp-gruppo">Dentro l'app</div>
      <dl class="imp-tasti">${[["Ctrl+1 … 5", "Oggi, Chat, Appunti, Mappa, Inbox"], ["Ctrl+Shift+T", "Nuova chat"], ["Ctrl+Shift+W", "Chiudi la chat"],
        ["Ctrl+Tab", "Chat successiva"], ["Ctrl+,", "Impostazioni"], ["Shift+Invio", "A capo nel terminale"], ["Ctrl+V / tasto destro", "Incolla nel terminale"]]
        .map(([k, v]) => html`<dt><kbd>${k}</kbd></dt><dd>${v}</dd>`)}</dl>`,

    dati: html`
      <${Voce} titolo="Second brain in uso" testo=${d.radice}>
        <button class="btn piccolo" onClick=${() => api("apri_cartella")}>Apri cartella</button></${Voce}>
      <${Voce} titolo="Esporta una copia" testo="Un .zip di tutti gli appunti nei Download (senza la cronologia git).">
        <button class="btn piccolo" onClick=${() => azione("esporta", (r) => `Copia salvata: ${r.conto} file`)}>Esporta</button></${Voce}>
      <${CestinoChat} api=${api} avvisa=${avvisa} />
      <${Voce} titolo="Registri dell'app" testo="Errori e ultimi aggiornamenti degli appunti, utili se qualcosa non va.">
        <button class="btn piccolo" onClick=${() => api("apri_registri")}>Apri</button></${Voce}>
      <${Voce} titolo="Svuota la cache" testo="Le parole chiave delle chat si ricalcolano. Nessun appunto viene toccato.">
        <button class="btn piccolo" onClick=${() => azione("svuota_cache", "Cache svuotata")}>Svuota</button></${Voce}>
      <${Voce} titolo="Cambia second brain" testo="Rifai il primo avvio per crearne un altro o collegarne uno diverso. Quello attuale resta dov'è.">
        <button class="btn piccolo pericolo" onClick=${async () => { const r = await api("rifai_primo_avvio"); if (!r.errore) { chiudi(); primoAvvio(); } }}>Rifai il primo avvio</button></${Voce}>`,

    info: html`
      <div class="imp-info"><img src="icona.svg" width="56" height="56" alt="" />
        <div><b>Second Brain Studio</b><span>Versione ${d.versione}</span></div></div>
      <p class="imp-nota">Codice aperto con licenza PolyForm Noncommercial 1.0.0: gratis per tutti, nessuno può venderlo.</p>
      <div class="imp-riquadro imp-kofi-grande"><b>Ti è utile Second Brain Studio?</b>
        <span>È gratis e lo sviluppo nel tempo libero. Un caffè su Ko-fi mi aiuta a continuare: nuove funzioni e la versione per Mac.</span>
        <button class="btn primario piccolo" onClick=${() => api("apri_link", KOFI)}>${Icona.caffe()}Offrimi un caffè su Ko-fi</button></div>
      <p class="imp-nota">Icone degli emblemi: Fluent Emoji di Microsoft (MIT). Terminale: xterm.js. Interfaccia: Preact.</p>`,
  }[sez];

  return html`<div class="velo" onClick=${(e) => e.target === e.currentTarget && chiudi()}>
    <div class="dialogo imp" role="dialog" aria-modal="true" aria-label="Impostazioni">
      <nav class="imp-nav" aria-label="Sezioni delle impostazioni">
        <h3>Impostazioni</h3>
        ${SEZIONI.map(([k, n, ic]) => html`<button class=${sez === k ? "attivo" : ""} onClick=${() => setSez(k)}>${(Icona[ic] || Icona.oggi)()}${n}</button>`)}
      </nav>
      <section class="imp-corpo">
        <div class="imp-testa"><h2>${SEZIONI.find(([k]) => k === sez)[1]}</h2>
          <button class="btn fantasma piccolo" onClick=${chiudi} aria-label="Chiudi">${Icona.chiudi()}</button></div>
        <div class="imp-voci" key=${sez}>${corpo}</div>
        ${sez !== "info" && html`<button class="imp-kofi" onClick=${() => api("apri_link", KOFI)} title="Apre ko-fi.com nel browser">
          ${Icona.caffe()}<span>Ti piace Second Brain Studio? <b>Offrimi un caffè</b></span>${Icona.esterno()}</button>`}
      </section>
    </div></div>`;
}
