# Riga "oggi" della home: eventi di calendario di oggi (da cal.py) e scadenze
# dei prossimi 7 giorni (una riga di Haiku, con cache giornaliera in CACHE).
# Tutte le funzioni degradano in silenzio (lista vuota / None) su errore.
import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from haiku import chiedi_haiku
from percorsi import python_di_sistema
import struttura

MAX_PROMPT = 12000
MAX_RIGA = 160
PAUSA_ERRORE = 3600
SEP = " \u00b7 "
_EVENTO = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?\S*\s*\|[^|]*\|\s*([^|]+?)\s*(?:\||$)")


def eventi_oggi(radice: Path, timeout: float = 5, oggi: date | None = None) -> list[str]:
    giorno = (oggi or date.today()).isoformat()
    script = Path(radice) / struttura.di(radice)["sistema"] / "calendario" / "cal.py"
    try:
        r = subprocess.run([python_di_sistema(), str(script), "lista", "1"],
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                           timeout=timeout, encoding="utf-8", errors="replace", capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    righe = []
    for riga in r.stdout.splitlines():
        m = _EVENTO.match(riga.strip())
        if not m or m.group(1) != giorno:
            continue
        ora, titolo = m.group(2), m.group(3)
        righe.append(f"{ora} {titolo}" if ora else titolo)
    return righe


def _leggi(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _progetti_attivi(radice: Path) -> list[Path]:
    st = struttura.di(radice)
    indice = _leggi(radice / st["indice"])
    m = re.search(r"^## (?:Progetti attivi|Active projects)\s*$(.*?)(?=^## |\Z)", indice, re.S | re.M)
    if not m:
        return []
    return [radice / p for p in re.findall(rf"`({re.escape(st['progetti'])}/[^`]+/CLAUDE\.md)`", m.group(1))]


def _stati_delle_aree(radice: Path) -> list[Path]:
    # il file di stato (stato.md / status.md) di ogni area: Università, Work, Famiglia...
    st = struttura.di(radice)
    if not radice.is_dir():
        return []
    aree = sorted((d for d in radice.iterdir() if d.is_dir() and struttura.gruppo(d.name, st) not in (None, "Io", "Sistema")),
                  key=lambda d: d.name.lower())
    return [d / st["stato"] for d in aree if (d / st["stato"]).is_file()]


PROMPT_SCADENZE = {
    "it": ("Usa SOLO il materiale qui sopra: non leggere file, non fare domande, non spiegare. "
           "Rispondi con una riga sola: esami, appuntamenti importanti e scadenze dei prossimi 7 giorni, "
           "formato `cosa data`, separati da ' \u00b7 ', senza grassetto. Oggi \u00e8 {oggi}."),
    "en": ("Use ONLY the material above: don't read files, don't ask questions, don't explain. "
           "Answer with a single line: exams, important appointments and deadlines in the next 7 days, "
           "format `what date`, separated by ' \u00b7 ', no bold. Today is {oggi}."),
}


def _scrivi(file: Path, dati: dict) -> None:
    try:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(dati, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def scadenze(radice: Path, cache: Path, oggi: date, chiedi=chiedi_haiku) -> str | None:
    file = Path(cache) / "scadenze.json"
    try:
        dati = json.loads(file.read_text(encoding="utf-8"))
        if dati.get("data") == oggi.isoformat() and dati.get("testo"):
            return dati["testo"]
        if float(dati.get("riprova_dopo") or 0) > time.time():
            return None
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    radice = Path(radice)
    parti = [(p.relative_to(radice).as_posix(), _leggi(p)) for p in _stati_delle_aree(radice) + _progetti_attivi(radice)]
    if not parti:
        return None
    # ogni file ha la sua quota, cosi' nessuno resta tagliato fuori dal materiale
    quota = MAX_PROMPT // max(1, len(parti))
    materiale = "\n\n".join(f"### {n}\n{t[:quota]}" for n, t in parti)
    prompt = f"{materiale}\n\n" + PROMPT_SCADENZE[struttura.rileva(radice)].format(oggi=oggi.isoformat())
    testo = chiedi(prompt, timeout=60)
    if testo and not _riga_valida(testo):
        testo = None
    if not testo:
        _scrivi(file, {"data": oggi.isoformat(), "testo": None,
                       "riprova_dopo": time.time() + PAUSA_ERRORE})
        return None
    testo = " ".join(testo.split())
    _scrivi(file, {"data": oggi.isoformat(), "testo": testo})
    return testo


def _riga_valida(testo: str) -> bool:
    # scarta le risposte che non sono la riga chiesta (spiegazioni, richieste di permessi)
    t = " ".join(testo.split())
    vietate = ("**", "permess", "non riesco", "concedi", "leggere", "permission", "can't", "cannot", "unable", "grant")
    return 0 < len(t) <= 220 and not any(v in t.lower() for v in vietate)


def _taglia(t: str) -> str:
    return t if len(t) <= MAX_RIGA else t[:MAX_RIGA - 1] + "\u2026"


def riga_oggi(eventi: list[str], scadenze: str | None) -> str:
    righe = []
    if eventi:
        righe.append(_taglia(SEP.join(eventi)))
    if scadenze:
        righe.append(_taglia(scadenze))
    return "\n".join(righe)
