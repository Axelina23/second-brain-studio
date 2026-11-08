# Semaforo di sincronizzazione del repo delle note con GitHub.
# verde: allineato. giallo: GitHub non aggiornato (modifiche non committate,
# file nuovi o commit non pushati). rosso: il PC non e' aggiornato (commit
# remoti da scaricare); rosso vince sul giallo. grigio: stato ignoto (nessun
# upstream, non e' un repo, fetch fallito/offline, errore git). Non solleva mai.
import base64
import os
import subprocess
from pathlib import Path

_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def ambiente_git(token: str | None = None) -> dict:
    # ambiente per git senza domande. Con la chiave dell'app: la chiave va come intestazione
    # (solo nell'ambiente del processo, mai su riga di comando o in .git/config) e il gestore
    # credenziali di Windows e' spento, perche' in un processo senza finestre resta appeso
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    if token:
        b = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env.update(GIT_CONFIG_COUNT="2",
                   GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
                   GIT_CONFIG_VALUE_0=f"AUTHORIZATION: basic {b}",
                   GIT_CONFIG_KEY_1="credential.helper", GIT_CONFIG_VALUE_1="")
    return env


def _git(radice: Path, *args: str, timeout: float, token: str | None = None):
    return subprocess.run(["git", *args], cwd=radice, capture_output=True, text=True,
                          encoding="utf-8", timeout=timeout, env=ambiente_git(token),
                          creationflags=_FLAGS)


def stato_sync(radice: Path, fetch: bool = True, timeout: float = 10, token: str | None = None) -> str:
    try:
        radice = Path(radice)
        if fetch and _git(radice, "fetch", "--quiet", timeout=timeout, token=token).returncode != 0:
            return "grigio"
        conteggio = _git(radice, "rev-list", "--left-right", "--count", "HEAD...@{u}",
                         timeout=timeout)
        if conteggio.returncode != 0:
            return "grigio"
        avanti, indietro = (int(n) for n in conteggio.stdout.split())
        stato = _git(radice, "status", "--porcelain", timeout=timeout)
        if stato.returncode != 0:
            return "grigio"
        if indietro > 0:
            return "rosso"
        if avanti > 0 or stato.stdout.strip():
            return "giallo"
        return "verde"
    except Exception:
        return "grigio"
