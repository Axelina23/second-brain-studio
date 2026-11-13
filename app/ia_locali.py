"""Motore locale condiviso: nessun avvio implicito, nessuna modifica agli account cloud."""
import copy
import http.client
import json
import hashlib
import os
import re
import socket
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PREDEFINITE = {"eseguibile": "", "porta": 8087, "modelli": {}, "inattivita_secondi": 300,
               "cartelle_modelli": [], "contesto": 32768, "dflash": False, "visione": False,
               "compattazione_automatica": False,
               "cache_ram_mib": 512, "checkpoint": 2, "cache_kv": "q8_0", "mmap": False, "layer_gpu": -1}
MODELLI_CLIENT = {"claude", "codex"}
VELOCITA = re.compile(r"(prompt )?eval time\s*=.*?([\d.]+) tokens per second")


def normalizza_anthropic(corpo):
    corpo = copy.deepcopy(corpo)
    sistema = corpo.get("system", [])
    if isinstance(sistema, str):
        sistema = [{"type": "text", "text": sistema}]
    messaggi = []
    for messaggio in corpo.get("messages", []):
        if messaggio.get("role") in ("system", "developer"):
            contenuto = messaggio.get("content", "")
            sistema.extend([{"type": "text", "text": contenuto}] if isinstance(contenuto, str) else contenuto)
        else:
            messaggi.append(messaggio)
    if "messages" in corpo:
        corpo["messages"] = messaggi
    if sistema:
        corpo["system"] = "\n\n".join(x.get("text", "") for x in sistema if x.get("type") == "text")
    return corpo


def argomenti_server(cfg, modello, contesto=8192, dflash=True, visione=False):
    cfg = {**PREDEFINITE, **cfg}
    if type(contesto) is not int or contesto not in (4096, 8192, 16384, 32768, 65536, 131072):
        raise ValueError("Contesto non valido")
    if type(dflash) is not bool or type(visione) is not bool:
        raise ValueError("DFlash e visione devono essere booleani")
    voce = cfg["modelli"].get(modello)
    if not voce:
        raise ValueError("Modello locale non configurato")
    richiesti = [cfg["eseguibile"], voce.get("file", "")]
    if dflash:
        richiesti.append(voce.get("draft", ""))
    if visione:
        richiesti.append(voce.get("proiettore", ""))
    if any(not p or not Path(p).is_absolute() or not Path(p).is_file() for p in richiesti):
        raise ValueError("Eseguibile, modello o componenti richiesti mancanti")
    argv = [cfg["eseguibile"], "-m", voce["file"], "--host", "127.0.0.1", "--port", str(cfg["porta"]),
            "--alias", "qwen-locale", "-ngl", "all" if cfg["layer_gpu"] == -1 else str(cfg["layer_gpu"]),
            "--fit", "off", "-c", str(contesto), "-np", "1",
            "-b", "256", "-ub", "128", "-fa", "on", "-ctk", cfg["cache_kv"], "-ctv", cfg["cache_kv"],
            "--jinja", "--reasoning", "off", "--cache-ram", str(cfg["cache_ram_mib"]),
            "--ctx-checkpoints", str(cfg["checkpoint"]), "--sleep-idle-seconds", str(cfg["inattivita_secondi"] or -1), "--metrics"]
    argv += ["--load-mode", "mmap" if cfg["mmap"] else "none"]
    if dflash:
        argv += ["-md", voce["draft"], "--spec-type", "draft-dflash", "--spec-draft-n-max", "7",
                 "--spec-draft-ngl", "all"]
    if visione:
        argv += ["--mmproj", voce["proiettore"]]
    return argv


class GestoreLocale:
    def __init__(self, cartella, emetti=None, popen=subprocess.Popen, salute=None, orologio=time.monotonic):
        self.cartella = Path(cartella)
        self.emetti = emetti or (lambda nome, dati: None)
        self._popen, self._salute, self._ora = popen, salute or self._controlla_salute, orologio
        self._lock = threading.RLock()
        self._processo = None
        self._ponte = None
        self._config = self._leggi_config()
        self._stato = {"stato": "spento", "modello": None, "contesto": None, "dflash": False, "visione": False}
        self._client = set()
        self._ultimo_uso = self._ora()

    def _leggi_config(self):
        try:
            cfg = json.loads((self.cartella / "config.json").read_text(encoding="utf-8"))
            return self._valida_config(cfg)
        except (OSError, ValueError, TypeError):
            return copy.deepcopy(PREDEFINITE)

    @staticmethod
    def _valida_config(cfg):
        if not isinstance(cfg, dict) or set(cfg) - set(PREDEFINITE):
            raise ValueError("Configurazione locale non valida")
        nuova = {**copy.deepcopy(PREDEFINITE), **cfg}
        if type(nuova["porta"]) is not int or not 1024 <= nuova["porta"] <= 65535:
            raise ValueError("Porta non valida")
        if type(nuova["inattivita_secondi"]) is not int or not (nuova["inattivita_secondi"] == 0 or 30 <= nuova["inattivita_secondi"] <= 86400):
            raise ValueError("Inattivita non valida: zero oppure da 30 a 86400 secondi")
        for chiave, minimo, massimo in (("cache_ram_mib", 0, 8192), ("checkpoint", 0, 8), ("layer_gpu", -1, 200)):
            if type(nuova[chiave]) is not int or not minimo <= nuova[chiave] <= massimo:
                raise ValueError(f"Limite non valido: {chiave}")
        if nuova["contesto"] not in (4096, 8192, 16384, 32768, 65536, 131072) or type(nuova["contesto"]) is not int:
            raise ValueError("Contesto non valido")
        if nuova["cache_kv"] not in ("f16", "q8_0", "q4_0") or any(type(nuova[k]) is not bool for k in ("mmap", "dflash", "visione", "compattazione_automatica")):
            raise ValueError("Profilo memoria non valido")
        if not isinstance(nuova["cartelle_modelli"], list) or len(nuova["cartelle_modelli"]) > 12 or any(
                not isinstance(p, str) or not Path(p).is_absolute() for p in nuova["cartelle_modelli"]):
            raise ValueError("Cartelle modelli non valide")
        if not isinstance(nuova["modelli"], dict) or not isinstance(nuova["eseguibile"], str):
            raise ValueError("Catalogo locale non valido")
        for chiave, voce in nuova["modelli"].items():
            if not isinstance(chiave, str) or not chiave or not isinstance(voce, dict):
                raise ValueError("Voce modello non valida")
            if set(voce) - {"nome", "file", "draft", "proiettore"} or any(not isinstance(x, str) for x in voce.values()):
                raise ValueError("Percorsi del modello non validi")
        return nuova

    def configura(self, cfg):
        nuova = self._valida_config(cfg)
        with self._lock:
            if self._vivo():
                raise ValueError("Arrestare il server prima di cambiare configurazione")
            self.cartella.mkdir(parents=True, exist_ok=True)
            temporaneo = self.cartella / "config.json.tmp"
            temporaneo.write_text(json.dumps(nuova, ensure_ascii=False, indent=2), encoding="utf-8")
            temporaneo.replace(self.cartella / "config.json")
            self._config = nuova
        return self.catalogo()

    def _modelli_disponibili(self):
        modelli = copy.deepcopy(self._config["modelli"])
        noti = {os.path.normcase(str(Path(v.get("file", "")).resolve())) for v in modelli.values()}
        noti.update(os.path.normcase(str(Path(v[k]).resolve())) for v in modelli.values()
                    for k in ("draft", "proiettore") if v.get(k))
        radici = set(self._config["cartelle_modelli"])
        radici.update(str(Path(v["file"]).parent) for v in modelli.values() if v.get("file"))
        visitati = 0
        for radice in sorted(radici):
            for cartella, sottocartelle, nomi in os.walk(radice):
                visitati += 1
                if visitati > 1000:
                    break
                if len(Path(cartella).relative_to(radice).parts) >= 4:
                    sottocartelle[:] = []
                for nome in nomi:
                    basso = nome.lower()
                    if not basso.endswith(".gguf") or any(x in basso for x in ("mmproj", "dflash", "draft", "embedding")):
                        continue
                    if "-of-" in basso and "-00001-of-" not in basso:
                        continue
                    p = Path(cartella) / nome
                    identita = os.path.normcase(str(p.resolve()))
                    if identita in noti:
                        continue
                    noti.add(identita)
                    chiave = "gguf-" + hashlib.sha256(identita.encode()).hexdigest()[:16]
                    modelli[chiave] = {"nome": p.stem.replace("-", " "), "file": str(p)}
        return modelli

    def catalogo(self):
        with self._lock:
            cfg = copy.deepcopy(self._config)
            modelli = self._modelli_disponibili()
        def dimensione(voce):
            try:
                return round(Path(voce.get("file", "")).stat().st_size / 1e9, 2)
            except OSError:
                return None
        return {"configurazione": cfg, "modelli": [{"id": k, **v, "dimensione_gb": dimensione(v),
                "disponibile": Path(v.get("file", "")).is_file()} for k, v in modelli.items()],
                "funzioni": {"file": True, "ricerca_web": False, "lettura_siti": False,
                             "browser": False, "visione": "richiede_proiettore"}}

    def _vivo(self):
        return self._processo is not None and self._processo.poll() is None

    def stato(self):
        with self._lock:
            return {**self._stato, "pid": self._processo.pid if self._vivo() else None,
                    "client": len(self._client), "url": f"http://127.0.0.1:{self._config['porta']}"}

    def _notifica(self):
        self.emetti("ia-locale", self.stato())

    def _controlla_salute(self):
        # Nessun proxy di sistema per un endpoint rigorosamente locale.
        apri = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with apri.open(self.stato()["url"] + "/health", timeout=2) as r:
                return json.load(r).get("status") == "ok"
        except (OSError, ValueError):
            return False

    def _controlla_riposo(self):
        apri = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with apri.open(self.stato()["url"] + "/props", timeout=2) as r:
                return json.load(r).get("is_sleeping", False)
        except (OSError, ValueError):
            return None

    def _leggi_velocita(self, posizione):
        """Legge dal log le ultime velocita' (token/s) di prompt e risposta; restituisce la nuova posizione."""
        try:
            with open(self._stato["log"], "rb") as f:
                f.seek(posizione)
                grezzo = f.read()
        except (OSError, KeyError):
            return posizione
        grezzo = grezzo[:grezzo.rfind(b"\n") + 1]  # solo righe complete
        nuova = dict(self._stato.get("velocita") or {})
        for prompt, valore in VELOCITA.findall(grezzo.decode("utf-8", "replace")):
            nuova["input" if prompt else "output"] = float(valore)
        if nuova != (self._stato.get("velocita") or {}):
            self._stato["velocita"] = nuova
            self._notifica()
        return posizione + len(grezzo)

    def avvia(self, modello, contesto=8192, dflash=True, visione=False):
        with self._lock:
            if self._vivo():
                if all(self._stato.get(k) == v for k, v in dict(modello=modello, contesto=contesto,
                                                              dflash=dflash, visione=visione).items()):
                    return self.stato()
                raise ValueError("Un altro profilo e attivo: arrestarlo prima del cambio")
            if self._client:
                raise ValueError("Chiudere le chat locali del precedente avvio prima di caricare un modello")
            argv = argomenti_server({**self._config, "modelli": self._modelli_disponibili()}, modello, contesto, dflash, visione)
            with socket.socket() as s:
                try:
                    s.bind(("127.0.0.1", self._config["porta"]))
                except OSError as e:
                    raise ValueError("Porta occupata da un altro processo: non verra arrestato dall'app") from e
            self.cartella.mkdir(parents=True, exist_ok=True)
            log = self.cartella / f"server-{time.time_ns()}.log"
            with log.open("wb") as uscita:
                processo = self._popen(argv, stdin=subprocess.DEVNULL, stdout=uscita, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self._processo = processo
            self._ultimo_uso = self._ora()
            self._stato = dict(stato="caricamento", modello=modello, contesto=contesto, dflash=dflash,
                               visione=visione, log=str(log))
            threading.Thread(target=self._sorveglia, args=(processo,), daemon=True, name="ia-locale").start()
        self._notifica()
        return self.stato()

    def _sorveglia(self, processo):
        scadenza = self._ora() + 900
        ultimo_controllo = posizione_log = 0
        while True:
            with self._lock:
                if self._processo is not processo:
                    return
                if processo.poll() is not None:
                    self._stato.update(stato="errore", errore=f"Server terminato con codice {processo.returncode}")
                    self._notifica()
                    return
                pronto = self._stato["stato"] in ("pronto", "riposo")
            if pronto and self._ora() - ultimo_controllo >= 3:
                ultimo_controllo = self._ora()
                riposo = self._controlla_riposo()
                with self._lock:
                    nuovo = "riposo" if riposo else "pronto"
                    if self._processo is processo and riposo is not None and self._stato["stato"] != nuovo:
                        self._stato["stato"] = nuovo
                        self._notifica()
                    if self._processo is processo:
                        posizione_log = self._leggi_velocita(posizione_log)
            if not pronto and self._salute():
                with self._lock:
                    if self._processo is not processo:
                        return
                    self._stato["stato"] = "pronto"
                    self._ultimo_uso = self._ora()
                self._notifica()
            elif not pronto and self._ora() >= scadenza:
                with self._lock:
                    if self._processo is not processo:
                        return
                    self.arresta()
                    self._stato.update(stato="errore", errore="Caricamento oltre 15 minuti: controllare il log")
                self._notifica()
                return
            with self._lock:
                if self._processo is not processo:
                    return
                if pronto and self.scarica_se_inattivo():
                    return
            time.sleep(0.5)

    def scarica_se_inattivo(self):
        with self._lock:
            if self._client or not self._config["inattivita_secondi"] or self._ora() - self._ultimo_uso < self._config["inattivita_secondi"]:
                return False
            self.arresta()
            return True

    def registra_client(self, sid):
        with self._lock:
            self._client.add(sid)
            self._ultimo_uso = self._ora()

    def sessione(self, sid):
        try:
            return json.loads((self.cartella / "sessioni.json").read_text(encoding="utf-8")).get(sid)
        except (OSError, ValueError, AttributeError):
            return None

    def ricorda_sessione(self, sid, assistente, profilo):
        with self._lock:
            try:
                dati = json.loads((self.cartella / "sessioni.json").read_text(encoding="utf-8"))
                if not isinstance(dati, dict):
                    dati = {}
            except (OSError, ValueError):
                dati = {}
            dati[sid] = {"assistente": assistente, **profilo}
            self.cartella.mkdir(parents=True, exist_ok=True)
            tmp = self.cartella / "sessioni.json.tmp"
            tmp.write_text(json.dumps(dati), encoding="utf-8")
            tmp.replace(self.cartella / "sessioni.json")

    def profilo_chat(self, modello=None, precedente=None):
        """Le chat riprese adottano i limiti nuovi senza ridurre il contesto storico."""
        with self._lock:
            cfg = self._config
            modello = precedente["modello"] if precedente else modello
            voce = self._modelli_disponibili().get(modello, {})
            return {"modello": modello,
                    "contesto": max(cfg["contesto"], precedente.get("contesto", 0) if precedente else 0),
                    "dflash": cfg["dflash"] and bool(voce.get("draft")),
                    "visione": precedente["visione"] if precedente else cfg["visione"]}

    def rilascia_client(self, sid):
        with self._lock:
            self._client.discard(sid)
            self._ultimo_uso = self._ora()

    def arresta(self, forza=False):
        with self._lock:
            if self._client and not forza:
                raise ValueError("Ci sono chat locali aperte: chiuderle o confermare forza=true")
            processo, self._processo = self._processo, None
            if processo and processo.poll() is None:
                processo.terminate()
                try:
                    processo.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    processo.kill()
                    processo.wait(timeout=5)
            self._stato = dict(stato="spento", modello=None, contesto=None, dflash=False, visione=False)
            self._notifica()
            return self.stato()

    def _avvia_ponte(self):
        if self._ponte:
            return self._ponte.server_address[1]
        gestore = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass  # Mai contenuti o credenziali nei log.

            def inoltra(self):
                conn = None
                iniziata = False
                try:
                    dati = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                    if dati and self.path.split("?")[0] in ("/v1/messages", "/v1/messages/count_tokens"):
                        dati = json.dumps(normalizza_anthropic(json.loads(dati))).encode()
                    headers = {k: v for k, v in self.headers.items() if k.lower() not in
                               ("host", "content-length", "connection", "authorization", "x-api-key")}
                    headers.update({"Content-Length": str(len(dati)), "Connection": "close"})
                    conn = http.client.HTTPConnection("127.0.0.1", gestore._config["porta"], timeout=600)
                    conn.request(self.command, self.path, dati, headers)
                    risposta = conn.getresponse()
                    self.send_response(risposta.status)
                    iniziata = True
                    for k, v in risposta.getheaders():
                        if k.lower() not in ("connection", "content-length", "transfer-encoding"):
                            self.send_header(k, v)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    while blocco := risposta.read1(65536):
                        self.wfile.write(blocco)
                        self.wfile.flush()
                except (OSError, ValueError):
                    if not iniziata:
                        try:
                            self.send_error(502, "Server locale non disponibile")
                        except OSError:
                            pass
                finally:
                    if conn:
                        conn.close()
                    self.close_connection = True

            do_POST = inoltra
            do_GET = inoltra

        self._ponte = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._ponte.daemon_threads = True
        threading.Thread(target=self._ponte.serve_forever, daemon=True, name="ia-ponte-claude").start()
        return self._ponte.server_address[1]

    def prepara_client(self, assistente):
        with self._lock:
            if assistente not in MODELLI_CLIENT:
                raise ValueError("Assistente locale non supportato")
            if self._stato["stato"] not in ("pronto", "riposo") or not self._vivo():
                raise ValueError("Avviare il modello e attendere lo stato pronto")
            contesto = self._stato["contesto"]
            if assistente == "codex":
                home = self.cartella / "codex"
                home.mkdir(parents=True, exist_ok=True)
                (home / "config.toml").write_text(
                    f'model = "qwen-locale"\nmodel_provider = "second_brain_locale"\n'
                    f'model_context_window = {contesto}\nmodel_auto_compact_token_limit = {int(contesto * .75)}\n'
                    'approval_policy = "on-request"\nsandbox_mode = "workspace-write"\n'
                    '[model_providers.second_brain_locale]\nname = "Second Brain locale"\n'
                    f'base_url = "{self.stato()["url"]}/v1"\nwire_api = "responses"\nrequires_openai_auth = false\n',
                    encoding="utf-8")
                return [], {"CODEX_HOME": str(home)}
            porta = self._avvia_ponte()
            env = {"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{porta}", "ANTHROPIC_API_KEY": "",
                   "ANTHROPIC_AUTH_TOKEN": "locale-senza-autenticazione", "ANTHROPIC_MODEL": "qwen-locale",
                   "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen-locale", "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen-locale",
                   "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen-locale", "CLAUDE_CODE_SUBAGENT_MODEL": "qwen-locale",
                   "CLAUDE_CODE_MAX_CONTEXT_TOKENS": str(contesto), "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "2048",
                   "DISABLE_AUTO_COMPACT": "0" if self._config["compattazione_automatica"] else "1",
                   "DISABLE_COMPACT": "0",
                   "MAX_THINKING_TOKENS": "0"}
            settings = self.cartella / "claude-locale.json"
            settings.write_text(json.dumps({"env": env, "disableAllHooks": True}), encoding="utf-8")
            # profilo snello: senza plugin, MCP e skill dell'utente il prompt scende da ~55k a ~8k token
            return ["--settings", str(settings), "--model", "qwen-locale", "--setting-sources", "project",
                    "--strict-mcp-config", "--disable-slash-commands",
                    "--tools", "Bash,Edit,Read,Write,Glob,Grep"], env

    def chiedi(self, prompt, profilo, timeout=60):
        with self._lock:
            # anche a riposo: la richiesta stessa fa ricaricare il modello a llama.cpp
            if not profilo or self._stato["stato"] not in ("pronto", "riposo") or any(
                    profilo.get(k) != self._stato[k] for k in ("modello", "contesto", "dflash", "visione")):
                raise ValueError("Attivare il profilo locale della chat prima di generare il titolo")
            url = self.stato()["url"] + "/v1/chat/completions"
        richiesta = urllib.request.Request(url, json.dumps({"model": "qwen-locale", "messages": [
            {"role": "user", "content": prompt}], "max_tokens": 128, "temperature": 0.3}).encode(),
            {"Content-Type": "application/json"})
        apri = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with apri.open(richiesta, timeout=timeout) as risposta:
            return json.load(risposta)["choices"][0]["message"]["content"]

    def chiudi(self):
        self.arresta(forza=True)
        if self._ponte:
            self._ponte.shutdown()
            self._ponte.server_close()
            self._ponte = None
