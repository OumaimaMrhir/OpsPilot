from datetime import datetime

from opspilot.correlate import correlate
from opspilot.detection import aggregate, detect
from opspilot.simulate import generate


def test_aggregation_computes_error_rate_and_p95(events):
    metrics = aggregate(events)
    assert len({m.service for m in metrics}) == 3
    assert all(0 <= m.error_rate <= 1 for m in metrics)


def test_anomalies_only_during_injected_incident(events):
    anomalies = detect(aggregate(events))
    assert anomalies
    assert {a.service for a in anomalies} == {"payment-api"}
    assert all(datetime(2026, 10, 10, 9, 30) <= a.minute < datetime(2026, 10, 10, 9, 42) for a in anomalies)


def test_no_false_positive_without_incident():
    calm = generate(incident_duration=0, seed=7)
    assert detect(aggregate(calm)) == []


def test_correlation_builds_one_p1_incident(events):
    metrics = aggregate(events)
    incidents = correlate(detect(metrics), metrics, events)
    assert len(incidents) == 1
    incident = incidents[0]
    assert incident.severity == "P1"
    assert set(incident.signals) == {"error_rate", "p95_latency_ms"}
    assert "pool" in incident.top_errors[0][0]
