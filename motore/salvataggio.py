# Stato di salvataggio delle note per una sessione di Claude Code, dai segni
# lasciati dagli hook in ~/.claude/second-brain/segni/: <id>.in-corso (scritto
# alla chiusura) e <id>.salvata (scritto dal worker a fine riassunto).
import time
from datetime import datetime
from pathlib import Path

from percorsi import SOGLIA_SIGNIFICATIVA
from sessioni import Sessione

ATTESA_MAX = 15 * 60
MARGINE = 60


def _prima_attivazione(s: Sessione, segni: Path) -> bool:
    # segni/attivazione: momento in cui gli hook hanno iniziato a scrivere i segni
    try:
        soglia = datetime.fromisoformat((segni / "attivazione").read_text(encoding="utf-8").strip())
        return s.ultima.astimezone() < soglia.astimezone()
    except (OSError, ValueError, TypeError, AttributeError, OverflowError):
        return False


def stato_salvataggio(s: Sessione, segni: Path) -> str:
    if s.dimensione < SOGLIA_SIGNIFICATIVA:
        return "breve"
    if _prima_attivazione(s, segni):
        return "salvata"
    # un segno vale solo se non e' anteriore all'ultima attivita' della chat (ripresa dopo il salvataggio)
    minimo = s.ultima.timestamp() - MARGINE
    def tempo(tipo):
        try:
            return (segni / f"{s.id}.{tipo}").stat().st_mtime
        except OSError:
            return 0
    errore, corso, salvata = tempo("errore"), tempo("in-corso"), tempo("salvata")
    if errore >= minimo and errore > max(corso, salvata):
        return "errore_salvataggio"
    if corso >= minimo and corso > salvata:
        return "in_corso" if time.time() - corso <= ATTESA_MAX else "errore_salvataggio"
    try:
        if (segni / f"{s.id}.salvata").stat().st_mtime >= minimo:
            return "salvata"
    except OSError:
        pass
    try:
        mtime = (segni / f"{s.id}.in-corso").stat().st_mtime
    except OSError:
        return "non_salvata"
    return "in_corso" if mtime >= minimo and time.time() - mtime <= ATTESA_MAX else "non_salvata"
