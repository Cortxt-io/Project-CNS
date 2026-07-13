<#
.SYNOPSIS
    Set a secret without it passing through chat, history or process arguments.

.DESCRIPTION
    A secret must travel straight from where it is created to where it is stored, via stdin.
    Paste it into a command argument (gh secret set X --body "<token>") and it lands in the
    process list and the shell history. At that point it is leaked and must be rotated.

    The value is read with a HIDDEN prompt and piped to `gh secret set`, or written to an
    untracked env file. It is never echoed.

    ASCII only, deliberately: Windows PowerShell 5.1 reads a UTF-8 file without BOM as ANSI,
    and an em-dash or an "a-ring" turns into a parser error. A script that will not run is
    worse than no script, because the fallback is pasting the token on the command line.

.EXAMPLE
    powershell -File scripts/set_secret.ps1 -Name VAULT_TOKEN -Repo Cortxt-io/Project-CNS

.EXAMPLE
    powershell -File scripts/set_secret.ps1 -Name ANTHROPIC_API_KEY -EnvFile .env
#>
[CmdletBinding()]
param(
    # The NAME of the secret. Never the value.
    [Parameter(Mandatory = $true)]
    [string]$Name,

    # GitHub Actions secret. Defaults to the repo you are standing in.
    [string]$Repo,

    # Alternative target: an untracked env file instead of an Actions secret.
    [string]$EnvFile
)

$ErrorActionPreference = 'Stop'

if ($EnvFile -and $Repo) {
    throw "Pick one target: -Repo (Actions secret) OR -EnvFile (local key)."
}

if ($Name -match '^(gh[pousr]_|github_pat_|sk-ant-)') {
    throw "That looks like a TOKEN VALUE, not a name. -Name is the secret's NAME (e.g. VAULT_TOKEN). Revoke it: it is now in your shell history."
}

# Hidden input. The value is never rendered and never enters history.
$secure = Read-Host -Prompt "Paste the value for $Name (hidden)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if (-not $plain) { throw "Empty value. Nothing was set." }

try {
    if ($EnvFile) {
        # Local key. The file MUST be gitignored, or the secret gets committed.
        $ignored = & git check-ignore $EnvFile 2>$null
        if (-not $ignored) {
            throw "$EnvFile is NOT gitignored. Add it to .gitignore first, or the secret gets committed."
        }
        $lines = @()
        if (Test-Path $EnvFile) {
            $lines = Get-Content $EnvFile | Where-Object { $_ -notmatch "^$([regex]::Escape($Name))=" }
        }
        $lines + "$Name=$plain" | Set-Content $EnvFile -Encoding utf8
        Write-Host "Wrote $Name to $EnvFile (untracked)." -ForegroundColor Green
    } else {
        # Actions secret. Via stdin, never as --body.
        $ghArgs = @('secret', 'set', $Name)
        if ($Repo) { $ghArgs += @('--repo', $Repo) }
        $plain | & gh @ghArgs
        if ($LASTEXITCODE -ne 0) { throw "gh secret set failed (exit $LASTEXITCODE)." }
        Write-Host "Set $Name as an Actions secret." -ForegroundColor Green
    }
} finally {
    $plain = $null
    [GC]::Collect()
}
