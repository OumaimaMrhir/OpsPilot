"""Tableau de bord : streamlit run src/opspilot/dashboard.py"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from opspilot.pipeline import run
from opspilot.simulate import generate

st.set_page_config(page_title="OpsPilot", layout="wide")
st.title("OpsPilot")
st.caption("Supervision AIOps : détection d'anomalies, incidents, triage IA et remédiation.")


@st.cache_data
def load():
    return run(generate())


result = load()
metrics = pd.DataFrame([m.model_dump() for m in result.metrics])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Services supervisés", metrics["service"].nunique())
c2.metric("Anomalies détectées", len(result.anomalies))
c3.metric("Incidents", len(result.incidents))
c4.metric("Remédiations automatiques", sum(r.status.startswith("exécutée") for r in result.remediations))

left, right = st.columns(2)
with left:
    st.subheader("Taux d'erreur par minute")
    st.line_chart(metrics.pivot(index="minute", columns="service", values="error_rate"))
with right:
    st.subheader("Latence p95 (ms)")
    st.line_chart(metrics.pivot(index="minute", columns="service", values="p95_latency_ms"))

st.subheader("Incidents et triage")
for inc, diag, rem in zip(result.incidents, result.diagnoses, result.remediations, strict=True):
    with st.container(border=True):
        st.markdown(
            f"**{inc.id} · {inc.service} · {inc.severity}** – {inc.start:%H:%M} → {inc.end:%H:%M} · "
            f"ticket ServiceNow **{result.tickets[inc.id]}**"
        )
        st.write(diag.summary)
        st.write(f"Runbook **{diag.runbook_id}** · confiance {diag.confidence:.0%} · remédiation : **{rem.status}**")
        st.code(rem.detail, language="powershell")

st.subheader("Étapes du pipeline")
st.dataframe(pd.DataFrame([t.model_dump() for t in result.timings]), hide_index=True, width="stretch")
