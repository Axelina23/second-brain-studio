# Ponte tra l'interfaccia (JS, via pywebview js_api) e la logica del second brain.
# Riusa i moduli di ../motore (fonte unica della logica). Ogni metodo pubblico
# restituisce dati JSON-serializzabili e non solleva: in caso di errore {"errore": "..."}.
# I lavori lenti (git fetch, Haiku, lettura delle trascrizioni) girano in thread e
# avvisano l'interfaccia con self.emetti(nome_evento, dati).
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

AVVIO = Path(__file__).resolve().parent.parent / "motore"
if str(AVVIO) not in sys.path:
    sys.path.insert(0, str(AVVIO))

import appunti as mod_appunti  # noqa: E402
import note as mod_note  # noqa: E402
import oggi as mod_oggi  # noqa: E402
import parole  # noqa: E402
import salvataggio  # noqa: E402
import sessioni as mod_sessioni  # noqa: E402
import struttura as mod_struttura  # noqa: E402
import sync as mod_sync  # noqa: E402
from haiku import chiedi_haiku  # noqa: E402
# assistenti da riga di comando che l'app sa ospitare in una linguetta, oltre a Claude Code
ASSISTENTI = {"claude": "Claude", "codex": "Codex", "agy": "Antigravity"}
MODELLI_CLAUDE = ("fable", "opus", "sonnet", "haiku")

from percorsi import CACHE, CARTELLA_SESSIONI, CLAUDE, RADICE, SEGNI, SOGLIA_SIGNIFICATIVA  # noqa: E402
from percorsi import cartella_sessioni as cartella_sessioni_di  # noqa: E402
import chat_extra  # noqa: E402

# per lingua della struttura del second brain (struttura.py)
PROMPT_SALVA = {"it": "Aggiorna gli appunti e il Registro con quanto fatto in questa chat.",
                "en": "Update the notes and the Log with what was done in this chat."}
SEZIONE_PROGETTI = {"it": "## Progetti attivi", "en": "## Active projects"}
RE_SEZIONE_PROGETTI = r"^## (?:Progetti attivi|Active projects)\s*$(.*?)(?=^## |\Z)"
RE_ABBANDONATO = r"abbandonat|abandoned"
RECENTE = timedelta(minutes=3)
GIORNI_FERMO = 14
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]
_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
MAX_ANTEPRIMA = 400
MAX_RISULTATI = 40


def saluto(ora: int) -> str:
    if 5 <= ora < 13:
        return "Buongiorno"
    if 13 <= ora < 18:
        return "Buon pomeriggio"
    return "Buonasera"


def data_lunga(d: datetime) -> str:
    return f"{GIORNI[d.weekday()].capitalize()} {d.day} {MESI[d.month - 1]}"


def date_git(radice: Path, timeout: float = 15) -> dict[str, float]:
    # ultima modifica committata di ogni file (percorso relativo con /): piu' affidabile
    # dell'mtime, che su un PC si azzera a ogni pull
    try:
        r = subprocess.run(["git", "log", "--since=1.year", "--format=@%ct", "--name-only"],
                           cwd=radice, capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout, creationflags=_FLAGS,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except (OSError, subprocess.SubprocessError):
        return {}
    if r.returncode != 0:
        return {}
    date, quando = {}, None
    for riga in r.stdout.splitlines():
        if riga.startswith("@"):
            try:
                quando = float(riga[1:])
            except ValueError:
                quando = None
        elif riga.strip() and quando is not None:
            date.setdefault(riga.strip().strip('"'), quando)
    return date


def _rel(p: Path, radice: Path) -> str:
    return p.resolve().relative_to(radice.resolve()).as_posix()


class Ponte:
    def __init__(self, radice: Path = RADICE, cartella_sessioni: Path = CARTELLA_SESSIONI,
                 cache: Path = CACHE, segni: Path = SEGNI, terminali=None, chiedi=chiedi_haiku,
                 adesso=lambda: datetime.now().astimezone()):
        self.radice = Path(radice)
        self.cartella_sessioni = Path(cartella_sessioni)
        self.cache = Path(cache)
        self.segni = Path(segni)
        self.terminali = terminali
        self._chiedi = chiedi
        self.adesso = adesso
        self.emetti = lambda nome, dati: None
        self._sessioni_cache: dict[str, tuple] = {}
        self._date_git: dict[str, float] = {}
        self._date_git_quando = 0.0
        self._blocco = threading.Lock()
        self._lavori: set[str] = set()
        self.sync_stato = "grigio"
        self.token_git = lambda: None  # l'app ci mette la chiave di GitHub (main.py)
        self.oggi_eventi: list[str] = []
        self.oggi_scadenze: str | None = None

    # ---------- utilita' ----------
    def _in_thread(self, nome: str, funzione, *args) -> None:
        with self._blocco:
            if nome in self._lavori:
                return
            self._lavori.add(nome)

        def corpo():
            try:
                funzione(*args)
            except Exception:
                self._log()
            finally:
                with self._blocco:
                    self._lavori.discard(nome)
        threading.Thread(target=corpo, name=nome, daemon=True).start()

    def _nota(self, testo: str) -> None:
        try:
            self.cache.mkdir(parents=True, exist_ok=True)
            with open(self.cache / "app-errori.log", "a", encoding="utf-8") as f:
                f.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S}\n{testo}\n\n")
        except OSError:
            pass

    def _log(self) -> None:
        try:
            self.cache.mkdir(parents=True, exist_ok=True)
            with open(self.cache / "app-errori.log", "a", encoding="utf-8") as f:
                f.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S}\n{traceback.format_exc()}\n")
        except OSError:
            pass

    def _sicuro(self, rel: str, suffissi=(".md", ".txt")) -> Path | None:
        # solo file dentro il second brain, mai fuori (niente ../)
        try:
            p = (self.radice / rel).resolve()
            p.relative_to(self.radice.resolve())
        except (ValueError, OSError):
            return None
        return p if p.suffix.lower() in suffissi else None

    def _eta_giorni(self, p: Path) -> float:
        quando = self._date_git.get(_rel(p, self.radice)) if self._date_git else None
        if quando is None:
            try:
                quando = p.stat().st_mtime
            except OSError:
                return 0
        return max(0.0, (time.time() - quando) / 86400)

    def _aggiorna_date_git(self, forza=False) -> None:
        if forza or time.time() - self._date_git_quando > 300:
            d = date_git(self.radice)
            if d:
                self._date_git = d
            self._date_git_quando = time.time()

    # ---------- sessioni ----------
    def _sessioni(self) -> list:
        # rilegge solo i trascritti cambiati (dimensione o mtime)
        nuove = {}
        for p in self.cartella_sessioni.glob("*.jsonl"):
            try:
                st = p.stat()
            except OSError:
                continue
            chiave = (st.st_size, st.st_mtime)
            vecchia = self._sessioni_cache.get(p.stem)
            if vecchia and vecchia[0] == chiave:
                nuove[p.stem] = vecchia
                continue
            try:
                s = mod_sessioni._leggi(p, completo=True)  # testo completo: ricerca nelle chat
            except OSError:
                continue
            nuove[p.stem] = (chiave, s)
        self._sessioni_cache = nuove
        return sorted((s for _, s in nuove.values() if s), key=lambda s: s.ultima, reverse=True)

    def _meta(self) -> dict:
        # titoli scelti a mano e chat fissate; si rilegge solo se il file e' cambiato
        try:
            m = (self.cache / "chat-meta.json").stat().st_mtime
        except OSError:
            m = None
        if getattr(self, "_meta_cache", None) is None or self._meta_cache[0] != m:
            self._meta_cache = (m, chat_extra.leggi_meta(self.cache))
        return self._meta_cache[1]

    def _salva_meta(self, meta: dict) -> None:
        chat_extra.scrivi_meta(self.cache, meta)
        self._meta_cache = None

    def _etichetta(self, s) -> str:
        scelto = self._meta()["titoli"].get(s.id)
        return scelto or parole.parole_chiave(s, self.cache / "parole.json") or parole.ripiego(s)

    def _ordinate(self, elenco) -> list:
        # le chat fissate in cima, nell'ordine in cui sono state fissate (l'ultima per prima)
        fissate = self._meta()["fissate"]
        per_id = {s.id: s for s in elenco}
        prima = [per_id[i] for i in reversed(fissate) if i in per_id]
        return prima + [s for s in elenco if s.id not in set(fissate)]

    def _stato(self, s) -> str:
        aperta = any(t.sessione == s.id for t in (self.terminali.attive() if self.terminali else []))
        # attiva da poco: probabilmente e' aperta in un altro terminale
        if aperta or s.ultima > self.adesso() - RECENTE:
            return "aperta"
        return salvataggio.stato_salvataggio(s, self.segni)

    def _voce_chat(self, s) -> dict:
        return {"id": s.id, "etichetta": self._etichetta(s), "ultima": s.ultima.isoformat(),
                "dimensione": s.dimensione, "messaggi": s.n_messaggi, "stato": self._stato(s),
                "primo": s.primo_messaggio[:200], "fissata": s.id in self._meta()["fissate"],
                "rinominata": s.id in self._meta()["titoli"]}

    def voci_per_altri_pc(self, limite: int = 100) -> list:
        # chat di questo PC per il riepilogo condiviso (altri_pc.py): senza il primo messaggio,
        # con lo stato di salvataggio vero (serve all'uscita, quando nessuna chat resta aperta)
        return [{**self._voce_chat(s), "primo": "", "stato_salvataggio": salvataggio.stato_salvataggio(s, self.segni)}
                for s in self._sessioni()[:limite]]

    def chat(self, limite: int = 200) -> dict:
        try:
            elenco = self._ordinate(self._sessioni())[:limite]
            self._in_thread("parole", self._lavoro_parole, elenco)
            return {"chat": [self._voce_chat(s) for s in elenco]}
        except Exception as e:
            self._log()
            return {"errore": str(e)}

    def _lavoro_parole(self, elenco) -> None:
        for s in elenco:
            prima = self._etichetta(s)
            parole.aggiorna_parole([s], self.cache / "parole.json", chiedi=self._chiedi)
            dopo = self._etichetta(s)
            if dopo != prima:
                self.emetti("chat", {"id": s.id, "etichetta": dopo})

    def _non_salvate(self, elenco) -> list:
        limite = self.adesso() - RECENTE
        return [s for s in elenco if s.ultima < limite and self._stato(s) == "non_salvata"]

    # ---------- home ----------
    def home(self) -> dict:
        try:
            adesso = self.adesso()
            self._aggiorna_date_git()
            elenco = self._sessioni()
            non_salvate = self._non_salvate(elenco)[:10]
            progetti = self._progetti()
            inbox = self._file_inbox()
            avvisi = []
            if non_salvate:
                n = len(non_salvate)
                avvisi.append({"tipo": "non_salvate", "livello": "attenzione",
                               "testo": f"{n} chat chius{'a' if n == 1 else 'e'} senza salvare gli appunti",
                               "chat": [self._voce_chat(s) for s in non_salvate]})
            for p in progetti:
                if p["giorni"] > GIORNI_FERMO:
                    avvisi.append({"tipo": "fermo", "livello": "info", "percorso": p["percorso"],
                                   "testo": f"{p['nome']}: appunti fermi da {int(p['giorni'])} giorni"})
            if inbox:
                n = len(inbox)
                avvisi.append({"tipo": "inbox", "livello": "info",
                               "testo": f"{n} not{'a' if n == 1 else 'e'} da smistare in Inbox"})
            self._in_thread("sync", self._lavoro_sync)
            self._in_thread("oggi", self._lavoro_oggi)
            self._in_thread("parole", self._lavoro_parole, elenco[:30])
            import percorsi
            return {"data": data_lunga(adesso), "saluto": saluto(adesso.hour), "nome": percorsi.leggi_config().get("nome"),
                    "dispositivo": os.environ.get("COMPUTERNAME", "").title(),
                    "sync": self.sync_stato, "oggi": self._oggi_dati(),
                    "avvisi": avvisi, "progetti": progetti, "inbox": len(inbox),
                    "chat": [self._voce_chat(s) for s in self._ordinate(elenco)[:8]]}
        except Exception as e:
            self._log()
            return {"errore": str(e)}

    def _progetti_attivi(self) -> list[Path]:
        # progetti della sezione "Progetti attivi" dell'indice ("Active projects" in inglese):
        # percorsi in backtick sotto Progetti/ (file CLAUDE.md o cartella), esclusi gli abbandonati
        st = mod_struttura.di(self.radice)
        try:
            indice = (self.radice / st["indice"]).read_text(encoding="utf-8")
        except OSError:
            return []
        m = re.search(RE_SEZIONE_PROGETTI, indice, re.S | re.M)
        if not m:
            return []
        abbandonati = mod_appunti._abbandonati(self.radice)
        visti, out = set(), []
        for riga in m.group(1).splitlines():
            if re.search(RE_ABBANDONATO, riga, re.I):
                continue
            for rel in re.findall(rf"`({re.escape(st['progetti'])}/[^`]+?)`", riga):
                p = self.radice / rel
                if p.is_dir():
                    p = p / "CLAUDE.md"
                if p.name == "CLAUDE.md" and p.is_file() and p.parent.name not in abbandonati and p not in visti:
                    visti.add(p)
                    out.append(p)
        return out

    def _progetti(self) -> list:
        out = []
        for p in self._progetti_attivi():
            if p.is_file():
                g = self._eta_giorni(p)
                out.append({"nome": p.parent.name, "percorso": _rel(p, self.radice),
                            "giorni": round(g, 1), "colore": mod_appunti.colore(g),
                            "aspetto": self._aspetto(p.parent)})
        return out

    # ---------- progetti nuovi ----------
    @staticmethod
    def _aspetto(cartella: Path) -> dict | None:
        try:
            import json
            d = json.loads((cartella / ".piastrella.json").read_text(encoding="utf-8"))
            return {k: d[k] for k in ("fondo", "emblema", "motivo") if isinstance(d.get(k), str)} or None
        except (OSError, ValueError, AttributeError):
            return None

    @staticmethod
    def _scrivi_aspetto(cartella: Path, fondo: str | None, emblema: str | None, motivo: str | None = None) -> None:
        import json
        dati = {}
        if motivo and re.fullmatch(r"[a-z]{2,12}", motivo):
            dati["motivo"] = motivo
        if fondo and re.fullmatch(r"#[0-9a-fA-F]{6}", fondo):
            dati["fondo"] = fondo
        if emblema and re.fullmatch(r"(f:)?[a-z][a-z-]{1,40}", emblema):
            dati["emblema"] = emblema
        (cartella / ".piastrella.json").write_text(json.dumps(dati), encoding="utf-8")

    def crea_progetto(self, nome: str, descrizione: str = "", fondo: str | None = None, emblema: str | None = None,
                      motivo: str | None = None) -> dict:
        # crea Progetti/<Nome>/CLAUDE.md + Output/ (regola dei progetti nuovi), salva l'aspetto
        # della piastrella e aggiunge il progetto alla sezione "Progetti attivi" di INDICE.md
        nome = " ".join((nome or "").split())
        descrizione = " ".join((descrizione or "").split())
        if not nome or len(nome) > 40 or re.search(r'[\\/:*?"<>|`]', nome) or nome.startswith("."):
            return {"errore": "Nome non valido: massimo 40 caratteri, senza / \\ : * ? \" < > |"}
        lin = mod_struttura.rileva(self.radice)
        st = mod_struttura.STRUTTURE[lin]
        cartella = self.radice / st["progetti"] / nome
        if cartella.exists():
            return {"errore": f"Esiste già un progetto \"{nome}\""}
        try:
            (cartella / st["output"]).mkdir(parents=True)
            oggi = f"{self.adesso():%Y-%m-%d}"
            testo = (f"# {nome} — status\n\n{descrizione or 'Project created from the app.'}\n\n"
                     f"## Done ({oggi})\n- Project created.\n\n## To do\n- Define goals and next steps.\n") if lin == "en" else (
                     f"# {nome} — stato\n\n{descrizione or 'Progetto creato dall’app.'}\n\n"
                     f"## Fatto ({oggi})\n- Progetto creato.\n\n## Da fare\n- Definire obiettivi e prossimi passi.\n")
            (cartella / "CLAUDE.md").write_text(testo, encoding="utf-8", newline="\n")
            self._scrivi_aspetto(cartella, fondo, emblema, motivo)
            self._aggiungi_all_indice(nome, descrizione)
        except OSError as e:
            return {"errore": str(e)}
        return {"ok": True, "nome": nome, "percorso": _rel(cartella / "CLAUDE.md", self.radice)}

    def _aggiungi_all_indice(self, nome: str, descrizione: str) -> None:
        lin = mod_struttura.rileva(self.radice)
        st = mod_struttura.STRUTTURE[lin]
        indice = self.radice / st["indice"]
        try:
            righe = indice.read_text(encoding="utf-8").splitlines()
        except OSError:
            righe = ["# Index" if lin == "en" else "# Indice"]
        voce = f"- **{nome}**{f' — {descrizione}' if descrizione else ''} → `{st['progetti']}/{nome}/CLAUDE.md`"
        inizio = next((i for i, r in enumerate(righe) if re.fullmatch(r"## (Progetti attivi|Active projects)", r.strip())), None)
        if inizio is None:
            righe += ["", SEZIONE_PROGETTI[lin], voce]
        else:
            fine = next((i for i in range(inizio + 1, len(righe)) if righe[i].startswith("## ")), len(righe))
            # prima delle righe "Piccoli..." / "Abbandonato..." se ci sono, altrimenti in fondo
            pos = next((i for i in range(inizio + 1, fine) if re.match(r"-\s*(Piccoli|Abbandonat|Small|Abandoned)", righe[i], re.I)), None)
            if pos is None:
                pos = fine
                while pos > inizio + 1 and not righe[pos - 1].strip():
                    pos -= 1
            righe.insert(pos, voce)
        indice.write_text("\n".join(righe) + "\n", encoding="utf-8", newline="\n")

    def cambia_aspetto(self, percorso: str, fondo: str | None, emblema: str | None, motivo: str | None = None) -> dict:
        p = self._sicuro(percorso)
        if p is None or p.name != "CLAUDE.md" or not p.is_file():
            return {"errore": "Progetto non trovato"}
        try:
            self._scrivi_aspetto(p.parent, fondo, emblema, motivo)
        except OSError as e:
            return {"errore": str(e)}
        return {"ok": True}

    def _oggi_dati(self) -> dict:
        return {"eventi": self.oggi_eventi, "scadenze": self.oggi_scadenze}

    def _lavoro_sync(self) -> None:
        # con la chiave dell'app il controllo non passa dal gestore credenziali di Windows
        self.sync_stato = mod_sync.stato_sync(self.radice, token=self.token_git())
        self.emetti("sync", {"stato": self.sync_stato})

    def _lavoro_oggi(self) -> None:
        self.oggi_eventi = mod_oggi.eventi_oggi(self.radice) or []
        self.emetti("oggi", self._oggi_dati())
        self.oggi_scadenze = mod_oggi.scadenze(self.radice, self.cache, self.adesso().date(),
                                               chiedi=self._chiedi)
        self.emetti("oggi", self._oggi_dati())

    # ---------- appunti ----------
    def appunti(self) -> dict:
        try:
            self._aggiorna_date_git()
            voci = []
            for a in mod_appunti.elenca_appunti(self.radice):
                g = self._eta_giorni(a.percorso)
                voci.append({"gruppo": a.gruppo, "nome": a.nome, "percorso": _rel(a.percorso, self.radice),
                             "giorni": round(g, 1), "colore": mod_appunti.colore(g),
                             "abbandonato": a.abbandonato})
            return {"appunti": voci}
        except Exception as e:
            self._log()
            return {"errore": str(e)}

    def leggi(self, rel: str) -> dict:
        p = self._sicuro(rel)
        if p is None or not p.is_file():
            return {"errore": "File non trovato"}
        try:
            return {"percorso": _rel(p, self.radice), "testo": p.read_text(encoding="utf-8"),
                    "mtime": p.stat().st_mtime, "giorni": round(self._eta_giorni(p), 1)}
        except (OSError, UnicodeDecodeError) as e:
            return {"errore": str(e)}

    def scrivi(self, rel: str, testo: str, mtime_atteso: float | None) -> dict:
        p = self._sicuro(rel)
        if p is None:
            return {"errore": "Percorso non valido"}
        try:
            if p.exists() and mtime_atteso is not None and abs(p.stat().st_mtime - mtime_atteso) > 0.001:
                return {"conflitto": True, "errore": "Il file è cambiato nel frattempo"}
            tmp = p.with_name(f".{p.name}.tmp")
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                f.write(testo)
            os.replace(tmp, p)
            return {"ok": True, "mtime": p.stat().st_mtime}
        except OSError as e:
            return {"errore": str(e)}

    def cerca(self, query: str) -> dict:
        q = (query or "").strip()
        if len(q) < 2:
            return {"risultati": []}
        parole_q = [w.lower() for w in q.split()]
        risultati = []
        for a in mod_appunti.elenca_appunti(self.radice):
            try:
                testo = a.percorso.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            basso = testo.lower()
            nome = a.nome.lower()
            if not all(w in basso or w in nome for w in parole_q):
                continue
            punti = sum(basso.count(w) for w in parole_q) + 10 * sum(w in nome for w in parole_q)
            i = basso.find(parole_q[0])
            inizio = max(0, i - 60) if i >= 0 else 0
            estratto = " ".join(testo[inizio:inizio + 200].split())
            risultati.append({"nome": a.nome, "gruppo": a.gruppo, "percorso": _rel(a.percorso, self.radice),
                              "estratto": estratto, "punti": punti})
        risultati.sort(key=lambda r: -r["punti"])
        return {"risultati": risultati[:MAX_RISULTATI]}

    # ---------- inbox e note ----------
    def _file_inbox(self) -> list[Path]:
        cartella = self.radice / "Inbox"
        if not cartella.is_dir():
            return []
        return sorted((p for p in cartella.iterdir() if p.is_file() and not p.name.startswith(".")),
                      key=lambda p: p.stat().st_mtime, reverse=True)

    def conta_inbox(self) -> dict:
        # controllo leggero e frequente: il numero sull'icona segue l'Inbox anche quando
        # la svuota Claude da un terminale
        try:
            cartella = self.radice / "Inbox"
            n = sum(1 for p in cartella.iterdir() if p.is_file() and not p.name.startswith(".")) if cartella.is_dir() else 0
        except OSError:
            n = 0
        return {"inbox": n}

    def inbox(self) -> dict:
        voci = []
        for p in self._file_inbox():
            anteprima = ""
            if p.suffix.lower() in (".md", ".txt"):
                try:
                    anteprima = p.read_text(encoding="utf-8", errors="replace")[:MAX_ANTEPRIMA]
                except OSError:
                    pass
            voci.append({"nome": p.name, "percorso": _rel(p, self.radice), "anteprima": anteprima,
                         "dimensione": p.stat().st_size,
                         "modificato": datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat()})
        return {"inbox": voci}

    def aggiungi_inbox(self, percorsi: list[str]) -> dict:
        # file trascinati nell'app: copiati in Inbox/ con la data davanti (regola dei
        # documenti: "AAAA-MM-GG descrizione.ext"), mai sovrascrivendo; le cartelle si saltano
        import shutil
        cartella = self.radice / "Inbox"
        cartella.mkdir(parents=True, exist_ok=True)
        oggi = f"{self.adesso():%Y-%m-%d}"
        aggiunti, saltati = [], []
        for percorso in percorsi or []:
            p = Path(percorso)
            if not p.is_file():
                saltati.append(p.name or str(p))
                continue
            nome = p.name if re.match(r"^\d{4}-\d{2}-\d{2} ", p.name) else f"{oggi} {p.name}"
            dest, n = cartella / nome, 2
            while dest.exists():
                dest = cartella / f"{Path(nome).stem}-{n}{p.suffix}"
                n += 1
            try:
                shutil.copy2(p, dest)
                aggiunti.append(dest.name)
            except OSError:
                saltati.append(p.name)
        return {"aggiunti": aggiunti, "saltati": saltati}

    def nota(self, testo: str) -> dict:
        adesso = self.adesso()
        try:
            p = mod_note.salva_nota_subito(testo, self.radice / "Inbox", adesso)
        except ValueError:
            return {"errore": "Nota vuota"}
        except OSError as e:
            return {"errore": str(e)}

        def rinomina():
            nuovo = mod_note.rinomina_nota(p, testo, adesso, chiedi=self._chiedi)
            if nuovo != p:
                self.emetti("nota", {"nome": nuovo.name})
        self._in_thread(f"nota-{p.name}", rinomina)
        return {"ok": True, "nome": p.name}

    # ---------- terminali ----------
    def apri_chat(self, tipo: str = "nuova", sessione: str | None = None, prompt: str | None = None,
                  cartella: str | None = None, titolo: str | None = None, modello: str | None = None,
                  assistente: str | None = None) -> dict:
        # cartella: dove lavora Claude (predefinita: il second brain); deve esistere.
        # modello: "fable" / "opus" / "sonnet" / "haiku" per le chat nuove (Impostazioni > Terminale)
        # assistente: "codex" / "agy" solo per una chat nuova e vuota; riprendere una chat e i
        # comandi dell'app (briefing, smista l'inbox...) sono cose di Claude e usano sempre lui
        if self.terminali is None:
            return {"errore": "Terminale non disponibile"}
        if tipo == "riprendi" and sessione:
            for t in self.terminali.attive():
                if t.sessione == sessione:
                    return self._voce_scheda(t)
        dove = self.radice
        if cartella:
            dove = Path(cartella)
            if not dove.is_absolute() or not dove.is_dir():
                return {"errore": f"La cartella non esiste: {cartella}"}
        if tipo == "nuova" and not prompt and assistente in ("codex", "agy"):
            argv = self._comando_assistente(assistente)
            if argv is None:
                return {"errore": f"{ASSISTENTI[assistente]} non è installato su questo PC"}
            try:
                t = self.terminali.apri(argv, str(dove), (titolo or "").strip()[:60] or ASSISTENTI[assistente],
                                        assistente=assistente)
            except Exception as e:
                self._log()
                return {"errore": f"Non riesco ad avviare {ASSISTENTI[assistente]}: {e}"}
            return self._voce_scheda(t)
        argv = [str(CLAUDE)]
        if tipo != "riprendi" and modello in MODELLI_CLAUDE:
            argv += ["--model", modello]
        nome_scelto = (titolo or "").strip()[:60]
        titolo = "Nuova chat"
        if tipo in ("riprendi", "duplica") and sessione:
            argv += ["--resume", sessione]
            s = next((x for x in self._sessioni() if x.id == sessione), None)
            titolo = self._etichetta(s) if s else "Chat"
            if tipo == "duplica":
                # copia della conversazione con un id nuovo: l'originale resta com'e'
                argv.append("--fork-session")
                titolo = f"{titolo} (copia)"
        if prompt:
            argv.append(prompt)
            if tipo != "riprendi":
                titolo = prompt.capitalize()
        if nome_scelto:
            titolo = nome_scelto
        try:
            t = self.terminali.apri(argv, str(dove), titolo, sessione=None if tipo == "duplica" else sessione)
            if tipo == "duplica":
                t.nome_scelto = True  # quando la copia ha il suo id, il titolo "(copia)" le resta
        except Exception as e:
            self._log()
            return {"errore": f"Non riesco ad avviare Claude: {e}"}
        return self._voce_scheda(t)

    @staticmethod
    def _comando_assistente(nome: str) -> list[str] | None:
        # eseguibile nel PATH; i .cmd di npm (codex) passano da cmd.exe, che il terminale non avvia da solo
        trovato = shutil.which(nome)
        if not trovato:
            return None
        if trovato.lower().endswith((".cmd", ".bat")):
            return [os.environ.get("COMSPEC", "cmd.exe"), "/c", trovato]
        return [trovato]

    def assistenti(self) -> dict:
        # quali assistenti si possono scegliere per una chat nuova su questo PC
        return {"assistenti": [{"id": k, "nome": n, "installato": k == "claude" or self._comando_assistente(k) is not None}
                               for k, n in ASSISTENTI.items()]}

    def salva_chat(self, sessione: str) -> dict:
        return self.apri_chat("riprendi", sessione, PROMPT_SALVA[mod_struttura.rileva(self.radice)])

    # Eliminare una chat (tasto destro): il trascritto <id>.jsonl e la sua cartella <id>/
    # (sotto-agenti, file temporanei) non si cancellano subito ma vanno nel cestino dell'app,
    # cache/cestino-chat/<id>/, da cui "Annulla" li rimette a posto. Il cestino si svuota da
    # solo dopo GIORNI_CESTINO. Una chat aperta in una linguetta non si elimina.
    GIORNI_CESTINO = 30

    def _id_valido(self, sessione) -> bool:
        return isinstance(sessione, str) and bool(re.fullmatch(r"[0-9A-Za-z_-]{1,80}", sessione))

    def elimina_chat(self, sessione: str) -> dict:
        if not self._id_valido(sessione):
            return {"errore": "Chat non valida"}
        if any(t.sessione == sessione for t in (self.terminali.attive() if self.terminali else [])):
            return {"errore": "La chat è aperta in una linguetta: chiudila prima di eliminarla"}
        trascritto = self.cartella_sessioni / f"{sessione}.jsonl"
        if not trascritto.exists():
            return {"errore": "Chat non trovata"}
        try:
            cestino = self.cache / "cestino-chat"
            self._svuota_cestino(cestino)
            dest = cestino / sessione
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            dest.mkdir(parents=True)
            shutil.move(str(trascritto), str(dest / trascritto.name))
            cartella = self.cartella_sessioni / sessione
            if cartella.is_dir():
                shutil.move(str(cartella), str(dest / sessione))
        except OSError as e:
            self._log()
            return {"errore": f"Non riesco a eliminare la chat: {e}"}
        self._sessioni_cache.pop(sessione, None)
        self.emetti("chat-eliminata", {"id": sessione})
        return {"ok": True}

    def ripristina_chat(self, sessione: str) -> dict:
        if not self._id_valido(sessione):
            return {"errore": "Chat non valida"}
        dest = self.cache / "cestino-chat" / sessione
        trascritto = dest / f"{sessione}.jsonl"
        if not trascritto.exists():
            return {"errore": "La chat non è più nel cestino"}
        try:
            if (self.cartella_sessioni / trascritto.name).exists():
                return {"errore": "Esiste già una chat con lo stesso id"}
            shutil.move(str(trascritto), str(self.cartella_sessioni / trascritto.name))
            if (dest / sessione).is_dir() and not (self.cartella_sessioni / sessione).exists():
                shutil.move(str(dest / sessione), str(self.cartella_sessioni / sessione))
            shutil.rmtree(dest, ignore_errors=True)
        except OSError as e:
            self._log()
            return {"errore": f"Non riesco a ripristinare la chat: {e}"}
        self.emetti("chat-eliminata", {"id": sessione, "ripristinata": True})
        return {"ok": True}

    def _svuota_cestino(self, cestino: Path) -> None:
        limite = time.time() - self.GIORNI_CESTINO * 86400
        for d in (cestino.iterdir() if cestino.is_dir() else []):
            try:
                if d.stat().st_mtime < limite:
                    if d.is_dir():
                        shutil.rmtree(d, ignore_errors=True)
                    else:
                        d.unlink()
            except OSError:
                pass

    def cestino_chat(self) -> dict:
        # chat eliminate, per Impostazioni > Dati: la piu' recente per prima
        voci = []
        cestino = self.cache / "cestino-chat"
        for d in (cestino.iterdir() if cestino.is_dir() else []):
            trascritto = d / f"{d.name}.jsonl"
            try:
                s = mod_sessioni._leggi(trascritto) if trascritto.exists() else None
                quando = d.stat().st_mtime
            except OSError:
                continue
            if s is None:
                continue
            voci.append({"id": d.name, "etichetta": self._etichetta(s), "ultima": s.ultima.isoformat(),
                         "eliminata": datetime.fromtimestamp(quando).astimezone().isoformat(),
                         "giorni_rimasti": max(0, self.GIORNI_CESTINO - int((time.time() - quando) / 86400))})
        voci.sort(key=lambda v: v["eliminata"], reverse=True)
        return {"cestino": voci, "giorni": self.GIORNI_CESTINO}

    def elimina_per_sempre(self, sessione: str) -> dict:
        if not self._id_valido(sessione):
            return {"errore": "Chat non valida"}
        dest = self.cache / "cestino-chat" / sessione
        if not dest.is_dir():
            return {"errore": "La chat non è più nel cestino"}
        shutil.rmtree(dest, ignore_errors=True)
        self._dimentica(sessione)
        return {"ok": True}

    def svuota_cestino_chat(self) -> dict:
        cestino = self.cache / "cestino-chat"
        n = 0
        for d in (cestino.iterdir() if cestino.is_dir() else []):
            shutil.rmtree(d, ignore_errors=True)
            self._dimentica(d.name)
            n += 1
        return {"ok": True, "conto": n}

    def _dimentica(self, sessione: str) -> None:
        meta = self._meta()
        if sessione in meta["titoli"] or sessione in meta["fissate"]:
            meta["titoli"].pop(sessione, None)
            meta["fissate"] = [x for x in meta["fissate"] if x != sessione]
            self._salva_meta(meta)

    # ---------- altre azioni sulle chat (tasto destro) ----------
    def _sessione(self, sessione):
        return next((s for s in self._sessioni() if s.id == sessione), None) if self._id_valido(sessione) else None

    def _imposta_titolo(self, sessione: str, titolo: str) -> None:
        meta = self._meta()
        if titolo:
            meta["titoli"][sessione] = titolo
        else:
            meta["titoli"].pop(sessione, None)
        self._salva_meta(meta)

    def rinomina_chat(self, sessione: str, titolo: str) -> dict:
        # titolo vuoto: si torna alle parole chiave automatiche
        s = self._sessione(sessione)
        if s is None:
            return {"errore": "Chat non trovata"}
        titolo = chat_extra.pulisci_titolo(titolo)
        self._imposta_titolo(sessione, titolo)
        etichetta = self._etichetta(s)
        for t in (self.terminali.schede.values() if self.terminali else []):
            if t.sessione == sessione:
                t.titolo = etichetta
        self.emetti("chat", {"id": sessione, "etichetta": etichetta, "rinominata": bool(titolo)})
        return {"ok": True, "etichetta": etichetta}

    def rinomina_scheda(self, sid: str, titolo: str) -> dict:
        # linguetta aperta: se conosce gia' la sua chat il nome vale anche per la chat,
        # altrimenti lo riceve appena la chat nuova ha il suo id (_risolvi_schede)
        t = self.terminali.schede.get(sid) if self.terminali else None
        if t is None:
            return {"errore": "Linguetta non trovata"}
        if t.sessione and self._sessione(t.sessione):
            return self.rinomina_chat(t.sessione, titolo)
        titolo = chat_extra.pulisci_titolo(titolo)
        if not titolo:
            return {"errore": "Scrivi un nome"}
        t.titolo, t.nome_scelto = titolo, True
        return {"ok": True, "etichetta": titolo}

    def fissa_chat(self, sessione: str, fissa: bool = True) -> dict:
        if self._sessione(sessione) is None:
            return {"errore": "Chat non trovata"}
        meta = self._meta()
        meta["fissate"] = [x for x in meta["fissate"] if x != sessione] + ([sessione] if fissa else [])
        self._salva_meta(meta)
        self.emetti("chat-cambiate", {"id": sessione})
        return {"ok": True}

    def apri_in_cartella(self, sessione: str, cartella: str) -> dict:
        # Claude riprende una chat solo dalla cartella in cui e' nata: si copia il trascritto
        # nella cartella delle chat dell'altra cartella e lo si riprende da li'. I messaggi
        # nuovi finiscono nella copia; l'originale qui resta com'era.
        s = self._sessione(sessione)
        if s is None:
            return {"errore": "Chat non trovata"}
        dove = Path(cartella or "")
        if not dove.is_absolute() or not dove.is_dir():
            return {"errore": f"La cartella non esiste: {cartella}"}
        destinazione = cartella_sessioni_di(dove)
        if destinazione.resolve() != self.cartella_sessioni.resolve():
            try:
                destinazione.mkdir(parents=True, exist_ok=True)
                copia = destinazione / s.percorso.name
                if not copia.exists() or copia.stat().st_mtime < s.percorso.stat().st_mtime:
                    shutil.copy2(s.percorso, copia)
            except OSError as e:
                self._log()
                return {"errore": f"Non riesco a copiare la chat: {e}"}
        for t in (self.terminali.attive() if self.terminali else []):
            if t.sessione == sessione:
                return {"errore": "La chat è già aperta in una linguetta: chiudila prima"}
        return self.apri_chat("riprendi", sessione, cartella=str(dove), titolo=f"{self._etichetta(s)} · {dove.name}")

    def esporta_chat(self, sessione: str) -> dict:
        s = self._sessione(sessione)
        if s is None:
            return {"errore": "Chat non trovata"}
        try:
            p = chat_extra.esporta_markdown(s, self._etichetta(s), self.radice / "Inbox")
        except OSError as e:
            self._log()
            return {"errore": f"Non riesco a esportare la chat: {e}"}
        return {"ok": True, "nome": p.name, "percorso": _rel(p, self.radice)}

    def riga_registro(self, sessione: str) -> dict:
        s = self._sessione(sessione)
        if s is None:
            return {"errore": "Chat non trovata"}
        registro = self.radice / mod_struttura.di(self.radice)["registro"]
        riga = chat_extra.riga_registro(registro, s, self._etichetta(s))
        if not riga:
            return {"errore": "Nel Registro non trovo una riga per questa chat (forse non è stata salvata)"}
        return {"percorso": _rel(registro, self.radice), "riga": riga}

    def cerca_chat(self, query: str) -> dict:
        # nel testo completo di domande e risposte, gia' in memoria: pochi millisecondi
        try:
            inizio = time.perf_counter()
            trovate = chat_extra.cerca_nel_testo(self._sessioni(), str(query or "")[:200])
            return {"trovate": trovate, "ms": round((time.perf_counter() - inizio) * 1000, 1)}
        except Exception as e:
            self._log()
            return {"errore": str(e)}

    # ---------- Inbox: tasto destro ----------
    def _file_inbox_sicuro(self, rel: str) -> Path | None:
        try:
            p = (self.radice / rel).resolve()
            p.relative_to((self.radice / "Inbox").resolve())
        except (ValueError, OSError):
            return None
        return p if p.is_file() else None

    def elimina_inbox(self, rel: str) -> dict:
        p = self._file_inbox_sicuro(rel)
        if p is None:
            return {"errore": "File non trovato nell'Inbox"}
        cestino = self.cache / "cestino-inbox"
        try:
            cestino.mkdir(parents=True, exist_ok=True)
            self._svuota_cestino(cestino)
            chiave = f"{int(time.time() * 1000)}-{p.name}"
            shutil.move(str(p), str(cestino / chiave))
        except OSError as e:
            self._log()
            return {"errore": f"Non riesco a eliminare il file: {e}"}
        return {"ok": True, "chiave": chiave}

    def ripristina_inbox(self, chiave: str) -> dict:
        if not isinstance(chiave, str) or "/" in chiave or "\\" in chiave or ".." in chiave:
            return {"errore": "File non valido"}
        sorgente = self.cache / "cestino-inbox" / chiave
        if not sorgente.is_file():
            return {"errore": "Il file non è più nel cestino"}
        nome = chiave.split("-", 1)[1] if "-" in chiave else chiave
        dest = self.radice / "Inbox" / nome
        if dest.exists():
            return {"errore": "Nell'Inbox c'è già un file con lo stesso nome"}
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(sorgente), str(dest))
        except OSError as e:
            return {"errore": f"Non riesco a ripristinare il file: {e}"}
        return {"ok": True}

    def rinomina_inbox(self, rel: str, nome: str) -> dict:
        p = self._file_inbox_sicuro(rel)
        if p is None:
            return {"errore": "File non trovato nell'Inbox"}
        nome = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(nome or "")).strip().rstrip(".")[:120]
        if not nome:
            return {"errore": "Scrivi un nome"}
        if not Path(nome).suffix and p.suffix:
            nome += p.suffix  # l'estensione resta quella di prima se non la scrivi
        dest = p.with_name(nome)
        if dest.exists() and dest != p:
            return {"errore": "Esiste già un file con questo nome"}
        try:
            p.rename(dest)
        except OSError as e:
            return {"errore": f"Non riesco a rinominare il file: {e}"}
        return {"ok": True, "nome": dest.name, "percorso": _rel(dest, self.radice)}

    def sposta_inbox(self, rel: str, progetto: str) -> dict:
        # nella cartella di un progetto (percorso del suo CLAUDE.md, come in home.progetti)
        p = self._file_inbox_sicuro(rel)
        if p is None:
            return {"errore": "File non trovato nell'Inbox"}
        stato = self._sicuro(progetto)
        if stato is None or not stato.exists():
            return {"errore": "Progetto non trovato"}
        dest = stato.parent / p.name
        if dest.exists():
            return {"errore": f"In {stato.parent.name} c'è già un file con lo stesso nome"}
        try:
            shutil.move(str(p), str(dest))
        except OSError as e:
            return {"errore": f"Non riesco a spostare il file: {e}"}
        return {"ok": True, "percorso": _rel(dest, self.radice), "progetto": stato.parent.name}

    def _voce_scheda(self, t) -> dict:
        return {"id": t.id, "titolo": t.titolo, "sessione": t.sessione, "url": self.terminali.url(t.id),
                "chiusa": t.codice is not None, "assistente": getattr(t, "assistente", "claude")}

    def schede(self) -> dict:
        if self.terminali is None:
            return {"schede": []}
        try:
            self._risolvi_schede()
        except Exception:
            self._log()
        return {"schede": [self._voce_scheda(t) for t in self.terminali.schede.values()]}

    def _risolvi_schede(self) -> None:
        # una chat nuova non sa ancora il suo id: lo deduce dal trascritto nato dopo l'apertura
        # della scheda; poi il titolo diventa le parole chiave (se la scheda non ha un comando)
        senza = sorted((t for t in self.terminali.schede.values()
                        if t.sessione is None and getattr(t, "assistente", "claude") == "claude"),
                       key=lambda t: t.aperta_il)
        if not senza:
            return
        usate = {t.sessione for t in self.terminali.schede.values() if t.sessione}
        nuove = sorted((s for s in self._sessioni() if s.id not in usate),
                       key=lambda s: s.percorso.stat().st_ctime)
        for t in senza:
            s = next((s for s in nuove if s.percorso.stat().st_ctime >= t.aperta_il - 2), None)
            if s is None:
                continue
            nuove.remove(s)
            t.sessione = s.id
            if getattr(t, "nome_scelto", False):
                self._imposta_titolo(s.id, t.titolo)
            elif t.titolo == "Nuova chat":
                t.titolo = self._etichetta(s)

    def chiudi_scheda(self, sid: str) -> dict:
        if self.terminali:
            self.terminali.chiudi(sid)
        return {"ok": True}

    def scheda_chiusa(self, scheda) -> None:
        # chiamata dal thread del terminale quando claude esce: individua la sessione e,
        # dopo l'attesa dello hook, dice all'interfaccia se gli appunti risultano non salvati
        def lavoro():
            if getattr(scheda, "assistente", "claude") != "claude":
                # Codex e Antigravity non hanno sessioni di Claude ne' appunti da salvare
                self.emetti("scheda", {"id": scheda.id, "chiusa": True, "sessione": None})
                return
            sid = scheda.sessione
            if sid is None:
                nuove = [s for s in self._sessioni() if s.ultima.timestamp() >= scheda.aperta_il - 2]
                sid = max(nuove, key=lambda s: s.ultima).id if nuove else None
                scheda.sessione = sid
            self.emetti("scheda", {"id": scheda.id, "chiusa": True, "sessione": sid})
            if not sid:
                return
            time.sleep(4)
            s = next((x for x in self._sessioni() if x.id == sid), None)
            stato = salvataggio.stato_salvataggio(s, self.segni) if s else "breve"
            self.emetti("scheda", {"id": scheda.id, "chiusa": True, "sessione": sid, "stato": stato})
        self._in_thread(f"chiusa-{scheda.id}", lavoro)

    # ---------- varie ----------
    def apri_esterno(self, rel: str) -> dict:
        p = self._sicuro(rel, suffissi=(".md", ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx"))
        if p is None or not p.exists():
            return {"errore": "File non trovato"}
        try:
            os.startfile(str(p))  # type: ignore[attr-defined]
            return {"ok": True}
        except OSError as e:
            return {"errore": str(e)}

    def apri_cartella(self) -> dict:
        try:
            os.startfile(str(self.radice))  # type: ignore[attr-defined]
            return {"ok": True}
        except OSError as e:
            return {"errore": str(e)}

    def stato_git(self) -> dict:
        # per la barra di stato: ramo, file modificati non ancora caricati, commit da caricare
        def git(*args):
            r = subprocess.run(["git", *args], cwd=self.radice, capture_output=True, text=True,
                               encoding="utf-8", timeout=10, creationflags=_FLAGS,
                               env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
            return r.stdout.strip() if r.returncode == 0 else ""
        try:
            ramo = git("rev-parse", "--abbrev-ref", "HEAD")
            modifiche = len([r for r in git("status", "--porcelain").splitlines() if r.strip()])
            conto = git("rev-list", "--left-right", "--count", "HEAD...@{u}").split()
            avanti = int(conto[0]) if len(conto) == 2 else 0
            return {"ramo": ramo, "modifiche": modifiche, "da_caricare": avanti, "sync": self.sync_stato}
        except (OSError, subprocess.SubprocessError, ValueError):
            return {"ramo": "", "modifiche": 0, "da_caricare": 0, "sync": self.sync_stato}

    def attivita(self, settimane: int = 26) -> dict:
        # file di appunti modificati per giorno (dalla cronologia git) e per area negli ultimi
        # 30 giorni: per il calendario dell'attivita' nella pagina Mappa
        try:
            r = subprocess.run(["git", "log", f"--since={settimane}.weeks", "--format=@%ct", "--name-only"],
                               cwd=self.radice, capture_output=True, text=True, encoding="utf-8",
                               timeout=20, creationflags=_FLAGS,
                               env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        except (OSError, subprocess.SubprocessError):
            return {"giorni": {}, "aree": {}}
        if r.returncode != 0:
            return {"giorni": {}, "aree": {}}
        st = mod_struttura.di(self.radice)
        giorni, aree, quando = {}, {}, None
        limite_aree = time.time() - 30 * 86400
        for riga in r.stdout.splitlines():
            if riga.startswith("@"):
                try:
                    quando = float(riga[1:])
                except ValueError:
                    quando = None
                continue
            rel = riga.strip().strip('"')
            if not rel or quando is None or not rel.endswith(".md"):
                continue
            giorno = datetime.fromtimestamp(quando).date().isoformat()
            giorni[giorno] = giorni.get(giorno, 0) + 1
            if quando >= limite_aree:
                testa = rel.split("/", 1)[0] if "/" in rel else ""
                area = "Progetti" if testa == st["progetti"] else (testa and mod_struttura.gruppo(testa, st)) or "Generali"
                aree[area] = aree.get(area, 0) + 1
        return {"giorni": giorni, "aree": aree}

    def uso(self) -> dict:
        # uso del piano Claude (5 ore e settimana) scritto dalla riga di stato di Claude Code
        # in cache/uso.json; una finestra gia' ripartita vale 0%
        try:
            import json
            dati = json.loads((self.cache / "uso.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"noto": False}
        adesso = time.time()
        out = {"noto": True, "aggiornato": dati.get("aggiornato")}
        for k in ("five_hour", "seven_day"):
            w = dati.get(k) or {}
            p, reset = w.get("used_percentage"), w.get("resets_at")
            if p is None:
                continue
            if reset and reset <= adesso:
                p, reset = 0, None
            out[k] = {"percentuale": round(float(p)), "azzera": reset}
        return out

    def mappa(self) -> dict:
        # grafo del second brain: un nodo per appunto, archi quando un appunto ne cita un altro
        # (percorso in backtick, link Markdown o nome di un progetto in grassetto)
        try:
            self._aggiorna_date_git()
            elenco = mod_appunti.elenca_appunti(self.radice)
            nodi, testi = [], {}
            per_nome = {}
            for a in elenco:
                rel = _rel(a.percorso, self.radice)
                g = self._eta_giorni(a.percorso)
                try:
                    testi[rel] = a.percorso.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    testi[rel] = ""
                nodi.append({"id": rel, "nome": a.nome, "gruppo": a.gruppo, "giorni": round(g, 1),
                             "colore": mod_appunti.colore(g), "abbandonato": a.abbandonato,
                             "peso": len(testi[rel])})
                per_nome[a.nome.lower()] = rel
            archi = set()
            st = mod_struttura.di(self.radice)
            fissi = (st["registro"].split("/")[-1], st["indice"])
            for rel, testo in testi.items():
                basso = testo.lower()
                for altro in testi:
                    if altro != rel and (altro.lower() in basso or altro.split("/")[-1].lower() in basso
                                         and altro.endswith(fissi)):
                        archi.add(tuple(sorted((rel, altro))))
                for nome, altro in per_nome.items():
                    if altro != rel and len(nome) > 3 and f"**{nome}**" in basso:
                        archi.add(tuple(sorted((rel, altro))))
            return {"nodi": nodi, "archi": [{"da": a, "a": b} for a, b in sorted(archi)]}
        except Exception as e:
            self._log()
            return {"errore": str(e)}

    def stato_notifiche(self) -> dict:
        # usato dall'area di notifica: cosa merita una notifica di Windows adesso
        elenco = self._sessioni()
        return {"non_salvate": [self._voce_chat(s) for s in self._non_salvate(elenco)[:5]],
                "inbox": len(self._file_inbox()), "sync": self.sync_stato,
                "scadenze": self.oggi_scadenze}
