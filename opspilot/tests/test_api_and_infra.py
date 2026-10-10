from pathlib import Path

import hcl2
from fastapi.testclient import TestClient

from opspilot.api import app

ROOT = Path(__file__).resolve().parents[1]


def test_api_demo_and_incidents():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    body = client.post("/analyze/demo").json()
    assert len(body["incidents"]) == 1
    incidents = client.get("/incidents").json()
    assert incidents[0]["ticket"].startswith("INC")


def test_terraform_files_are_valid_hcl_and_define_monitoring():
    resources = {}
    for tf in (ROOT / "infra/terraform").glob("*.tf"):
        for block in hcl2.load(tf.open()).get("resource", []):
            resources.update({k.strip('"'): v for k, v in block.items()})
    for expected in ("azurerm_log_analytics_workspace", "azurerm_container_app", "azurerm_monitor_scheduled_query_rules_alert_v2"):
        assert expected in resources


def test_kql_queries_exist():
    queries = sorted(p.name for p in (ROOT / "kql").glob("*.kql"))
    assert len(queries) == 4
    assert "series_decompose_anomalies" in (ROOT / "kql/02_detection_anomalies.kql").read_text(encoding="utf-8")
