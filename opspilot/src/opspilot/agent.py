"""Agent de triage : rapproche l'incident d'un runbook, rédige un diagnostic et propose une remédiation.

Garde-fou : seules les actions en liste blanche (`automatable: true`) sont exécutées automatiquement, et
uniquement pour les incidents dont la confiance est suffisante. Tout le reste attend une validation humaine.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import yaml

from .models import Diagnosis, Incident, RemediationResult

ROOT = Path(__file__).resolve().parents[2]
AUTO_CONFIDENCE = 0.6


def load_runbooks(path: str | Path | None = None) -> list[dict]:
    path = path or os.getenv("OPSPILOT_RUNBOOKS") or ROOT / "runbooks" / "runbooks.yaml"
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["runbooks"]


def _match_runbook(incident: Incident, runbooks: list[dict]) -> tuple[dict | None, float]:
    total = sum(count for _, count in incident.top_errors) or 1
    best, best_share = None, 0.0
    for rb in runbooks:
        hits = sum(count for msg, count in incident.top_errors if any(p in msg.lower() for p in rb["patterns"]))
        if hits / total > best_share:
            best, best_share = rb, hits / total
    return best, round(best_share, 2)


def _llm_summary(incident: Incident, runbook: dict | None) -> str | None:
    """Résumé rédigé par un LLM (optionnel). En cas d'absence de clé ou d'erreur, on reste sur le résumé déterministe."""
    key = os.getenv("OPENAI_API_KEY")
    if os.getenv("LLM_PROVIDER") != "openai" or not key:
        return None
    prompt = (
        f"Incident {incident.id} sur {incident.service} ({incident.severity}), de {incident.start:%H:%M} à {incident.end:%H:%M}. "
        f"Taux d'erreur max {incident.peak_error_rate:.0%}, latence p95 max {incident.peak_p95_latency_ms:.0f} ms. "
        f"Erreurs principales : {incident.top_errors}. Runbook : {runbook['title'] if runbook else 'aucun'}. "
        "Rédige en 3 phrases un résumé pour l'équipe d'astreinte : impact, cause probable, action recommandée."
    )
    try:
        r = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "messages": [{"role": "user", "content": prompt}], "temperature": 0},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def diagnose(incident: Incident, runbooks: list[dict]) -> Diagnosis:
    runbook, confidence = _match_runbook(incident, runbooks)
    impact = (
        f"{incident.service} dégradé de {incident.start:%H:%M} à {incident.end:%H:%M} ({incident.severity}) : "
        f"jusqu'à {incident.peak_error_rate:.0%} d'erreurs et {incident.peak_p95_latency_ms:.0f} ms de latence p95."
    )
    if runbook is None or confidence == 0:
        summary = impact + " Aucune signature connue : analyse manuelle requise."
        return Diagnosis(
            incident_id=incident.id,
            runbook_id=None,
            probable_cause="Inconnue",
            recommended_action="investigate",
            automated=False,
            confidence=0.0,
            summary=summary,
        )
    summary = f"{impact} Cause probable : {runbook['probable_cause']} Action : {runbook['steps'][0]}"
    llm_text = _llm_summary(incident, runbook)
    return Diagnosis(
        incident_id=incident.id,
        runbook_id=runbook["id"],
        probable_cause=runbook["probable_cause"],
        recommended_action=runbook["action"],
        automated=bool(runbook["automatable"]) and confidence >= AUTO_CONFIDENCE,
        confidence=confidence,
        summary=llm_text or summary,
        mode="llm:openai" if llm_text else "règles",
    )


def remediate(diagnosis: Diagnosis, dry_run: bool = True) -> RemediationResult:
    """Exécute (ici en simulation) l'action si elle est autorisée, sinon la met en attente de validation."""
    if diagnosis.recommended_action == "investigate":
        return RemediationResult(
            incident_id=diagnosis.incident_id, action="investigate", status="aucune action", detail="Analyse manuelle."
        )
    if not diagnosis.automated:
        return RemediationResult(
            incident_id=diagnosis.incident_id,
            action=diagnosis.recommended_action,
            status="en attente de validation",
            detail="Action hors liste blanche ou confiance insuffisante : validation humaine requise.",
        )
    command = f"scripts/Invoke-Remediation.ps1 -Action {diagnosis.recommended_action} -IncidentId {diagnosis.incident_id}"
    return RemediationResult(
        incident_id=diagnosis.incident_id,
        action=diagnosis.recommended_action,
        status="exécutée (simulation)",
        detail=f"{'[dry-run] ' if dry_run else ''}{command}",
    )
