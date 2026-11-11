import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "motore"))

import aggiornamenti as agg  # noqa: E402


def _rel(tag, prerelease=False, draft=False, nome=None, size=10, digest=None):
    nome = nome or f"Second.Brain.Studio.Setup.{tag}.exe"
    return {"tag_name": f"v{tag}", "prerelease": prerelease, "draft": draft, "body": "novità",
            "assets": [{"name": nome, "url": f"https://api/{tag}", "browser_download_url": f"https://dl/{tag}",
                        "size": size, "digest": digest}]}


def test_numeri():
    assert agg.numeri("2026.11.8.0317") == (2026, 11, 8, 317)
    assert agg.numeri("v2026.11.7.2237") == (2026, 11, 7, 2237)
    assert agg.numeri("sviluppo") is None


def test_release_pubbliche_disponibili_anche_con_token_scaduto(monkeypatch):
    chiamate = []
    def get(url, token, accetta, timeout=30):
        chiamate.append(token)
        if token:
            raise agg.urllib.error.HTTPError(url, 401, 'Unauthorized', {}, None)
        return _Risposta(b'[]')
    monkeypatch.setattr(agg, '_get', get)
    assert agg.leggi_release('scaduto') == [] and chiamate == ['scaduto', None]


def test_sceglie_la_piu_nuova():
    r = [_rel("2026.11.7.2237"), _rel("2026.11.8.0317"), _rel("2026.11.8.0900", prerelease=True)]
    assert agg.scegli(r, "2026.11.7.2237", prove=True)["versione"] == "2026.11.8.0900"
    assert agg.scegli(r, "2026.11.7.2237", prove=False)["versione"] == "2026.11.8.0317"


def test_niente_se_aggiornata_o_da_sorgente_o_bozza():
    r = [_rel("2026.11.8.0317"), _rel("2026.12.1.0000", draft=True)]
    assert agg.scegli(r, "2026.11.8.0317", prove=True) is None
    assert agg.scegli(r, "sviluppo", prove=True) is None


def test_ignora_allegati_che_non_sono_installer():
    r = [_rel("2026.11.9.0100", nome="sorgenti.zip")]
    assert agg.scegli(r, "2026.11.8.0317", prove=True) is None
    r = [_rel("2026.11.9.0100", nome="Second Brain Studio Setup 2026.11.9.0100.exe")]
    assert agg.scegli(r, "2026.11.8.0317", prove=True)["versione"] == "2026.11.9.0100"


class _Risposta:
    def __init__(self, dati): self.dati, self.pos = dati, 0
    def read(self, n=-1):
        pezzo = self.dati[self.pos:] if n < 0 else self.dati[self.pos:self.pos + n]
        self.pos += len(pezzo); return pezzo
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_controlla_scarica_verifica_e_scrive(tmp_path, monkeypatch):
    contenuto = b"installer finto" * 100
    sha = hashlib.sha256(contenuto).hexdigest()
    rel = [_rel("2026.11.9.0100", prerelease=True, size=len(contenuto), digest=f"sha256:{sha}")]
    chiamate = []

    def finto_get(url, token, accetta, timeout=30):
        chiamate.append((url, token))
        return _Risposta(json.dumps(rel).encode() if url == agg.API else contenuto)
    monkeypatch.setattr(agg, "_get", finto_get)
    esito = agg.controlla("2026.11.8.0317", True, "chiave", tmp_path)
    assert esito == {"nuova": "2026.11.9.0100"}
    d = json.loads((tmp_path / "aggiornamento.json").read_text(encoding="utf-8"))
    assert d["versione"] == "2026.11.9.0100" and Path(d["setup"]).read_bytes() == contenuto
    assert ("https://api/2026.11.9.0100", "chiave") in chiamate  # con la chiave passa dall'API


def test_sha_sbagliato_non_lascia_file(tmp_path, monkeypatch):
    rel = [_rel("2026.11.9.0100", size=3, digest="sha256:" + "0" * 64)]
    monkeypatch.setattr(agg, "_get", lambda url, token, accetta, timeout=30: _Risposta(json.dumps(rel).encode() if url == agg.API else b"abc"))
    try:
        agg.controlla("2026.11.8.0317", True, None, tmp_path)
        assert False, "doveva fallire"
    except ValueError:
        pass
    assert not (tmp_path / "aggiornamento.json").exists()
    assert not list((tmp_path / "aggiornamenti").glob("*"))


def test_script_aggiornamento_apici_e_scelte(tmp_path):
    s = agg.script_aggiornamento(123, r"C:\Users\d'Amico\Setup.exe", "2026.11.9.0001", True, Path(r"C:\App d'oggi"), tmp_path)
    assert r"'C:\Users\d''Amico\Setup.exe'" in s and r"'C:\App d''oggi'" in s   # apici raddoppiati
    assert "'/SILENT'" in s and "/NOAVVIO" not in s and "/FORCECLOSEAPPLICATIONS" in s
    assert "aggiornamento-errore.json" in s and "Get-Process -Id 123" in s
    s2 = agg.script_aggiornamento(1, "x.exe", "v", False, None, tmp_path)
    assert "'/VERYSILENT'" in s2 and "'/NOAVVIO'" in s2 and "$cartella = ''" in s2
