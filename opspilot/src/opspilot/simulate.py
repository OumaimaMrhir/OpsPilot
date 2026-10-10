"""Génère des logs applicatifs réalistes, avec un incident injecté, pour tester la plateforme sans environnement réel."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from .models import LogEvent

SERVICES = {
    "payment-api": ["Payment authorized", "Card token validated"],
    "catalog-api": ["Product list served", "Cache hit for catalog"],
    "auth-api": ["User authenticated", "Token refreshed"],
}

INCIDENT_ERRORS = [
    "DB connection pool exhausted (max=50)",
    "Timeout while acquiring connection from pool",
]


def generate(
    start: datetime | None = None,
    minutes: int = 120,
    incident_service: str = "payment-api",
    incident_start: int = 90,
    incident_duration: int = 12,
    seed: int = 42,
) -> list[LogEvent]:
    rng = random.Random(seed)
    start = start or datetime(2026, 10, 10, 8, 0)
    events: list[LogEvent] = []
    for minute in range(minutes):
        in_incident = incident_start <= minute < incident_start + incident_duration
        for service, messages in SERVICES.items():
            for _ in range(rng.randint(40, 60)):
                ts = start + timedelta(minutes=minute, seconds=rng.uniform(0, 59.9))
                degraded = in_incident and service == incident_service
                error_prob = 0.35 if degraded else 0.01
                latency = rng.gauss(900, 200) if degraded else rng.gauss(120, 25)
                if rng.random() < error_prob:
                    msg = rng.choice(INCIDENT_ERRORS) if degraded else "Upstream returned HTTP 502"
                    events.append(LogEvent(timestamp=ts, service=service, level="ERROR", message=msg, latency_ms=max(latency, 5)))
                else:
                    events.append(
                        LogEvent(timestamp=ts, service=service, level="INFO", message=rng.choice(messages), latency_ms=max(latency, 5))
                    )
    events.sort(key=lambda e: e.timestamp)
    return events


def write_jsonl(events: list[LogEvent], path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e.model_dump(mode="json"), ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[LogEvent]:
    return [LogEvent.model_validate_json(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
