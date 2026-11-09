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


def test_assistente_codex_e_agy_e_ripiego_su_claude(monkeypatch):
    visti = []

    def f(cmd, *a, **k):
        visti.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "ok", "")
    _run(monkeypatch, f)
    monkeypatch.setattr(haiku.assistenti, "comando", lambda n: [f"C:/bin/{n}.exe"])
    assert haiku.chiedi_haiku("x", assistente="codex") == "ok"
    assert visti[-1] == ["C:/bin/codex.exe", "exec", "--ephemeral", "--skip-git-repo-check", "-s", "read-only", "-m", "gpt-5.6-luna", "-"]
    assert haiku.chiedi_haiku("x", assistente="agy") == "ok"
    assert visti[-1] == ["C:/bin/agy.exe", "-p", "--model", "gemini-3.8-flash-low", "--disable-slash-commands"]
    monkeypatch.setattr(haiku.assistenti, "comando", lambda n: None)
    assert haiku.chiedi_haiku("x", assistente="codex") == "ok"
    assert visti[-1][-3:] == ["-p", "--model", "haiku"]
