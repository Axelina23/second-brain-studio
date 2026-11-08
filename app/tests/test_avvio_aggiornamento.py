# Lo script dell'aggiornamento deve partire anche se l'app ha canali standard non validi
# (app riaperta dall'installer) e anche senza la correzione di canali.py.
import subprocess
import sys
import time
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent

FIGLIO = r"""
import ctypes, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
k = ctypes.windll.kernel32
k.SetStdHandle.argtypes = [ctypes.c_ulong, ctypes.c_void_p]
for c in (-10, -11, -12):
    k.SetStdHandle(ctypes.c_ulong(c & 0xFFFFFFFF).value, ctypes.c_void_p(0x7FF0))  # handle finti
import aggiornamenti
ok = aggiornamenti.avvia_staccato(Path(sys.argv[2]))
Path(sys.argv[3]).write_text(str(ok))
"""


@pytest.mark.skipif(sys.platform != "win32", reason="solo Windows")
def test_due_script_insieme_ne_parte_uno(tmp_path):
    # doppio clic sul pulsante: il secondo script deve uscire senza lanciare un altro installer
    sys.path.insert(0, str(APP))
    import aggiornamenti
    testo = aggiornamenti.script_aggiornamento(999999, str(tmp_path / "manca.exe"), "1.0", False, None, tmp_path)
    testo = _mutex_di_prova(testo, tmp_path)
    # il primo resta un po' dentro (mutex preso) prima di finire
    testo = testo.replace("$fine = (Get-Date).AddSeconds(60)", "Start-Sleep -Seconds 4; $fine = (Get-Date).AddSeconds(60)", 1)
    script = tmp_path / "s.ps1"
    script.write_text(testo, encoding="utf-8")
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    a = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    b = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    a.wait(timeout=60)
    log = (tmp_path / "aggiornamento.log").read_text(encoding="utf-8-sig")
    assert log.count("inizio:") == 1, log
    assert "gia in corso" in log


def _mutex_di_prova(testo: str, tmp_path: Path) -> str:
    # nome del mutex unico per il test: un aggiornamento vero in corso sul PC non lo disturba
    nome = "Local\\SecondBrainStudioAggiornamento"
    assert nome in testo
    return testo.replace(nome, f"Local\\SBSProva{abs(hash(str(tmp_path)))}")


@pytest.mark.skipif(sys.platform != "win32", reason="solo Windows")
def test_installer_che_riapre_l_app_non_blocca_lo_script(tmp_path):
    # l'installer riapre l'app alla fine (un suo processo figlio che resta vivo): lo script deve
    # registrare la fine dell'installer e uscire, senza aspettare che l'app venga chiusa
    sys.path.insert(0, str(APP))
    import aggiornamenti
    setup = tmp_path / "setup.cmd"
    setup.write_text('@start "" /b powershell -NoProfile -Command "Start-Sleep -Seconds 40"\r\n@exit /b 0\r\n', encoding="ascii")
    testo = _mutex_di_prova(aggiornamenti.script_aggiornamento(999999, str(setup), "1.0", False, None, tmp_path), tmp_path)
    script = tmp_path / "s.ps1"
    script.write_text(testo, encoding="utf-8")
    inizio = time.time()
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                   stdin=subprocess.DEVNULL, capture_output=True, timeout=90)
    log = (tmp_path / "aggiornamento.log").read_text(encoding="utf-8-sig")
    assert "installer finito: codice 0" in log, log
    assert time.time() - inizio < 30, "lo script ha aspettato il processo figlio dell'installer"


@pytest.mark.skipif(sys.platform != "win32", reason="solo Windows")
def test_avvio_con_canali_non_validi(tmp_path):
    segno = tmp_path / "partito.txt"
    script = tmp_path / "prova.ps1"
    script.write_text(f"Set-Content -LiteralPath '{segno}' -Value 'si'", encoding="utf-8")
    esito = tmp_path / "esito.txt"
    subprocess.run([sys.executable, "-c", FIGLIO, str(APP), str(script), str(esito)],
                   stdin=subprocess.DEVNULL, capture_output=True, timeout=90)
    assert esito.read_text() == "True"
    for _ in range(60):
        if segno.exists():
            break
        time.sleep(0.5)
    assert segno.exists(), "lo script staccato non e' partito"
