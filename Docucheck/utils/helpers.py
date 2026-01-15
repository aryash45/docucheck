"""Utility functions for JSON parsing from LLM responses."""
import re, json, sys

def parse__llm__json(raw_text):
    """Extract and parse JSON from LLM response text."""
    # Try fenced code block
    fenced = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", raw_text, re.S | re.I)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except: pass
    
    # Try direct JSON parsing
    try:
        return json.loads(raw_text)
    except: pass
    
    # Try inline JSON extraction
    m = re.search(r"(\[.*\]|\{.*\})", raw_text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except: pass
    
    return None
