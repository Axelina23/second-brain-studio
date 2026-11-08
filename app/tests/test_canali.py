# Riproduce il guasto "[WinError 6] Handle non valido" in un processo figlio: canale di
# ingresso non valido, subprocess fallisce; dopo canali.sistema() funziona.
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent

FIGLIO = r"""
import ctypes, subprocess, sys
sys.path.insert(0, sys.argv[1])
k = ctypes.windll.kernel32
k.SetStdHandle.argtypes = [ctypes.c_ulong, ctypes.c_void_p]
k.SetStdHandle(ctypes.c_ulong(-10 & 0xFFFFFFFF).value, ctypes.c_void_p(0x7FF0))  # handle finto
def prova():
    try:
        subprocess.run(["cmd", "/c", "echo ok"], capture_output=True, text=True, timeout=20)
        return "ok"
    except OSError as e:
        return f"errore {getattr(e, 'winerror', '')}"
prima = prova()
import canali
sostituiti = canali.sistema()
print(prima, "|", prova(), "|", sostituiti)
"""


@pytest.mark.skipif(sys.platform != "win32", reason="solo Windows")
def test_canale_non_valido_viene_sistemato():
    r = subprocess.run([sys.executable, "-c", FIGLIO, str(APP)], capture_output=True, text=True, timeout=60)
    prima, dopo, sostituiti = (x.strip() for x in r.stdout.split("|"))
    assert prima == "errore 6", r.stdout + r.stderr
    assert dopo == "ok"
    assert "-10" in sostituiti


@pytest.mark.skipif(sys.platform != "win32", reason="solo Windows")
def test_app_impacchettata_li_sostituisce_sempre():
    # come nell'app installata: tutti e tre su NUL, e i comandi funzionano
    codice = ("import sys, subprocess; sys.path.insert(0, sys.argv[1]); import canali; s = canali.sistema(sempre=True); "
              "r = subprocess.run(['cmd', '/c', 'echo ok'], capture_output=True, text=True); print(s, r.stdout.strip())")
    r = subprocess.run([sys.executable, "-c", codice, str(APP)], capture_output=True, text=True, timeout=60)
    assert r.stdout.strip() == "[-10, -11, -12] ok", r.stdout + r.stderr


def test_canali_validi_restano():
    # in un processo con canali validi non si sostituisce niente
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import canali; print(canali.sistema())", str(APP)],
                       capture_output=True, text=True, timeout=60)
    assert r.stdout.strip() == "[]", r.stdout + r.stderr
