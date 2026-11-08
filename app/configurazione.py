# Primo avvio: controlla i requisiti (Claude Code, git, accesso a Claude), valuta la
# cartella scelta e completa la configurazione (second brain nuovo, esistente o
# scaricato da GitHub; collegamento a CLAUDE.md e agli hook di Claude Code).
# La configurazione finisce in ~/.claude/second-brain/config.json (vedi motore/percorsi.py).
import json
import shutil
import subprocess
from pathlib import Path

import modello
import percorsi
import struttura

_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _accesso_claude() -> bool:
    # Claude Code salva l'account in ~/.claude.json dopo /login
    try:
        d = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
        return bool(d.get("oauthAccount"))
    except (OSError, ValueError):
        return False


def stato() -> dict:
    claude = percorsi.trova_claude()
    radice = percorsi.radice_configurata()
    precedente = percorsi.leggi_config().get("radice_precedente")
    return {"configurato": radice is not None, "radice": str(radice) if radice else None,
            "precedente": precedente if precedente and Path(precedente).is_dir() and radice is None else None,
            "proposta": str(Path.home() / "Second Brain"),
            "requisiti": {"claude": str(claude) if claude else None, "git": bool(shutil.which("git")),
                          "accesso": _accesso_claude()}}


def valuta_cartella(percorso: str) -> dict:
    if not percorso or not isinstance(percorso, str):
        return {"errore": "Scegli una cartella"}
    p = Path(percorso).expanduser()
    if not p.is_absolute():
        return {"errore": "Serve un percorso completo, ad esempio C:\\Users\\nome\\Second Brain"}
    if p.exists() and not p.is_dir():
        return {"errore": "C'è già un file con quel nome"}
    esiste = p.is_dir()
    contenuto = [x.name for x in p.iterdir()][:50] if esiste else []
    return {"percorso": str(p), "esiste": esiste, "vuota": not contenuto,
            "second_brain": struttura.ha_indice(p), "git": (p / ".git").exists(),
            "file": len(contenuto)}


def apri_accesso_claude() -> dict:
    # /login di Claude Code vuole un terminale vero: apre claude in una finestra a parte
    claude = percorsi.trova_claude()
    if not claude:
        return {"errore": "Claude Code non è installato"}
    subprocess.Popen(["cmd", "/c", "start", "Accesso a Claude", str(claude)], cwd=str(Path.home()),
                     creationflags=_FLAGS)
    return {"ok": True}


def completa(scelte: dict, github, cartella_hook_app: Path) -> dict:
    # scelte: {modo: nuovo|esistente|github, cartella, risposte, repo (url per github),
    #          claude_md: bool, hook: bool}
    scelte = scelte if isinstance(scelte, dict) else {}
    modo = scelte.get("modo")
    v = valuta_cartella(scelte.get("cartella", ""))
    if "errore" in v:
        return v
    radice = Path(v["percorso"])
    risposte = scelte.get("risposte") if isinstance(scelte.get("risposte"), dict) else {}
    passi = []
    if modo == "nuovo":
        if v["second_brain"]:
            return {"errore": "In quella cartella c'è già un second brain: scegli \"Ne ho già uno\""}
        modello.crea_struttura(radice, risposte)
        passi.append("Cartelle, regole e indice creati")
    elif modo == "esistente":
        if not v["esiste"]:
            return {"errore": "La cartella non esiste"}
        if not v["second_brain"]:
            # cartella di appunti senza indice: si aggiungono solo i file che mancano
            modello.crea_struttura(radice, risposte, git=not v["git"])
            passi.append("Aggiunti indice e regole che mancavano")
    elif modo == "github":
        if v["esiste"] and not v["vuota"]:
            return {"errore": "Per scaricare da GitHub serve una cartella nuova o vuota"}
        esito = github.clona(scelte.get("repo", ""), radice)
        if "errore" in esito:
            return esito
        passi.append("Second brain scaricato da GitHub")
    else:
        return {"errore": "Scelta non valida"}

    claude = percorsi.trova_claude()
    nome = str(risposte.get("nome") or "").strip()[:40]
    percorsi.scrivi_config({**percorsi.leggi_config(), "radice": str(radice), "configurato": True,
                            **({"claude": str(claude)} if claude else {}), **({"nome": nome} if nome else {})})
    if scelte.get("claude_md", True):
        try:
            modello.collega_claude_md(radice)
            passi.append("Claude Code legge regole e indice in ogni chat")
        except OSError as e:
            passi.append(f"CLAUDE.md non aggiornato: {e}")
    if scelte.get("hook", True):
        try:
            r = modello.collega_hook(cartella_hook_app, percorsi.CACHE / "hooks")
            passi.append(r.get("errore") or "Appunti aggiornati da soli a fine chat")
        except OSError as e:
            passi.append(f"Hook non collegati: {e}")
    prompt = modello.prompt_iniziale(risposte) if modo != "github" else None
    return {"ok": True, "radice": str(radice), "passi": passi, "prompt": prompt}


def annulla() -> dict:
    # "Rifai il primo avvio" annullato: si torna al second brain di prima
    cfg = percorsi.leggi_config()
    p = cfg.get("radice_precedente")
    if not p or not Path(p).is_dir():
        return {"errore": "Non c'è un second brain precedente"}
    cfg.update(radice=p, configurato=True)
    cfg.pop("radice_precedente", None)
    percorsi.scrivi_config(cfg)
    return {"ok": True, "radice": p}
