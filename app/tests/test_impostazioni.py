import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ponte  # noqa: E402,F401
import impostazioni as imp  # noqa: E402
import percorsi  # noqa: E402


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(percorsi, "CACHE", tmp_path)
    monkeypatch.setattr(percorsi, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(imp, "gioco_a_schermo_intero", lambda: False)


def test_predefinite_e_salvataggio():
    assert imp.leggi()["tema"] == "scuro"
    r = imp.salva({"tema": "chiaro", "testo": 110, "colore": "nero", "sconosciuta": 1, "appunti_auto": "no",
                   "modello_codex": "gpt-6-astra", "modello_appunti_codex": "gpt-5.5"})
    assert r["ok"] and set(r["scartate"]) == {"colore", "sconosciuta", "appunti_auto", "modello_appunti_codex"}
    letto = imp.leggi()
    assert letto["tema"] == "chiaro" and letto["testo"] == 110 and letto["colore"] == "limone"
    assert letto["modello_codex"] == "gpt-6-astra" and letto["modello_appunti_codex"] == "gpt-5.6-luna"
    assert percorsi.leggi_config()["impostazioni"]["tema"] == "chiaro"


def test_modalita_indipendenti_e_migrazione_codex():
    assert imp.salva({"codex_senza_conferme": True})["ok"]
    assert imp.leggi()["modalita_codex"] == "completa"
    assert imp.salva({"modalita_codex": "lettura", "modalita_claude": "plan", "modalita_agy": "auto", "impegno_codex": "high"})["ok"]
    lette = imp.leggi()
    assert (lette["modalita_codex"], lette["modalita_claude"], lette["modalita_agy"]) == ("lettura", "plan", "auto")
    assert lette["impegno_codex"] == "high"
    assert set(imp.salva({"modalita_codex": "plan", "impegno_codex": "max"})["scartate"]) == {"modalita_codex", "impegno_codex"}


def test_limiti_numerici():
    assert "scartate" in imp.salva({"testo": 300})
    assert "scartate" in imp.salva({"sync_minuti": True})


def test_silenzio_a_cavallo_della_mezzanotte():
    i = {"silenzio_attivo": True, "silenzio_da": "23:00", "silenzio_a": "08:00", "silenzio_gioco": False}
    assert imp.in_silenzio(i, datetime(2026, 1, 1, 23, 30))
    assert imp.in_silenzio(i, datetime(2026, 1, 1, 7, 59))
    assert not imp.in_silenzio(i, datetime(2026, 1, 1, 12, 0))
    assert not imp.in_silenzio({**i, "silenzio_attivo": False}, datetime(2026, 1, 1, 23, 30))


def test_esporta(tmp_path, monkeypatch):
    b = tmp_path / "brain"
    (b / ".git").mkdir(parents=True)
    (b / ".git" / "x").write_text("x", encoding="utf-8")
    (b / "INDICE.md").write_text("i", encoding="utf-8")
    monkeypatch.setattr(imp.Path, "home", lambda: tmp_path)
    r = imp.esporta(b)
    assert r["conto"] == 1 and Path(r["file"]).is_file()
