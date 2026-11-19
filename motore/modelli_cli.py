# Elenco dei modelli che le CLI degli assistenti dichiarano disponibili:
# - Antigravity: `agy models` (una riga per modello: slug<TAB>nome)
# - Codex: `codex debug models` (JSON, si tengono solo quelli con visibility "list")
# Il risultato sta in ~/.claude/second-brain/modelli.json e si rinnova da solo ogni 6 ore.
# Gli elenchi fissi di assistenti.py restano il ripiego se la CLI manca o non risponde.
import json
import os
import re
import subprocess
import time

import assistenti
import percorsi

DURATA = 6 * 3600
RE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _file():
    return percorsi.CACHE / "modelli.json"


def _esegui(argv: list[str], timeout: float = 40) -> str | None:
    try:
        r = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, creationflags=_FLAGS,
                           env={**os.environ, "NO_COLOR": "1"})
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def leggi_agy(testo: str) -> list[dict]:
    modelli = []
    for riga in testo.splitlines():
        parti = riga.rstrip().split("\t", 1)
        # salta "Fetching...", righe vuote e gli "orchestrator" (non sono modelli da scegliere)
        if len(parti) != 2 or not RE_SLUG.match(parti[0]) or "orchestrator" in parti[0]:
            continue
        modelli.append({"id": parti[0], "nome": parti[1].strip()})
    return modelli


def leggi_codex(testo: str) -> list[dict]:
    try:
        dati = json.loads(testo)
    except ValueError:
        return []
    modelli = []
    for m in dati.get("models", []) if isinstance(dati, dict) else []:
        slug = m.get("slug") if isinstance(m, dict) else None
        if isinstance(slug, str) and RE_SLUG.match(slug) and m.get("visibility") == "list":
            modelli.append({"id": slug, "nome": str(m.get("display_name") or slug)})
    return modelli


_LETTORI = {"agy": (["models"], leggi_agy), "codex": (["debug", "models"], leggi_codex)}


def scarica(nome: str) -> list[dict] | None:
    try:
        base = assistenti.comando(nome)
        if not base or nome not in _LETTORI:
            return None
        args, lettore = _LETTORI[nome]
        testo = _esegui([*base, *args])
        return (lettore(testo) if testo else []) or None
    except Exception:
        return None


def _cache() -> dict:
    try:
        d = json.loads(_file().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def elenco(nome: str) -> list[dict]:
    voci = (_cache().get("assistenti") or {}).get(nome)
    return [v for v in voci if isinstance(v, dict) and RE_SLUG.match(str(v.get("id", "")))] if isinstance(voci, list) else []


def conosce(nome: str, modello: str) -> bool:
    return any(v["id"] == modello for v in elenco(nome))


def scaduta() -> bool:
    return time.time() - float(_cache().get("aggiornata") or 0) > DURATA


def aggiorna(forza: bool = False) -> dict:
    # Rilegge le CLI se l'elenco e' vecchio (o se forza). Una CLI che fallisce
    # lascia il suo elenco precedente: nessun errore per l'utente, resta il ripiego.
    if not forza and not scaduta():
        return _cache()
    vecchi = _cache().get("assistenti") or {}
    nuovi = {}
    for nome in _LETTORI:
        scaricati = scarica(nome)
        if scaricati:
            nuovi[nome] = scaricati
        elif vecchi.get(nome):
            nuovi[nome] = vecchi[nome]
    dati = {"aggiornata": time.time(), "assistenti": nuovi}
    try:
        percorsi.CACHE.mkdir(parents=True, exist_ok=True)
        tmp = _file().with_suffix(".tmp")
        tmp.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, _file())
    except OSError:
        pass
    return dati


def catalogo() -> dict:
    return {"assistenti": {n: elenco(n) for n in _LETTORI}}


LIVELLI = ("low", "medium", "high", "xhigh")
RE_LIVELLO = re.compile(r"(.+)-(low|medium|high|xhigh)")


def con_livello(modello: str, impegno: str) -> str:
    # gemini-4-neon-medium + "high" -> gemini-4-neon-high; se quel livello non esiste per il modello
    # si prende il piu' vicino verso il basso (poi verso l'alto). "max" vale xhigh.
    m = RE_LIVELLO.fullmatch(modello or "")
    if not m or impegno not in (*LIVELLI, "max"):
        return modello
    disponibili = [l for l in LIVELLI if conosce("agy", f"{m.group(1)}-{l}")]
    if not disponibili:
        return modello
    voluto = LIVELLI.index("xhigh" if impegno == "max" else impegno)
    sotto = [l for l in disponibili if LIVELLI.index(l) <= voluto]
    return f"{m.group(1)}-{(sotto[-1] if sotto else disponibili[0])}"


def ultimo_codex(modello: str) -> str:
    # gpt-6-sol -> gpt-6.2-sol: la versione piu' nuova della stessa famiglia nell'elenco
    m = re.fullmatch(r"gpt-(\d+(?:\.\d+)*)-([a-z]+)", modello or "")
    if not m:
        return modello
    def versione(slug):
        return tuple(int(x) for x in slug.split("-")[1].split("."))
    stessi = [v["id"] for v in elenco("codex") if v["id"].endswith("-" + m.group(2)) and re.fullmatch(r"gpt-\d+(?:\.\d+)*-[a-z]+", v["id"])]
    return max(stessi, key=versione, default=modello) if stessi else modello
