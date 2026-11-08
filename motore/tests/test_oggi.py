import json
import subprocess
from datetime import date
from pathlib import Path

import oggi

OGGI = date(2026, 11, 7)


def _fake_run(stdout="", exc=None, rc=0):
    def run(*a, **k):
        if exc:
            raise exc
        return subprocess.CompletedProcess(a, rc, stdout=stdout, stderr="")
    return run


def test_parsing_cal(monkeypatch):
    out = ("2026-11-07 15:00 | Esami | Ricevimento | uid=x\n"
           "2026-11-07 17:30:00+01:00 | Esami | Lezione | Aula 3 | uid=y\n"
           "2026-11-08 09:00 | Esami | Domani | uid=z\n"
           "2026-11-07 | Vita | Compleanno | uid=w\n")
    monkeypatch.setattr(oggi.subprocess, "run", _fake_run(out))
    assert oggi.eventi_oggi(Path("."), oggi=OGGI) == [
        "15:00 Ricevimento", "17:30 Lezione", "Compleanno"]


def test_cal_fallisce(monkeypatch):
    monkeypatch.setattr(oggi.subprocess, "run", _fake_run(rc=1, stdout="x"))
    assert oggi.eventi_oggi(Path("."), oggi=OGGI) == []
    monkeypatch.setattr(oggi.subprocess, "run",
                        _fake_run(exc=subprocess.TimeoutExpired("cal", 5)))
    assert oggi.eventi_oggi(Path("."), oggi=OGGI) == []
    monkeypatch.setattr(oggi.subprocess, "run", _fake_run(exc=OSError("no")))
    assert oggi.eventi_oggi(Path("."), oggi=OGGI) == []


def test_scadenze_cache(tmp_path):
    radice = tmp_path / "r"
    (radice / "Universit\u00e0").mkdir(parents=True)
    (radice / "Universit\u00e0" / "stato.md").write_text("appello 12 nov", encoding="utf-8")
    (radice / "Progetti" / "A").mkdir(parents=True)
    (radice / "Progetti" / "A" / "CLAUDE.md").write_text("scadenza A", encoding="utf-8")
    (radice / "INDICE.md").write_text(
        "## Progetti attivi\n- **A** — x → `Progetti/A/CLAUDE.md`\n\n## Vita\n", encoding="utf-8")
    chiamate = []

    def chiedi(p, timeout=60):
        chiamate.append(p)
        return "Appello 12 nov"

    cache = tmp_path / "c"
    assert oggi.scadenze(radice, cache, OGGI, chiedi) == "Appello 12 nov"
    assert oggi.scadenze(radice, cache, OGGI, chiedi) == "Appello 12 nov"
    assert len(chiamate) == 1
    assert "scadenza A" in chiamate[0] and "appello 12 nov" in chiamate[0]
    assert json.loads((cache / "scadenze.json").read_text(encoding="utf-8"))["data"] == "2026-11-07"
    # giorno dopo: richiama
    oggi.scadenze(radice, cache, date(2026, 11, 8), chiedi)
    assert len(chiamate) == 2


def test_scadenze_senza_risposta(tmp_path):
    assert oggi.scadenze(tmp_path, tmp_path / "c", OGGI, lambda p, timeout=60: None) is None


def test_riga_oggi():
    assert oggi.riga_oggi(["15:00 A", "B"], "Appello 12 nov") == "15:00 A \u00b7 B\nAppello 12 nov"
    assert oggi.riga_oggi([], None) == ""
    assert oggi.riga_oggi([], "S") == "S"
    lunga = oggi.riga_oggi(["x" * 300], "y" * 300).split("\n")
    assert len(lunga) == 2 and all(len(r) <= 160 for r in lunga)


def test_cal_non_utf8(monkeypatch):
    def run(*a, **k):
        assert k.get("errors") == "replace"
        return subprocess.CompletedProcess(a, 0, stdout="2026-11-07 | X | Caff\ufffd\n", stderr="")
    monkeypatch.setattr(oggi.subprocess, "run", run)
    assert oggi.eventi_oggi(Path("."), oggi=OGGI) == ["Caff\ufffd"]
    monkeypatch.setattr(oggi.subprocess, "run",
                        _fake_run(exc=UnicodeDecodeError("utf-8", b"", 0, 1, "x")))
    assert oggi.eventi_oggi(Path("."), oggi=OGGI) == []


def _area(radice, rel="Lavoro/stato.md"):
    (radice / rel).parent.mkdir(parents=True, exist_ok=True)
    (radice / rel).write_text("consegna 10 nov", encoding="utf-8")


def test_scadenze_json_malformato(tmp_path):
    _area(tmp_path)
    cache = tmp_path / "c"
    cache.mkdir()
    for contenuto in ("{rotto", "[1,2]", '{"riprova_dopo": "x"}'):
        (cache / "scadenze.json").write_text(contenuto, encoding="utf-8")
        assert oggi.scadenze(tmp_path, cache, OGGI, lambda p, timeout=60: "ok") == "ok"


def test_scadenze_cache_negativa(tmp_path, monkeypatch):
    chiamate = []

    def chiedi(p, timeout=60):
        chiamate.append(1)
        return None

    _area(tmp_path)
    ora = [1000.0]
    monkeypatch.setattr(oggi.time, "time", lambda: ora[0])
    cache = tmp_path / "c"
    assert oggi.scadenze(tmp_path, cache, OGGI, chiedi) is None
    ora[0] += 1800
    assert oggi.scadenze(tmp_path, cache, OGGI, chiedi) is None
    assert len(chiamate) == 1
    ora[0] += 2000
    oggi.scadenze(tmp_path, cache, OGGI, chiedi)
    assert len(chiamate) == 2


def test_scadenze_scarta_risposte_non_valide(tmp_path):
    cattiva = "Non riesco a leggere `Progetti/X/CLAUDE.md`: il permesso non è stato concesso. **Appello** 12 nov"
    assert oggi.scadenze(tmp_path, tmp_path / "c", OGGI, lambda p, timeout=60: cattiva) is None
    assert oggi.scadenze(tmp_path, tmp_path / "d", OGGI, lambda p, timeout=60: "x" * 300) is None


def test_scadenze_aree_qualsiasi_e_inglese(tmp_path):
    # tutte le aree (non solo Università) e, nella struttura inglese, file e domanda in inglese
    _area(tmp_path, "Lavoro/stato.md")
    _area(tmp_path, "Io/stato.md")   # Io non e' un'area
    chiamate = []
    oggi.scadenze(tmp_path, tmp_path / "c", OGGI, lambda p, timeout=60: chiamate.append(p) or "ok")
    assert "### Lavoro/stato.md" in chiamate[0] and "Io/stato.md" not in chiamate[0] and "Oggi è" in chiamate[0]
    en = tmp_path / "en"
    _area(en, "Work/status.md")
    (en / "Projects" / "A").mkdir(parents=True)
    (en / "Projects" / "A" / "CLAUDE.md").write_text("launch 9 nov", encoding="utf-8")
    (en / "INDEX.md").write_text("## Active projects\n- **A** → `Projects/A/CLAUDE.md`\n", encoding="utf-8")
    oggi.scadenze(en, tmp_path / "d", OGGI, lambda p, timeout=60: chiamate.append(p) or "ok")
    assert "### Work/status.md" in chiamate[1] and "launch 9 nov" in chiamate[1] and "Today is" in chiamate[1]


def test_niente_materiale_niente_haiku(tmp_path):
    assert oggi.scadenze(tmp_path, tmp_path / "c", OGGI, lambda p, timeout=60: 1 / 0) is None
