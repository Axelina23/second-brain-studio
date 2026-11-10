// Interfaccia del Second Brain (Preact + htm, senza build).
// Pagine: Oggi, Chat, Appunti, Mappa, Inbox. A destra la colonna dei terminali
// (una linguetta per chat di Claude Code), in basso la barra di stato.
// Dati e azioni passano da window.pywebview.api (ponte.py); gli eventi asincroni
// arrivano da Python su window.sb.evento(nome, dati).
import { html, render, useState, useEffect, useRef, useMemo, useCallback } from "./vendor/preact-htm.mjs";
import { marked } from "./vendor/marked.esm.js";
import DOMPurify from "./vendor/purify.es.mjs";
import { Icona, Emblema, Motivo, fondoPiastrella, Marchio } from "./icone.mjs";
import { Console } from "./terminale.mjs";
import { PaginaMappa, ordinaGruppi } from "./mappa.mjs";
import { linguaAttiva } from "./lingua.mjs";
import { DialogoProgetto } from "./progetto.mjs";
import { PrimoAvvio } from "./primo-avvio.mjs";
import { Impostazioni, applicaAspetto, SceltaCodex } from "./impostazioni.mjs";

// ---------- ponte ----------
const pronto = new Promise((ok) => {
  if (window.pywebview && window.pywebview.api) ok();
  else window.addEventListener("pywebviewready", () => ok(), { once: true });
});
async function api(nome, ...args) {
  await pronto;
  try { return await window.pywebview.api[nome](...args); }
  catch (e) { return { errore: String(e && e.message || e) }; }
}
const ascoltatori = new Set();
window.sb = { evento: (nome, dati) => ascoltatori.forEach((f) => f(nome, dati)) };
function useEvento(f) {
  const rif = useRef(f); rif.current = f;
  useEffect(() => { const g = (n, d) => rif.current(n, d); ascoltatori.add(g); return () => ascoltatori.delete(g); }, []);
}

// ---------- formattazione ----------
const GG = ["dom", "lun", "mar", "mer", "gio", "ven", "sab"];
const MM = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
const ora = (d) => `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
function quando(iso) {
  const d = new Date(iso), oggi = new Date();
  const g = Math.round((new Date(oggi.toDateString()) - new Date(d.toDateString())) / 864e5);
  if (g === 0) return `oggi ${ora(d)}`;
  if (g === 1) return `ieri ${ora(d)}`;
  if (g < 7) return `${GG[d.getDay()]} ${d.getDate()}`;
  return `${d.getDate()} ${MM[d.getMonth()]}`;
}
function segnale(eta) {
  // eta in secondi -> "adesso", "3 min fa", "alle 14:20", "ieri alle 22:10", "3 nov"
  if (eta < 90) return "adesso";
  if (eta < 3600) return `${Math.round(eta / 60)} min fa`;
  const d = new Date(Date.now() - eta * 1000), oggi = new Date();
  const g = Math.round((new Date(oggi.toDateString()) - new Date(d.toDateString())) / 864e5);
  if (g === 0) return `alle ${ora(d)}`;
  if (g === 1) return `ieri alle ${ora(d)}`;
  return `${d.getDate()} ${MM[d.getMonth()]}`;
}
function gruppoGiorno(iso) {
  const d = new Date(iso), oggi = new Date();
  const g = Math.round((new Date(oggi.toDateString()) - new Date(d.toDateString())) / 864e5);
  if (g === 0) return "Oggi";
  if (g === 1) return "Ieri";
  if (g < 7) return "Questa settimana";
  if (g < 31) return "Questo mese";
  return "Prima";
}
const etaTesto = (g) => g < 1 ? "oggi" : g < 2 ? "ieri" : `${Math.floor(g)} g`;
const etaClasse = (g) => g < 3 ? "" : g < 8 ? "e1" : g <= 14 ? "e2" : "e3";
const STATI = { errore_salvataggio: "Salvataggio non riuscito", auto_disattivati: "Appunti automatici disattivati", salvata: "salvata", non_salvata: "non salvata", in_corso: "salvataggio…", aperta: "aperta", breve: "breve" };
const SYNC = {
  verde: "Sincronizzato con GitHub", giallo: "Modifiche da caricare su GitHub",
  rosso: "Ci sono appunti nuovi da scaricare", grigio: "Stato di GitHub sconosciuto",
};

const Timbro = ({ stato }) => html`<span class=${`timbro ${stato}`}>${STATI[stato] || stato}</span>`;

// ---------- app ----------
function App({ primaChat, impIniziali, primoAvvio }) {
  const [imp, setImp] = useState(impIniziali);
  const [pagina, setPagina] = useState(() => (impIniziali && impIniziali.pagina_iniziale) || localStorage.getItem("pagina") || "oggi");
  const [home, setHome] = useState(null);
  const [schede, setSchede] = useState([]);
  const [attiva, setAttiva] = useState(null);
  const [sceltaNuova, setSceltaNuova] = useState(false);
  const [modoTerm, setModoTerm] = useState(() => localStorage.getItem("modoTerm") || "normale");
  const [toasts, setToasts] = useState([]);
  const [dialogo, setDialogo] = useState(null);
  const [git, setGit] = useState(null);
  const [apriAppunto, setApriAppunto] = useState(null);
  const [orologio, setOrologio] = useState(new Date());
  const [uso, setUso] = useState(null);
  const [remoti, setRemoti] = useState(null);
  useEffect(() => {
    const leggi = async () => { const r = await api("pc_remoti"); if (r && !r.errore_api) setRemoti(r); };
    leggi(); const t = setInterval(leggi, 30e3); return () => clearInterval(t);
  }, []);
  useEvento((n, d) => {
    if (n === "pc-remoti") setRemoti(d);
    // clic su una notifica: la chat nella sua linguetta, se e' aperta nell'app; altrimenti la pagina Chat
    if (n === "vai-chat") {
      const s = schede.find((x) => x.sessione && x.sessione === d.sessione);
      if (s) { setAttiva(s.id); if (modoTerm === "nascosto") setModoTerm("normale"); } else setPagina("chat");
    }
  });
  const [aggiornamento, setAggiornamento] = useState(false);
  const [versione, setVersione] = useState("");
  const [gh, setGh] = useState(null);
  const caricaGh = useCallback(async () => { const s = await api("github_stato"); if (!s.errore) setGh(s); }, []);
  useEffect(() => { caricaGh(); }, []);
  useEffect(() => {
    const leggi = async () => { const r = await api("aggiornamento"); setAggiornamento(r && r.pronto ? (r.nuova || true) : false); if (r && r.versione) setVersione(r.versione); };
    leggi(); const t = setInterval(leggi, 60e3); return () => clearInterval(t);
  }, []);
  useEffect(() => {
    const leggi = async () => { const u = await api("uso"); if (!u.errore) setUso(u); };
    leggi(); const t = setInterval(leggi, 30e3); return () => clearInterval(t);
  }, []);

  // azione facoltativa: { testo, fai } diventa un pulsante nell'avviso (es. "Annulla")
  const togliToast = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const avvisa = useCallback((testo, tipo = "", azione = null) => {
    const id = Math.random();
    setToasts((t) => [...t.slice(-2), { id, testo, tipo, azione }]);
    setTimeout(() => togliToast(id), azione ? 8000 : 4200);
  }, []);

  // ---------- menu del tasto destro (chat, linguette, Inbox) ----------
  const [menu, setMenu] = useState(null);
  const apriMenu = (e, voci) => {
    e.preventDefault(); e.stopPropagation();
    let { clientX: x, clientY: y } = e;
    if (!x && !y) { const r = e.currentTarget.getBoundingClientRect(); x = r.left + 24; y = r.bottom - 4; }  // da tastiera
    setMenu({ x, y, voci: voci.filter(Boolean) });
  };
  const ok = (r) => { if (r && r.errore) { avvisa(r.errore, "errore"); return false; } return true; };
  const copia = (testo, msg) => navigator.clipboard.writeText(testo).then(() => avvisa(msg), () => avvisa("Non riesco a copiare negli appunti di Windows", "errore"));
  const chiediTesto = (titolo, valore, conferma, aiuto = "") => setDialogo({ tipo: "testo", titolo, valore, conferma, aiuto });

  const eliminaChat = async (elenco) => {
    const fatte = [];
    for (const c of elenco) { const r = await api("elimina_chat", c.id); if (ok(r)) fatte.push(c); }
    caricaHome();
    if (!fatte.length) return;
    avvisa(fatte.length === 1 ? `Chat eliminata: ${fatte[0].etichetta}` : `${fatte.length} chat eliminate`, "", { testo: "Ripristina", fai: async () => {
      let n = 0; for (const c of fatte) if (ok(await api("ripristina_chat", c.id))) n++;
      if (n) avvisa(n === 1 ? "Chat ripristinata" : `${n} chat ripristinate`); caricaHome();
    } });
  };
  const rinominaChat = (c) => chiediTesto("Rinomina la chat", c.rinominata ? c.etichetta : "", async (t) => {
    if (ok(await api("rinomina_chat", c.id, t))) caricaHome();
  }, `Lascia vuoto per tornare al titolo automatico (${c.rinominata ? "parole chiave" : c.etichetta}).`);
  const apriInCartella = async (c) => {
    const s = await api("scegli_cartella"); if (!s || !s.percorso) return;
    const r = await api("apri_in_cartella", c.id, s.percorso);
    if (!ok(r)) return;
    setSchede((v) => v.some((x) => x.id === r.id) ? v : [...v, r]); setAttiva(r.id); setModoTerm((m) => m === "nascosto" ? "normale" : m);
  };
  const mostraRegistro = async (c) => { const r = await api("riga_registro", c.id); if (ok(r)) vaiAppunto(r.percorso, r.riga); };
  const esportaChat = async (c) => {
    const r = await api("esporta_chat", c.id);
    if (ok(r)) { caricaHome(); avvisa(`Esportata nell'Inbox: ${r.nome}`, "", { testo: "Apri", fai: () => vaiAppunto(r.percorso) }); }
  };
  // selezionate: le chat scelte con Ctrl/Shift+clic nella pagina Chat (se il menu parte da una di loro)
  const menuChat = (e, c, selezionate = null, pulisci = null) => {
    if (selezionate && selezionate.length > 1 && selezionate.some((x) => x.id === c.id)) {
      apriMenu(e, [
        { testo: `Elimina ${selezionate.length} chat`, icona: Icona.cestino, pericolo: true, fai: () => { eliminaChat(selezionate); pulisci && pulisci(); } },
        { testo: "Annulla la selezione", fai: () => pulisci && pulisci() },
      ]);
      return;
    }
    apriMenu(e, [
      { testo: "Riprendi", icona: Icona.riprendi, fai: () => apriChat("riprendi", c.id) },
      ["non_salvata", "errore_salvataggio"].includes(c.stato) && { testo: c.stato === "errore_salvataggio" ? "Riprova" : "Salva gli appunti", icona: Icona.salva, fai: () => salvaChat(c.id) },
      { testo: "Rinomina…", icona: Icona.matita, fai: () => rinominaChat(c) },
      ...(!c.rinominata ? [{ testo: "Rigenera titolo", icona: Icona.ricarica, fai: async () => { if (ok(await api("rigenera_titolo", c.id))) avvisa("Rigenerazione titolo avviata"); } }] : []),
      { testo: c.fissata ? "Togli dall'alto" : "Fissa in alto", icona: Icona.puntina, fai: async () => { if (ok(await api("fissa_chat", c.id, !c.fissata))) caricaHome(); } },
      diClaude(c) && { testo: "Apri in un'altra cartella…", icona: Icona.cartella, fai: () => apriInCartella(c) },
      "-",
      { testo: "Copia l'id della chat", icona: Icona.copia, fai: () => copia(c.id, `Id copiato: ${c.id}`) },
      { testo: "Mostra nel Registro", icona: Icona.appunti, fai: () => mostraRegistro(c) },
      { testo: "Esporta in Markdown", icona: Icona.esporta, fai: () => esportaChat(c) },
      "-",
      { testo: "Elimina chat", icona: Icona.cestino, pericolo: true, fai: () => eliminaChat([c]) },
    ].filter(Boolean));
  };
  // linguette delle chat aperte (in alto sul terminale e nella barra laterale)
  const menuScheda = (e, s) => apriMenu(e, [
    { testo: "Rinomina…", icona: Icona.matita, fai: () => chiediTesto("Rinomina la chat", s.titolo, async (t) => {
      const r = await api("rinomina_scheda", s.id, t);
      if (ok(r)) { setSchede((v) => v.map((x) => x.id === s.id ? { ...x, titolo: r.etichetta } : x)); caricaHome(); }
    }, s.sessione ? "Vale anche per la chat nell'elenco. Lascia vuoto per il titolo automatico." : "") },
    s.sessione && diClaude(s) && { testo: "Duplica (copia della conversazione)", icona: Icona.copia, fai: async () => {
      const r = await api("duplica_chat", s.sessione);
      if (ok(r)) { setSchede((v) => [...v, r]); setAttiva(r.id); }
    } },
    s.sessione && { testo: "Copia l'id della chat", icona: Icona.copia, fai: () => copia(s.sessione, `Id copiato: ${s.sessione}`) },
    "-",
    { testo: "Chiudi", icona: Icona.chiudi, fai: () => chiudiScheda(s.id) },
    schede.length > 1 && { testo: "Chiudi le altre", fai: () => { for (const x of schede) if (x.id !== s.id) chiudiScheda(x.id); setAttiva(s.id); } },
  ]);
  // note e file dell'Inbox; ricarica: funzione della pagina Inbox
  const menuInbox = (e, v, ricarica) => {
    const testo = /\.(md|txt)$/i.test(v.nome);
    apriMenu(e, [
      { testo: "Apri", icona: Icona.appunti, fai: () => testo ? vaiAppunto(v.percorso) : api("apri_esterno", v.percorso) },
      testo && { testo: "Apri fuori", icona: Icona.esterno, fai: () => api("apri_esterno", v.percorso) },
      { testo: "Smista con Claude", icona: Icona.chat, fai: () => apriChat("nuova", null, linguaAttiva() === "en"
        ? `Sort only the file ${v.percorso} from the Inbox: move the useful information into the right status files and move the file to its folder with a dated name, as the Rules say.`
        : `Smista dall'Inbox solo il file ${v.percorso}: estrai le informazioni utili nei file di stato giusti e sposta il file nella sua cartella col nome datato, come dicono le Regole.`) },
      { testo: "Sposta in un progetto…", icona: Icona.cartella, fai: () => setDialogo({ tipo: "sposta", file: v, ricarica }) },
      { testo: "Rinomina…", icona: Icona.matita, fai: () => chiediTesto("Rinomina il file", v.nome.replace(/\.(md|txt)$/i, ""), async (t) => {
        if (ok(await api("rinomina_inbox", v.percorso, t))) ricarica();
      }, "L'estensione resta quella di prima se non la scrivi.") },
      "-",
      { testo: "Elimina", icona: Icona.cestino, pericolo: true, fai: async () => {
        const r = await api("elimina_inbox", v.percorso); if (!ok(r)) return;
        ricarica(); caricaHome();
        avvisa(`Eliminato: ${v.nome}`, "", { testo: "Ripristina", fai: async () => { if (ok(await api("ripristina_inbox", r.chiave))) { ricarica(); caricaHome(); } } });
      } },
    ]);
  };

  const caricaHome = useCallback(async () => {
    const h = await api("home");
    if (h.errore) avvisa(`Non riesco a leggere i dati: ${h.errore}`, "errore"); else setHome(h);
    const g = await api("stato_git"); if (!g.errore) setGit(g);
  }, []);

  useEffect(() => { caricaHome(); const t = setInterval(caricaHome, 5 * 60e3); return () => clearInterval(t); }, []);
  // l'Inbox cambia anche da fuori (Claude nei terminali): se il numero di file cambia, home ricaricata
  const contoInbox = useRef(null);
  contoInbox.current = home ? home.inbox : null;
  useEffect(() => {
    const t = setInterval(async () => {
      const r = await api("conta_inbox");
      if (r && typeof r.inbox === "number" && contoInbox.current !== null && r.inbox !== contoInbox.current) caricaHome();
    }, 10e3);
    return () => clearInterval(t);
  }, []);
  useEffect(() => { const t = setInterval(() => setOrologio(new Date()), 20e3); return () => clearInterval(t); }, []);
  useEffect(() => { localStorage.setItem("pagina", pagina); api("pagina", pagina); }, [pagina]);
  useEffect(() => { localStorage.setItem("modoTerm", modoTerm); }, [modoTerm]);
  useEffect(() => { (async () => {
    const s = await api("schede"); if (s.schede && s.schede.length) { setSchede(s.schede); setAttiva(s.schede[0].id); }
    // dopo un aggiornamento: riapre le chat che erano aperte
    if (primaChat) { await apriChat("nuova", null, primaChat); return; }
    const r = await api("da_riaprire");
    for (const id of (r && r.sessioni) || []) await apriChat("riprendi", id);
  })(); }, []);
  // ogni 20 s aggiorna titoli e sessioni delle linguette (le chat nuove ricevono il loro nome)
  useEffect(() => {
    const t = setInterval(async () => {
      const r = await api("schede"); if (!r.schede) return;
      const per = new Map(r.schede.map((s) => [s.id, s]));
      setSchede((v) => v.map((s) => per.has(s.id) ? { ...s, titolo: per.get(s.id).titolo, sessione: per.get(s.id).sessione || s.sessione } : s));
    }, 20e3);
    return () => clearInterval(t);
  }, []);

  const [assistenti, setAssistenti] = useState([]);
  useEffect(() => {
    const leggi = () => api("assistenti").then((r) => {
      if (r && r.assistenti) setAssistenti((vecchi) => JSON.stringify(vecchi) === JSON.stringify(r.assistenti) ? vecchi : r.assistenti);
    });
    leggi();
    const timer = setInterval(leggi, 15000);
    window.addEventListener("focus", leggi);
    return () => { clearInterval(timer); window.removeEventListener("focus", leggi); };
  }, []);
  const mettiImp = useCallback(async (k, v) => {
    setImp((x) => ({ ...x, [k]: v }));
    const r = await api("salva_impostazioni", { [k]: v });
    if (r && r.errore) avvisa(r.errore, "errore");
  }, []);

  const schedeRif = useRef(schede); schedeRif.current = schede;
  const apriChat = useCallback(async (tipo = "nuova", sessione = null, prompt = null, cartella = null, titolo = null, diretta = false) => {
    if (tipo === "nuova" && !prompt && !cartella && !diretta && schedeRif.current.length > 0) {
      setSceltaNuova(true);
      setModoTerm((m) => m === "nascosto" ? "normale" : m);
      return;
    }
    setSceltaNuova(false);
    const r = await api("apri_chat", tipo, sessione, prompt, cartella, titolo);
    if (r.errore) { avvisa(r.errore, "errore"); return; }
    if (r.nota) avvisa(r.nota);
    setSchede((s) => s.some((x) => x.id === r.id) ? s : [...s, r]);
    setAttiva(r.id);
    setModoTerm((m) => m === "nascosto" ? "normale" : m);
    setTimeout(caricaHome, 1500);
  }, []);
  const salvaChat = useCallback(async (sessione) => {
    const r = await api("salva_chat", sessione);
    if (r.errore) { avvisa(r.errore, "errore"); return; }
    if (r.avviato) { avvisa("Salvataggio degli appunti avviato"); caricaHome(); return; }
    setSchede((s) => s.some((x) => x.id === r.id) ? s : [...s, r]);
    setAttiva(r.id); setModoTerm((m) => m === "nascosto" ? "normale" : m);
  }, []);
  const chiudiScheda = useCallback(async (id) => {
    await api("chiudi_scheda", id);
    setSchede((s) => {
      const resto = s.filter((x) => x.id !== id);
      setAttiva((a) => a === id ? (resto[resto.length - 1] || {}).id || null : a);
      return resto;
    });
    setTimeout(caricaHome, 800);
  }, []);
  const accediGh = async () => {
    const r = await api("github_accedi");
    if (r.errore) { avvisa(r.errore, "errore"); return; }
    setDialogo({ tipo: "github", codice: r.codice, url: r.url });
  };
  // se lo script dell'aggiornamento non parte l'app resta aperta e dice cosa fare
  const aggiornaOra = async () => { const r = await api("aggiorna"); if (r && r.errore) { setDialogo(null); avvisa(r.errore, "errore"); } };
  const sincronizzaGh = async () => { setGh((g) => g && { ...g, in_corso: true }); await api("github_sincronizza"); };
  const creaRepoGh = async () => {
    avvisa("Creo il repository privato su GitHub…");
    const r = await api("github_crea_repo", "second-brain");
    if (r.errore) avvisa(r.errore, "errore"); else avvisa(`Repository creato: ${r.repo}`);
    caricaGh(); caricaHome();
  };
  // evidenzia: testo di una riga da mostrare e mettere in risalto (es. la riga del Registro)
  const vaiAppunto = (percorso, evidenzia = null) => { setApriAppunto({ percorso, evidenzia, t: Date.now() }); setPagina("appunti"); };

  useEvento((nome, d) => {
    if (nome === "sync") setHome((h) => h && { ...h, sync: d.stato });
    else if (nome === "oggi") setHome((h) => h && { ...h, oggi: d });
    else if (nome === "chat") { setSchede((v) => v.map((s) => s.sessione === d.id ? { ...s, titolo: d.etichetta } : s)); setHome((h) => h && { ...h, chat: h.chat.map((c) => c.id === d.id ? { ...c, etichetta: d.etichetta } : c) }); }
    else if (nome === "nota") avvisa(`Nota rinominata: ${d.nome}`);
    else if (nome === "accesso-assistente") { setSceltaNuova(false); setSchede((s) => [...s, d]); setAttiva(d.id); setModoTerm((m) => m === "nascosto" ? "normale" : m); }
    else if (nome === "scheda") {
      setSchede((s) => s.map((x) => x.id === d.id ? { ...x, chiusa: true, sessione: d.sessione || x.sessione, stato: d.stato || x.stato } : x));
      setTimeout(caricaHome, 500);
    }
    else if (nome === "conferma-uscita") setDialogo({ tipo: "uscita", aperte: d.aperte });
    else if (nome === "nuova-chat") apriChat();
    else if (nome === "apri-chat") apriChat("nuova", null, d.prompt, d.cartella, d.titolo);
    else if (nome === "claude-avviso" && d.scheda) {
      // pallino sulla scheda finche' non la guardi
      const vista = document.hasFocus() && d.scheda === attivaRif.current;
      if (!vista) setSchede((s) => s.map((x) => x.id === d.scheda ? { ...x, avviso: d.tipo } : x));
    }
    else if (nome === "mostrata") caricaHome();
    else if (nome === "inbox-aggiunti") {
      const n = d.aggiunti.length;
      if (n) avvisa(n === 1 ? `Aggiunto all'Inbox: ${d.aggiunti[0]}` : `${n} file aggiunti all'Inbox`);
      if (d.saltati.length) avvisa(`Saltati (cartelle o non leggibili): ${d.saltati.join(", ")}`, "errore");
      caricaHome();
    }
    else if (nome === "inbox-altrove") avvisa("Per aggiungere file all'Inbox trascinali nella pagina Inbox");
    else if (nome === "github") {
      if (d.esito === "collegato") { setDialogo(null); avvisa(`GitHub collegato${d.utente ? `: @${d.utente}` : ""}`); }
      else if (d.esito === "accesso_scaduto") { setGh(d); avvisa("L'accesso a GitHub è scaduto: ricollega GitHub", "errore"); }
      else if (d.esito === "negato" || d.esito === "scaduto") { setDialogo(null); avvisa(d.esito === "negato" ? "Accesso a GitHub annullato" : "Il codice è scaduto: riprova", "errore"); }
      else if (d.esito === "fatto") {
        if (d.conflitto) setDialogo({ tipo: "conflitto", file: d.file || [] });
        else if (d.errore) avvisa(d.errore, "errore");
        else avvisa(d.salvati ? `Sincronizzato: ${d.salvati} file caricati su GitHub` : "Sincronizzato con GitHub");
        caricaHome();
      }
      caricaGh();
    }
  });

  // scorciatoie globali (fase di cattura: arrivano prima del terminale)
  useEffect(() => {
    const f = (e) => {
      const k = e.key.toLowerCase();
      let fatto = true;
      if (e.ctrlKey && e.shiftKey && k === "t") apriChat();
      else if (e.ctrlKey && e.shiftKey && k === "w" && attiva) chiudiScheda(attiva);
      else if (e.ctrlKey && k === "tab" && schede.length > 1) {
        const i = schede.findIndex((s) => s.id === attiva);
        setAttiva(schede[(i + (e.shiftKey ? -1 : 1) + schede.length) % schede.length].id);
      }
      else if (e.ctrlKey && k === ",") setDialogo({ tipo: "impostazioni" });
      else if (e.ctrlKey && !e.shiftKey && /^[1-5]$/.test(k)) setPagina(["oggi", "chat", "appunti", "mappa", "inbox"][+k - 1]);
      else fatto = false;
      if (fatto) { e.preventDefault(); e.stopPropagation(); }
    };
    window.addEventListener("keydown", f, true);
    return () => window.removeEventListener("keydown", f, true);
  }, [schede, attiva]);

  const attivaRif = useRef(attiva); attivaRif.current = attiva;
  useEffect(() => {
    // la scheda guardata perde il pallino; Python sa cosa stai guardando (niente notifiche inutili)
    if (attiva) setSchede((s) => s.some((x) => x.id === attiva && x.avviso) ? s.map((x) => x.id === attiva ? { ...x, avviso: null } : x) : s);
    const manda = () => { const s = schede.find((x) => x.id === attiva); api("visibile", document.hasFocus() && !document.hidden, s ? s.sessione : null); };
    manda();
    window.addEventListener("focus", manda); window.addEventListener("blur", manda); document.addEventListener("visibilitychange", manda);
    return () => { window.removeEventListener("focus", manda); window.removeEventListener("blur", manda); document.removeEventListener("visibilitychange", manda); };
  }, [attiva, schede.length]);

  const progettoDialogo = (progetto = null) => setDialogo({ tipo: "progetto", progetto });
  const contesto = { home, apriChat, salvaChat, vaiAppunto, avvisa, caricaHome, setPagina, api, progettoDialogo, remoti, menuChat, menuInbox, eliminaChat };
  const Pagina = { oggi: PaginaOggi, chat: PaginaChat, appunti: PaginaAppunti, mappa: PaginaMappa, inbox: PaginaInbox }[pagina] || PaginaOggi;
  const classe = `app ${modoTerm === "ampio" ? "term-ampio" : modoTerm === "nascosto" ? "term-nascosto" : ""} ${schede.length ? "" : "term-libero"}`;

  return html`<div class=${classe}>
    <${Laterale} pagina=${pagina} setPagina=${setPagina} home=${home} schede=${schede} attiva=${sceltaNuova ? null : attiva}
      setAttiva=${(id) => { setSceltaNuova(false); setAttiva(id); if (modoTerm === "nascosto") setModoTerm("normale"); }} apriChat=${apriChat}
      gh=${gh} accediGh=${accediGh} sincronizzaGh=${sincronizzaGh} creaRepoGh=${creaRepoGh}
      apriImpostazioni=${() => setDialogo({ tipo: "impostazioni" })} menuScheda=${menuScheda} />
    <main class="principale">
      <${Pagina} ...${contesto} apri=${apriAppunto} />
    </main>
    <${Maniglia} />
    <${ColonnaTerminali} schede=${schede} attiva=${attiva} setAttiva=${(id) => { setSceltaNuova(false); setAttiva(id); }} chiudi=${chiudiScheda}
      apriChat=${apriChat} salvaChat=${salvaChat} modo=${modoTerm} setModo=${setModoTerm} home=${home} menuScheda=${menuScheda}
      imp=${imp} mettiImp=${mettiImp} assistenti=${assistenti} sceltaNuova=${sceltaNuova} setSceltaNuova=${setSceltaNuova} />
    <${BarraStato} git=${git} home=${home} schede=${schede} attiva=${attiva} sceltaNuova=${sceltaNuova} imp=${imp}
      orologio=${orologio} modo=${modoTerm} setModo=${setModoTerm} uso=${uso}
      aggiornamento=${aggiornamento} versione=${versione} remoti=${remoti} aggiorna=${() => schede.some((s) => !s.chiusa) ? setDialogo({ tipo: "aggiorna", aperte: schede.filter((s) => !s.chiusa).length }) : aggiornaOra()} />
    <div class="avvisi-volo" role="status">${toasts.map((t) => html`<div class=${`toast ${t.tipo}`} key=${t.id}><span>${t.testo}</span>
      ${t.azione && html`<button class="toast-azione" onClick=${() => { togliToast(t.id); t.azione.fai(); }}>${t.azione.testo}</button>`}</div>`)}</div>
    ${menu && html`<${MenuContestuale} x=${menu.x} y=${menu.y} chiudi=${() => setMenu(null)} voci=${menu.voci} />`}
    ${dialogo && dialogo.tipo === "testo" && html`<${DialogoTesto} ...${dialogo} chiudi=${() => setDialogo(null)} />`}
    ${dialogo && dialogo.tipo === "sposta" && html`<div class="velo" onClick=${(e) => e.target === e.currentTarget && setDialogo(null)}>
      <div class="dialogo" role="dialog" aria-modal="true" aria-label="Sposta in un progetto">
        <h3>Sposta in un progetto</h3><p>${dialogo.file.nome} finisce nella cartella del progetto, accanto al suo CLAUDE.md.</p>
        <div class="scelta-progetti">${(home && home.progetti || []).map((p) => html`<button class="btn" onClick=${async () => {
          setDialogo(null);
          const r = await api("sposta_inbox", dialogo.file.percorso, p.percorso);
          if (ok(r)) { avvisa(`Spostato in ${r.progetto}`, "", { testo: "Apri", fai: () => vaiAppunto(r.percorso) }); dialogo.ricarica(); caricaHome(); }
        }}>${p.nome}</button>`)}</div>
        <div class="azioni"><button class="btn fantasma" onClick=${() => setDialogo(null)}>Annulla</button></div>
      </div></div>`}
    ${dialogo && dialogo.tipo === "progetto" && html`<${DialogoProgetto} api=${api} progetto=${dialogo.progetto} apriChat=${apriChat}
      chiudi=${() => setDialogo(null)} fatto=${(msg) => { setDialogo(null); avvisa(msg); caricaHome(); }} />`}
    ${dialogo && dialogo.tipo === "impostazioni" && html`<${Impostazioni} api=${api} avvisa=${avvisa} gh=${gh} accediGh=${accediGh}
      sincronizzaGh=${sincronizzaGh} aggiornaGh=${caricaGh} chiudi=${() => setDialogo(null)} primoAvvio=${primoAvvio}
      cambiate=${(n) => { setImp(n); applicaAspetto(n); }} />`}
    ${dialogo && dialogo.tipo === "github" && html`<div class="velo">
      <div class="dialogo" role="dialog" aria-modal="true">
        <h3>Collega GitHub</h3>
        <p>Su GitHub inserisci questo codice e autorizza "Second Brain Desktop". L'app non vede mai la tua password.</p>
        <div class="codice-gh num">${dialogo.codice}</div>
        <p class="attesa-gh"><span class="pallino giallo pulsa"></span>In attesa dell'autorizzazione…</p>
        <div class="azioni">
          <button class="btn fantasma" onClick=${() => { api("github_annulla"); setDialogo(null); }}>Annulla</button>
          <button class="btn primario" onClick=${() => { navigator.clipboard.writeText(dialogo.codice).catch(() => {}); api("apri_github", dialogo.url); }}>Copia il codice e apri GitHub</button>
        </div>
      </div></div>`}
    ${dialogo && dialogo.tipo === "conflitto" && html`<div class="velo" onClick=${(e) => e.target === e.currentTarget && setDialogo(null)}>
      <div class="dialogo" role="dialog" aria-modal="true">
        <h3>Conflitto da sistemare</h3>
        <p>Lo stesso appunto è cambiato su due dispositivi${dialogo.file.length ? html`: <b>${dialogo.file.join(", ")}</b>` : ""}. Non ho cambiato niente: le tue modifiche sono salvate in locale.</p>
        <div class="azioni">
          <button class="btn fantasma" onClick=${() => setDialogo(null)}>Più tardi</button>
          <button class="btn primario" onClick=${() => { setDialogo(null); apriChat("nuova", null, `Nel second brain la sincronizzazione con GitHub si è fermata per un conflitto${dialogo.file.length ? ` in ${dialogo.file.join(", ")}` : ""}. Fai git pull --rebase, unisci le due versioni tenendo le informazioni di entrambe, completa il rebase e fai push. Poi dimmi in una riga cosa hai unito.`); }}>Fallo sistemare a Claude</button>
        </div>
      </div></div>`}
    ${dialogo && dialogo.tipo === "aggiorna" && html`<div class="velo" onClick=${(e) => e.target === e.currentTarget && setDialogo(null)}>
      <div class="dialogo" role="dialog" aria-modal="true">
        <h3>Riavviare per aggiornare?</h3>
        <p>${dialogo.aperte === 1 ? "La chat aperta si chiude e si riapre da sola dopo l'aggiornamento, dal punto in cui era." : `Le ${dialogo.aperte} chat aperte si chiudono e si riaprono da sole dopo l'aggiornamento, dal punto in cui erano.`}</p>
        <div class="azioni"><button class="btn fantasma" onClick=${() => setDialogo(null)}>Più tardi</button>
          <button class="btn primario" onClick=${aggiornaOra}>Aggiorna e riavvia</button></div>
      </div></div>`}
    ${dialogo && dialogo.tipo === "uscita" && html`<div class="velo" onClick=${(e) => e.target === e.currentTarget && setDialogo(null)}>
      <div class="dialogo" role="dialog" aria-modal="true">
        <h3>Chiudere Second Brain Studio?</h3>
        <p>${dialogo.aperte === 1 ? "C'è una chat di Claude ancora aperta: verrà interrotta." : `Ci sono ${dialogo.aperte} chat di Claude ancora aperte: verranno interrotte.`}</p>
        <div class="azioni"><button class="btn fantasma" onClick=${() => setDialogo(null)}>Annulla</button>
          <button class="btn pericolo" onClick=${() => api("esci", true)}>Chiudi tutto</button></div>
      </div></div>`}
  </div>`;
}

// ---------- barra laterale ----------
const ICONA_IMP = html`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>`;

function Laterale({ pagina, setPagina, home, schede, attiva, setAttiva, apriChat, gh, accediGh, sincronizzaGh, creaRepoGh, apriImpostazioni, menuScheda }) {
  const voci = [["oggi", "Oggi"], ["chat", "Chat"], ["appunti", "Appunti"], ["mappa", "Mappa"], ["inbox", "Inbox"]];
  const sync = home ? home.sync : "grigio";
  return html`<aside class="laterale">
    <div class="marchio"><${Marchio} /><span>Second Brain <i>Studio</i></span></div>
    <nav class="nav" aria-label="Sezioni">
      ${voci.map(([id, nome], i) => html`<button class=${pagina === id ? "attivo" : ""} onClick=${() => setPagina(id)} title=${`${nome} (Ctrl+${i + 1})`}>
        ${Icona[id]()}${nome}${id === "inbox" && home && home.inbox ? html`<span class="conto">${home.inbox}</span>` : ""}</button>`)}
    </nav>
    <div class="sezione-lat">Chat aperte<button onClick=${() => apriChat()} title="Nuova chat (Ctrl+Shift+T)" aria-label="Nuova chat">${Icona.piu()}</button></div>
    <div class="aperte">
      ${schede.length === 0 ? html`<div class="vuoto-lat">Nessuna chat aperta</div>` :
        schede.map((s) => html`<button class=${`lat-chat ${s.id === attiva ? "attiva" : ""}`} onClick=${() => setAttiva(s.id)} onContextMenu=${(e) => menuScheda(e, s)}>
          <span class=${`pallino ${s.avviso === "attesa" ? "attesa" : s.avviso ? "risposta" : s.chiusa ? (s.stato === "non_salvata" ? "rosso" : "grigio") : "giallo pulsa"}`}
            title=${s.avviso === "attesa" ? "Aspetta un tuo permesso" : s.avviso ? "Ha risposto" : ""}></span><span title=${s.titolo}>${s.titolo}</span></button>`)}
    </div>
    <div class="piede-lat">
      <div><span class=${`pallino ${sync}`}></span>${SYNC[sync]}</div>
      <div class="lat-riga"><span><span class="pallino grigio"></span>${home && home.dispositivo ? home.dispositivo : "Questo PC"}</span>
        <button class="lat-imp" onClick=${apriImpostazioni} title="Impostazioni (Ctrl+,)" aria-label="Impostazioni">${ICONA_IMP}</button></div>
      ${gh && html`<div class="gh">
        ${!gh.collegato && (!gh.repo || gh.scaduto) ? html`<button class="btn piccolo gh-btn" onClick=${accediGh}>${Icona.github()}${gh.scaduto ? "Ricollega GitHub" : "Collega GitHub"}</button>`
        : !gh.repo ? html`<button class="btn piccolo gh-btn" onClick=${creaRepoGh}>${Icona.github()}Crea repository privato</button>`
        : html`<span class="gh-nome" title=${gh.repo}>${Icona.github()}${gh.utente ? `@${gh.utente}` : gh.repo}</span>
          <div class="gh-riga">
            <button class="btn piccolo gh-sinc" onClick=${sincronizzaGh} disabled=${gh.in_corso} title="Scarica le novità, salva le modifiche e caricale su GitHub">
              <span class=${gh.in_corso ? "gira" : ""}>${Icona.ricarica()}</span>${gh.in_corso ? "Sincronizzo…" : "Sincronizza"}</button>
          </div>
          ${!gh.collegato && html`<button class="gh-link" onClick=${accediGh}>Collega l'account per sincronizzare anche senza Claude</button>`}`}
      </div>`}
    </div>
  </aside>`;
}

// ---------- Oggi ----------
function PaginaOggi({ home, apriChat, salvaChat, vaiAppunto, avvisa, caricaHome, setPagina, progettoDialogo, menuChat }) {
  const [nota, setNota] = useState("");
  if (!home) return html`<div class="pagina"><div class="testata"><div><div class="data"><span class="carica"></span></div><h1>Un attimo…</h1></div></div></div>`;
  const ev = home.oggi && home.oggi.eventi || [];
  const sc = home.oggi && home.oggi.scadenze;
  const scadenze = sc ? sc.split(" · ") : [];
  const salvaNota = async (e) => {
    e.preventDefault();
    if (!nota.trim()) return;
    const r = await api("nota", nota);
    if (r.errore) avvisa(r.errore, "errore"); else { avvisa(`Nota salvata in Inbox: ${r.nome}`); setNota(""); caricaHome(); }
  };
  const azioneAvviso = (a) => {
    if (a.tipo === "non_salvate") return a.chat.length === 1
      ? html`<button class="btn piccolo" onClick=${() => salvaChat(a.chat[0].id)}>${Icona.salva()}${a.chat[0].stato === "errore_salvataggio" ? "Riprova" : "Salva"}</button>`
      : a.chat.length <= 3
        ? html`<button class="btn piccolo" onClick=${() => a.chat.forEach((c) => salvaChat(c.id))} title="Apre una linguetta per ogni chat e ci fa salvare gli appunti">${Icona.salva()}Salva tutte</button>`
        : html`<button class="btn piccolo" onClick=${() => setPagina("chat")}>Vedi</button>`;
    if (a.tipo === "inbox") return html`<button class="btn piccolo" onClick=${() => apriChat("nuova", null, "smista l'inbox")}>Smista</button>`;
    if (a.tipo === "fermo") return html`<button class="btn piccolo fantasma" onClick=${() => vaiAppunto(a.percorso)}>Apri</button>`;
    return "";
  };
  return html`<div class="pagina">
    <header class="testata">
      <div><div class="data">${home.data}</div><h1>${home.saluto}${home.nome ? `, ${home.nome}` : ""}</h1></div>
      <div class="azioni">
        <button class="btn" onClick=${() => apriChat("nuova", null, "briefing")}>${Icona.briefing()}Briefing</button>
        <button class="btn" onClick=${() => apriChat("nuova", null, "revisione")}>${Icona.revisione()}Revisione</button>
        <button class="btn primario" onClick=${() => apriChat()}>${Icona.piu()}Nuova chat</button>
      </div>
    </header>
    <div class="striscia">
      <div><div class="voce">Calendario</div><div class=${`val ${ev.length ? "" : "muto"}`}>${home.oggi ? (ev.length ? ev.join(" · ") : "Nessun evento oggi") : html`<span class="carica"></span>`}</div></div>
      <div><div class="voce">Prossima scadenza</div><div class=${`val ${scadenze[0] ? "" : "muto"}`} title=${sc || ""}>${scadenze[0] || (home.oggi ? "Niente nei prossimi giorni" : html`<span class="carica"></span>`)}</div></div>
      <div><div class="voce">Poi</div><div class=${`val ${scadenze[1] ? "" : "muto"}`} title=${sc || ""}>${scadenze.slice(1).join(" · ") || (home.oggi ? "—" : html`<span class="carica"></span>`)}</div></div>
    </div>
    <div class="griglia-oggi">
        <section class="blocco area-avvisi"><h2>Avvisi <span class="det num">${home.avvisi.length || ""}</span></h2>
          <div class="scheda">${home.avvisi.length === 0
            ? html`<div class="nessun-avviso"><span class="pallino verde"></span>Tutto in ordine: niente da recuperare.</div>`
            : home.avvisi.map((a) => html`<div class="avviso">
                <span class=${`pallino ${a.livello === "attenzione" || a.tipo === "fermo" ? "rosso" : "giallo"}`}></span>
                <p>${a.testo}${a.tipo === "non_salvate" ? html`<span class="sotto">${a.chat.slice(0, 3).map((c) => c.etichetta).join(" · ")}</span>` : ""}</p>
                ${azioneAvviso(a)}</div>`)}</div>
        </section>
        <section class="blocco area-progetti"><h2>Progetti <span class="det">freschezza degli appunti</span><span class="spazio"></span>
          <button onClick=${() => progettoDialogo()} title="Crea un progetto nuovo">${Icona.piu()} Nuovo</button></h2>
          <div class="panchina" style=${`--n:${home.progetti.length || 1}`}>${home.progetti.map((p) => html`<button class=${`piastrella ${etaClasse(p.giorni)}`}
              style=${`--fondo:${fondoPiastrella(p.nome, p.aspetto)};--crepe-pos:${(p.nome.length * 37) % 192}px ${(p.nome.charCodeAt(0) * 53) % 192}px`} onClick=${() => vaiAppunto(p.percorso)}
              onContextMenu=${(e) => { e.preventDefault(); progettoDialogo(p); }} title=${`Apri ${p.percorso} (tasto destro: cambia aspetto)`}>
              <${Motivo} motivo=${p.aspetto && p.aspetto.motivo} /><${Emblema} nome=${p.nome} emblema=${p.aspetto && p.aspetto.emblema} /><span class="nome">${p.nome}</span><span class="eta">${etaTesto(p.giorni)}</span></button>`)}</div>
        </section>
      <section class="blocco area-chat"><h2>Chat da riprendere<span class="spazio"></span><button onClick=${() => setPagina("chat")}>Tutte</button></h2>
        <div class="scheda">${home.chat.length === 0 ? html`<div class="vuoto"><strong>Nessuna chat ancora</strong>Inizia con "Nuova chat".</div>`
          : home.chat.map((c) => html`<div class="chat-riga" role="button" tabindex="0" onClick=${() => apriChat("riprendi", c.id)}
              onKeyDown=${(e) => e.key === "Enter" && apriChat("riprendi", c.id)} onContextMenu=${(e) => menuChat(e, c)}
              title="Riprendi questa chat (tasto destro: altre azioni)">
              <span style="min-width:0"><div class="titolo" title=${c.etichetta}>${c.fissata ? html`<span class="segno-fissata" title="Fissata in alto">${Icona.puntina()}</span>` : ""}<${Assistente} c=${c} />${c.etichetta}</div>${!c.primo.startsWith(c.etichetta) && html`<div class="primo">${c.primo}</div>`}</span>
              <span class="quando num">${quando(c.ultima)}</span><${Timbro} stato=${c.stato} /></div>`)}</div>
        <form class="nota-volo" onSubmit=${salvaNota}>
          <input class="campo" value=${nota} onInput=${(e) => setNota(e.target.value)} placeholder="Nota al volo… (Invio per salvarla in Inbox)" aria-label="Nota al volo" />
        </form>
      </section>
    </div>
  </div>`;
}

// ---------- menu del tasto destro ----------
// voci: { testo, icona, fai, pericolo } oppure "-" per un separatore. Si chiude con un clic
// fuori, Esc, la rotella o perdendo il fuoco; resta sempre dentro la finestra.
function MenuContestuale({ x, y, voci, chiudi }) {
  const rif = useRef(null);
  const [pos, setPos] = useState({ x, y, visibile: false });
  useEffect(() => {
    const r = rif.current.getBoundingClientRect();
    setPos({ x: Math.max(8, Math.min(x, innerWidth - r.width - 8)), y: Math.max(8, Math.min(y, innerHeight - r.height - 8)), visibile: true });
    const primo = rif.current.querySelector("button"); if (primo) primo.focus();
    const fuori = (e) => { if (!rif.current || !rif.current.contains(e.target)) chiudi(); };
    const tasto = (e) => {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); chiudi(); return; }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); e.stopPropagation();
        const b = [...rif.current.querySelectorAll("button")]; const i = b.indexOf(document.activeElement);
        b[(i + (e.key === "ArrowDown" ? 1 : b.length - 1)) % b.length].focus();
      }
    };
    addEventListener("mousedown", fuori, true); addEventListener("contextmenu", fuori, true);
    addEventListener("keydown", tasto, true); addEventListener("wheel", chiudi, true); addEventListener("blur", chiudi);
    return () => { removeEventListener("mousedown", fuori, true); removeEventListener("contextmenu", fuori, true);
      removeEventListener("keydown", tasto, true); removeEventListener("wheel", chiudi, true); removeEventListener("blur", chiudi); };
  }, []);
  return html`<div class="menu-destro" role="menu" ref=${rif} style=${`left:${pos.x}px;top:${pos.y}px;${pos.visibile ? "" : "visibility:hidden"}`}
      onContextMenu=${(e) => e.preventDefault()}>
    ${voci.map((v) => v === "-" ? html`<div class="menu-sep" role="separator"></div>`
      : html`<button role="menuitem" class=${v.pericolo ? "pericolo" : ""} onClick=${() => { chiudi(); v.fai(); }}>${v.icona && v.icona()}${v.testo}</button>`)}
  </div>`;
}

// dialogo con un campo di testo (rinomina): Invio conferma, Esc chiude
function DialogoTesto({ titolo, valore, aiuto, conferma, chiudi }) {
  const [t, setT] = useState(valore || "");
  const campo = useRef(null);
  useEffect(() => { campo.current.focus(); campo.current.select(); }, []);
  const vai = (e) => { e.preventDefault(); chiudi(); conferma(t.trim()); };
  return html`<div class="velo" onClick=${(e) => e.target === e.currentTarget && chiudi()}>
    <form class="dialogo" role="dialog" aria-modal="true" aria-label=${titolo} onSubmit=${vai}
        onKeyDown=${(e) => { if (e.key === "Escape") { e.stopPropagation(); chiudi(); } }}>
      <h3>${titolo}</h3>${aiuto && html`<p>${aiuto}</p>`}
      <input class="campo" ref=${campo} value=${t} onInput=${(e) => setT(e.target.value)} maxlength="120" aria-label=${titolo} />
      <div class="azioni" style="margin-top:16px"><button type="button" class="btn fantasma" onClick=${chiudi}>Annulla</button>
        <button type="submit" class="btn primario">Salva</button></div>
    </form></div>`;
}

// ---------- Chat ----------
function PaginaChat({ apriChat, salvaChat, remoti, menuChat, eliminaChat }) {
  const [elenco, setElenco] = useState(null);
  const [q, setQ] = useState("");
  const [filtro, setFiltro] = useState("tutte");
  const carica = async () => { const r = await api("chat"); setElenco(r.chat || []); };
  useEffect(() => { carica(); }, []);
  useEvento((n, d) => { if (n === "chat") setElenco((e) => e && e.map((c) => c.id === d.id ? { ...c, etichetta: d.etichetta, rinominata: d.rinominata ?? c.rinominata } : c)); if (n === "scheda" || n === "chat-eliminata" || n === "chat-cambiate") carica(); });
  // ricerca anche dentro le conversazioni (domande e risposte): il testo e' gia' in memoria
  // in Python, quindi la risposta arriva in pochi millisecondi; qui solo un breve ritardo
  // mentre scrivi. trovate: id -> estratto del punto in cui compare
  const [trovate, setTrovate] = useState(null);
  useEffect(() => {
    if (q.trim().length < 2) { setTrovate(null); return; }
    const t = setTimeout(async () => { const r = await api("cerca_chat", q); if (r && r.trovate) setTrovate(new Map(r.trovate.map((x) => [x.id, x.estratto]))); }, 120);
    return () => clearTimeout(t);
  }, [q]);
  const visibili = useMemo(() => (elenco || []).filter((c) => {
    if (filtro === "non_salvate" && !["non_salvata", "errore_salvataggio"].includes(c.stato)) return false;
    if (filtro === "aperte" && c.stato !== "aperta") return false;
    if (!q.trim()) return true;
    const t = `${c.etichetta} ${c.primo}`.toLowerCase();
    return q.toLowerCase().split(/\s+/).every((w) => t.includes(w)) || (trovate && trovate.has(c.id));
  }), [elenco, q, filtro, trovate]);
  // fissate in cima in un gruppo a parte, poi per giorno
  const gruppi = [];
  for (const c of visibili) { const g = c.fissata ? "Fissate" : gruppoGiorno(c.ultima); if (!gruppi.length || gruppi[gruppi.length - 1][0] !== g) gruppi.push([g, []]); gruppi[gruppi.length - 1][1].push(c); }
  // selezione multipla: Ctrl+clic aggiunge o toglie, Shift+clic prende l'intervallo; Esc la annulla
  const [sel, setSel] = useState(() => new Set());
  const ancora = useRef(null);
  const pulisci = () => setSel(new Set());
  useEffect(() => { const f = (e) => { if (e.key === "Escape" && sel.size) pulisci(); }; addEventListener("keydown", f); return () => removeEventListener("keydown", f); }, [sel]);
  const clicRiga = (e, c) => {
    if (e.ctrlKey || e.metaKey) {
      const n = new Set(sel); n.has(c.id) ? n.delete(c.id) : n.add(c.id); setSel(n); ancora.current = c.id; return;
    }
    if (e.shiftKey && ancora.current) {
      const ids = visibili.map((x) => x.id); const a = ids.indexOf(ancora.current), b = ids.indexOf(c.id);
      if (a >= 0 && b >= 0) { setSel(new Set(ids.slice(Math.min(a, b), Math.max(a, b) + 1))); return; }
    }
    if (sel.size) { pulisci(); return; }
    apriChat("riprendi", c.id);
  };
  const scelte = (elenco || []).filter((c) => sel.has(c.id));
  const altri = (remoti && remoti.attivo && remoti.pc) || [];
  const [chiusi, setChiusi] = useState(() => { try { return JSON.parse(localStorage.getItem("pcChiusi") || "[]"); } catch (_) { return []; } });
  const apriChiudi = (pc) => { const n = chiusi.includes(pc) ? chiusi.filter((x) => x !== pc) : [...chiusi, pc]; setChiusi(n); localStorage.setItem("pcChiusi", JSON.stringify(n)); };
  const filtra = (c) => (filtro !== "non_salvate" || ["non_salvata", "errore_salvataggio"].includes(c.stato)) && (filtro !== "aperte" || c.stato === "aperta")
    && (!q.trim() || q.toLowerCase().split(/\s+/).every((w) => (c.etichetta || "").toLowerCase().includes(w)));
  const nNon = (elenco || []).filter((c) => ["non_salvata", "errore_salvataggio"].includes(c.stato)).length + altri.reduce((n, p) => n + p.chat.filter((c) => ["non_salvata", "errore_salvataggio"].includes(c.stato)).length, 0);
  return html`<div class="pagina">
    <header class="testata"><div><h1 class="piccolo">Chat</h1></div>
      <div class="azioni"><button class="btn primario" onClick=${() => apriChat()}>${Icona.piu()}Nuova chat</button></div></header>
    <div class="filtri">
      <input class="campo" placeholder="Cerca tra le chat…" value=${q} onInput=${(e) => setQ(e.target.value)} aria-label="Cerca tra le chat" />
      <div class="schede-filtro" role="tablist">
        ${[["tutte", "Tutte"], ["non_salvate", `Non salvate${nNon ? ` (${nNon})` : ""}`], ["aperte", "Aperte"]].map(([id, n]) =>
          html`<button role="tab" aria-selected=${filtro === id} class=${filtro === id ? "attivo" : ""} onClick=${() => setFiltro(id)}>${n}</button>`)}
      </div>
    </div>
    ${sel.size > 0 && html`<div class="barra-scelte" role="status">
      <b>${sel.size === 1 ? "1 chat selezionata" : `${sel.size} chat selezionate`}</b><span class="det">Ctrl+clic per aggiungere, Shift+clic per un intervallo</span>
      <span class="spazio"></span>
      <button class="btn piccolo fantasma" onClick=${pulisci}>Annulla</button>
      <button class="btn piccolo pericolo" onClick=${() => { eliminaChat(scelte); pulisci(); }}>${Icona.cestino()}Elimina</button></div>`}
    ${altri.length > 0 && html`<div class="pc-testa questo"><span class="pallino verde"></span><b>${remoti.questo || "Questo PC"}</b><span class="pc-sotto">questo PC</span></div>`}
    ${elenco === null ? html`<span class="carica"></span>` : visibili.length === 0
      ? html`<div class="scheda vuoto"><strong>${q ? "Nessuna chat trovata" : "Niente qui"}</strong>${q ? "Prova con altre parole." : "Non ci sono chat in questo filtro."}</div>`
      : gruppi.map(([g, cs]) => html`<div><div class="gruppo-giorno">${g}</div><div class="scheda">
          ${cs.map((c) => html`<div class=${`chat-riga ampia ${sel.has(c.id) ? "scelta" : ""}`} role="button" tabindex="0" aria-pressed=${sel.has(c.id)}
              onClick=${(e) => clicRiga(e, c)} onMouseDown=${(e) => e.shiftKey && e.preventDefault()}
              onKeyDown=${(e) => { if (e.key === "Enter") apriChat("riprendi", c.id); else if (e.key === " ") { e.preventDefault(); clicRiga({ ctrlKey: true }, c); } }}
              onContextMenu=${(e) => menuChat(e, c, scelte, pulisci)}>
            <span style="min-width:0"><div class="titolo" title=${c.etichetta}>${c.fissata ? html`<span class="segno-fissata" title="Fissata in alto">${Icona.puntina()}</span>` : ""}<${Assistente} c=${c} />${c.etichetta}</div>
              <div class="primo">${trovate && trovate.has(c.id) ? html`<span class="estratto">${trovate.get(c.id)}</span>` : c.primo}</div></span>
            <span class="quando num">${quando(c.ultima)}</span><${Timbro} stato=${c.stato} />
            <span class="azione-riga" style="justify-self:end">${["non_salvata", "errore_salvataggio"].includes(c.stato)
              ? html`<button class="btn piccolo" onClick=${(e) => { e.stopPropagation(); salvaChat(c.id); }}>${Icona.salva()}${c.stato === "errore_salvataggio" ? "Riprova" : "Salva"}</button>` : ""}</span>
          </div>`)}</div></div>`)}
    ${altri.map((p) => { const cs = p.chat.filter(filtra); const chiuso = chiusi.includes(p.pc);
      return html`<section class=${`pc-sezione ${p.acceso ? "" : "spento"}`}>
        <button class="pc-testa" onClick=${() => apriChiudi(p.pc)} aria-expanded=${!chiuso}>
          <span class=${`pallino ${p.acceso ? "verde" : "grigio"}`}></span><b>${p.pc}</b>
          <span class="pc-sotto" title=${p.acceso ? "" : "Nessun segnale recente: forse è spento o senza rete"}>${p.acceso ? "" : "probabilmente spento · "}ultimo segnale ${segnale(p.eta)}</span>
          <span class="pc-conto">${cs.length === 1 ? "1 chat" : `${cs.length} chat`}</span><span class=${`pc-freccia ${chiuso ? "" : "aperta"}`}>›</span></button>
        ${!chiuso && (cs.length === 0 ? html`<div class="scheda vuoto piccolo">Nessuna chat in questo filtro.</div>`
          : html`<div class="scheda">${cs.map((c) => { const vecchia = !p.acceso && c.stato === "aperta";
            return html`<div class="chat-riga ampia remota" title=${`Chat di ${p.pc}: solo lettura`}>
              <span style="min-width:0"><div class="titolo">${c.etichetta || "chat senza titolo"}</div>${c.messaggi ? html`<div class="primo conteggio">${c.messaggi} messaggi</div>` : ""}</span>
              <span class="quando num">${quando(c.ultima)}</span>
              ${vecchia ? html`<span class="timbro vecchia">aperta alle ${ora(new Date(c.ultima))}</span>` : html`<${Timbro} stato=${c.stato} />`}
              <span></span></div>`; })}</div>`)}
      </section>`; })}
    ${remoti && remoti.attivo && !altri.length && html`<p class="pc-nota">${remoti.errore || "Le chat degli altri PC con questo second brain compaiono qui, appena ci apri Second Brain Studio."}</p>`}
  </div>`;
}

// ---------- Appunti ----------
function PaginaAppunti({ apri, avvisa, apriChat }) {
  const [voci, setVoci] = useState(null);
  const [q, setQ] = useState("");
  const [risultati, setRisultati] = useState(null);
  const [doc, setDoc] = useState(null);
  const [modifica, setModifica] = useState(null);
  const [conflitto, setConflitto] = useState(false);
  const lettore = useRef(null);
  useEffect(() => { (async () => { const r = await api("appunti"); setVoci(r.appunti || []); })(); }, []);
  useEffect(() => { if (apri) leggi(apri.percorso, apri.evidenzia); else if (!doc) { const ultimo = localStorage.getItem("appunto"); if (ultimo) leggi(ultimo); else apriIndice(); } }, [apri && apri.t]);
  // la prima volta l'indice: INDICE.md o INDEX.md secondo la struttura del second brain
  async function apriIndice() {
    for (const p of ["INDICE.md", "INDEX.md"]) { const r = await api("leggi", p); if (!r.errore) { setDoc(r); localStorage.setItem("appunto", p); return; } }
  }
  // riga da mettere in risalto (es. "Mostra nel Registro"): il primo elemento che contiene
  // l'inizio della riga, senza i segni del Markdown, viene portato al centro e colorato
  const [evidenzia, setEvidenzia] = useState(null);
  useEffect(() => {
    if (!evidenzia || !lettore.current) return;
    const chiave = evidenzia.replace(/^\s*[-*]\s*/, "").replace(/[`*_]/g, "").slice(0, 60).trim();
    const t = setTimeout(() => {
      const el = [...lettore.current.querySelectorAll(".md li, .md p")].find((x) => x.textContent.replace(/\s+/g, " ").includes(chiave));
      if (el) { el.classList.add("evidenziata"); el.scrollIntoView({ block: "center", behavior: "smooth" }); }
      setEvidenzia(null);
    }, 80);
    return () => clearTimeout(t);
  }, [evidenzia, doc]);
  useEffect(() => {
    if (q.trim().length < 2) { setRisultati(null); return; }
    const t = setTimeout(async () => { const r = await api("cerca", q); setRisultati(r.risultati || []); }, 220);
    return () => clearTimeout(t);
  }, [q]);
  async function leggi(percorso, riga = null) {
    if (modifica !== null && !confirm("Ci sono modifiche non salvate. Lasciarle?")) return;
    const r = await api("leggi", percorso);
    if (r.errore) { avvisa(r.errore, "errore"); return; }
    setDoc(r); setModifica(null); setConflitto(false); localStorage.setItem("appunto", percorso);
    if (lettore.current) lettore.current.scrollTop = 0;
    setEvidenzia(riga);
  }
  async function salva() {
    const r = await api("scrivi", doc.percorso, modifica, doc.mtime);
    if (r.conflitto) { setConflitto(true); return; }
    if (r.errore) { avvisa(r.errore, "errore"); return; }
    setDoc({ ...doc, testo: modifica, mtime: r.mtime, giorni: 0 }); setModifica(null); avvisa("Appunto salvato");
  }
  const noti = useMemo(() => new Set((voci || []).map((v) => v.percorso)), [voci]);
  const htmlDoc = useMemo(() => {
    if (!doc) return "";
    const h = DOMPurify.sanitize(marked.parse(doc.testo, { gfm: true, breaks: false }));
    // i percorsi in `codice` che puntano ad appunti noti diventano link interni
    return h.replace(/<code>([^<]+?)<\/code>/g, (m, t) => {
      const p = t.replace(/\\/g, "/");
      return noti.has(p) ? `<a href="#" data-app="${p}"><code>${t}</code></a>` : m;
    });
  }, [doc, noti]);
  const clicLettore = (e) => {
    const a = e.target.closest("a"); if (!a) return;
    e.preventDefault();
    const p = a.getAttribute("data-app") || a.getAttribute("href");
    if (p && noti.has(p)) leggi(p);
    else if (p && /^https?:/.test(p)) window.open(p, "_blank");
  };
  useEffect(() => {
    const f = (e) => { if (e.ctrlKey && e.key.toLowerCase() === "s" && modifica !== null) { e.preventDefault(); salva(); } };
    window.addEventListener("keydown", f); return () => window.removeEventListener("keydown", f);
  }, [modifica, doc]);

  const gruppi = {};
  for (const v of voci || []) (gruppi[v.gruppo] = gruppi[v.gruppo] || []).push(v);
  const ordine = ordinaGruppi(Object.keys(gruppi));
  return html`<div class="appunti">
    <nav class="elenco-app" aria-label="Appunti">
      <input class="campo" placeholder="Cerca negli appunti…" value=${q} onInput=${(e) => setQ(e.target.value)} aria-label="Cerca negli appunti" />
      ${risultati ? (risultati.length === 0 ? html`<div class="vuoto-lat">Nessun risultato</div>` :
          risultati.map((r) => html`<button class="risultato" onClick=${() => leggi(r.percorso)}><b>${r.nome}</b><span>${r.estratto}</span></button>`))
        : voci === null ? html`<span class="carica"></span>` :
          ordine.filter((g) => gruppi[g]).map((g) => html`<h3>${g}</h3>${gruppi[g].map((v) => html`
            <button class=${`voce-app ${doc && doc.percorso === v.percorso ? "attiva" : ""} ${v.abbandonato ? "abbandonato" : ""}`}
              onClick=${() => leggi(v.percorso)} title=${v.percorso}>
              <span class=${`pallino ${v.colore}`}></span><span class="n">${v.nome}</span><span class="g num">${etaTesto(v.giorni)}</span></button>`)}`)}
    </nav>
    <${Maniglia} tipo="appunti" />
    <article class="lettore" ref=${lettore} onClick=${clicLettore}>
      ${doc && html`<div class="lettore-testa">
        <span class="percorso">${doc.percorso}</span><span class="pallino ${etaClasse(doc.giorni) === "e3" ? "rosso" : "verde"}"></span>
        <span class="percorso">${etaTesto(doc.giorni)}</span><span class="spazio"></span>
        ${modifica === null ? html`
          <button class="btn piccolo" onClick=${() => setModifica(doc.testo)}>${Icona.matita()}Modifica</button>
          <button class="btn piccolo fantasma" onClick=${() => api("apri_esterno", doc.percorso)}>${Icona.esterno()}Apri fuori</button>`
        : html`<button class="btn piccolo fantasma" onClick=${() => { setModifica(null); setConflitto(false); }}>Annulla</button>
          <button class="btn piccolo primario" onClick=${salva}>${Icona.salva()}Salva</button>`}
      </div>
      ${conflitto && html`<div class="messaggio">Il file è cambiato su disco mentre lo modificavi (forse l'ha aggiornato Claude).
        <button class="btn piccolo" onClick=${() => { setModifica(null); leggi(doc.percorso); }}>Ricarica</button></div>`}
      ${modifica === null ? html`<div class="md" dangerouslySetInnerHTML=${{ __html: htmlDoc }}></div>`
        : html`<textarea class="editor" value=${modifica} onInput=${(e) => setModifica(e.target.value)} spellcheck="false" aria-label="Testo dell'appunto"></textarea>`}`}
    </article>
  </div>`;
}

// ---------- Inbox ----------
function PaginaInbox({ apriChat, menuInbox }) {
  const [voci, setVoci] = useState(null);
  const [sopra, setSopra] = useState(0);
  const carica = async () => { const r = await api("inbox"); setVoci(r.inbox || []); };
  useEffect(() => { carica(); }, []);
  useEvento((n) => { if (n === "inbox-aggiunti") { setSopra(0); carica(); } });
  // la copia la fa Python (riceve i percorsi veri); qui solo il riquadro di rilascio
  const conFile = (e) => e.dataTransfer && [...e.dataTransfer.types].includes("Files");
  return html`<div class="pagina pagina-inbox"
      onDragEnter=${(e) => conFile(e) && setSopra((n) => n + 1)} onDragLeave=${(e) => conFile(e) && setSopra((n) => Math.max(0, n - 1))}
      onDrop=${() => setSopra(0)}>
    ${sopra > 0 && html`<div class="rilascio"><div>${Icona.inbox()}<b>Rilascia per aggiungere all'Inbox</b><span>I file vengono copiati con la data di oggi davanti al nome</span></div></div>`}
    <header class="testata"><div><h1 class="piccolo">Inbox</h1></div>
      <div class="azioni"><button class="btn primario" disabled=${!voci || voci.length === 0}
        onClick=${() => apriChat("nuova", null, "smista l'inbox")}>Smista l'inbox</button></div></header>
    <p class="sotto-testata">Trascina qui i file da smistare: l'app li copia nella cartella Inbox del second brain.</p>
    ${voci === null ? html`<span class="carica"></span>` : voci.length === 0
      ? html`<div class="scheda vuoto" style="margin-top:22px"><strong>Inbox vuota</strong>Le note al volo e i file da smistare finiscono qui. Puoi trascinare dei file in questa pagina.</div>`
      : html`<div class="inbox-griglia">${voci.map((v) => html`<div class="scheda inbox-voce" tabindex="0" onContextMenu=${(e) => menuInbox(e, v, carica)}
          title="Tasto destro: apri, smista, sposta, rinomina, elimina">
          <b>${v.nome}</b>${v.anteprima ? html`<div class="md" dangerouslySetInnerHTML=${{ __html: DOMPurify.sanitize(marked.parse(v.anteprima)) }}></div>` : ""}
          <div class="riga"><span class="num">${quando(v.modificato)}</span><span class="spazio" style="flex:1"></span>
            <button class="btn piccolo fantasma" onClick=${() => api("apri_esterno", v.percorso)}>${Icona.esterno()}Apri</button></div></div>`)}</div>`}
  </div>`;
}

// ---------- terminali ----------
function Maniglia({ tipo = "terminale" }) {
  const el = useRef(null), trascina = useRef(false), ratio = useRef(.48);
  const [attiva, setAttiva] = useState(false), [orizzontale, setOrizzontale] = useState(false);
  const note = tipo === "appunti";
  const misure = () => {
    const box = el.current && el.current.closest(note ? ".appunti" : ".app");
    if (!box) return null;
    const verticale = note ? box.clientWidth < 600 : box.clientWidth <= 1100;
    const lato = note || verticale ? 0 : (box.querySelector(".laterale")?.offsetWidth || 0);
    const totale = verticale ? box.clientHeight - (note ? 6 : 36) : box.clientWidth - lato - (note ? 6 : 8);
    return { box, verticale, totale, key: `${note ? "appunti" : "term"}Ratio${verticale ? "H" : ""}` };
  };
  const applica = (valore, salva = false) => {
    const m = misure(); if (!m || m.totale < 1) return;
    const predefinito = note ? (m.verticale ? .28 : .25) : .48;
    const valoreValido = Number.isFinite(valore) && valore > 0 ? valore : predefinito;
    const minimo = note ? (m.verticale ? 90 : 145) : (m.verticale ? 170 : 340);
    const altroMinimo = note ? (m.verticale ? 150 : 260) : (m.verticale ? 180 : 300);
    const massimo = Math.max(minimo, m.totale - altroMinimo);
    const px = Math.max(Math.min(minimo, m.totale / 2), Math.min(massimo, m.totale * valoreValido));
    ratio.current = px / m.totale;
    document.documentElement.style.setProperty(`--${note ? "appunti" : "term"}-${m.verticale ? "h" : "w"}`, `${px}px`);
    setOrizzontale(m.verticale);
    if (salva) localStorage.setItem(m.key, String(ratio.current));
  };
  useEffect(() => {
    const aggiorna = () => { const m = misure(); if (m) applica(Number(localStorage.getItem(m.key))); };
    aggiorna();
    const osservatore = new ResizeObserver(aggiorna);
    osservatore.observe(el.current.closest(note ? ".appunti" : ".app"));
    window.addEventListener("resize", aggiorna);
    return () => { osservatore.disconnect(); window.removeEventListener("resize", aggiorna); };
  }, []);
  const muovi = (e) => {
    if (!trascina.current) return;
    const m = misure(), r = m.box.getBoundingClientRect();
    const scala = r.width / m.box.clientWidth;
    const px = m.verticale ? (note ? e.clientY - r.top : r.bottom - e.clientY - 28 * scala) / scala
      : (note ? e.clientX - r.left : r.right - e.clientX) / scala;
    applica(px / m.totale, true);
  };
  const fine = () => { trascina.current = false; setAttiva(false); };
  return html`<div ref=${el} class=${`maniglia ${note ? "maniglia-appunti" : ""} ${attiva ? "attiva" : ""}`}
    onPointerDown=${(e) => { e.preventDefault(); trascina.current = true; setAttiva(true); e.currentTarget.setPointerCapture(e.pointerId); }}
    onPointerMove=${muovi} onPointerUp=${fine} onPointerCancel=${fine}
    onDoubleClick=${() => { const m = misure(); localStorage.removeItem(m.key); applica(0); }}
    onKeyDown=${(e) => { if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) { e.preventDefault(); const cresce = e.key === "ArrowRight" || e.key === "ArrowDown"; applica(ratio.current + (cresce === note ? .04 : -.04), true); } if (e.key === "Home") applica(0, true); }}
    role="separator" tabIndex="0" aria-orientation=${orizzontale ? "horizontal" : "vertical"}
    aria-label=${note ? "Ridimensiona elenco appunti" : "Ridimensiona terminale"} title="Trascina per ridimensionare · doppio clic per ripristinare"></div>`;
}

const console_ = new Map();
function Schermo({ scheda, attiva, salvaChat, apriChat, chiudi }) {
  const el = useRef(null);
  const [uscita, setUscita] = useState(null);
  useEffect(() => {
    if (!console_.has(scheda.id)) console_.set(scheda.id, new Console(el.current, scheda.url, { allUscita: (c) => setUscita(c) }));
    return undefined;
  }, []);
  useEffect(() => { const c = console_.get(scheda.id); if (attiva && c) setTimeout(() => { c.adatta(true); c.fuoco(); }, 30); }, [attiva]);
  const chiusa = scheda.chiusa || uscita !== null;
  return html`<div class=${`schermo ${attiva ? "attivo" : ""}`} ref=${el}>
    ${chiusa && html`<div class="fine-chat">
      <p>${scheda.stato === "errore_salvataggio" ? "Salvataggio non riuscito" : ["non_salvata", "errore_salvataggio"].includes(scheda.stato) ? "Chat chiusa senza salvare gli appunti." : scheda.stato === "in_corso" ? "Chat chiusa: sto salvando gli appunti in background." : "Chat chiusa."}</p>
      ${scheda.sessione && ["non_salvata", "errore_salvataggio"].includes(scheda.stato) && html`<button class="btn piccolo primario" onClick=${() => { chiudi(scheda.id); salvaChat(scheda.sessione); }}>${Icona.salva()}${scheda.stato === "errore_salvataggio" ? "Riprova" : "Salva appunti"}</button>`}
      ${scheda.sessione && html`<button class="btn piccolo" onClick=${() => { chiudi(scheda.id); apriChat("riprendi", scheda.sessione); }}>${Icona.riprendi()}Riapri</button>`}
      <button class="btn piccolo fantasma" onClick=${() => chiudi(scheda.id)}>Chiudi</button></div>`}
  </div>`;
}

// Le chat portano il nome dell'assistente accanto al titolo; alcune
// azioni (eliminare, aprire in un'altra cartella, duplicare) esistono solo per quelle di Claude
const NOMI_ASSISTENTI = { claude: "Claude", codex: "Codex", agy: "Antigravity" };
const diClaude = (c) => !c.assistente || c.assistente === "claude";
const Assistente = ({ c }) => NOMI_ASSISTENTI[c.assistente || "claude"] ? html`<span class="etichetta-assistente">${NOMI_ASSISTENTI[c.assistente || "claude"]}</span>` : null;

// con quale assistente e modello parte una chat nuova: stesse impostazioni di Impostazioni > Terminale
const MODELLI_PER = {
  claude: [["predefinito", "Predefinito"], ["fable", "Fable"], ["opus", "Opus"], ["sonnet", "Sonnet"], ["haiku", "Haiku"]],
  agy: [["predefinito", "Predefinito"], ["gemini-4-argon-high", "Argon High"], ["gemini-4-argon-medium", "Argon Med"], ["gemini-4-argon-low", "Argon Low"], ["gemini-3.8-flash-high", "Flash High"], ["gemini-3.8-flash-low", "Flash Low"]],
};
const CHIAVE_MODELLO = { claude: "modello_chat", codex: "modello_codex", agy: "modello_agy" };
function SceltaChat({ imp, mettiImp, assistenti }) {
  if (!imp) return null;
  const installato = (id) => (assistenti.find((a) => a.id === id) || {}).installato;
  const scelto = installato(imp.assistente_chat) ? imp.assistente_chat : "claude";
  const chiave = CHIAVE_MODELLO[scelto] || "modello_chat";
  const modelli = MODELLI_PER[scelto] || MODELLI_PER.claude;
  const mod = imp[chiave] || "predefinito";
  return html`<div class="scelta-chat">
    ${assistenti.length > 1 && html`<span class="imp-seg" role="radiogroup" aria-label="Assistente">${assistenti.map((a) => html`<button role="radio"
      aria-checked=${scelto === a.id} class=${scelto === a.id ? "scelto" : ""} disabled=${!a.installato}
      title=${a.installato ? "" : "Non installato su questo PC"} onClick=${() => mettiImp("assistente_chat", a.id)}>${a.nome}</button>`)}</span>`}
    ${scelto === "codex"
      ? html`<${SceltaCodex} valore=${mod} cambia=${(v) => mettiImp(chiave, v)} />`
      : html`<span class="imp-seg" role="radiogroup" aria-label="Modello">${modelli.map(([v, n]) => html`<button role="radio"
          aria-checked=${mod === v} class=${mod === v ? "scelto" : ""} onClick=${() => mettiImp(chiave, v)}>${n}</button>`)}</span>`}
  </div>`;
}

function ColonnaTerminali({ schede, attiva, setAttiva, chiudi, apriChat, salvaChat, modo, setModo, home, menuScheda, imp, mettiImp, assistenti, sceltaNuova, setSceltaNuova }) {
  useEffect(() => { for (const id of [...console_.keys()]) if (!schede.some((s) => s.id === id)) { console_.get(id).distruggi(); console_.delete(id); } }, [schede]);
  useEffect(() => { const c = console_.get(attiva); if (c && !sceltaNuova) setTimeout(() => c.adatta(true), 60); }, [modo, sceltaNuova]);
  const ultima = home && home.chat && home.chat.find((c) => c.stato !== "aperta");
  const mostraScelta = schede.length === 0 || sceltaNuova;
  const avviaScelta = () => apriChat("nuova", null, null, null, null, true);
  return html`<section class="colonna-term" aria-label="Terminali di Claude Code">
    <div class="linguette">
      <div class="linguette-scorri" role="tablist">
        ${schede.map((s) => html`<div class=${`linguetta ${!sceltaNuova && s.id === attiva ? "attiva" : ""}`} role="tab" aria-selected=${!sceltaNuova && s.id === attiva} tabindex="0"
            onClick=${() => setAttiva(s.id)} onAuxClick=${(e) => e.button === 1 && chiudi(s.id)} onContextMenu=${(e) => menuScheda(e, s)} title=${s.titolo}>
          <span class=${`pallino ${s.chiusa ? "grigio" : "giallo"}`}></span><span class="t">${s.titolo}</span>
          <span class="x" role="button" aria-label="Chiudi" onClick=${(e) => { e.stopPropagation(); chiudi(s.id); }}>${Icona.chiudi()}</span></div>`)}
      </div>
      <div class="strumenti">
        <button class="icona-btn" title="Nuova chat (Ctrl+Shift+T)" aria-label="Nuova chat" onClick=${() => apriChat()}>${Icona.piu()}</button>
        <button class="icona-btn" title=${modo === "ampio" ? "Riduci il terminale" : "Allarga il terminale"} aria-label="Allarga o riduci"
          onClick=${() => setModo(modo === "ampio" ? "normale" : "ampio")}>${modo === "ampio" ? Icona.restringi() : Icona.allarga()}</button>
        <button class="icona-btn" title="Nascondi il terminale" aria-label="Nascondi il terminale" onClick=${() => setModo("nascosto")}>${Icona.chiudi()}</button>
      </div>
    </div>
    <div class="schermi">
      ${schede.map((s) => html`<${Schermo} key=${s.id} scheda=${s} attiva=${!mostraScelta && s.id === attiva}
          salvaChat=${salvaChat} apriChat=${apriChat} chiudi=${chiudi} />`)}
      ${mostraScelta && html`<div class="term-vuoto">
        <h3>${schede.length ? "Nuova chat" : "Claude Code, qui accanto"}</h3>
        <p>${schede.length ? "Scegli con quale assistente e modello aprire la nuova linguetta." : "Ogni chat si apre in una linguetta. Puoi tenerne aperte più di una e passare dall'una all'altra."}</p>
        <${SceltaChat} imp=${imp} mettiImp=${mettiImp} assistenti=${assistenti} />
        <div class="azioni">
          ${schede.length > 0 && html`<button class="btn fantasma" onClick=${() => setSceltaNuova(false)}>Annulla</button>`}
          <button class="btn primario" onClick=${avviaScelta}>${Icona.piu()}${schede.length ? "Avvia chat" : "Nuova chat"}</button>
          ${!schede.length && ultima && html`<button class="btn" onClick=${() => apriChat("riprendi", ultima.id)} title=${ultima.etichetta}>${Icona.riprendi()}Riprendi l'ultima</button>`}</div>
      </div>`}
    </div>
  </section>`;
}

// ---------- barra di stato ----------
// uso del piano: barra, percentuale e quando si azzera (5 ore: tra quanto; settimana: giorno e ora)
function Uso({ nome, w, settimana }) {
  if (!w) return "";
  const p = w.percentuale;
  const livello = p >= 95 ? "pieno" : p >= 80 ? "alto" : "";
  let quando = "";
  if (w.azzera) {
    const s = w.azzera - Date.now() / 1000, d = new Date(w.azzera * 1000);
    quando = settimana ? `${GG[d.getDay()]} ${ora(d)}` : s < 3600 ? `${Math.ceil(s / 60)}m` : `${Math.floor(s / 3600)}h${String(Math.floor(s % 3600 / 60)).padStart(2, "0")}`;
  }
  return html`<span class="uso" title=${`${nome === "5h" ? "Finestra di 5 ore" : "Settimana"}: ${p}% usato${quando ? `, si azzera ${settimana ? "" : "tra "}${quando}` : ""}`}>
    ${nome}<span class=${`uso-barra ${livello}`}><i style=${`width:${Math.max(p ? 4 : 0, p)}%`}></i></span><b class="num">${p}%</b>${quando && html`<span class="uso-reset num">↻ ${quando}</span>`}</span>`;
}

function BarraStato({ git, home, schede, attiva, sceltaNuova, imp, orologio, modo, setModo, uso, aggiornamento, aggiorna, versione, remoti }) {
  const altrove = ((remoti && remoti.attivo && remoti.pc) || []).map((p) => [p.pc, p.chat.filter((c) => ["non_salvata", "errore_salvataggio"].includes(c.stato)).length]).filter(([, n]) => n);
  const aperte = schede.filter((s) => !s.chiusa).length;
  const schedaAttiva = !sceltaNuova && schede.find((s) => s.id === attiva && !s.chiusa);
  const assAttivo = (schedaAttiva && schedaAttiva.assistente) || (imp && imp.assistente_chat) || "claude";
  const nomeAss = { claude: "Claude", codex: "Codex", agy: "Antigravity" }[assAttivo] || "Claude";
  const uAss = (uso && uso.assistenti && uso.assistenti[assAttivo]) || (assAttivo === "claude" ? uso : null);
  const vecchio = uAss && uAss.noto && uAss.aggiornato && Date.now() / 1000 - uAss.aggiornato > 600;
  return html`<footer class="stato">
    ${versione && html`<span class="versione" title="Versione di Second Brain Studio">v${versione}</span>`}
    ${git && git.ramo && html`<span title="Ramo del second brain">${git.ramo}</span>`}
    ${git && html`<span>${git.modifiche ? `${git.modifiche} file da caricare` : "nessuna modifica locale"}</span>`}
    ${home && home.sync === "rosso" && html`<span style="color:var(--terracotta-chiaro)">appunti nuovi su GitHub</span>`}
    ${altrove.map(([pc, n]) => html`<span class="altrove" title="Chat chiuse senza salvare gli appunti su un altro PC">${n === 1 ? "1 non salvata" : `${n} non salvate`} su ${pc}</span>`)}
    <span class="spazio"></span>
    ${aggiornamento && html`<button class="aggiorna-btn" onClick=${aggiorna} title=${`Installa la versione ${aggiornamento === true ? "nuova" : aggiornamento} e riapre l'app`}>${Icona.ricarica()}Aggiornamento pronto</button>`}
    ${uAss && uAss.noto ? html`<span class=${`uso-gruppo ${vecchio ? "vecchio" : ""}`}
        title=${vecchio ? `Ultimo dato alle ${ora(new Date(uAss.aggiornato * 1000))}: si aggiorna quando una chat di ${nomeAss} è aperta` : `Utilizzo di ${nomeAss}`}>
      <b>${nomeAss}</b><${Uso} nome="5h" w=${uAss.five_hour} /><${Uso} nome="7g" w=${uAss.seven_day} settimana /></span>`
      : uAss && (uAss.cinque_ore || uAss.sette_giorni || assAttivo !== "claude") && html`<span class="uso-gruppo"
        title=${`Messaggi inviati a ${nomeAss} nelle ultime 5 ore e negli ultimi 7 giorni`}>
      <b>${nomeAss}</b><span class="uso">5h <b class="num">${uAss.cinque_ore || 0}</b> msg</span><span class="uso">7g <b class="num">${uAss.sette_giorni || 0}</b> msg</span></span>`}
    <span>${aperte === 1 ? "1 chat aperta" : `${aperte} chat aperte`}</span>
    ${modo === "nascosto" && html`<button onClick=${() => setModo("normale")}>mostra terminale</button>`}
    <span class="num">${GG[orologio.getDay()]} ${orologio.getDate()} ${MM[orologio.getMonth()]} ${ora(orologio)}</span>
  </footer>`;
}

// prima del second brain: la procedura del primo avvio; poi l'app vera
function Radice() {
  const [conf, setConf] = useState(null);
  const [prima, setPrima] = useState(null);
  const [imp, setImp] = useState(null);
  useEffect(() => { (async () => {
    const i = await api("impostazioni"); const x = i && !i.errore ? i.impostazioni : {};
    setImp(x); applicaAspetto(x);
    const s = await api("configurazione"); setConf(s && !s.errore ? s : { configurato: true });
  })(); }, []);
  // "Come Windows": il tema segue il sistema anche mentre l'app è aperta
  useEffect(() => { const m = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)");
    if (!m) return; const f = () => imp && imp.tema === "sistema" && applicaAspetto(imp); m.addEventListener("change", f); return () => m.removeEventListener("change", f); }, [imp]);
  if (!conf || !imp) return null;
  if (!conf.configurato) return html`<${PrimoAvvio} api=${api} useEvento=${useEvento}
    fine=${(prompt) => { setPrima(prompt || null); setConf({ ...conf, configurato: true }); }} />`;
  return html`<${App} primaChat=${prima} impIniziali=${imp} primoAvvio=${() => setConf({ ...conf, configurato: false })} />`;
}

render(html`<${Radice} />`, document.getElementById("app"));
