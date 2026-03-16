Param(
    [switch]$ResetData
)

$ErrorActionPreference = "Stop"

function New-Scenario {
    param(
        [string]$Name,
        [string]$Claimant,
        [string]$Provider,
        [string]$RepairShop,
        [double]$Amount,
        [string]$ClaimType,
        [string]$IncidentDate,
        [string]$FilingDate,
        [int]$PriorClaims,
        [int]$DaysSinceLastClaim
    )

    return @{
        name = $Name
        claim = @{
            claimant_name = $Claimant
            provider_name = $Provider
            repair_shop_name = if ($RepairShop) { $RepairShop } else { $null }
            claim_amount = $Amount
            claim_type = $ClaimType
            incident_date = $IncidentDate
            filing_date = $FilingDate
            prior_claim_count = $PriorClaims
            days_since_last_claim = $DaysSinceLastClaim
            adjuster_id = "admin"
        }
    }
}

if ($ResetData) {
    Write-Host "[demo-matrix] resetting local SQLite demo data"
    docker compose exec backend python -c "import sqlite3; conn=sqlite3.connect('/app/data/local.db'); cur=conn.cursor(); cur.executescript('DELETE FROM inference_log; DELETE FROM graph_edges; DELETE FROM tasks; DELETE FROM claims; DELETE FROM entities;'); conn.commit(); conn.close(); print('reset-ok')" | Out-Null
}

$loginBody = @{
    username = "admin"
    password = "admin123"
} | ConvertTo-Json

$login = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/auth/login" -ContentType "application/json" -Body $loginBody
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$scenarios = @(
    (New-Scenario -Name "clean_property_01" -Claimant "Alice Hart" -Provider "North Property Group" -RepairShop "" -Amount 1600 -ClaimType "property" -IncidentDate "2026-01-03" -FilingDate "2026-01-05" -PriorClaims 0 -DaysSinceLastClaim 420)
    (New-Scenario -Name "clean_property_02" -Claimant "Ben Morris" -Provider "Harbor Property Group" -RepairShop "" -Amount 2200 -ClaimType "property" -IncidentDate "2026-01-04" -FilingDate "2026-01-07" -PriorClaims 0 -DaysSinceLastClaim 510)
    (New-Scenario -Name "clean_medical_01" -Claimant "Clara Reed" -Provider "Westside Clinic" -RepairShop "" -Amount 4800 -ClaimType "medical" -IncidentDate "2026-01-08" -FilingDate "2026-01-10" -PriorClaims 0 -DaysSinceLastClaim 365)
    (New-Scenario -Name "clean_medical_02" -Claimant "Daniel Frost" -Provider "Greenview Medical" -RepairShop "" -Amount 6200 -ClaimType "medical" -IncidentDate "2026-01-09" -FilingDate "2026-01-11" -PriorClaims 1 -DaysSinceLastClaim 280)
    (New-Scenario -Name "clean_liability_01" -Claimant "Evelyn Price" -Provider "Liability Partners" -RepairShop "" -Amount 3500 -ClaimType "liability" -IncidentDate "2026-01-10" -FilingDate "2026-01-13" -PriorClaims 0 -DaysSinceLastClaim 600)
    (New-Scenario -Name "clean_property_03" -Claimant "Frank Olsen" -Provider "Maple Property Claims" -RepairShop "" -Amount 2700 -ClaimType "property" -IncidentDate "2026-01-11" -FilingDate "2026-01-14" -PriorClaims 1 -DaysSinceLastClaim 300)

    (New-Scenario -Name "moderate_auto_01" -Claimant "Gina Torres" -Provider "Metro Auto Clinic" -RepairShop "Quick Fix Auto" -Amount 18000 -ClaimType "auto_repair" -IncidentDate "2026-01-15" -FilingDate "2026-01-16" -PriorClaims 1 -DaysSinceLastClaim 120)
    (New-Scenario -Name "moderate_auto_02" -Claimant "Henry Shaw" -Provider "City Auto Care" -RepairShop "Urban Repair Hub" -Amount 20500 -ClaimType "auto_repair" -IncidentDate "2026-01-16" -FilingDate "2026-01-17" -PriorClaims 1 -DaysSinceLastClaim 90)
    (New-Scenario -Name "moderate_auto_03" -Claimant "Iris Kent" -Provider "Metro Auto Clinic" -RepairShop "Quick Fix Auto" -Amount 24000 -ClaimType "auto_repair" -IncidentDate "2026-01-18" -FilingDate "2026-01-19" -PriorClaims 2 -DaysSinceLastClaim 75)
    (New-Scenario -Name "moderate_medical_01" -Claimant "Jon Lake" -Provider "Central Injury Center" -RepairShop "" -Amount 14500 -ClaimType "medical" -IncidentDate "2026-01-19" -FilingDate "2026-01-20" -PriorClaims 2 -DaysSinceLastClaim 110)
    (New-Scenario -Name "moderate_medical_02" -Claimant "Kara West" -Provider "Central Injury Center" -RepairShop "" -Amount 13500 -ClaimType "medical" -IncidentDate "2026-01-20" -FilingDate "2026-01-21" -PriorClaims 1 -DaysSinceLastClaim 95)
    (New-Scenario -Name "moderate_property_01" -Claimant "Liam Ross" -Provider "Maple Property Claims" -RepairShop "" -Amount 11200 -ClaimType "property" -IncidentDate "2026-01-21" -FilingDate "2026-01-22" -PriorClaims 1 -DaysSinceLastClaim 140)

    (New-Scenario -Name "repeat_claimant_seed_01" -Claimant "Mason Cole" -Provider "Premier Auto Assessors" -RepairShop "Silverline Collision" -Amount 26000 -ClaimType "auto_repair" -IncidentDate "2026-02-01" -FilingDate "2026-02-02" -PriorClaims 2 -DaysSinceLastClaim 60)
    (New-Scenario -Name "repeat_claimant_seed_02" -Claimant "Mason Cole" -Provider "Premier Auto Assessors" -RepairShop "Silverline Collision" -Amount 42000 -ClaimType "auto_repair" -IncidentDate "2026-02-05" -FilingDate "2026-02-06" -PriorClaims 4 -DaysSinceLastClaim 8)
    (New-Scenario -Name "linked_claimant_01" -Claimant "Nora Diaz" -Provider "Premier Auto Assessors" -RepairShop "Silverline Collision" -Amount 36500 -ClaimType "auto_repair" -IncidentDate "2026-02-06" -FilingDate "2026-02-07" -PriorClaims 2 -DaysSinceLastClaim 14)
    (New-Scenario -Name "linked_claimant_02" -Claimant "Owen Blake" -Provider "Premier Auto Assessors" -RepairShop "Silverline Collision" -Amount 39800 -ClaimType "auto_repair" -IncidentDate "2026-02-08" -FilingDate "2026-02-09" -PriorClaims 3 -DaysSinceLastClaim 12)
    (New-Scenario -Name "linked_claimant_03" -Claimant "Pia Novak" -Provider "Premier Auto Assessors" -RepairShop "Silverline Collision" -Amount 44500 -ClaimType "auto_repair" -IncidentDate "2026-02-09" -FilingDate "2026-02-10" -PriorClaims 3 -DaysSinceLastClaim 6)
    (New-Scenario -Name "linked_claimant_04" -Claimant "Quinn Yates" -Provider "Premier Auto Assessors" -RepairShop "Silverline Collision" -Amount 47000 -ClaimType "auto_repair" -IncidentDate "2026-02-10" -FilingDate "2026-02-10" -PriorClaims 4 -DaysSinceLastClaim 5)

    (New-Scenario -Name "shop_cluster_01" -Claimant "Rita Hayes" -Provider "Metro Auto Clinic" -RepairShop "Quick Fix Auto" -Amount 33500 -ClaimType "auto_repair" -IncidentDate "2026-02-11" -FilingDate "2026-02-12" -PriorClaims 2 -DaysSinceLastClaim 20)
    (New-Scenario -Name "shop_cluster_02" -Claimant "Sam Turner" -Provider "Metro Auto Clinic" -RepairShop "Quick Fix Auto" -Amount 35800 -ClaimType "auto_repair" -IncidentDate "2026-02-12" -FilingDate "2026-02-13" -PriorClaims 2 -DaysSinceLastClaim 16)
    (New-Scenario -Name "shop_cluster_03" -Claimant "Tina Boyle" -Provider "Metro Auto Clinic" -RepairShop "Quick Fix Auto" -Amount 38200 -ClaimType "auto_repair" -IncidentDate "2026-02-13" -FilingDate "2026-02-14" -PriorClaims 3 -DaysSinceLastClaim 11)

    (New-Scenario -Name "mixed_provider_01" -Claimant "Uma Patel" -Provider "Central Injury Center" -RepairShop "" -Amount 19500 -ClaimType "medical" -IncidentDate "2026-02-15" -FilingDate "2026-02-15" -PriorClaims 2 -DaysSinceLastClaim 35)
    (New-Scenario -Name "mixed_provider_02" -Claimant "Victor Lane" -Provider "Central Injury Center" -RepairShop "" -Amount 20800 -ClaimType "medical" -IncidentDate "2026-02-16" -FilingDate "2026-02-16" -PriorClaims 2 -DaysSinceLastClaim 28)
    (New-Scenario -Name "mixed_provider_03" -Claimant "Will Ford" -Provider "Central Injury Center" -RepairShop "" -Amount 23000 -ClaimType "medical" -IncidentDate "2026-02-17" -FilingDate "2026-02-18" -PriorClaims 3 -DaysSinceLastClaim 18)
)

$results = @()

foreach ($scenario in $scenarios) {
    $claimJson = $scenario.claim | ConvertTo-Json
    $created = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/claims" -Headers $headers -ContentType "application/json" -Body $claimJson
    $report = Invoke-RestMethod -Method Post -Uri ("http://localhost:8000/analyze/" + $created.claim_token) -Headers $headers

    if (-not $report.analysis) {
        throw "Scenario $($scenario.name) returned no analysis payload"
    }

    $analysis = $report.analysis
    $results += [pscustomobject]@{
        scenario = $scenario.name
        claim_token = $created.claim_token
        risk_level = $analysis.risk_level
        combined_score = [math]::Round([double]$analysis.combined_score, 2)
        gnn_score = [math]::Round([double]$analysis.gnn_score, 2)
        isolation_score = [math]::Round([double]$analysis.isolation_score, 2)
        graph_nodes = $analysis.graph_nodes.Count
        graph_edges = $analysis.graph_edges.Count
        top_evidence = if ($analysis.gnn_evidence.Count -gt 0) { $analysis.gnn_evidence[0].human_label } else { "" }
    }
}

$byRisk = $results | Group-Object risk_level | Sort-Object Name | ForEach-Object {
    [pscustomobject]@{
        risk_level = $_.Name
        count = $_.Count
        avg_score = [math]::Round((($_.Group | Measure-Object -Property combined_score -Average).Average), 2)
    }
}

Write-Host ""
Write-Host "Scenario Summary"
$results | Format-Table scenario, claim_token, risk_level, combined_score, graph_nodes, graph_edges -AutoSize

Write-Host ""
Write-Host "Risk Breakdown"
$byRisk | Format-Table -AutoSize
