import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ponte  # noqa: E402


def _radice(tmp_path: Path) -> Path:
    r = tmp_path / "brain"
    (r / "Io").mkdir(parents=True)
    (r / "Io" / "Regole.md").write_text("# Regole\nstile conciso", encoding="utf-8")
    (r / "Progetti" / "Alfa").mkdir(parents=True)
    (r / "Progetti" / "Alfa" / "CLAUDE.md").write_text("# Alfa\nstato del progetto alfa", encoding="utf-8")
    (r / "Inbox").mkdir()
    (r / "Inbox" / "2026-11-07 idea.md").write_text("un'idea", encoding="utf-8")
    (r / "INDICE.md").write_text("## Progetti attivi\n- **Alfa** → `Progetti/Alfa/CLAUDE.md`\n", encoding="utf-8")
    return r


def _sessione(cartella: Path, sid: str, testo: str, quando: datetime, gonfia: int = 0):
    cartella.mkdir(parents=True, exist_ok=True)
    righe = [{"type": "user", "entrypoint": "cli", "timestamp": quando.isoformat(),
              "message": {"content": testo}}]
    corpo = "\n".join(json.dumps(r) for r in righe) + "\n" + (" " * gonfia)
    (cartella / f"{sid}.jsonl").write_text(corpo, encoding="utf-8")


def _ponte(tmp_path):
    r = _radice(tmp_path)
    p = ponte.Ponte(radice=r, cartella_sessioni=tmp_path / "sessioni", cache=tmp_path / "cache",
                    segni=tmp_path / "segni", chiedi=lambda *a, **k: None)
    return p, r


def test_saluto_e_data():
    assert ponte.saluto(10) == "Buongiorno"
    assert ponte.saluto(15) == "Buon pomeriggio"
    assert ponte.saluto(21) == "Buonasera"
    assert ponte.data_lunga(datetime(2026, 11, 7)) == "Sabato 7 novembre"


def test_leggi_e_scrivi_con_conflitto(tmp_path):
    p, r = _ponte(tmp_path)
    d = p.leggi("Io/Regole.md")
    assert d["testo"].startswith("# Regole")
    ok = p.scrivi("Io/Regole.md", "# Regole\nnuovo", d["mtime"])
    assert ok.get("ok")
    vecchio = p.scrivi("Io/Regole.md", "altro", d["mtime"] - 100)
    assert vecchio.get("conflitto")
    assert (r / "Io" / "Regole.md").read_text(encoding="utf-8") == "# Regole\nnuovo"


def test_percorsi_fuori_dal_second_brain_rifiutati(tmp_path):
    p, _ = _ponte(tmp_path)
    (tmp_path / "segreto.md").write_text("x", encoding="utf-8")
    assert "errore" in p.leggi("../segreto.md")
    assert "errore" in p.scrivi("../segreto.md", "y", None)
    assert "errore" in p.leggi("Io/eseguibile.exe")


def test_cerca(tmp_path):
    p, _ = _ponte(tmp_path)
    r = p.cerca("progetto alfa")
    assert r["risultati"] and r["risultati"][0]["nome"] == "Alfa"
    assert p.cerca("x")["risultati"] == []


def test_home_avvisi_non_salvate_e_inbox(tmp_path):
    p, _ = _ponte(tmp_path)
    vecchia = datetime.now().astimezone() - timedelta(hours=3)
    _sessione(tmp_path / "sessioni", "s1", "lavoro lungo", vecchia, gonfia=40 * 1024)
    _sessione(tmp_path / "sessioni", "s2", "breve", vecchia)
    h = p.home()
    tipi = [a["tipo"] for a in h["avvisi"]]
    assert "non_salvate" in tipi and "inbox" in tipi
    assert h["progetti"][0]["nome"] == "Alfa"
    assert [c["id"] for c in h["chat"]] == ["s1", "s2"]
    assert {c["id"]: c["stato"] for c in h["chat"]} == {"s1": "non_salvata", "s2": "breve"}


def test_nota_in_inbox(tmp_path):
    p, r = _ponte(tmp_path)
    risposta = p.nota("comprare il latte")
    assert risposta["ok"]
    assert (r / "Inbox" / risposta["nome"]).read_text(encoding="utf-8").startswith("comprare il latte")
    assert "errore" in p.nota("   ")


def test_inbox_elenco(tmp_path):
    p, _ = _ponte(tmp_path)
    voci = p.inbox()["inbox"]
    assert voci[0]["nome"] == "2026-11-07 idea.md" and voci[0]["anteprima"] == "un'idea"


def test_conta_inbox_segue_la_cartella(tmp_path):
    # l'Inbox svuotata da fuori (Claude in un terminale) deve dare 0 subito
    p, r = _ponte(tmp_path)
    prima = p.conta_inbox()["inbox"]
    assert prima == len(p.inbox()["inbox"]) and prima > 0
    for f in (r / "Inbox").iterdir():
        f.unlink()
    assert p.conta_inbox() == {"inbox": 0}


def test_chat_attiva_da_poco_risulta_aperta(tmp_path):
    p, _ = _ponte(tmp_path)
    _sessione(tmp_path / "sessioni", "s3", "in corso", datetime.now().astimezone() - timedelta(minutes=1), gonfia=40 * 1024)
    assert p.chat()["chat"][0]["stato"] == "aperta"
    assert not any(a["tipo"] == "non_salvate" for a in p.home()["avvisi"])


def test_progetti_attivi_cartelle_e_abbandonati(tmp_path):
    p, r = _ponte(tmp_path)
    (r / "Progetti" / "Beta").mkdir()
    (r / "Progetti" / "Beta" / "CLAUDE.md").write_text("# Beta", encoding="utf-8")
    (r / "Progetti" / "Morto").mkdir()
    (r / "Progetti" / "Morto" / "CLAUDE.md").write_text("# Morto", encoding="utf-8")
    (r / "INDICE.md").write_text("## Progetti attivi\n- **Alfa** → `Progetti/Alfa/CLAUDE.md`\n"
                                 "- **Beta** → `Progetti/Beta/`\n- Abbandonato, non proporlo: Morto → `Progetti/Morto/CLAUDE.md`\n"
                                 "## Vita\n", encoding="utf-8")
    assert [x["nome"] for x in p.home()["progetti"]] == ["Alfa", "Beta"]


def test_second_brain_inglese(tmp_path):
    # struttura inglese (INDEX.md, Projects/, Archive/Log.md): progetti attivi, nuovo progetto, attivita'
    r = tmp_path / "brain"
    (r / "Projects" / "Alpha").mkdir(parents=True)
    (r / "Projects" / "Alpha" / "CLAUDE.md").write_text("# Alpha", encoding="utf-8")
    (r / "Projects" / "Dead").mkdir()
    (r / "Projects" / "Dead" / "CLAUDE.md").write_text("# Dead", encoding="utf-8")
    (r / "INDEX.md").write_text("# Index\n\n## Active projects\n- **Alpha** → `Projects/Alpha/CLAUDE.md`\n"
                                "- Abandoned, don't suggest: Dead → `Projects/Dead/CLAUDE.md`\n\n## Maintenance\nx\n", encoding="utf-8")
    p = ponte.Ponte(radice=r, cartella_sessioni=tmp_path / "sessioni", cache=tmp_path / "cache",
                    segni=tmp_path / "segni", chiedi=lambda *a, **k: None)
    assert [x["nome"] for x in p.home()["progetti"]] == ["Alpha"]
    assert p.crea_progetto("Garden", "tomatoes")["percorso"] == "Projects/Garden/CLAUDE.md"
    assert (r / "Projects" / "Garden" / "Output").is_dir()
    assert "## To do" in (r / "Projects" / "Garden" / "CLAUDE.md").read_text(encoding="utf-8")
    indice = (r / "INDEX.md").read_text(encoding="utf-8")
    assert indice.index("`Projects/Garden/CLAUDE.md`") < indice.index("Abandoned") < indice.index("## Maintenance")
    assert [x["nome"] for x in p.home()["progetti"]] == ["Alpha", "Garden"]
    assert not (r / "Progetti").exists() and not (r / "INDICE.md").exists()


def test_uso_del_piano(tmp_path):
    import json, time
    p, _ = _ponte(tmp_path)
    assert p.uso() == {"noto": False}
    (tmp_path / "cache").mkdir(exist_ok=True)
    (tmp_path / "cache" / "uso.json").write_text(json.dumps({
        "aggiornato": 1, "five_hour": {"used_percentage": 48.6, "resets_at": time.time() + 3600},
        "seven_day": {"used_percentage": 30, "resets_at": time.time() - 10}}), encoding="utf-8")
    u = p.uso()
    assert u["five_hour"]["percentuale"] == 49 and u["seven_day"] == {"percentuale": 0, "azzera": None}


def test_aggiungi_inbox_con_data_e_senza_sovrascrivere(tmp_path):
    p, r = _ponte(tmp_path)
    fuori = tmp_path / "fuori"
    fuori.mkdir()
    (fuori / "fattura.pdf").write_bytes(b"%PDF")
    (fuori / "2026-01-02 vecchio.txt").write_text("x", encoding="utf-8")
    oggi = f"{datetime.now():%Y-%m-%d}"
    e1 = p.aggiungi_inbox([str(fuori / "fattura.pdf"), str(fuori / "2026-01-02 vecchio.txt"), str(fuori)])
    assert e1["aggiunti"] == [f"{oggi} fattura.pdf", "2026-01-02 vecchio.txt"] and e1["saltati"] == ["fuori"]
    e2 = p.aggiungi_inbox([str(fuori / "fattura.pdf")])
    assert e2["aggiunti"] == [f"{oggi} fattura-2.pdf"]
    assert (r / "Inbox" / f"{oggi} fattura.pdf").read_bytes() == b"%PDF"


def test_crea_progetto_e_indice(tmp_path):
    p, r = _ponte(tmp_path)
    (r / "INDICE.md").write_text("## Progetti attivi\n- **Alfa** → `Progetti/Alfa/CLAUDE.md`\n"
                                 "- Abbandonato, non proporlo: Morto → `Progetti/Morto/CLAUDE.md`\n\n## Vita\n", encoding="utf-8")
    e = p.crea_progetto("Orto  Urbano", "pomodori sul balcone", "#2e6b3f", "f:seedling", "fiori")
    assert e["ok"] and (r / "Progetti" / "Orto Urbano" / "Output").is_dir()
    righe = (r / "INDICE.md").read_text(encoding="utf-8").splitlines()
    assert righe[2] == "- **Orto Urbano** — pomodori sul balcone → `Progetti/Orto Urbano/CLAUDE.md`"
    progetti = {x["nome"]: x for x in p.home()["progetti"]}
    assert progetti["Orto Urbano"]["aspetto"] == {"fondo": "#2e6b3f", "emblema": "f:seedling", "motivo": "fiori"}
    assert "errore" in p.crea_progetto("Orto Urbano")
    assert "errore" in p.crea_progetto("../fuori")
    assert p.cambia_aspetto("Progetti/Alfa/CLAUDE.md", "#1f4fa3", "codice")["ok"]


def test_elimina_e_ripristina_chat(tmp_path):
    p, _ = _ponte(tmp_path)
    eventi = []
    p.emetti = lambda n, d: eventi.append((n, d))
    quando = datetime.now().astimezone() - timedelta(hours=3)
    _sessione(tmp_path / "sessioni", "s1", "chat di prova", quando)
    _sessione(tmp_path / "sessioni", "s2", "da tenere", quando)
    (tmp_path / "sessioni" / "s1" / "subagents").mkdir(parents=True)
    assert {c["id"] for c in p.chat()["chat"]} == {"s1", "s2"}
    assert p.elimina_chat("s1") == {"ok": True}
    assert [c["id"] for c in p.chat()["chat"]] == ["s2"]
    cestino = tmp_path / "cache" / "cestino-chat" / "s1"
    assert (cestino / "s1.jsonl").exists() and (cestino / "s1" / "subagents").is_dir()
    assert eventi[-1] == ("chat-eliminata", {"id": "s1"})
    assert p.ripristina_chat("s1") == {"ok": True}
    assert {c["id"] for c in p.chat()["chat"]} == {"s1", "s2"}
    assert (tmp_path / "sessioni" / "s1" / "subagents").is_dir() and not cestino.exists()
    assert "errore" in p.ripristina_chat("s1")


def test_elimina_chat_rifiuta_id_strani_e_chat_aperte(tmp_path):
    p, _ = _ponte(tmp_path)
    _sessione(tmp_path / "sessioni", "s1", "aperta", datetime.now().astimezone())
    assert "errore" in p.elimina_chat("../s1")
    assert "errore" in p.elimina_chat("manca")

    class Aperta:
        sessione = "s1"

    class Terminali:
        def attive(self):
            return [Aperta()]
    p.terminali = Terminali()
    assert "errore" in p.elimina_chat("s1")
    assert (tmp_path / "sessioni" / "s1.jsonl").exists()


def test_cestino_si_svuota_dopo_trenta_giorni(tmp_path):
    import os
    p, _ = _ponte(tmp_path)
    vecchio = tmp_path / "cache" / "cestino-chat" / "vecchia"
    vecchio.mkdir(parents=True)
    t = datetime.now().timestamp() - 31 * 86400
    os.utime(vecchio, (t, t))
    _sessione(tmp_path / "sessioni", "s1", "x", datetime.now().astimezone())
    assert p.elimina_chat("s1") == {"ok": True}
    assert not vecchio.exists() and (tmp_path / "cache" / "cestino-chat" / "s1").exists()


def _sessione_con_risposte(cartella: Path, sid: str, domande_risposte, quando: datetime):
    cartella.mkdir(parents=True, exist_ok=True)
    righe = []
    for d, r in domande_risposte:
        righe.append({"type": "user", "entrypoint": "cli", "timestamp": quando.isoformat(), "message": {"content": d}})
        righe.append({"type": "assistant", "timestamp": quando.isoformat(),
                      "message": {"content": [{"type": "text", "text": r}, {"type": "tool_use", "name": "Bash"}]}})
    (cartella / f"{sid}.jsonl").write_text("\n".join(json.dumps(x) for x in righe) + "\n", encoding="utf-8")


def test_rinomina_fissa_e_ordine(tmp_path):
    p, _ = _ponte(tmp_path)
    ora = datetime.now().astimezone()
    for i, sid in enumerate(["a", "b", "c"]):
        _sessione(tmp_path / "sessioni", sid, f"chat {sid}", ora - timedelta(hours=i + 1))
    assert [c["id"] for c in p.chat()["chat"]] == ["a", "b", "c"]
    assert p.fissa_chat("c")["ok"] and p.fissa_chat("b")["ok"]
    elenco = p.chat()["chat"]
    assert [c["id"] for c in elenco] == ["b", "c", "a"] and elenco[0]["fissata"]
    assert [c["id"] for c in p.home()["chat"]][:2] == ["b", "c"]
    p.fissa_chat("b", False)
    assert [c["id"] for c in p.chat()["chat"]] == ["c", "a", "b"]
    assert p.rinomina_chat("a", "  Prove   varie ")["etichetta"] == "Prove varie"
    voce = next(c for c in p.chat()["chat"] if c["id"] == "a")
    assert voce["etichetta"] == "Prove varie" and voce["rinominata"]
    p.rinomina_chat("a", "")
    assert next(c for c in p.chat()["chat"] if c["id"] == "a")["etichetta"] != "Prove varie"
    assert "errore" in p.fissa_chat("../x")


def test_cerca_nel_testo_completo(tmp_path):
    p, _ = _ponte(tmp_path)
    ora = datetime.now().astimezone()
    _sessione_con_risposte(tmp_path / "sessioni", "x1", [("parliamo di cucina", "La carbonara vera usa il Guanciale di Amatrice")], ora)
    _sessione_con_risposte(tmp_path / "sessioni", "x2", [("ricetta", "pasta e patate con la provola")], ora)
    r = p.cerca_chat("guanciale amatrice")
    assert [t["id"] for t in r["trovate"]] == ["x1"] and "guanciale di amatrice" in r["trovate"][0]["estratto"]
    assert [t["id"] for t in p.cerca_chat("PROVOLA")["trovate"]] == ["x2"]
    assert p.cerca_chat("bash")["trovate"] == []  # niente nomi dei tool
    assert p.cerca_chat("")["trovate"] == []


def test_esporta_e_riga_registro(tmp_path):
    p, r = _ponte(tmp_path)
    ora = datetime(2026, 11, 8, 15, 0).astimezone()
    _sessione_con_risposte(tmp_path / "sessioni", "e1", [("organizziamo il viaggio in Giappone a Kyoto", "Ecco l'itinerario"),
                                                         ("aggiungi Nara", "Fatto")], ora)
    p.rinomina_chat("e1", "Giappone · Kyoto")
    e = p.esporta_chat("e1")
    testo = (r / e["percorso"]).read_text(encoding="utf-8")
    assert e["percorso"].startswith("Inbox/2026-11-08 chat giappone")
    assert testo.count("## Tu") == 2 and "Ecco l'itinerario" in testo and "Bash" not in testo
    (r / "Archivio").mkdir()
    (r / "Archivio" / "Registro.md").write_text(
        "# Registro\n\n- 2026-11-08 · Claude Code · Ricetta · pasta · nessuno\n"
        "- 2026-11-08 · Claude Code · Viaggio in Giappone · itinerario Kyoto e Nara · `Progetti/Giappone/CLAUDE.md`\n"
        "- 2026-10-01 · Claude Code · Giappone Kyoto viaggio vecchio · x\n", encoding="utf-8")
    assert "itinerario Kyoto e Nara" in p.riga_registro("e1")["riga"]
    (r / "Archivio" / "Registro.md").write_text("- 2026-11-08 · Claude Code · Ricetta · pasta\n", encoding="utf-8")
    assert "errore" in p.riga_registro("e1")


def test_apri_in_cartella_copia_il_trascritto(tmp_path, monkeypatch):
    p, _ = _ponte(tmp_path)
    _sessione(tmp_path / "sessioni", "k1", "chat da spostare", datetime.now().astimezone())
    altra = tmp_path / "progetto"
    altra.mkdir()
    monkeypatch.setattr(ponte, "cartella_sessioni_di", lambda c: tmp_path / "altre-sessioni")
    aperte = []
    monkeypatch.setattr(p, "apri_chat", lambda *a, **k: aperte.append((a, k)) or {"ok": True})
    assert p.apri_in_cartella("k1", str(altra)) == {"ok": True}
    assert (tmp_path / "altre-sessioni" / "k1.jsonl").exists() and (tmp_path / "sessioni" / "k1.jsonl").exists()
    assert aperte[0][0][:2] == ("riprendi", "k1") and aperte[0][1]["cartella"] == str(altra)
    assert "errore" in p.apri_in_cartella("k1", str(tmp_path / "manca"))


def test_cestino_in_impostazioni(tmp_path):
    p, _ = _ponte(tmp_path)
    ora = datetime.now().astimezone()
    _sessione(tmp_path / "sessioni", "z1", "prova uno", ora)
    _sessione(tmp_path / "sessioni", "z2", "prova due", ora)
    p.fissa_chat("z1")
    p.elimina_chat("z1"); p.elimina_chat("z2")
    assert {v["id"] for v in p.cestino_chat()["cestino"]} == {"z1", "z2"}
    assert p.elimina_per_sempre("z1") == {"ok": True}
    assert "z1" not in p._meta()["fissate"]
    assert p.svuota_cestino_chat()["conto"] == 1 and p.cestino_chat()["cestino"] == []


def test_inbox_elimina_ripristina_rinomina_sposta(tmp_path):
    p, r = _ponte(tmp_path)
    rel = "Inbox/2026-11-07 idea.md"
    e = p.elimina_inbox(rel)
    assert e["ok"] and not (r / rel).exists()
    assert p.ripristina_inbox(e["chiave"]) == {"ok": True} and (r / rel).exists()
    n = p.rinomina_inbox(rel, "2026-11-07 idea app")
    assert n["nome"] == "2026-11-07 idea app.md" and (r / n["percorso"]).exists()
    s = p.sposta_inbox(n["percorso"], "Progetti/Alfa/CLAUDE.md")
    assert s["progetto"] == "Alfa" and (r / "Progetti" / "Alfa" / "2026-11-07 idea app.md").exists()
    assert "errore" in p.elimina_inbox("Io/Regole.md")
    assert "errore" in p.ripristina_inbox("../x")
    assert "errore" in p.sposta_inbox("Inbox/manca.md", "Progetti/Alfa/CLAUDE.md")
