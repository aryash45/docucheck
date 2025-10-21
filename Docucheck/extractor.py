import fitz  # PyMuPDF
import google.generativeai as genai
import sys
import os
import re
from .utils import parse__llm__json

# Configure the model (shared within the module)
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found. External checks and smart extraction will be skipped.", file=sys.stderr)
        model = None
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
except Exception as e:
    print(f"Warning: Could not configure Generative AI. {e}", file=sys.stderr)
    model = None

def extract_structured_text(pdf_path):
    """
    Extracts text from a PDF, analyzing font size to identify headings.
    Returns a single string with markdown-like tags (e.g., [H1], [P]).
    """
    doc = fitz.open(pdf_path)
    structured_content = ""
    
    # 1. First pass: Find the most common font size (body text)
    font_counts = {}
    for page in doc:
        # ---- FIX: Removed the invalid 'flags' argument ----
        blocks = page.get_text("dict")["blocks"]
        # ----------------------------------------------------
        for block in blocks:
            if block["type"] == 0: # text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        size = round(span["size"])
                        font_counts[size] = font_counts.get(size, 0) + 1
    
    if not font_counts:
        doc.close()
        return "" # Empty doc
        
    body_size = max(font_counts, key=font_counts.get)
    
    # 2. Second pass: Extract text and tag it
    for page_num, page in enumerate(doc, start=1):
        structured_content += f"\n\n--- Page {page_num} ---\n\n"
        blocks = page.get_text("blocks", sort=True)
        for block_idx, block in enumerate(blocks):
            if block[6] == 0: # text block
                text = block[4].strip()
                if not text:
                    continue
                
                try:
                    # Get the block's first span's size
                    # ---- FIX: Removed the invalid 'flags' argument ----
                    span = page.get_text("dict")["blocks"][block_idx]["lines"][0]["spans"][0]
                    # ----------------------------------------------------
                    avg_size = round(span["size"])
                except Exception:
                    avg_size = body_size

                if avg_size > body_size + 2:
                    tag = "H1" # Major heading
                elif avg_size > body_size:
                    tag = "H2" # Sub-heading
                else:
                    tag = "P"  # Paragraph
                    
                structured_content += f"[{tag}] {text}\n"
                
    doc.close()
    return structured_content

def extract_claims(structured_text):
    """
    Extracts factual claims from the structured text using an LLM.
    The new prompt uses the structural tags [H1], [H2], [P].
    """
    if not model:
        print("Warning: Model not configured. Falling back to simple heuristic.", file=sys.stderr)
        # Fallback heuristic
        claims = []
        for line in structured_text.splitlines():
            if re.search(r"\d", line) and line.startswith("[P]"):
                claims.append({"claim": line[4:].strip(), "section": "Unknown"})
        return claims

    prompt = f"""
    You are an academic analyst. Extract important factual claims from this document text.
    The text is structured with tags: [H1]=Main Heading, [H2]=Sub-heading, [P]=Paragraph.
    Use the headings to determine the "section" (e.g., "Abstract", "Methods", "Results").
    
    Return ONLY a valid JSON list in this format:
    [
      {{"claim": "...", "section": "..."}}
    ]

    Document Text:
    {structured_text[:25000]}
    """
    
    try:
        resp = model.generate_content(prompt)
        raw = getattr(resp, 'text', str(resp))
        parsed_json = parse__llm__json(raw)
        
        if parsed_json and isinstance(parsed_json, list):
            return parsed_json
        else:
            print("Warning: Claim extraction returned invalid data, returning empty list.", file=sys.stderr)
            return []

    except Exception as e:
        print(f"Error: Model call failed for claim extraction. {e}", file=sys.stderr)
        return []