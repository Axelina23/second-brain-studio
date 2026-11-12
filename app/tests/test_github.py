import subprocess
import json
import time
from concurrent.futures import ThreadPoolExecutor
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


def _rebase_bloccato(tmp_path):
    # come il 2026-11-12: lo hook di fine sessione lascia un rebase in conflitto a meta'
    _, (a, b) = _ambiente(tmp_path)
    (a / "nota.md").write_text("base\n", encoding="utf-8")
    _gh(a).sincronizza(primo=True)
    git(b, "pull", "origin", "main")
    (a / "nota.md").write_text("versione A\n", encoding="utf-8")
    _gh(a).sincronizza()
    (b / "nota.md").write_text("versione B\n", encoding="utf-8")
    git(b, "commit", "-am", "auto: portatile")
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=b, capture_output=True)
    assert (b / ".git" / "rebase-merge").exists()
    return a, b


def test_rebase_a_meta_lasciato_da_altri(tmp_path):
    _, b = _rebase_bloccato(tmp_path)
    (b / "altra.md").write_text("nuova\n", encoding="utf-8")
    esito = _gh(b).sincronizza()
    # annullato, niente segni di conflitto nei commit, conflitto mostrato per farlo sistemare
    assert esito.get("conflitto") is True and esito["file"] == ["nota.md"]
    assert not (b / ".git" / "rebase-merge").exists()
    assert git(b, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert "<<<<<<<" not in git(b, "log", "-p", "-3")
    assert (b / "nota.md").read_text(encoding="utf-8") == "versione B\n"


def test_hook_annulla_rebase_a_meta(tmp_path, monkeypatch):
    _, b = _rebase_bloccato(tmp_path)
    casa = tmp_path / "casa"
    (casa / ".claude" / "second-brain").mkdir(parents=True)
    (casa / ".claude" / "second-brain" / "config.json").write_text(
        json.dumps({"radice": str(b)}), encoding="utf-8")
    hook = Path(__file__).resolve().parent.parent / "hooks" / "sync.ps1"
    monkeypatch.setenv("USERPROFILE", str(casa))
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(hook), "-Modo", "push"],
                   capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
    assert not (b / ".git" / "rebase-merge").exists()
    assert git(b, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert "<<<<<<<" not in git(b, "log", "-p", "-3")
    log = (casa / ".claude" / "second-brain" / "sync-ultimo.log").read_text(encoding="utf-8-sig")
    assert "CONFLITTO" in log


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


def test_rinnovo_sopravvive_al_riavvio_e_serializza_i_thread(tmp_path, monkeypatch):
    chiave = ChiaveFinta()
    prima = github.GitHub(tmp_path, chiave=chiave)
    prima._salva_accesso({"access_token": "vecchio", "refresh_token": "rinnovo", "expires_in": -1})
    chiamate = []
    def rinnova(url, dati=None, **kw):
        chiamate.append(dati)
        time.sleep(0.02)
        return {"access_token": "nuovo", "refresh_token": "nuovo-rinnovo", "expires_in": 28800}
    monkeypatch.setattr(github, "_richiesta", rinnova)
    seconda = github.GitHub(tmp_path, chiave=chiave)
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert list(pool.map(lambda _: seconda._token(), range(6))) == ["nuovo"] * 6
    assert len(chiamate) == 1 and chiamate[0]["grant_type"] == "refresh_token"
    terza = github.GitHub(tmp_path, chiave=chiave)
    assert terza._token() == "nuovo" and len(chiamate) == 1
    assert json.loads(chiave.v)["refresh_token"] == "nuovo-rinnovo"


def test_rinnovo_senza_rete_conserva_accesso_e_refresh(tmp_path, monkeypatch):
    chiave = ChiaveFinta()
    g = github.GitHub(tmp_path, chiave=chiave)
    g._salva_accesso({"access_token": "vecchio", "refresh_token": "rinnovo", "expires_in": -1})
    prima = chiave.v
    def rete(*a, **k):
        raise OSError("offline")
    monkeypatch.setattr(github, "_richiesta", rete)
    assert g._token() == "vecchio" and chiave.v == prima
    assert not g.rifiutato() and chiave.v == prima


def test_401_rinnova_anziche_scollegare(tmp_path, monkeypatch):
    g = github.GitHub(tmp_path, chiave=ChiaveFinta())
    g._salva_accesso({"access_token": "vecchio", "refresh_token": "rinnovo", "expires_in": 28800})
    def richiesta(url, dati=None, **kw):
        if dati:
            return {"access_token": "nuovo", "refresh_token": "rinnovo2", "expires_in": 28800}
        raise github.urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)
    monkeypatch.setattr(github, "_richiesta", richiesta)
    assert not g.rifiutato() and g._token() == "nuovo" and not g.scaduto


def test_risposta_401_vecchia_non_cancella_un_login_nuovo(tmp_path, monkeypatch):
    chiave = ChiaveFinta("vecchio")
    g = github.GitHub(tmp_path, chiave=chiave)
    def richiesta(url, **kw):
        chiave.set("nuovo")
        raise github.urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)
    monkeypatch.setattr(github, "_richiesta", richiesta)
    assert not g.rifiutato() and g._token() == "nuovo"


def test_refresh_revocato_richiede_accesso_solo_se_anche_token_rifiutato(tmp_path, monkeypatch):
    g = github.GitHub(tmp_path, chiave=ChiaveFinta())
    g._salva_accesso({"access_token": "vecchio", "refresh_token": "rinnovo", "expires_in": 28800})
    def richiesta(url, dati=None, **kw):
        if dati:
            return {"error": "bad_refresh_token"}
        raise github.urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)
    monkeypatch.setattr(github, "_richiesta", richiesta)
    assert g.rifiutato() and g._token() is None and g.scaduto
