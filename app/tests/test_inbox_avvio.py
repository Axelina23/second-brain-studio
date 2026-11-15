"""Verifica il percorso CLI e la consegna all'istanza esistente senza aprire finestre."""
import importlib.util
import json
import socket
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

APP = Path(__file__).resolve().parent.parent


def carica_main(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    import canali
    monkeypatch.setattr(canali, "sistema", lambda: None)
    spec = importlib.util.spec_from_file_location("sbs_main_inbox_test", APP / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_chiusa_consegna_tutti_i_percorsi(monkeypatch, tmp_path):
    m = carica_main(monkeypatch)
    chiamate = []
    monkeypatch.setattr(m, "gia_aperta", lambda comando: chiamate.append(comando) or False)
    monkeypatch.setattr(m, "App", lambda *a: SimpleNamespace(
        importa_inbox=lambda file: chiamate.append(file), avvia=lambda: chiamate.append("avviata")))
    file = [str(tmp_path / "uno con spazi.pdf"), str(tmp_path / "due è.png")]
    monkeypatch.setattr(sys, "argv", ["sbs", "--inbox", *file])
    m.main()
    assert json.loads(chiamate[0][6:]) == file
    assert chiamate[1:] == [file, "avviata"]


def test_istanza_aperta_riceve_un_invito_multifile(monkeypatch, tmp_path):
    m = carica_main(monkeypatch)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    monkeypatch.setattr(m, "PORTA_ISTANZA", porta)
    ricevuti = []
    evento = threading.Event()
    app = m.App.__new__(m.App)
    app.uscendo = False
    app.finestra = None
    app.importa_inbox = lambda file: (ricevuti.extend(file), evento.set())
    t = threading.Thread(target=app._ascolta_istanze, daemon=True)
    t.start()
    file = [str(tmp_path / "primo documento.pdf"), str(tmp_path / "secondo è.txt")]
    try:
        for _ in range(40):
            if m.gia_aperta(b"inbox " + json.dumps(file).encode()):
                break
            time.sleep(.025)
        assert evento.wait(2)
        assert ricevuti == file
    finally:
        app.uscendo = True
        m.gia_aperta()
        t.join(2)


def test_importazione_accodata_fino_a_interfaccia_pronta(monkeypatch, tmp_path):
    m = carica_main(monkeypatch)
    import ponte
    (tmp_path / "INDICE.md").write_text("# Indice", encoding="utf-8")
    file = tmp_path / "prova.pdf"
    file.write_bytes(b"documento inventato")
    app = m.App.__new__(m.App)
    app.ponte = ponte.Ponte(radice=tmp_path, cache=tmp_path / "cache", cartella_sessioni=tmp_path / "sessioni")
    app._blocco_importazioni = threading.Lock()
    app._importazioni = []
    app.mostra = lambda: None
    app.importa_inbox([str(file)])
    api = m.Api(app)
    assert len(api.importazioni_inbox()["esiti"][0]["aggiunti"]) == 1
    assert api.importazioni_inbox() == {"esiti": []}
    assert file.exists()
