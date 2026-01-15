"""Text extraction module for PDFs and documents."""
import fitz, google.generativeai as genai, sys, os, re
from ..utils import parse__llm__json

try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found.", file=sys.stderr)
        model = None
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
except Exception as e:
    print(f"Warning: Could not configure AI: {e}", file=sys.stderr)
    model = None

def extract_structured_text(pdf_path):
    """Extract text from PDF with structural tags."""
    doc = fitz.open(pdf_path)
    structured_content = ""
    
    # Find body text font size
    font_counts = {}
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        size = round(span["size"])
                        font_counts[size] = font_counts.get(size, 0) + 1
    
    if not font_counts:
        doc.close()
        return ""
    
    body_size = max(font_counts, key=font_counts.get)
    
    # Extract and tag text
    for page_num, page in enumerate(doc, start=1):
        structured_content += f"\n\n--- Page {page_num} ---\n\n"
        blocks = page.get_text("blocks", sort=True)
        for block_idx, block in enumerate(blocks):
            if block[6] == 0:
                text = block[4].strip()
                if not text: continue
                try:
                    span = page.get_text("dict")["blocks"][block_idx]["lines"][0]["spans"][0]
                    avg_size = round(span["size"])
                except:
                    avg_size = body_size
                
                tag = "H1" if avg_size > body_size + 2 else "H2" if avg_size > body_size else "P"
                structured_content += f"[{tag}] {text}\n"
    
    doc.close()
    return structured_content

def extract_claims(structured_text):
    """Extract factual claims from structured text."""
    if not model:
        claims = []
        for line in structured_text.splitlines():
            if re.search(r"\d", line) and line.startswith("[P]"):
                claims.append({"claim": line[4:].strip(), "section": "Unknown"})
        return claims

    prompt = f"""Extract important factual claims from this text.
    [H1]=Main Heading, [H2]=Sub-heading, [P]=Paragraph
    Return ONLY: [{{"claim": "...", "section": "..."}}]
    
    {structured_text}"""
    
    try:
        resp = model.generate_content(prompt)
        raw = getattr(resp, "text", str(resp))
        parsed = parse__llm__json(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception as e:
        print(f"Error extracting claims: {e}", file=sys.stderr)
        return []
