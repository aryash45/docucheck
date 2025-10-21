import re
import json
import sys
def parse__llm__json(raw_text):
    fenced = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", raw_text, re.S | re.I)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from fenced code block: {e}", file=sys.stderr)
            pass
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        pass
    m = re.search(r"(\[.*\]|\{.*\})", raw_text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from inline match: {e}", file=sys.stderr)
            pass
        print(f"Failed to parse JSON from text: {raw_text[:200]}...", file=sys.stderr)
        return None