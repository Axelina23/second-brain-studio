# Legge le sessioni interattive di Claude Code dai trascritti .jsonl.
# Esclude le esecuzioni headless (entrypoint "sdk-cli") e le sessioni senza
# messaggi utente testuali. I file sono letti riga per riga (possono essere enormi).
# Con completo=True raccoglie anche il testo di domande e risposte (niente output dei
# tool), in minuscolo e al massimo MAX_COMPLETO caratteri: serve alla ricerca nelle chat.
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

MAX_TESTO = 6000
MAX_COMPLETO = 1_000_000
PREFISSI_COMANDO = ("<local-command", "<command-")


@dataclass
class Sessione:
    id: str
    percorso: Path
    ultima: datetime
    dimensione: int
    primo_messaggio: str
    testo_utente: str
    n_messaggi: int = 0
    testo_completo: str = ""  # solo con completo=True, in minuscolo
    assistente: str = "claude"  # claude, codex o agy (vedi assistenti.py)


def _testo(messaggio) -> str:
    contenuto = messaggio.get("content") if isinstance(messaggio, dict) else None
    if isinstance(contenuto, str):
        return contenuto
    if isinstance(contenuto, list):
        return "\n".join(b.get("text", "") for b in contenuto
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _data(ts) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
    except (AttributeError, ValueError):
        return None


def _leggi(percorso: Path, completo: bool = False) -> Sessione | None:
    entrypoint = None
    ultima = None
    messaggi = []
    tutto, dim_tutto = [], 0
    with open(percorso, encoding="utf-8", errors="replace") as f:
        for riga in f:
            try:
                r = json.loads(riga)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            if entrypoint is None and r.get("entrypoint"):
                entrypoint = r["entrypoint"]
            d = _data(r.get("timestamp"))
            if d:
                ultima = d
            # isMeta: righe iniettate da Claude Code (report subagent, skill), non dell'utente
            if r.get("type") == "user" and not r.get("isMeta"):
                t = _testo(r.get("message")).strip()
                if t and not t.startswith(PREFISSI_COMANDO):
                    messaggi.append(t)
                    if completo and dim_tutto < MAX_COMPLETO:
                        tutto.append(t)
                        dim_tutto += len(t)
            elif completo and r.get("type") == "assistant" and dim_tutto < MAX_COMPLETO:
                t = _testo(r.get("message")).strip()
                if t:
                    tutto.append(t)
                    dim_tutto += len(t)
    if entrypoint == "sdk-cli" or not messaggi:
        return None
    st = percorso.stat()
    if ultima is None:
        ultima = datetime.fromtimestamp(st.st_mtime).astimezone()
    return Sessione(percorso.stem, percorso, ultima, st.st_size, messaggi[0],
                    "\n".join(messaggi)[-MAX_TESTO:], len(messaggi),
                    "\n".join(tutto)[:MAX_COMPLETO].lower() if completo else "")


def elenca_sessioni(cartella: Path) -> list[Sessione]:
    risultato = []
    for p in Path(cartella).glob("*.jsonl"):
        try:
            s = _leggi(p)
        except OSError:
            continue
        if s:
            risultato.append(s)
    return sorted(risultato, key=lambda s: s.ultima, reverse=True)
