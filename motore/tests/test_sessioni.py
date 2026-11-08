import json
from datetime import datetime, timezone

from sessioni import elenca_sessioni


def scrivi(cartella, nome, righe):
    p = cartella / f"{nome}.jsonl"
    p.write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in righe) + "\n", encoding="utf-8")
    return p


def utente(testo, ts="2026-01-01T10:00:00.000Z", entry="cli"):
    return {"type": "user", "entrypoint": entry, "timestamp": ts, "message": {"role": "user", "content": testo}}


def test_esclude_headless(tmp_path):
    scrivi(tmp_path, "a", [utente("ciao", entry="sdk-cli")])
    scrivi(tmp_path, "b", [utente("ciao")])
    assert [s.id for s in elenca_sessioni(tmp_path)] == ["b"]


def test_esclude_senza_messaggi(tmp_path):
    scrivi(tmp_path, "a", [{"type": "summary", "timestamp": "2026-01-01T10:00:00Z"}])
    scrivi(tmp_path, "b", [{"type": "user", "entrypoint": "cli", "message": {"content": [
        {"type": "tool_result", "content": "x"}]}}])
    assert elenca_sessioni(tmp_path) == []


def test_salta_comandi_locali(tmp_path):
    scrivi(tmp_path, "a", [utente("<local-command-stdout>x"), utente("<command-name>/x"), utente("vero")])
    s = elenca_sessioni(tmp_path)[0]
    assert s.primo_messaggio == "vero"


def test_blocchi_testo(tmp_path):
    r = {"type": "user", "entrypoint": "cli", "message": {"content": [
        {"type": "tool_result", "content": "no"}, {"type": "text", "text": "si"}]}}
    scrivi(tmp_path, "a", [r])
    assert elenca_sessioni(tmp_path)[0].primo_messaggio == "si"


def test_riga_rotta(tmp_path):
    scrivi(tmp_path, "a", [utente("uno"), "{non json", utente("due", ts="2026-01-02T10:00:00Z")])
    s = elenca_sessioni(tmp_path)
    assert len(s) == 1 and "due" in s[0].testo_utente


def test_ultima_attivita(tmp_path):
    scrivi(tmp_path, "a", [utente("uno"), utente("due", ts="2026-03-05T08:30:00Z"), {"type": "x"}])
    u = elenca_sessioni(tmp_path)[0].ultima
    assert u.tzinfo is not None
    assert u == datetime(2026, 3, 5, 8, 30, tzinfo=timezone.utc)


def test_ultima_fallback_mtime(tmp_path):
    p = scrivi(tmp_path, "a", [{"type": "user", "entrypoint": "cli", "message": {"content": "x"}}])
    u = elenca_sessioni(tmp_path)[0].ultima
    assert abs(u.timestamp() - p.stat().st_mtime) < 1


def test_ordinate_decrescente(tmp_path):
    scrivi(tmp_path, "vecchia", [utente("a", ts="2026-01-01T00:00:00Z")])
    scrivi(tmp_path, "nuova", [utente("a", ts="2026-02-01T00:00:00Z")])
    assert [s.id for s in elenca_sessioni(tmp_path)] == ["nuova", "vecchia"]


def test_testo_utente_limitato(tmp_path):
    scrivi(tmp_path, "a", [utente("A" * 5000), utente("B" * 5000)])
    t = elenca_sessioni(tmp_path)[0].testo_utente
    assert len(t) <= 6000 and t.endswith("B") and t.startswith("B") is False


def test_conta_messaggi(tmp_path):
    scrivi(tmp_path, "a", [utente("uno"), utente("<command-name>/x"), utente("due"), utente("tre")])
    assert elenca_sessioni(tmp_path)[0].n_messaggi == 3


def test_ignora_messaggi_meta(tmp_path):
    meta = dict(utente("Another Claude session sent a message", ts="2026-01-02T10:00:00Z"), isMeta=True)
    scrivi(tmp_path, "a", [meta, utente("vero"), meta])
    s = elenca_sessioni(tmp_path)[0]
    assert s.primo_messaggio == "vero" and s.testo_utente == "vero" and s.n_messaggi == 1
    assert s.ultima == datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)


def test_esclude_solo_meta(tmp_path):
    scrivi(tmp_path, "a", [dict(utente("Base directory for this skill"), isMeta=True)])
    assert elenca_sessioni(tmp_path) == []
