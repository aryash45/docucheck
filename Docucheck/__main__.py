"""Main CLI entry point for DocuCheck - Asynchronous Orchestrator."""
import argparse
import sys
import os
import asyncio
from . import core, report


from .models.schemas import Claim

async def run_analysis_async(args):
    """
    Production-grade asynchronous analysis pipeline.
    Orchestrates extraction and parallel verification tasks.
    """
    print(" 📖 Extracting text...")
    try:
        if args.input_file.lower().endswith(".pdf"):
            text = core.extractor.extract_structured_text(args.input_file)
        else:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        return None, None, None

    print(" 🔎 Extracting claims...")
    # Get raw claims and hydrate them into Pydantic objects
    raw_claims = core.extractor.extract_claims(text)
    if not raw_claims:
        print("No claims extracted.")
        return [], [], []
    
    claims = [Claim(**c) for c in raw_claims]
    print(f"  -> Extracted {len(claims)} claims.")

    # ---------------------------------------------------------
    # PARALLEL EXECUTION BLOCK
    # ---------------------------------------------------------
    print(f" 🚀 Performing parallel verification on {len(claims)} claims...")
    
    # Define the limit for external checks
    claims_to_check = claims if args.limit == 0 else claims[:args.limit]
    
    # Prepare all asynchronous tasks
    consistency_task = core.verifier.check_consistency_async(claims)
    fact_check_tasks = [
        core.verifier.external_fact_check_async(c) for c in claims_to_check
    ]
    
    # Execute everything concurrently using asyncio.gather
    # results[0] will be the consistency issues, the rest are fact-checks
    all_results = await asyncio.gather(consistency_task, *fact_check_tasks)
    
    issues = all_results[0]
    external_checks = all_results[1:]
        
    return claims, issues, external_checks

def main():
    """Entry point that manages the event loop and report generation."""
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

    # Check cache logic
    file_hash = core.caching.get_file_hash(args.input_file)
    cached_data = None
    if not args.force and file_hash:
        cached_data = core.caching.get_cache(file_hash)

    if cached_data:
        print(" Using cached results.")
        claims = [Claim(**c) for c in cached_data.get("claims", [])]
        issues = cached_data.get("issues", [])
        external_checks = cached_data.get("external_checks", [])
    else:
        if args.force:
            print(" Bypassing cache (--force set).")
        
        # Run the asynchronous pipeline
        claims, issues, external_checks = asyncio.run(run_analysis_async(args))
        
        if claims is None:
            sys.exit(1)

        if file_hash and not args.force:
            # Convert objects back to dicts for JSON caching
            core.caching.set_cache(file_hash, {
                "claims": [c.dict() for c in claims], 
                "issues": [i.description for i in issues], 
                "external_checks": [e.dict() for e in external_checks]
            })

    print(" Generating report...")
    # Convert Pydantic models back to dicts for the legacy reporter
    report_claims = [c.dict() for c in claims]
    report_issues = [i.description if hasattr(i, 'description') else i for i in issues]
    report_checks = [e.dict() for e in external_checks]

    html_report = report.reporter.generate_report(
        report_claims, report_issues, report_checks, input_filename
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_report)
    print(f" ✨ Analysis complete. Report saved to {args.output}")

if __name__ == "__main__":
    main()