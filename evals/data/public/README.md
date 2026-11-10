# Public Evaluation Data

DocuCheck uses the public [AllenAI SciFact dataset](https://github.com/allenai/scifact)
for a larger scientific claim-verification evaluation set.

## Provenance and licensing

- Source repository: `allenai/scifact`
- Official release: <https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz>
- Claims and evidence annotations: CC BY 4.0
- Abstract corpus: ODC-By 1.0, as stated by the dataset authors
- Dataset paper: [Fact or Fiction: Verifying Scientific Claims](https://arxiv.org/abs/2004.14974)

The normalized files are derived from the official release without adding or
rewriting claims. `evals/import_scifact.py` is the reproducible transformation.

## Splits

- `scifact_train.jsonl`: development data; do not use for final quality estimates.
- `scifact_dev.jsonl`: public labeled holdout used for the first larger estimate.
- `*.manifest.json`: input/output counts, label counts, and excluded records.

SciFact's raw claim records contain evidence annotations or an empty evidence map.
For DocuCheck's three-label schema, an empty evidence map is mapped to
`unverifiable`; this is a documented schema mapping, not a new human label.

The official unlabeled test split is intentionally not imported as an evaluation
set because it cannot produce public gold metrics.

## Rebuild

```bash
python -m evals.import_scifact --split train
python -m evals.import_scifact --split dev
```
