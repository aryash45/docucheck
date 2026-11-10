# Phase 3 Preparation — Public Evaluation Dataset

## Goal

Add a reproducible evaluation dataset derived only from a publicly available,
licensed benchmark before starting the Phase 3 reviewer and conflict work.

## Source and scope

- Source: official AllenAI SciFact release (`claims_train.jsonl`,
  `claims_dev.jsonl`, and `corpus.jsonl`).
- Committed data: normalized train and dev JSONL plus manifests.
- Excluded: the official unlabeled test split and downloaded raw release files.
- No claims, labels, evidence passages, or citations were authored for this
  project; the importer only maps the public schema into DocuCheck's schema.

## Verified results

- Dev: 300 claims; supported 124, refuted 64, unverifiable 112.
- Heuristic baseline: accuracy 0.7633, macro-F1 0.6314, retrieval recall@k
  0.9753 across 188 evidence-bearing claims, confidently-wrong rate 0.0767.
- Importer unit test covers public label preservation, sentence evidence, and
  character offsets.

## Limits and next action

The baseline is a deterministic heuristic run with gold evidence context; it
is a reproducibility and plumbing baseline, not a production quality estimate.
Next: plan Phase 3 around citation integrity, honest abstention, reviewer
checks, and conflict detection using this holdout as a fixed regression set.
