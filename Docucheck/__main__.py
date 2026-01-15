"""Main CLI entry point for DocuCheck."""
import argparse, sys, os
from . import core, report

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DocuCheck: Extract and verify claims from documents."
    )
    parser.add_argument("input_file", help="Path to input file (PDF, TXT, etc.).")
    parser.add_argument("-o", "--output", default="report.html", help="Output report path")
    parser.add_argument("-l", "--limit", type=int, default=0, help="Limit claims to check (0=all)")
    parser.add_argument("--force", action="store_true", help="Force re-analysis")
    
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    input_filename = os.path.basename(args.input_file)
    print(f"Processing '{input_filename}'...")

    # Check cache
    file_hash = core.caching.get_file_hash(args.input_file)
    if not args.force and file_hash:
        cached_data = core.caching.get_cache(file_hash)
        if cached_data:
            print("Using cached results.")
            claims = cached_data.get("claims", [])
            issues = cached_data.get("issues", [])
            external_checks = cached_data.get("external_checks", [])
        else:
            claims, issues, external_checks = run_analysis(args)
            if file_hash:
                core.caching.set_cache(file_hash, {
                    "claims": claims, "issues": issues, "external_checks": external_checks
                })
    else:
        if args.force:
            print("Bypassing cache (--force set).")
        claims, issues, external_checks = run_analysis(args)
        if file_hash and not args.force:
            core.caching.set_cache(file_hash, {
                "claims": claims, "issues": issues, "external_checks": external_checks
            })

    print(" Generating report...")
    html_report = report.reporter.generate_report(
        claims, issues, external_checks, input_filename
    )

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html_report)
        print(f" Report saved to {args.output}")
    except IOError as e:
        print(f"Error writing report: {e}", file=sys.stderr)
        sys.exit(1)

def run_analysis(args):
    """Run the full analysis pipeline."""
    print(" Extracting text...")
    try:
        if args.input_file.lower().endswith(".pdf"):
            text = core.extractor.extract_structured_text(args.input_file)
        else:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)

    print(" Extracting claims...")
    claims = core.extractor.extract_claims(text)
    if not claims:
        print("No claims extracted.")
        return [], [], []
    print(f"  -> Extracted {len(claims)} claims.")

    print(" Checking consistency...")
    issues = core.verifier.check_consistency_with_llm(claims)
    
    print(" Performing fact-checks...")
    claims_to_check = claims if args.limit == 0 else claims[:args.limit]
    if args.limit > 0 and len(claims) > args.limit:
        print(f"  -> Checking {args.limit}/{len(claims)} claims")
    else:
        print(f"  -> Checking all {len(claims_to_check)} claims")

    external_checks = []
    for i, c in enumerate(claims_to_check):
        print(f"  -> Checking claim {i+1}/{len(claims_to_check)}...")
        external_checks.append(core.verifier.external_fact_check(c["claim"]))
        
    return claims, issues, external_checks

if __name__ == "__main__":
    main()
