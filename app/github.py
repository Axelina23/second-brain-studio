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
        self._blocco_token = threading.RLock()
        self._riprova_rinnovo = 0.0
        self._rinnovo_negato = False

    # ---------- chiave d'accesso ----------
    def _credenziale(self) -> dict:
        try:
            if self._chiave:
                valore = self._chiave.get()
            else:
                import keyring
                valore = keyring.get_password(SERVIZIO, "token")
            if valore and valore.startswith("{"):
                dati = json.loads(valore)
                return dati if isinstance(dati, dict) else {}
            return {"access_token": valore} if valore else {}
        except Exception:
            return {}

    def _token(self) -> str | None:
        with self._blocco_token:
            dati = self._credenziale()
            if dati.get("refresh_token") and dati.get("expires_at", 0) <= time.time() + 120:
                self._rinnova(dati)
                dati = self._credenziale()
            return dati.get("access_token")

    def _salva_accesso(self, risposta: dict) -> None:
        # Una sola scrittura nel vault: accesso e rinnovo devono sopravvivere insieme al riavvio.
        dati = {"access_token": risposta["access_token"]}
        for campo in ("refresh_token", "scope"):
            if risposta.get(campo):
                dati[campo] = risposta[campo]
        if risposta.get("expires_in"):
            dati["expires_at"] = time.time() + int(risposta["expires_in"])
        with self._blocco_token:
            self._salva_token(json.dumps(dati))
            self._riprova_rinnovo = 0.0
            self._rinnovo_negato = False
            self.scaduto = False

    def _rinnova(self, dati: dict) -> bool:
        # Il lock impedisce a due thread di consumare lo stesso refresh token, che e' monouso.
        with self._blocco_token:
            if not dati.get("refresh_token") or time.time() < self._riprova_rinnovo:
                return False
            self._riprova_rinnovo = time.time() + 60
            try:
                r = _richiesta("https://github.com/login/oauth/access_token", {
                    "client_id": CLIENT_ID, "grant_type": "refresh_token", "refresh_token": dati["refresh_token"]})
                if not r.get("access_token"):
                    self._rinnovo_negato = r.get("error") == "bad_refresh_token"
                    self._nota("Rinnovo GitHub non riuscito: " + str(r.get("error", "risposta inattesa")))
                    return False
                self._salva_accesso(r)
                self._nota("Accesso GitHub rinnovato automaticamente")
                return True
            except Exception as e:
                self._nota(f"Rinnovo GitHub temporaneamente non disponibile ({type(e).__name__}): credenziali tenute")
                return False

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
        with self._blocco_token:
            dati = self._credenziale()
            if dati.get("access_token") != token or self._rinnova(dati):
                return False
            # Con un refresh disponibile si conserva tutto anche durante disservizi di rete.
            if dati.get("refresh_token") and not self._rinnovo_negato:
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
        if self._accesso and time.time() < self._accesso.get("scade", 0):
            return {"codice": self._accesso["codice"], "url": self._accesso["url"]}
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
                if not self._accesso or self._accesso.get("device_code") != device_code:
                    return
                self._salva_accesso(r)
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
        # un rebase o un merge lasciato a meta' (per esempio dallo hook di fine sessione) va
        # annullato prima del commit: altrimenti i segni del conflitto finiscono nel repo e
        # pull/push girano su un ramo staccato. Il pull qui sotto ritrova poi il conflitto vero.
        if not self._annulla_a_meta():
            return {"errore": "Una sincronizzazione precedente è rimasta a metà e non si riesce ad annullarla: serve sistemarla a mano"}
        self._git("add", "-A")
        cambiati = self._git("status", "--porcelain").stdout.strip()
        salvati = 0
        if cambiati:
            salvati = len(cambiati.splitlines())
            host = os.environ.get("COMPUTERNAME", "pc")
            r = self._git("commit", "-m", f"app: {host} {datetime.now():%Y-%m-%d %H:%M}")
            if r.returncode != 0:
                return {"errore": f"Commit non riuscito: {r.stderr.strip()[:200]}"}
        r = self._git("symbolic-ref", "--short", "-q", "HEAD")
        if r.returncode != 0:
            return {"errore": "Il second brain non è su nessun ramo (HEAD staccato): serve sistemarlo a mano"}
        ramo = r.stdout.strip() or "main"
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

    def _annulla_a_meta(self) -> bool:
        # True se non c'e' (piu') nessun rebase o merge a meta'
        cartella = self.radice / ".git"
        if (cartella / "rebase-merge").exists() or (cartella / "rebase-apply").exists():
            self._git("rebase", "--abort")
        if (cartella / "MERGE_HEAD").exists():
            self._git("merge", "--abort")
        return not any((cartella / n).exists() for n in ("rebase-merge", "rebase-apply", "MERGE_HEAD"))

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
