# Parole chiave delle chat: Haiku riassume ogni sessione in 1-3 argomenti.
# Cache JSON {id: {"dimensione": int, "parole": str}} valida finche' la
# dimensione del trascritto non cambia; scrittura atomica. Solo le sessioni
# significative (>= 30 KB o >= 3 messaggi utente) vengono mandate a Haiku:
# per le altre e in caso di errore la UI usa ripiego().
import json
import os
import threading
import time
from pathlib import Path

from haiku import chiedi_haiku
from percorsi import SOGLIA_SIGNIFICATIVA
from sessioni import Sessione

PROMPT = ("Elenca in italiano da 1 a 3 argomenti di questa chat, 1-3 parole ciascuno, "
          "separati da virgola, nient'altro.\n\n")
_blocco = threading.Lock()


def ripiego(s: Sessione) -> str:
    righe = s.primo_messaggio.strip().splitlines()
    testo = righe[0].strip() if righe else ""
    if len(testo) <= 50:
        return testo
    taglio = testo[:49].rsplit(" ", 1)[0] if " " in testo[:49] else testo[:49]
    return taglio.rstrip(" ,.;:") + "…"


def _carica(cache: Path) -> dict:
    try:
        d = json.loads(Path(cache).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def _salva(cache: Path, dati: dict) -> None:
    cache = Path(cache)
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_name(f"{cache.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, cache)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _formatta(risposta: str) -> str:
    voci = [v.strip().strip(".").strip() for v in risposta.replace("\n", ",").split(",")]
    voci = [v for v in voci if v][:3]
    voci = [v[:1].lower() + v[1:] if i == 0 else v for i, v in enumerate(voci)]
    testo = " · ".join(voci)
    # oltre 60 caratteri si tolgono argomenti interi, mai a meta' parola
    while len(testo) > 60 and " · " in testo:
        testo = testo.rsplit(" · ", 1)[0]
    if len(testo) > 60:
        testo = testo[:59].rsplit(" ", 1)[0] + "…"
    return testo


def _valida(voce, s: Sessione) -> bool:
    return isinstance(voce, dict) and voce.get("dimensione") == s.dimensione and bool(voce.get("parole"))


def parole_chiave(s: Sessione, cache: Path, chiedi=chiedi_haiku) -> str | None:
    voce = _carica(cache).get(s.id)
    return _formatta(voce["parole"].replace(" · ", ",")) if isinstance(voce, dict) and voce.get("parole") else None


def aggiorna_parole(sessioni: list[Sessione], cache: Path, chiedi=chiedi_haiku) -> None:
    for s in sessioni:
        try:
            _aggiorna_una(s, cache, chiedi)
        except Exception:
            continue


def _aggiorna_una(s: Sessione, cache: Path, chiedi) -> None:
    if s.dimensione < SOGLIA_SIGNIFICATIVA and s.n_messaggi < 3:
        return
    if _valida(_carica(cache).get(s.id), s):
        return
    risposta = chiedi(PROMPT + s.testo_utente)
    parole = _formatta(risposta) if risposta else ""
    if not parole:
        return
    with _blocco:
        dati = _carica(cache)
        dati[s.id] = {"dimensione": s.dimensione, "parole": parole}
        for tentativo in range(3):
            try:
                _salva(cache, dati)
                return
            except PermissionError:
                time.sleep(0.2)
        _salva(cache, dati)
