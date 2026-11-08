# La riga di stato in modalita' ponte: salva l'uso del piano per l'app e restituisce
# l'output della riga di stato che l'utente aveva gia', con gli stessi dati in ingresso.
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / "hooks"
DATI = {"model": {"display_name": "Opus"}, "context_window": {"used_percentage": 12},
        "rate_limits": {"five_hour": {"used_percentage": 41.5, "resets_at": 4102444800},
                        "seven_day": {"used_percentage": 9, "resets_at": 4102444800}}}


def _lancia(cartella: Path, casa: Path, *arg: str) -> subprocess.CompletedProcess:
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                           str(cartella / "riga-stato.ps1"), *arg],
                          input=json.dumps(DATI).encode("utf-8"), capture_output=True, timeout=60,
                          env={**os.environ, "USERPROFILE": str(casa)})


@pytest.mark.skipif(sys.platform != "win32", reason="solo Windows")
def test_ponte_salva_uso_e_restituisce_la_riga_dell_utente(tmp_path):
    cartella, casa = tmp_path / "hooks", tmp_path / "casa"
    cartella.mkdir()
    shutil.copy2(HOOKS / "riga-stato.ps1", cartella)
    # riga dell'utente finta: rimanda indietro quello che riceve, con un prefisso
    (cartella / "riga-stato-utente.sh").write_text('printf "MIA RIGA "; cat\n', encoding="utf-8", newline="\n")
    r = _lancia(cartella, casa, "-Ponte")
    fuori = r.stdout.decode("utf-8")
    assert fuori.startswith("MIA RIGA ") and json.loads(fuori[len("MIA RIGA "):]) == DATI, r.stderr
    uso = json.loads((casa / ".claude" / "second-brain" / "uso.json").read_text(encoding="utf-8"))
    assert uso["five_hour"]["used_percentage"] == 41.5 and uso["seven_day"]["used_percentage"] == 9


@pytest.mark.skipif(sys.platform != "win32", reason="solo Windows")
def test_senza_ponte_la_riga_e_la_nostra(tmp_path):
    cartella, casa = tmp_path / "hooks", tmp_path / "casa"
    cartella.mkdir()
    shutil.copy2(HOOKS / "riga-stato.ps1", cartella)
    fuori = _lancia(cartella, casa).stdout.decode("utf-8")
    assert fuori.startswith("Opus") and "42%" in fuori and (casa / ".claude" / "second-brain" / "uso.json").is_file()
