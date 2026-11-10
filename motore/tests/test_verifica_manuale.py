import json

import verifica_manuale as manuale


TESTO = "UTENTE: salva gli appunti e il registro\nCODEX: Ho aggiornato gli appunti in `Progetti/Alfa/CLAUDE.md` e il Registro.\nUTENTE: ok grazie\nCODEX: Appunti salvati."


def brain(tmp_path):
    (tmp_path / "Archivio").mkdir()
    (tmp_path / "Progetti/Alfa").mkdir(parents=True)
    (tmp_path / "INDICE.md").write_text("`Progetti/Alfa/CLAUDE.md`", encoding="utf-8")
    (tmp_path / "Archivio/Registro.md").write_text("Alfa completato", encoding="utf-8")
    (tmp_path / "Progetti/Alfa/CLAUDE.md").write_text("Alfa completato", encoding="utf-8")
    return tmp_path / "ricevuta.json"


def test_chat_normali_non_avviano_controlli_aggiuntivi(tmp_path):
    chiamate = []
    chiedi = lambda *a, **k: chiamate.append(a) or "CONFERMATO"
    for testo in ("UTENTE: correggi il bug\nCODEX: Corretto, appunti aggiornati.",
                  "UTENTE: il pulsante salva appunti non funziona\nCODEX: Appunti aggiornati.",
                  "UTENTE: non salvare gli appunti\nCODEX: Non ho salvato gli appunti."):
        assert not manuale.controlla(testo, tmp_path, tmp_path / "r.json", "codex", chiedi)["confermato"]
    assert chiamate == []


def test_nuove_informazioni_dopo_il_salvataggio_restano_normali():
    assert manuale.candidato(TESTO)
    assert not manuale.candidato(TESTO + "\nUTENTE: La prova ha trovato un errore nuovo\nCODEX: Controllo.")
    assert not manuale.candidato("UTENTE: aggiorna gli appunti\nCODEX: Non ho aggiornato gli appunti.")


def test_conferma_e_riuso_ricevuta_senza_riscrivere_appunti(tmp_path):
    ricevuta = brain(tmp_path)
    nota = tmp_path / "Progetti/Alfa/CLAUDE.md"
    prima = (nota.read_bytes(), nota.stat().st_mtime_ns)
    chiamate = []
    def chiedi(prompt, **kwargs):
        chiamate.append(kwargs)
        return "CONFERMATO"
    assert manuale.controlla(TESTO, tmp_path, ricevuta, "codex", chiedi)["confermato"]
    assert chiamate == [{"timeout": 12, "assistente": "codex"}]
    assert (nota.read_bytes(), nota.stat().st_mtime_ns) == prima
    assert manuale.controlla(TESTO, tmp_path, ricevuta, "codex", chiedi)["confermato"]
    assert len(chiamate) == 1
    nota.write_text("Nuovo stato", encoding="utf-8")
    assert manuale.controlla(TESTO, tmp_path, ricevuta, "codex", chiedi)["confermato"]
    assert len(chiamate) == 2


def test_timeout_o_risposta_incerta_non_segnano_salvata(tmp_path):
    ricevuta = brain(tmp_path)
    for risposta in (None, "DA_COMPLETARE", "Non posso confermare", "CONFERMATO forse"):
        esito = manuale.controlla(TESTO, tmp_path, ricevuta, "codex", lambda *a, **k: risposta)
        assert not esito["confermato"]
        assert not ricevuta.exists()


def test_modifiche_concorrenti_invalidano_la_conferma(tmp_path):
    ricevuta = brain(tmp_path)
    def chiedi(*args, **kwargs):
        (tmp_path / "Progetti/Alfa/CLAUDE.md").write_text("Cambio durante il controllo", encoding="utf-8")
        return "CONFERMATO"
    assert not manuale.controlla(TESTO, tmp_path, ricevuta, "codex", chiedi)["confermato"]
    assert not ricevuta.exists()


def test_modalita_helper_scrive_solo_esito_e_ricevuta(tmp_path, monkeypatch):
    input_path = tmp_path / "input.json"
    result = tmp_path / "result.json"
    input_path.write_text(json.dumps({"testo": "normale", "radice": str(tmp_path),
                                    "ricevuta": str(tmp_path / "r.json"), "assistente": "codex", "risultato": str(result)}), encoding="utf-8")
    manuale.esegui_file(input_path)
    assert json.loads(result.read_text(encoding="utf-8"))["confermato"] is False
