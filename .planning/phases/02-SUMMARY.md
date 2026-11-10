# Phase 2 Summary

## Status

Core implementation complete on 2026-11-10. External competitor comparison is
explicitly not claimed as complete; see `evals/comparisons/phase2.md`.

## Delivered

- Document-aware chunks with stable document/chunk IDs, character offsets, and
  optional page ranges.
- `PassageEvidence` records with quote, source, URL, score, direction, and location.
- Deterministic lexical top-k passage retrieval.
- Supporting/contradicting/neutral direction classification.
- Opt-in bounded citation URL resolution with status records.
- Structured JSON and Markdown evidence output.
- Retrieval recall, evidence-direction accuracy, and citation link-resolution metrics.
- Offline regression tests and an eval comparison note.

## Verification evidence

- Offline Phase 2 suite: 58 passed, 5 warnings.
- Citation-enabled smoke eval: 15 claims.
- Accuracy: 0.6667.
- Macro-F1: 0.5761.
- Retrieval recall: 0.9231 across 13 evidence-bearing claims.
- Evidence-direction accuracy: 0.6667 across 12 matched evidence items.
- Citation link-resolution rate: 0.75 across 12 checked URLs.
- Confidently-wrong rate: 0.0.

## Deviations and limits

- Retrieval is lexical and deterministic; embeddings are deferred until this
  baseline is stable.
- Citation checks are opt-in and network-dependent.
- Vendor head-to-head comparison still needs a manual session with captured,
  comparable outputs.
