// Un terminale xterm.js collegato via websocket a un processo claude.exe (vedi terminale.py).
// Le librerie xterm sono caricate come script globali da index.html.
// Tasti: Shift+Invio = a capo (ESC CR, come in WezTerm); Ctrl+C copia se c'e' una selezione,
// altrimenti va a Claude; Ctrl+V e tasto destro incollano.

const TEMA = {
  background: "#081016", foreground: "#e4e1d6", cursor: "#f2c94c", cursorAccent: "#081016",
  selectionBackground: "#1f4fa366", selectionForeground: "#ffffff",
  black: "#1a2a35", red: "#e06c5a", green: "#8cc29a", yellow: "#f2c94c", blue: "#7aa2e8",
  magenta: "#c79ad6", cyan: "#7cc4c4", white: "#d6d2c6",
  brightBlack: "#5f7480", brightRed: "#f08a78", brightGreen: "#a6dcb2", brightYellow: "#f7da7a",
  brightBlue: "#9cbcf2", brightMagenta: "#dab4e6", brightCyan: "#9adada", brightWhite: "#f6f3ea",
};

// carattere e dimensione scelti in Impostazioni > Terminale (window.sbTerminale)
const FAMIGLIE = { "JetBrains Mono": '"JetBrainsMono Nerd Font", "JetBrains Mono"', "Cascadia Mono": '"Cascadia Mono"', "Consolas": "Consolas" };
const famiglia = () => `${FAMIGLIE[(window.sbTerminale || {}).carattere] || FAMIGLIE["JetBrains Mono"]}, "Cascadia Mono", Consolas, monospace`;
const tutte = new Set();
window.addEventListener("sb-terminale", () => tutte.forEach((c) => {
  c.term.options.fontSize = (window.sbTerminale || {}).testo || 13.5; c.term.options.fontFamily = famiglia(); c.adatta(true);
}));

export class Console {
  constructor(contenitore, url, { allUscita } = {}) {
    this.url = url;
    this.allUscita = allUscita;
    this.chiusa = false;
    tutte.add(this);
    this.term = new window.Terminal({
      fontFamily: famiglia(), fontSize: (window.sbTerminale || {}).testo || 13.5, lineHeight: 1.15, cursorBlink: true, allowProposedApi: true,
      scrollback: 10000, theme: TEMA, macOptionIsMeta: true,
    });
    this.fit = new window.FitAddon.FitAddon();
    this.term.loadAddon(this.fit);
    this.term.loadAddon(new window.Unicode11Addon.Unicode11Addon());
    this.term.unicode.activeVersion = "11";
    this.term.loadAddon(new window.WebLinksAddon.WebLinksAddon());
    this.term.open(contenitore);
    try {
      this.gl = new window.WebglAddon.WebglAddon();
      this.gl.onContextLoss(() => { this.gl.dispose(); this.gl = null; });
      this.term.loadAddon(this.gl);
    } catch (e) { this.gl = null; /* senza WebGL resta il renderer DOM */ }

    this.term.attachCustomKeyEventHandler((e) => {
      if (e.type !== "keydown") return true;
      if (e.key === "Enter" && e.shiftKey) { this.invia("\x1b\r"); return false; }
      if (e.ctrlKey && !e.shiftKey && e.key.toLowerCase() === "c" && this.term.hasSelection()) {
        navigator.clipboard.writeText(this.term.getSelection()); this.term.clearSelection(); return false;
      }
      if (e.ctrlKey && e.key.toLowerCase() === "v") { this.incolla(); e.preventDefault(); return false; }
      return true;
    });
    contenitore.addEventListener("contextmenu", (e) => { e.preventDefault(); this.incolla(); });
    this.term.onData((d) => this.invia(d));
    this.collega();
    // durante un'animazione (allarga, ridimensiona finestra) arrivano molte misure:
    // si adatta una volta sola, quando la misura si e' fermata
    this.osservatore = new ResizeObserver(() => { cancelAnimationFrame(this.attesa); this.attesa = requestAnimationFrame(() => this.adatta()); });
    this.osservatore.observe(contenitore);
    document.fonts.ready.then(() => { if (!this.chiusa) this.adatta(true); });
  }

  collega() {
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => this.adatta(true);
    this.ws.onmessage = (e) => {
      const d = e.data;
      if (d.startsWith('{"t":"x"')) {
        try { const m = JSON.parse(d); this.chiusa = true; this.allUscita && this.allUscita(m.code); return; } catch (_) {}
      }
      this.term.write(d);
    };
  }

  invia(testo) {
    if (this.ws && this.ws.readyState === 1 && !this.chiusa) this.ws.send(JSON.stringify({ t: "i", d: testo }));
  }

  async incolla() {
    try { const t = await navigator.clipboard.readText(); if (t) this.term.paste(t); } catch (_) {}
  }

  adatta(forza = false) {
    const el = this.term.element;
    if (!el || !el.clientWidth || !el.clientHeight) return;  // senza misure: si riprova al prossimo cambio
    const prima = [this.term.cols, this.term.rows];
    try { this.fit.fit(); } catch (_) { return; }
    const cambiata = prima[0] !== this.term.cols || prima[1] !== this.term.rows;
    if ((forza || cambiata) && this.ws && this.ws.readyState === 1)
      this.ws.send(JSON.stringify({ t: "r", cols: this.term.cols, rows: this.term.rows }));
    if (cambiata || forza) this.ridisegna();
  }

  // ridisegno completo: dopo un cambio di misura o quando la linguetta torna visibile
  ridisegna() {
    try { if (this.gl) this.gl.clearTextureAtlas(); } catch (_) {}
    this.term.refresh(0, this.term.rows - 1);
  }

  fuoco() { this.term.focus(); }

  distruggi() {
    tutte.delete(this);
    this.osservatore.disconnect();
    cancelAnimationFrame(this.attesa);
    try { this.ws.close(); } catch (_) {}
    this.term.dispose();
  }
}
