# Test del semaforo di sincronizzazione: repo git veri in tmp_path (bare + cloni).
import base64
import subprocess
from pathlib import Path

import pytest

from sync import ambiente_git, stato_sync


def test_ambiente_con_chiave_spegne_il_gestore_credenziali():
    env = ambiente_git("gho_prova")
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_CONFIG_KEY_1"] == "credential.helper" and env["GIT_CONFIG_VALUE_1"] == ""
    atteso = base64.b64encode(b"x-access-token:gho_prova").decode()
    assert env["GIT_CONFIG_VALUE_0"] == f"AUTHORIZATION: basic {atteso}"


def test_ambiente_senza_chiave_lascia_le_credenziali_del_pc():
    assert "GIT_CONFIG_COUNT" not in ambiente_git(None) or ambiente_git(None)["GIT_CONFIG_COUNT"] != "2"


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   text=True, encoding="utf-8")


def clona(remoto, dest):
    git(remoto.parent, "clone", "-q", str(remoto), str(dest))
    git(dest, "config", "user.name", "T")
    git(dest, "config", "user.email", "t@t.it")
    return dest


def commit(repo, nome, testo="x"):
    (repo / nome).write_text(testo, encoding="utf-8")
    git(repo, "add", nome)
    git(repo, "commit", "-q", "-m", nome)


@pytest.fixture
def coppia(tmp_path):
    remoto = tmp_path / "remoto.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remoto))
    a = clona(remoto, tmp_path / "a")
    commit(a, "base.txt")
    git(a, "push", "-q", "-u", "origin", "HEAD:main")
    git(a, "branch", "-q", "-u", "origin/main")
    b = clona(remoto, tmp_path / "b")
    return a, b


def test_verde(coppia):
    assert stato_sync(coppia[0]) == "verde"


def test_giallo_non_committato(coppia):
    (coppia[0] / "base.txt").write_text("modificato", encoding="utf-8")
    assert stato_sync(coppia[0]) == "giallo"


def test_giallo_file_nuovo(coppia):
    (coppia[0] / "nuovo.txt").write_text("n", encoding="utf-8")
    assert stato_sync(coppia[0]) == "giallo"


def test_giallo_non_pushato(coppia):
    commit(coppia[0], "locale.txt")
    assert stato_sync(coppia[0]) == "giallo"


def test_rosso(coppia):
    a, b = coppia
    commit(b, "remoto.txt")
    git(b, "push", "-q", "origin", "HEAD:main")
    assert stato_sync(a) == "rosso"


def test_rosso_vince(coppia):
    a, b = coppia
    commit(b, "remoto.txt")
    git(b, "push", "-q", "origin", "HEAD:main")
    commit(a, "locale.txt")
    (a / "base.txt").write_text("sporco", encoding="utf-8")
    assert stato_sync(a) == "rosso"


def test_grigio_senza_upstream(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q")
    git(r, "config", "user.name", "T")
    git(r, "config", "user.email", "t@t.it")
    commit(r, "a.txt")
    assert stato_sync(r) == "grigio"


def test_grigio_non_repo(tmp_path):
    assert stato_sync(tmp_path) == "grigio"


def test_grigio_cartella_inesistente(tmp_path):
    assert stato_sync(tmp_path / "non-esiste") == "grigio"


def test_grigio_remoto_irraggiungibile(coppia, tmp_path):
    a = coppia[0]
    git(a, "remote", "set-url", "origin", str(tmp_path / "non-esiste.git"))
    assert stato_sync(a) == "grigio"
