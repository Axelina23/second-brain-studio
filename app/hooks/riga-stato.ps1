# Status line di Claude Code: modello, contesto usato e uso del piano (finestra di
# 5 ore e settimanale) come nelle impostazioni dell'app: barra di utilizzo, % usata
# e quando si azzera. Claude Code passa i dati in JSON su stdin.
# Barra blu, gialla dall'80%, rossa dal 95%.
# Nota: niente lettere accentate in questo file (PowerShell 5.1).

[Console]::InputEncoding  = [Text.Encoding]::UTF8
[Console]::OutputEncoding = [Text.Encoding]::UTF8
try { $d = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { exit 0 }

# Ultimo uso del piano anche per Second Brain Studio (barra di stato): uso.json in cache,
# scritto in modo atomico; un errore qui non deve mai rompere la riga di stato
if ($d.rate_limits) {
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
