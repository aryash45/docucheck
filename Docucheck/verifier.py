import google.generativeai as genai
import os
import re
import sys
from .utils import parse__llm__json

# Model must be configured in extractor.py, we just need to access it
try:
    if os.getenv("GEMINI_API_KEY"):
        model = genai.GenerativeModel("gemini-2.5-flash")
    else:
        model = None
except Exception as e:
    print(f"Warning: Could not configure Verifier model. {e}", file=sys.stderr)
    model = None

def check_consistency_with_llm(claims_list):
    """Uses the LLM to find logical contradictions in a list of claims."""
    if not model or len(claims_list) < 2:
        return []

    print("  -> Asking LLM to find internal contradictions...")
    all_claims_text = "\n".join([f"- {c['claim']}" for c in claims_list])
    
    prompt = f"""
    You are an analyst. Below is a list of all factual claims extracted from a single document.
    Your job is to read all of them and identify any claims that *directly contradict* each other.
    Only find direct, unambiguous contradictions.
    
    Return a JSON list of strings, where each string describes a contradiction.
    If you find no contradictions, return an empty list [].

    Example output:
    ["Found a contradiction: Claim 'X' states 50 participants, but Claim 'Y' states 100."]
    
    Claims:
    {all_claims_text}
    """
    
    try:
        resp = model.generate_content(prompt)
        raw = getattr(resp, 'text', str(resp))
        parsed_json = parse__llm__json(raw)
        
        if parsed_json and isinstance(parsed_json, list):
            return parsed_json
        return []
        
    except Exception as e:
        print(f"Warning: Could not check consistency with LLM. {e}", file=sys.stderr)
        return [f"Error during LLM consistency check: {e}"]

def external_fact_check(claim):
    """Uses the LLM to perform an external fact-check on a single claim."""
    prompt = f"""
    You are a fact-checking assistant. Check this factual claim against your knowledge.
    Return ONLY a valid JSON object:
    {{
      "claim": "...",
      "is_outdated": true/false/null,
      "latest_info": "..."
    }}
    - "is_outdated" should be true if obsolete, false if correct, and null if unverifiable.
    - "latest_info" should provide correct info if outdated, or supporting context if valid.

    Claim: {claim}
    """
    if not model:
        return {"claim": claim, "is_outdated": None, "latest_info": "Model not configured - check skipped"}

    try:
        resp = model.generate_content(prompt)
        raw = getattr(resp, 'text', str(resp))
        parsed_json = parse__llm__json(raw)
        
        if parsed_json and isinstance(parsed_json, dict):
            # Ensure the original claim is present
            if 'claim' not in parsed_json:
                parsed_json['claim'] = claim
            return parsed_json
        
        print(f"Warning: Could not parse JSON from fact-check.", file=sys.stderr)
        return {"claim": claim, "is_outdated": None, "latest_info": "Parsing failed."}

    except Exception as e:
        return {"claim": claim, "is_outdated": None, "latest_info": f"Error during external check: {e}"}