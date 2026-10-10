"""Intégration ServiceNow via la Table API (création d'incidents).

Sans identifiants, un client simulé enregistre les tickets en mémoire : utile pour les tests et la démo.
"""

from __future__ import annotations

import os

import httpx

from .models import Diagnosis, Incident

URGENCY = {"P1": "1", "P2": "2", "P3": "3"}


def incident_payload(incident: Incident, diagnosis: Diagnosis) -> dict:
    return {
        "short_description": f"[OpsPilot] {incident.service} dégradé – {incident.severity}",
        "description": diagnosis.summary,
        "urgency": URGENCY[incident.severity],
        "impact": URGENCY[incident.severity],
        "category": "software",
        "cmdb_ci": incident.service,
        "correlation_id": incident.id,
        "work_notes": (
            f"Runbook : {diagnosis.runbook_id or 'aucun'} | action : {diagnosis.recommended_action} "
            f"| confiance : {diagnosis.confidence:.0%}"
        ),
    }


class ServiceNowClient:
    def __init__(self, instance: str, user: str, password: str) -> None:
        self.base = f"https://{instance}.service-now.com/api/now/table/incident"
        self.auth = (user, password)

    @classmethod
    def from_env(cls) -> ServiceNowClient | MockServiceNow:
        instance, user, pwd = (os.getenv(k) for k in ("SNOW_INSTANCE", "SNOW_USER", "SNOW_PASSWORD"))
        return cls(instance, user, pwd) if instance and user and pwd else MockServiceNow()

    def create_incident(self, payload: dict) -> str:
        r = httpx.post(self.base, auth=self.auth, json=payload, headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        return r.json()["result"]["number"]


class MockServiceNow:
    def __init__(self) -> None:
        self.tickets: list[dict] = []

    def create_incident(self, payload: dict) -> str:
        number = f"INC{1000010 + len(self.tickets)}"
        self.tickets.append({"number": number, **payload})
        return number
