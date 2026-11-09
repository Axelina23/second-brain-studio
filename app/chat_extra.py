# Azioni extra sulle chat (menu del tasto destro): titoli scelti a mano e chat fissate
# (cache/chat-meta.json), esportazione in Markdown, riga del Registro che parla della
# chat, ricerca veloce nel testo completo (gia' in memoria, vedi sessioni._leggi).
import json
import re
from datetime import timedelta
from pathlib import Path

import assistenti as mod_assistenti
import sessioni as mod_sessioni

MAX_TITOLO = 80
PAROLE_VUOTE = {"della", "delle", "degli", "dello", "nella", "nelle", "sono", "come", "cosa", "questo", "questa",
                "quello", "quella", "anche", "perche", "perché", "fare", "fammi", "dimmi", "voglio", "vorrei",
                "possiamo", "puoi", "allora", "sulla", "sulle", "dalla", "alla", "alle", "agli", "però", "with", "that",
                # presenti in quasi ogni riga del Registro: non distinguono niente
                "claude", "code", "chat", "file", "nessun", "nessuno", "solo", "risposta", "fatto"}


# ---------- titoli e chat fissate ----------
def leggi_meta(cache: Path) -> dict:
    try:
        d = json.loads((cache / "chat-meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    titoli = d.get("titoli") if isinstance(d.get("titoli"), dict) else {}
    fissate = d.get("fissate") if isinstance(d.get("fissate"), list) else []
    return {"titoli": {k: v for k, v in titoli.items() if isinstance(v, str)},
            "fissate": [x for x in fissate if isinstance(x, str)]}


def scrivi_meta(cache: Path, meta: dict) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    tmp = cache / "chat-meta.json.tmp"
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(cache / "chat-meta.json")


def pulisci_titolo(titolo) -> str:
    return re.sub(r"\s+", " ", str(titolo or "")).strip()[:MAX_TITOLO]


# ---------- esportazione ----------
def _nome_file(testo: str) -> str:
    t = re.sub(r"[^\w\s-]", "", testo, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_]+", "-", t)[:50].strip("-") or "chat"


def _turni_claude(percorso: Path):
    # (chi, testo, None) come assistenti.turni, dal trascritto di Claude Code
    with open(percorso, encoding="utf-8", errors="replace") as f:
        for riga in f:
            try:
                r = json.loads(riga)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("isMeta"):
                continue
            t = mod_sessioni._testo(r.get("message")).strip()
            if r.get("type") == "user" and t and not t.startswith(mod_sessioni.PREFISSI_COMANDO + ("<system-reminder",)):
                yield "utente", t, None
            elif r.get("type") == "assistant" and t:
                yield "assistente", t, None


def esporta_markdown(sessione, etichetta: str, cartella: Path) -> Path:
    # conversazione leggibile: messaggi dell'utente e testo delle risposte, niente tool
    assistente = getattr(sessione, "assistente", "claude")
    strumento = mod_assistenti.STRUMENTI.get(assistente, "Claude Code")
    righe = [f"# {etichetta}", "", f"Chat di {strumento} del {sessione.ultima:%Y-%m-%d %H:%M} · id `{sessione.id}`", ""]
    ultimo = None  # chi ha scritto il blocco precedente: le risposte di fila stanno sotto un titolo
    nome = mod_assistenti.NOMI.get(assistente, "Claude")
    turni = _turni_claude(sessione.percorso) if assistente == "claude" else mod_assistenti.turni(sessione.percorso, assistente)
    for chi, t, _ in turni:
        if chi == "utente":
            righe += ["## Tu", "", t, ""]
        else:
            righe += ([] if ultimo == chi else [f"## {nome}", ""]) + [t, ""]
        ultimo = chi
    cartella.mkdir(parents=True, exist_ok=True)
    base = f"{sessione.ultima:%Y-%m-%d} chat {_nome_file(etichetta)}"
    dest, n = cartella / f"{base}.md", 2
    while dest.exists():
        dest = cartella / f"{base}-{n}.md"
        n += 1
    dest.write_text("\n".join(righe).rstrip() + "\n", encoding="utf-8")
    return dest


# ---------- Registro ----------
def _parole(testo: str) -> set:
    return {w for w in re.findall(r"[\wàèéìòù]{4,}", testo.lower()) if w not in PAROLE_VUOTE}


def riga_registro(registro: Path, sessione, etichetta: str) -> str | None:
    # il Registro non ha l'id delle chat: si cerca tra le righe dello stesso giorno (o del
    # giorno prima, per le chat a cavallo di mezzanotte) quella con piu' parole in comune
    try:
        testo = registro.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    stesso = f"{sessione.ultima:%Y-%m-%d}"
    prima = f"{sessione.ultima - timedelta(days=1):%Y-%m-%d}"
    cerca = _parole(f"{etichetta} {sessione.primo_messaggio} {sessione.testo_utente[-2000:]}")
    migliore, punti_max = None, 0
    for riga in testo.splitlines():
        m = re.match(r"^\s*-\s*(\d{4}-\d{2}-\d{2})", riga)
        if not m or m.group(1) not in (stesso, prima):
            continue
        # il giorno prima vale solo se le parole in comune sono davvero tante
        punti = len(cerca & _parole(riga)) - (3 if m.group(1) == prima else 0)
        if punti > punti_max:
            migliore, punti_max = riga.strip(), punti
    return migliore if punti_max >= 3 else None


# ---------- ricerca nel testo ----------
def cerca_nel_testo(sessioni_elenco, query: str, limite: int = 200) -> list[dict]:
    parole = [w for w in query.lower().split() if w]
    if not parole:
        return []
    trovate = []
    for s in sessioni_elenco:
        t = s.testo_completo
        if t and all(w in t for w in parole):
            i = t.find(parole[0])
            inizio = max(0, i - 50)
            estratto = re.sub(r"\s+", " ", t[inizio:i + 110]).strip()
            trovate.append({"id": s.id, "estratto": ("…" if inizio else "") + estratto + "…"})
            if len(trovate) >= limite:
                break
    return trovate
