[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("--generate", "--run-dry", "--apply", "--help")]
    [string]$Action = "--help"
)

$ErrorActionPreference = "Stop"

$Network = "faveley_faiv-migrations"
$Image = "faiveley-migrations"
$ProjectRoot = "/app"
$HostProjectRoot = Split-Path -Parent $PSScriptRoot

function Show-Usage {
    @"
Usage:
  .\src\migration\run-migrations.ps1 <option>

Options:
  --generate  Génère une migration Alembic depuis les modèles SQLAlchemy.
  --run-dry   Génère le SQL d'une mise à niveau sans modifier la base.
  --apply     Applique les migrations jusqu'à la révision choisie.
  --help      Affiche cette aide.
"@
}

function Import-EnvironmentFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Le fichier $Path n'existe pas."
    }

    foreach ($Line in Get-Content -LiteralPath $Path) {
        $TrimmedLine = $Line.Trim()

        if ([string]::IsNullOrWhiteSpace($TrimmedLine) -or $TrimmedLine.StartsWith("#")) {
            continue
        }

        if ($TrimmedLine -notmatch '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
            continue
        }

        $Name = $Matches[1]
        $Value = $Matches[2].Trim()

        $HasDoubleQuotes = $Value.StartsWith('"') -and $Value.EndsWith('"')
        $HasSingleQuotes = $Value.StartsWith("'") -and $Value.EndsWith("'")
        if ($Value.Length -ge 2 -and ($HasDoubleQuotes -or $HasSingleQuotes)) {
            $Value = $Value.Substring(1, $Value.Length - 2)
        }

        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }

    Write-Host "Variables d'environnement chargées depuis $Path."
}

function Select-Databases {
    Write-Host ""
    Write-Host "Choisissez les bases à traiter :"
    Write-Host "1. main"
    Write-Host "2. users"
    Write-Host "3. les deux"
    Write-Host "4. annuler"

    while ($true) {
        $Choice = Read-Host "Votre choix"

        switch ($Choice) {
            "1" { return @("main") }
            "2" { return @("users") }
            "3" { return @("main", "users") }
            "4" { exit 0 }
            default { Write-Host "Sélection invalide." }
        }
    }
}

function Set-DatabaseConfiguration {
    param(
        [Parameter(Mandatory)]
        [ValidateSet("main", "users")]
        [string]$DatabaseType
    )

    if ($DatabaseType -eq "main") {
        $script:MigrationDir = "$ProjectRoot/main"
        $script:HostMigrationDir = Join-Path $HostProjectRoot "migration\main"
    }
    else {
        $script:MigrationDir = "$ProjectRoot/users"
        $script:HostMigrationDir = Join-Path $HostProjectRoot "migration\users"
    }

    if (-not (Test-Path -LiteralPath $HostMigrationDir -PathType Container)) {
        throw "Le répertoire $HostMigrationDir n'existe pas."
    }
}

function Test-Prerequisites {
    & docker network inspect $Network *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Le réseau Docker $Network n'existe pas."
    }

    & docker image inspect $Image *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Construction de l'image $Image..."
        & docker build `
            -f (Join-Path $HostProjectRoot "migration\dockerfile.migr") `
            -t $Image `
            $HostProjectRoot

        if ($LASTEXITCODE -ne 0) {
            throw "La construction de l'image $Image a échoué."
        }
    }
}

function New-BindMount {
    param(
        [Parameter(Mandatory)]
        [string]$Source,

        [Parameter(Mandatory)]
        [string]$Target
    )

    return "type=bind,source=$Source,target=$Target"
}

function Invoke-Alembic {
    param(
        [Parameter(Mandatory)]
        [string]$Command,

        [string]$OutputFile
    )

    $Arguments = @(
        "run", "--rm", "--network", $Network,
        "-e", "POSTGRES_HOST=$env:POSTGRES_HOST",
        "-e", "POSTGRES_PORT=$env:POSTGRES_PORT",
        "-e", "POSTGRES_USER_MIGR=$env:POSTGRES_USER_MIGR",
        "-e", "POSTGRES_PASSWORD_MIGR=$env:POSTGRES_PASSWORD_MIGR",
        "-e", "POSTGRES_USER_APP=$env:POSTGRES_USER_APP",
        "-e", "POSTGRES_DB_MAIN=$env:POSTGRES_DB_MAIN",
        "-e", "POSTGRES_DB_USERS=$env:POSTGRES_DB_USERS",
        "--mount", (New-BindMount $HostMigrationDir $MigrationDir),
        "--mount", (New-BindMount (Join-Path $HostProjectRoot "common") "/app/common")
    )

    if (-not [string]::IsNullOrWhiteSpace($OutputFile)) {
        $DryRunsDirectory = Join-Path $HostMigrationDir "dry-runs"
        New-Item -ItemType Directory -Force -Path $DryRunsDirectory | Out-Null
        $Arguments += @(
            "--mount",
            (New-BindMount $DryRunsDirectory "$MigrationDir/dry-runs")
        )
    }

    $Arguments += @(
        $Image,
        "bash", "-c",
        "alembic -c '$MigrationDir/alembic.ini' $Command"
    )

    if ([string]::IsNullOrWhiteSpace($OutputFile)) {
        & docker @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "La commande Alembic a échoué."
        }
        return
    }

    $OutputPath = Join-Path $HostMigrationDir "dry-runs\$OutputFile"
    & docker @Arguments | Out-File -FilePath $OutputPath -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        throw "La génération SQL a échoué."
    }

    Write-Host "SQL écrit dans $OutputPath."
}

function New-Migration {
    param([Parameter(Mandatory)][string]$DatabaseType)

    Set-DatabaseConfiguration $DatabaseType
    $MigrationName = Read-Host "Nom de la migration pour $DatabaseType"

    if ([string]::IsNullOrWhiteSpace($MigrationName)) {
        throw "Le nom de migration est requis."
    }

    $EscapedName = $MigrationName.Replace("'", "'\''")
    Invoke-Alembic "revision --autogenerate -m '$EscapedName'"
}

function New-DryRun {
    param([Parameter(Mandatory)][string]$DatabaseType)

    Set-DatabaseConfiguration $DatabaseType
    $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    Invoke-Alembic "upgrade head --sql" "$Timestamp-upgrade-head.sql"
}

function Select-Revision {
    param([Parameter(Mandatory)][string]$DatabaseType)

    Set-DatabaseConfiguration $DatabaseType

    $Arguments = @(
        "run", "--rm", "--network", $Network,
        "-e", "POSTGRES_HOST=$env:POSTGRES_HOST",
        "-e", "POSTGRES_PORT=$env:POSTGRES_PORT",
        "-e", "POSTGRES_USER_MIGR=$env:POSTGRES_USER_MIGR",
        "-e", "POSTGRES_PASSWORD_MIGR=$env:POSTGRES_PASSWORD_MIGR",
        "-e", "POSTGRES_DB_MAIN=$env:POSTGRES_DB_MAIN",
        "-e", "POSTGRES_DB_USERS=$env:POSTGRES_DB_USERS",
        "--mount", (New-BindMount $HostMigrationDir $MigrationDir),
        "--mount", (New-BindMount (Join-Path $HostProjectRoot "common") "/app/common"),
        $Image, "bash", "-c",
        "alembic -c '$MigrationDir/alembic.ini' history --verbose"
    )

    $History = @(& docker @Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Impossible de lire l'historique Alembic."
    }

    $Revisions = @($History | Where-Object { $_ -match "^Rev: " } | ForEach-Object { ($_ -split "\s+")[1] })
    if ($Revisions.Count -eq 0) {
        throw "Aucune migration trouvée pour $DatabaseType."
    }

    Write-Host ""
    Write-Host "Révisions disponibles pour $DatabaseType :"
    for ($Index = 0; $Index -lt $Revisions.Count; $Index++) {
        Write-Host "$($Index + 1). $($Revisions[$Index])"
    }

    $HeadIndex = $Revisions.Count + 1
    $CancelIndex = $Revisions.Count + 2
    Write-Host "$HeadIndex. head"
    Write-Host "$CancelIndex. annuler"

    while ($true) {
        $Choice = Read-Host "Révision cible"
        if ($Choice -match "^\d+$") {
            $ChoiceNumber = [int]$Choice
            if ($ChoiceNumber -ge 1 -and $ChoiceNumber -le $Revisions.Count) {
                return $Revisions[$ChoiceNumber - 1]
            }
            if ($ChoiceNumber -eq $HeadIndex) { return "head" }
            if ($ChoiceNumber -eq $CancelIndex) { exit 0 }
        }
        Write-Host "Sélection invalide."
    }
}

function Invoke-Migrations {
    param([Parameter(Mandatory)][string]$DatabaseType)

    $Revision = Select-Revision $DatabaseType
    Set-DatabaseConfiguration $DatabaseType
    Invoke-Alembic "upgrade $Revision"
    Write-Host "Migrations appliquées jusqu'à $Revision pour $DatabaseType."
}

if ($Action -eq "--help") {
    Show-Usage
    exit 0
}

$EnvironmentFile = Join-Path $HostProjectRoot "migration\.env.migr"
Import-EnvironmentFile $EnvironmentFile
Test-Prerequisites
$Databases = Select-Databases

foreach ($DatabaseType in $Databases) {
    switch ($Action) {
        "--generate" { New-Migration $DatabaseType }
        "--run-dry" { New-DryRun $DatabaseType }
        "--apply" { Invoke-Migrations $DatabaseType }
    }
}
