# Chat degli altri PC, senza programmi esterni: ogni app pubblica il riepilogo delle sue chat
# (niente messaggi: parole chiave, orari, stato) nel repository GitHub del second brain, in un
# ramo tutto suo "stato/<PC>" fatto di UN SOLO commit, sovrascritto a ogni cambiamento.
# Il ramo main degli appunti non si tocca e la cronologia non cresce. Gli altri PC leggono
# l'elenco dei rami ogni 10 secondi con richieste condizionate (ETag: le risposte 304 non
# contano nei limiti di GitHub) e scaricano solo i riepiloghi cambiati.
# Usa la chiave GitHub dell'app (github.py). Solo libreria standard.
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
FORMATO = 1
PREFISSO = "stato/"
MAX_CHAT = 100
GIORNI = 30
BATTITO = 180          # secondi tra due battiti senza cambiamenti
VECCHIO = 10 * 60      # oltre: il PC e' "probabilmente spento"
NASCOSTO = 30 * 86400  # oltre: il PC non si mostra piu'


def nome_pc() -> str:
    # nome del computer, ripulito per stare in un nome di ramo e di file
    nome = os.environ.get("COMPUTERNAME") or (os.uname().nodename if hasattr(os, "uname") else "") or "PC"
    return re.sub(r"[^A-Za-z0-9_-]+", "-", nome).strip("-").upper()[:40] or "PC"


def riepilogo(chat: list, versione: str, adesso: float | None = None, uscita: bool = False) -> dict:
    # chat: voci come quelle della pagina Chat ({id, etichetta, ultima, stato, messaggi, dimensione, ...})
    adesso = adesso or time.time()
    limite = adesso - GIORNI * 86400
    voci = []
    for c in chat:
        try:
            quando = _epoch(c["ultima"])
        except (KeyError, ValueError, TypeError):
            continue
        if quando < limite:
            continue
        stato = c.get("stato")
        if uscita and stato == "aperta":
            stato = c.get("stato_salvataggio") or "non_salvata"
        voci.append({"id": str(c["id"]), "etichetta": str(c.get("etichetta") or "")[:120], "ultima": c["ultima"],
                     "stato": stato, "messaggi": int(c.get("messaggi") or 0), "dimensione": int(c.get("dimensione") or 0)})
    voci.sort(key=lambda v: v["ultima"], reverse=True)
    return {"formato": FORMATO, "pc": nome_pc(), "sistema": "mac" if sys.platform == "darwin" else "windows",
            "app": versione, "battito": int(adesso), "chat": voci[:MAX_CHAT]}


def _epoch(iso: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()


def senza_battito(r: dict) -> dict:
    return {k: v for k, v in r.items() if k != "battito"}


def valido(d) -> bool:
    return (isinstance(d, dict) and d.get("formato") == FORMATO and isinstance(d.get("pc"), str)
            and isinstance(d.get("battito"), (int, float)) and isinstance(d.get("chat"), list))


def per_interfaccia(remoti: dict, adesso: float | None = None) -> list:
    # elenco ordinato per l'interfaccia: prima i PC accesi, poi gli altri; via quelli muti da 30 giorni
    adesso = adesso or time.time()
    fuori = []
    for d in remoti.values():
        if not valido(d):
            continue
        eta = adesso - d["battito"]
        if eta > NASCOSTO:
            continue
        fuori.append({**d, "acceso": eta <= VECCHIO, "eta": max(0, int(eta))})
    return sorted(fuori, key=lambda d: (not d["acceso"], d["eta"]))


class _Risposta:
    def __init__(self, stato: int, dati, etag: str | None):
        self.stato, self.dati, self.etag = stato, dati, etag


class AltriPC:
    def __init__(self, token, repo, log=lambda: None, emetti=lambda n, d: None):
        # token(), repo(): funzioni (la chiave e il repository possono cambiare mentre l'app gira)
        self._token, self._repo, self._log, self.emetti = token, repo, log, emetti
        self.pc = nome_pc()
        self.remoti: dict[str, dict] = {}   # pc -> riepilogo
        self._sha: dict[str, str] = {}      # ramo -> sha del commit gia' letto
        self._etag: str | None = None
        self._pubblicato: dict | None = None
        self._ultimo_invio = 0.0
        self.errore: str | None = None

    # ---------- rete ----------
    def _chiedi(self, metodo: str, percorso: str, dati=None, etag: str | None = None, grezzo=False) -> _Risposta:
        token = self._token()
        if not token:
            raise PermissionError("GitHub non collegato")
        req = urllib.request.Request(API + percorso, method=metodo, data=json.dumps(dati).encode() if dati is not None else None)
        req.add_header("Accept", "application/vnd.github.raw+json" if grezzo else "application/vnd.github+json")
        req.add_header("User-Agent", "second-brain-studio")
        req.add_header("Authorization", f"Bearer {token}")
        if dati is not None:
            req.add_header("Content-Type", "application/json")
        if etag:
            req.add_header("If-None-Match", etag)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                corpo = r.read().decode("utf-8")
                return _Risposta(r.status, json.loads(corpo) if corpo else None, r.headers.get("ETag"))
        except urllib.error.HTTPError as e:
            if e.code == 304:
                return _Risposta(304, None, etag)
            raise

    def _base(self) -> str | None:
        repo = self._repo()
        return f"/repos/{repo}" if repo else None

    # ---------- scrittura ----------
    def pubblica(self, r: dict, forza: bool = False) -> bool:
        # un commit senza genitori con il solo file <PC>.json, ramo stato/<PC> spostato con forza
        base = self._base()
        if not base:
            return False
        adesso = time.time()
        if not forza and self._pubblicato == senza_battito(r) and adesso - self._ultimo_invio < BATTITO:
            return False
        testo = json.dumps(r, ensure_ascii=False, indent=1)
        albero = self._chiedi("POST", f"{base}/git/trees", {"tree": [
            {"path": f"{self.pc}.json", "mode": "100644", "type": "blob", "content": testo}]}).dati["sha"]
        commit = self._chiedi("POST", f"{base}/git/commits", {
            "message": f"stato: {self.pc}", "tree": albero, "parents": []}).dati["sha"]
        ref = f"heads/{PREFISSO}{self.pc}"
        try:
            self._chiedi("PATCH", f"{base}/git/refs/{urllib.parse.quote(ref)}", {"sha": commit, "force": True})
        except urllib.error.HTTPError as e:
            if e.code not in (404, 422):
                raise
            self._chiedi("POST", f"{base}/git/refs", {"ref": f"refs/{ref}", "sha": commit})
        self._pubblicato, self._ultimo_invio = senza_battito(r), adesso
        return True

    # ---------- lettura ----------
    def leggi(self) -> bool:
        # True se qualcosa e' cambiato
        base = self._base()
        if not base:
            return False
        r = self._chiedi("GET", f"{base}/git/matching-refs/heads/{PREFISSO}", etag=self._etag)
        if r.stato == 304:
            return False
        self._etag = r.etag
        cambiato = False
        visti = set()
        for ref in r.dati or []:
            nome = str(ref.get("ref", ""))[len(f"refs/heads/{PREFISSO}"):]
            sha = (ref.get("object") or {}).get("sha")
            if not nome or nome == self.pc or not sha:
                continue
            visti.add(nome)
            if self._sha.get(nome) == sha:
                continue
            try:
                f = self._chiedi("GET", f"{base}/contents/{urllib.parse.quote(nome)}.json?ref={urllib.parse.quote(sha)}", grezzo=True)
                dati = f.dati if isinstance(f.dati, dict) else None
            except (urllib.error.HTTPError, ValueError):
                dati = None
            if valido(dati):
                self.remoti[nome] = dati
            self._sha[nome] = sha
            cambiato = True
        for nome in list(self.remoti):
            if nome not in visti:
                self.remoti.pop(nome)
                self._sha.pop(nome, None)
                cambiato = True
        return cambiato

    def elenco(self) -> list:
        return per_interfaccia(self.remoti)
