import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO / "app"), str(REPO / "motore")]

import pytest
import appunti_locali
import ponte


def chat(tmp_path):
    p = tmp_path / "chat.jsonl"
    p.write_text("\n".join(json.dumps(d) for d in [
        {"type": "user", "message": {"content": [{"type": "text", "text": "Il progetto Alfa usa Python."}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read"},
          {"type": "text", "text": "Aggiorniamo gli appunti."}]}}
    ]), encoding="utf-8")
    return SimpleNamespace(id="test-locale", assistente="claude", percorso=p,
                           ultima=datetime.now().astimezone(), dimensione=50000)


class Gestore:
    def __init__(self): self.client = set()
    def sessione(self, sid): return {"assistente": "claude", "modello": "alfa"}
    def profilo_chat(self, **kw): return dict(modello="alfa", contesto=32768, dflash=False, visione=False)
    def stato(self): return dict(stato="pronto", pid=123, client=len(self.client), **self.profilo_chat())
    def avvia(self, **kw): return self.stato()
    def registra_client(self, sid): self.client.add(sid)
    def rilascia_client(self, sid): self.client.discard(sid)
    def prepara_client(self, assistente):
        return ["--settings", "locale.json"], {"ANTHROPIC_BASE_URL": "http://127.0.0.1:18880", "ANTHROPIC_MODEL": "qwen-locale"}


def test_worker_legge_claude_vero_non_confonde_tool_con_testo(tmp_path):
    s = chat(tmp_path)
    assert appunti_locali.conversazione(s) == "UTENTE: Il progetto Alfa usa Python.\n\nASSISTENTE: Aggiorniamo gli appunti."


@pytest.mark.parametrize("conferma", [True, False])
def test_worker_richiede_conferma_positiva_e_usa_ambiente_locale(tmp_path, monkeypatch, conferma):
    s = chat(tmp_path)
    monkeypatch.setattr(appunti_locali.assistenti, "comando", lambda chi: ["claude.exe"])
    def run(argv, **kw):
        assert kw["env"]["ANTHROPIC_MODEL"] == "qwen-locale"
        assert kw["env"]["ANTHROPIC_BASE_URL"].startswith("http://127.0.0.1:")
        assert "--no-session-persistence" in argv and "--disable-slash-commands" not in argv
        assert "SB_NOTES_OK" in kw["input"] and "INDICE.md" in kw["input"]
        return SimpleNamespace(returncode=0, stdout="Fatto\nSB_NOTES_OK\n" if conferma else "Non riesco", stderr="")
    if conferma:
        assert "SB_NOTES_OK" in appunti_locali.esegui(Gestore(), s, tmp_path, tmp_path / "log", run=run)
    else:
        with pytest.raises(RuntimeError, match="confermato"):
            appunti_locali.esegui(Gestore(), s, tmp_path, tmp_path / "log", run=run)


@pytest.mark.parametrize("errore", [False, True])
def test_pulsante_locale_attiva_stato_e_finalizza_senza_cloud(tmp_path, monkeypatch, errore):
    s = chat(tmp_path)
    p = ponte.Ponte(radice=tmp_path, cache=tmp_path / "cache", segni=tmp_path / "segni")
    p.locali = Gestore()
    lavori, eventi = [], []
    monkeypatch.setattr(p, "_sessione", lambda sid: s)
    monkeypatch.setattr(p, "_impostazioni", lambda: {"appunti_auto": False})
    monkeypatch.setattr(p, "_in_thread", lambda nome, f, *a: lavori.append((f, a)))
    monkeypatch.setattr(p, "_avvia", lambda *a: pytest.fail("worker cloud"))
    p.emetti = lambda *a: eventi.append(a)
    def esegui(*a, **kw):
        assert p.locali.client == {"appunti-" + s.id}
        if errore: raise RuntimeError("non confermato")
    monkeypatch.setattr(ponte.appunti_locali, "esegui", esegui)
    assert not p._appunti_di(s)  # automatici spenti
    assert p.salva_chat(s.id) == {"avviato": True, "sessione": s.id}
    assert ponte.salvataggio.stato_salvataggio(s, p.segni) == "in_corso"
    assert p.salva_chat(s.id)["avviato"] and len(lavori) == 1
    f, a = lavori[0]; f(*a)
    assert ponte.salvataggio.stato_salvataggio(s, p.segni) == ("errore_salvataggio" if errore else "salvata")
    assert not p.locali.client and not (p.segni / f"{s.id}.in-corso").exists()
    assert not (p.segni / f"{s.id}.salvata").exists() if errore else True
    assert eventi[-1][0] == "chat-cambiate"


def test_chiusura_locale_avvia_salvataggio_automatico(tmp_path, monkeypatch):
    s = chat(tmp_path)
    p = ponte.Ponte(radice=tmp_path, cache=tmp_path / "cache", segni=tmp_path / "segni")
    p.locali = Gestore()
    p.locali.ricorda_sessione = lambda *a: None
    monkeypatch.setattr(p, "_sessione", lambda sid: s)
    monkeypatch.setattr(p, "_impostazioni", lambda: {"appunti_auto": True, "soglia_kb": 30})
    lavori = []
    monkeypatch.setattr(p, "_in_thread", lambda nome, f, *a: lavori.append(nome))
    p.scheda_chiusa(SimpleNamespace(id="tab", sessione=s.id, assistente="claude", locale={"modello": "alfa"}))
    assert lavori == ["appunti-locali-" + s.id]
    assert (p.segni / f"{s.id}.chiusa").exists()
    assert ponte.salvataggio.stato_salvataggio(s, p.segni) == "in_corso"


@pytest.mark.parametrize("bloccato", [False, True])
def test_worker_codex_conferma_solo_ultima_risposta_locale(tmp_path, monkeypatch, bloccato):
    s = chat(tmp_path); s.assistente = "codex"
    monkeypatch.setattr(appunti_locali, "conversazione", lambda s: "UTENTE: Decisione sul progetto Alfa.")
    monkeypatch.setattr(appunti_locali.assistenti, "comando", lambda chi: ["codex.exe"])
    def run(argv, **kw):
        assert argv[:4] == ["codex.exe", "-a", "never", "exec"]
        assert "--ephemeral" in argv and argv[-1] == "-"
        assert kw["env"]["CODEX_HOME"] == str(tmp_path / "profilo-locale")
        Path(argv[argv.index("--output-last-message") + 1]).write_text("SB_NOTES_OK\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="log", stderr="rejected: blocked by policy" if bloccato else "")
    g = Gestore()
    g.prepara_client = lambda a: ([], {"CODEX_HOME": str(tmp_path / "profilo-locale")})
    if bloccato:
        with pytest.raises(RuntimeError, match="accesso"):
            appunti_locali.esegui(g, s, tmp_path, tmp_path / "log", run=run)
    else:
        assert "SB_NOTES_OK" in appunti_locali.esegui(g, s, tmp_path, tmp_path / "log", run=run)
