# Chiamata a Haiku tramite `claude -p` (abbonamento). Restituisce None su
# errore, timeout o uscita diversa da 0. Gira in cwd CACHE con
# CLAUDE_NOTES_PASS=1 cosi' la chiamata non produce note ne' sessioni nel second brain.
import os
import subprocess

from percorsi import CACHE, CLAUDE


def chiedi_haiku(prompt: str, timeout: float = 60) -> str | None:
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([str(CLAUDE), "-p", "--model", "haiku"], input=prompt,
                           cwd=CACHE, env={**os.environ, "CLAUDE_NOTES_PASS": "1"},
                           timeout=timeout, encoding="utf-8", errors="replace",
                           capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None
