<#
.SYNOPSIS
    Sätt en hemlighet utan att den passerar chatt, historik eller processargument.

.DESCRIPTION
    En hemlighet ska gå direkt från där den skapas till där den lagras — via stdin.
    Klistras den i ett kommandoargument (`gh secret set X --body "<token>"`) hamnar den i
    processlistan och i shell-historiken, och då är den läckt.

    Värdet läses med en DOLD prompt och pipas till `gh secret set` (Actions-secret) eller
    skrivs till en otrackad env-fil. Det syns aldrig på skärmen.

.EXAMPLE
    pwsh scripts/set_secret.ps1 -Name VAULT_TOKEN -Repo Cortxt-io/Project-CNS

.EXAMPLE
    pwsh scripts/set_secret.ps1 -Name ANTHROPIC_API_KEY -EnvFile .env
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Name,

    # GitHub Actions-secret. Default: repot du står i.
    [string]$Repo,

    # Alternativ: skriv till en otrackad env-fil i stället för en Actions-secret.
    [string]$EnvFile
)

$ErrorActionPreference = 'Stop'

if ($EnvFile -and $Repo) {
    throw "Välj ett mål: -Repo (Actions-secret) ELLER -EnvFile (lokal nyckel)."
}

# Dold inmatning. Värdet renderas aldrig, hamnar aldrig i historiken.
$secure = Read-Host -Prompt "Klistra in värdet för $Name (dolt)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if (-not $plain) { throw "Tomt värde — inget sattes." }

try {
    if ($EnvFile) {
        # Lokal nyckel. Filen MÅSTE vara gitignored — annars är hemligheten committad.
        $ignored = & git check-ignore $EnvFile 2>$null
        if (-not $ignored) {
            throw "$EnvFile är INTE gitignored. Lägg till den i .gitignore först — annars committas hemligheten."
        }
        $lines = @()
        if (Test-Path $EnvFile) {
            $lines = Get-Content $EnvFile | Where-Object { $_ -notmatch "^$([regex]::Escape($Name))=" }
        }
        $lines + "$Name=$plain" | Set-Content $EnvFile -Encoding utf8
        Write-Host "Skrev $Name till $EnvFile (otrackad)." -ForegroundColor Green
    } else {
        # Actions-secret. Via stdin — aldrig som --body.
        $args = @('secret', 'set', $Name)
        if ($Repo) { $args += @('--repo', $Repo) }
        $plain | & gh @args
        if ($LASTEXITCODE -ne 0) { throw "gh secret set misslyckades (exit $LASTEXITCODE)." }
        Write-Host "Satte $Name som Actions-secret$(if ($Repo) { " i $Repo" })." -ForegroundColor Green
    }
} finally {
    # Nolla klartexten i minnet så snart den gjort sitt.
    $plain = $null
    [GC]::Collect()
}
