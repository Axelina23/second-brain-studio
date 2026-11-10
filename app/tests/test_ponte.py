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


class _TerminaliFinti:
    # registra cosa verrebbe avviato, senza aprire un terminale vero
    def __init__(self):
        self.schede, self.avviate = {}, []

    def attive(self):
        return list(self.schede.values())

    def url(self, sid):
        return f"ws://finto/{sid}"

    def apri(self, argv, cwd, titolo, sessione=None, assistente="claude"):
        from terminale import Scheda
        s = Scheda(f"s{len(self.schede)}", argv, cwd, titolo, sessione, assistente=assistente)
        self.schede[s.id] = s
        self.avviate.append(argv)
        return s


def test_chat_nuova_con_modello_e_assistente(tmp_path, monkeypatch):
    p, _ = _ponte(tmp_path)
    p.terminali = _TerminaliFinti()
    monkeypatch.setattr(ponte.Ponte, "_comando_assistente", staticmethod(lambda n: [f"C:/bin/{n}.exe"] if n == "codex" else None))
    # Claude con il modello scelto
    assert p.apri_chat("nuova", modello="fable")["assistente"] == "claude"
    assert p.terminali.avviate[-1][-2:] == ["--model", "fable"]
    # Codex: il suo eseguibile, nessun modello di Claude, ma accetta il suo modello
    v = p.apri_chat("nuova", modello="opus", assistente="codex")
    assert v["assistente"] == "codex" and v["titolo"] == "Codex" and p.terminali.avviate[-1] == ["C:/bin/codex.exe"]
    p.apri_chat("nuova", modello="gpt-5.6-luna", assistente="codex")
    assert p.terminali.avviate[-1] == ["C:/bin/codex.exe", "-m", "gpt-5.6-luna"]
    # assistente non installato: errore chiaro, niente scheda
    assert "non è installato" in p.apri_chat("nuova", assistente="agy")["errore"]
    # i comandi dell'app (con un prompt) vanno all'assistente scelto, come primo messaggio
    assert p.apri_chat("nuova", prompt="briefing", assistente="codex")["assistente"] == "codex"
    assert p.terminali.avviate[-1] == ["C:/bin/codex.exe", "briefing"]
    assert [a["id"] for a in p.assistenti()["assistenti"] if a["installato"]] == ["claude", "codex"]


def test_scheda_di_codex_non_prende_una_sessione_di_claude(tmp_path, monkeypatch):
    p, _ = _ponte(tmp_path)
    p.terminali = _TerminaliFinti()
    monkeypatch.setattr(ponte.Ponte, "_comando_assistente", staticmethod(lambda n: [f"C:/bin/{n}.exe"]))
    p.apri_chat("nuova", assistente="codex")
    _sessione(tmp_path / "sessioni", "nata-dopo", "ciao", datetime.now().astimezone())
    assert p.schede()["schede"][0]["sessione"] is None


# ---------- chat di Codex e Antigravity ----------
ID_CODEX = "019f95b2-4a71-7a02-b726-5b8ef5f70a51"
ID_AGY = "ef8ac9af-61a7-4ca7-83eb-1caa7e6d03eb"


def _riga_codex(tipo, carico):
    return json.dumps({"timestamp": datetime.now().astimezone().isoformat(), "type": tipo, "payload": carico})


def _chat_codex(base, sid, cwd, testo="sistema il sito", gonfia=0):
    cartella = base / "sessions" / "2026" / "11" / "09"
    cartella.mkdir(parents=True, exist_ok=True)
    righe = [_riga_codex("session_meta", {"id": sid, "cwd": str(cwd), "source": "cli", "thread_source": "user"}),
             _riga_codex("response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": testo}]}),
             _riga_codex("response_item", {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Fatto, sito sistemato."}]})]
    p = cartella / f"rollout-2026-11-09T20-00-00-{sid}.jsonl"
    p.write_text("\n".join(righe) + "\n" + (" " * gonfia), encoding="utf-8")
    return p


def _chat_agy(base, sid, cwd, testo="collegati alla tv"):
    logs = base / "brain" / sid / ".system_generated" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    passi = [{"type": "USER_INPUT", "content": f"<USER_REQUEST>\n{testo}\n</USER_REQUEST>"},
             {"type": "PLANNER_RESPONSE", "content": "Sono collegato."}]
    (logs / "transcript.jsonl").write_text("\n".join(json.dumps(x) for x in passi) + "\n", encoding="utf-8")
    with open(base / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"display": testo, "workspace": str(cwd), "conversationId": sid}) + "\n")


def _ponte_con_altri(tmp_path):
    r = _radice(tmp_path)
    p = ponte.Ponte(radice=r, cartella_sessioni=tmp_path / "sessioni", cache=tmp_path / "cache",
                    segni=tmp_path / "segni", chiedi=lambda *a, **k: None,
                    cartella_codex=tmp_path / "codex", cartella_agy=tmp_path / "gemini" / "antigravity-cli")
    p.terminali = _TerminaliFinti()
    return p, r


def test_chat_di_codex_e_antigravity_in_elenco_solo_del_second_brain(tmp_path):
    p, r = _ponte_con_altri(tmp_path)
    _sessione(tmp_path / "sessioni", "di-claude", "domanda a claude", datetime.now().astimezone() - timedelta(hours=2))
    _chat_codex(p.cartella_codex, ID_CODEX, r)
    _chat_codex(p.cartella_codex, "11111111-2222-3333-4444-555555555555", tmp_path / "altro-progetto")
    _chat_agy(p.cartella_agy, ID_AGY, r)
    _chat_agy(p.cartella_agy, "99999999-2222-3333-4444-555555555555", tmp_path / "altro-progetto")
    per_id = {c["id"]: c for c in p.chat()["chat"]}
    assert set(per_id) == {"di-claude", ID_CODEX, ID_AGY}
    assert per_id[ID_CODEX]["assistente"] == "codex" and per_id[ID_AGY]["assistente"] == "agy"
    assert per_id["di-claude"]["assistente"] == "claude"
    # ricerca nel testo ed esportazione valgono anche per loro
    assert [x["id"] for x in p.cerca_chat("sito sistemato")["trovate"]] == [ID_CODEX]
    esportata = (r / "Inbox" / p.esporta_chat(ID_AGY)["nome"]).read_text(encoding="utf-8")
    assert "Chat di Antigravity" in esportata and "## Antigravity" in esportata and "collegati alla tv" in esportata


def test_ripresa_torna_al_suo_assistente_salvataggio_usa_worker(tmp_path, monkeypatch):
    p, r = _ponte_con_altri(tmp_path)
    monkeypatch.setattr(ponte.Ponte, "_comando_assistente", staticmethod(lambda n: [f"C:/bin/{n}.exe"]))
    _chat_codex(p.cartella_codex, ID_CODEX, r)
    _chat_agy(p.cartella_agy, ID_AGY, r)
    v = p.apri_chat("riprendi", ID_CODEX, assistente="claude")
    assert v["assistente"] == "codex" and v["sessione"] == ID_CODEX
    assert p.terminali.avviate[-1] == ["C:/bin/codex.exe", "resume", ID_CODEX]
    p.terminali.schede.clear()
    salvate = []
    monkeypatch.setattr(p, "_appunti_di", lambda s, manuale=False: salvate.append((s.id, manuale)) or True)
    assert p.salva_chat(ID_AGY) == {"avviato": True, "sessione": ID_AGY}
    assert salvate == [(ID_AGY, True)]
    # azioni che esistono solo per Claude: errore chiaro
    assert "non si possono duplicare" in p.apri_chat("duplica", ID_CODEX)["errore"]
    assert "Solo le chat di Claude" in p.apri_in_cartella(ID_AGY, str(tmp_path))["errore"]
    # cestino e ripristino funzionano anche per Codex e Antigravity
    p.terminali.schede.clear()
    for sid, ass in ((ID_CODEX, "codex"), (ID_AGY, "agy")):
        assert p.elimina_chat(sid) == {"ok": True}
        assert sid not in {c["id"] for c in p.chat()["chat"]}
        nel_cestino = {v["id"]: v for v in p.cestino_chat()["cestino"]}
        assert nel_cestino[sid]["assistente"] == ass
        assert p.ripristina_chat(sid) == {"ok": True}
        assert sid in {c["id"] for c in p.chat()["chat"]}


def test_linguetta_di_codex_prende_la_sua_chat_e_il_titolo(tmp_path, monkeypatch):
    p, r = _ponte_con_altri(tmp_path)
    monkeypatch.setattr(ponte.Ponte, "_comando_assistente", staticmethod(lambda n: [f"C:/bin/{n}.exe"]))
    p.apri_chat("nuova", assistente="codex")
    _sessione(tmp_path / "sessioni", "di-claude", "ciao", datetime.now().astimezone())
    _chat_codex(p.cartella_codex, ID_CODEX, r)
    scheda = p.schede()["schede"][0]
    assert scheda["sessione"] == ID_CODEX and scheda["titolo"] != "Codex"


def test_vecchia_chat_claude_salvata_senza_riaprire_claude(tmp_path, monkeypatch):
    p, r = _ponte(tmp_path)
    _sessione(p.cartella_sessioni, "vecchia", "decisione del progetto", datetime.now().astimezone(), gonfia=40 * 1024)
    p.cartella_hook.mkdir(parents=True)
    (p.cartella_hook / "fine-sessione-worker.ps1").write_text("# worker", encoding="utf-8")
    avviati = []
    scelta = {"assistente_appunti": "codex", "appunti_auto": False}
    monkeypatch.setattr(ponte.Ponte, "_avvia", staticmethod(avviati.append))
    monkeypatch.setattr(ponte.Ponte, "_impostazioni", staticmethod(lambda: scelta))
    assert p.salva_chat("vecchia")["avviato"]
    comando = avviati[-1]
    assert comando[comando.index("-Assistente") + 1] == "claude"
    assert comando[comando.index("-Transcript") + 1].endswith("vecchia.jsonl")
    assert "-Testo" not in comando  # il worker legge le impostazioni attuali, non la scelta della chat
    assert p.salva_chat("vecchia")["avviato"] and len(avviati) == 1
    assert "errore" in p.salva_chat("inesistente")


def test_appunti_a_fine_chat_per_codex(tmp_path, monkeypatch):
    p, r = _ponte_con_altri(tmp_path)
    (p.cartella_hook).mkdir(parents=True)
    for nome in ("fine-sessione-worker.ps1", "sync.ps1"):
        (p.cartella_hook / nome).write_text("", encoding="utf-8")
    avviati = []
    monkeypatch.setattr(ponte.Ponte, "_avvia", staticmethod(avviati.append))
    monkeypatch.setattr(ponte.Ponte, "_impostazioni", staticmethod(lambda: {"appunti_auto": True, "soglia_kb": 30}))
    _chat_codex(p.cartella_codex, ID_CODEX, r, gonfia=40 * 1024)
    _chat_agy(p.cartella_agy, ID_AGY, r)  # corta: niente appunti, solo sincronizzazione
    lunga, corta = p._sessione(ID_CODEX), p._sessione(ID_AGY)
    assert p._appunti_di(lunga) is True
    comando = avviati[-1]
    assert "fine-sessione-worker.ps1" in comando[5] and comando[comando.index("-Id") + 1] == ID_CODEX
    assert comando[comando.index("-Strumento") + 1] == "Codex"
    assert comando[comando.index("-Assistente") + 1] == "codex"
    riassunto = Path(comando[comando.index("-Testo") + 1])
    assert riassunto.read_text(encoding="utf-8").startswith("UTENTE: sistema il sito")
    riassunto.unlink()
    assert (p.segni / f"{ID_CODEX}.in-corso").is_file()
    assert p._voce_chat(lunga)["stato"] in ("aperta", "in_corso")
    assert p._appunti_di(corta) is False and "sync.ps1" in avviati[-1][5]
    # appunti automatici spenti: solo sincronizzazione anche per la chat lunga
    monkeypatch.setattr(ponte.Ponte, "_impostazioni", staticmethod(lambda: {"appunti_auto": False}))
    assert p._appunti_di(lunga) is False and "sync.ps1" in avviati[-1][5]


def test_uso_per_assistente(tmp_path):
    import time
    p, r = _ponte_con_altri(tmp_path)
    p_codex = _chat_codex(p.cartella_codex, ID_CODEX, r)
    with open(p_codex, "a", encoding="utf-8") as f:
        f.write(_riga_codex("event_msg", {"type": "token_count", "rate_limits": {
            "primary": {"used_percent": 22.4, "resets_at": time.time() + 1800},
            "secondary": {"used_percent": 15.1, "resets_at": time.time() + 86400}}}) + "\n")
    _chat_agy(p.cartella_agy, ID_AGY, r)
    u = p.uso()
    assert u["assistenti"]["codex"]["five_hour"]["percentuale"] == 22
    assert u["assistenti"]["codex"]["seven_day"]["percentuale"] == 15
    assert u["assistenti"]["codex"]["cinque_ore"] == 1 and u["assistenti"]["agy"]["cinque_ore"] == 1


def test_titolo_aperta_stabile_e_finale_aggiornato(tmp_path):
    from types import SimpleNamespace
    p, _ = _ponte(tmp_path)
    s = SimpleNamespace(id="abc", dimensione=50000, n_messaggi=4, testo_utente="Rete", assistente="claude")
    p._sessioni = lambda: [s]
    t = SimpleNamespace(sessione="abc")
    p.terminali = SimpleNamespace(attive=lambda: [t])
    chiamate = []
    p._chiedi_per = lambda a: lambda prompt: chiamate.append(prompt) or "Rete nuova"
    ponte.parole._salva(p.cache / "parole.json", {"abc": {"dimensione": 40000, "parole": "rete precedente"}})
    p._lavoro_parole([s])
    assert chiamate == []
    assert p._etichetta(s) == "rete precedente"
    p.terminali.attive = lambda: []
    p._lavoro_parole([s])
    assert len(chiamate) == 1
    assert p._etichetta(s) == "rete nuova"


def test_accesso_codex_apre_login_senza_chat(tmp_path):
    from types import SimpleNamespace
    p, _ = _ponte(tmp_path)
    chiamate = []
    t = SimpleNamespace(id="login", titolo="Accesso a Codex", sessione=None, codice=None, assistente="codex")
    def apri(*args, **kwargs):
        chiamate.append((args, kwargs))
        return t
    p.terminali = SimpleNamespace(apri=apri, url=lambda sid: "ws://test")
    p._comando_assistente = lambda nome: ["node", "codex.js"]
    eventi = []
    p.emetti = lambda nome, dati: eventi.append((nome, dati))
    assert p.accedi_codex() == {"ok": True}
    assert chiamate[0][0][0] == ["node", "codex.js", "login"]
    assert t.accesso
    p.scheda_chiusa(t)
    assert eventi[-1] == ("scheda", {"id": "login", "chiusa": True})


def test_accesso_codex_non_installato(tmp_path):
    p, _ = _ponte(tmp_path)
    p._comando_assistente = lambda nome: None
    assert "errore" in p.accedi_codex()


def test_chiusa_recente_non_risulta_aperta(tmp_path):
    from types import SimpleNamespace
    p, _ = _ponte(tmp_path)
    s = SimpleNamespace(id="abc", dimensione=40000, ultima=datetime.now().astimezone())
    p._impostazioni = lambda: {}
    assert p._stato(s) == "aperta"
    p.segni.mkdir()
    (p.segni / "abc.chiusa").touch()
    assert p._stato(s) == "non_salvata"
    p._impostazioni = lambda: {"appunti_auto": False}
    assert p._stato(s) == "auto_disattivati"
