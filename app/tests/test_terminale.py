import asyncio
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import terminale  # noqa: E402


class PtyFinto:
    def __init__(self, *a, **k):
        self.uscite = ["ciao\r\n", "secondo\r\n"]
        self.scritto = []
        self.dimensioni = None
        self.vivo = True
        self.exitstatus = None
        self.evento = threading.Event()

    def read(self, n):
        if self.uscite:
            return self.uscite.pop(0)
        self.evento.wait(2)
        if not self.vivo:
            raise EOFError
        return ""

    def isalive(self):
        return self.vivo

    def write(self, d):
        self.scritto.append(d)
        if d == "esci":
            self.vivo = False
            self.exitstatus = 0
            self.evento.set()

    def setwinsize(self, r, c):
        self.dimensioni = (r, c)

    def terminate(self, force=False):
        self.vivo = False
        self.exitstatus = 1
        self.evento.set()

    def wait(self):
        return self.exitstatus


def test_codex_recupera_daemon_senza_perdere_resume_prompt_e_permessi():
    chiamate, chiuse = [], []
    errore = 'Error: failed to open daemon process: Accesso negato. Rerun with --no-daemon'
    class Finito(PtyFinto):
        def __init__(self, testo, codice):
            super().__init__()
            self.uscite, self.exitstatus = [testo], codice
        def read(self, n):
            if self.uscite:
                return self.uscite.pop()
            raise EOFError
    def crea(argv, cwd, cols, rows, env):
        chiamate.append(list(argv))
        return Finito(errore if len(chiamate) == 1 else 'Codex pronto', 1 if len(chiamate) == 1 else 0)
    t = terminale.Terminali(crea_pty=crea, alla_chiusura=chiuse.append)
    argv = ['codex.exe', 'resume', 'sessione', '--sandbox', 'workspace-write', 'continua']
    s = t.apri(argv, '.', 'Codex', assistente='codex')
    assert s.uscita.wait(2)
    assert chiamate == [argv, ['codex.exe', '--no-daemon', *argv[1:]]]
    assert s.codice == 0 and chiuse == [s]


def test_codex_non_riprova_errori_generici_o_daemon_gia_escluso():
    for argv, errore in ((['codex.exe'], 'Unknown model'),
                         (['codex.exe', '--no-daemon'], 'background server --no-daemon')):
        chiamate = []
        class Fallito(PtyFinto):
            def __init__(self):
                super().__init__()
                self.uscite, self.exitstatus = [errore], 1
            def read(self, n):
                if self.uscite:
                    return self.uscite.pop()
                raise EOFError
        def crea(*a):
            chiamate.append(a)
            return Fallito()
        t = terminale.Terminali(crea_pty=crea)
        s = t.apri(argv, '.', 'Codex', assistente='codex')
        assert s.uscita.wait(2) and len(chiamate) == 1 and s.codice == 1


def test_ambiente_pulito_toglie_variabili_claude():
    env = terminale.ambiente_pulito({"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli",
                                     "PATH": "x", "CLAUDE_NOTES_PASS": "1"}, utente={})
    assert "CLAUDECODE" not in env and "CLAUDE_CODE_ENTRYPOINT" not in env
    assert env["PATH"] == "x" and env["CLAUDE_NOTES_PASS"] == "1"
    assert env["TERM"] == "xterm-256color"


def test_ambiente_tiene_le_variabili_account_salvate_in_windows():
    env = terminale.ambiente_pulito({"CLAUDE_CODE_USE_BEDROCK": "1", "PATH": "x"},
                                    utente={"CLAUDE_CODE_USE_BEDROCK": "1", "ANTHROPIC_API_KEY": "chiave-finta"})
    assert env["CLAUDE_CODE_USE_BEDROCK"] == "1" and env["ANTHROPIC_API_KEY"] == "chiave-finta"


def test_variabili_utente_legge_il_registro():
    assert isinstance(terminale.variabili_utente(), dict)


def test_websocket_input_resize_storico_e_uscita():
    from websockets.asyncio.client import connect
    finti = []

    def crea(*a, **k):
        p = PtyFinto()
        finti.append(p)
        return p
    chiuse = []
    t = terminale.Terminali(crea_pty=crea, alla_chiusura=chiuse.append)
    t.avvia()
    s = t.apri(["claude"], ".", "prova")
    time.sleep(0.3)

    async def cliente():
        ricevuti = []
        async with connect(t.url(s.id)) as ws:
            ricevuti.append(await ws.recv())
            ricevuti.append(await ws.recv())
            await ws.send(json.dumps({"t": "r", "cols": 100, "rows": 30}))
            await ws.send(json.dumps({"t": "i", "d": "esci"}))
            ricevuti.append(await asyncio.wait_for(ws.recv(), 5))
        return ricevuti
    ricevuti = asyncio.run(cliente())
    assert ricevuti[:2] == ["ciao\r\n", "secondo\r\n"]
    assert json.loads(ricevuti[2]) == {"t": "x", "code": 0}
    assert finti[0].dimensioni == (30, 100)
    time.sleep(0.2)
    assert chiuse and chiuse[0].id == s.id


def test_token_sbagliato_rifiutato():
    from websockets.asyncio.client import connect
    from websockets.exceptions import ConnectionClosed
    t = terminale.Terminali(crea_pty=lambda *a, **k: PtyFinto())
    t.avvia()
    s = t.apri(["claude"], ".", "prova")

    async def cliente():
        async with connect(f"ws://127.0.0.1:{t.porta}/pty/{s.id}?t=sbagliato") as ws:
            try:
                await asyncio.wait_for(ws.recv(), 3)
            except ConnectionClosed as e:
                return e.rcvd.code if e.rcvd else None
    assert asyncio.run(cliente()) == 4403
    t.USCITA_DOLCE = 0.5
    t.chiudi_tutte()


class PtyCheEsceConCtrlC(PtyFinto):
    # come claude: Ctrl+C due volte di fila lo fa uscire da solo (e parte lo hook SessionEnd)
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.uscite = []
        self.forzato = False

    def write(self, d):
        self.scritto.append(d)
        if self.scritto[-2:] == ["\x03", "\x03"]:
            self.vivo = False
            self.exitstatus = 0
            self.evento.set()

    def terminate(self, force=False):
        self.forzato = True
        super().terminate(force)


def test_chiudi_fa_uscire_claude_da_solo_senza_forzare():
    finti = []

    def crea(*a, **k):
        finti.append(PtyCheEsceConCtrlC())
        return finti[-1]
    chiuse = []
    t = terminale.Terminali(crea_pty=crea, alla_chiusura=chiuse.append)
    s = t.apri(["claude"], ".", "prova")
    t.chiudi(s.id).join(5)
    assert finti[0].scritto == ["\x1b", "\x03", "\x03"]
    assert not finti[0].forzato and s.codice == 0
    time.sleep(0.1)
    assert chiuse and chiuse[0].id == s.id
    assert s.id not in t.schede


def test_chiudi_forza_se_claude_non_risponde():
    class Sordo(PtyCheEsceConCtrlC):
        def write(self, d):
            self.scritto.append(d)
    finti = []

    def crea(*a, **k):
        finti.append(Sordo())
        return finti[-1]
    t = terminale.Terminali(crea_pty=crea)
    t.USCITA_DOLCE = 1.0
    s = t.apri(["claude"], ".", "prova")
    inizio = time.monotonic()
    t.chiudi_tutte()
    assert finti[0].forzato and time.monotonic() - inizio < 3
    assert finti[0].scritto[:3] == ["\x1b", "\x03", "\x03"]
