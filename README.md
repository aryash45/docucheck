# Docucheck

## Overview
Docucheck is a Python-based tool that extracts factual claims from PDF documents and performs automated fact-checking using a generative AI model (Gemini or compatible). It produces a human-readable HTML report (`report.html`) summarizing extracted claims, internal consistency checks, and external verification results.

## Contents
- `Docucheck.py` — Main script: extracts text from PDFs, extracts claims, queries an LLM for fact checks, and generates `report.html`.
- `requirements.txt` — Python dependencies used by `Docucheck.py`.
- `3d.html`, `Style.css`, `script.js` — Demo 3D website included in the repo (optional for this project).
- `.env.example` — Example environment variables (no secrets).
- `.gitignore` — Ignores `.env` and other sensitive files.

## Quick start (backend)

1. Create and activate a virtual environment (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and add your Gemini API key:

```powershell
copy .env.example .env
# Edit .env and set GEMINI_API_KEY=your-key
```

4. Place the PDF you want to analyze next to `Docucheck.py` or update the script's path, then run:

```powershell
python Docucheck.py
```

5. `report.html` will be generated in the same folder with extracted claims and fact-check notes.

## How it works (high level)
- Extract text from the provided PDF using PyMuPDF (`fitz`).
- Use a small prompt to a generative model to extract structured claims.
- Perform internal consistency checks (e.g., conflicting numbers/dates) locally.
- Ask the model to perform external checks and return evidence and a confidence summary.
- Generate a readable HTML report with findings.

## Configuration
- `GEMINI_API_KEY` must be set in `.env` for LLM calls. If you don't have an API key or prefer not to use one, the script will use heuristic fallbacks for claim extraction but external verification may be skipped.

## Security
- Never commit a real `.env` file. Use `.env.example` in the repo and set secrets locally or via your CI provider's secret store.
- If a key was accidentally committed, rotate it immediately and consider scrubbing history.

## Publishing to GitHub
1. (If not already) initialize and commit the repo locally:

```powershell
git init -b main
git add .
git commit -m "Initial commit: Docucheck"
```

2. Create a GitHub repository, then add the remote and push:

```powershell
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

## Troubleshooting
- If you see "No module named fitz": install PyMuPDF with `pip install PyMuPDF`.
- If the model returns unparsable text, the script logs raw output and applies heuristics to extract claims.

## License
Demo/hackathon code — free to adapt. Replace placeholder keys and models before production use.

## Contact
Open an issue or contact the project owner for help or feature requests.
