# Chiamata rapida a un assistente (predefinito: Haiku tramite `claude -p`).
# Se si passa assistente="codex" o "agy", usa Codex (`codex exec --ephemeral`) o
# Antigravity (`agy -p`) cosi' ogni IA fa il lavoro per se' senza consumare il piano
# di Claude. Se l'assistente richiesto non e' installato, ripiega su Claude.
# Gira in cwd CACHE con CLAUDE_NOTES_PASS=1 (niente note ne' sessioni nel second brain).
import os
import subprocess

import assistenti
from percorsi import CACHE, CLAUDE

MODELLI_BREVI = {
    "claude": "haiku",
    "codex": "gpt-6-luna",
    "agy": "gemini-3.8-flash-low",
}


def _comando_breve(assistente: str | None, modello: str | None, prompt: str = "") -> tuple[list[str], str | None]:
    nome = assistente if assistente in ("claude", "codex", "agy") else "claude"
    mod = modello if modello and modello != "predefinito" else MODELLI_BREVI[nome]
    if nome == "codex":
        mod = assistenti.ultimo_modello_codex(mod)
    if nome in ("codex", "agy"):
        base = assistenti.comando(nome)
        if base:
            if nome == "agy":
                return [*base, "--model", mod, "--disable-slash-commands", "-p", prompt], None
            return [*base, "exec", "--ephemeral", "--skip-git-repo-check", "-s", "read-only", "-m", mod, "-"], prompt
        mod = MODELLI_BREVI["claude"]
    return [str(CLAUDE), "-p", "--model", mod], prompt


def chiedi_haiku(prompt: str, timeout: float = 60, assistente: str | None = None,
                 modello: str | None = None) -> str | None:
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        cmd, stdin = _comando_breve(assistente, modello, prompt)
        r = subprocess.run(cmd, input=stdin,
                           cwd=CACHE, env={**os.environ, "CLAUDE_NOTES_PASS": "1"},
                           timeout=timeout, encoding="utf-8", errors="replace",
                           capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None
