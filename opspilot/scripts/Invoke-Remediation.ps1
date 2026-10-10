<#
.SYNOPSIS
    Exécute une action de remédiation OpsPilot sur une Azure Container App.

.DESCRIPTION
    Appelé par l'agent de triage pour les actions en liste blanche. Utilise Azure CLI.
    Supporte -WhatIf : l'action est décrite sans être exécutée.

.EXAMPLE
    ./Invoke-Remediation.ps1 -Action restart_service -IncidentId INC-0001 -ResourceGroup rg-opspilot -AppName ca-opspilot-api -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('restart_service', 'scale_out')]
    [string] $Action,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^INC-\d{4}$')]
    [string] $IncidentId,

    [string] $ResourceGroup = 'rg-opspilot',
    [string] $AppName = 'ca-opspilot-api',
    [ValidateRange(1, 10)]
    [int] $Replicas = 3
)

$ErrorActionPreference = 'Stop'

function Write-OpsLog {
    param([string] $Message)
    Write-Output ('[{0}] [{1}] {2}' -f (Get-Date -Format 's'), $IncidentId, $Message)
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Azure CLI (az) est requis : https://learn.microsoft.com/cli/azure/install-azure-cli'
}

switch ($Action) {
    'restart_service' {
        $revision = az containerapp revision list --name $AppName --resource-group $ResourceGroup `
            --query "[?properties.active].name | [0]" --output tsv
        if (-not $revision) { throw "Aucune révision active trouvée pour $AppName." }

        if ($PSCmdlet.ShouldProcess("$AppName/$revision", 'Redémarrer la révision')) {
            az containerapp revision restart --name $AppName --resource-group $ResourceGroup --revision $revision | Out-Null
            Write-OpsLog "Révision $revision redémarrée."
        }
    }
    'scale_out' {
        if ($PSCmdlet.ShouldProcess($AppName, "Passer à $Replicas réplicas minimum")) {
            az containerapp update --name $AppName --resource-group $ResourceGroup --min-replicas $Replicas | Out-Null
            Write-OpsLog "Nombre minimal de réplicas porté à $Replicas."
        }
    }
}
