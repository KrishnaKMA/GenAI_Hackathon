$ErrorActionPreference = "Stop"

$loginBody = @{
    username = "admin"
    password = "admin123"
} | ConvertTo-Json

$login = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/auth/login" -ContentType "application/json" -Body $loginBody
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$scenarios = @(
    @{
        name = "clean_property"
        claim = @{
            claimant_name = "Alice Demo"
            provider_name = "Property Claims Group"
            repair_shop_name = $null
            claim_amount = 1800
            claim_type = "property"
            incident_date = "2024-06-01"
            filing_date = "2024-06-04"
            prior_claim_count = 0
            days_since_last_claim = 400
            adjuster_id = "admin"
        }
    },
    @{
        name = "high_auto_repair"
        claim = @{
            claimant_name = "Brian Demo"
            provider_name = "Metro Auto Clinic"
            repair_shop_name = "Quick Fix Auto"
            claim_amount = 32500
            claim_type = "auto_repair"
            incident_date = "2024-04-10"
            filing_date = "2024-04-11"
            prior_claim_count = 2
            days_since_last_claim = 45
            adjuster_id = "admin"
        }
    },
    @{
        name = "critical_repeat_claimant"
        claim = @{
            claimant_name = "Brian Demo"
            provider_name = "Metro Auto Clinic"
            repair_shop_name = "Quick Fix Auto"
            claim_amount = 49500
            claim_type = "auto_repair"
            incident_date = "2024-04-20"
            filing_date = "2024-04-21"
            prior_claim_count = 4
            days_since_last_claim = 10
            adjuster_id = "admin"
        }
    },
    @{
        name = "medical_no_shop"
        claim = @{
            claimant_name = "Cara Demo"
            provider_name = "City Medical Center"
            repair_shop_name = $null
            claim_amount = 12000
            claim_type = "medical"
            incident_date = "2024-05-15"
            filing_date = "2024-05-15"
            prior_claim_count = 1
            days_since_last_claim = 120
            adjuster_id = "admin"
        }
    }
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
    foreach ($scoreName in @("gnn_score", "isolation_score", "combined_score")) {
        $score = [double]$analysis.$scoreName
        if ($score -lt 0 -or $score -gt 100) {
            throw "Scenario $($scenario.name) returned invalid $scoreName=$score"
        }
    }

    if ($analysis.graph_nodes.Count -lt 2) {
        throw "Scenario $($scenario.name) returned too few graph nodes"
    }

    $results += [pscustomobject]@{
        scenario = $scenario.name
        claim_token = $created.claim_token
        risk_level = $analysis.risk_level
        gnn_score = $analysis.gnn_score
        isolation_score = $analysis.isolation_score
        combined_score = $analysis.combined_score
        graph_nodes = $analysis.graph_nodes.Count
        graph_edges = $analysis.graph_edges.Count
    }
}

$results | Format-Table -AutoSize
