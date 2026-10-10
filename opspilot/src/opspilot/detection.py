"""Agrégation des logs en métriques par minute et détection d'anomalies (z-score sur une fenêtre glissante).

Équivalent local des requêtes KQL du dossier `kql/` (summarize par bin de 1 minute, series_decompose_anomalies).
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import datetime

from .models import Anomaly, LogEvent, Metric

WINDOW = 30  # minutes de référence
Z_THRESHOLD = 4.0
MIN_ABS_CHANGE = {"error_rate": 0.05, "p95_latency_ms": 150.0}  # évite les fausses alertes sur des variations minimes


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]


def aggregate(events: list[LogEvent]) -> list[Metric]:
    buckets: dict[tuple[str, datetime], list[LogEvent]] = defaultdict(list)
    for e in events:
        buckets[(e.service, e.timestamp.replace(second=0, microsecond=0))].append(e)
    metrics = []
    for (service, minute), items in sorted(buckets.items()):
        errors = sum(e.level == "ERROR" for e in items)
        metrics.append(
            Metric(
                service=service,
                minute=minute,
                requests=len(items),
                errors=errors,
                error_rate=round(errors / len(items), 4),
                p95_latency_ms=round(_p95([e.latency_ms for e in items]), 1),
            )
        )
    return metrics


def detect(metrics: list[Metric]) -> list[Anomaly]:
    by_service: dict[str, list[Metric]] = defaultdict(list)
    for m in metrics:
        by_service[m.service].append(m)

    anomalies: list[Anomaly] = []
    for service, series in by_service.items():
        series.sort(key=lambda m: m.minute)
        for signal in ("error_rate", "p95_latency_ms"):
            history: list[float] = []
            for m in series:
                value = getattr(m, signal)
                if len(history) >= 10:
                    baseline = statistics.fmean(history[-WINDOW:])
                    spread = statistics.pstdev(history[-WINDOW:]) or 1e-6
                    z = (value - baseline) / spread
                    if z >= Z_THRESHOLD and value - baseline >= MIN_ABS_CHANGE[signal]:
                        anomalies.append(
                            Anomaly(
                                service=service,
                                minute=m.minute,
                                signal=signal,
                                value=value,
                                baseline=round(baseline, 3),
                                zscore=round(z, 1),
                            )
                        )
                        continue  # une minute anormale n'entre pas dans la référence
                history.append(value)
    return sorted(anomalies, key=lambda a: (a.service, a.minute))
