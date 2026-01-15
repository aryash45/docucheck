"""Fact verification module."""
import google.generativeai as genai, os, re, sys
from ..utils import parse__llm__json

try:
    if os.getenv("GEMINI_API_KEY"):
        model = genai.GenerativeModel("gemini-2.5-flash")
    else:
        model = None
except Exception as e:
    print(f"Warning: Could not configure Verifier: {e}", file=sys.stderr)
    model = None

def check_consistency_with_llm(claims_list):
    """Find contradictions in claims."""
    if not model or len(claims_list) < 2:
        return []
    
    print("  -> Checking internal contradictions...")
    all_claims = "\n".join([f"- {c['claim']}" for c in claims_list])
    prompt = f"""Find direct contradictions between these claims.
    Return only a JSON list of strings describing contradictions, or [].
    
    {all_claims}"""
    
    try:
        resp = model.generate_content(prompt)
        raw = getattr(resp, "text", str(resp))
        parsed = parse__llm__json(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        print(f"Warning: Consistency check failed: {e}", file=sys.stderr)
        return []

def external_fact_check(claim):
    """Fact-check a single claim."""
    prompt = f"""Check this claim against your knowledge.
    Return ONLY: {{"claim": "...", "is_outdated": true/false/null, "latest_info": "..."}}
    
    Claim: {claim}"""
    
    if not model:
        return {"claim": claim, "is_outdated": None, "latest_info": "Model not configured"}
    
    try:
        resp = model.generate_content(prompt)
        raw = getattr(resp, "text", str(resp))
        parsed = parse__llm__json(raw)
        if isinstance(parsed, dict):
            if "claim" not in parsed:
                parsed["claim"] = claim
            return parsed
        return {"claim": claim, "is_outdated": None, "latest_info": "Parsing failed"}
    except Exception as e:
        return {"claim": claim, "is_outdated": None, "latest_info": f"Error: {e}"}
