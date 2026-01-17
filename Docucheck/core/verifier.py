"""Fact verification module with refined agentic prompts."""
import asyncio
import json
import os
import sys
from typing import List
import google.generativeai as genai

# Import Pydantic schemas for type-safe data handling
from ..models.schemas import Claim, Contradiction, FactCheckResult

try:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        # Using Gemini 2.0 Flash for high-speed, structured reasoning
        model = genai.GenerativeModel("gemini-3-pro-preview")
    else:
        model = None
except Exception as e:
    print(f"Warning: Could not configure Verifier: {e}", file=sys.stderr)
    model = None

# Enforce JSON mode to match our Pydantic schemas
generation_config = {"response_mime_type": "application/json"}

async def check_consistency_async(claims: List[Claim]) -> List[Contradiction]:
    """
    Refined Internal Consistency Agent.
    Identifies logical clashes and numerical contradictions within the document.
    """
    if not model or len(claims) < 2:
        return []

    # Format claims for the prompt including their section context
    all_claims_text = "\n".join([f"- [{c.section}] {c.claim}" for c in claims])
    
    refined_prompt = f"""
    Act as a Forensic Document Auditor. Your goal is to identify direct logical contradictions within the provided list of claims. 
    
    Instructions:
    1. Compare every claim against all others for numerical conflicts (e.g., conflicting dates/values) or logical opposites.
    2. Focus on factual clashes; ignore minor wording differences.
    3. For every contradiction found, provide a concise explanation.
    
    Output Format:
    Return a JSON list of objects matching this schema: {{"description": "string"}}. 
    If no contradictions exist, return [].

    Claims to Audit:
    {all_claims_text}
    """
    
    try:
        # Asynchronous call for non-blocking execution
        response = await model.generate_content_async(
            refined_prompt, 
            generation_config=generation_config
        )
        raw_data = json.loads(response.text)
        # Hydrate raw JSON into Pydantic objects for type safety
        return [Contradiction(**item) for item in raw_data]
    except Exception as e:
        print(f"Warning: Consistency check failed: {e}", file=sys.stderr)
        return []

async def external_fact_check_async(claim_obj: Claim) -> FactCheckResult:
    """
    Refined External Fact-Checking Agent.
    Verifies a single claim against real-world data using Chain of Thought reasoning.
    """
    if not model:
        return FactCheckResult(
            claim=claim_obj.claim, 
            is_outdated=None, 
            latest_info="Model not configured"
        )

    refined_prompt = f"""
    Act as a Professional Fact-Checker. You will verify this specific claim against real-world data available as of 2026.
    
    Evaluation Criteria:
    - is_outdated = true: New data, laws, or events have rendered the claim obsolete.
    - is_outdated = false: The claim is verified as current and accurate.
    - is_outdated = null: The claim is subjective, a future prediction, or unverifiable.
    
    Reasoning Steps:
    1. Analyze the core factual assertion.
    2. Determine if the claim remains valid based on current global information.
    
    Output Format (Strict JSON):
    {{
      "claim": "{claim_obj.claim}",
      "is_outdated": boolean or null,
      "latest_info": "1-2 sentence explanation of current status.",
      "confidence_score": float (0.0 to 1.0)
    }}
    """
    
    try:
        response = await model.generate_content_async(
            refined_prompt, 
            generation_config=generation_config
        )
        data = json.loads(response.text)
        # Ensure the claim text remains consistent with the input
        data["claim"] = claim_obj.claim
        return FactCheckResult(**data)
    except Exception as e:
        return FactCheckResult(
            claim=claim_obj.claim, 
            is_outdated=None, 
            latest_info=f"Parsing error: {e}"
        )