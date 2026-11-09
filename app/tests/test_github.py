import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import github  # noqa: E402


class ChiaveFinta:
    def __init__(self, v=None): self.v = v
    def get(self): return self.v
    def set(self, v): self.v = v


def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def _ambiente(tmp_path):
    # remoto locale (bare) e due copie, come due PC
    remoto = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remoto)], check=True, capture_output=True)
    copie = []
    for nome in ("fisso", "portatile"):
        c = tmp_path / nome
        c.mkdir()
        git(c, "init", "-b", "main")
        git(c, "config", "user.email", "t@t"); git(c, "config", "user.name", "t")
        git(c, "remote", "add", "origin", str(remoto))
        copie.append(c)
    return remoto, copie


def _gh(c):
    g = github.GitHub(c, chiave=ChiaveFinta())
    g.repo = lambda: "utente/second-brain"
    return g


def test_repo_da_remote(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "remote", "add", "origin", "https://github.com/utente-prova/second-brain.git")
    assert github.GitHub(tmp_path, chiave=ChiaveFinta()).repo() == "utente-prova/second-brain"


def test_sincronizza_tra_due_pc(tmp_path):
    _, (a, b) = _ambiente(tmp_path)
    (a / "nota.md").write_text("ciao", encoding="utf-8")
    assert _gh(a).sincronizza(primo=True)["ok"]
    git(b, "pull", "origin", "main")
    (b / "nota.md").write_text("ciao dal portatile", encoding="utf-8")
    esito = _gh(b).sincronizza()
    assert esito == {"ok": True, "salvati": 1}
    assert _gh(a).sincronizza()["ok"]
    assert (a / "nota.md").read_text(encoding="utf-8") == "ciao dal portatile"


def test_conflitto_si_ferma_senza_rompere(tmp_path):
    _, (a, b) = _ambiente(tmp_path)
    (a / "nota.md").write_text("base\n", encoding="utf-8")
    _gh(a).sincronizza(primo=True)
    git(b, "pull", "origin", "main")
    (a / "nota.md").write_text("versione A\n", encoding="utf-8")
    _gh(a).sincronizza()
    (b / "nota.md").write_text("versione B\n", encoding="utf-8")
    esito = _gh(b).sincronizza()
    assert esito.get("conflitto") is True
    assert not (b / ".git" / "rebase-merge").exists()  # nessun rebase lasciato a meta'
    assert (b / "nota.md").read_text(encoding="utf-8") == "versione B\n"


def test_senza_repository(tmp_path):
    git(tmp_path, "init", "-b", "main")
    assert "errore" in github.GitHub(tmp_path, chiave=ChiaveFinta()).sincronizza()


def _http(codice):
    def solleva(*a, **k):
        raise github.urllib.error.HTTPError("https://api.github.com/user", codice, "x", {}, None)
    return solleva


def test_chiave_rifiutata_da_git(tmp_path, monkeypatch):
    # GitHub revoca la chiave (anche /user la rifiuta): toglie la chiave e chiede di ricollegare
    monkeypatch.setattr(github, "_richiesta", _http(401))
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    eventi = []
    g = github.GitHub(tmp_path, chiave=ChiaveFinta("gho_revocata"), emetti=lambda n, d: eventi.append(d))
    g.repo = lambda: "utente/second-brain"
    g._utente = "utente"  # niente chiamata a /user nel test
    fallito = subprocess.CompletedProcess([], 128, "", "remote: Invalid username or token.\nfatal: Authentication failed")
    originale = g._git
    g._git = lambda *a, **k: fallito if a[0] in ("pull", "push") else originale(*a, **k)
    esito = g.sincronizza()
    assert esito.get("scaduto") is True
    assert g._token() is None and g.scaduto
    assert any(e.get("esito") == "accesso_scaduto" for e in eventi)


def test_401_isolato_non_toglie_la_chiave(tmp_path, monkeypatch):
    # una chiamata ha 401 ma /user accetta la chiave: si tiene e si scrive nel registro
    monkeypatch.setattr(github, "_richiesta", lambda *a, **k: {"login": "utente"})
    note = []
    g = github.GitHub(tmp_path, chiave=ChiaveFinta("gho_buona"), nota=note.append)
    assert g.rifiutato("chat degli altri PC", "401 passeggero") is False
    assert g._token() == "gho_buona" and not g.scaduto
    assert "chat degli altri PC" in note[0] and "tenuta" in note[0] and "gho_buona" not in note[0]


def test_401_con_rete_assente_non_toglie_la_chiave(tmp_path, monkeypatch):
    def senza_rete(*a, **k):
        raise OSError("rete")
    monkeypatch.setattr(github, "_richiesta", senza_rete)
    g = github.GitHub(tmp_path, chiave=ChiaveFinta("gho_buona"))
    assert g.rifiutato("aggiornamenti") is False and g._token() == "gho_buona"


def test_git_rifiutato_per_un_momento(tmp_path, monkeypatch):
    # git dice "Authentication failed" ma la chiave e' valida: niente "ricollega"
    monkeypatch.setattr(github, "_richiesta", lambda *a, **k: {"login": "utente"})
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    g = github.GitHub(tmp_path, chiave=ChiaveFinta("gho_buona"))
    g.repo = lambda: "utente/second-brain"
    g._utente = "utente"
    fallito = subprocess.CompletedProcess([], 128, "", "fatal: Authentication failed")
    originale = g._git
    g._git = lambda *a, **k: fallito if a[0] in ("pull", "push") else originale(*a, **k)
    esito = g.sincronizza()
    assert "scaduto" not in esito and "momento" in esito["errore"] and g._token() == "gho_buona"


def test_stato_con_chiave_revocata(tmp_path, monkeypatch):
    git(tmp_path, "init", "-b", "main")
    def rifiuta(*a, **k):
        raise github.urllib.error.HTTPError("https://api.github.com/user", 401, "Unauthorized", {}, None)
    monkeypatch.setattr(github, "_richiesta", rifiuta)
    g = github.GitHub(tmp_path, chiave=ChiaveFinta("gho_revocata"))
    s = g.stato()
    assert s["collegato"] is False and s["scaduto"] is True and g._token() is None


def test_stato_senza_chiave(tmp_path):
    git(tmp_path, "init", "-b", "main")
    s = github.GitHub(tmp_path, chiave=ChiaveFinta()).stato()
    assert s["collegato"] is False and s["repo"] is None
