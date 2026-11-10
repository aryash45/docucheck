# DocuCheck Eval Metrics Changelog

Curated record of eval runs for resume/demo. Only measured values after the harness exists.

| Date | Git SHA | Dataset | Provider | Change | Accuracy | F1 Macro | Conf-Wrong | Abstention | Notes |
|------|---------|---------|----------|--------|----------|----------|------------|------------|-------|
| *(run `python -m evals.run_eval` to populate)* | | | | | | | | | |
| 2026-11-08 | c0d9a13 | smoke.jsonl | heuristic | Phase 1 complete: deterministic heuristic baseline with evidence-ID recall | 0.6000 | 0.4398 | 0.0667 | 0.4667 | retrieval_recall=0.6154 (13 claims) |
| 2026-11-10 | 177ec74 | smoke.jsonl | heuristic | Phase 2 passage retrieval and direction baseline | 0.6667 | 0.5761 | 0.0000 | 0.3333 | retrieval_recall=0.0 (13 claims) |
| 2026-11-10 | 177ec74 | smoke.jsonl | heuristic | Phase 2 passage retrieval and direction baseline (fixed source IDs) | 0.6667 | 0.5761 | 0.0000 | 0.3333 | retrieval_recall=0.9231 (13 claims) |
| 2026-11-10 | 177ec74 | smoke.jsonl | heuristic | Phase 2 citation-enabled baseline | 0.6667 | 0.5761 | 0.0000 | 0.3333 | retrieval_recall=0.9231 (13 claims) |
| 2026-11-10 | 5cd13a1 | scifact_dev.jsonl | heuristic | Public SciFact dev holdout baseline | 0.7633 | 0.6314 | 0.0767 | 0.4233 | retrieval_recall=0.9753 (188 claims) |
