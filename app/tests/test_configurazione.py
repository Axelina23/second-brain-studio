import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ponte  # noqa: E402,F401  (aggiunge motore/ al percorso)
import configurazione  # noqa: E402
import modello  # noqa: E402
import percorsi  # noqa: E402


@pytest.fixture
def casa(tmp_path, monkeypatch):
    # isola config.json, ~/.claude/CLAUDE.md e settings.json in una cartella temporanea
    cache = tmp_path / "cache"
    monkeypatch.setattr(percorsi, "CACHE", cache)
    monkeypatch.setattr(percorsi, "CONFIG", cache / "config.json")
    claude_md = tmp_path / "CLAUDE.md"
    settings = tmp_path / "settings.json"
    vero_md, vero_hook = modello.collega_claude_md, modello.collega_hook
    monkeypatch.setattr(modello, "collega_claude_md", lambda r, f=None: vero_md(r, claude_md))
    monkeypatch.setattr(modello, "collega_hook", lambda s, d, f=None, riga_stato=True: vero_hook(s, d, settings))
    hook = tmp_path / "hook-app"
    hook.mkdir()
    (hook / "sync.ps1").write_text("#", encoding="utf-8")
    return {"tmp": tmp_path, "claude_md": claude_md, "settings": settings, "hook": hook}


def test_non_configurato(casa):
    s = configurazione.stato()
    assert not s["configurato"] and s["proposta"].endswith("Second Brain")


def test_completa_nuovo(casa):
    cartella = casa["tmp"] / "Mio Brain"
    esito = configurazione.completa({"modo": "nuovo", "cartella": str(cartella),
                                     "risposte": {"nome": "Luca", "aree": "Lavoro"}}, None, casa["hook"])
    assert esito["ok"] and esito["prompt"] and "Luca" in esito["prompt"]
    assert (cartella / "INDICE.md").is_file() and (cartella / "Lavoro" / "stato.md").is_file()
    assert json.loads(percorsi.CONFIG.read_text(encoding="utf-8"))["radice"] == str(cartella)
    assert configurazione.stato()["configurato"]
    assert "Mio\\ Brain/INDICE.md" in casa["claude_md"].read_text(encoding="utf-8")
    assert "SessionEnd" in json.loads(casa["settings"].read_text(encoding="utf-8"))["hooks"]


def test_nuovo_su_brain_esistente(casa):
    c = casa["tmp"] / "b"
    c.mkdir()
    (c / "INDICE.md").write_text("x", encoding="utf-8")
    assert "errore" in configurazione.completa({"modo": "nuovo", "cartella": str(c)}, None, casa["hook"])
    assert configurazione.completa({"modo": "esistente", "cartella": str(c), "hook": False,
                                    "claude_md": False}, None, casa["hook"])["ok"]
    assert (c / "INDICE.md").read_text(encoding="utf-8") == "x"


def test_github_vuole_cartella_vuota(casa):
    c = casa["tmp"] / "piena"
    c.mkdir()
    (c / "a.txt").write_text("x", encoding="utf-8")
    assert "errore" in configurazione.completa({"modo": "github", "cartella": str(c), "repo": "https://github.com/a/b"},
                                               None, casa["hook"])


def test_valuta_cartella_relativa():
    assert "errore" in configurazione.valuta_cartella("relativa")
