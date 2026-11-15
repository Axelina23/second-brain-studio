import base64
import io
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import inbox_import as imp

ADESSO = datetime(2026, 11, 15, 15, 42, 30)


def test_incolla_pixel_e_duplicati(tmp_path, monkeypatch):
    monkeypatch.setattr(imp.ImageGrab, "grabclipboard", lambda: Image.new("RGB", (30, 20), "red"))
    uno = imp.incolla_immagine(tmp_path, ADESSO)
    due = imp.incolla_immagine(tmp_path, ADESSO)
    assert uno["aggiunti"] == ["2026-11-15 screenshot 154230.png"]
    assert due["aggiunti"] == ["2026-11-15 screenshot 154230-2.png"]
    with Image.open(tmp_path / uno["aggiunti"][0]) as im:
        assert im.size == (30, 20)
        assert im.getpixel((0, 0)) == (255, 0, 0)
    assert imp.miniatura(tmp_path / uno["aggiunti"][0]).startswith("data:image/jpeg;base64,")


def test_incolla_browser_e_rifiuta_file_o_testo(tmp_path, monkeypatch):
    out = io.BytesIO()
    Image.new("RGBA", (12, 8), "blue").save(out, "PNG")
    r = imp.incolla_immagine(tmp_path, ADESSO, base64.b64encode(out.getvalue()).decode())
    assert len(r["aggiunti"]) == 1
    for valore in (None, ["un-file.pdf"]):
        monkeypatch.setattr(imp.ImageGrab, "grabclipboard", lambda: valore)
        assert "errore" in imp.incolla_immagine(tmp_path, ADESSO)
    for dati in ("!!!", "bm9uIHVuJ2ltbWFnaW5l", "a" * (40 * 1024 * 1024 + 1)):
        assert "errore" in imp.incolla_immagine(tmp_path, ADESSO, dati)
    assert len(list(tmp_path.iterdir())) == 1


def test_invii_concorrenti_non_sovrascrivono_originali(tmp_path):
    sorgente = tmp_path / "dati con spazi è.txt"
    sorgente.write_text("prova", encoding="utf-8")
    inbox = tmp_path / "Inbox"
    with ThreadPoolExecutor(max_workers=4) as pool:
        risultati = list(pool.map(lambda _: imp.copia_file(inbox, [str(sorgente)], ADESSO), range(8)))
    assert len({r["aggiunti"][0] for r in risultati}) == 8
    assert sorgente.read_text(encoding="utf-8") == "prova"
    assert all(p.read_text(encoding="utf-8") == "prova" for p in inbox.iterdir())
    r = imp.copia_file(inbox, [str(tmp_path), str(tmp_path / "assente.pdf")], ADESSO)
    assert len(r["saltati"]) == 2


def test_errore_scrittura_non_lascia_file_vuoto(tmp_path):
    def fallisce(f):
        f.write(b"parziale")
        raise OSError("disco pieno")
    import pytest
    with pytest.raises(OSError):
        imp.scrivi_unico(tmp_path, "prova.txt", fallisce)
    assert not list(tmp_path.iterdir())
