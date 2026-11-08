import json
import sys
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import altri_pc  # noqa: E402
from altri_pc import AltriPC, _Risposta  # noqa: E402

ADESSO = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def _voce(i, ore=1, stato="salvata", **extra):
    return {"id": f"c{i}", "etichetta": f"chat {i}", "ultima": (ADESSO - timedelta(hours=ore)).isoformat(),
            "stato": stato, "messaggi": 3, "dimensione": 100, "primo": "testo segreto", **extra}


def test_riepilogo_senza_testo_e_limitato(monkeypatch):
    monkeypatch.setenv("COMPUTERNAME", "fisso")
    voci = [_voce(i, ore=i) for i in range(150)] + [_voce(999, ore=24 * 40)]
    r = altri_pc.riepilogo(voci, "2026.11.8.0317", adesso=ADESSO.timestamp())
    assert r["pc"] == "FISSO" and r["formato"] == 1 and r["battito"] == int(ADESSO.timestamp())
    assert len(r["chat"]) == altri_pc.MAX_CHAT
    assert "testo segreto" not in json.dumps(r)
    assert all(c["id"] != "c999" for c in r["chat"])  # oltre 30 giorni
    assert r["chat"][0]["id"] == "c0"  # piu' recente prima


def test_riepilogo_all_uscita_niente_aperte():
    voci = [_voce(1, stato="aperta", stato_salvataggio="salvata"), _voce(2, stato="aperta")]
    r = altri_pc.riepilogo(voci, "v", adesso=ADESSO.timestamp(), uscita=True)
    assert [c["stato"] for c in r["chat"]] == ["salvata", "non_salvata"]


def test_per_interfaccia_acceso_spento_nascosto():
    t = ADESSO.timestamp()
    remoti = {"A": {"formato": 1, "pc": "A", "battito": t - 30, "chat": []},
              "B": {"formato": 1, "pc": "B", "battito": t - 3600, "chat": []},
              "C": {"formato": 1, "pc": "C", "battito": t - 40 * 86400, "chat": []},
              "D": {"formato": 99, "pc": "D", "battito": t, "chat": []}}
    e = altri_pc.per_interfaccia(remoti, adesso=t)
    assert [(d["pc"], d["acceso"]) for d in e] == [("A", True), ("B", False)]


class Finto(AltriPC):
    def __init__(self, risposte):
        super().__init__(lambda: "chiave", lambda: "io/second-brain")
        self.pc = "PORTATILE"
        self.chiamate, self.risposte = [], risposte

    def _chiedi(self, metodo, percorso, dati=None, etag=None, grezzo=False):
        self.chiamate.append((metodo, percorso, dati, etag))
        for (m, inizio), r in self.risposte.items():
            if m == metodo and percorso.startswith(inizio):
                return r(dati, etag) if callable(r) else r
        raise AssertionError(f"chiamata inattesa {metodo} {percorso}")


def test_pubblica_un_commit_senza_genitori_e_non_ripete():
    f = Finto({("POST", "/repos/io/second-brain/git/trees"): _Risposta(201, {"sha": "albero"}, None),
               ("POST", "/repos/io/second-brain/git/commits"): _Risposta(201, {"sha": "commit"}, None),
               ("PATCH", "/repos/io/second-brain/git/refs/heads/stato/PORTATILE"): _Risposta(200, {}, None)})
    r = altri_pc.riepilogo([_voce(1)], "v", adesso=ADESSO.timestamp())
    assert f.pubblica(r) is True
    commit = [c for c in f.chiamate if c[1].endswith("/git/commits")][0]
    assert commit[2]["parents"] == [] and commit[2]["tree"] == "albero"
    albero = [c for c in f.chiamate if c[1].endswith("/git/trees")][0]
    assert albero[2]["tree"][0]["path"] == "PORTATILE.json"
    n = len(f.chiamate)
    assert f.pubblica({**r, "battito": r["battito"] + 5}) is False  # stesso contenuto, battito recente
    assert len(f.chiamate) == n


def test_pubblica_crea_il_ramo_la_prima_volta():
    def manca(dati, etag):
        raise urllib.error.HTTPError("u", 422, "Reference does not exist", {}, None)
    f = Finto({("POST", "/repos/io/second-brain/git/trees"): _Risposta(201, {"sha": "a"}, None),
               ("POST", "/repos/io/second-brain/git/commits"): _Risposta(201, {"sha": "c"}, None),
               ("PATCH", "/repos/io/second-brain/git/refs/"): manca,
               ("POST", "/repos/io/second-brain/git/refs"): _Risposta(201, {}, None)})
    assert f.pubblica(altri_pc.riepilogo([], "v")) is True
    assert any(c[0] == "POST" and c[1].endswith("/git/refs") and c[2]["ref"] == "refs/heads/stato/PORTATILE" for c in f.chiamate)


def test_leggi_salta_il_proprio_ramo_usa_etag_e_toglie_i_rami_spariti():
    t = ADESSO.timestamp()
    fisso = {"formato": 1, "pc": "FISSO", "battito": t, "chat": [{"id": "x", "stato": "aperta"}]}
    refs = [{"ref": "refs/heads/stato/PORTATILE", "object": {"sha": "mio"}},
            {"ref": "refs/heads/stato/FISSO", "object": {"sha": "s1"}}]
    f = Finto({("GET", "/repos/io/second-brain/git/matching-refs/heads/stato/"): _Risposta(200, refs, '"e1"'),
               ("GET", "/repos/io/second-brain/contents/FISSO.json"): _Risposta(200, fisso, None)})
    assert f.leggi() is True and f.remoti == {"FISSO": fisso}
    assert not any("PORTATILE.json" in c[1] for c in f.chiamate)
    # nessun cambiamento: GitHub risponde 304 e non si scarica niente
    f.risposte[("GET", "/repos/io/second-brain/git/matching-refs/heads/stato/")] = lambda d, etag: _Risposta(304, None, etag)
    n = len(f.chiamate)
    assert f.leggi() is False and f.chiamate[-1][3] == '"e1"' and len(f.chiamate) == n + 1
    # ramo di FISSO cancellato
    f.risposte[("GET", "/repos/io/second-brain/git/matching-refs/heads/stato/")] = _Risposta(200, refs[:1], '"e2"')
    assert f.leggi() is True and f.remoti == {}


def test_senza_repository_non_fa_niente():
    f = AltriPC(lambda: "chiave", lambda: None)
    assert f.pubblica(altri_pc.riepilogo([], "v")) is False and f.leggi() is False
