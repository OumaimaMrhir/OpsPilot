variable "subscription_id" {
  description = "Identifiant de l'abonnement Azure"
  type        = string
}

variable "location" {
  description = "Région Azure"
  type        = string
  default     = "francecentral"
}

variable "prefix" {
  description = "Préfixe des ressources (lettres minuscules et chiffres)"
  type        = string
  default     = "opspilot"
}

variable "container_image" {
  description = "Image de l'API OpsPilot (à remplacer par <acr>.azurecr.io/opspilot:<tag> après le premier push)"
  type        = string
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}

variable "target_port" {
  description = "Port exposé par le conteneur (8000 pour l'API OpsPilot, 80 pour l'image de démarrage)"
  type        = number
  default     = 80
}

variable "alert_email" {
  description = "Adresse qui reçoit les alertes d'incident"
  type        = string
}
