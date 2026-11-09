# Avvisi di Claude: l'hook avviso.ps1 (Stop / Notification) lascia un file JSON in
# ~/.claude/second-brain/eventi; qui si leggono, si arricchiscono (progetto, titolo della
# chat, anteprima della risposta) e si cancellano. Decide main.py se mostrarli.
import json
import time
from pathlib import Path

VECCHIO = 15 * 60  # eventi rimasti da quando l'app era chiusa: niente notifiche in ritardo


def leggi_eventi(cartella: Path, adesso: float | None = None) -> list[dict]:
    cartella = Path(cartella)
    if not cartella.is_dir():
        return []
    adesso = adesso or time.time()
    eventi = []
    for f in sorted(cartella.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            d = None
        try:
            f.unlink()
        except OSError:
            continue  # lo sta ancora scrivendo qualcuno: si riprende al giro dopo
        if isinstance(d, dict) and adesso - float(d.get("quando") or 0) < VECCHIO:
            eventi.append(d)
    return eventi


def accorcia(testo: str, massimo: int = 180) -> str:
    testo = " ".join(str(testo or "").replace("*", "").replace("`", "").split())
    return testo if len(testo) <= massimo else testo[:massimo - 1].rsplit(" ", 1)[0] + "…"


def ultima_risposta(trascrizione: str | None, massimo: int = 180) -> str:
    # testo dell'ultima risposta di Claude, dalle ultime righe della trascrizione
    if not trascrizione:
        return ""
    p = Path(trascrizione)
    try:
        with open(p, "rb") as f:
            f.seek(max(0, p.stat().st_size - 256 * 1024))
            righe = f.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for riga in reversed(righe):
        if '"assistant"' not in riga:
            continue
        try:
            o = json.loads(riga)
        except ValueError:
            continue
        if o.get("type") != "assistant":
            continue
        parti = (o.get("message") or {}).get("content") or []
        testo = " ".join(x.get("text", "") for x in parti if isinstance(x, dict) and x.get("type") == "text").strip()
        if testo:
            testo = " ".join(testo.replace("*", "").replace("`", "").split())
            return testo if len(testo) <= massimo else testo[:massimo - 1].rsplit(" ", 1)[0] + "…"
    return ""


def nome_progetto(cwd: str | None, radice: Path | None) -> str:
    # "Negozio" per una chat in Progetti/Negozio (Projects/ nella struttura inglese),
    # "Second brain" per la cartella principale,
    # altrimenti il nome della cartella di lavoro (es. un repository aperto da VS Code)
    if not cwd:
        return "Claude"
    c = Path(cwd)
    if radice:
        try:
            rel = c.resolve().relative_to(Path(radice).resolve())
            if rel.parts[:1] in (("Progetti",), ("Projects",)) and len(rel.parts) > 1:
                return rel.parts[1]
            return "Second brain" if not rel.parts else rel.parts[0]
        except (ValueError, OSError):
            pass
    return c.name or str(c)
