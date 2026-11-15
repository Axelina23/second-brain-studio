# Crea "Second Brain Studio.exe" con PyInstaller e l'installer classico di Windows con Inno Setup
# ("Second Brain Studio Setup <versione>.exe" in Sistema\app\dist, da condividere).
# Poi aggiorna questo PC:
#  - app chiusa: lancia l'installer in modalita' rapida (/SILENT): si vede la barra di
#    avanzamento e alla fine l'app si apre;
#  - app aperta: non la tocca (dentro potrebbe esserci una chat in corso); scrive
#    ~/.claude/second-brain/aggiornamento.json e nell'app compare "Aggiornamento pronto".
# Uso: powershell -ExecutionPolicy Bypass -File app\build.ps1 [-SoloInstaller] [-Pubblica | -Stabile]
#  -Pubblica: pre-release di prova (la ricevono solo le app con "Anche le versioni di prova")
#  -Stabile:  release vera per tutti, con le note della prima sezione di CHANGELOG.md
# Nota: niente lettere accentate in questo file (PowerShell 5.1 legge male l'UTF-8).
param([switch]$SoloInstaller, [switch]$Pubblica, [switch]$Stabile, [switch]$MenuWindows11, [switch]$FirmaLocaleDiProva)
$ErrorActionPreference = "Stop"

$qui = $PSScriptRoot
if ($FirmaLocaleDiProva -and (-not $Pubblica -or $Stabile -or -not $MenuWindows11)) {
  throw "FirmaLocaleDiProva e' consentito solo con -Pubblica -MenuWindows11, mai per una stabile"
}
$menu = Join-Path $qui "shell\dist"
if ($MenuWindows11) {
  foreach ($nome in @("SBSInbox.dll", "InboxMenu.msix", "publisher.cer")) {
    if (-not (Test-Path -LiteralPath (Join-Path $menu $nome))) { throw "Compilare e firmare prima app\shell\build.ps1: manca $nome" }
  }
  $firma = Get-AuthenticodeSignature -FilePath (Join-Path $menu "InboxMenu.msix")
  if (-not $firma.SignerCertificate) { throw "Il pacchetto del menu non e' firmato" }
  $firmaAutofirmata = $firma.SignerCertificate.Subject -eq $firma.SignerCertificate.Issuer
  if (($Pubblica -or $Stabile) -and (($firma.Status -ne "Valid") -or ($firmaAutofirmata -and -not $FirmaLocaleDiProva))) { throw "Serve una firma attendibile. Per una pre-release locale esplicita usare anche -FirmaLocaleDiProva; mai per una stabile" }
}
$avvio = Join-Path (Split-Path $qui) "motore"
# Python: il piu' recente tra le installazioni classiche e quelle del nuovo gestore (pythoncore-3.x)
$py = @(Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "$env:LOCALAPPDATA\Python\pythoncore-3.*\python.exe" -ErrorAction SilentlyContinue) |
  Sort-Object { [version]($_.VersionInfo.ProductVersion -replace '[^0-9.].*$', '') } -Descending | Select-Object -First 1
if (-not $py) { throw "Python non trovato in $env:LOCALAPPDATA\Programs\Python o $env:LOCALAPPDATA\Python" }
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") |
  Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup non trovato: winget install JRSoftware.InnoSetup" }
$lavoro = Join-Path $env:TEMP "second-brain-build"
$versione = Get-Date -Format "yyyy.M.d.HHmm"
Set-Content -Path (Join-Path $qui "versione.txt") -Value $versione -NoNewline -Encoding ASCII

Write-Host "Dipendenze..."
& $py.FullName -m pip install --user -q -r (Join-Path $qui "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip non riuscito" }

Write-Host "PyInstaller (versione $versione)..."
& $py.FullName (Join-Path $qui "icona.py") | Out-Null
& $py.FullName -m PyInstaller --noconfirm --clean --windowed --onedir `
  --name "Second Brain Studio" --icon (Join-Path $qui "icona.ico") `
  --paths $avvio --add-data "$(Join-Path $qui 'web');web" --add-data "$(Join-Path $qui 'hooks');hooks" --add-data "$(Join-Path $qui 'versione.txt');." `
  --collect-all winpty --collect-submodules webview `
  --hidden-import pystray._win32 `
  --workpath (Join-Path $lavoro "work") --distpath (Join-Path $lavoro "dist") --specpath $lavoro `
  (Join-Path $qui "main.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller non riuscito" }
$uscita = Join-Path $lavoro "dist\Second Brain Studio"
if ($MenuWindows11) {
  $shellOut = Join-Path $uscita "_shell"
  New-Item -ItemType Directory -Force -Path $shellOut | Out-Null
  foreach ($nome in @("SBSInbox.dll", "InboxMenu.msix", "publisher.cer")) { Copy-Item -LiteralPath (Join-Path $menu $nome) -Destination $shellOut }
  Copy-Item -LiteralPath (Join-Path $qui "shell\gestisci-menu.ps1") -Destination $shellOut
  Copy-Item -LiteralPath (Join-Path $qui "icona-1024.png") -Destination (Join-Path $shellOut "logo.png")
}
Remove-Item (Join-Path $uscita "_internal\web\prova.html") -ErrorAction SilentlyContinue

Write-Host "Installer (Inno Setup)..."
$dist = Join-Path $qui "dist"
New-Item -ItemType Directory -Force -Path $dist | Out-Null
$opzioniMenu = @()
if ($MenuWindows11) { $opzioniMenu = @("/DMenuWindows11") }
& $iscc /Q "/DVersione=$versione" "/DSorgente=$uscita" "/O$dist" @opzioniMenu (Join-Path $qui "installer.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup non riuscito" }
$setup = Join-Path $dist "Second Brain Studio Setup $versione.exe"
# tiene solo gli ultimi 3 installer
Get-ChildItem $dist -Filter "Second Brain*Setup *.exe" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 3 | Remove-Item -Force
Write-Host "Installer: $setup"
# -Pubblica / -Stabile: release su GitHub, cosi' gli altri PC la ricevono da soli
if ($Pubblica -or $Stabile) {
  if ($Stabile) {
    # note = prima sezione "## ..." di CHANGELOG.md (la versione che si sta pubblicando)
    $righe = @(Get-Content (Join-Path (Split-Path $qui) "CHANGELOG.md") -Encoding UTF8)
    $sezioni = @($righe | Select-String -Pattern '^## ' | ForEach-Object { $_.LineNumber - 1 })
    if ($sezioni.Count -eq 0) { throw "CHANGELOG.md senza sezioni '## '" }
    $fine = if ($sezioni.Count -gt 1) { $sezioni[1] - 1 } else { $righe.Count - 1 }
    $corpo = ($righe[($sezioni[0] + 1)..$fine] -join "`n").Trim()
    $titolo = "Second Brain Studio $versione"
    $tipo = @()
  } else {
    $righe = @(Get-Content (Join-Path (Split-Path $qui) "CHANGELOG.md") -Encoding UTF8)
    $inizio = [array]::IndexOf($righe, '## Next version')
    $corpo = "Test build $versione. It may have rough edges: stable releases are the ones without the Pre-release label."
    if ($inizio -ge 0) {
      $novita = @()
      for ($i = $inizio + 1; $i -lt $righe.Count -and $righe[$i] -notmatch '^## '; $i++) { $novita += $righe[$i] }
      $corpo += "`n`n" + ($novita -join "`n").Trim()
    }
    $titolo = "$versione (test)"
    $tipo = @("--prerelease")
  }
  $corpo += "`n`n**Install:** download the ``Setup`` file below and run it (no administrator rights needed). " +
    "Windows SmartScreen may say it protected your PC because the installer is not code-signed yet: click **More info**, then **Run anyway**."
  if ($FirmaLocaleDiProva) {
    $corpo += "`n`n**Windows 11 main Inbox menu - development certificate:** this pre-release contains a self-signed sparse package. " +
      "On another PC, first import the attached public ``publisher.cer`` into **Local Computer > Trusted People** with explicit administrator approval, then run the installer. If you already installed it, import the certificate and run the installer again. " +
      "The installer never imports certificate trust automatically. Do not import it into Trusted Root Certification Authorities. " +
      "Screenshot paste and drag-and-drop work without this certificate. A production-trusted signature is still required before a stable release of the modern menu. " +
      "Certificate SHA-1 thumbprint: ``$($firma.SignerCertificate.Thumbprint)``. [Instructions](https://github.com/Axelina23/second-brain-studio/blob/main/docs/INBOX.md)."
  }
  $notefile = Join-Path $lavoro "note.md"
  [IO.File]::WriteAllText($notefile, $corpo, (New-Object Text.UTF8Encoding($false)))
  $asset = @($setup)
  if ($FirmaLocaleDiProva) { $asset += (Join-Path $menu "publisher.cer") }
  $testa = git -C (Split-Path $qui) rev-parse HEAD
  if ($LASTEXITCODE -ne 0) { throw "Commit sorgente non trovato" }
  gh release create "v$versione" @asset --repo Axelina23/second-brain-studio @tipo --target $testa.Trim() --title $titolo --notes-file $notefile
  if ($LASTEXITCODE -ne 0) { throw "Pubblicazione su GitHub non riuscita" }
  Write-Host "Pubblicata: v$versione"
}
if ($SoloInstaller) { return }

$cache = Join-Path $env:USERPROFILE ".claude\second-brain"
New-Item -ItemType Directory -Force -Path $cache | Out-Null
if (Get-Process -Name "Second Brain Studio", "Second Brain" -ErrorAction SilentlyContinue) {
  $dati = @{ versione = $versione; setup = $setup } | ConvertTo-Json -Compress
  [IO.File]::WriteAllText((Join-Path $cache "aggiornamento.json"), $dati, (New-Object Text.UTF8Encoding($false)))
  Write-Host "L'app e' aperta: nell'app compare 'Aggiornamento pronto' (versione $versione)."
} else {
  Remove-Item (Join-Path $cache "aggiornamento.json") -ErrorAction SilentlyContinue
  Start-Process $setup -ArgumentList "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"
  Write-Host "Installo la versione $versione (finestra di avanzamento)."
}
