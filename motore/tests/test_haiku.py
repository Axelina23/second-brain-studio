import subprocess

import haiku


def _run(monkeypatch, comportamento):
    monkeypatch.setattr(haiku.subprocess, "run", comportamento)
    monkeypatch.setattr(haiku.CACHE.__class__, "mkdir", lambda *a, **k: None)


def test_ok(monkeypatch):
    _run(monkeypatch, lambda *a, **k: subprocess.CompletedProcess(a, 0, " ok\n", ""))
    assert haiku.chiedi_haiku("x") == "ok"


def test_uscita_diversa_da_zero(monkeypatch):
    _run(monkeypatch, lambda *a, **k: subprocess.CompletedProcess(a, 1, "ok", "err"))
    assert haiku.chiedi_haiku("x") is None


def test_timeout(monkeypatch):
    def f(*a, **k):
        raise subprocess.TimeoutExpired("c", 1)
    _run(monkeypatch, f)
    assert haiku.chiedi_haiku("x") is None


def test_oserror_e_valueerror(monkeypatch):
    for exc in (OSError, ValueError):
        def f(*a, **k):
            raise exc()
        _run(monkeypatch, f)
        assert haiku.chiedi_haiku("x") is None


def test_parametri(monkeypatch):
    visti = {}

    def f(*a, **k):
        visti.update(k)
        return subprocess.CompletedProcess(a, 0, "ok", "")
    _run(monkeypatch, f)
    haiku.chiedi_haiku("x", 5)
    assert visti["env"]["CLAUDE_NOTES_PASS"] == "1" and visti["timeout"] == 5
    assert visti["errors"] == "replace"
