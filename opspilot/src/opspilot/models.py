"""Modèles de données de la plateforme."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["P1", "P2", "P3"]


class LogEvent(BaseModel):
    timestamp: datetime
    service: str
    level: Literal["INFO", "WARN", "ERROR"]
    message: str
    latency_ms: float


class Metric(BaseModel):
    service: str
    minute: datetime
    requests: int
    errors: int
    error_rate: float
    p95_latency_ms: float


class Anomaly(BaseModel):
    service: str
    minute: datetime
    signal: Literal["error_rate", "p95_latency_ms"]
    value: float
    baseline: float
    zscore: float


class Incident(BaseModel):
    id: str
    service: str
    start: datetime
    end: datetime
    severity: Severity
    signals: list[str]
    peak_error_rate: float
    peak_p95_latency_ms: float
    top_errors: list[tuple[str, int]] = Field(default_factory=list)


class Diagnosis(BaseModel):
    incident_id: str
    runbook_id: str | None
    probable_cause: str
    recommended_action: str
    automated: bool
    confidence: float
    summary: str
    mode: str = "règles"


class RemediationResult(BaseModel):
    incident_id: str
    action: str
    status: Literal["exécutée (simulation)", "en attente de validation", "aucune action"]
    detail: str
