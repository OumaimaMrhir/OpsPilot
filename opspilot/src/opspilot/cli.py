"""python -m opspilot.cli [--logs fichier.jsonl]"""

from __future__ import annotations

import argparse

from .pipeline import run
from .simulate import generate, read_jsonl, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="OpsPilot : détection, triage et remédiation d'incidents.")
    parser.add_argument("--logs", help="Logs au format JSON Lines (sinon, logs simulés)")
    parser.add_argument("--save-logs", help="Enregistre les logs simulés dans ce fichier")
    args = parser.parse_args()

    events = read_jsonl(args.logs) if args.logs else generate()
    if args.save_logs:
        write_jsonl(events, args.save_logs)
    result = run(events)

    print(f"{len(events)} lignes de logs analysées\n")
    for t in result.timings:
        print(f"[{t.step:<12}] {t.duration_ms:>7.1f} ms  {t.output}")
    for inc, diag, rem in zip(result.incidents, result.diagnoses, result.remediations, strict=True):
        print(f"\n{inc.id} · {inc.service} · {inc.severity} · {inc.start:%H:%M}-{inc.end:%H:%M} · ticket {result.tickets[inc.id]}")
        print(f"  Diagnostic ({diag.mode}, confiance {diag.confidence:.0%}) : {diag.summary}")
        print(f"  Remédiation : {rem.status} – {rem.detail}")


if __name__ == "__main__":
    main()
