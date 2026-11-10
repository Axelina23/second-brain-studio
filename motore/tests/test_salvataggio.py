import os
import time
from datetime import datetime

import salvataggio
from sessioni import Sessione


def _s(dim):
    return Sessione("abc", None, datetime.now(), dim, "", "")


def test_stati(tmp_path):
    assert salvataggio.stato_salvataggio(_s(1000), tmp_path) == "breve"
    assert salvataggio.stato_salvataggio(_s(40000), tmp_path) == "non_salvata"
    (tmp_path / "abc.in-corso").write_text("")
    assert salvataggio.stato_salvataggio(_s(40000), tmp_path) == "in_corso"
    vecchio = time.time() - 20 * 60
    os.utime(tmp_path / "abc.in-corso", (vecchio, vecchio))
    assert salvataggio.stato_salvataggio(_s(40000), tmp_path) == "non_salvata"
    (tmp_path / "abc.salvata").write_text("")
    assert salvataggio.stato_salvataggio(_s(40000), tmp_path) == "salvata"


def _sess(dim, ultima):
    return Sessione("abc", None, ultima, dim, "", "")


def test_attivazione(tmp_path):
    (tmp_path / "attivazione").write_text("2026-11-07T03:54:39+01:00", encoding="utf-8")
    prima = datetime(2026, 11, 6, 12, 0)
    dopo = datetime(2026, 11, 7, 10, 0)
    assert salvataggio.stato_salvataggio(_sess(40000, prima), tmp_path) == "salvata"
    assert salvataggio.stato_salvataggio(_sess(40000, dopo), tmp_path) == "non_salvata"
    assert salvataggio.stato_salvataggio(_sess(1000, prima), tmp_path) == "breve"


def test_attivazione_malformata(tmp_path):
    (tmp_path / "attivazione").write_text("boh", encoding="utf-8")
    assert salvataggio.stato_salvataggio(_sess(40000, datetime(2020, 1, 1)), tmp_path) == "non_salvata"


def test_salvata_vecchia_con_sessione_ripresa(tmp_path):
    ultima = datetime.now()
    (tmp_path / "abc.salvata").write_text("")
    vecchio = time.time() - 3600
    os.utime(tmp_path / "abc.salvata", (vecchio, vecchio))
    assert salvataggio.stato_salvataggio(_sess(40000, ultima), tmp_path) == "non_salvata"
    (tmp_path / "abc.salvata").write_text("x")  # segno fresco
    assert salvataggio.stato_salvataggio(_sess(40000, ultima), tmp_path) == "salvata"


def test_in_corso_vecchio_con_sessione_ripresa(tmp_path):
    (tmp_path / "abc.in-corso").write_text("")
    vecchio = time.time() - 5 * 60  # giovane (< 15 min) ma anteriore all'ultima attivita'
    os.utime(tmp_path / "abc.in-corso", (vecchio, vecchio))
    assert salvataggio.stato_salvataggio(_sess(40000, datetime.now()), tmp_path) == "non_salvata"


def test_fallimento_e_nuovo_tentativo(tmp_path):
    s = _s(40000)
    errore = tmp_path / "abc.errore"
    errore.touch()
    os.utime(errore, (time.time() - 5, time.time() - 5))
    assert salvataggio.stato_salvataggio(s, tmp_path) == "errore_salvataggio"
    (tmp_path / "abc.in-corso").touch()
    assert salvataggio.stato_salvataggio(s, tmp_path) == "in_corso"
    (tmp_path / "abc.salvata").touch()
    assert salvataggio.stato_salvataggio(s, tmp_path) == "salvata"
