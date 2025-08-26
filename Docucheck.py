import os
import re
import json
from dotenv import load_dotenv 
import fitz

import google.generativeai as genai
#Step 1: Load the .env file
load_dotenv()
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    # library APIs vary; attempt common constructor name and fall back gracefully
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
    except Exception:
        # if the package exposes a different entrypoint, just keep model as None
        model = None
except Exception:
    model = None
#Step 2: Extract text from PDF
def extract_text_from_first_page(pdf_path):
    doc = fitz.open(pdf_path)
    text=""
    for page in doc:
        text+= page.get_text("text")
    return text
def extract_claims(text):
    prompt = f"""
    Extract important factual claims from this academic/research text.
    Include numbers, years, statistics, participant counts, citations, etc.
    Return JSON list in this format:
    [
      {{"claim": "...", "section": "Abstract/Intro/Methods/Results/Discussion"}}
    ]
    Only output valid JSON.
    Text:
    {text}
    """
    # Use the model when available; otherwise perform a lightweight heuristic extraction
    if model:
        try:
            resp = model.generate_content(prompt)
            raw = getattr(resp, 'text', resp)
            try:
                # If the model wrapped JSON in Markdown fences (```json ... ```), extract the inner JSON first
                fenced = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", str(raw), re.S | re.I)
                if fenced:
                    candidate = fenced.group(1)
                    return json.loads(candidate)

                return json.loads(raw)
            except Exception as e:
                print("could not parse json from model response:", e)
                print("--- raw model output start ---")
                try:
                    print(repr(raw[:2000]))
                except Exception:
                    print(str(raw))
                print("--- raw model output end ---")
                # try to extract a JSON substring if the model wrapped JSON in text
                m = re.search(r"(\[.*\]|\{.*\})", str(raw), re.S)
                if m:
                    candidate = m.group(1)
                    try:
                        return json.loads(candidate)
                    except Exception as e2:
                        print("extracted JSON still invalid:", e2)
                # fall through to heuristic extraction
        except Exception as e:
            print("could not parse json from model response:", e)
            # fall through to heuristic extraction

    # Heuristic fallback: extract sentences that contain numbers or years
    claims = []
    sentences = re.split(r"(?<=[\.\?\!])\s+", text)
    for s in sentences:
        if re.search(r"\d", s) or re.search(r"(?:19|20)\d{2}", s):
            claims.append({"claim": s.strip(), "section": "Unknown"})
    return claims
def check_consistency(claims):
    issues =[]
    participants = []
    for c in claims:
        nums = re.findall(r"\d+",c["claim"])
        if "participant" in c["claim"].lower() and nums:
            participants.append(int(nums[0]))
    if len(participants)>1:
        issues.append(f"Conflicting participant counts: {participants}")
    years =[]
    for c in claims:
        y = re.findall(r"(?:19|20)\d{2}", c["claim"])
        if y:
            years.extend(y)
    if len(set(years))>1:
        issues.append(f"Conflicting years mentioned: {set(years)}")
    return issues                                  
def external_fact_check(claim):
    prompt = f"""
    You are a fact-checking assistant. 
    Check this factual claim against your knowledge base (till 2024).
    
    Return ONLY a valid JSON object in the following format:
    {{
      "claim": "...",
      "is_outdated": true/false,
      "latest_info": "..."
    }}

    Claim: {claim}
    """
    # If model isn't configured, skip external check
    if not model:
        return {"claim": claim, "is_outdated": None, "latest_info": "Model not configured - external check skipped"}

    try:
        resp = model.generate_content(prompt)
        raw = getattr(resp, 'text', resp)

        # 1) If model returned fenced JSON like ```json {...}```, extract inner JSON
        fenced = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", str(raw), re.S | re.I)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except Exception:
                pass

        # 2) Try parsing raw directly
        try:
            return json.loads(raw)
        except Exception:
            pass

        # 3) Attempt to extract a JSON substring from the raw text
        m = re.search(r"(\{(?:.|\n)*\}|\[(?:.|\n)*\])", str(raw), re.S)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass

        # If all parsing attempts fail, log and return a helpful fallback
        print("⚠️ Could not parse JSON, got raw text instead:", raw)
        return {"claim": claim, "is_outdated": None, "latest_info": "Parsing failed, see raw model output above."}

    except Exception as e:
        return {"claim": claim, "is_outdated": None, "latest_info": f"Error during external check: {e}"}
def generate_report(claims,issues,external_checks):
    claim_items = "".join(
        [f"<li>{c['claim']} <span class='section'>({c['section']})</span></li>" for c in claims]
    )

    # Internal issues
    issue_items = "".join(
        [f"<li class='issue'>{i}</li>" for i in issues]
    ) if issues else "<li class='ok'>✅ No major internal issues found</li>"

    # Parse external checks
    external_items = ""
    valid, outdated = 0, 0
    for e in external_checks:
        if isinstance(e, dict):
            status = "✅ Still valid" if not e.get("is_outdated") else "❌ Outdated"
            if e.get("is_outdated"):
                outdated += 1
            else:
                valid += 1
            external_items += f"""
            <div class="ext-card">
                <p><b>Claim:</b> {e['claim']}</p>
                <p><b>Status:</b> {status}</p>
                <p><b>Latest Info:</b> {e['latest_info']}</p>
            </div>
            """
        else:
            external_items += f"<div class='ext-card'><p>{e}</p></div>"

    # Calculate summary
    total = valid + outdated if (valid + outdated) > 0 else 1
    accuracy = round((valid / total) * 100, 1)

    # Final HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>DocuCheck Report</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #f9fafb;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 950px;
                margin: auto;
            }}
            h1 {{
                color: #1e3a8a;
                text-align: center;
                margin-bottom: 10px;
            }}
            .summary {{
                text-align: center;
                background: #eef2ff;
                border: 2px solid #1e3a8a;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 20px;
            }}
            .progress {{
                background: #ddd;
                border-radius: 20px;
                height: 20px;
                margin-top: 10px;
            }}
            .progress-bar {{
                height: 20px;
                border-radius: 20px;
                background: #16a34a;
                width: {accuracy}%;
                text-align: center;
                color: white;
                font-size: 12px;
            }}
            .card {{
                background: white;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 15px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }}
            .ext-card {{
                background: #f3f4f6;
                border-radius: 8px;
                padding: 10px 15px;
                margin-bottom: 10px;
                border-left: 4px solid #1e3a8a;
            }}
            .section {{
                color: gray;
                font-size: 0.9em;
            }}
            .issue {{
                color: red;
                font-weight: bold;
            }}
            .ok {{
                color: green;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📑 DocuCheck Report</h1>

            <div class="summary">
                <h2>📊 Overall Summary</h2>
                <p>Total Claims Checked: <b>{total}</b></p>
                <p>Valid: <b>{valid}</b> | Outdated: <b>{outdated}</b></p>
                <div class="progress">
                    <div class="progress-bar">{accuracy}%</div>
                </div>
            </div>

            <div class="card">
                <h2>🔍 Extracted Claims</h2>
                <ul>{claim_items}</ul>
            </div>
            <div class="card">
                <h2>⚖️ Internal Consistency Issues</h2>
                <ul>{issue_items}</ul>
            </div>
            <div class="card">
                <h2>🌍 External Checks</h2>
                {external_items}
            </div>
        </div>
    </body>
    </html>
    """
    return html

# -----------------------------
# STEP 6: Main Runner
# -----------------------------
if __name__ == "__main__":
    pdf_path = "sample.pdf"  # change this to your PDF
    text = extract_text_from_first_page(pdf_path)

    print("🔍 Extracting claims...")
    claims = extract_claims(text)

    print("🔎 Checking consistency...")
    issues = check_consistency(claims)

    print("🌍 External verification (Gemini)...")
    external_checks = [external_fact_check(c["claim"]) for c in claims[:5]]  # limit to 5

    report = generate_report(claims, issues, external_checks)

    with open("report.html", "w", encoding="utf-8") as f:
        f.write(report)

    print("✅ Report saved as report.html")