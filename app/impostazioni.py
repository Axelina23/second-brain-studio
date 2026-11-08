# Impostazioni dell'app: stanno in ~/.claude/second-brain/config.json sotto "impostazioni"
# (gli hook le leggono da li', ad esempio per gli appunti automatici). Ogni valore viene
# controllato contro i predefiniti: tipo giusto e, per le scelte, uno dei valori ammessi.
# Qui anche le azioni di sistema delle Impostazioni: avvio con Windows, account Claude,
# esportazione, scorciatoia globale, "non disturbare" e gioco a schermo intero.
import json
import os
import subprocess
import sys
import threading
import zipfile
from datetime import datetime
from pathlib import Path

import percorsi


def lingua_di_windows() -> str:
    # lingua di partenza dell'app finche' non la si sceglie: italiano se Windows e' in
    # italiano, inglese in tutti gli altri casi
    try:
        import ctypes
        return "it" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x10 else "en"
    except (AttributeError, OSError):
        import locale
        return "it" if (locale.getlocale()[0] or "").lower().startswith("it") else "en"


PREDEFINITE = {
    # aspetto
    "lingua": lingua_di_windows(), "tema": "scuro", "colore": "limone", "testo": 100, "animazioni": True, "pagina_iniziale": "oggi",
    # notifiche
    "notifica_risposta": True, "notifica_permesso": True, "notifica_non_salvate": True, "notifica_scadenze": True,
    "notifica_inbox": True, "notifica_sync": True, "notifica_fuori_app": False, "anteprima": True,
    "silenzio_attivo": False, "silenzio_da": "23:00", "silenzio_a": "08:00", "silenzio_gioco": True,
    # terminale
    "terminale_testo": 13.5, "terminale_carattere": "JetBrains Mono", "modello_chat": "predefinito",
    # appunti automatici (letti dagli hook)
    "appunti_auto": True, "modello_appunti": "sonnet", "soglia_kb": 30,
    # GitHub
    "sync_minuti": 0,
    # scorciatoie
    "scorciatoia_globale": True,
    # aggiornamenti dalle release di GitHub; le versioni di prova (pre-release) solo a chi le chiede
    "aggiornamenti_auto": True, "aggiornamenti_prova": False,
    # chat degli altri PC (rami stato/<PC> del repository del second brain)
    "chat_altri_pc": True,
}
SCELTE = {
    "lingua": ("it", "en"), "tema": ("scuro", "chiaro", "sistema"),
    "colore": ("limone", "cobalto", "verderame", "terracotta", "viola", "rosa"),
    "pagina_iniziale": ("oggi", "chat", "appunti", "mappa", "inbox"),
    "modello_chat": ("predefinito", "opus", "sonnet", "haiku"), "modello_appunti": ("sonnet", "haiku", "opus"),
    "terminale_carattere": ("JetBrains Mono", "Cascadia Mono", "Consolas"),
}
LIMITI = {"testo": (85, 130), "terminale_testo": (10, 20), "soglia_kb": (5, 500), "sync_minuti": (0, 240)}
_ORA = __import__("re").compile(r"^([01]\d|2[0-3]):[0-5]\d$")
COLLEGAMENTO_AVVIO = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Second Brain Studio.lnk"
_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def leggi() -> dict:
    salvate = percorsi.leggi_config().get("impostazioni") or {}
    return {k: salvate.get(k, v) if _valido(k, salvate.get(k)) else v for k, v in PREDEFINITE.items()}


def _valido(k: str, v) -> bool:
    if v is None:
        return False
    base = PREDEFINITE[k]
    if isinstance(base, bool):
        return isinstance(v, bool)
    if isinstance(base, (int, float)):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return False
        lo, hi = LIMITI.get(k, (float("-inf"), float("inf")))
        return lo <= v <= hi
    if k in SCELTE:
        return v in SCELTE[k]
    if k in ("silenzio_da", "silenzio_a"):
        return isinstance(v, str) and bool(_ORA.match(v))
    return isinstance(v, str)


def salva(nuove: dict) -> dict:
    if not isinstance(nuove, dict):
        return {"errore": "Impostazioni non valide"}
    scartate = [k for k, v in nuove.items() if k not in PREDEFINITE or not _valido(k, v)]
    cfg = percorsi.leggi_config()
    imp = {**(cfg.get("impostazioni") or {}), **{k: v for k, v in nuove.items() if k not in scartate}}
    cfg["impostazioni"] = imp
    percorsi.scrivi_config(cfg)
    return {"ok": True, "impostazioni": leggi(), **({"scartate": scartate} if scartate else {})}


# ---------- avvio con Windows ----------
def avvio_attivo() -> bool:
    return COLLEGAMENTO_AVVIO.is_file()


def imposta_avvio(attivo: bool) -> dict:
    if not getattr(sys, "frozen", False):
        return {"errore": "L'avvio con Windows si imposta solo dall'app installata"}
    if not attivo:
        COLLEGAMENTO_AVVIO.unlink(missing_ok=True)
        return {"ok": True, "attivo": False}
    exe = sys.executable.replace("'", "''")
    lnk = str(COLLEGAMENTO_AVVIO).replace("'", "''")
    script = (f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}'); $s.TargetPath = '{exe}'; "
              f"$s.Arguments = '--nascosta'; $s.WorkingDirectory = '{Path(exe).parent}'; $s.Save()")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True,
                       timeout=20, creationflags=_FLAGS)
    if r.returncode != 0 or not avvio_attivo():
        return {"errore": "Non riesco a creare il collegamento di avvio"}
    return {"ok": True, "attivo": True}


# ---------- account Claude ----------
def account_claude() -> dict:
    # come Claude Code accede a Claude: abbonamento (account), chiave API o Bedrock/Vertex
    from terminale import variabili_utente
    amb = {**os.environ, **variabili_utente()}
    if amb.get("CLAUDE_CODE_USE_BEDROCK"):
        return {"tipo": "bedrock", "testo": "Amazon Bedrock"}
    if amb.get("CLAUDE_CODE_USE_VERTEX"):
        return {"tipo": "vertex", "testo": "Google Vertex AI"}
    if amb.get("ANTHROPIC_API_KEY") or amb.get("ANTHROPIC_AUTH_TOKEN"):
        return {"tipo": "chiave", "testo": "Chiave API di Anthropic"}
    try:
        d = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
        acc = d.get("oauthAccount") or {}
    except (OSError, ValueError):
        acc = {}
    if acc:
        return {"tipo": "abbonamento", "testo": "Abbonamento Claude", "email": acc.get("emailAddress"),
                "organizzazione": acc.get("organizationName")}
    return {"tipo": "nessuno", "testo": "Non collegato"}


# ---------- dati ----------
def esporta(radice: Path) -> dict:
    # copia .zip del second brain (senza la cartella .git) nei Download
    radice = Path(radice)
    dest = Path.home() / "Downloads" / f"Second Brain {datetime.now():%Y-%m-%d %H%M}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for p in radice.rglob("*"):
            rel = p.relative_to(radice)
            if p.is_file() and ".git" not in rel.parts and "node_modules" not in rel.parts:
                z.write(p, rel.as_posix())
                n += 1
    return {"ok": True, "file": str(dest), "conto": n}


def svuota_cache() -> dict:
    # parole chiave delle chat (si ricalcolano) e file dell'interfaccia: niente di personale
    tolti = 0
    for nome in ("parole.json",):
        f = percorsi.CACHE / nome
        if f.is_file():
            f.unlink()
            tolti += 1
    return {"ok": True, "tolti": tolti}


# ---------- silenzio ----------
def in_silenzio(imp: dict, adesso: datetime | None = None) -> bool:
    if imp.get("silenzio_gioco", True) and gioco_a_schermo_intero():
        return True
    if not imp.get("silenzio_attivo"):
        return False
    t = (adesso or datetime.now()).strftime("%H:%M")
    da, a = imp.get("silenzio_da", "23:00"), imp.get("silenzio_a", "08:00")
    return da <= t < a if da <= a else (t >= da or t < a)


def gioco_a_schermo_intero() -> bool:
    # Windows sa se c'e' un gioco o una presentazione a schermo intero (SHQueryUserNotificationState)
    if os.name != "nt":
        return False
    try:
        import ctypes
        stato = ctypes.c_int(0)
        if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(stato)) != 0:
            return False
        return stato.value in (2, 3, 4)  # occupato, gioco D3D a schermo intero, presentazione
    except Exception:
        return False


# ---------- scorciatoia globale (Ctrl+Alt+Spazio) ----------
class Scorciatoia:
    def __init__(self, azione):
        self.azione = azione
        self._thread_id = None

    def avvia(self) -> None:
        if os.name != "nt" or self._thread_id:
            return
        threading.Thread(target=self._ciclo, name="scorciatoia", daemon=True).start()

    def ferma(self) -> None:
        if self._thread_id:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
            self._thread_id = None

    def _ciclo(self) -> None:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        if not u.RegisterHotKey(None, 1, 0x0002 | 0x0001 | 0x4000, 0x20):  # Ctrl+Alt (no ripetizione) + Spazio
            self._thread_id = None
            return
        msg = wintypes.MSG()
        try:
            while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    try:
                        self.azione()
                    except Exception:
                        pass
        finally:
            u.UnregisterHotKey(None, 1)
