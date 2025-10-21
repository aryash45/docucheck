import argparse
import sys
import os

# Import our new modules
from . import extractor
from . import verifier
from . import reporter
from . import caching

def main():
    
    
    parser = argparse.ArgumentParser(description="DocuCheck: Extract and verify claims from a document.")
    
    parser.add_argument("input_file", help="Path to the input file to analyze (PDF, TXT, etc.).")
    parser.add_argument("-o", "--output", default="report.html", help="Path to save the output HTML report (default: report.html)")
    parser.add_argument("-l", "--limit", type=int, default=0, help="Number of claims to externally fact-check (default: 0, which means ALL). Use --limit 5 to check only 5.")
    parser.add_argument("--force", action="store_true", help="Force re-analysis and bypass any cached results.")
    
    args = parser.parse_args()

    # --- 1. File Validation ---
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found at '{args.input_file}'", file=sys.stderr)
        sys.exit(1)
    
    input_filename = os.path.basename(args.input_file)
    print(f"Processing '{input_filename}'...")

    # --- 2. Caching Check ---
    file_hash = caching.get_file_hash(args.input_file)
    if not args.force and file_hash:
        cached_data = caching.get_cache(file_hash)
        if cached_data:
            print("Info: Found cached results. Using cached data.")
            # Re-generate report from cache
            claims = cached_data.get("claims", [])
            issues = cached_data.get("issues", [])
            external_checks = cached_data.get("external_checks", [])
            # (Fall through to report generation)
        else:
            print("Info: No cache found. Starting new analysis.")
            claims, issues, external_checks = run_analysis(args)
            
            # Save new results to cache
            if file_hash:
                caching.set_cache(file_hash, {
                    "claims": claims,
                    "issues": issues,
                    "external_checks": external_checks
                })
    else:
        if args.force:
            print("Info: --force flag set. Bypassing cache.")
        claims, issues, external_checks = run_analysis(args)
        # Save new results to cache
        if file_hash and not args.force:
            caching.set_cache(file_hash, {
                "claims": claims,
                "issues": issues,
                "external_checks": external_checks
            })


    # --- 6. Report Generation ---
    print("📊 Generating report...")
    report = reporter.generate_report(claims, issues, external_checks, input_filename)

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ Report saved as {args.output}")
    except IOError as e:
        print(f"Error: Could not write report to '{args.output}'. {e}", file=sys.stderr)
        sys.exit(1)

def run_analysis(args):
    """Orchestrates the full analysis pipeline."""
    
    # --- 3. Text Extraction (Now Structural) ---
    print("📖 Extracting structured text...")
    try:
        # We only support PDF for now, but this is where we'd add more
        if args.input_file.lower().endswith(".pdf"):
            text = extractor.extract_structured_text(args.input_file)
        else:
            # Simple text fallback
            with open(args.input_file, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        print(f"Error: Failed to process file. {e}", file=sys.stderr)
        sys.exit(1)

    # --- 4. Claim Extraction ---
    print("🔍 Extracting claims...")
    claims = extractor.extract_claims(text)
    if not claims:
        print("No claims extracted. Exiting.")
        return [], [], []
    print(f"  -> Extracted {len(claims)} claims.")

    # --- 5. Analysis ---
    print("🔎 Checking internal consistency...")
    issues = verifier.check_consistency_with_llm(claims)
    
    print("🌍 Performing external verification...")
    claims_to_check = claims if args.limit == 0 else claims[:args.limit]
    total_to_check = len(claims_to_check)
    
    if args.limit > 0 and len(claims) > args.limit:
        print(f"  -> Checking first {args.limit} of {len(claims)} claims. (Use --limit 0 to check all)")
    else:
        print(f"  -> Checking all {total_to_check} claims.")

    external_checks = []
    for i, c in enumerate(claims_to_check):
        print(f"  -> Checking claim {i+1} of {total_to_check}...")
        external_checks.append(verifier.external_fact_check(c["claim"]))
        
    return claims, issues, external_checks

if __name__ == "__main__":
    main()