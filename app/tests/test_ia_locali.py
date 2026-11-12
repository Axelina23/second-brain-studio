import json
import http.client
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ia_locali import GestoreLocale, argomenti_server, normalizza_anthropic
import terminale


def configurazione(tmp_path):
    for nome in ("motore.exe", "modello.gguf", "draft.gguf", "immagini.gguf"):
        (tmp_path / nome).touch()
    return {"eseguibile": str(tmp_path / "motore.exe"), "porta": 8087,
            "inattivita_secondi": 30,
            "modelli": {"alfa": {"nome": "Alfa", "file": str(tmp_path / "modello.gguf"),
                                     "draft": str(tmp_path / "draft.gguf"),
                                     "proiettore": str(tmp_path / "immagini.gguf")}}}


class Processo:
    pid = 1234
    returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


def gestore(tmp_path, monkeypatch, **kwargs):
    chiamate = []

    def popen(argv, **opzioni):
        chiamate.append((argv, opzioni))
        return Processo()

    g = GestoreLocale(tmp_path / "dati", popen=popen, **kwargs)
    monkeypatch.setattr(g, "_sorveglia", lambda processo: None)
    g.configura(configurazione(tmp_path))
    return g, chiamate


def test_costruzione_non_avvia_ne_scrive(tmp_path):
    g = GestoreLocale(tmp_path / "dati", popen=lambda *a, **k: pytest.fail("avvio implicito"))
    assert g.stato()["stato"] == "spento"
    assert not (tmp_path / "dati").exists()


def test_argomenti_memoria_componenti_e_percorsi_con_spazi(tmp_path):
    cfg = configurazione(tmp_path)
    argv = argomenti_server(cfg, "alfa", dflash=True, visione=True)
    assert argv[argv.index("--cache-ram") + 1] == "512"
    assert argv[argv.index("--ctx-checkpoints") + 1] == "2"
    assert argv[argv.index("-np") + 1] == "1"
    assert "--mmproj" in argv and "-md" in argv
    assert cfg["modelli"]["alfa"]["file"] in argv
    (tmp_path / "immagini.gguf").unlink()
    with pytest.raises(ValueError, match="mancanti"):
        argomenti_server(cfg, "alfa", visione=True)


@pytest.mark.parametrize("modifica", [{"porta": True}, {"porta": 80}, {"modelli": []},
                                      {"inattivita_secondi": -1}, {"chiave_api": "non-ammessa"}])
def test_configurazioni_non_valide_rifiutate(tmp_path, modifica):
    g = GestoreLocale(tmp_path / "dati")
    with pytest.raises(ValueError):
        g.configura({**configurazione(tmp_path), **modifica})
    assert not (g.cartella / "config.json").exists()


def test_avvio_idempotente_canali_espliciti_e_stop(tmp_path, monkeypatch):
    g, chiamate = gestore(tmp_path, monkeypatch)
    assert g.avvia("alfa")["stato"] == "caricamento"
    g.avvia("alfa")
    assert len(chiamate) == 1
    assert chiamate[0][1]["stdin"] == subprocess.DEVNULL
    assert chiamate[0][1]["stderr"] == subprocess.STDOUT
    with pytest.raises(ValueError, match="profilo"):
        g.avvia("alfa", contesto=16384)
    assert g.arresta()["stato"] == "spento"
    assert g.stato()["pid"] is None


def test_non_ferma_un_server_esterno(tmp_path, monkeypatch):
    g, chiamate = gestore(tmp_path, monkeypatch)
    with socket.socket() as esterno:
        esterno.bind(("127.0.0.1", 0))
        esterno.listen()
        g.configura({**configurazione(tmp_path), "porta": esterno.getsockname()[1]})
        with pytest.raises(ValueError, match="altro processo"):
            g.avvia("alfa")
        g.arresta()
        assert not chiamate and esterno.fileno() >= 0


def test_client_impediscono_scaricamento_e_cambio_profilo(tmp_path, monkeypatch):
    ora = [0.0]
    g, _ = gestore(tmp_path, monkeypatch, orologio=lambda: ora[0])
    g.avvia("alfa")
    g.registra_client("tab")
    ora[0] = 50
    assert not g.scarica_se_inattivo()
    with pytest.raises(ValueError, match="chat locali"):
        g.arresta()
    g.arresta(forza=True)
    with pytest.raises(ValueError, match="precedente avvio"):
        g.avvia("alfa")
    g.rilascia_client("tab")
    g.avvia("alfa")
    ora[0] = 100
    assert g.scarica_se_inattivo() and g.stato()["stato"] == "spento"


def test_normalizzazione_non_muta_originale_e_preserva_tool_result():
    richiesta = {"system": [{"type": "text", "text": "Regole iniziali"}], "messages": [
        {"role": "user", "content": "Domanda"}, {"role": "system", "content": "Altre regole"},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": "42"}]}]}
    normale = normalizza_anthropic(richiesta)
    assert normale["system"] == "Regole iniziali\n\nAltre regole"
    assert len(normale["messages"]) == 2 and len(richiesta["messages"]) == 3
    assert normale["messages"][-1] == richiesta["messages"][-1]


def test_client_pronti_isolati_e_sessioni_persistenti(tmp_path, monkeypatch):
    g, _ = gestore(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="pronto"):
        g.prepara_client("codex")
    g.avvia("alfa")
    g._stato["stato"] = "pronto"
    argv, env = g.prepara_client("codex")
    assert not argv
    import tomllib
    cfg = tomllib.loads((Path(env["CODEX_HOME"]) / "config.toml").read_text())
    assert cfg["model_provider"] == "second_brain_locale"
    assert cfg["model_context_window"] == 8192
    monkeypatch.setattr(g, "_avvia_ponte", lambda: 12345)
    argv, env = g.prepara_client("claude")
    assert env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:12345"
    assert env["ANTHROPIC_API_KEY"] == "" and env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == "8192"
    assert argv[-2:] == ["--model", "qwen-locale"]
    g.ricorda_sessione("prova", "codex", {"modello": "alfa"})
    riaperto = GestoreLocale(g.cartella)
    assert riaperto.sessione("prova") == {"assistente": "codex", "modello": "alfa"}
    g.chiudi()


def test_ambiente_locale_sovrascrive_account_senza_mutare_cloud(monkeypatch):
    monkeypatch.setattr(terminale, "variabili_utente", lambda: {"ANTHROPIC_API_KEY": "finta-cloud", "CLAUDE_CODE_USE_BEDROCK": "1"})
    ambienti = []

    class Pty:
        exitstatus = 0
        def read(self, n): raise EOFError

    def crea(argv, cwd, cols, rows, env):
        ambienti.append(env)
        return Pty()

    t = terminale.Terminali(crea_pty=crea)
    t.apri(["claude"], ".", "locale", locale={"modello": "alfa"},
           ambiente={"ANTHROPIC_BASE_URL": "http://127.0.0.1:12345", "ANTHROPIC_API_KEY": ""})
    t.apri(["claude"], ".", "cloud")
    assert "CLAUDE_CODE_USE_BEDROCK" not in ambienti[0]
    assert ambienti[0]["ANTHROPIC_API_KEY"] == ""
    assert ambienti[1]["ANTHROPIC_API_KEY"] == "finta-cloud"


def test_config_corrotto_non_impedisce_apertura_app(tmp_path):
    (tmp_path / "config.json").write_text('[]', encoding="utf-8")
    assert GestoreLocale(tmp_path).catalogo()["modelli"] == []


def test_sorvegliante_notifica_pronto_senza_gpu(tmp_path):
    pronto = threading.Event()
    g = GestoreLocale(tmp_path / "dati", popen=lambda *a, **k: Processo(), salute=lambda: True,
                      emetti=lambda nome, stato: pronto.set() if stato["stato"] == "pronto" else None)
    g.configura(configurazione(tmp_path))
    try:
        g.avvia("alfa")
        assert pronto.wait(2)
        assert g.stato()["stato"] == "pronto"
    finally:
        g.chiudi()


def test_ponte_anthropic_preserva_stream_e_non_inoltra_credenziali(tmp_path):
    class Backend(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def do_POST(self):
            self.server.ricevuto = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.server.headers_ricevuti = self.headers
            dati = b'event: message_start\ndata: {"type":"message_start"}\n\nevent: message_stop\ndata: {"type":"message_stop"}\n\n'
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(dati)))
            self.end_headers()
            self.wfile.write(dati)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    g = GestoreLocale(tmp_path / "dati")
    g.configura({**configurazione(tmp_path), "porta": server.server_port})
    try:
        porta = g._avvia_ponte()
        client = http.client.HTTPConnection("127.0.0.1", porta, timeout=3)
        corpo = {"system": "Regole", "messages": [{"role": "user", "content": "Ciao"},
                 {"role": "system", "content": "Altre regole"}], "stream": True}
        client.request("POST", "/v1/messages?beta=true", json.dumps(corpo),
                       {"Content-Type": "application/json", "Authorization": "Bearer finta", "X-Api-Key": "finta"})
        risposta = client.getresponse()
        assert risposta.status == 200 and b'message_stop' in risposta.read()
        assert server.ricevuto["system"] == "Regole\n\nAltre regole"
        assert len(server.ricevuto["messages"]) == 1
        assert server.headers_ricevuti.get("Authorization") is None
        assert server.headers_ricevuti.get("X-Api-Key") is None
        client.close()
    finally:
        g.chiudi()
        server.shutdown()
        server.server_close()


class TerminaliLocaliFinti:
    def __init__(self):
        self.schede = {}
        self.ambienti = []

    def apri(self, argv, cwd, titolo, sessione=None, assistente="claude", ambiente=None, locale=None):
        scheda = terminale.Scheda(str(len(self.schede)), argv, cwd, titolo, sessione,
                                 assistente=assistente, locale=locale)
        self.schede[scheda.id] = scheda
        self.ambienti.append(ambiente)
        return scheda

    def attive(self):
        return [s for s in self.schede.values() if s.codice is None]

    def url(self, sid): return "ws://127.0.0.1/test/" + sid


@pytest.mark.parametrize("assistente", ["claude", "codex"])
def test_ponte_apre_schede_locali_con_ambiente_separato(tmp_path, monkeypatch, assistente):
    import ponte
    g, _ = gestore(tmp_path, monkeypatch)
    g.avvia("alfa")
    g._stato["stato"] = "pronto"
    monkeypatch.setattr(g, "_avvia_ponte", lambda: 12345)
    terminali_finti = TerminaliLocaliFinti()
    p = ponte.Ponte(radice=tmp_path, cache=tmp_path / "cache", terminali=terminali_finti)
    p.locali = g
    monkeypatch.setattr(p, "_impostazioni", lambda: {})
    monkeypatch.setattr(p, "_comando_assistente", lambda nome: ["codex.exe"])
    monkeypatch.setattr(p, "_sessione", lambda sid: None)
    voce = p.apri_chat_locale(assistente, prompt="Ciao")
    assert voce["assistente"] == assistente and voce["locale"]["modello"] == "alfa"
    assert g.stato()["client"] == 1
    scheda = terminali_finti.schede[voce["id"]]
    assert scheda.argv[-1] == "Ciao"
    if assistente == "claude":
        assert "--session-id" in scheda.argv
        assert g.sessione(scheda.sessione)["assistente"] == "claude"
        assert terminali_finti.ambienti[0]["ANTHROPIC_BASE_URL"].endswith(":12345")
        scheda.codice = 0
        ripresa = p.apri_chat("riprendi", scheda.sessione)
        assert ripresa["locale"]["modello"] == "alfa"
        assert "--resume" in terminali_finti.schede[ripresa["id"]].argv
    else:
        assert "CODEX_HOME" in terminali_finti.ambienti[0]
    g.chiudi()


def test_parole_e_appunti_locali_non_chiamano_worker_cloud(tmp_path, monkeypatch):
    import ponte
    from types import SimpleNamespace
    p = ponte.Ponte(radice=tmp_path, cache=tmp_path / "cache")
    p.locali.ricorda_sessione("locale", "claude", {"modello": "alfa"})
    sessione = SimpleNamespace(id="locale", assistente="claude", percorso=tmp_path / "chat.jsonl")
    monkeypatch.setattr(p, "_chiedi_per", lambda *a: pytest.fail("chiamata cloud"))
    monkeypatch.setattr(p, "_avvia", lambda *a: pytest.fail("worker cloud"))
    p._lavoro_parole([sessione])
    assert p._appunti_di(sessione) is False
