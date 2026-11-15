param([ValidateSet("installa", "rimuovi")][string]$Azione = "installa", [string]$CartellaApp)
$ErrorActionPreference = "Stop"
$nome = "SecondBrainStudio.InboxMenu"
$logDir = Join-Path $env:USERPROFILE ".claude\second-brain"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "menu-inbox.log"
try {
  if ($Azione -eq "rimuovi") {
    Get-AppxPackage -Name $nome | Remove-AppxPackage -ErrorAction Stop
  } else {
    if ([Environment]::OSVersion.Version.Build -lt 22000) { exit 0 }
    $package = Join-Path $CartellaApp "_shell\InboxMenu.msix"
    if (-not (Test-Path -LiteralPath $package)) { throw "Pacchetto del menu assente" }
    # Windows verifica la fiducia della firma. Non si importano certificati qui.
    Add-AppxPackage -Path $package -ExternalLocation $CartellaApp -ForceUpdateFromAnyVersion -ErrorAction Stop
  }
  Add-Content -LiteralPath $logFile -Value "$(Get-Date -Format o) $Azione OK"
  exit 0
} catch {
  Add-Content -LiteralPath $logFile -Value "$(Get-Date -Format o) $Azione ERRORE: $($_.Exception.Message)"
  exit 1
}
