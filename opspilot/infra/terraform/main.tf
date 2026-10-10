locals {
  tags = {
    project    = "opspilot"
    managed_by = "terraform"
  }
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.prefix}"
  location = var.location
  tags     = local.tags
}

# --- Observabilité -----------------------------------------------------------

resource "azurerm_log_analytics_workspace" "law" {
  name                = "log-${var.prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_application_insights" "appi" {
  name                = "appi-${var.prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  workspace_id        = azurerm_log_analytics_workspace.law.id
  application_type    = "web"
  tags                = local.tags
}

# --- Hébergement de l'API ------------------------------------------------------

resource "azurerm_container_registry" "acr" {
  name                = "acr${var.prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${var.prefix}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_container_app_environment" "env" {
  name                       = "cae-${var.prefix}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  tags                       = local.tags
}

resource "azurerm_container_app" "api" {
  name                         = "ca-${var.prefix}-api"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  secret {
    name  = "appinsights-connection-string"
    value = azurerm_application_insights.appi.connection_string
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "opspilot-api"
      image  = var.container_image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = var.target_port

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}

# --- Alerte : taux d'erreur > 10 % sur 5 minutes ------------------------------

resource "azurerm_monitor_action_group" "oncall" {
  name                = "ag-${var.prefix}-oncall"
  resource_group_name = azurerm_resource_group.rg.name
  short_name          = "oncall"
  tags                = local.tags

  email_receiver {
    name          = "astreinte"
    email_address = var.alert_email
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "error_rate" {
  name                 = "alert-${var.prefix}-error-rate"
  resource_group_name  = azurerm_resource_group.rg.name
  location             = azurerm_resource_group.rg.location
  description          = "Un service dépasse 10 % d'erreurs sur 5 minutes"
  severity             = 1
  evaluation_frequency = "PT5M"
  window_duration      = "PT5M"
  scopes               = [azurerm_log_analytics_workspace.law.id]
  tags                 = local.tags

  criteria {
    query                   = file("${path.module}/../../kql/04_alerte_taux_erreur.kql")
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.oncall.id]
  }
}
