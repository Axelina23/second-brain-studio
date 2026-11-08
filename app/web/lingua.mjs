// Interfaccia in inglese. L'app e' scritta in italiano; con la lingua "en" un osservatore del
// DOM traduce testi, title, placeholder e aria-label usando il dizionario di lingua-en.mjs
// (frasi fisse) e alcune regole per i testi con numeri e date. L'originale resta in memoria,
// cosi' tornando all'italiano si ripristina senza ricaricare.
// Non si traducono mai i contenuti dell'utente: appunti (.md, .editor), terminali (.xterm),
// campi di testo, titoli e anteprime delle chat, e tutto cio' che sta in [data-no-trad].
import { EN, REGOLE } from "./lingua-en.mjs";

const SALTA = ".xterm, .md, .editor, textarea, input, select, code, .chat-riga .titolo, .chat-riga .primo:not(.conteggio), .lat-chat span:last-child, .linguetta-titolo, [data-no-trad]";
const ATTRIBUTI = ["title", "placeholder", "aria-label"];
let lingua = "it";
let osservatore = null;
const originali = new WeakMap();  // nodo di testo -> [italiano, tradotto]

export function traduci(s) {
  if (lingua !== "en" || !s) return s;
  const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(s);
  const [, prima, corpo, dopo] = m;
  if (!corpo) return s;
  if (Object.prototype.hasOwnProperty.call(EN, corpo)) return prima + EN[corpo] + dopo;
  const unito = corpo.replace(/\s+/g, " ");   // testi spezzati su piu' righe nel codice
  if (unito !== corpo && Object.prototype.hasOwnProperty.call(EN, unito)) return prima + EN[unito] + dopo;
  for (const [re, f] of REGOLE) {
    const r = re.exec(corpo);
    if (r) return prima + f(...r.slice(1)) + dopo;
  }
  return s;
}

function daSaltare(el) { return !el || (el.closest && el.closest(SALTA)); }

function testo(nodo) {
  if (daSaltare(nodo.parentElement)) return;
  const noto = originali.get(nodo);
  if (noto && nodo.data === noto[1]) return;          // gia' tradotto da noi
  const it = nodo.data;
  const en = traduci(it);
  if (en !== it) { originali.set(nodo, [it, en]); nodo.data = en; }
  else originali.delete(nodo);
}

// i campi di testo si saltano per il contenuto, ma segnaposto ed etichette sono interfaccia
const CAMPO = "input, textarea, select";
function attributi(el) {
  if (daSaltare(el) && !(el.matches && el.matches(CAMPO) && !el.closest(".xterm"))) return;
  for (const a of ATTRIBUTI) {
    if (!el.hasAttribute(a)) continue;
    const v = el.getAttribute(a), salvato = el.dataset[`it_${a.replace("-", "_")}`];
    if (salvato !== undefined && v === traduci(salvato)) continue;
    const en = traduci(v);
    if (en !== v) { el.dataset[`it_${a.replace("-", "_")}`] = v; el.setAttribute(a, en); }
  }
}

function passa(radice) {
  if (radice.nodeType === 3) { testo(radice); return; }
  if (radice.nodeType !== 1) return;
  if (daSaltare(radice)) { attributi(radice); return; }
  attributi(radice);
  const w = document.createTreeWalker(radice, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  let n;
  while ((n = w.nextNode())) { if (n.nodeType === 3) testo(n); else attributi(n); }
}

function ripristina() {
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  let n;
  while ((n = w.nextNode())) {
    if (n.nodeType === 3) { const o = originali.get(n); if (o && n.data === o[1]) n.data = o[0]; originali.delete(n); continue; }
    for (const a of ATTRIBUTI) {
      const k = `it_${a.replace("-", "_")}`;
      if (n.dataset && n.dataset[k] !== undefined) { n.setAttribute(a, n.dataset[k]); delete n.dataset[k]; }
    }
  }
}

export function impostaLingua(nuova) {
  nuova = nuova === "en" ? "en" : "it";
  if (nuova === lingua) return;
  lingua = nuova;
  document.documentElement.lang = nuova;
  if (nuova === "en") {
    passa(document.body);
    osservatore = new MutationObserver((cambi) => {
      for (const c of cambi) {
        if (c.type === "characterData") testo(c.target);
        else if (c.type === "attributes") attributi(c.target);
        else c.addedNodes.forEach(passa);
      }
    });
    osservatore.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRIBUTI });
  } else {
    if (osservatore) osservatore.disconnect();
    osservatore = null;
    ripristina();
  }
}

export const linguaAttiva = () => lingua;
