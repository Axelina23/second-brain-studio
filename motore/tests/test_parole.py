from datetime import datetime
from pathlib import Path

from parole import aggiorna_parole, parole_chiave, ripiego
from sessioni import Sessione


def sess(id="a", dim=50_000, n=5, primo="Come configuro il wifi?\nAltra riga", testo="testo"):
    return Sessione(id, Path(f"{id}.jsonl"), datetime.now().astimezone(), dim, primo, testo, n)


class Finto:
    def __init__(self, risposta="Dispositivi wifi, interfaccia"):
        self.risposta = risposta
        self.chiamate = []

    def __call__(self, prompt, timeout=60):
        self.chiamate.append(prompt)
        return self.risposta


def test_cache_per_mtime(tmp_path):
    cache = tmp_path / "parole.json"
    f = Finto()
    aggiorna_parole([sess()], cache, f)
    assert len(f.chiamate) == 1
    aggiorna_parole([sess()], cache, f)
    assert len(f.chiamate) == 1
    aggiorna_parole([sess(dim=60_000)], cache, f)
    assert len(f.chiamate) == 2


def test_haiku_fallisce(tmp_path):
    cache = tmp_path / "parole.json"
    f = Finto(None)
    s = sess()
    aggiorna_parole([s], cache, f)
    assert parole_chiave(s, cache) is None
    assert not cache.exists() or "a" not in cache.read_text(encoding="utf-8")
    assert ripiego(s) == "Come configuro il wifi?"


def test_formato(tmp_path):
    cache = tmp_path / "parole.json"
    s = sess()
    aggiorna_parole([s], cache, Finto("Dispositivi wifi, interfaccia SecondBrain\n"))
    assert parole_chiave(s, cache) == "dispositivi wifi · interfaccia SecondBrain"


def test_formato_limiti(tmp_path):
    cache = tmp_path / "parole.json"
    s = sess()
    aggiorna_parole([s], cache, Finto("a, b, c, d, " + "x" * 80))
    assert parole_chiave(s, cache) == "a · b · c"
    aggiorna_parole([sess("b")], cache, Finto("y" * 100))
    assert len(parole_chiave(sess("b"), cache)) <= 60


def test_sessioni_piccole_non_chiamate(tmp_path):
    cache = tmp_path / "parole.json"
    f = Finto()
    aggiorna_parole([sess(dim=1000, n=2), sess("b", dim=1000, n=3), sess("c", dim=40_000, n=1)], cache, f)
    assert len(f.chiamate) == 2


def test_ripiego_lungo():
    assert len(ripiego(sess(primo="x" * 200))) <= 50


def test_cache_corrotta(tmp_path):
    cache = tmp_path / "parole.json"
    cache.write_text("{rotto", encoding="utf-8")
    assert parole_chiave(sess(), cache) is None
    aggiorna_parole([sess()], cache, Finto())
    assert parole_chiave(sess(), cache) is not None


def test_eccezione_non_ferma_il_giro(tmp_path):
    cache = tmp_path / "parole.json"

    def chiedi(prompt, timeout=60):
        if "BOOM" in prompt:
            raise RuntimeError("x")
        return "uno, due"

    aggiorna_parole([sess("a", testo="BOOM"), sess("b")], cache, chiedi)
    assert parole_chiave(sess("a"), cache) is None
    assert parole_chiave(sess("b"), cache) == "uno · due"


def test_salvataggio_fallito_pulisce_tmp(tmp_path, monkeypatch):
    import parole
    cache = tmp_path / "parole.json"

    def replace(a, b):
        raise PermissionError

    monkeypatch.setattr(parole.os, "replace", replace)
    monkeypatch.setattr(parole.time, "sleep", lambda s: None)
    aggiorna_parole([sess("a"), sess("b")], cache, Finto())
    assert list(tmp_path.glob("*.tmp")) == []
