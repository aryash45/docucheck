"""Normalize the public SciFact release into DocuCheck's eval JSONL schema.

This script only transforms records from the official SciFact release. It does
not generate claims, labels, or evidence. Empty evidence is mapped to
``unverifiable`` because SciFact provides no annotated evidence for that claim;
the mapping is documented in evals/data/public/README.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LABELS = {"SUPPORT": "supported", "CONTRADICT": "refuted"}


def _load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _abstract_text_and_offsets(sentences: list[str]) -> tuple[str, list[tuple[int, int]]]:
    parts: list[str] = []
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for index, sentence in enumerate(sentences):
        if index:
            parts.append(" ")
            cursor += 1
        start = cursor
        parts.append(sentence)
        cursor += len(sentence)
        offsets.append((start, cursor))
    return "".join(parts), offsets


def normalize_split(raw_dir: Path, split: str) -> tuple[list[dict], dict]:
    claims = _load_jsonl(raw_dir / f"claims_{split}.jsonl")
    corpus = {
        str(item["doc_id"]): item
        for item in _load_jsonl(raw_dir / "corpus.jsonl")
    }
    normalized: list[dict] = []
    excluded: list[dict] = []

    for item in claims:
        evidence = item.get("evidence", {})
        labels = {
            rationale.get("label")
            for rationales in evidence.values()
            for rationale in rationales
        }
        if len(labels) > 1:
            excluded.append({"id": item["id"], "reason": "mixed evidence labels"})
            continue

        gold_evidence: list[dict] = []
        for source_id, rationales in evidence.items():
            source = corpus.get(str(source_id), {})
            sentences = source.get("abstract", [])
            abstract, offsets = _abstract_text_and_offsets(sentences)
            for rationale_index, rationale in enumerate(rationales):
                selected = [i for i in rationale.get("sentences", []) if i < len(sentences)]
                if not selected:
                    continue
                char_start = min(offsets[i][0] for i in selected)
                char_end = max(offsets[i][1] for i in selected)
                gold_evidence.append({
                    "source_id": str(source_id),
                    "source_title": source.get("title", f"SciFact document {source_id}"),
                    "url": "",
                    "quote": " ".join(sentences[i] for i in selected),
                    "location": {
                        "sentence_start": min(selected),
                        "sentence_end": max(selected),
                        "char_start": char_start,
                        "char_end": char_end,
                    },
                    "direction": (
                        "supporting" if rationale["label"] == "SUPPORT" else "contradicting"
                    ),
                })

        if gold_evidence:
            gold_label = LABELS[next(iter(labels))]
        else:
            gold_label = "unverifiable"

        normalized.append({
            "id": f"scifact_{split}_{item['id']}",
            "domain": "scientific_claim_verification",
            "document_id": f"scifact_{split}_{item['id']}",
            "claim": item["claim"],
            "gold_label": gold_label,
            "gold_evidence": gold_evidence,
            "allowed_sources": [str(source_id) for source_id in item.get("cited_doc_ids", [])],
            "notes": (
                f"Imported from AllenAI SciFact {split} split; original claim id={item['id']}. "
                "Empty evidence is mapped to unverifiable."
            ),
        })

    return normalized, {
        "source": "allenai/scifact",
        "split": split,
        "input_claims": len(claims),
        "output_claims": len(normalized),
        "excluded_claims": excluded,
        "label_counts": {
            label: sum(row["gold_label"] == label for row in normalized)
            for label in ("supported", "refuted", "unverifiable")
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import public SciFact data")
    parser.add_argument("--raw-dir", default="evals/data/public/scifact/data")
    parser.add_argument("--split", choices=("train", "dev"), default="dev")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    rows, manifest = normalize_split(Path(args.raw_dir), args.split)
    output = Path(args.output or f"evals/data/public/scifact_{args.split}.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest_path = output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **manifest}, indent=2))


if __name__ == "__main__":
    main()
