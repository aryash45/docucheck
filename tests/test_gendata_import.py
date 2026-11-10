from pathlib import Path
from evals.import_gendata import normalize

def test_normalize_gendata_maps_public_verdicts(tmp_path: Path):
    source = tmp_path / "verification.csv"
    source.write_text("case_id,claim,model,correct_verdict,doi,reference_quote_or_reason\n"
        "c1,Claim one,Model A,supported,10.1/x,Exact quote\n"
        "c2,Claim two,Model A,not_supported,10.1/y,Contradicting quote\n"
        "c3,Claim three,Model A,no_comparable_evidence,,,\n", encoding="utf-8")
    rows, manifest = normalize(source)
    assert [row["gold_label"] for row in rows] == ["supported", "refuted", "unverifiable"]
    assert rows[0]["gold_evidence"][0]["url"] == "https://doi.org/10.1/x"
    assert manifest["input_rows"] == 3
