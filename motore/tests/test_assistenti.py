import json
import sqlite3

import assistenti
import modello


def riga_codex(tipo, carico, quando="2026-11-09T20:00:00.000Z"):
    return json.dumps({"timestamp": quando, "type": tipo, "payload": carico})


def messaggio_codex(ruolo, testo, quando="2026-11-09T20:00:05.000Z"):
    tipo = "input_text" if ruolo == "user" else "output_text"
    return riga_codex("response_item", {"type": "message", "role": ruolo, "content": [{"type": tipo, "text": testo}]}, quando)


def scrivi_codex(base, sid, cwd, righe, origine="cli"):
    cartella = base / "sessions" / "2026" / "11" / "09"
    cartella.mkdir(parents=True, exist_ok=True)
    p = cartella / f"rollout-2026-11-09T20-00-00-{sid}.jsonl"
    meta = riga_codex("session_meta", {"id": sid, "cwd": str(cwd), "source": origine, "thread_source": "user"})
    p.write_text("\n".join([meta, *righe]) + "\n", encoding="utf-8")
    return p


def scrivi_agy(base, sid, cwd, passi):
    logs = base / "brain" / sid / ".system_generated" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    p = logs / "transcript.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in passi) + "\n", encoding="utf-8")
    with open(base / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"display": "x", "workspace": str(cwd), "conversationId": sid}) + "\n")
    return p


ID = "019f95b2-4a71-7a02-b726-5b8ef5f70a51"


def test_codex_messaggi_senza_blocchi_di_sistema(tmp_path):
    p = scrivi_codex(tmp_path, ID, tmp_path / "brain", [
        messaggio_codex("user", "<environment_context>\n  <cwd>C:\\x</cwd>\n</environment_context>"),
        messaggio_codex("developer", "<permissions instructions>...</permissions instructions>"),
        messaggio_codex("user", "sistema il sito"),
        messaggio_codex("assistant", "Fatto: ho corretto **index.html**.", "2026-11-09T20:03:00.000Z"),
    ])
    assert assistenti.meta_codex(p)["id"] == ID
    s = assistenti.leggi(p, "codex", ID, completo=True)
    assert s.assistente == "codex" and s.n_messaggi == 1 and s.primo_messaggio == "sistema il sito"
    assert "index.html" in s.testo_completo and "environment_context" not in s.testo_completo
    assert s.ultima.minute == 3
    assert assistenti.testo_per_appunti(p, "codex") == "UTENTE: sistema il sito\n\nCODEX: Fatto: ho corretto **index.html**."
    assert assistenti.ultima_risposta(p, "codex") == "Fatto: ho corretto index.html."


def test_codex_trascritto_compresso(tmp_path):
    from compression import zstd
    p = scrivi_codex(tmp_path, ID, tmp_path, [messaggio_codex("user", "ciao")])
    compresso = p.with_name(p.name + ".zst")
    compresso.write_bytes(zstd.compress(p.read_bytes()))
    p.unlink()
    assert assistenti.file_codex(tmp_path) == [compresso]
    assert assistenti.leggi(compresso, "codex", ID).primo_messaggio == "ciao"


def test_agy_richiesta_risposte_e_cartella(tmp_path):
    p = scrivi_agy(tmp_path, "ef8ac9af-61a7-4ca7-83eb-1caa7e6d03eb", tmp_path / "brain", [
        {"type": "USER_INPUT", "source": "USER_EXPLICIT", "created_at": "2026-11-03T17:50:21Z",
         "content": "<USER_REQUEST>\ncollegati alla tv\n</USER_REQUEST>\n<ADDITIONAL_METADATA>x</ADDITIONAL_METADATA>"},
        {"type": "GENERIC", "source": "MODEL", "content": "Command exited with code 0."},
        {"type": "PLANNER_RESPONSE", "source": "MODEL", "thinking": "penso", "tool_calls": []},
        {"type": "PLANNER_RESPONSE", "source": "MODEL", "created_at": "2026-11-03T17:53:12Z", "content": "Sono collegato."},
    ])
    sid = assistenti.id_agy(p)
    s = assistenti.leggi(p, "agy", sid, completo=True)
    assert s.primo_messaggio == "collegati alla tv" and s.n_messaggi == 1 and s.assistente == "agy"
    assert "sono collegato" in s.testo_completo and "command exited" not in s.testo_completo
    assert assistenti.stessa_cartella(assistenti.cartelle_agy(tmp_path)[sid], tmp_path / "brain")


def test_agy_cartella_dal_database_e_sotto_agenti_esclusi(tmp_path):
    c = sqlite3.connect(tmp_path / "conversation_summaries.db")
    c.execute("create table conversation_summaries (conversation_id text, workspace_uris text, parent_conversation_id text)")
    c.execute("insert into conversation_summaries values ('a', '[\"file:///c%3A/Users/x/Mio%20Brain\"]', '')")
    c.execute("insert into conversation_summaries values ('figlio', '[\"file:///c%3A/Users/x/Mio%20Brain\"]', 'a')")
    c.commit()
    c.close()
    cartelle = assistenti.cartelle_agy(tmp_path)
    assert assistenti.stessa_cartella(cartelle["a"], "C:\\Users\\x\\Mio Brain") and not cartelle["figlio"]


def test_argomenti_per_nuova_ripresa_e_messaggio():
    assert assistenti.argomenti("codex") == [] and assistenti.argomenti("agy") == []
    assert assistenti.argomenti("codex", "id1", "salva") == ["resume", "id1", "salva"]
    assert assistenti.argomenti("agy", "id1", "salva") == ["--conversation", "id1", "-i", "salva"]
    assert assistenti.argomenti("codex", prompt="briefing") == ["briefing"]


def test_hook_di_codex_aggiunti_senza_toccare_gli_altri(tmp_path):
    base, hook = tmp_path / ".codex", tmp_path / "hooks"
    base.mkdir()
    (base / "hooks.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "mio.exe"}]}]}}), encoding="utf-8")
    r = modello.collega_hook_assistente("codex", hook, base)
    assert r["cambiato"]
    d = json.loads((base / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert [h["hooks"][0]["command"] for h in d["Stop"]][0] == "mio.exe" and len(d["Stop"]) == 2
    assert "-Assistente codex" in d["Stop"][1]["hooks"][0]["command"]
    assert "sync.ps1" in d["SessionStart"][0]["hooks"][0]["command"] and "PermissionRequest" in d
    assert len(list(base.glob("hooks.json.prima-di-second-brain-*"))) == 1
    # rifarlo non cambia niente e non duplica
    assert modello.collega_hook_assistente("codex", hook, base)["cambiato"] is False


def test_hook_di_antigravity_nel_file_condiviso(tmp_path):
    base = tmp_path / ".gemini" / "antigravity-cli"
    base.mkdir(parents=True)
    r = modello.collega_hook_assistente("agy", tmp_path / "hooks", base)
    d = json.loads((tmp_path / ".gemini" / "config" / "hooks.json").read_text(encoding="utf-8"))
    assert r["cambiato"] and "-Assistente agy" in d["second-brain-studio"]["Stop"][0]["command"]
    assert "-Json" in d["second-brain-studio"]["SessionStart"][0]["command"]
    # Antigravity rovina le virgolette doppie: nei suoi comandi non ce ne devono essere
    assert '"' not in d["second-brain-studio"]["Stop"][0]["command"] and "-Command . '" in d["second-brain-studio"]["Stop"][0]["command"]


def test_agents_md_creato_una_volta_sola(tmp_path):
    (tmp_path / "INDICE.md").write_text("# indice", encoding="utf-8")
    assert modello.collega_agents_md(tmp_path)["cambiato"]
    testo = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Io/Regole.md" in testo and "INDICE.md" in testo
    (tmp_path / "AGENTS.md").write_text("mio", encoding="utf-8")
    assert modello.collega_agents_md(tmp_path)["cambiato"] is False
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "mio"
