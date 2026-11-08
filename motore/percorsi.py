# Percorsi e soglie condivisi. La cartella del second brain non e' fissa: sta in
# ~/.claude/second-brain/config.json ("radice"), scritto dal primo avvio dell'app.
# Senza configurazione RADICE resta None e l'app mostra il primo avvio.
import json
import os
import re
import shutil
import sys
from pathlib import Path

CACHE = Path.home() / ".claude" / "second-brain"
CONFIG = CACHE / "config.json"
SEGNI = CACHE / "segni"
SOGLIA_SIGNIFICATIVA = 30 * 1024


def leggi_config() -> dict:
    try:
        d = json.loads(CONFIG.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def scrivi_config(dati: dict) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, CONFIG)


def radice_configurata() -> Path | None:
    cfg = leggi_config()
    if cfg.get("radice") and Path(cfg["radice"]).is_dir():
        return Path(cfg["radice"])
    return None


def cartella_sessioni(radice: Path) -> Path:
    # Claude Code salva le chat di una cartella in ~/.claude/projects/<percorso con - al posto
    # di ogni carattere non alfanumerico>, es. C:\Users\x\Mio Brain -> C--Users-x-Mio-Brain
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(radice))


def trova_claude() -> Path | None:
    for p in (Path.home() / ".local" / "bin" / "claude.exe", Path.home() / ".local" / "bin" / "claude"):
        if p.is_file():
            return p
    trovato = shutil.which("claude")
    return Path(trovato) if trovato else None


RADICE = radice_configurata()
CARTELLA_SESSIONI = cartella_sessioni(RADICE) if RADICE else CACHE / "nessuna-sessione"
CLAUDE = trova_claude() or Path.home() / ".local" / "bin" / "claude.exe"


def python_di_sistema() -> str:
    # l'interprete con cui lanciare gli script del second brain (cal.py...): quello corrente,
    # tranne dentro l'app impacchettata, dove sys.executable e' l'app stessa
    if not getattr(sys, "frozen", False):
        return sys.executable
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python"
    candidati = sorted(base.glob("Python3*/python.exe"), reverse=True) if base.is_dir() else []
    if candidati:
        return str(candidati[0])
    return shutil.which("py") or shutil.which("python") or "python"
