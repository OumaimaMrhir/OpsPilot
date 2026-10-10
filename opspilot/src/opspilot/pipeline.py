"""Pipeline complet : logs -> métriques -> anomalies -> incidents -> diagnostic -> ticket -> remédiation."""

from __future__ import annotations

import time

from pydantic import BaseModel

from .agent import diagnose, load_runbooks, remediate
from .correlate import correlate
from .detection import aggregate, detect
from .models import Anomaly, Diagnosis, Incident, LogEvent, Metric, RemediationResult
from .servicenow import MockServiceNow, ServiceNowClient, incident_payload


class StepTiming(BaseModel):
    step: str
    duration_ms: float
    output: str


class PipelineResult(BaseModel):
    metrics: list[Metric]
    anomalies: list[Anomaly]
    incidents: list[Incident]
    diagnoses: list[Diagnosis]
    tickets: dict[str, str]
    remediations: list[RemediationResult]
    timings: list[StepTiming]


def run(events: list[LogEvent], snow: ServiceNowClient | MockServiceNow | None = None, dry_run: bool = True) -> PipelineResult:
    snow = snow or ServiceNowClient.from_env()
    timings: list[StepTiming] = []

    def step(name: str, fn, describe):
        t = time.perf_counter()
        out = fn()
        timings.append(StepTiming(step=name, duration_ms=round((time.perf_counter() - t) * 1000, 1), output=describe(out)))
        return out

    metrics = step("Agrégation", lambda: aggregate(events), lambda m: f"{len(m)} points de métriques")
    anomalies = step("Détection", lambda: detect(metrics), lambda a: f"{len(a)} anomalies")
    incidents = step("Corrélation", lambda: correlate(anomalies, metrics, events), lambda i: f"{len(i)} incident(s)")
    runbooks = load_runbooks()
    diagnoses = step("Triage IA", lambda: [diagnose(i, runbooks) for i in incidents], lambda d: f"{len(d)} diagnostic(s)")
    tickets = step(
        "ServiceNow",
        lambda: {i.id: snow.create_incident(incident_payload(i, d)) for i, d in zip(incidents, diagnoses, strict=True)},
        lambda t: f"{len(t)} ticket(s) créé(s)",
    )
    remediations = step(
        "Remédiation", lambda: [remediate(d, dry_run) for d in diagnoses], lambda r: ", ".join(x.status for x in r) or "aucune"
    )
    return PipelineResult(
        metrics=metrics,
        anomalies=anomalies,
        incidents=incidents,
        diagnoses=diagnoses,
        tickets=tickets,
        remediations=remediations,
        timings=timings,
    )
