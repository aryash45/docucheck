"""Normalize GenData's public 2026 scientific-verification benchmark."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

LABELS = {"supported": "supported", "not_supported": "refuted", "no_comparable_evidence": "unverifiable"}

def normalize(path: Path) -> tuple[list[dict], dict]:
    rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        for item in csv.DictReader(handle):
            label = LABELS[item["correct_verdict"]]
            doi = item.get("doi", "").strip()
            quote = item.get("reference_quote_or_reason", "").strip()
            rows.append({
                "id": f"gendata_{item['case_id']}_{item['model'].lower().replace(' ', '_')}",
                "domain": "scientific_claim_verification", "document_id": item["case_id"],
                "claim": item["claim"], "gold_label": label,
                "gold_evidence": [{"source_id": doi or item["deciding_record_id"],
                    "source_title": f"Open-access paper {doi}" if doi else "Public reference record",
                    "url": f"https://doi.org/{doi}" if doi else "", "quote": quote,
                    "direction": "supporting" if label == "supported" else ("contradicting" if label == "refuted" else "neutral")}]
                    if quote else [],
                "allowed_sources": [doi] if doi else [],
                "notes": f"Imported from GenData scientific-verification 2026; original model row={item['model']}."})
    return rows, {"source": "GenData-Research/scientific-verification", "version": "3.0",
        "input_rows": len(rows), "label_counts": {label: sum(r["gold_label"] == label for r in rows)
        for label in ("supported", "refuted", "unverifiable")}}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="evals/data/public/gendata/verification.csv")
    parser.add_argument("--output", default="evals/data/public/gendata_2026.jsonl")
    args = parser.parse_args()
    rows, manifest = normalize(Path(args.input))
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **manifest}, indent=2))

if __name__ == "__main__": main()
