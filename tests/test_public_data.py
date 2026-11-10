from pathlib import Path

from evals.import_scifact import normalize_split


def test_normalize_scifact_preserves_public_labels_and_evidence(tmp_path: Path):
    raw_dir = tmp_path / "scifact"
    raw_dir.mkdir()
    (raw_dir / "corpus.jsonl").write_text(
        '{"doc_id": 7, "title": "Public paper", "abstract": ["First sentence.", "Second sentence."]}\n',
        encoding="utf-8",
    )
    (raw_dir / "claims_dev.jsonl").write_text(
        '{"id": 1, "claim": "Supported claim.", "evidence": {"7": [{"label": "SUPPORT", "sentences": [1]}]}, "cited_doc_ids": [7]}\n'
        '{"id": 2, "claim": "Unverifiable claim.", "evidence": {}, "cited_doc_ids": []}\n',
        encoding="utf-8",
    )

    rows, manifest = normalize_split(raw_dir, "dev")

    assert [row["gold_label"] for row in rows] == ["supported", "unverifiable"]
    assert rows[0]["gold_evidence"][0]["quote"] == "Second sentence."
    assert rows[0]["gold_evidence"][0]["location"] == {
        "sentence_start": 1,
        "sentence_end": 1,
        "char_start": len("First sentence. "),
        "char_end": len("First sentence. Second sentence."),
    }
    assert manifest["input_claims"] == manifest["output_claims"] == 2
    assert manifest["label_counts"] == {"supported": 1, "refuted": 0, "unverifiable": 1}
