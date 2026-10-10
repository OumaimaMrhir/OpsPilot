"""Regroupe les anomalies proches dans le temps en incidents, avec sévérité et signatures d'erreurs."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta

from .models import Anomaly, Incident, LogEvent, Metric

GAP = timedelta(minutes=3)


def _severity(peak_error_rate: float, duration_min: float) -> str:
    if peak_error_rate >= 0.25 or duration_min >= 15:
        return "P1"
    if peak_error_rate >= 0.10 or duration_min >= 5:
        return "P2"
    return "P3"


def correlate(anomalies: list[Anomaly], metrics: list[Metric], events: list[LogEvent]) -> list[Incident]:
    by_service: dict[str, list[Anomaly]] = defaultdict(list)
    for a in anomalies:
        by_service[a.service].append(a)

    incidents: list[Incident] = []
    for service, items in sorted(by_service.items()):
        items.sort(key=lambda a: a.minute)
        groups: list[list[Anomaly]] = [[items[0]]]
        for a in items[1:]:
            if a.minute - groups[-1][-1].minute <= GAP:
                groups[-1].append(a)
            else:
                groups.append([a])
        for group in groups:
            start, end = group[0].minute, group[-1].minute + timedelta(minutes=1)
            window = [m for m in metrics if m.service == service and start <= m.minute < end]
            errors = Counter(e.message for e in events if e.service == service and e.level == "ERROR" and start <= e.timestamp < end)
            peak_err = max((m.error_rate for m in window), default=0.0)
            peak_lat = max((m.p95_latency_ms for m in window), default=0.0)
            incidents.append(
                Incident(
                    id=f"INC-{len(incidents) + 1:04d}",
                    service=service,
                    start=start,
                    end=end,
                    severity=_severity(peak_err, (end - start).total_seconds() / 60),  # type: ignore[arg-type]
                    signals=sorted({a.signal for a in group}),
                    peak_error_rate=peak_err,
                    peak_p95_latency_ms=peak_lat,
                    top_errors=errors.most_common(3),
                )
            )
    return incidents
