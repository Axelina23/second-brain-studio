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
param([switch]$SoloInstaller, [switch]$Pubblica, [switch]$Stabile)
$ErrorActionPreference = "Stop"

$qui = $PSScriptRoot
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
Remove-Item (Join-Path $uscita "_internal\web\prova.html") -ErrorAction SilentlyContinue

Write-Host "Installer (Inno Setup)..."
$dist = Join-Path $qui "dist"
New-Item -ItemType Directory -Force -Path $dist | Out-Null
& $iscc /Q "/DVersione=$versione" "/DSorgente=$uscita" "/O$dist" (Join-Path $qui "installer.iss")
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
    $corpo = "Test build $versione. It may have rough edges: stable releases are the ones without the Pre-release label."
    $titolo = "$versione (test)"
    $tipo = @("--prerelease")
  }
  $corpo += "`n`n**Install:** download the ``Setup`` file below and run it (no administrator rights needed). " +
    "Windows SmartScreen may say it protected your PC because the installer is not code-signed yet: click **More info**, then **Run anyway**."
  $notefile = Join-Path $lavoro "note.md"
  [IO.File]::WriteAllText($notefile, $corpo, (New-Object Text.UTF8Encoding($false)))
  gh release create "v$versione" $setup --repo Axelina23/second-brain-studio @tipo --title $titolo --notes-file $notefile
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
