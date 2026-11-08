import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import avvisi  # noqa: E402


def test_leggi_eventi_cancella_e_scarta_i_vecchi(tmp_path):
    (tmp_path / "1.json").write_text(json.dumps({"evento": "fine", "quando": time.time()}), encoding="utf-8")
    (tmp_path / "2.json").write_text(json.dumps({"evento": "fine", "quando": time.time() - 3600}), encoding="utf-8")
    (tmp_path / "3.json").write_text("rotto", encoding="utf-8")
    e = avvisi.leggi_eventi(tmp_path)
    assert len(e) == 1 and not list(tmp_path.glob("*.json"))


def test_ultima_risposta(tmp_path):
    t = tmp_path / "s.jsonl"
    righe = [{"type": "user", "message": {"content": "ciao"}},
             {"type": "assistant", "message": {"content": [{"type": "text", "text": "Prima **risposta**"}]}},
             {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
             {"type": "assistant", "message": {"content": [{"type": "text", "text": "Ho finito: " + "parola " * 60}]}}]
    t.write_text("\n".join(json.dumps(r) for r in righe), encoding="utf-8")
    r = avvisi.ultima_risposta(str(t), 60)
    assert r.startswith("Ho finito:") and r.endswith("…") and len(r) <= 60
    assert avvisi.ultima_risposta(None) == "" and avvisi.ultima_risposta(str(tmp_path / "no")) == ""


def test_nome_progetto(tmp_path):
    r = tmp_path / "Brain"
    (r / "Progetti" / "Negozio" / "src").mkdir(parents=True)
    assert avvisi.nome_progetto(str(r / "Progetti" / "Negozio" / "src"), r) == "Negozio"
    assert avvisi.nome_progetto(str(r), r) == "Second brain"
    assert avvisi.nome_progetto(str(tmp_path / "repo"), r) == "repo"
