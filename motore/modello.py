# Crea un second brain nuovo dalle risposte del questionario del primo avvio:
# cartelle, regole, indice, profilo, registro, .gitignore, primo commit git, e il
# collegamento in ~/.claude/CLAUDE.md (blocco tra segni, con copia di sicurezza).
# Non sovrascrive mai file esistenti: se un file c'e' gia', lo lascia com'e'.
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import struttura

_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
INIZIO = "<!-- second-brain-studio:inizio -->"
FINE = "<!-- second-brain-studio:fine -->"
CARTELLA_HOOK = Path.home() / ".claude" / "second-brain" / "hooks"

STILI = {
    "conciso": "conciso e diretto, minimo preambolo",
    "spiegato": "chiaro e spiegato passo per passo, con esempi quando servono",
    "amichevole": "amichevole e colloquiale, ma senza giri di parole",
}

# testi dei file creati, per lingua della struttura (vedi struttura.py). {n} = nome della persona
T = {
    "it": {
        "stili": STILI, "persona": "l'utente", "lingua": "italiano", "aree": "le mie aree", "assistente": "assistente",
        "chiedi": ["cancellare o sovrascrivere file fuori dal second brain", "inviare mail o messaggi (al massimo prepara bozze)"],
        "metodo": ["se non sei sicuro chiedi, non inventare", "verifica prima di consegnare"],
        "claude": "# Second brain di {n}\nLeggi `{indice}` e `{regole}`: dicono chi sono, le regole sempre valide e dove sta ogni cosa. "
                  "Gli altri file aprili solo quando la richiesta li riguarda.\n",
        "regole": "# Regole per Claude (sempre valide)", "stile": "- **Stile:** rispondi in {lingua}, {stile}.",
        "r_metodo": "- **Metodo:** ", "r_chiedi": "- **Chiedi prima di:** ", "r_mai": "- **Mai:** ",
        "mai_chiavi": "scrivere password o chiavi negli appunti",
        "memoria": "- **Memoria:** quando qualcosa cambia stato, aggiorna il suo file di stato sostituendo l'informazione superata, e dimmelo in una riga. "
                   "File di stato sotto le ~80 righe: il vecchio va in `{archivio}/`. Il Registro lo aggiorna lo hook di fine sessione.",
        "file": "- **File:** documenti archiviati come `AAAA-MM-GG descrizione.ext`; output nella cartella `{output}/` del progetto. "
                "Progetto nuovo chiaro → crea `{progetti}/<Nome>/CLAUDE.md` + `{output}/` e aggiungilo all'indice; se è dubbio, chiedi.",
        "inbox": "- **Inbox:** quando dico \"smista l'inbox\", estrai le informazioni utili nei file di stato e sposta ogni file nella sua cartella col nome datato.",
        "ruoli": "- **Ruoli:** quando chiamo uno di questi nomi, rispondi in quel ruolo:",
        "profilo": "# Profilo di {n}\n\n{chi}## Persone\n(chi conta nella mia vita e nel lavoro: Claude le aggiunge quando le nomino)\n\n"
                   "## Preferenze\n(come mi piace lavorare: Claude le aggiunge quando le scopre)\n",
        "i_titolo": "# Indice del second brain di {n}",
        "i_base": "Base: `{radice}`. Regole sempre valide: `{regole}`. Apri un file solo se la richiesta lo riguarda.",
        "i_io": "## Io", "i_profilo": "- Profilo e persone → `{profilo}`",
        "i_area": "- Stato, scadenze e cose da fare → `{a}/{stato}`",
        "i_progetti": ["## Progetti attivi", "(nessuno ancora: ogni progetto ha `{progetti}/<Nome>/CLAUDE.md`)"],
        "i_sistema": ["## Sistema (per Claude)", "- Strumenti e programmi → `{strumenti}`",
                      "- `{inbox}/`: file da smistare · `{archivio}/`: Registro delle sessioni (`{registro}`) e vecchi appunti"],
        "i_manut": ["## Manutenzione",
                    "Aggiorna questo indice solo quando un progetto nasce, cambia stato o finisce. Indice + Regole sotto le 60 righe."],
        "stato": "# {a} — stato\n\n## In corso\n\n## Scadenze\n\n## Fatto\n",
        "registro": "# Registro delle sessioni\n\n"
                    "Una riga per sessione significativa, la più recente in alto. Serve a ritrovare \"quella volta che abbiamo fatto X\".\n"
                    "Formato: `AAAA-MM-GG · strumento · argomento · cosa si è deciso o fatto · dove sta il risultato`\n"
                    "Tieni le ultime 40 righe; quando diventano di più, riassumi le più vecchie in una riga per mese in fondo.\n\n"
                    "- {oggi} · Second Brain Studio · Primo avvio · Creato il second brain · `{indice}`\n",
        "strumenti": "# Strumenti\n\nProgrammi, comandi e servizi che Claude può usare su questo PC (li aggiunge Claude quando li installi).\n",
        "leggimi": ("LEGGIMI.md", "# Inbox\n\nTrascina qui file e note da smistare. Poi chiedi a Claude: \"smista l'inbox\".\n"),
        "commit": "Primo avvio: second brain creato con Second Brain Studio",
        "blocco": ["# Second brain (gestito da Second Brain Studio)",
                   "- Se la richiesta riguarda un progetto o un argomento dell'indice, leggi il file indicato prima di rispondere.",
                   "- Per passare un lavoro a una chat nuova in una scheda di Second Brain Studio: scrivi il compito in un file e lancia ",
                   "-PromptFile <file> -Cartella <cartella di lavoro>`.",
                   "- Se cito una sessione passata, guarda `{registro}`."],
        "prompt": "Ciao{n}! Questo è il mio second brain appena creato. "
                  "Leggi {indice} e {regole}, poi fammi al massimo 5 domande, una alla volta, per conoscermi meglio "
                  "(cosa sto facendo adesso in {aree}, scadenze vicine, progetti in corso, persone importanti). "
                  "Man mano scrivi le risposte nei file giusti ({profilo}, i file {stato} delle aree, {progetti}/ per i progetti, "
                  "aggiornando {indice}) e alla fine dimmi in breve cosa hai salvato e dove.",
    },
    "en": {
        "stili": {"conciso": "concise and direct, minimal preamble",
                  "spiegato": "clear and explained step by step, with examples when useful",
                  "amichevole": "friendly and conversational, but straight to the point"},
        "persona": "the user", "lingua": "English", "aree": "my areas", "assistente": "assistant",
        "chiedi": ["delete or overwrite files outside the second brain", "send emails or messages (at most prepare drafts)"],
        "metodo": ["if you're not sure, ask; don't make things up", "check before handing over"],
        "claude": "# {n}'s second brain\nRead `{indice}` and `{regole}`: they say who I am, the rules that always apply and where everything is. "
                  "Open other files only when the request is about them.\n",
        "regole": "# Rules for Claude (always apply)", "stile": "- **Style:** answer in {lingua}, {stile}.",
        "r_metodo": "- **Method:** ", "r_chiedi": "- **Ask before:** ", "r_mai": "- **Never:** ",
        "mai_chiavi": "write passwords or keys in the notes",
        "memoria": "- **Memory:** when something changes status, update its status file replacing the outdated information, and tell me in one line. "
                   "Status files stay under ~80 lines: older parts go to `{archivio}/`. The end-of-session hook updates the Log.",
        "file": "- **Files:** archived documents named `YYYY-MM-DD description.ext`; outputs in the project's `{output}/` folder. "
                "Clear new project → create `{progetti}/<Name>/CLAUDE.md` + `{output}/` and add it to the index; if unsure, ask.",
        "inbox": "- **Inbox:** when I say \"sort the inbox\", move the useful information into the status files and move each file to its folder with a dated name.",
        "ruoli": "- **Roles:** when I call one of these names, answer in that role:",
        "profilo": "# {n}'s profile\n\n{chi}## People\n(who matters in my life and work: Claude adds them when I mention them)\n\n"
                   "## Preferences\n(how I like to work: Claude adds them when it finds out)\n",
        "i_titolo": "# Index of {n}'s second brain",
        "i_base": "Base: `{radice}`. Rules that always apply: `{regole}`. Open a file only if the request is about it.",
        "i_io": "## Me", "i_profilo": "- Profile and people → `{profilo}`",
        "i_area": "- Status, deadlines and to-dos → `{a}/{stato}`",
        "i_progetti": ["## Active projects", "(none yet: every project has `{progetti}/<Name>/CLAUDE.md`)"],
        "i_sistema": ["## System (for Claude)", "- Tools and programs → `{strumenti}`",
                      "- `{inbox}/`: files to sort · `{archivio}/`: session log (`{registro}`) and old notes"],
        "i_manut": ["## Maintenance",
                    "Update this index only when a project starts, changes status or ends. Index + Rules under 60 lines."],
        "stato": "# {a} — status\n\n## In progress\n\n## Deadlines\n\n## Done\n",
        "registro": "# Session log\n\n"
                    "One line per meaningful session, newest on top. It helps find \"that time we did X\".\n"
                    "Format: `YYYY-MM-DD · tool · topic · what was decided or done · where the result is`\n"
                    "Keep the last 40 lines; when there are more, summarize the oldest into one line per month at the bottom.\n\n"
                    "- {oggi} · Second Brain Studio · First run · Second brain created · `{indice}`\n",
        "strumenti": "# Tools\n\nPrograms, commands and services Claude can use on this PC (Claude adds them when you install them).\n",
        "leggimi": ("README.md", "# Inbox\n\nDrop files and notes to sort here. Then ask Claude: \"sort the inbox\".\n"),
        "commit": "First run: second brain created with Second Brain Studio",
        "blocco": ["# Second brain (managed by Second Brain Studio)",
                   "- If the request is about a project or a topic in the index, read the file it points to before answering.",
                   "- To hand a task to a new chat in a Second Brain Studio tab: write the task in a file and run ",
                   "-PromptFile <file> -Cartella <working folder>`.",
                   "- If I mention a past session, look at `{registro}`."],
        "prompt": "Hi{n}! This is my brand-new second brain. "
                  "Read {indice} and {regole}, then ask me at most 5 questions, one at a time, to get to know me better "
                  "(what I'm doing right now in {aree}, upcoming deadlines, ongoing projects, important people). "
                  "As you go, write the answers in the right files ({profilo}, the areas' {stato} files, {progetti}/ for projects, "
                  "updating {indice}) and at the end tell me briefly what you saved and where.",
    },
}


def _lingua_struttura(r: dict) -> str:
    return "en" if (r or {}).get("struttura") == "en" else "it"

GITIGNORE = """# segreti: mai nel backup
*.env
.env*
.secrets/
*credential*
*secret*
# file pesanti e cartelle di build
*.mp4
*.mkv
node_modules/
dist/
__pycache__/
.pytest_cache/
.worktrees/
"""


def _nome_cartella(testo: str) -> str | None:
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(testo or "")).strip().strip(".")
    return t[:40] or None


def _lista(valori) -> list[str]:
    if isinstance(valori, str):
        valori = re.split(r"[\n,;]", valori)
    return [v.strip() for v in (valori or []) if isinstance(v, str) and v.strip()]


def _scrivi(p: Path, testo: str) -> bool:
    if p.exists():
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(testo, encoding="utf-8")
    return True


def testi(r: dict, radice: Path) -> dict[str, str]:
    # i file da creare (percorso relativo -> contenuto), dalle risposte del questionario;
    # r["struttura"] = "en" crea cartelle e testi in inglese (INDEX.md, Me/, Projects/...)
    r = r if isinstance(r, dict) else {}
    lin = _lingua_struttura(r)
    t, s = T[lin], struttura.STRUTTURE[lin]
    nome = (r.get("nome") or "").strip() or t["persona"]
    chi = (r.get("chi") or "").strip()
    lingua = (r.get("lingua") or t["lingua"]).strip()
    stile = t["stili"].get(r.get("stile"), t["stili"]["conciso"])
    aree = [a for a in (_nome_cartella(x) for x in _lista(r.get("aree"))) if a][:8]
    mai = _lista(r.get("mai"))
    # regole scelte nel questionario; se la chiave manca si usano quelle di partenza
    chiedi = _lista(r["chiedi"]) if "chiedi" in r else t["chiedi"]
    metodo = _lista(r["metodo"]) if "metodo" in r else t["metodo"]
    ruoli = [x for x in (r.get("ruoli") or []) if isinstance(x, dict) and (x.get("nome") or "").strip()]
    oggi = datetime.now().strftime("%Y-%m-%d")
    f: dict[str, str] = {}

    f["CLAUDE.md"] = t["claude"].format(n=nome, **s)

    regole = [t["regole"], t["stile"].format(lingua=lingua, stile=stile)]
    if metodo:
        regole.append(t["r_metodo"] + "; ".join(metodo) + ".")
    if chiedi:
        regole.append(t["r_chiedi"] + "; ".join(chiedi) + ".")
    regole.append(t["r_mai"] + "; ".join([*mai, t["mai_chiavi"]]) + ".")
    regole += [t["memoria"].format(**s), t["file"].format(**s), t["inbox"]]
    if ruoli:
        regole.append(t["ruoli"])
        for x in ruoli:
            regole.append(f"  - **{x['nome'].strip()}** — {(x.get('compito') or '').strip() or t['assistente']}")
    f[s["regole"]] = "\n".join(regole) + "\n"

    f[s["profilo"]] = t["profilo"].format(n=nome, chi=f"{chi}\n\n" if chi else "")

    indice = [t["i_titolo"].format(n=nome), t["i_base"].format(radice=radice, **s),
              "", t["i_io"], (chi or nome), t["i_profilo"].format(**s), ""]
    for a in aree:
        indice += [f"## {a}", t["i_area"].format(a=a, **s), ""]
    indice += [x.format(**s) for x in t["i_progetti"]] + [""]
    indice += [x.format(**s) for x in t["i_sistema"]] + [""]
    indice += t["i_manut"]
    f[s["indice"]] = "\n".join(indice) + "\n"

    for a in aree:
        f[f"{a}/{s['stato']}"] = t["stato"].format(a=a)

    f[s["registro"]] = t["registro"].format(oggi=oggi, **s)
    f[s["strumenti"]] = t["strumenti"]
    f[f"{s['inbox']}/{t['leggimi'][0]}"] = t["leggimi"][1]
    f[f"{s['progetti']}/.gitkeep"] = ""
    f[".gitignore"] = GITIGNORE
    return f


def crea_struttura(radice: Path, risposte: dict, git: bool = True) -> dict:
    radice = Path(radice)
    radice.mkdir(parents=True, exist_ok=True)
    creati = [rel for rel, testo in testi(risposte, radice).items() if _scrivi(radice / rel, testo)]
    messaggio = T[_lingua_struttura(risposte)]["commit"]
    if git and shutil.which("git"):
        def g(*a):
            return subprocess.run(["git", *a], cwd=radice, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=30, creationflags=_FLAGS)
        if not (radice / ".git").exists():
            g("init", "-b", "main")
        g("add", "-A")
        if g("status", "--porcelain").stdout.strip():
            r = g("commit", "-m", messaggio)
            if r.returncode != 0:  # nome e mail di git non impostati: commit con un autore locale
                g("-c", "user.name=Second Brain", "-c", "user.email=second-brain@localhost",
                  "commit", "-m", messaggio)
    return {"ok": True, "creati": creati}


def blocco_claude(radice: Path) -> str:
    # blocco per ~/.claude/CLAUDE.md nella lingua della struttura del second brain
    st = struttura.di(radice)
    t = T["en" if st is struttura.STRUTTURE["en"] else "it"]["blocco"]
    r = Path(radice).as_posix()
    i = r.replace(" ", "\\ ")  # negli import @ di Claude gli spazi vanno scritti "\ "
    return (f"{INIZIO}\n{t[0]}\n"
            f"@{i}/{st['regole']}\n@{i}/{st['indice']}\n\n"
            f"{t[1]}\n{t[2]}"
            f"`powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"{CARTELLA_HOOK.as_posix()}/apri-chat.ps1\" "
            f"{t[3]}\n"
            f"{t[4].format(registro=f'{r}/' + st['registro'])}\n{FINE}\n")


def collega_claude_md(radice: Path, file: Path | None = None) -> dict:
    # inserisce (o aggiorna) il blocco tra i segni in ~/.claude/CLAUDE.md, lasciando il resto
    file = Path(file) if file else Path.home() / ".claude" / "CLAUDE.md"
    blocco = blocco_claude(radice)
    vecchio = file.read_text(encoding="utf-8") if file.is_file() else ""
    if INIZIO in vecchio and FINE in vecchio:
        prima, resto = vecchio.split(INIZIO, 1)
        dopo = resto.split(FINE, 1)[1].lstrip("\n")
        nuovo = prima + blocco + (("\n" + dopo) if dopo else "")
    else:
        nuovo = blocco + ("\n" + vecchio if vecchio else "")
    if nuovo == vecchio:
        return {"ok": True, "cambiato": False}
    file.parent.mkdir(parents=True, exist_ok=True)
    if vecchio:
        shutil.copy2(file, file.with_name(f"CLAUDE.md.prima-di-second-brain-{datetime.now():%Y%m%d-%H%M%S}"))
    file.write_text(nuovo, encoding="utf-8")
    return {"ok": True, "cambiato": True}


def prompt_iniziale(r: dict) -> str:
    # la prima chat: Claude conosce la persona e riempie gli appunti con le sue risposte
    lin = _lingua_struttura(r)
    t, st = T[lin], struttura.STRUTTURE[lin]
    nome = (r.get("nome") or "").strip()
    aree = ", ".join(_lista(r.get("aree"))) or t["aree"]
    return t["prompt"].format(n=(" " + nome) if nome else "", aree=aree, **st)


def _comando(script: Path, *arg: str) -> str:
    return " ".join(["powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File", f'"{script.as_posix()}"', *arg])


def migra_hook_appunti_legacy(destinazione: Path, base: Path | None = None) -> bool:
    # Anche le chat gia' aperte possono avere ancora il vecchio comando SessionEnd.
    base = Path(base) if base else Path.home() / ".claude"
    legacy = base / "hooks" / "aggiorna-appunti.ps1"
    if not legacy.is_file():
        return False
    testo = legacy.read_text(encoding="utf-8-sig")
    if not all(segno in testo for segno in ("Hook SessionEnd di Claude Code", "aggiorna-appunti-worker.ps1", "CLAUDE_NOTES_PASS")):
        return False
    worker = (Path(destinazione) / "fine-sessione.ps1").resolve()
    if not worker.is_file():
        return False
    shutil.copy2(legacy, legacy.with_name(f"{legacy.name}.prima-di-second-brain-{datetime.now():%Y%m%d-%H%M%S}"))
    percorso = worker.as_posix().replace("'", "''")
    legacy.write_text("# Compatibilita con le vecchie chat: impostazioni lette al salvataggio.\n"
                      f"& '{percorso}'\nexit $LASTEXITCODE\n", encoding="utf-8")
    return True


def collega_hook(sorgente: Path, destinazione: Path, settings: Path | None = None,
                 riga_stato: bool = True, solo_avvisi: bool = False) -> dict:
    # copia gli hook dell'app in una cartella stabile (non quella d'installazione, che
    # cambia) e li aggiunge a ~/.claude/settings.json senza toccare gli altri hook;
    # la riga di stato nostra, o il ponte davanti a quella che l'utente ha gia'
    import json
    settings = Path(settings) if settings else Path.home() / ".claude" / "settings.json"
    destinazione = Path(destinazione)
    destinazione.mkdir(parents=True, exist_ok=True)
    for f in Path(sorgente).glob("*.ps1"):
        shutil.copy2(f, destinazione / f.name)
    migra_hook_appunti_legacy(destinazione, settings.parent)
    testo = settings.read_text(encoding="utf-8") if settings.is_file() else ""
    try:
        d = json.loads(testo) if testo.strip() else {}
    except ValueError:
        return {"errore": "settings.json di Claude non è leggibile: lo lascio com'è"}
    if not isinstance(d, dict):
        return {"errore": "settings.json di Claude ha un formato inatteso"}
    prima = json.dumps(d, sort_keys=True)
    hooks = d.setdefault("hooks", {})
    segno = destinazione.as_posix()

    def aggiungi(evento: str, voce: dict) -> None:
        elenco = hooks.setdefault(evento, [])
        elenco[:] = [v for v in elenco if not any(segno in str(h.get("command", "")) for h in v.get("hooks", []))]
        elenco.append(voce)

    if not solo_avvisi:
        aggiungi("SessionStart", {"matcher": "startup", "hooks": [
            {"type": "command", "command": _comando(destinazione / "sync.ps1", "-Modo", "pull"), "timeout": 20}]})
        aggiungi("SessionEnd", {"hooks": [
            {"type": "command", "command": _comando(destinazione / "fine-sessione.ps1"), "timeout": 30}]})
    # avvisi per le notifiche dell'app: Claude ha finito di rispondere / aspetta un permesso
    aggiungi("Stop", {"hooks": [
        {"type": "command", "command": _comando(destinazione / "avviso.ps1", "-Evento", "fine"), "timeout": 10}]})
    aggiungi("Notification", {"hooks": [
        {"type": "command", "command": _comando(destinazione / "avviso.ps1", "-Evento", "attesa"), "timeout": 10}]})
    stato = ponte = False
    if riga_stato and not solo_avvisi:
        attuale = d.get("statusLine") if isinstance(d.get("statusLine"), dict) else None
        cmd = str((attuale or {}).get("command") or "")
        if attuale is None:
            d["statusLine"] = {"type": "command", "command": _comando(destinazione / "riga-stato.ps1"), "refreshInterval": 30}
            stato = True
        elif segno in cmd:
            stato, ponte = True, "-Ponte" in cmd  # gia' nostra (o gia' il ponte): resta com'e'
        elif cmd:
            # riga di stato dell'utente: la si salva accanto agli hook e la fa girare il ponte,
            # che prima registra l'uso del piano per l'app; l'utente continua a vedere la sua
            (destinazione / "riga-stato-utente.sh").write_text(cmd + "\n", encoding="utf-8", newline="\n")
            (destinazione / "riga-stato-utente.json").write_text(json.dumps(attuale, ensure_ascii=False, indent=2), encoding="utf-8")
            d["statusLine"] = {**attuale, "type": "command", "command": _comando(destinazione / "riga-stato.ps1", "-Ponte")}
            stato = ponte = True
    if json.dumps(d, sort_keys=True) == prima:
        return {"ok": True, "cambiato": False, "riga_stato": stato, "ponte": ponte}
    settings.parent.mkdir(parents=True, exist_ok=True)
    if testo:
        shutil.copy2(settings, settings.with_name(f"settings.json.prima-di-second-brain-{datetime.now():%Y%m%d-%H%M%S}"))
    settings.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "cambiato": True, "riga_stato": stato, "ponte": ponte}


# ---------- Codex e Antigravity ----------
AGENTS = {
    "it": ("# Second brain\n\n"
           "Questa cartella è un second brain: appunti che gli assistenti leggono e tengono aggiornati.\n"
           "Prima di rispondere leggi `{regole}` e `{indice}`: dicono chi è la persona, le regole sempre "
           "valide e dove sta ogni cosa. Apri gli altri file solo quando la richiesta li riguarda.\n"
           "Quando qualcosa cambia stato, aggiorna il suo file di stato sostituendo l'informazione superata.\n"),
    "en": ("# Second brain\n\n"
           "This folder is a second brain: notes that assistants read and keep up to date.\n"
           "Before answering read `{regole}` and `{indice}`: they say who the person is, the rules that "
           "always apply and where everything lives. Open the other files only when the request is about them.\n"
           "When something changes status, update its status file, replacing the outdated information.\n"),
}


def collega_agents_md(radice: Path) -> dict:
    # Codex e Antigravity leggono AGENTS.md nella cartella di lavoro: li manda a regole e indice,
    # come CLAUDE.md fa con Claude. Un AGENTS.md che c'e' gia' non si tocca.
    file = Path(radice) / "AGENTS.md"
    if file.exists():
        return {"ok": True, "cambiato": False}
    st = struttura.di(radice)
    lingua = "en" if st is struttura.STRUTTURE["en"] else "it"
    file.write_text(AGENTS[lingua].format(regole=st["regole"], indice=st["indice"]), encoding="utf-8", newline="\n")
    return {"ok": True, "cambiato": True}


def _comando_senza_virgolette(script: Path, *arg: str) -> str:
    # Antigravity passa il comando a cmd.exe trasformando le virgolette doppie in \" (che
    # PowerShell poi prende alla lettera): qui il percorso sta tra apici singoli, dentro -Command
    percorso = script.as_posix().replace("'", "''")
    return " ".join(["powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command .", f"'{percorso}'", *arg])


def collega_hook_assistente(assistente: str, hook: Path, base: Path) -> dict:
    # aggiunge gli hook dell'app (sync a inizio chat, avvisi per le notifiche) alla
    # configurazione di Codex (<base>/hooks.json, stesso formato di Claude) o di Antigravity
    # (<base>/../config/hooks.json, un blocco con il nostro nome), senza toccare gli altri.
    # Gli appunti a fine chat non passano da qui: li avvia l'app alla chiusura della linguetta.
    import json
    hook, base = Path(hook), Path(base)
    file = base / "hooks.json" if assistente == "codex" else base.parent / "config" / "hooks.json"
    testo = file.read_text(encoding="utf-8") if file.is_file() else ""
    try:
        d = json.loads(testo) if testo.strip() else {}
    except ValueError:
        return {"errore": f"{file.name} non è leggibile: lo lascio com'è"}
    if not isinstance(d, dict):
        return {"errore": f"{file.name} ha un formato inatteso"}
    prima = json.dumps(d, sort_keys=True)
    comando = _comando if assistente == "codex" else _comando_senza_virgolette
    sync = comando(hook / "sync.ps1", "-Modo", "pull", "-Json")
    fine = comando(hook / "avviso.ps1", "-Evento", "fine", "-Assistente", assistente)
    attesa = comando(hook / "avviso.ps1", "-Evento", "attesa", "-Assistente", assistente)
    if assistente == "codex":
        hooks = d.setdefault("hooks", {})
        segno = hook.as_posix()
        for evento, riga, tempo in (("SessionStart", sync, 20), ("Stop", fine, 10), ("PermissionRequest", attesa, 10)):
            elenco = hooks.setdefault(evento, [])
            elenco[:] = [v for v in elenco if not any(segno in str(h.get("command", "")) for h in v.get("hooks", []))]
            elenco.append({"hooks": [{"type": "command", "command": riga, "timeout": tempo}]})
    else:
        d["second-brain-studio"] = {
            "SessionStart": [{"type": "command", "command": sync, "timeout": 20}],
            "Stop": [{"type": "command", "command": fine, "timeout": 10}],
            "PreToolUse": [{"matcher": "ask_question",
                            "hooks": [{"type": "command", "command": attesa, "timeout": 10}]}]}
    if json.dumps(d, sort_keys=True) == prima:
        return {"ok": True, "cambiato": False, "file": str(file)}
    file.parent.mkdir(parents=True, exist_ok=True)
    if testo:
        shutil.copy2(file, file.with_name(f"{file.name}.prima-di-second-brain-{datetime.now():%Y%m%d-%H%M%S}"))
    file.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "cambiato": True, "file": str(file)}
