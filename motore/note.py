# Note al volo: salva una riga in Inbox/ con nome di una parola scelto da Haiku.
import re
from datetime import datetime
from pathlib import Path

from haiku import chiedi_haiku

PROMPT = ("Dai a questa nota un nome di UNA sola parola italiana o inglese, super "
          "descrittiva, minuscola. Rispondi solo con la parola.\n\nNota: ")


def _pulisci(risposta: str | None) -> str | None:
    if not risposta:
        return None
    s = risposta.strip().strip(".,;:!?\"'`*_()[]").lower()
    if not s or not re.fullmatch(r"[^\W_]+(?:-[^\W_]+)*", s):
        return None
    return s[:30].strip("-") or None


def _libero(inbox: Path, adesso: datetime, nome: str) -> Path:
    data = f"{adesso:%Y-%m-%d}"
    percorso = inbox / f"{data} {nome}.md"
    n = 2
    while percorso.exists():
        percorso = inbox / f"{data} {nome}-{n}.md"
        n += 1
    return percorso


def salva_nota_subito(testo: str, inbox: Path, adesso: datetime) -> Path:
    # scrive subito la nota col nome di ripiego (nota-HHMM), senza aspettare Haiku
    testo = testo.strip()
    if not testo:
        raise ValueError("nota vuota")
    inbox.mkdir(parents=True, exist_ok=True)
    percorso = _libero(inbox, adesso, f"nota-{adesso:%H%M}")
    corpo = f"{testo}\n\n_Nota al volo, {adesso:%Y-%m-%d %H:%M}_\n"
    with open(percorso, "w", encoding="utf-8", newline="\n") as f:
        f.write(corpo)
    return percorso


def rinomina_nota(percorso: Path, testo: str, adesso: datetime, chiedi=chiedi_haiku) -> Path:
    # chiede il nome a Haiku e rinomina il file; se qualcosa va storto resta il nome di ripiego
    nome = _pulisci(chiedi(PROMPT + testo.strip(), 20))
    if not nome:
        return percorso
    nuovo = _libero(percorso.parent, adesso, nome)
    try:
        percorso.rename(nuovo)
    except OSError:
        return percorso
    return nuovo


def salva_nota(testo: str, inbox: Path, adesso: datetime, chiedi=chiedi_haiku) -> Path:
    return rinomina_nota(salva_nota_subito(testo, inbox, adesso), testo, adesso, chiedi)
