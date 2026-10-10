from datetime import datetime

from opspilot.agent import diagnose, load_runbooks, remediate
from opspilot.models import Incident
from opspilot.servicenow import MockServiceNow, incident_payload


def make_incident(errors):
    return Incident(
        id="INC-0001",
        service="payment-api",
        start=datetime(2026, 10, 10, 9, 30),
        end=datetime(2026, 10, 10, 9, 42),
        severity="P1",
        signals=["error_rate"],
        peak_error_rate=0.4,
        peak_p95_latency_ms=1200,
        top_errors=errors,
    )


def test_known_signature_is_auto_remediated():
    diag = diagnose(make_incident([("DB connection pool exhausted (max=50)", 120)]), load_runbooks())
    assert diag.runbook_id == "RB-001"
    assert diag.automated
    result = remediate(diag)
    assert result.status == "exécutée (simulation)"
    assert "Invoke-Remediation.ps1" in result.detail


def test_non_whitelisted_action_waits_for_human():
    diag = diagnose(make_incident([("Upstream returned HTTP 502", 80)]), load_runbooks())
    assert diag.runbook_id == "RB-002"
    assert not diag.automated
    assert remediate(diag).status == "en attente de validation"


def test_unknown_signature_requires_investigation():
    diag = diagnose(make_incident([("Something strange happened", 10)]), load_runbooks())
    assert diag.runbook_id is None
    assert remediate(diag).status == "aucune action"


def test_servicenow_payload_and_mock():
    incident = make_incident([("DB connection pool exhausted (max=50)", 120)])
    payload = incident_payload(incident, diagnose(incident, load_runbooks()))
    assert payload["urgency"] == "1"
    assert payload["correlation_id"] == "INC-0001"
    snow = MockServiceNow()
    assert snow.create_incident(payload) == "INC1000010"
