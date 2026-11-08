# DocuCheck Eval Harness

Measures verification quality on a fixed claim set so every change is accountable.

## Quick start

```bash
# Run the heuristic baseline (no API keys needed)
python -m evals.run_eval --dataset evals/data/smoke.jsonl

# Run with LLM enabled (requires GEMINI_API_KEY)
python -m evals.run_eval --dataset evals/data/smoke.jsonl --provider gemini
```

Results are written to `outputs/evals/<timestamp>/`.

## Dataset format (JSONL)

One claim per line:

```json
{
  "id": "claim_001",
  "domain": "machine_learning",
  "document_id": "doc_001",
  "claim": "The intervention reduced mortality by 20%.",
  "gold_label": "supported",
  "gold_evidence": [
    {
      "source_id": "paper_001",
      "source_title": "...",
      "url": "...",
      "quote": "Exact passage.",
      "location": {"page": 3, "char_start": 1200, "char_end": 1320},
      "direction": "supporting"
    }
  ],
  "allowed_sources": ["paper_001"],
  "notes": "Why this label was chosen."
}
```

Labels: `supported`, `refuted`, `unverifiable`.

## Metrics

| Metric | Definition |
|--------|-----------|
| Accuracy | Correct verdicts / total |
| Per-class P/R/F1 | For supported, refuted, unverifiable |
| Confidently-wrong rate | Wrong + confidence > threshold |
| Abstention rate | % predicted unverifiable |
| Retrieval recall@k | Gold evidence IDs present in the predicted evidence IDs (when labels exist) |

## Output structure

```
outputs/evals/<timestamp>/
  config.json      — git SHA, dataset, provider, thresholds
  predictions.jsonl — per-claim prediction with confidence
  metrics.json     — all computed metrics
```

`outputs/evals/index.jsonl` — one summary row per run.
`evals/results/CHANGELOG.md` — curated metrics changelog for resume/demo.

The current Phase 1 runner uses gold evidence passages as deterministic paper
context so the verifier can be evaluated without network calls. Its retrieval
recall is therefore a context/evidence-ID plumbing check, not a claim about a
production retriever. Phase 2 should replace that fixture with real retrieval.
