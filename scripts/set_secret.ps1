<#
.SYNOPSIS
  Sätt en GitHub Actions-secret säkert — hemligheten passerar aldrig chatt,
  shell-historik eller processargument.

.DESCRIPTION
  Hemligheter ska gå direkt från där de skapas till där de lagras, via stdin.
  Det här skriptet läser värdet med en dold prompt (Read-Host -AsSecureString)
  och pipe:ar det till `gh secret set <namn> --repo <repo>` på stdin — utan
  `--body`, så värdet aldrig hamnar i kommandoraden eller `gh`-anropets argument.

  Generering (t.ex. `claude setup-token`) är interaktiv/webbläsarbaserad och kan
  inte automatiseras helt; kör den separat, kopiera token:n, och klistra in den
  i den DOLDA prompten här (inte i chatten, inte som argument).

.PARAMETER Name
  Secret-namnet, t.ex. CLAUDE_CODE_OAUTH_TOKEN.

.PARAMETER Repo
  owner/repo, default rian010194/Project-CNS.

.PARAMETER Env
  Valfritt: skriv även till en lokal otrackad .env-fil (KEY=VALUE) i stället för
  GitHub. Använd för lokala nycklar (jfr .cns-agent-key). Filen måste vara gitignored.

.EXAMPLE
  pwsh scripts/set_secret.ps1 -Name CLAUDE_CODE_OAUTH_TOKEN
  # → kör `claude setup-token` i en annan terminal, kopiera, klistra i dolda prompten

.EXAMPLE
  pwsh scripts/set_secret.ps1 -Name ANTHROPIC_API_KEY -Env .env
  # → lagrar lokalt i .env i stället för GitHub
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Name,

    [string]$Repo = 'rian010194/Project-CNS',

    [string]$Env
)

$ErrorActionPreference = 'Stop'

# Läs värdet dolt — syns aldrig på skärmen, i historik eller i argument.
$secure = Read-Host -AsSecureString "Klistra in värdet för $Name (dolt — syns inte)"
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if ([string]::IsNullOrWhiteSpace($plain)) {
    Write-Error "Tomt värde — inget sattes."
    exit 1
}

if ($Env) {
    # Lokal otrackad fil. Varna om den inte är gitignored.
    $tracked = (& git check-ignore $Env) 2>$null
    if (-not $tracked) {
        Write-Warning "$Env verkar INTE vara gitignored — lägg den i .gitignore innan du committar något."
    }
    # Ersätt ev. befintlig rad för nyckeln, annars lägg till.
    $line = "$Name=$plain"
    if (Test-Path $Env) {
        $content = Get-Content $Env | Where-Object { $_ -notmatch "^$([regex]::Escape($Name))=" }
        ($content + $line) | Set-Content -Encoding utf8 $Env
    }
    else {
        $line | Set-Content -Encoding utf8 $Env
    }
    Write-Host "✓ $Name skrivet till $Env (lokalt, otrackat)."
}
else {
    # Pipe:a på stdin — värdet hamnar ALDRIG i kommandoraden/argumenten.
    $plain | & gh secret set $Name --repo $Repo
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Secret $Name satt på $Repo."
    }
    else {
        Write-Error "gh secret set misslyckades (exit $LASTEXITCODE)."
    }
}

# Nolla klartext-variabeln direkt.
$plain = $null
[System.GC]::Collect()
