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


def _porta_libera():
    # non la 8087: il motore vero dell'app installata puo' essere acceso durante i test
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORTA_LIBERA = _porta_libera()


def configurazione(tmp_path):
    for nome in ("motore.exe", "modello.gguf", "draft.gguf", "immagini.gguf"):
        (tmp_path / nome).touch()
    return {"eseguibile": str(tmp_path / "motore.exe"), "porta": PORTA_LIBERA,
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
    assert argv[argv.index("--model") + 1] == "qwen-locale"
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
    g.configura({**configurazione(tmp_path), "contesto": 8192, "dflash": True})
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
        eventi = []
        p.emetti = lambda nome, dati: eventi.append((nome, dati))
        ripresa = p.apri_chat("riprendi", scheda.sessione)
        assert ripresa["in_avvio"]
        fine = time.monotonic() + 2
        while not eventi and time.monotonic() < fine:
            time.sleep(.01)
        voce_ripresa = next(d for nome, d in eventi if nome == "chat-locale-pronta")
        assert voce_ripresa["locale"]["modello"] == "alfa"
        assert "--resume" in terminali_finti.schede[voce_ripresa["id"]].argv
    else:
        assert "CODEX_HOME" in terminali_finti.ambienti[0]
    g.chiudi()


def test_ripresa_migra_limiti_solo_dopo_apertura_riuscita(tmp_path, monkeypatch):
    import ponte
    g, _ = gestore(tmp_path, monkeypatch)
    cfg = {**configurazione(tmp_path), "contesto": 32768, "dflash": False}
    g.configura(cfg)
    storico = {"modello": "alfa", "contesto": 16384, "dflash": True, "visione": False}
    g.ricorda_sessione("vecchia", "claude", storico)
    p = ponte.Ponte(radice=tmp_path, cache=tmp_path / "cache", terminali=TerminaliLocaliFinti())
    p.locali = g
    monkeypatch.setattr(p, "_impostazioni", lambda: {})
    monkeypatch.setattr(g, "_avvia_ponte", lambda: 12345)
    monkeypatch.setattr(p, "_in_thread", lambda nome, lavoro: lavoro())
    monkeypatch.setattr(g, "_sorveglia", lambda processo: g._stato.update(stato="pronto"))
    eventi = []
    p.emetti = lambda nome, dati: eventi.append(dati)
    # Un client incompatibile non deve essere interrotto, ne' migrare i metadati.
    g.avvia("alfa", 16384, True)
    g.registra_client("altra")
    assert "errore" in p.richiedi_chat_locale("claude", sessione="vecchia")
    assert g.sessione("vecchia")["contesto"] == 16384
    g.rilascia_client("altra")
    assert p.richiedi_chat_locale("claude", sessione="vecchia")["in_avvio"]
    assert eventi[-1]["locale"] == {**storico, "contesto": 32768, "dflash": False}
    assert g.sessione("vecchia")["contesto"] == 32768
    assert p.terminali.ambienti[-1]["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == "32768"
    assert p.terminali.ambienti[-1]["DISABLE_AUTO_COMPACT"] == "1"
    g.chiudi()


def test_ripresa_non_riduce_contesto_ne_cambia_identita_e_visione(tmp_path, monkeypatch):
    g, _ = gestore(tmp_path, monkeypatch)
    precedente = {"modello": "alfa", "contesto": 65536, "dflash": True, "visione": True}
    g.configura({**configurazione(tmp_path), "contesto": 32768, "dflash": False, "visione": False})
    assert g.profilo_chat("altro", precedente) == {**precedente, "dflash": False}
    g.avvia("alfa", 32768, False)
    g._stato["stato"] = "pronto"
    monkeypatch.setattr(g, "_avvia_ponte", lambda: 12345)
    assert g.prepara_client("claude")[1]["DISABLE_AUTO_COMPACT"] == "1"
    g.arresta()
    g.configura({**configurazione(tmp_path), "compattazione_automatica": True})
    g.avvia("alfa", 32768, False)
    g._stato["stato"] = "pronto"
    assert g.prepara_client("claude")[1]["DISABLE_AUTO_COMPACT"] == "0"
    g.chiudi()


def test_ripresa_fallita_non_migra_metadati(tmp_path, monkeypatch):
    import ponte
    g, _ = gestore(tmp_path, monkeypatch)
    storico = {"modello": "alfa", "contesto": 16384, "dflash": True, "visione": False}
    g.ricorda_sessione("vecchia", "claude", storico)
    g.avvia("alfa", 32768, False)
    g._stato["stato"] = "pronto"
    p = ponte.Ponte(radice=tmp_path, cache=tmp_path / "cache", terminali=TerminaliLocaliFinti())
    p.locali = g
    monkeypatch.setattr(p, "_impostazioni", lambda: {})
    monkeypatch.setattr(g, "_avvia_ponte", lambda: 12345)
    def fallisci(*a, **k): raise OSError("apertura fallita")
    monkeypatch.setattr(p.terminali, "apri", fallisci)
    assert "errore" in p.apri_chat_locale("claude", sessione="vecchia")
    assert g.sessione("vecchia") == {"assistente": "claude", **storico}
    g.chiudi()


def test_parole_e_appunti_locali_non_chiamano_worker_cloud(tmp_path, monkeypatch):
    import ponte
    from types import SimpleNamespace
    p = ponte.Ponte(radice=tmp_path, cache=tmp_path / "cache")
    p.locali.ricorda_sessione("locale", "claude", {"modello": "alfa"})
    sessione = SimpleNamespace(id="locale", assistente="claude", percorso=tmp_path / "chat.jsonl", dimensione=100)
    monkeypatch.setattr(p, "_chiedi_per", lambda *a: pytest.fail("chiamata cloud"))
    monkeypatch.setattr(p, "_avvia", lambda *a: pytest.fail("worker cloud"))
    p._lavoro_parole([sessione])
    assert p._appunti_di(sessione) is False


def test_catalogo_dinamico_non_carica_pesi_e_segue_rimozioni(tmp_path):
    g = GestoreLocale(tmp_path / "cache")
    cfg = configurazione(tmp_path)
    g.configura(cfg)
    modello = tmp_path / "Beta-7B-Q4.gguf"
    modello.write_bytes(b'GGUF')
    primo = g.catalogo()["modelli"]
    beta = next(m for m in primo if m["file"] == str(modello))
    assert beta["disponibile"] and beta["id"].startswith("gguf-")
    assert not any(m["file"] == cfg["modelli"]["alfa"]["proiettore"] for m in primo)
    modello.unlink()
    assert not any(m["id"] == beta["id"] for m in g.catalogo()["modelli"])
    assert g.stato()["pid"] is None


def test_limiti_e_riposo_sono_passati_al_motore(tmp_path):
    cfg = {**configurazione(tmp_path), "cache_ram_mib": 256, "checkpoint": 1, "cache_kv": "q4_0",
           "layer_gpu": 20, "mmap": False, "inattivita_secondi": 60}
    argv = argomenti_server(cfg, "alfa", contesto=32768, dflash=False)
    for chiave, valore in (("--sleep-idle-seconds", "60"), ("--cache-ram", "256"), ("--ctx-checkpoints", "1"), ("-ngl", "20"), ("-ctk", "q4_0")):
        assert argv[argv.index(chiave) + 1] == valore
    assert argv[argv.index("--load-mode") + 1] == "none" and "-md" not in argv


def test_riposo_non_impedisce_riutilizzo_del_client(tmp_path, monkeypatch):
    g, _ = gestore(tmp_path, monkeypatch)
    g.avvia("alfa")
    g._stato["stato"] = "riposo"
    _, env = g.prepara_client("codex")
    assert env["CODEX_HOME"]
    g.chiudi()


def test_chiedi_funziona_anche_a_riposo(tmp_path, monkeypatch):
    g, _ = gestore(tmp_path, monkeypatch)
    g.avvia("alfa")
    g._stato["stato"] = "riposo"
    visti = []
    class Risposta:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, *a): return b'{"choices": [{"message": {"content": "391"}}]}'
    class Apri:
        def open(self, richiesta, timeout=None):
            visti.append(timeout)
            return Risposta()
    monkeypatch.setattr("ia_locali.urllib.request.build_opener", lambda *a: Apri())
    profilo = {k: g.stato()[k] for k in ("modello", "contesto", "dflash", "visione")}
    assert g.chiedi("x", profilo, timeout=600) == "391" and visti == [600]
    g.chiudi()


def test_velocita_letta_dal_log_e_profilo_snello(tmp_path, monkeypatch):
    g, _ = gestore(tmp_path, monkeypatch)
    g.avvia("alfa")
    g._stato["stato"] = "pronto"
    Path(g._stato["log"]).write_bytes(
        b"slot print_timing: prompt eval time =   52794.88 ms /  6906 tokens (    7.64 ms per token,   130.81 tokens per second)\n"
        b"slot print_timing:        eval time =     355.70 ms /     4 tokens (  118.57 ms per token,     8.43 tokens per second)\n"
        b"riga incompleta eval time = 1 ms / 1 tokens ( 1 ms per token, 99.0 tokens per sec")
    fine = g._leggi_velocita(0)
    assert g.stato()["velocita"] == {"input": 130.81, "output": 8.43}
    assert g._leggi_velocita(fine) == fine
    opzioni, _ = g.prepara_client("claude")
    assert opzioni[opzioni.index("--setting-sources") + 1] == "user,project,local"
    assert "--disable-slash-commands" not in opzioni and "--strict-mcp-config" in opzioni
    strumenti = opzioni[opzioni.index("--tools") + 1].split(",")
    assert {"Skill", "Agent", "Read", "Write", "Bash"} <= set(strumenti)
    assert "Workflow" not in strumenti and "ToolSearch" not in strumenti
    assert g.prepara_client("claude")[1]["SLASH_COMMAND_TOOL_CHAR_BUDGET"] == "3000"
    g.chiudi()


def test_mcp_opzionale_non_disabilita_comandi_o_skill(tmp_path, monkeypatch):
    g, _ = gestore(tmp_path, monkeypatch)
    g.configura({**configurazione(tmp_path), "mcp_claude": True})
    g.avvia("alfa")
    g._stato["stato"] = "pronto"
    monkeypatch.setattr(g, "_avvia_ponte", lambda: 12345)
    argv, env = g.prepara_client("claude")
    assert "--strict-mcp-config" not in argv and "--disable-slash-commands" not in argv
    assert "ToolSearch" in argv[argv.index("--tools") + 1]
    assert env["ANTHROPIC_MODEL"] == "qwen-locale" and env["DISABLE_COMPACT"] == "0"
    g.chiudi()


def test_profilo_personale_persistente_e_modificabile_a_motore_acceso(tmp_path, monkeypatch):
    g, chiamate = gestore(tmp_path, monkeypatch)
    g.avvia("alfa", 32768, False)
    g._stato["stato"] = "pronto"
    monkeypatch.setattr(g, "_avvia_ponte", lambda: 12345)
    cfg = g.catalogo()["configurazione"]
    cfg.update(profilo_strumenti_claude="personalizzato", strumenti_claude=["Read", "Skill", "NuovoTool", "Read"], budget_skill_claude=1200)
    g.configura(cfg)
    argv, env = g.prepara_client("claude")
    assert argv[argv.index("--tools") + 1] == "Read,Skill,NuovoTool"
    assert env["SLASH_COMMAND_TOOL_CHAR_BUDGET"] == "1200"
    assert "--disable-slash-commands" not in argv
    assert len(chiamate) == 1 and g.stato()["pid"] == Processo.pid
    riaperto = GestoreLocale(g.cartella).catalogo()["configurazione"]
    assert riaperto["strumenti_claude"] == ["Read", "Skill", "NuovoTool"]
    assert riaperto["profilo_strumenti_claude"] == "personalizzato"
    with pytest.raises(ValueError, match="Arrestare"):
        g.configura({**cfg, "contesto": 65536})
    g.chiudi()


def test_migrazione_completo_e_personalizzato_senza_strumenti(tmp_path, monkeypatch):
    g, _ = gestore(tmp_path, monkeypatch)
    g.configura({**configurazione(tmp_path), "strumenti_estesi_claude": True})
    assert g.catalogo()["configurazione"]["profilo_strumenti_claude"] == "completo"
    g.avvia("alfa")
    g._stato["stato"] = "pronto"
    monkeypatch.setattr(g, "_avvia_ponte", lambda: 12345)
    argv, _ = g.prepara_client("claude")
    assert argv[argv.index("--tools") + 1] == "default"
    cfg = g.catalogo()["configurazione"]
    g.configura({**cfg, "profilo_strumenti_claude": "personalizzato", "strumenti_claude": []})
    argv, _ = g.prepara_client("claude")
    assert argv[argv.index("--tools") + 1] == ""
    g.chiudi()


@pytest.mark.parametrize("modifica", [
    {"strumenti_claude": "Read"}, {"strumenti_claude": ["Read,--model"]},
    {"strumenti_claude": [False]}, {"profilo_strumenti_claude": "inventato"},
    {"budget_skill_claude": True}, {"budget_skill_claude": 0}, {"budget_skill_claude": 100000}])
def test_validazione_profilo_personale(tmp_path, modifica):
    with pytest.raises(ValueError):
        GestoreLocale(tmp_path / "dati").configura({**configurazione(tmp_path), **modifica})
