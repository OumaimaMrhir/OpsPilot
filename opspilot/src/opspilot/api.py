"""API FastAPI : uvicorn opspilot.api:app"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from . import __version__
from .models import LogEvent
from .pipeline import PipelineResult, run
from .simulate import generate

app = FastAPI(title="OpsPilot API", version=__version__, description="Détection d'anomalies, triage IA et remédiation d'incidents.")
_last: PipelineResult | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.post("/analyze", response_model=PipelineResult)
def analyze(events: list[LogEvent]) -> PipelineResult:
    global _last
    if not events:
        raise HTTPException(status_code=422, detail="Aucun log fourni.")
    _last = run(events)
    return _last


@app.post("/analyze/demo", response_model=PipelineResult)
def analyze_demo() -> PipelineResult:
    """Analyse un jeu de logs simulé contenant un incident."""
    global _last
    _last = run(generate())
    return _last


@app.get("/incidents")
def incidents() -> list[dict]:
    if _last is None:
        return []
    return [
        {**i.model_dump(mode="json"), "ticket": _last.tickets.get(i.id), "diagnosis": d.model_dump()}
        for i, d in zip(_last.incidents, _last.diagnoses, strict=True)
    ]
