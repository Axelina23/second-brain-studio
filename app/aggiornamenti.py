# Aggiornamenti dalle release di GitHub (Axelina23/second-brain-studio).
# All'avvio e ogni 6 ore si leggono le release, si sceglie la piu' nuova con un installer
# ("Second Brain Studio Setup <versione>.exe"), lo si scarica nella cache controllando
# dimensione e sha256 (campo "digest" di GitHub) e si scrive aggiornamento.json: da li'
# compare il pulsante "Aggiornamento pronto" (main.py), come per le versioni costruite in locale.
# Finche' il repository e' privato serve la chiave GitHub dell'app (accesso con codice).
# Solo libreria standard.
import hashlib
import json
import re
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO = "Axelina23/second-brain-studio"
_NASCOSTO = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_STACCATO = getattr(subprocess, "DETACHED_PROCESS", 0)
_FUORI_DAL_JOB = 0x01000000  # CREATE_BREAKAWAY_FROM_JOB
_NULLI = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def avvia_staccato(script: Path, attesa: float = 0.0) -> bool:
    # lancia lo script PowerShell in un processo che sopravvive alla chiusura dell'app.
    # Tre tentativi, dal piu' sicuro: WMI (nessun legame con l'app, nemmeno se l'app sta in un
    # "job" di Windows), poi processo staccato fuori dal job, poi staccato semplice.
    # Tutti i canali sono espliciti: mai ereditati (vedi canali.py e docs/AGGIORNAMENTI.md).
    comando = f'powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{script}"'
    args = ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    try:
        cim = comando.replace("'", "''")
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            f"(Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{{CommandLine='{cim}'}}).ReturnValue"],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, creationflags=_NASCOSTO)
        if r.stdout.strip() == "0":
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    for flag in (_NASCOSTO | _STACCATO | _FUORI_DAL_JOB, _NASCOSTO | _STACCATO):
        try:
            subprocess.Popen(args, creationflags=flag, **_NULLI)
            time.sleep(attesa)
            return True
        except OSError:
            continue
    return False
API = f"https://api.github.com/repos/{REPO}/releases?per_page=20"
_INSTALLER = re.compile(r"^Second[ ._]Brain[ ._]Studio[ ._]Setup[ ._](\d{4}\.\d{1,2}\.\d{1,2}\.\d{1,4})\.exe$", re.I)


def numeri(versione: str | None) -> tuple | None:
    # "2026.11.8.0317" o "v2026.11.8.0317" -> (2026, 11, 8, 317); "sviluppo" -> None
    m = re.fullmatch(r"v?(\d{4})\.(\d{1,2})\.(\d{1,2})\.(\d{1,4})", str(versione or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def scegli(release: list, attuale: str, prove: bool) -> dict | None:
    # la release piu' nuova di quella in uso, con un installer allegato
    base = numeri(attuale)
    if base is None:
        return None  # app avviata da sorgente: niente aggiornamenti
    migliore = None
    for r in release if isinstance(release, list) else []:
        if not isinstance(r, dict) or r.get("draft") or (r.get("prerelease") and not prove):
            continue
        for a in r.get("assets") or []:
            m = _INSTALLER.match(str(a.get("name", "")))
            v = numeri(m.group(1)) if m else None
            if v and v > base and (migliore is None or v > migliore["numeri"]):
                migliore = {"numeri": v, "versione": m.group(1), "nome": a["name"], "url": a.get("url"),
                            "pubblico": a.get("browser_download_url"), "dimensione": a.get("size"),
                            "digest": a.get("digest"), "note": r.get("body") or "", "tag": r.get("tag_name")}
    return migliore


def _get(url: str, token: str | None, accetta: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"Accept": accetta, "User-Agent": "second-brain-studio"})
    if token:
        # la chiave non segue il rinvio verso il server dei file (che rifiuterebbe due accessi)
        req.add_unredirected_header("Authorization", f"Bearer {token}")
    return urllib.request.urlopen(req, timeout=timeout)


def leggi_release(token: str | None) -> list:
    try:
        with _get(API, token, "application/vnd.github+json") as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if not token or e.code != 401:
            raise
        # Le release sono pubbliche: il login non deve bloccare gli aggiornamenti.
        with _get(API, None, "application/vnd.github+json") as r:
            return json.loads(r.read().decode("utf-8"))


def scarica(scelta: dict, cartella: Path, token: str | None) -> Path:
    # scarica in un file .part e lo rinomina solo se dimensione e sha256 tornano
    cartella.mkdir(parents=True, exist_ok=True)
    dest = cartella / scelta["nome"].replace(" ", "_")
    if dest.is_file() and _verifica(dest, scelta):
        return dest
    parziale = dest.with_suffix(".part")
    # con la chiave si passa dall'API (funziona anche col repository privato)
    url, accetta = (scelta["url"], "application/octet-stream") if token and scelta.get("url") else (scelta["pubblico"], "*/*")
    h = hashlib.sha256()
    try:
        risposta = _get(url, token if url == scelta.get("url") else None, accetta, timeout=120)
    except urllib.error.HTTPError as e:
        if not token or e.code != 401 or not scelta.get("pubblico"):
            raise
        risposta = _get(scelta["pubblico"], None, "*/*", timeout=120)
    with risposta as r, open(parziale, "wb") as f:
        while True:
            pezzo = r.read(1 << 16)
            if not pezzo:
                break
            h.update(pezzo)
            f.write(pezzo)
    if not _verifica(parziale, scelta, h.hexdigest()):
        parziale.unlink(missing_ok=True)
        raise ValueError("installer scaricato non valido (dimensione o sha256 diversi)")
    parziale.replace(dest)
    return dest


def _verifica(file: Path, scelta: dict, sha: str | None = None) -> bool:
    if scelta.get("dimensione") and file.stat().st_size != scelta["dimensione"]:
        return False
    digest = str(scelta.get("digest") or "")
    if digest.startswith("sha256:"):
        if sha is None:
            h = hashlib.sha256()
            with open(file, "rb") as f:
                for pezzo in iter(lambda: f.read(1 << 16), b""):
                    h.update(pezzo)
            sha = h.hexdigest()
        return sha.lower() == digest.split(":", 1)[1].lower()
    return True


def controlla(attuale: str, prove: bool, token: str | None, cache: Path) -> dict:
    # {"nuova": None} se non c'e' niente; {"nuova": versione} se l'installer e' pronto
    scelta = scegli(leggi_release(token), attuale, prove)
    if not scelta:
        return {"nuova": None}
    setup = scarica(scelta, cache / "aggiornamenti", token)
    dati = {"versione": scelta["versione"], "setup": str(setup), "fonte": "github", "note": scelta["note"][:2000]}
    (cache / "aggiornamento.json").write_text(json.dumps(dati, ensure_ascii=False), encoding="utf-8")
    # via gli installer vecchi scaricati
    for f in (cache / "aggiornamenti").glob("*.exe"):
        if f != setup:
            f.unlink(missing_ok=True)
    return {"nuova": scelta["versione"]}


def _ps(s: str) -> str:
    # stringa PowerShell tra apici singoli
    return "'" + str(s).replace("'", "''") + "'"


def script_aggiornamento(pid: int, setup: str, versione: str, riapri: bool, cartella_app: Path | None, cache: Path) -> str:
    # Script del processo che installa l'aggiornamento dopo la chiusura dell'app. Scrive un
    # registro (aggiornamento.log), chiude a forza i processi rimasti della cartella dell'app
    # (console dei terminali: altrimenti l'installer silenzioso rinuncia), lancia l'installer
    # col suo registro (setup-ultimo.log) e, se fallisce, lascia l'offerta di aggiornamento,
    # scrive aggiornamento-errore.json (l'app lo mostra al prossimo avvio) e riapre l'app.
    log, log_setup = cache / "aggiornamento.log", cache / "setup-ultimo.log"
    argomenti = ["/SILENT" if riapri else "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                 "/CLOSEAPPLICATIONS", "/FORCECLOSEAPPLICATIONS", f'/LOG="{log_setup}"'] + ([] if riapri else ["/NOAVVIO"])
    cartella = str(cartella_app) if cartella_app else ""
    exe = str(Path(cartella) / "Second Brain Studio.exe") if cartella else ""
    righe = [
        "$ErrorActionPreference = 'Continue'",
        f"$log = {_ps(log)}",
        "function L($t) { Add-Content -Path $log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $t) -Encoding UTF8 }",
        # un solo aggiornamento alla volta: un secondo script (doppio clic) esce subito
        "$unico = New-Object System.Threading.Mutex($false, 'Local\\SecondBrainStudioAggiornamento')",
        "if (-not $unico.WaitOne(0)) { L 'aggiornamento gia in corso: esco'; exit 0 }",
        f"L ('inizio: versione ' + {_ps(versione)} + ', app {pid}')",
        "$fine = (Get-Date).AddSeconds(60)",
        f"while ((Get-Process -Id {pid} -ErrorAction SilentlyContinue) -and (Get-Date) -lt $fine) {{ Start-Sleep -Milliseconds 300 }}",
        f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ L 'app ancora aperta dopo 60 s: la chiudo'; Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue }}",
        f"$cartella = {_ps(cartella)}",
        "if ($cartella) {",
        "  $fine = (Get-Date).AddSeconds(15)",
        "  do {",
        "    $resti = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($cartella, [StringComparison]::OrdinalIgnoreCase) })",
        "    if ($resti.Count -eq 0) { break }",
        "    Start-Sleep -Milliseconds 500",
        "  } while ((Get-Date) -lt $fine)",
        "  foreach ($r in $resti) { L ('chiudo ' + $r.Name + ' ' + $r.Id); Stop-Process -Id $r.Id -Force -ErrorAction SilentlyContinue }",
        "  Start-Sleep -Milliseconds 500",
        "}",
        f"$setup = {_ps(setup)}",
        "$codice = -1",
        "if (Test-Path -LiteralPath $setup) {",
        # niente -Wait: aspetterebbe anche i figli dell'installer, cioè l'app che riapre alla fine,
        # e lo script resterebbe appeso col mutex preso (il prossimo aggiornamento non partirebbe).
        # $p.Handle subito: in PowerShell 5.1 senza handle aperto ExitCode resta vuoto.
        f"  $p = Start-Process -FilePath $setup -ArgumentList @({', '.join(_ps(a) for a in argomenti)}) -PassThru",
        "  $null = $p.Handle",
        "  $p.WaitForExit()",
        "  $codice = $p.ExitCode",
        "} else { L 'installer non trovato' }",
        "L ('installer finito: codice ' + $codice)",
        "if ($codice -eq 0) {",
        f"  Remove-Item -LiteralPath {_ps(cache / 'aggiornamento.json')}, {_ps(cache / 'aggiornamento-errore.json')} -ErrorAction SilentlyContinue",
        "} else {",
        f"  $e = @{{ versione = {_ps(versione)}; codice = $codice; quando = (Get-Date -Format s) }} | ConvertTo-Json -Compress",
        f"  [IO.File]::WriteAllText({_ps(cache / 'aggiornamento-errore.json')}, $e)",
        f"  if ({'$true' if riapri else '$false'} -and {_ps(exe)} -and (Test-Path -LiteralPath {_ps(exe)})) {{ Start-Process -FilePath {_ps(exe)} }}",
        "}",
    ]
    return "\n".join(righe) + "\n"
