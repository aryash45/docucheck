# Phase 2 — Passage-Level Parity

## Goal

Return each claim with exact passage evidence, evidence direction, source citation
status, and structured JSON/Markdown output, with metrics proving the behavior.

## Subphases

1. Chunk identity and locations
2. Passage evidence model
3. Deterministic passage retrieval
4. Evidence direction classification
5. Citation resolution
6. Structured output
7. Eval metrics and tests
8. Verification and handoff

## Acceptance

An offline smoke run produces per-claim verdicts with passage quotes, source IDs,
locations, supporting/contradicting/neutral counts, citation status, and measured
retrieval/direction/link metrics.

## Deviations

- Phase 2 uses a dependency-free lexical retriever as the measured baseline; an
  embedding retriever is intentionally deferred until the baseline is stable.
- Citation checks are opt-in because live HTTP calls are not appropriate for the
  default offline suite.
- External head-to-head vendor testing is documented as a manual follow-up rather
  than represented as completed evidence.
