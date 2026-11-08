import subprocess

import modello

RISPOSTE = {"nome": "Anna", "chi": "Studentessa di medicina a Bologna", "aree": "Università, Lavoro, Vita",
            "stile": "spiegato", "lingua": "italiano", "mai": ["comprare online"],
            "ruoli": [{"nome": "Archivista", "compito": "tiene in ordine gli appunti"}]}


def test_crea_struttura(tmp_path):
    r = modello.crea_struttura(tmp_path / "Brain", RISPOSTE)
    b = tmp_path / "Brain"
    assert r["ok"]
    for rel in ("CLAUDE.md", "INDICE.md", "Io/Regole.md", "Io/Profilo.md", "Università/stato.md",
                "Lavoro/stato.md", "Archivio/Registro.md", "Inbox/LEGGIMI.md", ".gitignore"):
        assert (b / rel).is_file(), rel
    regole = (b / "Io/Regole.md").read_text(encoding="utf-8")
    assert "passo per passo" in regole and "comprare online" in regole and "**Archivista**" in regole
    indice = (b / "INDICE.md").read_text(encoding="utf-8")
    assert "## Progetti attivi" in indice and "`Università/stato.md`" in indice
    log = subprocess.run(["git", "log", "--oneline"], cwd=b, capture_output=True, text=True).stdout
    assert "Primo avvio" in log


def test_crea_struttura_inglese(tmp_path):
    # interfaccia in inglese: cartelle, file e testi in inglese, niente nomi italiani
    r = {**RISPOSTE, "struttura": "en", "aree": "Work, Family", "lingua": "English", "stile": "spiegato"}
    modello.crea_struttura(tmp_path, r)
    for rel in ("CLAUDE.md", "INDEX.md", "Me/Rules.md", "Me/Profile.md", "Work/status.md", "Family/status.md",
                "Archive/Log.md", "System/tools.md", "Inbox/README.md", "Projects/.gitkeep"):
        assert (tmp_path / rel).is_file(), rel
    tutto = "\n".join(p.read_text(encoding="utf-8") for p in tmp_path.rglob("*.md"))
    for parola in ("INDICE", "Regole", "Progetti", "Archivio", "Registro", "stato.md", "Primo avvio"):
        assert parola not in tutto, parola
    regole = (tmp_path / "Me/Rules.md").read_text(encoding="utf-8")
    assert "answer in English, clear and explained step by step" in regole and "**Archivista**" in regole
    assert "## Active projects" in (tmp_path / "INDEX.md").read_text(encoding="utf-8")
    log = subprocess.run(["git", "log", "--oneline"], cwd=tmp_path, capture_output=True, text=True).stdout
    assert "First run" in log
    blocco = modello.blocco_claude(tmp_path)
    assert "/Me/Rules.md" in blocco and "/INDEX.md" in blocco and "Archive/Log.md" in blocco and "gestito" not in blocco
    p = modello.prompt_iniziale(r)
    assert p.startswith("Hi Anna!") and "Me/Profile.md" in p and "Work, Family" in p


def test_non_sovrascrive(tmp_path):
    (tmp_path / "Io").mkdir()
    (tmp_path / "Io" / "Regole.md").write_text("mie", encoding="utf-8")
    r = modello.crea_struttura(tmp_path, RISPOSTE, git=False)
    assert (tmp_path / "Io" / "Regole.md").read_text(encoding="utf-8") == "mie"
    assert "Io/Regole.md" not in r["creati"]


def test_aree_con_caratteri_strani(tmp_path):
    f = modello.testi({"aree": "a/b, <x>, ok"}, tmp_path)
    assert "ab/stato.md" in f and "x/stato.md" in f and "ok/stato.md" in f


def test_collega_claude_md(tmp_path):
    file = tmp_path / "CLAUDE.md"
    file.write_text("# mie istruzioni\n", encoding="utf-8")
    assert modello.collega_claude_md(tmp_path / "B1", file)["cambiato"]
    t = file.read_text(encoding="utf-8")
    assert t.count(modello.INIZIO) == 1 and "# mie istruzioni" in t and "B1/INDICE.md" in t
    assert "@" + tmp_path.as_posix().replace(" ", "\ ") in t
    assert list(tmp_path.glob("CLAUDE.md.prima-di-second-brain-*"))
    modello.collega_claude_md(tmp_path / "B2", file)
    t = file.read_text(encoding="utf-8")
    assert t.count(modello.INIZIO) == 1 and "B2/INDICE.md" in t and "B1" not in t and "# mie istruzioni" in t
    assert not modello.collega_claude_md(tmp_path / "B2", file)["cambiato"]


def test_prompt_iniziale():
    p = modello.prompt_iniziale(RISPOSTE)
    assert "Anna" in p and "Università" in p


def test_collega_hook(tmp_path):
    import json
    src = tmp_path / "src"
    src.mkdir()
    for n in ("sync.ps1", "fine-sessione.ps1", "riga-stato.ps1"):
        (src / n).write_text("#", encoding="utf-8")
    s = tmp_path / "settings.json"
    s.write_text(json.dumps({"hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": "altro.ps1"}]}]},
                             "statusLine": {"type": "command", "command": "mia.ps1"}}), encoding="utf-8")
    dest = tmp_path / "hooks"
    r = modello.collega_hook(src, dest, s)
    assert r["cambiato"] and not r["riga_stato"] and (dest / "sync.ps1").is_file()
    d = json.loads(s.read_text(encoding="utf-8"))
    assert len(d["hooks"]["SessionEnd"]) == 2 and d["statusLine"]["command"] == "mia.ps1"
    assert "sync.ps1" in d["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert not modello.collega_hook(src, dest, s)["cambiato"]  # idempotente
    assert len(json.loads(s.read_text(encoding="utf-8"))["hooks"]["SessionEnd"]) == 2


def test_collega_hook_senza_settings(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    r = modello.collega_hook(src, tmp_path / "h", tmp_path / "settings.json")
    assert r["cambiato"] and r["riga_stato"]


def test_import_con_spazi():
    from pathlib import Path
    assert "@C:/Users/x/Second\ Brain/INDICE.md" in modello.blocco_claude(Path(r"C:\Users\x\Second Brain"))


def test_solo_avvisi(tmp_path):
    import json
    src = tmp_path / "src"
    src.mkdir()
    (src / "avviso.ps1").write_text("#", encoding="utf-8")
    s = tmp_path / "settings.json"
    s.write_text(json.dumps({"statusLine": {"command": "mia"}}), encoding="utf-8")
    r = modello.collega_hook(src, tmp_path / "h", s, solo_avvisi=True)
    d = json.loads(s.read_text(encoding="utf-8"))
    assert r["cambiato"] and set(d["hooks"]) == {"Stop", "Notification"} and d["statusLine"]["command"] == "mia"
    assert "-Evento attesa" in d["hooks"]["Notification"][0]["hooks"][0]["command"]
