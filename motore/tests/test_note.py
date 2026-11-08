from datetime import datetime

import pytest

from note import salva_nota

ADESSO = datetime(2026, 11, 7, 16, 42)


def test_nome_da_haiku(tmp_path):
    p = salva_nota("Provare WezTerm", tmp_path, ADESSO, chiedi=lambda p, t: "WezTerm.")
    assert p.name == "2026-11-07 wezterm.md"


def test_nome_esistente(tmp_path):
    f = lambda p, t: "wezterm"
    salva_nota("a", tmp_path, ADESSO, chiedi=f)
    p = salva_nota("b", tmp_path, ADESSO, chiedi=f)
    assert p.name == "2026-11-07 wezterm-2.md"


@pytest.mark.parametrize("risp", [None, "due parole", "", "..."])
def test_ripiego(tmp_path, risp):
    p = salva_nota("x", tmp_path, ADESSO, chiedi=lambda p, t: risp)
    assert p.name == "2026-11-07 nota-1642.md"


def test_accenti_e_inbox_creata(tmp_path):
    p = salva_nota("x", tmp_path / "Inbox", ADESSO, chiedi=lambda p, t: "Città!")
    assert p.name == "2026-11-07 città.md"


def test_contenuto_utf8(tmp_path):
    p = salva_nota("Idea è bella", tmp_path, ADESSO, chiedi=lambda p, t: None)
    raw = p.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert raw.decode("utf-8") == "Idea è bella\n\n_Nota al volo, 2026-11-07 16:42_\n"


@pytest.mark.parametrize("t", ["", "   \n "])
def test_vuota(tmp_path, t):
    with pytest.raises(ValueError):
        salva_nota(t, tmp_path, ADESSO, chiedi=lambda p, t: "x")
    assert list(tmp_path.iterdir()) == []


def test_salva_subito_nome_di_ripiego(tmp_path):
    from note import salva_nota_subito
    p = salva_nota_subito("x", tmp_path, ADESSO)
    assert p.name == "2026-11-07 nota-1642.md"
    assert salva_nota_subito("y", tmp_path, ADESSO).name == "2026-11-07 nota-1642-2.md"


def test_rinomina(tmp_path):
    from note import rinomina_nota, salva_nota_subito
    p = salva_nota_subito("Provare WezTerm", tmp_path, ADESSO)
    nuovo = rinomina_nota(p, "Provare WezTerm", ADESSO, chiedi=lambda p, t: "WezTerm")
    assert nuovo.name == "2026-11-07 wezterm.md" and nuovo.exists() and not p.exists()


def test_rinomina_collisione(tmp_path):
    from note import rinomina_nota, salva_nota_subito
    (tmp_path / "2026-11-07 wezterm.md").write_text("altra", encoding="utf-8")
    p = salva_nota_subito("x", tmp_path, ADESSO)
    assert rinomina_nota(p, "x", ADESSO, chiedi=lambda p, t: "wezterm").name == "2026-11-07 wezterm-2.md"


def test_rinomina_senza_risposta_o_con_errore(tmp_path, monkeypatch):
    from pathlib import Path
    from note import rinomina_nota, salva_nota_subito
    p = salva_nota_subito("x", tmp_path, ADESSO)
    assert rinomina_nota(p, "x", ADESSO, chiedi=lambda p, t: None) == p

    def rotto(self, dest):
        raise OSError("bloccato")
    monkeypatch.setattr(Path, "rename", rotto)
    assert rinomina_nota(p, "x", ADESSO, chiedi=lambda p, t: "nome") == p and p.exists()
