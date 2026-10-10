output "api_url" {
  description = "URL publique de l'API OpsPilot"
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "acr_login_server" {
  description = "Registre où pousser l'image Docker"
  value       = azurerm_container_registry.acr.login_server
}

output "log_analytics_workspace_id" {
  description = "Espace Log Analytics où exécuter les requêtes KQL"
  value       = azurerm_log_analytics_workspace.law.workspace_id
}
