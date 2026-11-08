// Icone disegnate a mano in SVG. Due famiglie:
// - icone di interfaccia: tratto 1.6, angoli arrotondati, colore = currentColor;
// - emblemi dei progetti per le piastrelle di maiolica: forme piene "dipinte" con
//   i colori dello smalto (--e1 tinta principale, --e2 seconda, --e3 contorno).
import { html } from "./vendor/preact-htm.mjs";
import { FLUENT } from "./vendor/emblemi-fluent.mjs";

const tratto = (corpo, dim = 18) => html`<svg class="ic" width=${dim} height=${dim} viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"
  aria-hidden="true">${corpo}</svg>`;

export const Icona = {
  oggi: () => tratto(html`<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.2M12 19.3v2.2M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6"/>`),
  chat: () => tratto(html`<path d="M4 5.5h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-9l-4.5 3.5v-3.5H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1z"/><path d="M7.5 10h9M7.5 13h5.5"/>`),
  appunti: () => tratto(html`<path d="M6 3h9l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M14.5 3v4.5H19M8.5 12h7M8.5 15.5h7M8.5 8.5h3"/>`),
  mappa: () => tratto(html`<circle cx="6" cy="6.5" r="2.2"/><circle cx="18" cy="8" r="2.2"/><circle cx="9" cy="17.5" r="2.2"/><circle cx="18.5" cy="18" r="1.6"/><path d="M8 7.2l7.9.6M7 8.5l1.4 6.9M16.6 9.7l-5.9 6.2M11.2 17.6l5.7.3"/>`),
  inbox: () => tratto(html`<path d="M3.5 13.5l2.6-7.6A1.5 1.5 0 0 1 7.5 5h9a1.5 1.5 0 0 1 1.4.9l2.6 7.6V18a1.5 1.5 0 0 1-1.5 1.5h-14A1.5 1.5 0 0 1 3.5 18z"/><path d="M3.5 13.5h4.6l1.3 2.3h5.2l1.3-2.3h4.6"/>`),
  piu: () => tratto(html`<path d="M12 5v14M5 12h14"/>`, 16),
  chiudi: () => tratto(html`<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>`, 14),
  cerca: () => tratto(html`<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.3-4.3"/>`, 16),
  matita: () => tratto(html`<path d="M4 20l1-4.5L15.5 5a2.1 2.1 0 0 1 3 3L8 18.5z"/><path d="M13.5 7l3.5 3.5"/>`, 16),
  esterno: () => tratto(html`<path d="M14 4h6v6M20 4l-8.5 8.5M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>`, 16),
  riprendi: () => tratto(html`<path d="M5 12a7 7 0 1 0 2.1-5"/><path d="M5 4.5V9h4.5"/>`, 16),
  puntina: () => tratto(html`<path d="M9 4h6l-1 5 3 3v2H7v-2l3-3zM12 14v6"/>`, 16),
  copia: () => tratto(html`<rect x="8.5" y="8.5" width="11" height="11" rx="1.5"/><path d="M15.5 8.5V5.5a1 1 0 0 0-1-1h-9a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h3"/>`, 16),
  esporta: () => tratto(html`<path d="M12 4v11M7.5 8.5 12 4l4.5 4.5M5 14v4.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V14"/>`, 16),
  cestino: () => tratto(html`<path d="M4.5 7h15M9.5 7V4.8h5V7M6.5 7l.9 12.2a1 1 0 0 0 1 .8h7.2a1 1 0 0 0 1-.8L17.5 7M10.2 10.5v6M13.8 10.5v6"/>`, 16),
  salva: () => tratto(html`<path d="M5 4h11l3 3v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>`, 16),
  allarga: () => tratto(html`<path d="M14 4h6v6M10 20H4v-6M20 4l-6.5 6.5M4 20l6.5-6.5"/>`, 16),
  restringi: () => tratto(html`<path d="M20 10h-6V4M4 14h6v6M14 10l6.5-6.5M10 14l-6.5 6.5"/>`, 16),
  cartella: () => tratto(html`<path d="M3.5 6.5a1 1 0 0 1 1-1h4.8l2 2.2h8.2a1 1 0 0 1 1 1v9.8a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1z"/>`, 16),
  ricarica: () => tratto(html`<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4.2h-4.2"/>`, 16),
  github: () => tratto(html`<path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/>`, 15),
  briefing: () => tratto(html`<path d="M4 18.5h16M6.5 15l3-4 3 2.5 5-6.5"/>`, 16),
  revisione: () => tratto(html`<path d="M5 6.5h9M5 12h6M5 17.5h5"/><path d="M14.5 16l2 2 4-4.5"/>`, 16),
  caffe: () => tratto(html`<path d="M4.5 9h12v5.5a5 5 0 0 1-5 5h-2a5 5 0 0 1-5-5z"/><path d="M16.5 10.5h1.2a2.3 2.3 0 0 1 0 4.6h-1.6"/><path d="M8.5 3.5c-.6.9.6 1.6 0 2.6M12 3.5c-.6.9.6 1.6 0 2.6"/>`, 16),
};

// --- emblemi dipinti per progetto ---
const E = {
  // gruccia: abbigliamento e magazzino
  negozio: html`<path d="M32 15a4.5 4.5 0 1 1 4.5 4.5c-2 0-4.5 1.2-4.5 4v3" fill="none" stroke="var(--e3)" stroke-width="3" stroke-linecap="round"/>
    <path d="M32 26.5L9 41.5c-2 1.3-1.1 4.3 1.3 4.3h43.4c2.4 0 3.3-3 1.3-4.3z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M17 41.5h30" stroke="var(--e2)" stroke-width="3" stroke-linecap="round"/>`,
  // ramo di limone del chiostro
  limone: html`<path d="M14 50C24 40 34 33 50 30" fill="none" stroke="var(--e3)" stroke-width="3" stroke-linecap="round"/>
    <path d="M24 41c-6-1-10-6-10-12 6 0 11 5 10 12z" fill="var(--e2)" stroke="var(--e3)" stroke-width="2"/>
    <path d="M38 33c1-6 6-10 12-10 0 6-5 11-12 10z" fill="var(--e2)" stroke="var(--e3)" stroke-width="2"/>
    <ellipse cx="33" cy="45" rx="9.5" ry="7.5" transform="rotate(-25 33 45)" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4"/>
    <circle cx="30" cy="42.5" r="2" fill="#fff" opacity=".55"/>`,
  // pallone
  calcio: html`<circle cx="32" cy="33" r="17" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4"/>
    <path d="M32 24.5l7 5-2.7 8.2h-8.6L25 29.5z" fill="var(--e3)"/>
    <path d="M32 24.5V16.5M39 29.5l7.5-2.6M36.3 37.7l4.8 6.6M27.7 37.7l-4.8 6.6M25 29.5l-7.5-2.6" stroke="var(--e3)" stroke-width="2.2" stroke-linecap="round"/>`,
  // ragno sulla tela
  ragno: html`<path d="M32 10v12M12 22l14 6M52 22l-14 6M14 48l13-10M50 48l-13-10" stroke="var(--e2)" stroke-width="1.6" stroke-linecap="round"/>
    <path d="M24 30l-9-6-3 6M24 34l-10 1-2 7M40 30l9-6 3 6M40 34l10 1 2 7M26 38l-6 7M38 38l6 7" fill="none" stroke="var(--e3)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
    <ellipse cx="32" cy="35" rx="7" ry="9" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.2"/>
    <circle cx="32" cy="24.5" r="4.5" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.2"/>
    <path d="M29 33l3 3 3-3M32 36v4" stroke="var(--e3)" stroke-width="1.8" fill="none" stroke-linecap="round"/>`,
  // spada
  spada: html`<path d="M32 9l5 7v22h-10V16z" fill="var(--e2)" stroke="var(--e3)" stroke-width="2.2" stroke-linejoin="round"/>
    <path d="M32 13v24" stroke="var(--e3)" stroke-width="1.4" opacity=".6"/>
    <path d="M20 38h24a2 2 0 0 1 0 4H20a2 2 0 0 1 0-4z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.2"/>
    <path d="M29 42h6v9h-6z" fill="var(--e3)"/><circle cx="32" cy="54" r="3.4" fill="var(--e1)" stroke="var(--e3)" stroke-width="2"/>`,
  // borsa della spesa
  borsa: html`<path d="M25 23v-3a7 7 0 0 1 14 0v3" fill="none" stroke="var(--e3)" stroke-width="2.6" stroke-linecap="round"/>
    <path d="M16 23h32l-2.5 26a3 3 0 0 1-3 2.7H21.5a3 3 0 0 1-3-2.7z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M25 33l4.5 4.5L39 29" fill="none" stroke="var(--e2)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`,
  // libro (universita')
  libro: html`<path d="M12 18c7-3 14-3 20 1 6-4 13-4 20-1v29c-7-3-14-3-20 1-6-4-13-4-20-1z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M32 19v29" stroke="var(--e3)" stroke-width="2"/><path d="M17 25c4-1 7-1 10 .5M17 31c4-1 7-1 10 .5M37 25.5c3-1.5 6-1.5 10-.5" stroke="var(--e2)" stroke-width="2" stroke-linecap="round"/>`,
  // ciak (film)
  ciak: html`<path d="M12 27h40v21a2 2 0 0 1-2 2H14a2 2 0 0 1-2-2z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M11.5 20.5l38-8.5 1.6 7-38 8.5z" fill="var(--e2)" stroke="var(--e3)" stroke-width="2.2" stroke-linejoin="round"/>
    <path d="M19 18.8l5.5 6.4M28.5 16.7l5.5 6.4M38 14.5l5.5 6.4" stroke="var(--e3)" stroke-width="2.6"/>
    <path d="M18 35h28M18 41h18" stroke="var(--e3)" stroke-width="2.2" stroke-linecap="round" opacity=".7"/>`,
  // --- emblemi generici per i progetti nuovi ---
  codice: html`<rect x="9" y="14" width="46" height="36" rx="5" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4"/>
    <path d="M9 22h46" stroke="var(--e3)" stroke-width="2"/><path d="M25 30l-6 6 6 6M39 30l6 6-6 6M35 28l-6 16" fill="none" stroke="var(--e2)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`,
  musica: html`<path d="M26 44V18l22-5v26" fill="none" stroke="var(--e3)" stroke-width="3" stroke-linejoin="round"/>
    <path d="M26 24l22-5" stroke="var(--e3)" stroke-width="3"/><ellipse cx="20" cy="45" rx="7" ry="5.5" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4"/>
    <ellipse cx="42" cy="40" rx="7" ry="5.5" fill="var(--e2)" stroke="var(--e3)" stroke-width="2.4"/>`,
  viaggio: html`<path d="M10 36l16-4 12-17c2-3 7-1 6 2l-6 18 14 4-2 5-15-1-8 9h-5l3-11-12-1z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M14 52h36" stroke="var(--e2)" stroke-width="3" stroke-linecap="round"/>`,
  casa: html`<path d="M12 30L32 13l20 17v20a2 2 0 0 1-2 2H14a2 2 0 0 1-2-2z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M27 52V38h10v14" fill="var(--e2)" stroke="var(--e3)" stroke-width="2.2"/><path d="M8 32L32 11l24 21" fill="none" stroke="var(--e3)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>`,
  soldi: html`<circle cx="32" cy="33" r="18" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4"/><circle cx="32" cy="33" r="13" fill="none" stroke="var(--e2)" stroke-width="2"/>
    <path d="M37 27c-4-3-11-2-11 2 0 5 11 3 11 8 0 4-7 5-11 2M31.5 23v4M31.5 41v4" fill="none" stroke="var(--e3)" stroke-width="2.6" stroke-linecap="round"/>`,
  sport: html`<path d="M22 32h20" stroke="var(--e3)" stroke-width="4" stroke-linecap="round"/>
    <rect x="12" y="20" width="9" height="24" rx="3" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4"/><rect x="43" y="20" width="9" height="24" rx="3" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4"/>
    <rect x="6" y="25" width="6" height="14" rx="2" fill="var(--e2)" stroke="var(--e3)" stroke-width="2"/><rect x="52" y="25" width="6" height="14" rx="2" fill="var(--e2)" stroke="var(--e3)" stroke-width="2"/>`,
  cucina: html`<path d="M14 30h36v6a14 14 0 0 1-14 14h-8a14 14 0 0 1-14-14z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M10 30h44M50 33h6" stroke="var(--e3)" stroke-width="2.6" stroke-linecap="round"/><path d="M24 23c-2-3 2-5 0-9M32 23c-2-3 2-5 0-9M40 23c-2-3 2-5 0-9" fill="none" stroke="var(--e2)" stroke-width="2.4" stroke-linecap="round"/>`,
  foto: html`<path d="M12 22h9l4-6h14l4 6h9a2 2 0 0 1 2 2v22a2 2 0 0 1-2 2H12a2 2 0 0 1-2-2V24a2 2 0 0 1 2-2z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <circle cx="32" cy="35" r="9" fill="var(--e2)" stroke="var(--e3)" stroke-width="2.4"/><circle cx="32" cy="35" r="3.5" fill="var(--e3)"/>`,
  salute: html`<path d="M32 51S11 38 11 24a10 10 0 0 1 21-5 10 10 0 0 1 21 5c0 14-21 27-21 27z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M16 32h10l3-6 5 12 3-6h11" fill="none" stroke="var(--e2)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>`,
  lavoro: html`<rect x="9" y="22" width="46" height="28" rx="4" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4"/>
    <path d="M25 22v-5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v5" fill="none" stroke="var(--e3)" stroke-width="2.6"/><path d="M9 33h46" stroke="var(--e3)" stroke-width="2"/>
    <rect x="28" y="30" width="8" height="7" rx="1.5" fill="var(--e2)" stroke="var(--e3)" stroke-width="2"/>`,
  scuola: html`<path d="M6 25l26-11 26 11-26 11z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M17 30v11c0 4 7 8 15 8s15-4 15-8V30" fill="var(--e2)" stroke="var(--e3)" stroke-width="2.4"/><path d="M52 27v14" stroke="var(--e3)" stroke-width="2.6" stroke-linecap="round"/><circle cx="52" cy="43" r="2.6" fill="var(--e3)"/>`,
  gioco: html`<path d="M18 21h28c6 0 9 6 10 14 1 7-1 13-6 13-4 0-6-6-10-6H24c-4 0-6 6-10 6-5 0-7-6-6-13 1-8 4-14 10-14z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M20 28v10M15 33h10" stroke="var(--e3)" stroke-width="3" stroke-linecap="round"/><circle cx="42" cy="30" r="2.8" fill="var(--e2)"/><circle cx="47" cy="35" r="2.8" fill="var(--e2)"/>`,
  arte: html`<path d="M32 12C18 12 9 21 9 32s9 20 19 20c4 0 5-3 3-6s0-6 4-6h7c7 0 13-5 13-11 0-9-10-17-23-17z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <circle cx="22" cy="27" r="3.4" fill="var(--e2)"/><circle cx="31" cy="20" r="3.4" fill="#c8643b"/><circle cx="42" cy="22" r="3.4" fill="#1f4fa3"/><circle cx="20" cy="38" r="3.4" fill="#6fa287"/>`,
  pianta: html`<path d="M32 52V28" stroke="var(--e3)" stroke-width="3" stroke-linecap="round"/>
    <path d="M32 34c-10 0-17-7-17-17 10 0 17 7 17 17z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M32 30c0-10 7-17 17-17 0 10-7 17-17 17z" fill="var(--e2)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M22 52h20" stroke="var(--e3)" stroke-width="3" stroke-linecap="round"/>`,
  razzo: html`<path d="M32 8c9 7 12 17 10 28H22C20 25 23 15 32 8z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <circle cx="32" cy="23" r="4.5" fill="var(--e2)" stroke="var(--e3)" stroke-width="2.2"/><path d="M22 30l-8 8v6l8-4M42 30l8 8v6l-8-4" fill="var(--e2)" stroke="var(--e3)" stroke-width="2.2" stroke-linejoin="round"/>
    <path d="M27 40l5 14 5-14" fill="#f2c94c" stroke="var(--e3)" stroke-width="2" stroke-linejoin="round"/>`,
  idea: html`<path d="M32 9a15 15 0 0 0-9 27c2 2 3 4 3 6v2h12v-2c0-2 1-4 3-6a15 15 0 0 0-9-27z" fill="var(--e1)" stroke="var(--e3)" stroke-width="2.4" stroke-linejoin="round"/>
    <path d="M26 49h12M28 54h8" stroke="var(--e3)" stroke-width="2.8" stroke-linecap="round"/><path d="M28 30l4-6 4 6" fill="none" stroke="var(--e2)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>`,
  // stella maiolicata a otto punte (ripiego)
  stella: html`<path d="M32 10l5.5 13.2L51 18l-5.2 13.5L59 37l-13.2 5.5L51 56l-13.5-5.2L32 64 26.5 50.8 13 56l5.2-13.5L5 37l13.2-5.5L13 18l13.5 5.2z" transform="translate(32 33) scale(.62) translate(-32 -37)" fill="var(--e1)" stroke="var(--e3)" stroke-width="3.2" stroke-linejoin="round"/>
    <circle cx="32" cy="33" r="5" fill="var(--e2)" stroke="var(--e3)" stroke-width="2"/>`,
};

// colori per emblema: [fondo piastrella, tinta, seconda, contorno]
const SMALTI = {
  negozio: ["#1f4fa3", "#f2c94c", "#c8643b", "#0f2547"],
  limone: ["#2b6d5a", "#f2c94c", "#8cc29a", "#13362c"],
  calcio: ["#2e6b3f", "#f1ece0", "#f2c94c", "#14301c"],
  ragno: ["#8e2f3c", "#1f4fa3", "#f1ece0", "#330d14"],
  spada: ["#3b2f5c", "#c8643b", "#e5e1d6", "#160f26"],
  borsa: ["#2f5d6e", "#f2c94c", "#c8643b", "#0f2630"],
  libro: ["#1f4fa3", "#f1ece0", "#c8643b", "#0f2547"],
  ciak: ["#5a2e4a", "#f1ece0", "#f2c94c", "#22101c"],
  codice: ["#2f5d6e", "#13242f", "#8cc29a", "#0b1a20"],
  musica: ["#3b2f5c", "#f2c94c", "#f1ece0", "#160f26"],
  viaggio: ["#245a7a", "#f1ece0", "#f2c94c", "#0c2433"],
  casa: ["#8a6a1f", "#f1ece0", "#c8643b", "#2e2208"],
  soldi: ["#2e6b3f", "#f2c94c", "#d9ad2b", "#14301c"],
  sport: ["#1f4fa3", "#f1ece0", "#f2c94c", "#0f2547"],
  cucina: ["#8e2f3c", "#f1ece0", "#f2c94c", "#330d14"],
  foto: ["#3f4f5c", "#f1ece0", "#4f7fd0", "#12181d"],
  salute: ["#2b6d5a", "#e08460", "#f1ece0", "#13362c"],
  lavoro: ["#5a2e4a", "#c8643b", "#f2c94c", "#22101c"],
  scuola: ["#1f4fa3", "#13242f", "#f2c94c", "#0b1622"],
  gioco: ["#3b2f5c", "#f1ece0", "#c8643b", "#160f26"],
  arte: ["#2f5d6e", "#f1ece0", "#f2c94c", "#0b1a20"],
  pianta: ["#2e6b3f", "#8cc29a", "#f2c94c", "#14301c"],
  razzo: ["#245a7a", "#f1ece0", "#c8643b", "#0c2433"],
  idea: ["#3f4f5c", "#f2c94c", "#c8643b", "#12181d"],
  stella: ["#245a7a", "#f2c94c", "#c8643b", "#0c2433"],
};

// emblema predefinito indovinato dal nome del progetto (finche' non se ne sceglie uno)
export function emblemaPer(nome) {
  const n = (nome || "").toLowerCase();
  const ha = (...parole) => parole.some((p) => n.includes(p));
  if (ha("acquist", "shopping")) return "borsa";
  if (ha("negozio", "shop", "store")) return "negozio";
  if (ha("second brain")) return "limone";
  if (ha("calcio", "football", "soccer")) return "calcio";
  if (ha("fumett", "comic")) return "ragno";
  if (ha("gdr", "rpg", "gioco di ruolo")) return "spada";
  if (ha("univers", "esam", "exam", "tesi", "thesis", "studio", "study")) return "libro";
  if (ha("film", "movie", "cinema")) return "ciak";
  return "stella";
}

// catalogo per la scelta dell'emblema e dei fondi nella creazione di un progetto
// emblemi per i progetti nuovi: Fluent Emoji (chiave "f:<nome>"); i disegni a mano restano per i vecchi
export const EMBLEMI = Object.keys(FLUENT).map((k) => `f:${k}`);
export const NOMI_EMBLEMI = { negozio: "Negozio", limone: "Limone", calcio: "Calcio", ragno: "Fumetti", spada: "Gioco di ruolo",
  borsa: "Acquisti", libro: "Studio", ciak: "Film", codice: "Codice", musica: "Musica", viaggio: "Viaggi", casa: "Casa",
  soldi: "Soldi", sport: "Sport", cucina: "Cucina", foto: "Foto", salute: "Salute", lavoro: "Lavoro", scuola: "Scuola",
  gioco: "Videogiochi", arte: "Arte", pianta: "Natura", razzo: "Startup", idea: "Idea", stella: "Stella" };
export const FONDI = ["#1f4fa3", "#245a7a", "#2f5d6e", "#2b6d5a", "#2e6b3f", "#8a6a1f", "#8e2f3c", "#5a2e4a", "#3b2f5c", "#3f4f5c"];

export const nomeEmblema = (k) => (k && k.startsWith("f:") && FLUENT[k.slice(2)] ? FLUENT[k.slice(2)].nome : NOMI_EMBLEMI[k] || k);

// motivi decorativi dello sfondo della piastrella
export const MOTIVI = [["smalto", "Smalto"], ["liscio", "Liscio"], ["crepe", "Crepe"], ["righe", "Righe"], ["pois", "Pois"],
  ["onde", "Onde"], ["quadri", "Quadretti"], ["fiori", "Fiori"], ["raggi", "Raggi"]];
export const Motivo = ({ motivo }) => motivo && motivo !== "smalto" ? html`<span class=${`motivo m-${motivo}`} aria-hidden="true"></span>` : "";

// emblema predefinito (Fluent) per i progetti senza aspetto scelto: dal vecchio disegno al nuovo
const DA_VECCHIO = { negozio: "f:t-shirt", limone: "f:brain", calcio: "f:soccer-ball", ragno: "f:spider",
  spada: "f:crossed-swords", borsa: "f:shopping-bags", libro: "f:books", ciak: "f:clapper-board", stella: "f:sparkles" };

export function Emblema({ nome, emblema }) {
  if (!emblema || !(emblema.startsWith("f:") || E[emblema])) emblema = DA_VECCHIO[emblemaPer(nome)];
  if (emblema && emblema.startsWith("f:") && FLUENT[emblema.slice(2)])
    return html`<svg class="emblema fluent" viewBox="0 0 32 32" aria-hidden="true" dangerouslySetInnerHTML=${{ __html: FLUENT[emblema.slice(2)].svg }}></svg>`;
  const k = emblema && E[emblema] ? emblema : emblemaPer(nome);
  const [, e1, e2, e3] = SMALTI[k];
  return html`<svg class="emblema" viewBox="0 0 64 64" aria-hidden="true"
    style=${`--e1:${e1};--e2:${e2};--e3:${e3}`}>${E[k]}</svg>`;
}

export const fondoPiastrella = (nome, aspetto) => (aspetto && aspetto.fondo) || SMALTI[(aspetto && E[aspetto.emblema] && aspetto.emblema) || emblemaPer(nome)][0];
export const FONDI_EXTRA = ["#a5352a", "#c8643b", "#4f7fd0", "#7a8a2e", "#1d3443", "#6b4a2e"];

// marchio dell'app: piastrella cobalto con quarto di limone e foglia
export const Marchio = ({ dim = 28 }) => html`<img class="marchio-img" src="icona.svg" width=${dim} height=${dim} alt="" />`;
export const MarchioVecchio = ({ dim = 26 }) => html`<svg width=${dim} height=${dim} viewBox="0 0 32 32" aria-hidden="true">
  <rect width="32" height="32" rx="6" fill="#1f4fa3"/>
  <path d="M0 6a6 6 0 0 1 6-6h12A18 18 0 0 1 0 18z" fill="#f2c94c"/>
  <path d="M19 24C18.9 19.2 23.6 15.4 29 16C29.1 20.8 24.4 24.6 19 24z" fill="#6fa287"/>
  <path d="M19 24L29 16" stroke="#1f4fa3" stroke-width=".7"/>
  <rect x="1" y="1" width="30" height="30" rx="5.5" fill="none" stroke="#f1ece0" stroke-opacity=".18"/>
</svg>`;
