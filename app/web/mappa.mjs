// Pagina "Mappa": il second brain visto in cinque modi, a scelta (la scelta resta memorizzata).
//  - Grafo 2D e Grafo 3D: appunti collegati alla loro area e agli appunti che citano;
//  - Mosaico (treemap): aree divise nei loro appunti, grandi quanto il contenuto;
//  - Raggiera (sunburst): second brain al centro, poi aree, poi appunti;
//  - Attivita': calendario degli ultimi 6 mesi dalla cronologia git + aree dell'ultimo mese.
// Opzioni: colore per area o per freschezza, etichette, aree nascoste. Disegnato a mano
// (SVG e canvas), senza librerie: l'app resta leggera.
import { html, useState, useEffect, useRef, useMemo } from "./vendor/preact-htm.mjs";
import { traduci } from "./lingua.mjs";

// colori dei gruppi fissi e delle aree note; le altre aree (Lavoro, Work, Famiglia...) prendono
// un colore della tavolozza scelto dal nome, cosi' resta lo stesso a ogni apertura
const COLORI_NOTI = { Io: "#f2c94c", "Università": "#e08460", Progetti: "#4f7fd0", Vita: "#8cc29a", Sistema: "#7cc4c4", Generali: "#e4dfd2" };
const ALTRI_COLORI = ["#e08460", "#8cc29a", "#c58fd6", "#e6a3b8", "#d9a066", "#9fc0e8", "#b8c46c"];
const codice = (t) => [...t].reduce((h, c) => (h * 31 + c.codePointAt(0)) >>> 0, 7);
export const COLORI_GRUPPO = new Proxy(COLORI_NOTI, {
  get: (o, g) => o[g] || (typeof g === "string" ? ALTRI_COLORI[codice(g) % ALTRI_COLORI.length] : undefined) });
// ordine dei gruppi: Io, poi le aree in ordine alfabetico, poi Progetti, Sistema, Generali
const FISSI_IN_FONDO = ["Progetti", "Sistema", "Generali"];
export function ordinaGruppi(nomi) {
  const ci = new Set(nomi);
  const aree = [...ci].filter((g) => g !== "Io" && !FISSI_IN_FONDO.includes(g)).sort((a, b) => a.localeCompare(b));
  return [...(ci.has("Io") ? ["Io"] : []), ...aree, ...FISSI_IN_FONDO.filter((g) => ci.has(g))];
}
const COLORI_ETA = { verde: "#8cc29a", giallo: "#f2c94c", rosso: "#e08460" };
const VISTE = [["grafo2d", "Grafo 2D"], ["grafo3d", "Grafo 3D"], ["mosaico", "Mosaico"], ["raggiera", "Raggiera"], ["attivita", "Attività"], ["metro", "Metro"], ["citta", "Città"], ["orbite", "Orbite"]];
const DESCRIZIONI = {
  grafo2d: "Ogni punto è un appunto, legato alla sua area e agli appunti che cita. Cerchi vuoti: fermi da più di due settimane.",
  grafo3d: "Lo stesso grafo nello spazio: trascina per ruotare, rotella per lo zoom.",
  mosaico: "Ogni riquadro è un appunto, grande quanto il suo contenuto: si vede cosa pesa e cosa è fermo.",
  raggiera: "Al centro il second brain, poi le aree, poi gli appunti. Passa sopra un settore per i dettagli.",
  attivita: "Quanti appunti sono cambiati ogni giorno, dalla cronologia di GitHub.",
  metro: "Ogni area è una linea, gli appunti sono le fermate: dal più fresco al più vecchio. Tratteggi: interscambi tra aree.",
  citta: "Ogni appunto è un palazzo alto quanto il suo contenuto. Finestre accese: aggiornato da poco; buio: dimenticato.",
  orbite: "Più un appunto è lontano dal centro, più tempo è passato dall'ultima modifica.",
};
const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];

const leggi = (k, d) => { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (_) { return d; } };
const scrivi = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} };
const eta = (g) => g < 1 ? "oggi" : g < 2 ? "ieri" : `${Math.floor(g)} g`;
const colorePer = (n, modo) => n.hub || modo === "area" ? (COLORI_GRUPPO[n.gruppo] || "#e4dfd2") : (COLORI_ETA[n.colore] || "#8ea0a8");

// generatore a seme fisso: le disposizioni restano uguali tra un'apertura e l'altra
function generatore(seme = 1742) { return () => { seme = (seme * 16807) % 2147483647; return seme / 2147483647; }; }

// ---------- simulazione di forze (2D e 3D) ----------
function simula(nodi, archi, tre) {
  const caso = generatore();
  const gruppi = [...new Set(nodi.map((n) => n.gruppo))];
  const hub = gruppi.map((g, i) => {
    const a = i / gruppi.length * 2 * Math.PI, b = tre ? (caso() - .5) * 1.6 : 0;
    return { id: `#${g}`, nome: g, gruppo: g, hub: true, x: Math.cos(a) * 220, y: Math.sin(a) * 220 * (tre ? .8 : 1) + b * 60, z: tre ? Math.sin(b) * 180 : 0 };
  });
  const tutti = [...hub, ...nodi.map((n) => ({ ...n }))];
  const per = new Map(tutti.map((n) => [n.id, n]));
  for (const n of tutti) if (!n.hub) {
    const c = per.get(`#${n.gruppo}`);
    n.x = c.x + (caso() - .5) * 90; n.y = c.y + (caso() - .5) * 90; n.z = tre ? c.z + (caso() - .5) * 90 : 0;
  }
  const legami = [...nodi.map((n) => ({ a: per.get(`#${n.gruppo}`), b: per.get(n.id), l: 90, area: true })),
    ...archi.map((e) => ({ a: per.get(e.da), b: per.get(e.a), l: 170 })).filter((e) => e.a && e.b)];
  for (const n of tutti) n.grado = 0;
  for (const { a, b, area } of legami) if (!area) { a.grado++; b.grado++; }
  const giri = 300;
  for (let it = 0; it < giri; it++) {
    const t = 1 - it / giri;
    for (let i = 0; i < tutti.length; i++) for (let j = i + 1; j < tutti.length; j++) {
      const a = tutti[i], b = tutti[j];
      let dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
      const d2 = dx * dx + dy * dy + dz * dz + .01;
      if (d2 > 250000) continue;
      const f = (a.hub && b.hub ? 9000 : a.hub || b.hub ? 3200 : 2000) / d2, d = Math.sqrt(d2);
      dx /= d; dy /= d; dz /= d;
      a.x -= dx * f * t; a.y -= dy * f * t; a.z -= dz * f * t; b.x += dx * f * t; b.y += dy * f * t; b.z += dz * f * t;
      const min = a.hub || b.hub ? 70 : 34;
      if (d < min) { const k = (min - d) / 2; a.x -= dx * k; a.y -= dy * k; a.z -= dz * k; b.x += dx * k; b.y += dy * k; b.z += dz * k; }
    }
    for (const { a, b, l } of legami) {
      const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z, d = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1, f = (d - l) * .04 * t;
      a.x += dx / d * f; a.y += dy / d * f; a.z += dz / d * f; b.x -= dx / d * f; b.y -= dy / d * f; b.z -= dz / d * f;
    }
    for (const n of tutti) { n.x *= .997; n.y *= .997; n.z *= .997; }
  }
  return { tutti, legami };
}

function vicini(legami, id) {
  if (!id) return null;
  const s = new Set([id]);
  for (const { a, b } of legami) { if (a.id === id) s.add(b.id); if (b.id === id) s.add(a.id); }
  return s;
}

const mostraEtichetta = (n, modo, acceso, vic) =>
  modo === "tutte" || n.hub || n.id === acceso || (vic && vic.has(n.id)) || (modo === "principali" && n.grado >= 2);

// ---------- grafo 2D ----------
function Grafo2D({ dati, opz, vai, dim }) {
  const [acceso, setAcceso] = useState(null);
  const [vista, setVista] = useState({ x: 0, y: 0, k: 1 });
  const trascina = useRef(null);
  const disposto = useMemo(() => {
    const { tutti, legami } = simula(dati.nodi, dati.archi, false);
    const xs = tutti.map((n) => n.x), ys = tutti.map((n) => n.y);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const s = Math.min((dim.w - 240) / Math.max(1, x1 - x0), (dim.h - 90) / Math.max(1, y1 - y0), 1.6);
    for (const n of tutti) { n.px = 60 + (n.x - x0) * s + (dim.w - 240 - (x1 - x0) * s) / 2; n.py = 30 + (n.y - y0) * s + (dim.h - 90 - (y1 - y0) * s) / 2; }
    return { tutti, legami };
  }, [dati, dim.w, dim.h]);
  const vic = useMemo(() => vicini(disposto.legami, acceso), [disposto, acceso]);
  const ruota = (e) => { e.preventDefault(); setVista((v) => ({ ...v, k: Math.min(3, Math.max(.4, v.k * (e.deltaY < 0 ? 1.1 : .9))) })); };
  const giu = (e) => { if (e.target.closest(".nodo")) return; trascina.current = { x: e.clientX - vista.x, y: e.clientY - vista.y }; };
  const muovi = (e) => { if (trascina.current) setVista((v) => ({ ...v, x: e.clientX - trascina.current.x, y: e.clientY - trascina.current.y })); };
  return html`<svg class="mappa-svg" onWheel=${ruota} onMouseDown=${giu} onMouseMove=${muovi}
      onMouseUp=${() => (trascina.current = null)} onMouseLeave=${() => (trascina.current = null)} role="img" aria-label="Grafo degli appunti">
    <g transform=${`translate(${vista.x} ${vista.y}) scale(${vista.k})`}>
      ${disposto.legami.map(({ a, b, area }) => {
        const on = vic && vic.has(a.id) && vic.has(b.id);
        return html`<line class=${`arco ${on ? "acceso" : ""} ${area ? "area" : ""}`} x1=${a.px} y1=${a.py} x2=${b.px} y2=${b.py} opacity=${vic && !on ? .18 : 1} />`;
      })}
      ${disposto.tutti.map((n) => {
        const col = colorePer(n, opz.colore), r = n.hub ? 10 : 3.5 + Math.min(6, Math.sqrt(n.peso || 0) / 16);
        const fermo = !n.hub && n.colore === "rosso";
        return html`<g class=${`nodo ${n.hub ? "hub" : ""}`} opacity=${vic && !vic.has(n.id) ? .3 : 1}
            onMouseEnter=${() => setAcceso(n.id)} onMouseLeave=${() => setAcceso(null)} onClick=${() => !n.hub && vai(n.id)}>
          <circle cx=${n.px} cy=${n.py} r=${r} stroke=${col} stroke-width=${fermo ? 1.6 : n.hub ? 2.5 : 0}
            style=${`fill:${fermo ? "var(--notte)" : n.hub ? `color-mix(in srgb, ${col} 28%, #0e1a22)` : col}`} />
          ${mostraEtichetta(n, opz.etichette, acceso, vic) && html`<text x=${n.px + r + 4} y=${n.py + 3.5}>${n.nome}${n.id === acceso && !n.hub ? ` · ${eta(n.giorni)}` : ""}</text>`}
        </g>`;
      })}
    </g></svg>`;
}

// ---------- grafo 3D (canvas) ----------
function Grafo3D({ dati, opz, vai, dim }) {
  const tela = useRef(null);
  const stato = useRef({ yaw: .6, pitch: -.25, zoom: 1, auto: true, acceso: null, trascina: null });
  const disposto = useMemo(() => simula(dati.nodi, dati.archi, true), [dati]);
  useEffect(() => {
    const c = tela.current, ctx = c.getContext("2d"), dpr = window.devicePixelRatio || 1;
    c.width = dim.w * dpr; c.height = dim.h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    let ciclo;
    const proietta = () => {
      const { yaw, pitch, zoom } = stato.current, cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
      const D = 900, s0 = Math.min(dim.w, dim.h) / 470 * zoom;
      for (const n of disposto.tutti) {
        const x1 = n.x * cy - n.z * sy, z1 = n.x * sy + n.z * cy, y2 = n.y * cp - z1 * sp, z2 = n.y * sp + z1 * cp;
        const s = s0 * D / (D + z2);
        n.sx = dim.w / 2 + x1 * s; n.sy = dim.h / 2 - 10 + y2 * s; n.sz = z2; n.ss = s;
      }
    };
    const disegna = () => {
      const st = stato.current;
      if (st.auto) st.yaw += .0025;
      proietta();
      ctx.clearRect(0, 0, dim.w, dim.h);
      const vic = vicini(disposto.legami, st.acceso);
      for (const { a, b, area } of disposto.legami) {
        const on = vic && vic.has(a.id) && vic.has(b.id), prof = Math.max(.12, Math.min(1, .75 - (a.sz + b.sz) / 1400));
        ctx.strokeStyle = on ? "rgba(242,201,76,.9)" : `rgba(92,124,146,${(area ? .35 : .55) * prof * (vic && !on ? .3 : 1)})`;
        ctx.lineWidth = on ? 1.6 : 1;
        ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy); ctx.stroke();
      }
      const ordinati = [...disposto.tutti].sort((p, q) => q.sz - p.sz);
      for (const n of ordinati) {
        const col = colorePer(n, opz.colore), r = (n.hub ? 9 : 3.2 + Math.min(5, Math.sqrt(n.peso || 0) / 18)) * n.ss;
        const nebbia = Math.max(.25, Math.min(1, .9 - n.sz / 700)) * (vic && !vic.has(n.id) ? .35 : 1);
        ctx.globalAlpha = nebbia;
        ctx.beginPath(); ctx.arc(n.sx, n.sy, Math.max(1.5, r), 0, Math.PI * 2);
        if (!n.hub && n.colore === "rosso") { ctx.fillStyle = "#0e1a22"; ctx.fill(); ctx.strokeStyle = col; ctx.lineWidth = 1.5; ctx.stroke(); }
        else { ctx.fillStyle = col; ctx.fill(); }
        if (mostraEtichetta(n, opz.etichette, st.acceso, vic)) {
          ctx.font = `${n.hub ? 650 : 500} ${n.hub ? 12 : 11}px Figtree, sans-serif`;
          ctx.lineWidth = 3.5; ctx.strokeStyle = "#0e1a22"; ctx.fillStyle = n.hub || n.id === st.acceso ? "#f1ece0" : "#b9c4c8";
          const t = n.id === st.acceso && !n.hub ? `${n.nome} · ${eta(n.giorni)}` : n.hub ? traduci(n.nome) : n.nome;
          ctx.strokeText(t, n.sx + r + 4, n.sy + 4); ctx.fillText(t, n.sx + r + 4, n.sy + 4);
        }
        ctx.globalAlpha = 1;
      }
      ciclo = requestAnimationFrame(disegna);
    };
    disegna();
    return () => cancelAnimationFrame(ciclo);
  }, [disposto, dim.w, dim.h, opz.colore, opz.etichette]);
  const trova = (e) => {
    const r = tela.current.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    let meglio = null, dmin = 14;
    for (const n of disposto.tutti) { const d = Math.hypot(n.sx - x, n.sy - y); if (d < dmin) { dmin = d; meglio = n; } }
    return meglio;
  };
  const st = stato.current;
  return html`<canvas ref=${tela} class="mappa-tela" style=${`width:${dim.w}px;height:${dim.h}px`}
    onMouseDown=${(e) => { st.trascina = { x: e.clientX, y: e.clientY, yaw: st.yaw, pitch: st.pitch, mosso: false }; st.auto = false; }}
    onMouseMove=${(e) => {
      if (st.trascina) {
        const dx = e.clientX - st.trascina.x, dy = e.clientY - st.trascina.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) st.trascina.mosso = true;
        st.yaw = st.trascina.yaw + dx * .006; st.pitch = Math.max(-1.4, Math.min(1.4, st.trascina.pitch + dy * .006));
      } else { const n = trova(e); st.acceso = n ? n.id : null; tela.current.style.cursor = n && !n.hub ? "pointer" : "grab"; }
    }}
    onMouseUp=${(e) => { const t = st.trascina; st.trascina = null; if (t && !t.mosso) { const n = trova(e); if (n && !n.hub) vai(n.id); } }}
    onMouseLeave=${() => { st.trascina = null; st.acceso = null; }}
    onWheel=${(e) => { e.preventDefault(); st.zoom = Math.min(3, Math.max(.4, st.zoom * (e.deltaY < 0 ? 1.1 : .9))); }}
    onDblClick=${() => { st.auto = !st.auto; }} aria-label="Grafo 3D degli appunti"></canvas>`;
}

// ---------- mosaico (treemap squarified) ----------
function squarify(voci, x, y, w, h) {
  const out = [], tot = voci.reduce((s, v) => s + v.v, 0);
  if (!tot || w <= 0 || h <= 0) return out;
  let resto = voci.map((v) => ({ ...v, a: v.v * w * h / tot }));
  while (resto.length) {
    const lato = Math.min(w, h);
    const peggiore = (riga) => {
      const s = riga.reduce((t, q) => t + q.a, 0), mx = Math.max(...riga.map((q) => q.a)), mn = Math.min(...riga.map((q) => q.a));
      return Math.max(lato * lato * mx / (s * s), s * s / (lato * lato * mn));
    };
    let riga = [resto[0]], i = 1;
    while (i < resto.length && peggiore([...riga, resto[i]]) <= peggiore(riga)) riga.push(resto[i++]);
    const s = riga.reduce((t, q) => t + q.a, 0);
    if (w >= h) { const lw = s / h; let yy = y; for (const q of riga) { const qh = q.a / lw; out.push({ ...q, x, y: yy, w: lw, h: qh }); yy += qh; } x += lw; w -= lw; }
    else { const lh = s / w; let xx = x; for (const q of riga) { const qw = q.a / lh; out.push({ ...q, x: xx, y, w: qw, h: lh }); xx += qw; } y += lh; h -= lh; }
    resto = resto.slice(i);
  }
  return out;
}

function Mosaico({ dati, opz, vai, dim }) {
  const [acceso, setAcceso] = useState(null);
  const W = dim.w - 48, H = dim.h - 60;
  const gruppi = useMemo(() => {
    const per = {};
    for (const n of dati.nodi) (per[n.gruppo] = per[n.gruppo] || []).push(n);
    const voci = Object.entries(per).map(([g, ns]) => ({ id: g, v: ns.reduce((s, n) => s + Math.max(600, n.peso || 0), 0), ns }))
      .sort((a, b) => b.v - a.v);
    return squarify(voci, 0, 0, W, H).map((g) => ({
      ...g, figli: squarify(g.ns.map((n) => ({ ...n, v: Math.max(600, n.peso || 0) })).sort((a, b) => b.v - a.v),
        g.x + 3, g.y + 24, g.w - 6, g.h - 27),
    }));
  }, [dati, W, H]);
  return html`<svg class="mappa-svg" style="cursor:default" role="img" aria-label="Mosaico degli appunti">
    <g transform="translate(24 8)">
      ${gruppi.map((g) => html`<g>
        <rect x=${g.x + 1} y=${g.y + 1} width=${Math.max(0, g.w - 2)} height=${Math.max(0, g.h - 2)} rx="6" class="mosaico-area" />
        <text x=${g.x + 10} y=${g.y + 16} class="mosaico-titolo" style=${`fill:${COLORI_GRUPPO[g.id] || "#e4dfd2"}`}>${g.w > 60 ? g.id : ""}</text>
        ${g.figli.map((n) => {
          const col = colorePer(n, opz.colore), on = acceso === n.id, mostra = n.w > 58 && n.h > 26;
          return html`<g class="mosaico-voce" onClick=${() => vai(n.id)} onMouseEnter=${() => setAcceso(n.id)} onMouseLeave=${() => setAcceso(null)}>
            <title>${n.nome} · ${eta(n.giorni)}</title>
            <rect x=${n.x + 1.5} y=${n.y + 1.5} width=${Math.max(0, n.w - 3)} height=${Math.max(0, n.h - 3)} rx="4"
              style=${`fill:color-mix(in srgb, ${col} ${on ? 58 : n.colore === "rosso" && opz.colore === "area" ? 16 : 34}%, #13242f);stroke:${on ? col : "transparent"}`} />
            ${mostra && html`<text x=${n.x + 9} y=${n.y + 18} class="mosaico-nome">${n.nome.length * 7 > n.w - 14 ? n.nome.slice(0, Math.max(3, Math.floor((n.w - 18) / 7))) + "…" : n.nome}</text>`}
            ${mostra && n.h > 44 && html`<text x=${n.x + 9} y=${n.y + 34} class="mosaico-eta">${eta(n.giorni)}</text>`}
          </g>`;
        })}</g>`)}
    </g></svg>`;
}

// ---------- raggiera (sunburst) ----------
function arco(cx, cy, r0, r1, a0, a1) {
  const g = a1 - a0 > Math.PI ? 1 : 0, p = (r, a) => `${cx + r * Math.cos(a)} ${cy + r * Math.sin(a)}`;
  return `M${p(r1, a0)}A${r1} ${r1} 0 ${g} 1 ${p(r1, a1)}L${p(r0, a1)}A${r0} ${r0} 0 ${g} 0 ${p(r0, a0)}Z`;
}

function Raggiera({ dati, opz, vai, dim }) {
  const [acceso, setAcceso] = useState(null);
  const cx = dim.w / 2, cy = 10 + (dim.h - 60) / 2, R = Math.min(dim.w - 80, dim.h - 60) / 2;
  const settori = useMemo(() => {
    const per = {};
    for (const n of dati.nodi) (per[n.gruppo] = per[n.gruppo] || []).push(n);
    const val = (n) => Math.max(800, n.peso || 0);
    const tot = dati.nodi.reduce((s, n) => s + val(n), 0) || 1;
    let a = -Math.PI / 2;
    return ordinaGruppi(Object.keys(per)).map((g) => {
      const ns = per[g].sort((p, q) => val(q) - val(p)), span = ns.reduce((s, n) => s + val(n), 0) / tot * 2 * Math.PI;
      let b = a;
      const figli = ns.map((n) => { const s = val(n) / tot * 2 * Math.PI, f = { ...n, a0: b, a1: b + s }; b += s; return f; });
      const out = { id: g, a0: a, a1: a + span, figli }; a += span; return out;
    });
  }, [dati]);
  const info = acceso && (settori.find((s) => s.id === acceso) || settori.flatMap((s) => s.figli).find((n) => n.id === acceso));
  const r0 = R * .3, r1 = R * .58, r2 = R;
  return html`<svg class="mappa-svg" style="cursor:default" role="img" aria-label="Raggiera degli appunti">
    ${settori.map((s) => html`<g>
      <path d=${arco(cx, cy, r0, r1 - 2, s.a0 + .004, s.a1 - .004)} class="raggio-area"
        style=${`fill:color-mix(in srgb, ${COLORI_GRUPPO[s.id]} ${acceso === s.id ? 70 : 45}%, #13242f)`}
        onMouseEnter=${() => setAcceso(s.id)} onMouseLeave=${() => setAcceso(null)} />
      ${s.a1 - s.a0 > .35 && html`<text class="raggio-etichetta" x=${cx + (r0 + r1) / 2 * Math.cos((s.a0 + s.a1) / 2)} y=${cy + (r0 + r1) / 2 * Math.sin((s.a0 + s.a1) / 2) + 4}
        text-anchor="middle">${s.id}</text>`}
      ${s.figli.map((n) => html`<path d=${arco(cx, cy, r1, r2, n.a0 + .003, n.a1 - .003)} class="raggio-voce"
          style=${`fill:color-mix(in srgb, ${colorePer(n, opz.colore)} ${acceso === n.id ? 75 : n.colore === "rosso" && opz.colore === "area" ? 18 : 40}%, #13242f)`}
          onMouseEnter=${() => setAcceso(n.id)} onMouseLeave=${() => setAcceso(null)} onClick=${() => vai(n.id)}><title>${n.nome}</title></path>`)}
      ${s.figli.filter((n) => (n.a1 - n.a0) * (r1 + r2) / 2 > 15).map((n) => {
        const m = (n.a0 + n.a1) / 2, gradi = m * 180 / Math.PI, sinistra = Math.cos(m) < 0, rr = r1 + 10;
        const x = cx + (sinistra ? r2 - 10 : rr) * Math.cos(m), y = cy + (sinistra ? r2 - 10 : rr) * Math.sin(m);
        const spazio = Math.floor((r2 - r1 - 20) / 6.4), nome = n.nome.length > spazio ? n.nome.slice(0, Math.max(2, spazio - 1)) + "…" : n.nome;
        return html`<text class="raggio-voce-nome" x=${x} y=${y} dy="4" transform=${`rotate(${sinistra ? gradi + 180 : gradi} ${x} ${y})`}>${nome}</text>`;
      })}
    </g>`)}
    <circle cx=${cx} cy=${cy} r=${r0 - 4} class="raggio-centro" />
    <text x=${cx} y=${cy - 4} text-anchor="middle" class="raggio-nome">${info ? (info.nome || info.id) : "Second Brain"}</text>
    <text x=${cx} y=${cy + 15} text-anchor="middle" class="raggio-det">${info ? (info.figli ? `${info.figli.length} appunti` : eta(info.giorni)) : `${dati.nodi.length} appunti`}</text>
  </svg>`;
}

// ---------- attivita' ----------
function Attivita({ api, dim }) {
  const [dati, setDati] = useState(null);
  useEffect(() => { (async () => { const r = await api("attivita"); setDati(r.errore ? { giorni: {}, aree: {} } : r); })(); }, []);
  if (!dati) return html`<div class="mappa-vuota"><span class="carica"></span></div>`;
  const settimane = 26, cella = Math.max(11, Math.min(18, Math.floor((dim.w - 120) / settimane) - 3)), passo = cella + 3;
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0);
  const inizio = new Date(oggi); inizio.setDate(oggi.getDate() - ((oggi.getDay() + 6) % 7) - (settimane - 1) * 7);
  const celle = [], mesi = [];
  let massimo = 1, totale = 0, attivi = 0, serie = 0, serieMax = 0;
  for (const v of Object.values(dati.giorni)) massimo = Math.max(massimo, v);
  for (let w = 0; w < settimane; w++) for (let d = 0; d < 7; d++) {
    const g = new Date(inizio); g.setDate(inizio.getDate() + w * 7 + d);
    if (g > oggi) continue;
    const k = `${g.getFullYear()}-${String(g.getMonth() + 1).padStart(2, "0")}-${String(g.getDate()).padStart(2, "0")}`;
    const v = dati.giorni[k] || 0;
    totale += v; if (v) { attivi++; serie++; serieMax = Math.max(serieMax, serie); } else serie = 0;
    if (d === 0 && g.getDate() <= 7) mesi.push({ w, nome: MESI[g.getMonth()] });
    celle.push({ w, d, v, k, g });
  }
  const livello = (v) => v === 0 ? 0 : Math.min(4, Math.ceil(v / massimo * 4));
  const aree = Object.entries(dati.aree).sort((a, b) => b[1] - a[1]), maxArea = Math.max(1, ...aree.map((a) => a[1]));
  return html`<div class="attivita">
    <div class="attivita-numeri">
      <div><b class="num">${totale}</b><span>modifiche agli appunti in 6 mesi</span></div>
      <div><b class="num">${attivi}</b><span>giorni con almeno una modifica</span></div>
      <div><b class="num">${serieMax}</b><span>giorni di fila, il record</span></div>
    </div>
    <svg width=${40 + settimane * passo} height=${30 + 7 * passo} class="calendario" role="img" aria-label="Calendario dell'attività">
      ${mesi.map((m) => html`<text x=${40 + m.w * passo} y="12" class="cal-mese">${m.nome}</text>`)}
      ${[["lun", 0], ["mer", 2], ["ven", 4]].map(([n, d]) => html`<text x="0" y=${30 + d * passo + cella - 2} class="cal-mese">${n}</text>`)}
      ${celle.map((c) => html`<rect x=${40 + c.w * passo} y=${20 + c.d * passo} width=${cella} height=${cella} rx="3" class=${`cal l${livello(c.v)}`}>
        <title>${c.g.getDate()} ${MESI[c.g.getMonth()]}: ${c.v ? `${c.v} modific${c.v === 1 ? "a" : "he"}` : "nessuna modifica"}</title></rect>`)}
    </svg>
    <div class="cal-legenda">meno ${[0, 1, 2, 3, 4].map((l) => html`<span class=${`cal-q l${l}`}></span>`)} più</div>
    <h2 class="attivita-titolo">Dove hai lavorato nell'ultimo mese</h2>
    <div class="aree-barre">${aree.length === 0 ? html`<span class="vuoto-lat">Nessuna modifica negli ultimi 30 giorni</span>` :
      aree.map(([g, v]) => html`<div class="area-riga"><span>${g}</span>
        <span class="area-barra"><i style=${`width:${v / maxArea * 100}%;background:${COLORI_GRUPPO[g] || "#e4dfd2"}`}></i></span><b class="num">${v}</b></div>`)}</div>
  </div>`;
}

// ---------- metro ----------
// ogni area e' una linea; fermate = appunti dal piu' fresco (capolinea a sinistra) al piu' vecchio;
// interscambi tratteggiati quando un appunto ne cita uno di un'altra area; fermate ferme vuote
function Metro({ dati, vai, dim }) {
  const [acceso, setAcceso] = useState(null);
  const linee = useMemo(() => {
    const per = {};
    for (const n of dati.nodi) (per[n.gruppo] = per[n.gruppo] || []).push(n);
    const gruppi = ordinaGruppi(Object.keys(per));
    const alto = 54, basso = dim.h - 86, passoY = gruppi.length > 1 ? Math.min(110, (basso - alto) / (gruppi.length - 1)) : 0;
    const x0 = 160, x1 = dim.w - 70;
    const pos = new Map();
    const out = gruppi.map((g, i) => {
      const ns = per[g].slice().sort((a, b) => a.giorni - b.giorni), y = alto + i * passoY;
      const passo = ns.length > 1 ? Math.min(120, (x1 - x0) / (ns.length - 1)) : 0;
      const fermate = ns.map((n, k) => { const f = { ...n, x: x0 + k * passo, y }; pos.set(n.id, f); return f; });
      return { g, y, fermate, spazio: Math.max(4, Math.floor((passo || 200) * 2 / 6.2) - 1) };
    });
    const scambi = dati.archi.map((e) => [pos.get(e.da), pos.get(e.a)]).filter(([a, b]) => a && b && a.gruppo !== b.gruppo);
    return { out, scambi };
  }, [dati, dim.w, dim.h]);
  return html`<svg class="mappa-svg" style="cursor:default" role="img" aria-label="Mappa della metro degli appunti">
    <text x="160" y="20" class="metro-asse">più recenti</text>
    <text x=${dim.w - 70} y="20" class="metro-asse" text-anchor="end">più vecchi</text>
    ${linee.scambi.map(([a, b]) => html`<path class=${`metro-scambio ${acceso === a.id || acceso === b.id ? "acceso" : ""}`}
      d=${`M${a.x} ${a.y} C${a.x} ${(a.y + b.y) / 2} ${b.x} ${(a.y + b.y) / 2} ${b.x} ${b.y}`} />`)}
    ${linee.out.map(({ g, y, fermate, spazio }) => html`<g>
      <rect x="18" y=${y - 13} width="112" height="26" rx="13" style=${`fill:${COLORI_GRUPPO[g]}`} />
      <text x="74" y=${y + 4.5} text-anchor="middle" class="metro-linea">${g}</text>
      ${fermate.length > 1 && html`<line x1=${fermate[0].x} y1=${y} x2=${fermate[fermate.length - 1].x} y2=${y}
        style=${`stroke:${COLORI_GRUPPO[g]}`} class="metro-binario" />`}
      ${fermate.map((f, k) => {
        const fermo = f.colore === "rosso", on = acceso === f.id;
        return html`<g class="metro-fermata" onClick=${() => vai(f.id)} onMouseEnter=${() => setAcceso(f.id)} onMouseLeave=${() => setAcceso(null)}>
          <circle cx=${f.x} cy=${y} r=${on ? 8 : 6.5} style=${`fill:${fermo ? "#0e1a22" : "#f1ece0"};stroke:${fermo ? "#5f7480" : "#0e1a22"}`} />
          <text x=${f.x} y=${k % 2 ? y - 14 : y + 22} text-anchor="middle" class=${`metro-nome ${on ? "acceso" : ""}`}>${on ? `${f.nome} · ${eta(f.giorni)}` : f.nome.length > spazio ? f.nome.slice(0, spazio - 1) + "…" : f.nome}</text>
        </g>`;
      })}
    </g>`)}
  </svg>`;
}

// ---------- citta' ----------
// ogni appunto e' un palazzo: altezza = contenuto, quartiere = area, finestre accese = freschezza
function Citta({ dati, opz, vai, dim }) {
  const [acceso, setAcceso] = useState(null);
  const palazzi = useMemo(() => {
    const per = {};
    for (const n of dati.nodi) (per[n.gruppo] = per[n.gruppo] || []).push(n);
    const gruppi = ordinaGruppi(Object.keys(per)), tot = dati.nodi.length + gruppi.length;
    const largo = Math.max(18, Math.min(46, (dim.w - 60) / tot - 6)), suolo = dim.h - 78;
    const maxP = Math.max(1, ...dati.nodi.map((n) => Math.sqrt(n.peso || 1)));
    let x = 30;
    const out = [], quartieri = [];
    for (const g of gruppi) {
      const x0 = x;
      for (const n of per[g].slice().sort((a, b) => (b.peso || 0) - (a.peso || 0))) {
        const h = 40 + (Math.sqrt(n.peso || 1) / maxP) * (suolo - 120);
        out.push({ ...n, x, y: suolo - h, w: largo, h, luce: Math.max(0, 1 - n.giorni / 30) });
        x += largo + 6;
      }
      quartieri.push({ g, x0, x1: x - 6 });
      x += largo;
    }
    // la citta' al centro dello spazio
    const sposta = Math.max(0, (dim.w - (x - largo) - 30) / 2);
    for (const p of out) p.x += sposta;
    for (const q of quartieri) { q.x0 += sposta; q.x1 += sposta; }
    return { out, quartieri, suolo };
  }, [dati, dim.w, dim.h]);
  const finestre = (p) => {
    const righe = Math.floor((p.h - 14) / 12), colonne = Math.max(1, Math.floor((p.w - 6) / 9)), out = [];
    for (let r = 0; r < righe; r++) for (let c = 0; c < colonne; c++) {
      // accese in modo sparso ma stabile, tante quante dice la freschezza
      const h = ((r * 31 + c * 17 + p.nome.length * 7) % 100) / 100;
      out.push({ x: p.x + 4 + c * 9, y: p.y + 8 + r * 12, on: h < p.luce });
    }
    return out;
  };
  const sopra = acceso && palazzi.out.find((x) => x.id === acceso);
  return html`<svg class="mappa-svg" style="cursor:default" role="img" aria-label="Città degli appunti">
    <circle cx=${dim.w - 80} cy="54" r="22" class="citta-luna" />
    ${palazzi.out.map((p) => {
      const col = colorePer(p, opz.colore), on = acceso === p.id;
      return html`<g class="citta-palazzo" onClick=${() => vai(p.id)} onMouseEnter=${() => setAcceso(p.id)} onMouseLeave=${() => setAcceso(null)}>
        <rect x=${p.x} y=${p.y} width=${p.w} height=${p.h} rx="2"
          style=${`fill:color-mix(in srgb, ${col} ${on ? 45 : 24}%, #0b151c);stroke:${on ? col : "transparent"}`} />
        ${finestre(p).map((f) => html`<rect x=${f.x} y=${f.y} width="5" height="6" rx="1" class=${f.on ? "citta-luce" : "citta-buio"} />`)}
      </g>`;
    })}
    <line x1="16" y1=${palazzi.suolo} x2=${dim.w - 16} y2=${palazzi.suolo} class="citta-suolo" />
    ${palazzi.quartieri.map((q) => html`<text x=${(q.x0 + q.x1) / 2} y=${palazzi.suolo + 20} text-anchor="middle" class="citta-quartiere"
      style=${`fill:${COLORI_GRUPPO[q.g]}`}>${q.g}</text>`)}
    ${sopra && html`<text x=${sopra.x + sopra.w / 2} y=${sopra.y - 8} text-anchor="middle" class="citta-nome">${sopra.nome} · ${eta(sopra.giorni)}</text>`}
  </svg>`;
}

// ---------- orbite ----------
// sistema solare: distanza dal centro = giorni dall'ultima modifica (scala logaritmica),
// settore = area, grandezza = contenuto; ruota piano e si ferma al passaggio del mouse
function Orbite({ dati, opz, vai, dim }) {
  const [acceso, setAcceso] = useState(null);
  const [giro, setGiro] = useState(0);
  const fermo = useRef(false);
  useEffect(() => {
    let ciclo, prima = performance.now();
    const passo = (t) => { if (!fermo.current) setGiro((g) => g + (t - prima) * .000035); prima = t; ciclo = requestAnimationFrame(passo); };
    ciclo = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(ciclo);
  }, []);
  const cx = dim.w / 2, cy = (dim.h - 30) / 2 + 6, R = Math.min(dim.w - 60, dim.h - 70) / 2, r0 = 44;
  const raggio = (g) => r0 + 14 + (R - r0 - 14) * Math.min(1, Math.log1p(g) / Math.log1p(120));
  const pianeti = useMemo(() => {
    const per = {};
    for (const n of dati.nodi) (per[n.gruppo] = per[n.gruppo] || []).push(n);
    const gruppi = ordinaGruppi(Object.keys(per)), spicchio = 2 * Math.PI / Math.max(1, gruppi.length);
    return gruppi.flatMap((g, i) => per[g].map((n, k) => ({
      ...n, a: i * spicchio + (k + .5) / per[g].length * spicchio * .85, r: 3 + Math.min(9, Math.sqrt(n.peso || 0) / 14),
    })));
  }, [dati]);
  const anelli = [[1, "ieri"], [7, "1 settimana"], [30, "1 mese"], [90, "3 mesi"]];
  return html`<svg class="mappa-svg" style="cursor:default" role="img" aria-label="Orbite degli appunti"
      onMouseEnter=${() => (fermo.current = true)} onMouseLeave=${() => { fermo.current = false; setAcceso(null); }}>
    ${anelli.map(([g, t]) => html`<g><circle cx=${cx} cy=${cy} r=${raggio(g)} class="orbita" />
      <text x=${cx + 4} y=${cy - raggio(g) - 4} class="orbita-nome">${t}</text></g>`)}
    <circle cx=${cx} cy=${cy} r=${r0} class="orbite-sole" />
    <text x=${cx} y=${cy + 4} text-anchor="middle" class="orbite-centro">Second Brain</text>
    ${pianeti.map((p) => {
      const d = raggio(p.giorni), a = p.a + giro * (1.6 - d / R), x = cx + d * Math.cos(a), y = cy + d * Math.sin(a), on = acceso === p.id;
      return html`<g class="orbite-pianeta" onClick=${() => vai(p.id)} onMouseEnter=${() => setAcceso(p.id)}>
        <circle cx=${x} cy=${y} r=${on ? p.r + 2 : p.r} style=${`fill:${colorePer(p, opz.colore)}`} />
        ${(on || opz.etichette === "tutte") && html`<text x=${x + p.r + 5} y=${y + 4} class="orbite-nome">${p.nome}${on ? ` · ${eta(p.giorni)}` : ""}</text>`}
      </g>`;
    })}
  </svg>`;
}

// ---------- pagina ----------
export function PaginaMappa({ vaiAppunto, api }) {
  const [vista, setVista] = useState(() => leggi("mappaVista", "grafo2d"));
  const [opz, setOpz] = useState(() => ({ colore: "area", etichette: "principali", nascoste: [], ...leggi("mappaOpzioni", {}) }));
  const [pannello, setPannello] = useState(false);
  const [aSinistra, setASinistra] = useState(false);
  const [largMax, setLargMax] = useState(470);
  const [dati, setDati] = useState(null);
  const [dim, setDim] = useState({ w: 900, h: 640 });
  const contenitore = useRef(null);
  useEffect(() => { (async () => { const r = await api("mappa"); if (!r.errore) setDati(r); })(); }, []);
  useEffect(() => {
    const el = contenitore.current;
    const o = new ResizeObserver(() => setDim({ w: el.clientWidth, h: el.clientHeight }));
    o.observe(el); return () => o.disconnect();
  }, []);
  const comandi = useRef(null);
  useEffect(() => {
    if (!pannello) return;
    const fuori = (e) => { if (comandi.current && !comandi.current.contains(e.target)) setPannello(false); };
    const esc = (e) => { if (e.key === "Escape") setPannello(false); };
    window.addEventListener("mousedown", fuori); window.addEventListener("keydown", esc);
    return () => { window.removeEventListener("mousedown", fuori); window.removeEventListener("keydown", esc); };
  }, [pannello]);
  useEffect(() => scrivi("mappaVista", vista), [vista]);
  useEffect(() => scrivi("mappaOpzioni", opz), [opz]);
  const filtrati = useMemo(() => {
    if (!dati) return null;
    const via = new Set(opz.nascoste);
    const nodi = dati.nodi.filter((n) => !via.has(n.gruppo)), ids = new Set(nodi.map((n) => n.id));
    return { nodi, archi: dati.archi.filter((e) => ids.has(e.da) && ids.has(e.a)) };
  }, [dati, opz.nascoste]);
  const gruppiDati = useMemo(() => dati ? ordinaGruppi(dati.nodi.map((n) => n.gruppo)) : [], [dati]);
  const imposta = (k, v) => setOpz((o) => ({ ...o, [k]: v }));
  const scegli = (k, valori) => html`<div class="schede-filtro">${valori.map(([v, n]) =>
    html`<button class=${opz[k] === v ? "attivo" : ""} onClick=${() => imposta(k, v)}>${n}</button>`)}</div>`;
  const Vista = { grafo2d: Grafo2D, grafo3d: Grafo3D, mosaico: Mosaico, raggiera: Raggiera, attivita: Attivita, metro: Metro, citta: Citta, orbite: Orbite }[vista] || Grafo2D;
  return html`<div class="mappa-pagina">
    <div class="mappa-area" ref=${contenitore}>
    ${vista === "attivita" ? html`<${Attivita} api=${api} dim=${dim} />`
      : filtrati ? html`<${Vista} key=${vista} dati=${filtrati} opz=${opz} vai=${vaiAppunto} dim=${dim} />`
      : html`<div class="mappa-vuota"><span class="carica"></span></div>`}
    ${vista !== "attivita" && html`<div class="mappa-chiavi">${opz.colore === "area"
      ? gruppiDati.filter((g) => !opz.nascoste.includes(g)).map((g) => html`<span><span class="pallino" style=${`background:${COLORI_GRUPPO[g]}`}></span>${g}</span>`)
      : [["verde", "meno di una settimana"], ["giallo", "1-2 settimane"], ["rosso", "ferma da più di 2 settimane"]].map(([c, t]) =>
          html`<span><span class="pallino" style=${`background:${COLORI_ETA[c]}`}></span>${t}</span>`)}</div>`}
    </div>
    <div class="mappa-testa">
      <div class="mappa-legenda"><h1>Mappa</h1><p>${DESCRIZIONI[vista]}</p></div>
      <div class="mappa-comandi">
        <div class="schede-filtro" role="tablist" aria-label="Tipo di visualizzazione">${VISTE.map(([v, n]) =>
          html`<button role="tab" aria-selected=${vista === v} class=${vista === v ? "attivo" : ""} onClick=${() => setVista(v)}>${n}</button>`)}</div>
        ${vista !== "attivita" && html`<div class="mappa-ancora" ref=${comandi}>
          <button class=${`btn piccolo ${pannello ? "attivo-btn" : ""}`} aria-expanded=${pannello} onClick=${(e) => {
            // il pannello si apre dal lato con piu' spazio dentro la colonna della mappa
            const b = e.currentTarget.getBoundingClientRect(), area = contenitore.current.getBoundingClientRect();
            const sx = b.right - area.left < 480;
            setASinistra(sx);
            setLargMax(Math.max(260, Math.min(470, sx ? area.right - b.left - 16 : b.right - area.left - 16)));
            setPannello(!pannello);
          }}>Opzioni</button>
        ${pannello && vista !== "attivita" && html`<div class=${`mappa-opzioni scheda ${aSinistra ? "a-sinistra" : ""}`} style=${`max-width:${largMax}px`} role="dialog" aria-label="Opzioni della mappa">
          <div><span>Colore</span>${scegli("colore", [["area", "Per area"], ["freschezza", "Per freschezza"]])}</div>
          <div><span>Etichette</span>${scegli("etichette", [["principali", "Principali"], ["tutte", "Tutte"], ["nessuna", "Al passaggio"]])}</div>
          <div><span>Aree</span><div class="mappa-aree">${gruppiDati.map((g) => html`<label>
            <input type="checkbox" checked=${!opz.nascoste.includes(g)}
              onChange=${(e) => imposta("nascoste", e.target.checked ? opz.nascoste.filter((x) => x !== g) : [...opz.nascoste, g])} />
            <span class="pallino" style=${`background:${COLORI_GRUPPO[g]}`}></span>${g}</label>`)}</div></div>
        </div>`}
        </div>`}
      </div>
    </div>
  </div>`;
}
