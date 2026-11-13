import { html, useState, useEffect } from "./vendor/preact-htm.mjs";

export const LOCALE = (id) => id === "claude_locale" || id === "codex_locale";
const ETICHETTE = { spento: "Motore spento", caricamento: "Caricamento del modello…", pronto: "Modello pronto", riposo: "In riposo · modello scaricato", errore: "Errore del motore" };
function useLocali(api) {
  const [catalogo, setCatalogo] = useState(null), [stato, setStato] = useState(null), [errore, setErrore] = useState("");
  const carica = async () => { const r = await api("ia_locale_catalogo"); if (!r.errore) { setCatalogo(r); setErrore(""); } else setErrore(r.errore); };
  useEffect(() => { let vivo = true;
    const stato = async () => { const r = await api("ia_locale_stato"); if (vivo && !r.errore) setStato(r); };
    carica(); stato(); const a = setInterval(carica, 15000), b = setInterval(stato, 2000);
    return () => { vivo = false; clearInterval(a); clearInterval(b); };
  }, []);
  return { catalogo, stato, errore, carica };
}

export function SceltaLocale({ api, imp, mettiImp }) {
  const { catalogo, stato, errore, carica } = useLocali(api);
  const modelli = (catalogo?.modelli || []).filter(m => m.disponibile);
  const firma = modelli.map(m => m.id).join("|");
  useEffect(() => { if (modelli.length && !modelli.some(m => m.id === imp.modello_locale)) mettiImp("modello_locale", modelli[0].id); }, [firma, imp.modello_locale]);
  const preferenze = () => { localStorage.setItem("impSezione", "ia-locale"); window.sb.evento("impostazioni-locali", {}); };
  if (!catalogo) return html`<p class="nota" role="status">${errore || "Cerco i modelli installati…"}</p>`;
  return html`<div class="scelta-locale">
    ${modelli.length ? html`<span class="imp-seg modelli-locali" role="radiogroup" aria-label="Modello locale">
      ${modelli.map(m => html`<button role="radio" aria-checked=${imp.modello_locale === m.id} class=${imp.modello_locale === m.id ? "scelto" : ""}
        title=${`${m.nome || m.id}${m.dimensione_gb ? ` · ${m.dimensione_gb} GB` : ""}\n${m.file}`}
        onClick=${() => mettiImp("modello_locale", m.id)}>${m.nome || m.id}</button>`)}</span>`
      : html`<p class="nota">Nessun modello GGUF trovato. Aggiungi una cartella in IA locale.</p>`}
    <div class="locale-stato" role="status"><span class=${`pallino ${stato?.stato === "pronto" ? "verde" : stato?.stato === "caricamento" ? "giallo" : "grigio"}`}></span>
      <span>${ETICHETTE[stato?.stato] || "Motore locale"}</span>
      <button class="btn piccolo fantasma" onClick=${carica} title="Aggiorna i modelli installati">Aggiorna</button>
      <button class="btn piccolo fantasma" onClick=${preferenze}>Gestisci</button></div>
  </div>`;
}

function Riga({ titolo, testo, children }) {
  return html`<div class="imp-voce"><span class="imp-testi"><b>${titolo}</b>${testo && html`<span>${testo}</span>`}</span><span class="imp-comando">${children}</span></div>`;
}
function Campo({ valore, cambia, tipo="text", min, max }) {
  return html`<input class="campo imp-sel" type=${tipo} value=${valore ?? ""} min=${min} max=${max}
    onInput=${e => cambia(tipo === "number" ? Number(e.target.value) : e.target.value)} />`;
}

export function ImpostazioniLocali({ api, avvisa, imp, mettiImp }) {
  const { catalogo, stato, errore, carica } = useLocali(api);
  const [form, setForm] = useState(null), [selezione, setSelezione] = useState(""), [salvando, setSalvando] = useState(false), [forza, setForza] = useState(false);
  useEffect(() => { if (catalogo && !form) setForm(catalogo.configurazione); }, [catalogo]);
  if (!form || !catalogo) return html`<p class="imp-nota">${errore || "Carico la configurazione locale…"}</p>`;
  const modelli = catalogo.modelli || [], id = selezione || imp.modello_locale || modelli[0]?.id || "";
  const voce = form.modelli[id] || modelli.find(m => m.id === id) || {};
  const attivo = !!stato?.pid, modifica = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const modificaModello = (k, v) => setForm(f => ({ ...f, modelli: { ...f.modelli, [id]: {
    nome: voce.nome || id, file: voce.file || "", ...(voce.draft ? { draft: voce.draft } : {}),
    ...(voce.proiettore ? { proiettore: voce.proiettore } : {}), [k]: v } } }));
  const scegli = async (tipo, applica) => { const r = await api("ia_locale_scegli_percorso", tipo); if (r.errore) avvisa(r.errore, "errore"); else if (r.percorso) applica(r.percorso); };
  const salva = async () => { setSalvando(true); const r = await api("ia_locale_configura", form); setSalvando(false);
    if (r.errore) { avvisa(r.errore, "errore"); return false; } setForm(r.configurazione); await carica(); avvisa("Impostazioni locali salvate"); return true; };
  const avvia = async () => { if (!await salva()) return; const r = await api("ia_locale_avvia", id, form.contesto, !!form.dflash && !!voce.draft, !!form.visione);
    if (r.errore) avvisa(r.errore, "errore"); };
  const arresta = async (conferma=false) => { const r = await api("ia_locale_arresta", conferma);
    if (r.errore && stato?.client && !conferma) setForza(true); else if (r.errore) avvisa(r.errore, "errore"); else { setForza(false); avvisa("Motore arrestato"); } };
  const percorso = (valore, tipo, cambia) => html`<span class="locale-percorso"><${Campo} valore=${valore} cambia=${cambia} /><button class="btn piccolo" disabled=${attivo} onClick=${() => scegli(tipo, cambia)}>Sfoglia</button></span>`;
  const spunta = (k, nome, testo) => html`<${Riga} titolo=${nome} testo=${testo}><label class="locale-check"><input type="checkbox" checked=${!!form[k]} onChange=${e => modifica(k, e.target.checked)} />Attivo</label></${Riga}>`;
  return html`<div class="ia-locale">
    <div class="imp-riquadro locale-riepilogo"><b role="status">${ETICHETTE[stato?.stato] || "Motore locale"}</b>
      <span>${stato?.modello ? `${modelli.find(m => m.id === stato.modello)?.nome || stato.modello} · ${stato.contesto / 1024}k token${stato.dflash ? " · DFlash" : ""}` : "Si carica solo quando avvii una chat locale."}</span>
      ${stato?.errore && html`<span class="locale-errore">${stato.errore}</span>`}
      <div class="locale-azioni"><button class="btn piccolo" disabled=${!attivo} onClick=${() => arresta()}>Arresta e libera memoria</button>
        <button class="btn piccolo fantasma" onClick=${carica}>Aggiorna elenco</button></div>
      ${forza && html`<div class="locale-conferma"><span>Ci sono chat locali aperte. La risposta in corso verrà interrotta.</span>
        <button class="btn piccolo pericolo" onClick=${() => arresta(true)}>Arresta comunque</button><button class="btn piccolo" onClick=${() => setForza(false)}>Annulla</button></div>`}</div>
    ${attivo && html`<p class="imp-nota">Arresta il motore per cambiare percorsi o limiti. Le chat cloud restano indipendenti.</p>`}
    <fieldset disabled=${attivo || salvando} class="locale-campi">
      <div class="imp-gruppo">Motore e modelli</div>
      <${Riga} titolo="Eseguibile llama-server">${percorso(form.eseguibile, "eseguibile", v => modifica("eseguibile", v))}</${Riga}>
      <${Riga} titolo="Porta locale" testo="Il servizio ascolta soltanto su questo computer."><${Campo} tipo="number" valore=${form.porta} min="1024" max="65535" cambia=${v => modifica("porta", v)} /></${Riga}>
      <label class="locale-cartelle"><b>Cartelle dei modelli GGUF</b><span>Una cartella per riga. L'elenco si aggiorna anche quando aggiungi o rimuovi file.</span>
        <textarea class="campo" rows="3" value=${form.cartelle_modelli.join("\n")} onInput=${e => modifica("cartelle_modelli", e.target.value.split("\n").map(x => x.trim()).filter(Boolean))}></textarea></label>
      <button class="btn piccolo" onClick=${() => scegli("cartella", p => modifica("cartelle_modelli", [...new Set([...form.cartelle_modelli, p])]))}>Aggiungi cartella</button>
      <${Riga} titolo="Modello da gestire"><select class="campo imp-sel locale-select" value=${id} onChange=${e => { setSelezione(e.target.value); mettiImp("modello_locale", e.target.value); }}>
        ${modelli.map(m => html`<option value=${m.id}>${m.nome || m.id}${m.disponibile ? "" : " · file mancante"}</option>`)}</select></${Riga}>
      ${id && html`<${Riga} titolo="Nome visualizzato"><${Campo} valore=${voce.nome || id} cambia=${v => modificaModello("nome", v)} /></${Riga}>
        <${Riga} titolo="File del modello">${percorso(voce.file, "modello", v => modificaModello("file", v))}</${Riga}>
        <${Riga} titolo="Drafter opzionale" testo="Per DFlash serve un file compatibile con il modello scelto.">${percorso(voce.draft, "draft", v => modificaModello("draft", v))}</${Riga}>
        <${Riga} titolo="Proiettore immagini" testo="Componente visivo opzionale, compatibile con il modello scelto.">${percorso(voce.proiettore, "proiettore", v => modificaModello("proiettore", v))}</${Riga}>`}
      <div class="imp-gruppo">Profilo delle chat locali</div>
      <${Riga} titolo="Contesto" testo="Consigliati almeno 32k per gli agenti. Le chat riprese adottano gli aumenti; mantengono il contesto precedente se più grande. Chiudi e riapri le chat dopo le modifiche."><select class="campo imp-sel" value=${form.contesto} onChange=${e => modifica("contesto", Number(e.target.value))}>
        ${[4096,8192,16384,32768,65536,131072].map(n => html`<option value=${n}>${n / 1024}k token</option>`)}</select></${Riga}>
      ${spunta("dflash", "Accelerazione DFlash", "Usata solo quando il modello ha un drafter configurato. Richiede altra VRAM.")}
      ${spunta("visione", "Abilita immagini", "Richiede il proiettore. Immagini grandi o numerose aumentano memoria e contesto.")}
      ${spunta("compattazione_automatica", "Compattazione automatica Claude locale", "Disattiva per evitare riassunti automatici molto lenti con contesti piccoli. Al limite usa /compact manualmente o apri una nuova chat. Vale dalla riapertura della chat.")}
      ${spunta("mcp_claude", "Connettori MCP di Claude locale", "Carica i server MCP configurati in Claude Code e nei plugin. Aumentano strumenti e contesto; alcuni richiedono rete o servizi esterni. Comandi e skill sono disponibili anche con questa opzione spenta. Riapri la chat per applicare.")}
      <${Riga} titolo="Riposo dopo inattività" testo="Scarica modello e contesto anche con chat aperta; la richiesta successiva li ricarica."><select class="campo imp-sel" value=${form.inattivita_secondi} onChange=${e => modifica("inattivita_secondi", Number(e.target.value))}>
        ${[[0,"Mai"],[60,"1 minuto"],[180,"3 minuti"],[300,"5 minuti"],[600,"10 minuti"],[1800,"30 minuti"],[3600,"1 ora"]].map(([n,t]) => html`<option value=${n}>${t}</option>`)}</select></${Riga}>
      <details class="locale-avanzate"><summary>Memoria e impostazioni avanzate</summary>
        <${Riga} titolo="Cache conversazioni (MiB)" testo="Limite della cache, non della RAM totale del processo. Zero la disattiva."><${Campo} tipo="number" valore=${form.cache_ram_mib} min="0" max="8192" cambia=${v => modifica("cache_ram_mib", v)} /></${Riga}>
        <${Riga} titolo="Checkpoint del contesto" testo="Più checkpoint possono accelerare il riuso, ma occupano RAM."><${Campo} tipo="number" valore=${form.checkpoint} min="0" max="8" cambia=${v => modifica("checkpoint", v)} /></${Riga}>
        <${Riga} titolo="Precisione cache KV"><select class="campo imp-sel" value=${form.cache_kv} onChange=${e => modifica("cache_kv", e.target.value)}>${["f16","q8_0","q4_0"].map(v => html`<option value=${v}>${v}</option>`)}</select></${Riga}>
        <${Riga} titolo="Layer sulla GPU" testo="−1 carica tutti i layer; 0 usa la CPU. Un valore specifico permette un caricamento misto."><${Campo} tipo="number" valore=${form.layer_gpu} min="-1" max="200" cambia=${v => modifica("layer_gpu", v)} /></${Riga}>
        ${spunta("mmap", "Mapping dei pesi in RAM", "Può velocizzare alcuni caricamenti; influisce sulla memoria del processo. L'SSD accelera l'avvio in entrambi i casi.")}
      </details>
      <div class="locale-azioni"><button class="btn primario" onClick=${salva}>${salvando ? "Salvo…" : "Salva impostazioni"}</button>
        <button class="btn" disabled=${!id} onClick=${avvia}>Carica modello</button></div>
    </fieldset>
    <p class="imp-nota">I file possono stare su dischi diversi. I gestori dei modelli si occupano dei download; ricerca, siti e browser sono strumenti dell'agente. Questa versione collega i GGUF a llama.cpp.</p>
  </div>`;
}
