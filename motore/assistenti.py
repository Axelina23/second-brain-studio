# Chat degli altri assistenti da riga di comando (Codex di OpenAI, Antigravity di Google):
# dove salvano i trascritti, come si leggono e come si collegano i loro hook.
# - Codex: ~/.codex/sessions/AAAA/MM/GG/rollout-<data>-<id>.jsonl (i vecchi sono .jsonl.zst);
#   la prima riga (session_meta) dice id e cartella di lavoro.
# - Antigravity: ~/.gemini/antigravity-cli/brain/<id>/.system_generated/logs/transcript.jsonl;
#   la cartella di lavoro sta in conversation_summaries.db (o in history.jsonl).
# Si elencano solo le chat nate nella cartella del second brain, come per Claude Code.
# Il risultato e' la stessa Sessione di sessioni.py, con il campo "assistente".
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from sessioni import MAX_COMPLETO, MAX_TESTO, Sessione, _data

NOMI = {"claude": "Claude", "codex": "Codex", "agy": "Antigravity"}
STRUMENTI = {"claude": "Claude Code", "codex": "Codex", "agy": "Antigravity"}
MODELLI = {
    "claude": ("predefinito", "fable", "opus", "sonnet", "haiku"),
    "codex": ("predefinito", "gpt-5.6-luna", "gpt-6-luna", "gpt-5.6-terra", "gpt-6.1-terra",
              "gpt-5.6-sol", "gpt-6-sol", "gpt-6.1-sol", "gpt-6-astra"),
    "agy": ("predefinito", "gemini-4-argon-high", "gemini-4-argon-medium", "gemini-4-argon-low",
            "gemini-3.8-flash-high", "gemini-3.8-flash-low"),
}
RE_ID = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE)
RE_BLOCCO = re.compile(r"^<([A-Za-z_]+)[\s>]")
RE_RICHIESTA = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.DOTALL)


def cartella_codex() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def cartella_agy() -> Path:
    return Path.home() / ".gemini" / "antigravity-cli"


def stessa_cartella(a, b) -> bool:
    if not a or not b:
        return False
    def norma(p):
        return os.path.normcase(os.path.normpath(str(p))).rstrip("\\/")
    return norma(a) == norma(b)


def _apri(p: Path):
    # i trascritti vecchi di Codex sono compressi (zstd, nella libreria standard da Python 3.14)
    if p.suffix == ".zst":
        from compression import zstd
        return zstd.open(p, "rt", encoding="utf-8", errors="replace")
    return open(p, encoding="utf-8", errors="replace")


def _righe(p: Path):
    with _apri(p) as f:
        for riga in f:
            try:
                r = json.loads(riga)
            except ValueError:
                continue
            if isinstance(r, dict):
                yield r


# ---------- Codex ----------
def meta_codex(p: Path) -> dict:
    # prima riga del trascritto: id, cartella di lavoro e origine della sessione
    try:
        for r in _righe(p):
            carico = r.get("payload") if isinstance(r.get("payload"), dict) else {}
            if r.get("type") == "session_meta":
                return carico
            break
    except (OSError, EOFError, ImportError):
        pass
    return {}


def _di_sistema(testo: str) -> bool:
    # blocchi che Codex mette tra i messaggi dell'utente: <environment_context>...</environment_context>
    m = RE_BLOCCO.match(testo)
    return bool(m) and testo.rstrip().endswith(f"</{m.group(1)}>")


def turni_codex(p: Path):
    for r in _righe(p):
        carico = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        if r.get("type") != "response_item" or carico.get("type") != "message":
            continue
        ruolo = carico.get("role")
        if ruolo not in ("user", "assistant"):
            continue
        parti = carico.get("content") if isinstance(carico.get("content"), list) else []
        testo = "\n".join(x.get("text", "") for x in parti if isinstance(x, dict)
                          and x.get("type") in ("input_text", "output_text", "text")).strip()
        if testo and not (ruolo == "user" and _di_sistema(testo)):
            yield ("utente" if ruolo == "user" else "assistente"), testo, _data(r.get("timestamp"))


def file_codex(base: Path | None = None) -> list[Path]:
    cartella = (base or cartella_codex()) / "sessions"
    if not cartella.is_dir():
        return []
    return [p for p in cartella.rglob("rollout-*") if p.name.endswith((".jsonl", ".jsonl.zst"))]


def uso_codex(base: Path | None = None) -> dict | None:
    # ultimo stato dei limiti (5 ore e 7 giorni) scritto da Codex nei file di sessione
    files = file_codex(base)
    if not files:
        return None
    try:
        recenti = sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    except OSError:
        return None
    for p in recenti:
        ultimo, ts = None, None
        try:
            for r in _righe(p):
                if r.get("type") != "event_msg":
                    continue
                carico = r.get("payload") or {}
                rl = carico.get("rate_limits") if carico.get("type") == "token_count" else None
                if isinstance(rl, dict) and (rl.get("primary") or rl.get("secondary")):
                    ultimo, ts = rl, _data(r.get("timestamp"))
            if ultimo:
                agg = int(ts.timestamp()) if ts else int(p.stat().st_mtime)
                out: dict = {"aggiornato": agg}
                for k_da, k_a in (("primary", "five_hour"), ("secondary", "seven_day")):
                    w = ultimo.get(k_da)
                    if isinstance(w, dict) and w.get("used_percent") is not None:
                        out[k_a] = {"used_percentage": w["used_percent"], "resets_at": w.get("resets_at")}
                if "five_hour" in out or "seven_day" in out:
                    return out
        except (OSError, EOFError, ImportError):
            continue
    return None


# ---------- Antigravity ----------
def turni_agy(p: Path):
    for r in _righe(p):
        testo = r.get("content")
        if not isinstance(testo, str) or not testo.strip():
            continue
        quando = _data(r.get("created_at"))
        if r.get("type") == "USER_INPUT":
            m = RE_RICHIESTA.search(testo)
            testo = (m.group(1) if m else testo).strip()
            if testo:
                yield "utente", testo, quando
        elif r.get("type") == "PLANNER_RESPONSE":
            yield "assistente", testo.strip(), quando


def file_agy(base: Path | None = None) -> list[Path]:
    cartella = (base or cartella_agy()) / "brain"
    if not cartella.is_dir():
        return []
    return [p for d in cartella.iterdir() if d.is_dir()
            for p in [d / ".system_generated" / "logs" / "transcript.jsonl"] if p.is_file()]


def id_agy(p: Path) -> str:
    return p.parents[2].name


def _percorso_da_uri(uri: str) -> str:
    u = urlparse(uri)
    percorso = unquote(u.path)
    return percorso.lstrip("/") if re.match(r"^/[A-Za-z]:", percorso) else percorso


def cartelle_agy(base: Path | None = None) -> dict[str, str]:
    # id della conversazione -> cartella di lavoro; le conversazioni dei sotto-agenti restano fuori
    base = base or cartella_agy()
    trovate: dict[str, str] = {}
    try:
        for riga in open(base / "history.jsonl", encoding="utf-8", errors="replace"):
            try:
                r = json.loads(riga)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get("conversationId") and r.get("workspace"):
                trovate[r["conversationId"]] = r["workspace"]
    except OSError:
        pass
    db = base / "conversation_summaries.db"
    if db.is_file():
        try:
            c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True, timeout=1)
            try:
                for cid, uri, genitore in c.execute(
                        "select conversation_id, workspace_uris, parent_conversation_id from conversation_summaries"):
                    if genitore:
                        trovate.pop(cid, None)
                        trovate[cid] = ""
                        continue
                    try:
                        elenco = json.loads(uri or "[]")
                    except ValueError:
                        elenco = []
                    if elenco and isinstance(elenco[0], str):
                        trovate[cid] = _percorso_da_uri(elenco[0])
            finally:
                c.close()
        except sqlite3.Error:
            pass
    return trovate


# ---------- lettura comune ----------
PROMPT_WORKER = ("Sei il passaggio automatico che aggiorna gli appunti",
                 "You are the automatic step that updates the notes")


def turni(percorso: Path, assistente: str):
    return turni_codex(percorso) if assistente == "codex" else turni_agy(percorso)


def leggi(percorso: Path, assistente: str, sid: str, completo: bool = False) -> Sessione | None:
    messaggi, tutto, dim_tutto, ultima = [], [], 0, None
    try:
        for chi, testo, quando in turni(percorso, assistente):
            ultima = quando or ultima
            if chi == "utente":
                messaggi.append(testo)
            if completo and dim_tutto < MAX_COMPLETO:
                tutto.append(testo)
                dim_tutto += len(testo)
    except (EOFError, ImportError):
        pass  # file troncato, o Python senza zstd: si tiene quello che si e' letto
    # fuori le sessioni del worker degli appunti (girano nella cartella del second brain)
    if not messaggi or messaggi[0].startswith(PROMPT_WORKER):
        return None
    st = percorso.stat()
    if ultima is None:
        ultima = datetime.fromtimestamp(st.st_mtime).astimezone()
    return Sessione(sid, percorso, ultima, st.st_size, messaggi[0], "\n".join(messaggi)[-MAX_TESTO:], len(messaggi),
                    "\n".join(tutto)[:MAX_COMPLETO].lower() if completo else "", assistente=assistente)


def testo_per_appunti(percorso: Path, assistente: str, massimo: int = 150_000) -> str:
    # stesso riassunto che il worker di fine sessione ricava dai trascritti di Claude
    nome = NOMI[assistente].upper()
    righe = [("UTENTE: " + t[:2000]) if chi == "utente" else (f"{nome}: " + t[:1500])
             for chi, t, _ in turni(percorso, assistente)]
    testo = "\n\n".join(righe)
    return testo if len(testo) <= massimo else "[...inizio tagliato...]\n" + testo[-massimo:]


def ultima_risposta(percorso, assistente: str, massimo: int = 180) -> str:
    try:
        ultimo = ""
        for chi, t, _ in turni(Path(percorso), assistente):
            if chi == "assistente":
                ultimo = t
    except (OSError, EOFError, ImportError):
        return ""
    ultimo = " ".join(ultimo.replace("*", "").replace("`", "").split())
    return ultimo if len(ultimo) <= massimo else ultimo[:massimo - 1].rsplit(" ", 1)[0] + "…"


# ---------- comando da avviare ----------
def _percorsi_comandi() -> str:
    percorsi = []
    if sys.platform == "win32":
        import winreg
        for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                          (winreg.HKEY_CURRENT_USER, r"Environment")):
            try:
                with winreg.OpenKey(hive, key) as registro:
                    percorsi.append(os.path.expandvars(winreg.QueryValueEx(registro, "Path")[0]))
            except OSError:
                pass
    percorsi.append(os.environ.get("PATH", ""))
    locali = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    roaming = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    noti = [Path.home() / ".local" / "bin", Path.home() / ".cargo" / "bin"]
    if sys.platform == "win32":
        noti += [locali / "Programs" / "OpenAI" / "Codex" / "bin", roaming / "npm",
                 locali / "Microsoft" / "WinGet" / "Links", locali / "Programs" / "nodejs",
                 Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs"]
    else:
        noti += [Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
    percorsi.extend(str(p) for p in noti if p.is_dir())
    return os.pathsep.join(p for p in percorsi if p)


def comando(nome: str) -> list[str] | None:
    # eseguibile nel PATH. Codex installato con npm e' un .cmd: lo si avvia con node sul suo
    # script, cosi' il testo del prompt non passa da cmd.exe (che interpreta & | % e virgolette)
    percorsi = _percorsi_comandi()
    trovato = shutil.which(nome, path=percorsi)
    if not trovato:
        return None
    if trovato.lower().endswith((".cmd", ".bat")):
        script = Path(trovato).parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        node = shutil.which("node", path=percorsi)
        if nome == "codex" and node and script.is_file():
            return [node, str(script)]
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", trovato]
    return [trovato]


def passa_da_cmd(argv: list[str]) -> bool:
    return len(argv) > 1 and argv[1] == "/c"


def argomenti(nome: str, sessione: str | None = None, prompt: str | None = None,
              modello: str | None = None) -> list[str]:
    # nuova chat, ripresa di una chat, modello e primo messaggio, per ciascun assistente
    valido = modello if not sessione and modello in MODELLI.get(nome, ()) and modello != "predefinito" else None
    if nome == "codex":
        return (["-m", valido] if valido else []) + (["resume", sessione] if sessione else []) + ([prompt] if prompt else [])
    return (["--model", valido] if valido else []) + (["--conversation", sessione] if sessione else []) + (["-i", prompt] if prompt else [])
