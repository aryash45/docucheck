<h1 align="center">📑 DocuCheck</h1>
<p align="center">
  <b>AI-Powered Fact-Checker for Research Papers, Policy Briefs & Reports</b>  
  <br/>
  Built with <code>Python</code> • <code>PyMuPDF</code> • <code>Gemini</code>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python" />
  <img src="https://img.shields.io/badge/AI-Gemini-black" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
  <img src="https://img.shields.io/badge/Status-Prototype-orange" />
</p>

---

## ✨ What is DocuCheck?

Not every research paper or policy document tells the full truth.  
**DocuCheck** is a prototype that helps spot:
- ❌ Outdated claims  
- ⚖️ Internal mismatches (e.g., participant counts, conflicting years)  
- 🌍 Misleading statistics  

It reads a PDF, extracts factual claims, checks them for **consistency + accuracy**, and generates a **clean HTML dashboard report**.

<p align="center">
  <img src="./screenshots/report-summary.png" width="700"/>
  <br/>
  <i>Example report output (dashboard with claim validation)</i>
</p>

---

## 🚀 Quickstart

### 1️⃣ Clone the repo
```bash
git clone https://github.com/<your-username>/docucheck-ai.git
cd docucheck-ai
2️⃣ Create & activate a venv
bash
Copy
Edit
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
3️⃣ Install requirements
bash
Copy
Edit
pip install -r requirements.txt
4️⃣ Configure API key
bash
Copy
Edit
cp .env.example .env
Open .env and add:

ini
Copy
Edit
GEMINI_API_KEY=your_api_key_here
5️⃣ Run on a PDF
bash
Copy
Edit
python docucheck.py sample_docs/misleading_doc.pdf
Output:

✅ report.html → interactive dashboard

📑 Terminal logs (claims extracted + checked)

📂 Project Structure
bash
Copy
Edit
docucheck-ai/
├─ docucheck.py           # main script
├─ requirements.txt
├─ README.md
├─ .env.example
├─ .gitignore
├─ LICENSE
├─ sample_docs/
│  ├─ misleading_doc.pdf   # fake paper with errors (demo)
│  └─ climate_test.pdf     # real-world style doc
├─ screenshots/
│  ├─ report-summary.png
│  └─ report-claims.png
🧠 How it Works
Extract text → parse PDF using PyMuPDF

Claim extraction → Gemini identifies claims in JSON

Internal checks → mismatched numbers, years, participant counts

External checks → Gemini validates claims against knowledge

Report generator → HTML dashboard with ✅ Valid / ❌ Outdated

<p align="center"> <img src="./screenshots/report-claims.png" width="700"/> <br/> <i>Extracted claims with status indicators</i> </p>
🧪 Demo Docs
sample_docs/misleading_doc.pdf → Fake “research paper” with intentional errors

sample_docs/climate_test.pdf → Climate summary with real + testable claims

You can drop any academic, policy, or geopolitical PDF into sample_docs/ and run DocuCheck on it.

📦 Requirements
shell
Copy
Edit
python-dotenv>=1.0.1
PyMuPDF>=1.24.9
google-generativeai>=0.7.2
🛣 Roadmap
 Handle complex PDFs (multi-column, tables, references)

 Add source-backed verification (links to real references)

 Build Streamlit UI (drag & drop PDFs → instant dashboard)

 Export results to CSV/PDF

 Add confidence scoring

 Domain presets (medical, climate, geopolitics)

⚠️ Known Limitations
Most papers are correct → sometimes no issues will appear

Some claims need deep domain context → AI may be uncertain

Parsing complex PDFs (columns, figures) is tricky

Verification is reasoning-based, not a “live source lookup”

Ambiguous statements (“might”, “likely”) are hard to fact-check

👉 This is v1. Not perfect — but catching even 10% of hidden errors can prevent misinformation from spreading.

🤝 Contributing
Contributions welcome!

Keep PRs small + testable

Add docstrings & screenshots if possible

📜 License
MIT License — see LICENSE

🙋‍♂️ About
👋 Built by <your name>

🌐 LinkedIn: [your profile]

💬 Always open to collabs in AI, NLP, and research integrity

<p align="center"> <b>🚀 DocuCheck: Bringing trust & accountability back into research.</b> </p> ```
📦 requirements.txt
markdown
Copy
Edit
python-dotenv>=1.0.1
PyMuPDF>=1.24.9
google-generativeai>=0.7.2
🔐 .env.example
markdown
Copy
Edit
# Gemini API Key
GEMINI_API_KEY=your_api_key_here
🙈 .gitignore
markdown
Copy
Edit
# Python
__pycache__/
*.pyc
.venv/
venv/

# Environment
.env

# Reports & cache
report.html
screenshots/*.psd

# OS
.DS_Store
📜 LICENSE (MIT)
markdown
Copy
Edit
MIT License

Copyright (c) 2025 <Your Name>
