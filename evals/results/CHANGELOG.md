# DocuCheck Eval Metrics Changelog

Curated record of eval runs for resume/demo. Only measured values after the harness exists.

| Date | Git SHA | Dataset | Provider | Change | Accuracy | F1 Macro | Conf-Wrong | Abstention | Notes |
|------|---------|---------|----------|--------|----------|----------|------------|------------|-------|
| *(run `python -m evals.run_eval` to populate)* | | | | | | | | | |
| 2026-11-08 | c0d9a13 | smoke.jsonl | heuristic | Phase 1 complete: deterministic heuristic baseline with evidence-ID recall | 0.6000 | 0.4398 | 0.0667 | 0.4667 | retrieval_recall=0.6154 (13 claims) |
