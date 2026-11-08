// Primo avvio: procedura guidata che compare finché il second brain non è configurato.
// Passi: benvenuto → requisiti → cartella (nuova, esistente, da GitHub) → questionario
// → collegamenti → fatto. Alla fine l'app vera parte con una prima chat su misura.
// Tutto passa da main.py (configurazione.py): qui solo interfaccia.
import { html, useState, useEffect } from "./vendor/preact-htm.mjs";
import { Icona } from "./icone.mjs";
import { impostaLingua, linguaAttiva, traduci } from "./lingua.mjs";

const PASSI = [["benvenuto", "Benvenuto"], ["requisiti", "Requisiti"], ["cartella", "Cartella"],
  ["domande", "Su di te"], ["collegamenti", "Collegamenti"], ["fatto", "Pronto"]];
const AREE = ["Lavoro", "Università", "Scuola", "Casa", "Salute", "Finanze", "Famiglia", "Hobby", "Viaggi"];
// regole di base: [testo, acceso all'inizio]. "Mai scrivere password negli appunti" c'è sempre (modello.py)
const REGOLE = {
  chiedi: ["Chiedi prima di…", [
    ["cancellare o sovrascrivere file fuori dal second brain", true],
    ["inviare mail o messaggi (al massimo prepara bozze)", true],
    ["usare il mio browser (navigare con i miei account, compilare moduli)", false],
    ["fare ricerche sul web", false],
    ["installare programmi o estensioni", false],
    ["cambiare impostazioni di Windows o di Claude", false],
    ["pubblicare qualcosa online (repository pubblici, post, siti)", false],
    ["avviare lavori lunghi o con molti sotto-agenti", false]]],
  mai: ["Non fare mai…", [
    ["comprare, pagare o concludere ordini (al massimo il carrello)", true],
    ["scrivere a persone su WhatsApp, Telegram o social (solo lettura)", false],
    ["condividere i miei dati personali con siti o servizi esterni", false],
    ["accettare termini, cookie o permessi al posto mio", false],
    ["salvare negli appunti cose di altre persone che usano questo PC", false]]],
  metodo: ["Modo di lavorare", [
    ["se non sei sicuro chiedi, non inventare", true],
    ["verifica prima di consegnare", true],
    ["dimmi in una riga cosa hai salvato negli appunti", false],
    ["le attività lunghe falle quando non sto lavorando", false]]],
};
const regoleIniziali = () => Object.fromEntries(Object.entries(REGOLE).map(([k, [, voci]]) => [k, voci.filter(([, s]) => s).map(([v]) => v)]));
const STILI = [["conciso", "Conciso", "Risposte brevi e dirette, senza giri di parole."],
  ["spiegato", "Spiegato", "Passo per passo, con esempi quando servono."],
  ["amichevole", "Amichevole", "Colloquiale e alla mano, ma sempre al punto."]];
const LINGUE = ["italiano", "inglese", "spagnolo", "francese", "tedesco"];

function Scelta({ attiva, onClick, titolo, testo, icona }) {
  return html`<button class=${`pa-scelta ${attiva ? "scelto" : ""}`} role="radio" aria-checked=${attiva} onClick=${onClick}>
    ${icona && html`<span class="pa-scelta-ic">${Icona[icona]()}</span>`}
    <span><b>${titolo}</b><span>${testo}</span></span></button>`;
}

function Gettone({ attivo, onClick, children }) {
  return html`<button class=${`pa-gettone ${attivo ? "scelto" : ""}`} aria-pressed=${attivo} onClick=${onClick}>${children}</button>`;
}

function Requisito({ ok, titolo, testo, azione }) {
  return html`<li class=${`pa-req ${ok ? "ok" : "no"}`}>
    <span class="pa-req-segno" aria-hidden="true">${ok ? "✓" : "!"}</span>
    <span class="pa-req-testo"><b>${titolo}</b><span>${testo}</span></span>${!ok && azione}</li>`;
}

export function PrimoAvvio({ api, useEvento, fine }) {
  const [passo, setPasso] = useState(0);
  const [stato, setStato] = useState(null);
  const [modo, setModo] = useState("nuovo");
  const [cartella, setCartella] = useState("");
  const [valutazione, setValutazione] = useState(null);
  const [gh, setGh] = useState(null);
  const [codice, setCodice] = useState(null);
  const [repos, setRepos] = useState(null);
  const [repo, setRepo] = useState("");
  // lingua dell'app: decide anche la struttura del second brain creato (INDICE.md o INDEX.md)
  const [lin, setLin] = useState(linguaAttiva());
  const [r, setR] = useState({ nome: "", chi: "", aree: ["Lavoro"], altraArea: "", stile: "conciso", lingua: linguaAttiva() === "en" ? "inglese" : "italiano",
    regole: regoleIniziali(), altroMai: "", ruoliSi: false, ruoli: [{ nome: "", compito: "" }] });
  const [claudeMd, setClaudeMd] = useState(true);
  const [hook, setHook] = useState(true);
  const [copiaGh, setCopiaGh] = useState(true);
  const [lavoro, setLavoro] = useState(false);
  const [errore, setErrore] = useState("");
  const [esito, setEsito] = useState(null);
  const cambia = (k, v) => setR((x) => ({ ...x, [k]: v }));
  const cambiaLingua = (l) => {
    impostaLingua(l); setLin(l); api("salva_impostazioni", { lingua: l });
    // la lingua delle risposte segue quella dell'app finche' non la si sceglie a mano
    setR((x) => ({ ...x, lingua: x.lingua === (l === "en" ? "italiano" : "inglese") ? (l === "en" ? "inglese" : "italiano") : x.lingua }));
  };

  const controlla = async () => { const s = await api("configurazione"); if (!s.errore) { setStato(s); setCartella((c) => c || s.proposta); } };
  useEffect(() => { controlla(); api("github_stato").then((s) => !s.errore && setGh(s)); }, []);
  useEffect(() => { const t = setTimeout(async () => setValutazione(cartella ? await api("valuta_cartella", cartella) : null), 250); return () => clearTimeout(t); }, [cartella]);
  useEffect(() => { if (modo === "github" && gh && gh.collegato && !repos) api("github_repo_lista").then((x) => setRepos(x.repo || [])); }, [modo, gh]);
  useEvento((nome, d) => {
    if (nome !== "github") return;
    if (d.esito === "collegato") { setCodice(null); setGh(d); }
    else if (d.esito === "negato" || d.esito === "scaduto") { setCodice(null); setErrore(d.esito === "negato" ? "Accesso a GitHub annullato" : "Il codice è scaduto: riprova"); }
  });

  // il questionario serve solo quando si crea qualcosa di nuovo
  const saltaDomande = modo === "github" || (modo === "esistente" && valutazione && valutazione.second_brain);
  const id = PASSI[passo][0];
  const vai = (d) => { setErrore(""); let n = passo + d; if (PASSI[n] && PASSI[n][0] === "domande" && saltaDomande) n += d; setPasso(n); };

  const req = stato && stato.requisiti;
  const requisitiOk = req && req.claude && req.git;
  const v = valutazione || {};
  const cartellaOk = !v.errore && v.percorso && (
    modo === "nuovo" ? !v.second_brain :
    modo === "esistente" ? v.esiste :
    (!v.esiste || v.vuota) && !!repo);
  const avvisoCartella = v.errore ? v.errore
    : modo === "nuovo" && v.second_brain ? "Qui c'è già un second brain: scegli \"Ne ho già uno\"."
    : modo === "nuovo" && v.esiste && !v.vuota ? `La cartella contiene già ${v.file} elementi: verranno solo aggiunti i file nuovi, niente viene sovrascritto.`
    : modo === "esistente" && v.percorso && !v.esiste ? "Questa cartella non esiste."
    : modo === "esistente" && v.esiste && !v.second_brain ? "Non trovo INDICE.md: aggiungerò indice e regole, senza toccare i tuoi file."
    : modo === "github" && v.esiste && !v.vuota ? "Per scaricare da GitHub serve una cartella nuova o vuota." : "";

  const scegli = async () => { const x = await api("scegli_cartella", cartella || null); if (x.percorso) setCartella(modo === "nuovo" && !x.percorso.endsWith("Second Brain") ? x.percorso + "\\Second Brain" : x.percorso); };
  const accediGh = async () => { setErrore(""); const x = await api("github_accedi"); if (x.errore) setErrore(x.errore); else { setCodice(x); api("apri_github", x.url); } };

  const accessoGh = codice ? html`<div class="pa-codice"><span>Inserisci questo codice nella pagina di GitHub che si è aperta:</span>
      <b class="num">${codice.codice}</b><button class="btn piccolo fantasma" onClick=${() => api("apri_github", codice.url)}>Riapri la pagina</button></div>`
    : html`<button class="btn" onClick=${accediGh}>${Icona.github()} Accedi a GitHub</button>`;

  const completa = async () => {
    setLavoro(true); setErrore("");
    // in inglese gettoni e lingua vanno nei file come li si vede (tradotti); il testo scritto a mano resta com'e'
    const T = (x) => lin === "en" ? traduci(x) : x;
    const aree = [...r.aree.map(T), ...r.altraArea.split(",").map((s) => s.trim()).filter(Boolean)];
    const mai = [...r.regole.mai.map(T), ...r.altroMai.split(",").map((s) => s.trim()).filter(Boolean)];
    const risposte = { nome: r.nome.trim(), chi: r.chi.trim(), aree, stile: r.stile, lingua: T(r.lingua), mai,
      chiedi: r.regole.chiedi.map(T), metodo: r.regole.metodo.map(T), struttura: lin,
      ruoli: r.ruoliSi ? r.ruoli.filter((x) => x.nome.trim()) : [] };
    const x = await api("completa_configurazione", { modo, cartella, risposte, repo, claude_md: claudeMd, hook });
    setLavoro(false);
    if (x.errore) { setErrore(x.errore); return; }
    if (modo !== "github" && copiaGh && gh && gh.collegato) {
      // copia online: repository privato creato e primo caricamento
      const c = await api("github_crea_repo", "second-brain");
      x.passi = [...(x.passi || []), c.errore ? `Copia su GitHub non fatta: ${c.errore}` : `Copia privata su GitHub: ${c.repo}`];
    }
    setEsito(x); setPasso(PASSI.length - 1);
  };

  const corpo = {
    benvenuto: html`<div class="pa-pagina">
      <img class="pa-logo" src="icona.svg" alt="" width="72" height="72" />
      <h1>Benvenuto in Second Brain Studio</h1>
      <p class="pa-intro">Un posto unico per i tuoi appunti e per Claude. Claude ricorda chi sei, i tuoi progetti e le tue regole,
        e aggiorna gli appunti da solo alla fine di ogni chat.</p>
      <ul class="pa-punti">
        <li><b>I tuoi appunti, file normali.</b> Una cartella di file Markdown sul tuo PC: niente database, niente abbonamenti in più.</li>
        <li><b>Claude Code incorporato.</b> Il vero Claude Code con il tuo piano, in schede accanto agli appunti.</li>
        <li><b>Copia su GitHub, se vuoi.</b> Un repository privato per averlo su più PC.</li>
      </ul>
      <p class="pa-nota">Ci vogliono un paio di minuti. Puoi cambiare tutto anche dopo.</p>
      <div class="pa-gettoni pa-lingua" role="radiogroup" aria-label="Lingua dell'app">
        ${[["it", "Italiano"], ["en", "English"]].map(([l, n]) => html`<${Gettone} attivo=${lin === l} onClick=${() => cambiaLingua(l)}><span data-no-trad>${n}</span></${Gettone}>`)}
      </div></div>`,

    requisiti: html`<div class="pa-pagina">
      <h2>Cosa serve</h2>
      <p class="pa-intro">Second Brain Studio usa Claude Code per parlare con Claude e git per tenere la storia degli appunti.</p>
      ${!req ? html`<p class="pa-nota">Controllo…</p>` : html`<ul class="pa-reqs">
        <${Requisito} ok=${!!req.claude} titolo="Claude Code" testo=${req.claude ? "Installato" : "Serve un piano Claude (Pro o Max). Installalo e poi premi Ricontrolla."}
          azione=${html`<button class="btn piccolo" onClick=${() => api("apri_link", `https://docs.claude.com/${lin}/docs/claude-code/setup`)}>Come installarlo</button>`} />
        <${Requisito} ok=${req.git} titolo="Git" testo=${req.git ? "Installato" : "Serve per la cronologia degli appunti."}
          azione=${html`<button class="btn piccolo" onClick=${() => api("apri_link", "https://git-scm.com/download/win")}>Scarica Git</button>`} />
        <${Requisito} ok=${req.accesso} titolo="Accesso a Claude" testo=${req.accesso ? "Fatto" : "Apri Claude Code e accedi con il tuo account (puoi farlo anche dopo)."}
          azione=${req.claude && html`<button class="btn piccolo" onClick=${() => api("accedi_claude")}>Accedi</button>`} />
      </ul>`}
      <button class="btn fantasma pa-ricontrolla" onClick=${controlla}>${Icona.ricarica()} Ricontrolla</button></div>`,

    cartella: html`<div class="pa-pagina">
      <h2>Dove sta il tuo second brain</h2>
      <div class="pa-scelte" role="radiogroup" aria-label="Da dove partire">
        <${Scelta} attiva=${modo === "nuovo"} onClick=${() => setModo("nuovo")} icona="piu" titolo="Creane uno nuovo" testo="Cartelle, regole e indice pronti, su misura per te." />
        <${Scelta} attiva=${modo === "esistente"} onClick=${() => setModo("esistente")} icona="cartella" titolo="Ne ho già uno" testo="Una cartella di appunti già sul PC." />
        <${Scelta} attiva=${modo === "github"} onClick=${() => setModo("github")} icona="github" titolo="Scaricalo da GitHub" testo="Lo usi già su un altro PC." />
      </div>
      ${modo === "github" && html`<div class="pa-gh">
        ${gh && gh.collegato ? html`<div class="pa-riga"><span class="pa-ok">✓</span> Collegato come <b>${gh.utente || "utente GitHub"}</b></div>
          ${repos === null ? html`<p class="pa-nota">Carico i repository…</p>` : !repos.length ? html`<p class="pa-nota">Nessun repository trovato.</p>` :
          html`<label class="etichetta-campo">Repository
            <select class="campo" value=${repo} onChange=${(e) => setRepo(e.target.value)}>
              <option value="">Scegli…</option>
              ${repos.map((x) => html`<option value=${x.url}>${x.nome}${x.privato ? " · privato" : ""}</option>`)}</select></label>`}`
        : accessoGh}</div>`}
      <label class="etichetta-campo">Cartella
        <div class="pa-riga"><input class="campo" value=${cartella} onInput=${(e) => setCartella(e.target.value)} spellcheck="false" />
          <button class="btn" onClick=${scegli}>Sfoglia…</button></div></label>
      ${avvisoCartella && html`<p class=${`pa-avviso ${cartellaOk ? "" : "grave"}`}>${avvisoCartella}</p>`}</div>`,

    domande: html`<div class="pa-pagina">
      <h2>Raccontami di te</h2>
      <p class="pa-intro">Le risposte diventano le regole e l'indice che Claude legge in ogni chat. Si possono cambiare quando vuoi.</p>
      <div class="pa-griglia">
        <label class="etichetta-campo">Come ti chiami
          <input class="campo" value=${r.nome} maxLength="40" onInput=${(e) => cambia("nome", e.target.value)} placeholder="Es. Giulia" /></label>
        <label class="etichetta-campo">Lingua delle risposte
          <select class="campo" value=${r.lingua} onChange=${(e) => cambia("lingua", e.target.value)}>${LINGUE.map((l) => html`<option value=${l}>${traduci(l)}</option>`)}</select></label>
      </div>
      <label class="etichetta-campo"><span>Chi sei, in una riga <span class="facolt">· facoltativo</span></span>
        <input class="campo" value=${r.chi} maxLength="200" onInput=${(e) => cambia("chi", e.target.value)} placeholder="Es. Studio architettura a Torino e lavoro part-time in una libreria" /></label>
      <div class="etichetta-campo">Le aree della tua vita da tenere in ordine</div>
      <div class="pa-gettoni">${AREE.map((a) => html`<${Gettone} attivo=${r.aree.includes(a)}
        onClick=${() => cambia("aree", r.aree.includes(a) ? r.aree.filter((x) => x !== a) : [...r.aree, a])}>${a}</${Gettone}>`)}
        <input class="campo pa-altro" value=${r.altraArea} onInput=${(e) => cambia("altraArea", e.target.value)} placeholder="Altre, separate da virgola" /></div>
      <div class="etichetta-campo">Come vuoi che ti risponda</div>
      <div class="pa-scelte tre" role="radiogroup" aria-label="Stile delle risposte">${STILI.map(([k, t, d]) => html`<${Scelta} attiva=${r.stile === k} onClick=${() => cambia("stile", k)} titolo=${t} testo=${d} />`)}</div>
      <div class="etichetta-campo">Regole per Claude <span class="facolt">· tocca per accendere o spegnere</span></div>
      ${Object.entries(REGOLE).map(([k, [titolo, voci]]) => html`<div class="pa-regole">
        <div class="pa-regole-titolo">${titolo}</div>
        <div class="pa-gettoni">${voci.map(([a]) => html`<${Gettone} attivo=${r.regole[k].includes(a)}
          onClick=${() => cambia("regole", { ...r.regole, [k]: r.regole[k].includes(a) ? r.regole[k].filter((x) => x !== a) : [...r.regole[k], a] })}>${a}</${Gettone}>`)}
          ${k === "mai" && html`<input class="campo pa-altro" value=${r.altroMai} onInput=${(e) => cambia("altroMai", e.target.value)} placeholder="Altro, separato da virgola" />`}</div></div>`)}
      <p class="pa-nota">Sempre attiva: Claude non scrive mai password, chiavi o codici negli appunti.</p>
      <label class="pa-interruttore"><input type="checkbox" checked=${r.ruoliSi} onChange=${(e) => cambia("ruoliSi", e.target.checked)} />
        <span><b>Assistenti con un nome</b> <span class="facolt">· facoltativo</span><br />Dai un nome a dei ruoli (es. "Archivista" tiene in ordine gli appunti) e chiamali in chat.</span></label>
      ${r.ruoliSi && html`<div class="pa-ruoli">${r.ruoli.map((x, i) => html`<div class="pa-riga">
          <input class="campo pa-ruolo-nome" value=${x.nome} maxLength="30" placeholder="Nome" onInput=${(e) => cambia("ruoli", r.ruoli.map((y, j) => j === i ? { ...y, nome: e.target.value } : y))} />
          <input class="campo" value=${x.compito} maxLength="120" placeholder="Cosa fa" onInput=${(e) => cambia("ruoli", r.ruoli.map((y, j) => j === i ? { ...y, compito: e.target.value } : y))} />
          ${r.ruoli.length > 1 && html`<button class="btn fantasma piccolo" aria-label="Togli" onClick=${() => cambia("ruoli", r.ruoli.filter((_, j) => j !== i))}>✕</button>`}</div>`)}
        ${r.ruoli.length < 6 && html`<button class="btn piccolo fantasma" onClick=${() => cambia("ruoli", [...r.ruoli, { nome: "", compito: "" }])}>+ Aggiungi un ruolo</button>`}</div>`}</div>`,

    collegamenti: html`<div class="pa-pagina">
      <h2>Collegamenti con Claude Code</h2>
      <p class="pa-intro">Così ogni chat, anche fuori dall'app, conosce il tuo second brain. Prima di cambiare qualcosa faccio una copia dei file.</p>
      <label class="pa-interruttore"><input type="checkbox" checked=${claudeMd} onChange=${(e) => setClaudeMd(e.target.checked)} />
        <span><b>Regole e indice in ogni chat</b> <span class="consigliato">consigliato</span><br />Aggiunge due righe a <code>~/.claude/CLAUDE.md</code>, senza toccare il resto.</span></label>
      <label class="pa-interruttore"><input type="checkbox" checked=${hook} onChange=${(e) => setHook(e.target.checked)} />
        <span><b>Appunti aggiornati da soli</b> <span class="consigliato">consigliato</span><br />A fine chat Claude riassume cosa è cambiato e aggiorna gli appunti; a inizio chat scarica le novità dagli altri PC. Aggiunge anche il consumo del piano nella barra in basso.</span></label>
      ${modo !== "github" && html`<div class="pa-gh">
        <div><b>Copia privata su GitHub</b> <span class="facolt">· facoltativo</span><br />
          <span class="pa-nota">Un repository privato tuo: il second brain è al sicuro e lo ritrovi su altri PC. Gratis, serve solo un account GitHub.</span></div>
        ${gh && gh.collegato ? html`<label class="pa-interruttore"><input type="checkbox" checked=${copiaGh} onChange=${(e) => setCopiaGh(e.target.checked)} />
            <span><b>Crea il repository e carica il second brain</b><br />Collegato come ${gh.utente || "utente GitHub"}.</span></label>`
          : accessoGh}
        <span class="pa-nota">Puoi farlo anche dopo, dal fondo della barra laterale.</span></div>`}
      <dl class="pa-riepilogo">
        <dt>Cartella</dt><dd>${cartella}</dd>
        <dt>Partenza</dt><dd>${modo === "nuovo" ? "second brain nuovo" : modo === "esistente" ? "cartella esistente" : "scaricato da GitHub"}</dd>
      </dl></div>`,

    fatto: html`<div class="pa-pagina">
      <img class="pa-logo" src="icona.svg" alt="" width="64" height="64" />
      <h1>Il tuo second brain è pronto</h1>
      <ul class="pa-fatti">${((esito && esito.passi) || []).map((p) => html`<li><span class="pa-ok">✓</span>${p}</li>`)}</ul>
      ${esito && esito.prompt ? html`<p class="pa-intro">Nella prima chat Claude ti farà qualche domanda e scriverà le risposte negli appunti giusti.</p>`
        : html`<p class="pa-intro">Apri l'app e riprendi da dove eri rimasto.</p>`}</div>`,
  }[id];

  const avanti = {
    benvenuto: html`<button class="btn primario" onClick=${() => vai(1)}>Iniziamo</button>`,
    requisiti: html`<button class="btn primario" disabled=${!requisitiOk} onClick=${() => vai(1)}>Continua</button>`,
    cartella: html`<button class="btn primario" disabled=${!cartellaOk} onClick=${() => vai(1)}>Continua</button>`,
    domande: html`<button class="btn primario" disabled=${!r.nome.trim()} onClick=${() => vai(1)}>Continua</button>`,
    collegamenti: html`<button class="btn primario" disabled=${lavoro} onClick=${completa}>${lavoro ? "Preparo…" : modo === "nuovo" ? "Crea il mio second brain" : "Collega il second brain"}</button>`,
    fatto: html`<button class="btn primario" onClick=${() => fine(esito && esito.prompt)}>${esito && esito.prompt ? "Apri la prima chat" : "Apri Second Brain Studio"}</button>`,
  }[id];

  return html`<div class="primo-avvio">
    <aside class="pa-lato">
      <div class="marchio"><img class="marchio-img" src="icona.svg" alt="" width="28" height="28" /><span>Second Brain <i>Studio</i></span></div>
      <ol class="pa-passi">${PASSI.map(([k, n], i) => (k === "domande" && saltaDomande) ? null : html`<li class=${i === passo ? "attivo" : i < passo ? "fatto" : ""}>
        <span class="pa-num num">${i < passo ? "✓" : i + 1}</span>${n}</li>`)}</ol>
      ${stato && stato.precedente && id !== "fatto" && html`<button class="btn fantasma piccolo pa-annulla"
        onClick=${async () => { const x = await api("annulla_primo_avvio"); if (x.errore) setErrore(x.errore); else fine(null); }}>← Torna al second brain di prima</button>`}
    </aside>
    <main class="pa-centro">
      <div class="pa-contenuto" key=${id}>${corpo}</div>
      ${errore && html`<div class="messaggio pa-errore">${errore}</div>`}
      <div class="pa-azioni">
        ${passo > 0 && id !== "fatto" && html`<button class="btn fantasma" disabled=${lavoro} onClick=${() => vai(-1)}>Indietro</button>`}
        <span class="pa-spazio"></span>${avanti}
      </div>
    </main></div>`;
}
