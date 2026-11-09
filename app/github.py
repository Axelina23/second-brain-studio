# GitHub dentro l'app: accesso con il flusso per dispositivi (codice da inserire su
# github.com, nessuna password nell'app), chiave d'accesso nel Gestione credenziali di
# Windows (keyring), creazione del repository privato e sincronizzazione del second brain
# (scarica, salva, carica) senza passare da Claude. Solo libreria standard + keyring.
# La chiave non finisce mai in .git/config: git la riceve come intestazione per comando.
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

_MOTORE = Path(__file__).resolve().parent.parent / "motore"
if str(_MOTORE) not in sys.path:
    sys.path.insert(0, str(_MOTORE))
from sync import ambiente_git  # noqa: E402

CLIENT_ID = "Ov23liTjKOrmefw98sGV"  # OAuth App "Second Brain Desktop" (pubblico per natura)
SERVIZIO = "second-brain-github"
API = "https://api.github.com"
_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _richiesta(url: str, dati: dict | None = None, token: str | None = None, metodo: str | None = None) -> dict:
    corpo = json.dumps(dati).encode() if dati is not None and url.startswith(API) else (
        urllib.parse.urlencode(dati).encode() if dati is not None else None)
    req = urllib.request.Request(url, data=corpo, method=metodo or ("POST" if corpo else "GET"))
    req.add_header("Accept", "application/json" if not url.startswith(API) else "application/vnd.github+json")
    req.add_header("User-Agent", "second-brain-studio")
    if url.startswith(API) and corpo:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as r:
        testo = r.read().decode("utf-8") or "{}"
    return json.loads(testo)


class GitHub:
    def __init__(self, radice: Path, emetti=lambda n, d: None, log=lambda: None, chiave=None, nota=lambda t: None):
        self.radice = Path(radice)
        self.emetti = emetti
        self._log = log
        self._nota = nota  # riga di testo nel registro degli errori
        self._chiave = chiave  # per i test: oggetto con get/set/delete al posto di keyring
        self._utente: str | None = None
        self._accesso: dict | None = None
        self._blocco = threading.Lock()
        self.in_corso = False
        self.ultima: dict | None = None
        self.scaduto = False  # GitHub ha rifiutato la chiave (revocata o scaduta): va ricollegato

    # ---------- chiave d'accesso ----------
    def _token(self) -> str | None:
        try:
            if self._chiave:
                return self._chiave.get()
            import keyring
            return keyring.get_password(SERVIZIO, "token")
        except Exception:
            return None

    def _salva_token(self, token: str | None) -> None:
        if self._chiave:
            self._chiave.set(token)
            return
        import keyring
        if token:
            keyring.set_password(SERVIZIO, "token", token)
        else:
            try:
                keyring.delete_password(SERVIZIO, "token")
            except Exception:
                pass

    def rifiutato(self, dove: str = "", errore: Exception | str | None = None) -> bool:
        # una chiamata ha avuto 401. La chiave si toglie solo se GitHub la rifiuta di nuovo
        # su /user: un 401 isolato (o arrivato con una chiave vecchia mentre se ne salvava una
        # nuova) non deve costringere a ricollegare. True = chiave tolta, va ricollegato.
        token = self._token()
        if token is None:
            return False
        try:
            _richiesta(f"{API}/user", token=token)
            confermato, verifica = False, "chiave valida su /user: tenuta"
        except urllib.error.HTTPError as e:
            confermato, verifica = e.code == 401, f"/user risponde {_dettagli(e)}"
        except Exception as e:
            confermato, verifica = False, f"/user non raggiungibile ({type(e).__name__}): chiave tenuta"
        self._nota(f"GitHub 401 in {dove or '?'}: {_dettagli(errore)} | verifica: {verifica}")
        if not confermato:
            return False
        self._salva_token(None)
        self._utente, self.scaduto = None, True
        self.emetti("github", {"esito": "accesso_scaduto", **self.stato()})
        return True

    # ---------- git ----------
    def _git(self, *args, timeout=60, autenticato=False) -> subprocess.CompletedProcess:
        # la chiave passa a git dall'ambiente del solo processo git (GIT_CONFIG_*), mai
        # dalla riga di comando, che altri programmi del PC potrebbero leggere
        env = ambiente_git(self._token() if autenticato else None)
        return subprocess.run(["git", *args], cwd=self.radice, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout, creationflags=_FLAGS, env=env)

    def repo(self) -> str | None:
        # "proprietario/nome" dal remote origin, se punta a GitHub
        try:
            r = self._git("remote", "get-url", "origin", timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        url = r.stdout.strip()
        if r.returncode != 0 or "github.com" not in url:
            return None
        coda = url.split("github.com", 1)[1].lstrip(":/")
        return coda[:-4] if coda.endswith(".git") else coda

    # ---------- stato ----------
    def stato(self) -> dict:
        token = self._token()
        if token and not self._utente:
            try:
                self._utente = _richiesta(f"{API}/user", token=token).get("login")
            except urllib.error.HTTPError as e:
                self._utente = None
                if e.code == 401 and self.rifiutato("stato", e):
                    token = None
            except Exception:
                self._utente = None
        return {"collegato": bool(token), "scaduto": self.scaduto, "utente": self._utente, "repo": self.repo(),
                "in_corso": self.in_corso, "ultima": self.ultima,
                "accesso": {k: v for k, v in (self._accesso or {}).items() if k != "device_code"} or None}

    # ---------- accesso con codice ----------
    def avvia_accesso(self) -> dict:
        try:
            r = _richiesta("https://github.com/login/device/code", {"client_id": CLIENT_ID, "scope": "repo"})
        except Exception as e:
            return {"errore": f"GitHub non risponde: {e}"}
        if "user_code" not in r:
            return {"errore": r.get("error_description") or "Risposta inattesa da GitHub"}
        self._accesso = {"codice": r["user_code"], "url": r["verification_uri"], "device_code": r["device_code"],
                         "scade": time.time() + int(r.get("expires_in", 900))}
        threading.Thread(target=self._attendi_accesso, args=(r["device_code"], int(r.get("interval", 5))),
                         name="github-accesso", daemon=True).start()
        return {"codice": r["user_code"], "url": r["verification_uri"]}

    def _attendi_accesso(self, device_code: str, intervallo: int) -> None:
        while self._accesso and self._accesso.get("device_code") == device_code and time.time() < self._accesso["scade"]:
            time.sleep(intervallo)
            try:
                r = _richiesta("https://github.com/login/oauth/access_token", {
                    "client_id": CLIENT_ID, "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
            except Exception:
                continue
            errore = r.get("error")
            if errore == "slow_down":
                intervallo += 5
            elif errore in ("expired_token", "access_denied"):
                self._accesso = None
                self.emetti("github", {"esito": "negato" if errore == "access_denied" else "scaduto"})
                return
            elif r.get("access_token"):
                self._salva_token(r["access_token"])
                self._accesso, self._utente, self.scaduto = None, None, False
                self.emetti("github", {"esito": "collegato", **self.stato()})
                return
        if self._accesso and self._accesso.get("device_code") == device_code:
            self._accesso = None
            self.emetti("github", {"esito": "scaduto"})

    def annulla_accesso(self) -> dict:
        self._accesso = None
        return {"ok": True}

    def scollega(self) -> dict:
        self._salva_token(None)
        self._utente = None
        return {"ok": True}

    # ---------- repository ----------
    def crea_repo(self, nome: str = "second-brain") -> dict:
        token = self._token()
        if not token:
            return {"errore": "Prima collega GitHub"}
        if self.repo():
            return {"errore": "Il second brain ha già un repository"}
        try:
            r = _richiesta(f"{API}/user/repos", {"name": nome, "private": True,
                           "description": "Il mio second brain (gestito con Second Brain Studio)"}, token=token)
        except urllib.error.HTTPError as e:
            return {"errore": "Esiste già un repository con quel nome" if e.code == 422 else f"GitHub ha risposto {e.code}"}
        except Exception as e:
            return {"errore": str(e)}
        url = r.get("clone_url")
        if not (self.radice / ".git").is_dir():
            self._git("init", "-b", "main")
        self._git("remote", "add", "origin", url)
        esito = self.sincronizza(primo=True)
        return {"ok": esito.get("ok", False), "repo": self.repo(), **({"errore": esito["errore"]} if "errore" in esito else {})}

    def repo_lista(self) -> dict:
        # i repository dell'utente, i piu' recenti prima (per "scarica il mio second brain")
        token = self._token()
        if not token:
            return {"errore": "Prima collega GitHub"}
        try:
            r = _richiesta(f"{API}/user/repos?per_page=100&sort=updated&affiliation=owner", token=token)
        except Exception as e:
            return {"errore": f"GitHub non risponde: {e}"}
        return {"repo": [{"nome": x.get("full_name"), "privato": x.get("private"), "url": x.get("clone_url"),
                          "aggiornato": x.get("pushed_at")} for x in (r if isinstance(r, list) else [])]}

    def clona(self, url: str, destinazione: Path) -> dict:
        if not isinstance(url, str) or not url.startswith("https://github.com/"):
            return {"errore": "Scegli un repository di GitHub"}
        destinazione = Path(destinazione)
        destinazione.parent.mkdir(parents=True, exist_ok=True)
        vecchia, self.radice = self.radice, destinazione.parent
        try:
            r = self._git("clone", url, str(destinazione), timeout=600, autenticato=True)
        except (OSError, subprocess.SubprocessError) as e:
            return {"errore": f"Scaricamento non riuscito: {e}"}
        finally:
            self.radice = vecchia
        if r.returncode != 0:
            return {"errore": f"Scaricamento non riuscito: {r.stderr.strip()[:200]}"}
        return {"ok": True}

    # ---------- sincronizzazione ----------
    def sincronizza(self, primo: bool = False) -> dict:
        if not self._blocco.acquire(blocking=False):
            return {"errore": "Sincronizzazione già in corso"}
        self.in_corso = True
        self.emetti("github", {"esito": "in_corso"})
        try:
            esito = self._sincronizza(primo)
        except Exception as e:
            self._log()
            esito = {"errore": str(e)}
        finally:
            self.in_corso = False
            self._blocco.release()
        self.ultima = {"quando": datetime.now().astimezone().isoformat(), **esito}
        self.emetti("github", {"esito": "fatto", **esito})
        return esito

    def _sincronizza(self, primo: bool) -> dict:
        if (self.radice / ".git" / "index.lock").exists():
            return {"errore": "Git è occupato (forse sta sincronizzando Claude): riprova tra poco"}
        if not self.repo():
            return {"errore": "Il second brain non ha ancora un repository su GitHub"}
        self._git("add", "-A")
        cambiati = self._git("status", "--porcelain").stdout.strip()
        salvati = 0
        if cambiati:
            salvati = len(cambiati.splitlines())
            host = os.environ.get("COMPUTERNAME", "pc")
            r = self._git("commit", "-m", f"app: {host} {datetime.now():%Y-%m-%d %H:%M}")
            if r.returncode != 0:
                return {"errore": f"Commit non riuscito: {r.stderr.strip()[:200]}"}
        ramo = self._git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
        if not primo:
            r = self._git("pull", "--rebase", "--autostash", "origin", ramo, timeout=120, autenticato=True)
            if r.returncode != 0:
                testo = (r.stdout + r.stderr).lower()
                if "conflict" in testo or "conflitto" in testo:
                    self._git("rebase", "--abort")
                    file = [l.split("Merge conflict in ")[-1] for l in (r.stdout + r.stderr).splitlines() if "Merge conflict in" in l]
                    return {"conflitto": True, "file": file,
                            "errore": "Lo stesso appunto è cambiato su due dispositivi: serve unirlo a mano"}
                if _accesso_rifiutato(testo):
                    return self._accesso_perso("git pull", r.stderr)
                if "couldn't find remote ref" not in testo:
                    return {"errore": f"Scaricamento non riuscito: {r.stderr.strip()[:200]}"}
        r = self._git("push", "-u", "origin", ramo, timeout=120, autenticato=True)
        if r.returncode != 0:
            if _accesso_rifiutato((r.stdout + r.stderr).lower()):
                return self._accesso_perso("git push", r.stderr)
            return {"errore": f"Caricamento non riuscito: {r.stderr.strip()[:200]}"}
        return {"ok": True, "salvati": salvati}

    def _accesso_perso(self, dove: str, testo: str) -> dict:
        # solo se la chiave c'era: senza chiave l'errore e' di git (credenziali del PC), non dell'app
        if self._token() is None:
            return {"errore": "GitHub ha rifiutato l'accesso: collega GitHub dall'app"}
        if not self.rifiutato(dove, testo.strip()):
            return {"errore": "GitHub ha rifiutato l'accesso per un momento: riprova tra poco"}
        return {"errore": "L'accesso a GitHub è scaduto: ricollega GitHub (i tuoi appunti sono salvi sul PC)", "scaduto": True}


def _dettagli(errore) -> str:
    # testo breve per il registro: codice, URL, id della richiesta e risposta di GitHub (mai la chiave)
    if isinstance(errore, urllib.error.HTTPError):
        try:
            corpo = " ".join(errore.read().decode("utf-8", "replace").split())[:200]
        except Exception:
            corpo = ""
        rid = errore.headers.get("X-GitHub-Request-Id", "") if errore.headers else ""
        return f"{errore.code} {errore.filename or ''} id={rid} {corpo}".strip()
    return " ".join(str(errore or "").split())[:300]


def _accesso_rifiutato(testo: str) -> bool:
    # messaggi di git quando GitHub non accetta la chiave
    return "invalid username or token" in testo or "authentication failed" in testo
