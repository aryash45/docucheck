# Phase 2 Comparison Note

## Completed internal comparison

The Phase 2 path is compared against the Phase 1 heuristic baseline through the
same 15-claim smoke dataset. The Phase 2 runner now records passage evidence IDs,
direction labels, and optional citation status; its smoke output is the measured
baseline for subsequent retrieval changes.

## External comparison status

No external competitor was run from this repository. The plan names Elicit,
Undermind, OpenAI Deep Research, and Gemini Deep Research, but none has a local
adapter or export fixture here. This is intentionally left as a manual follow-up;
the project does not claim vendor parity without observing the same claim set and
capturing comparable outputs.

## Comparison checklist

- claim-by-claim verdicts
- exact passage quote and location
- supporting/contradicting/neutral direction counts
- resolvable citation URL and status
- exportable structured evidence
- abstention behavior on unverifiable claims
