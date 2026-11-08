# Terminali incorporati: ogni scheda dell'app e' un processo (claude.exe) in una
# pseudo-console (ConPTY via pywinpty su Windows; su Mac andra' `ptyprocess`).
# Il browser (xterm.js) parla con il processo tramite un websocket locale:
#   client -> server: {"t":"i","d":testo} input, {"t":"r","cols":n,"rows":n} resize
#   server -> client: testo grezzo dell'output; alla fine {"t":"x","code":n} e chiusura.
# Server su 127.0.0.1, porta casuale, token casuale: nessun altro processo puo' collegarsi.
import asyncio
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

PREFISSI_DA_TOGLIERE = ("CLAUDECODE", "CLAUDE_CODE_")
PREFISSI_ACCOUNT = ("ANTHROPIC_", "CLAUDE_CODE_", "AWS_", "CLOUD_ML_", "VERTEX_", "GOOGLE_")


def variabili_utente() -> dict:
    # variabili d'ambiente salvate in Windows (utente e sistema), lette ogni volta dal
    # registro: una chiave API impostata dopo l'avvio dell'app vale subito, senza riavviarla
    if os.name != "nt":
        return {}
    import winreg
    trovate = {}
    for radice, percorso in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                             (winreg.HKEY_CURRENT_USER, "Environment")):  # l'utente vince sul sistema
        try:
            with winreg.OpenKey(radice, percorso) as k:
                i = 0
                while True:
                    try:
                        nome, valore, tipo = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    i += 1
                    if isinstance(valore, str) and nome.upper().startswith(PREFISSI_ACCOUNT):
                        trovate[nome] = os.path.expandvars(valore) if tipo == winreg.REG_EXPAND_SZ else valore
        except OSError:
            pass
    return trovate


def ambiente_pulito(base: dict | None = None, utente: dict | None = None) -> dict:
    # niente variabili di una sessione Claude genitore (Claude spegnerebbe le trascrizioni),
    # ma si tengono quelle che l'utente ha salvato in Windows per l'account: chiave API,
    # Bedrock/Vertex (CLAUDE_CODE_USE_*), token, ecc.
    utente = variabili_utente() if utente is None else utente
    env = {k: v for k, v in (base if base is not None else os.environ).items()
           if not k.startswith(PREFISSI_DA_TOGLIERE)}
    env.update(utente)
    # FORCE_COLOR: dentro l'exe (senza console propria) Claude non rileva i colori da solo
    env.update(TERM="xterm-256color", COLORTERM="truecolor", FORCE_COLOR="3")
    return env


def _crea_pty(argv: list[str], cwd: str, cols: int, rows: int, env: dict):
    from winpty import PtyProcess
    return PtyProcess.spawn(argv, cwd=cwd, dimensions=(rows, cols), env=env)


@dataclass
class Scheda:
    id: str
    argv: list[str]
    cwd: str
    titolo: str
    sessione: str | None = None
    pty: object = None
    codice: int | None = None
    aperta_il: float = field(default_factory=time.time)
    client: set = field(default_factory=set)
    storico: list = field(default_factory=list)  # output gia' emesso, per chi si ricollega
    dim_storico: int = 0
    uscita: threading.Event = field(default_factory=threading.Event)  # claude e' uscito


class Terminali:
    MAX_STORICO = 2_000_000

    def __init__(self, crea_pty: Callable = _crea_pty, alla_chiusura: Callable | None = None):
        self._crea_pty = crea_pty
        self._alla_chiusura = alla_chiusura  # (scheda) -> None, chiamata da un thread
        self.token = secrets.token_hex(16)
        self.porta: int | None = None
        self.schede: dict[str, Scheda] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._pronto = threading.Event()
        self._blocco = threading.Lock()

    # --- server websocket ---
    def avvia(self) -> None:
        threading.Thread(target=self._esegui, name="terminali", daemon=True).start()
        if not self._pronto.wait(10):
            raise RuntimeError("server dei terminali non avviato")

    def _esegui(self) -> None:
        from websockets.asyncio.server import serve

        async def main():
            self._loop = asyncio.get_running_loop()
            async with serve(self._gestisci, "127.0.0.1", 0, max_size=2**22) as server:
                self.porta = server.sockets[0].getsockname()[1]
                self._pronto.set()
                await asyncio.Future()
        asyncio.run(main())

    def url(self, sid: str) -> str:
        return f"ws://127.0.0.1:{self.porta}/pty/{sid}?t={self.token}"

    async def _gestisci(self, ws):
        percorso = ws.request.path
        sid, _, query = percorso.removeprefix("/pty/").partition("?t=")
        scheda = self.schede.get(sid)
        if not secrets.compare_digest(query, self.token) or scheda is None:
            await ws.close(4403, "negato")
            return
        scheda.client.add(ws)
        try:
            for pezzo in list(scheda.storico):
                await ws.send(pezzo)
            if scheda.codice is not None:
                await ws.send(json.dumps({"t": "x", "code": scheda.codice}))
            async for messaggio in ws:
                self._comando(scheda, messaggio)
        except Exception:
            pass
        finally:
            scheda.client.discard(ws)

    def _comando(self, scheda: Scheda, messaggio) -> None:
        try:
            m = json.loads(messaggio)
        except (ValueError, TypeError):
            return
        pty = scheda.pty
        if pty is None or scheda.codice is not None:
            return
        try:
            if m.get("t") == "i" and isinstance(m.get("d"), str):
                pty.write(m["d"])
            elif m.get("t") == "r":
                cols, rows = int(m["cols"]), int(m["rows"])
                if 2 <= cols <= 1000 and 2 <= rows <= 500:
                    pty.setwinsize(rows, cols)
        except Exception:
            pass

    # --- schede ---
    def apri(self, argv: list[str], cwd: str, titolo: str, sessione: str | None = None,
             cols: int = 120, rows: int = 32) -> Scheda:
        sid = secrets.token_hex(6)
        scheda = Scheda(sid, argv, cwd, titolo, sessione)
        scheda.pty = self._crea_pty(argv, cwd, cols, rows, ambiente_pulito())
        with self._blocco:
            self.schede[sid] = scheda
        threading.Thread(target=self._leggi, args=(scheda,), name=f"pty-{sid}", daemon=True).start()
        return scheda

    def _leggi(self, scheda: Scheda) -> None:
        pty = scheda.pty
        while True:
            try:
                dati = pty.read(65536)
            except EOFError:
                break
            except Exception:
                break
            if dati:
                self._diffondi(scheda, dati)
            elif not pty.isalive():
                break
        try:
            codice = pty.exitstatus if pty.exitstatus is not None else pty.wait()
        except Exception:
            codice = -1
        scheda.codice = codice if isinstance(codice, int) else -1
        scheda.uscita.set()
        self._diffondi(scheda, json.dumps({"t": "x", "code": scheda.codice}), storico=False)
        if self._alla_chiusura:
            try:
                self._alla_chiusura(scheda)
            except Exception:
                pass

    def _diffondi(self, scheda: Scheda, dati: str, storico: bool = True) -> None:
        if storico:
            scheda.storico.append(dati)
            scheda.dim_storico += len(dati)
            while scheda.dim_storico > self.MAX_STORICO and len(scheda.storico) > 1:
                scheda.dim_storico -= len(scheda.storico.pop(0))
        if self._loop is None:
            return
        for ws in list(scheda.client):
            asyncio.run_coroutine_threadsafe(self._invia(ws, dati), self._loop)

    @staticmethod
    async def _invia(ws, dati):
        try:
            await ws.send(dati)
        except Exception:
            pass

    # Chiusura di una scheda (la X) o dell'app: claude va fatto uscire da solo, perche' solo
    # cosi' parte lo hook SessionEnd che salva gli appunti; con terminate(force=True) non
    # partirebbe mai. Si premono i tasti che premerebbe una persona: Esc (ferma una risposta
    # in corso o un menu), poi Ctrl+C due volte (esce). Se dopo USCITA_DOLCE secondi claude e'
    # ancora vivo, si chiude a forza.
    USCITA_DOLCE = 15.0
    SEQUENZA_USCITA = (("\x1b", 0.6), ("\x03", 0.25), ("\x03", 2.0))  # (tasto, attesa dopo)

    def chiudi(self, sid: str) -> threading.Thread | None:
        scheda = self.schede.pop(sid, None)
        if not scheda or scheda.pty is None or scheda.codice is not None:
            return None
        t = threading.Thread(target=self._chiudi_dolce, args=(scheda,), name=f"chiudi-{sid}", daemon=True)
        t.start()
        return t

    def _chiudi_dolce(self, scheda: Scheda) -> None:
        fine = time.monotonic() + self.USCITA_DOLCE
        while not scheda.uscita.is_set() and time.monotonic() < fine:
            for tasto, attesa in self.SEQUENZA_USCITA:
                try:
                    scheda.pty.write(tasto)
                except Exception:
                    # pty non scrivibile (di solito claude sta gia' uscendo): breve attesa e basta
                    scheda.uscita.wait(1.0)
                    fine = 0
                    break
                if scheda.uscita.wait(min(attesa, max(0.0, fine - time.monotonic()))):
                    return
        if not scheda.uscita.is_set():
            try:
                scheda.pty.terminate(force=True)
            except Exception:
                pass

    def attive(self) -> list[Scheda]:
        return [s for s in self.schede.values() if s.codice is None]

    def chiudi_tutte(self) -> None:
        # in parallelo, e si aspetta la fine di tutte (all'uscita dall'app)
        fili = [self.chiudi(sid) for sid in list(self.schede)]
        for t in fili:
            if t:
                t.join(self.USCITA_DOLCE + 2)
