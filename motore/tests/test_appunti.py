# Test dell'elenco appunti su un albero finto in tmp_path.
from datetime import datetime, timedelta, timezone

from appunti import colore, elenca_appunti, eta


def scrivi(radice, rel, testo="x"):
    p = radice / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(testo, encoding="utf-8")


def albero(r):
    scrivi(r, "Io/Profilo.md")
    scrivi(r, "Università/stato.md")
    scrivi(r, "Vita/Hobby.md")
    scrivi(r, "Sistema/strumenti.md")
    scrivi(r, "Progetti/X/CLAUDE.md")
    scrivi(r, "Progetti/Personali.md")
    scrivi(r, "Progetti/README.md")
    scrivi(r, "Archivio/Registro.md")
    scrivi(r, "INDICE.md", "- Abbandonato, non proporlo: **VecchioProgetto** → `Progetti/D/CLAUDE.md`\n")
    scrivi(r, "Progetti/X/Output/a.md")
    scrivi(r, "Università/LSO/a.md")
    scrivi(r, "Archivio/vecchio.md")


def test_gruppi(tmp_path):
    albero(tmp_path)
    coppie = {(a.gruppo, a.nome) for a in elenca_appunti(tmp_path)}
    assert coppie == {
        ("Io", "Profilo"), ("Università", "stato"), ("Vita", "Hobby"),
        ("Sistema", "strumenti"), ("Progetti", "X"), ("Progetti", "Personali"),
        ("Generali", "Registro"), ("Generali", "INDICE"),
    }


def test_esclusi(tmp_path):
    albero(tmp_path)
    nomi = {a.percorso.name for a in elenca_appunti(tmp_path)}
    assert "a.md" not in nomi and "vecchio.md" not in nomi and "README.md" not in nomi


def test_abbandonati(tmp_path):
    scrivi(tmp_path, "INDICE.md", "- Abbandonato, non proporlo: **VecchioProgetto** → `x`\n")
    scrivi(tmp_path, "Progetti/VecchioProgetto/CLAUDE.md")
    scrivi(tmp_path, "Progetti/Altro/CLAUDE.md")
    ab = {a.nome: a.abbandonato for a in elenca_appunti(tmp_path) if a.gruppo == "Progetti"}
    assert ab == {"VecchioProgetto": True, "Altro": False}


def test_aree_qualsiasi(tmp_path):
    # le aree scelte nel primo avvio (Lavoro, Famiglia...) compaiono senza essere in un elenco fisso
    scrivi(tmp_path, "INDICE.md")
    scrivi(tmp_path, "Lavoro/stato.md")
    scrivi(tmp_path, "Inbox/nota.md")
    scrivi(tmp_path, ".git/x.md")
    coppie = {(a.gruppo, a.nome) for a in elenca_appunti(tmp_path)}
    assert coppie == {("Lavoro", "stato"), ("Generali", "INDICE")}


def test_struttura_inglese(tmp_path):
    scrivi(tmp_path, "INDEX.md", "- Abandoned, don't suggest: **Old** → `Projects/Old/CLAUDE.md`\n")
    scrivi(tmp_path, "Me/Rules.md")
    scrivi(tmp_path, "System/tools.md")
    scrivi(tmp_path, "Work/status.md")
    scrivi(tmp_path, "Projects/Old/CLAUDE.md")
    scrivi(tmp_path, "Projects/New/CLAUDE.md")
    scrivi(tmp_path, "Projects/Personal.md")
    scrivi(tmp_path, "Archive/Log.md")
    scrivi(tmp_path, "Archive/old.md")
    elenco = elenca_appunti(tmp_path)
    assert {(a.gruppo, a.nome) for a in elenco} == {
        ("Io", "Rules"), ("Sistema", "tools"), ("Work", "status"), ("Progetti", "Old"), ("Progetti", "New"),
        ("Progetti", "Personal"), ("Generali", "Log"), ("Generali", "INDEX")}
    assert {a.nome: a.abbandonato for a in elenco if a.gruppo == "Progetti"} == {"Old": True, "New": False, "Personal": False}


def test_colore_soglie():
    assert colore(6.9) == "verde"
    assert colore(7) == "giallo"
    assert colore(14) == "giallo"
    assert colore(14.1) == "rosso"


def test_accenti(tmp_path):
    scrivi(tmp_path, "Università/stato.md", "è")
    a = elenca_appunti(tmp_path)
    assert a[0].gruppo == "Università" and a[0].modificato.tzinfo is not None


def test_eta():
    ora = datetime.now(timezone.utc)
    assert eta(ora - timedelta(hours=5), ora) == "oggi"
    assert eta(ora - timedelta(hours=30), ora) == "ieri"
    assert eta(ora - timedelta(days=9, hours=1), ora) == "9 g"
