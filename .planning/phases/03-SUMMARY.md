# Phase 3 Summary

## Completed

- Added reviewer flags for missing, weak, conflicting, malformed, or poorly
  located evidence.
- Forced `UNVERIFIABLE` when passage-backed verification has no evidence or
  has both supporting and contradicting evidence.
- Exposed `review_flags` and `needs_review` in structured output.
- Added focused tests for conflict, abstention signals, citation integrity, and
  invalid locations.

## Limit

Citation URL resolution remains opt-in and is still bounded by the existing
resolver; this phase validates evidence records but does not add network calls.

## Calibration verification

Explicit absence language now maps to neutral evidence, and all-neutral
retrieved evidence forces abstention. The 2026 GenData heuristic baseline
remained 38.00% accurate, while macro-F1 improved from 25.46% to 30.00%,
confidently-wrong rate fell from 10.00% to 0.00%, and abstention rose from
14.00% to 30.00%.
