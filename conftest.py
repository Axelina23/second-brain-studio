# Pytest crea il collegamento "<nome>current" verso l'ultima cartella temporanea. Alcuni
# Windows 11 rifiutano di attraversare i collegamenti creati dai programmi (WinError 448,
# "punto di montaggio non attendibile") e i test falliscono in pulizia: il collegamento
# non serve, quindi non si crea.
import _pytest.pathlib
import _pytest.tmpdir
import subprocess
import sys

import pytest


@pytest.fixture(autouse=True)
def processi_test_nascosti(monkeypatch):
    if sys.platform != "win32":
        return
    originale = subprocess.Popen

    def nascosto(*args, **kwargs):
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
        startup = kwargs.get("startupinfo") or subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = startup
        return originale(*args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", nascosto)


@pytest.fixture(autouse=True)
def elenco_modelli_isolato(tmp_path, monkeypatch):
    # i test non devono leggere l'elenco dei modelli vero di questo PC (~/.claude/second-brain/modelli.json)
    try:
        import modelli_cli
    except ImportError:
        return
    monkeypatch.setattr(modelli_cli, "_file", lambda: tmp_path / "modelli-test.json")


def _niente(*a, **k):
    return None


_pytest.pathlib._force_symlink = _niente
_pytest.tmpdir._force_symlink = _niente
