# Status line di Claude Code: modello, contesto usato e uso del piano (finestra di
# 5 ore e settimanale) come nelle impostazioni dell'app: barra di utilizzo, % usata
# e quando si azzera. Claude Code passa i dati in JSON su stdin.
# Barra blu, gialla dall'80%, rossa dal 95%.
# Con -Ponte (l'utente aveva gia' una sua riga di stato): salva solo l'uso del piano per
# l'app e poi fa girare la riga dell'utente (riga-stato-utente.sh accanto a questo file,
# salvata dal primo avvio) con gli stessi dati, restituendo il suo output tale e quale.
# Nota: niente lettere accentate in questo file (PowerShell 5.1).
param([switch]$Ponte)

# UTF-8 senza BOM: con [Text.Encoding]::UTF8 PowerShell 5.1 metterebbe il BOM davanti ai dati
# passati alla riga di stato dell'utente (modalita' ponte)
[Console]::InputEncoding  = New-Object Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$testo = [Console]::In.ReadToEnd()
try { $d = $testo | ConvertFrom-Json } catch { $d = $null; if (-not $Ponte) { exit 0 } }

# Ultimo uso del piano anche per Second Brain Studio (barra di stato): uso.json in cache,
# scritto in modo atomico; un errore qui non deve mai rompere la riga di stato
if ($d -and $d.rate_limits) {
  try {
    $cache = Join-Path $env:USERPROFILE ".claude\second-brain"
    if (-not (Test-Path $cache)) { New-Item -ItemType Directory -Force -Path $cache | Out-Null }
    $uso = [ordered]@{ aggiornato = [DateTimeOffset]::Now.ToUnixTimeSeconds() }
    foreach ($k in @('five_hour', 'seven_day')) {
      $w = $d.rate_limits.$k
      if ($w) { $uso[$k] = [ordered]@{ used_percentage = $w.used_percentage; resets_at = $w.resets_at } }
    }
    $tmp = Join-Path $cache "uso.json.$PID.tmp"
    [IO.File]::WriteAllText($tmp, ($uso | ConvertTo-Json -Compress), (New-Object Text.UTF8Encoding($false)))
    Move-Item -Force $tmp (Join-Path $cache "uso.json")
  } catch {}
}

if ($Ponte) {
  # la riga dell'utente gira con Git Bash, come la farebbe girare Claude Code; senza Git Bash
  # con cmd. Mai bash.exe di System32 (e' WSL). Al massimo 5 secondi.
  $file = Join-Path $PSScriptRoot "riga-stato-utente.sh"
  if (-not (Test-Path $file)) { exit 0 }
  $bash = @($env:CLAUDE_CODE_GIT_BASH_PATH, "$env:ProgramFiles\Git\bin\bash.exe", "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
            "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe") | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
  $psi = New-Object Diagnostics.ProcessStartInfo
  if ($bash) { $psi.FileName = $bash; $psi.Arguments = '"' + $file + '"' }
  else { $psi.FileName = "cmd.exe"; $psi.Arguments = '/d /s /c "' + (Get-Content $file -Raw).Trim() + '"' }
  $psi.UseShellExecute = $false
  $psi.RedirectStandardInput = $true
  $psi.RedirectStandardOutput = $true
  $psi.CreateNoWindow = $true
  try {
    $p = [Diagnostics.Process]::Start($psi)
    $dentro = (New-Object Text.UTF8Encoding($false)).GetBytes($testo)
    $p.StandardInput.BaseStream.Write($dentro, 0, $dentro.Length)
    $p.StandardInput.Close()
    $fuori = New-Object IO.MemoryStream
    $copia = $p.StandardOutput.BaseStream.CopyToAsync($fuori)
    if (-not $p.WaitForExit(5000)) { try { $p.Kill() } catch {} }
    [void]$copia.Wait(1000)
    $b = $fuori.ToArray()
    $out = [Console]::OpenStandardOutput()
    $out.Write($b, 0, $b.Length)
    $out.Flush()
  } catch {}
  exit 0
}

$E     = [char]27
$R     = "$E[0m"
$DIM   = "$E[2m"
$TRACK = "$E[38;5;238m"
$DOT   = "  $DIM" + [char]0x00B7 + "$R  "
$BLOCCO = [string][char]0x2588
$IT    = [Globalization.CultureInfo]::GetCultureInfo('it-IT')

function Barra($p, $w = 10) {
  $c = if ($p -ge 95) { "$E[31m" } elseif ($p -ge 80) { "$E[33m" } else { "$E[38;5;75m" }
  $n = [int][math]::Min($w, [math]::Max(0, [math]::Round($p * $w / 100)))
  # Almeno un blocco pieno appena c'e' un minimo di consumo
  if ($p -gt 0 -and $n -eq 0) { $n = 1 }
  "$c$($BLOCCO * $n)$TRACK$($BLOCCO * ($w - $n))$R"
}

function Tra($sec) {
  if ($sec -lt 3600) { return "$([int][math]::Ceiling($sec / 60))m" }
  $h = [int][math]::Floor($sec / 3600)
  $m = [int][math]::Floor(($sec % 3600) / 60)
  if ($m -eq 0) { return "${h}h" } else { return '{0}h{1:00}' -f $h, $m }
}

$parti = @("$($d.model.display_name)")
$ctx = $d.context_window.used_percentage
if ($null -ne $ctx) { $parti += "ctx $([int][math]::Round($ctx))%" }

$ora = [DateTimeOffset]::Now.ToUnixTimeSeconds()
foreach ($f in @(@('five_hour', '5h'), @('seven_day', '7g'))) {
  $w = $d.rate_limits.($f[0])
  if (-not $w -or $null -eq $w.used_percentage) { continue }
  $p = [int][math]::Round($w.used_percentage)
  $reset = if ($w.resets_at) { [long]$w.resets_at } else { $null }
  # Finestra gia' ripartita: il dato e' vecchio, l'uso riparte da zero
  if ($reset -and $reset -le $ora) { $p = 0; $reset = $null }

  $quando = ''
  if ($reset) {
    if ($f[0] -eq 'five_hour') { $quando = " $DIM" + [char]0x21BB + " $(Tra ($reset - $ora))$R" }
    else { $quando = " $DIM" + [char]0x21BB + " " + [DateTimeOffset]::FromUnixTimeSeconds($reset).ToLocalTime().ToString('ddd HH:mm', $IT) + $R }
  }
  $parti += "$DIM$($f[1])$R $(Barra $p) $p%$quando"
}

Write-Output ($parti -join $DOT)
