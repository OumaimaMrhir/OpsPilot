<#
.SYNOPSIS
    Interroge l'API OpsPilot et affiche les incidents détectés et leur diagnostic.

.EXAMPLE
    ./Get-OpsPilotIncidents.ps1 -ApiUrl http://localhost:8000
#>
[CmdletBinding()]
param(
    [string] $ApiUrl = 'http://localhost:8000'
)

$ErrorActionPreference = 'Stop'

$result = Invoke-RestMethod -Method Post -Uri "$ApiUrl/analyze/demo"

$result.incidents | ForEach-Object {
    $incident = $_
    $diagnosis = $result.diagnoses | Where-Object { $_.incident_id -eq $incident.id }
    [PSCustomObject]@{
        Incident   = $incident.id
        Service    = $incident.service
        Severite   = $incident.severity
        Debut      = ([datetime] $incident.start).ToString('HH:mm')
        Ticket     = $result.tickets.($incident.id)
        Runbook    = $diagnosis.runbook_id
        Action     = $diagnosis.recommended_action
        Automatise = $diagnosis.automated
    }
} | Format-Table -AutoSize
