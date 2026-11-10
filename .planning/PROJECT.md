# DocuCheck GSD Project

DocuCheck is a Python document fact-checking pipeline. The primary wedge is Mode 3:
extract claims from an uploaded document, verify them against source material, and
return an auditable verdict with exact evidence.

## Current milestone

Phase 2: passage-level parity for claim verification.

## Constraints

- Keep the core deterministic and runnable without API keys.
- Preserve the existing Mode 1 research graph and Phase 1 eval harness.
- Do not add a web shell before evidence quality is represented in the core output.
- Treat retrieval and citation status as measurable output, not marketing claims.
