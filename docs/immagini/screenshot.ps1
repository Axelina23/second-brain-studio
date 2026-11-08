# Rifà gli screenshot del README dalla pagina di prova (app/web/prova.html, dati inventati)
# con Chrome o Edge senza finestra, in italiano e in inglese, poi la GIF del giro dell'app.
# Uso:  powershell -ExecutionPolicy Bypass -File docs\immagini\screenshot.ps1
param([int]$Porta = 8765)
$ErrorActionPreference = "Stop"
$qui = $PSScriptRoot
$web = Resolve-Path (Join-Path $qui "..\..\app\web")

$browser = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
             "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browser) { throw "Serve Chrome o Edge" }

$server = Start-Process py -ArgumentList "-3.14", "-m", "http.server", $Porta, "-d", "`"$web`"" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2
$profilo = Join-Path $env:TEMP "sbs-screenshot"
Remove-Item -Recurse -Force $profilo -ErrorAction SilentlyContinue   # niente moduli vecchi dalla cache

# nome del file -> parametri della pagina di prova
$scatti = [ordered]@{
  "oggi"              = "demo"
  "oggi-chiaro"       = "demo&tema=chiaro"
  "chat-pc"           = "demo&pagina=chat"
  "appunti"           = "demo&pagina=appunti"
  "inbox"             = "demo&pagina=inbox"
  "primo-avvio"       = "primo"
  "impostazioni"      = "demo&imp=notifiche"
  "mappa-grafo"       = "demo&pagina=mappa&vista=grafo2d"
  "mappa-grafo3d"     = "demo&pagina=mappa&vista=grafo3d"
  "mappa-mosaico"     = "demo&pagina=mappa&vista=mosaico"
  "mappa-raggiera"    = "demo&pagina=mappa&vista=raggiera"
  "mappa-attivita"    = "demo&pagina=mappa&vista=attivita"
  "mappa-metro"       = "demo&pagina=mappa&vista=metro"
  "mappa-citta"       = "demo&pagina=mappa&vista=citta"
  "mappa-orbite"      = "demo&pagina=mappa&vista=orbite"
}
try {
  foreach ($lingua in "it", "en") {
    foreach ($nome in $scatti.Keys) {
      $q = $scatti[$nome] + "&statico"
      $file = Join-Path $qui "$nome.png"
      if ($lingua -eq "en") { $q += "&en"; $file = Join-Path $qui "en\$nome.png" }
      New-Item -ItemType Directory -Force (Split-Path $file) | Out-Null
      $ErrorActionPreference = "Continue"   # Chrome scrive avvisi innocui su stderr
      & $browser --headless=new --hide-scrollbars --force-device-scale-factor=1 --window-size=1440,900 `
        --virtual-time-budget=8000 --user-data-dir="$profilo" --screenshot="$file" `
        "http://127.0.0.1:$Porta/prova.html?$q" 2>&1 | Out-Null
      $ErrorActionPreference = "Stop"
      Write-Host "$lingua  $nome"
    }
  }
} finally {
  Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}
py -3.14 (Join-Path $qui "giro.py")
