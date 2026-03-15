Param(
    [string]$DatabaseName = "CLAIMDB",
    [switch]$UseDb2
)

$ErrorActionPreference = "Stop"

if ($UseDb2) {
    Write-Host "[bootstrap] starting local Db2 container"
    docker compose up -d db2 | Out-Null

    $maxAttempts = 30
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        try {
            docker compose exec db2 bash -lc "su - db2inst1 -c 'db2level'" | Out-Null
            break
        } catch {
            if ($attempt -eq $maxAttempts) {
                throw "[bootstrap] Db2 instance did not become ready"
            }
            Write-Host "[bootstrap] waiting for Db2 instance ($attempt/$maxAttempts)"
            Start-Sleep -Seconds 10
        }
    }

    $exists = $false
    try {
        $directory = docker compose exec db2 bash -lc "su - db2inst1 -c 'db2 list db directory'" 2>$null
        if ($directory -match "Database name\s*=\s*$DatabaseName") {
            $exists = $true
        }
    } catch {
        $exists = $false
    }

    if (-not $exists) {
        Write-Host "[bootstrap] creating $DatabaseName"
        docker compose exec db2 bash -lc "su - db2inst1 -c 'db2 create db $DatabaseName'" | Out-Null
    } else {
        Write-Host "[bootstrap] $DatabaseName already exists"
    }
} else {
    Write-Host "[bootstrap] starting demo stack with SQLite backend"
}

Write-Host "[bootstrap] starting backend and frontend"
docker compose up -d backend frontend | Out-Null
Write-Host "[bootstrap] done"
