# Elenco degli appunti del second brain con la loro eta' (pagina "Appunti", sola lettura).
# Gruppi: ogni cartella di primo livello con file .md diretti (Io, Sistema e le aree come
# Università o Work), Progetti (<Nome>/CLAUDE.md e Personali.md), Generali (registro e
# indice). Struttura italiana o inglese: vedi struttura.py. Il resto e' escluso.
# I progetti abbandonati si leggono dalla riga "Abbandonato ... : Nome →" dell'indice
# ("Abandoned ... : Name →" nella struttura inglese).
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import struttura

RE_ABBANDONATI = re.compile(r"(?:abbandonat|abandoned)[^:]*:\s*([^→]+?)\s*→", re.IGNORECASE)


@dataclass
class Appunto:
    gruppo: str
    nome: str
    percorso: Path
    modificato: datetime
    abbandonato: bool


def _abbandonati(radice: Path) -> set[str]:
    indice = Path(radice) / struttura.di(radice)["indice"]
    if not indice.is_file():
        return set()
    trovati = set()
    for riga in indice.read_text(encoding="utf-8", errors="replace").splitlines():
        m = RE_ABBANDONATI.search(riga)
        if m:
            trovati.add(m.group(1).replace("*", "").strip())
    return trovati


def _mod(p: Path) -> datetime:
    return datetime.fromtimestamp(p.stat().st_mtime).astimezone()


def elenca_appunti(radice: Path) -> list[Appunto]:
    radice = Path(radice)
    s = struttura.di(radice)
    abb = _abbandonati(radice)
    out = []

    def aggiungi(gruppo, nome, p):
        out.append(Appunto(gruppo, nome, p, _mod(p), gruppo == "Progetti" and nome in abb))

    cartelle = sorted((d for d in radice.iterdir() if d.is_dir()), key=lambda d: d.name.lower()) if radice.is_dir() else []
    for d in cartelle:
        g = struttura.gruppo(d.name, s)
        if g:
            for p in sorted(d.glob("*.md")):
                aggiungi(g, p.stem, p)
    prog = radice / s["progetti"]
    if prog.is_dir():
        for d in sorted(x for x in prog.iterdir() if x.is_dir()):
            p = d / "CLAUDE.md"
            if p.is_file():
                aggiungi("Progetti", d.name, p)
        p = prog / s["personali"]
        if p.is_file():
            aggiungi("Progetti", p.stem, p)
    for rel in (s["registro"], s["indice"]):
        p = radice / rel
        if p.is_file():
            aggiungi("Generali", p.stem, p)
    return out


def colore(giorni: float) -> str:
    if giorni < 7:
        return "verde"
    return "giallo" if giorni <= 14 else "rosso"


def eta(modificato: datetime, adesso: datetime) -> str:
    giorni = (adesso - modificato).total_seconds() / 86400
    if giorni < 1:
        return "oggi"
    if giorni < 2:
        return "ieri"
    return f"{int(giorni)} g"
