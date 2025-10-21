# DocuCheck

[![Project Status](https://img.shields.io/badge/status-active-brightgreen)](https://github.com/aryash45/docucheck)  [![Python Version](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org/)[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

---

## 🧠 Overview

**DocuCheck** is a Python-based tool that extracts factual claims from documents (like PDFs) and performs **automated fact-checking** using a generative AI model (Google’s Gemini).  
It produces a **human-readable HTML report** (`report.html`) summarizing extracted claims, internal consistency checks, and external verification results.

---

## ⚙️ Features

- **Structural Text Extraction:** Parses PDFs to understand document structure (headings vs. paragraphs) for better context.  
- **AI-Powered Claim Extraction:** Uses a generative model to identify and extract factual claims from text.  
- **Internal Consistency Analysis:** Detects contradictions *within* the document’s own claims.  
- **External Fact-Checking:** Verifies claims against the model’s external knowledge to identify outdated or invalid information.  
- **Modern HTML Reporting:** Generates a clean, single-page HTML report with a visual summary dashboard.  
- **Result Caching:** Caches analysis results to avoid re-processing and repeated API calls.

---

## 🗂️ Project Structure

```
Docucheck/
├── main.py           # Main CLI entry point with argument parsing
├── extractor.py      # Handles PDF parsing and claim extraction
├── verifier.py       # Handles internal/external fact-checking
├── reporter.py       # Generates the final HTML report
├── caching.py        # Manages file hashing and result caching
└── utils.py          # Shared utilities (e.g., JSON parsing)

run.py                # The main script to execute the package
requirements.txt      # Python dependencies
.env.example          # Example environment variables
.gitignore            # Ignores .env, .venv, pycache, etc.
LICENSE               # MIT License
README.md             # This file
```

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and navigate into the project directory:

```bash
git clone https://github.com/<your-username>/docucheck.git
cd docucheck
```

---

### 2. Set Up Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux (bash):**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Set Up Environment

Copy the example `.env` file and add your **Gemini API key**.

**Windows (PowerShell):**

```powershell
copy .env.example .env
# Now edit the .env file with Notepad or VS Code
```

**macOS/Linux (bash):**

```bash
cp .env.example .env
# Now edit the .env file with nano, vim, or VS Code
```

Your `.env` file should look like this:

```ini
GEMINI_API_KEY=your-api-key-goes-here
```

---

## 🧩 Usage

Run the application using `run.py`, passing the path to the document you want to analyze.

### Basic Example

```bash
python run.py "path/to/your/document.pdf"
```

This will analyze the PDF and save the report as `report.html` in the same directory.

---

### Command-Line Arguments

| Argument | Description | Required | Default |
|-----------|--------------|-----------|----------|
| `input_file` | Path to the input file (.pdf, .txt, etc.) | ✅ | — |
| `-o`, `--output` | Path to save the output HTML report | ❌ | `report.html` |
| `-l`, `--limit` | Limit the number of claims to externally fact-check (0 = all) | ❌ | `0` |
| `--force` | Force re-analysis and bypass cached results | ❌ | `False` |

---

### Full Example

```bash
python run.py "my_research.pdf" -o "MyReport.html" -l 5 --force
```

This command:
- Analyzes `my_research.pdf`
- Saves the report as `MyReport.html`
- Only fact-checks the first **5 claims**
- **Bypasses** the cache

---

## 🧠 How It Works

1. `run.py` executes the `main()` function in `Docucheck/__main__.py`.  
2. The script parses command-line arguments.  
3. `caching.py` generates a **SHA-256 hash** of the input file and checks for a cached result.  
4. If cache exists (and `--force` not used), analysis is skipped and report generation begins.  
5. If no cache:
   - `extractor.py` uses **PyMuPDF** to extract structured text.
   - Text is sent to **Gemini API** for claim extraction.
6. `verifier.py`:
   - Checks for **internal contradictions**.
   - Performs **external fact-checking** using Gemini’s knowledge.
7. `reporter.py` compiles all results into a single **HTML report**.
8. `caching.py` saves all results (claims, contradictions, checks) to a `.Docucheck_Cache` JSON file.

---

## 📄 License

Distributed under the **MIT License**.  
See [LICENSE](./LICENSE) for more information.
