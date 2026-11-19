import json
import time

import assistenti
import modelli_cli

AGY = """Fetching available models...
gemini-4-neon-high\tGemini 4 Neon (High)
gemini-4-neon-low\tGemini 4 Neon (Low)
gemini-pro-orchestrator-neon\tOrchestrator (Neon)
claude-opus-5-5-low\tClaude Opus 5.5 (Low)
riga senza tabulazione
"""
CODEX = json.dumps({"models": [
    {"slug": "gpt-6.2-sol", "display_name": "GPT-6.2 Sol", "visibility": "list"},
    {"slug": "gpt-6.1-sol", "visibility": "list"},
    {"slug": "gpt-6-sol", "visibility": "list"},
    {"slug": "gpt-6-luna", "visibility": "list"},
    {"slug": "gpt-reserve", "visibility": "hide"},
    {"slug": "cattivo; rm -rf", "visibility": "list"},
]})


def test_lettura_agy_salta_intestazione_orchestrator_e_righe_storte():
    assert modelli_cli.leggi_agy(AGY) == [
        {"id": "gemini-4-neon-high", "nome": "Gemini 4 Neon (High)"},
        {"id": "gemini-4-neon-low", "nome": "Gemini 4 Neon (Low)"},
        {"id": "claude-opus-5-5-low", "nome": "Claude Opus 5.5 (Low)"},
    ]


def test_lettura_codex_solo_visibili_e_slug_sicuri():
    ids = [m["id"] for m in modelli_cli.leggi_codex(CODEX)]
    assert ids == ["gpt-6.2-sol", "gpt-6.1-sol", "gpt-6-sol", "gpt-6-luna"]
    assert modelli_cli.leggi_codex("non json") == []


def test_aggiorna_salva_cache_e_la_riusa(monkeypatch):
    chiamate = []
    monkeypatch.setattr(modelli_cli, "scarica", lambda n: chiamate.append(n) or [{"id": n + "-x", "nome": "X"}])
    modelli_cli.aggiorna()
    assert modelli_cli.conosce("agy", "agy-x") and modelli_cli.conosce("codex", "codex-x")
    modelli_cli.aggiorna()  # ancora fresca: nessuna nuova chiamata
    assert sorted(chiamate) == ["agy", "codex"]
    modelli_cli.aggiorna(forza=True)
    assert len(chiamate) == 4


def test_cli_che_fallisce_lascia_l_elenco_precedente(monkeypatch):
    monkeypatch.setattr(modelli_cli, "scarica", lambda n: [{"id": "vecchio-" + n, "nome": "V"}])
    modelli_cli.aggiorna(forza=True)
    monkeypatch.setattr(modelli_cli, "scarica", lambda n: None)
    modelli_cli.aggiorna(forza=True)
    assert modelli_cli.conosce("agy", "vecchio-agy")


def test_cache_scaduta_dopo_sei_ore(monkeypatch):
    monkeypatch.setattr(modelli_cli, "scarica", lambda n: [{"id": "m-" + n, "nome": "M"}])
    modelli_cli.aggiorna(forza=True)
    assert not modelli_cli.scaduta()
    dati = json.loads(modelli_cli._file().read_text(encoding="utf-8"))
    dati["aggiornata"] = time.time() - 7 * 3600
    modelli_cli._file().write_text(json.dumps(dati), encoding="utf-8")
    assert modelli_cli.scaduta()


def test_nuovi_modelli_diventano_validi_senza_toccare_il_codice(monkeypatch):
    assert assistenti.argomenti("agy", modello="gemini-4-neon-high") == []
    monkeypatch.setattr(modelli_cli, "scarica", lambda n: modelli_cli.leggi_agy(AGY) if n == "agy" else modelli_cli.leggi_codex(CODEX))
    modelli_cli.aggiorna(forza=True)
    assert assistenti.argomenti("agy", modello="gemini-4-neon-high") == ["--model", "gemini-4-neon-high"]
    assert assistenti.argomenti("agy", modello="claude-opus-5-5-low") == ["--model", "claude-opus-5-5-low"]
    assert assistenti.argomenti("agy", modello="inventato") == []


def test_codex_prende_la_versione_piu_nuova_della_famiglia(monkeypatch):
    # senza elenco: tabella fissa di ripiego
    assert assistenti.ultimo_modello_codex("gpt-6-sol") == "gpt-6.1-sol"
    monkeypatch.setattr(modelli_cli, "scarica", lambda n: modelli_cli.leggi_codex(CODEX) if n == "codex" else None)
    modelli_cli.aggiorna(forza=True)
    assert assistenti.ultimo_modello_codex("gpt-6-sol") == "gpt-6.2-sol"
    assert assistenti.ultimo_modello_codex("gpt-5.6-sol") == "gpt-6.2-sol"
    assert assistenti.ultimo_modello_codex("gpt-6-luna") == "gpt-6-luna"
    assert assistenti.argomenti("codex", modello="gpt-6.1-sol") == ["-m", "gpt-6.2-sol"]
