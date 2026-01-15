# DocuCheck - Quick Reference Guide

## 📌 Project Structure at a Glance

```
docucheck/
├── docucheck/                    Main Python package
│   ├── core/                    Core analysis modules
│   │   ├── extractor.py        Extract text & claims
│   │   ├── verifier.py         Check consistency & facts
│   │   └── caching.py          Cache results
│   ├── report/
│   │   └── reporter.py         Generate HTML reports
│   ├── utils/
│   │   └── helpers.py          JSON parsing utilities
│   └── __main__.py             Entry point
├── run.py                       Execute: python run.py
├── setup.py                     Install: pip install -e .
└── requirements.txt             Dependencies
```

## 🚀 Quick Start

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Or install package in development mode
pip install -e .
```

### Set Environment Variables
Create `.env` file:
```env
GEMINI_API_KEY=your_key_here
```

### Run Analysis
```bash
# As script
python run.py document.pdf -o report.html

# As module
python -m docucheck document.pdf

# As command (after pip install -e .)
docucheck document.pdf --force --limit 5
```

## 📖 Module Guide

### `core/extractor.py`
Handles text extraction and claim identification:
- `extract_structured_text(pdf_path)` - Extract PDF with structure tags
- `extract_claims(text)` - AI-powered claim extraction

### `core/verifier.py`
Fact-checking and consistency analysis:
- `check_consistency_with_llm(claims)` - Find contradictions
- `external_fact_check(claim)` - Verify single claim

### `core/caching.py`
Cache analysis results to avoid re-processing:
- `get_file_hash(filepath)` - SHA256 hash
- `get_cache(hash)` - Retrieve cached results
- `set_cache(hash, data)` - Store results

### `report/reporter.py`
Generate beautiful HTML reports:
- `generate_report(claims, issues, checks)` - Create HTML

### `utils/helpers.py`
Shared utility functions:
- `parse__llm__json(text)` - Extract JSON from LLM responses

## ⚙️ CLI Options

```bash
python run.py INPUT [-o OUTPUT] [-l LIMIT] [--force]

INPUT              Path to PDF or text file to analyze
-o, --output FILE  Save report to FILE (default: report.html)
-l, --limit N      Check only N claims (0=all, default: 0)
--force            Bypass cache and re-analyze
```

## 💾 Cache Management

Cache stored in `.docucheck_cache/` with structure:
```
.docucheck_cache/
├── hash1.json      # Results for file 1
├── hash2.json      # Results for file 2
└── ...
```

To clear cache:
```bash
rm -rf .docucheck_cache
```

## 🔄 Development Workflow

### Adding New Features
1. Add code to appropriate module (core/, report/, utils/)
2. Update related `__init__.py` if needed
3. Add tests to `tests/` directory
4. Update this guide

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_extractor.py
```

## 📝 Import Patterns

From other Python code:
```python
# Import specific modules
from docucheck.core import extractor, verifier, caching
from docucheck.report import reporter
from docucheck.utils import parse__llm__json

# Use them
text = extractor.extract_structured_text("doc.pdf")
claims = extractor.extract_claims(text)
issues = verifier.check_consistency_with_llm(claims)
report = reporter.generate_report(claims, issues, [])
```

## 🐛 Troubleshooting

### "GEMINI_API_KEY not found"
- Ensure `.env` file exists in project root
- Check key is set: `GEMINI_API_KEY=xxx`
- Run from project directory: `cd docucheck && python run.py`

### "ModuleNotFoundError: No module named 'docucheck'"
- Install dependencies: `pip install -r requirements.txt`
- Or install package: `pip install -e .`

### "PyMuPDF not found"
- Install: `pip install PyMuPDF`

## 📚 Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [Google Generative AI Docs](https://ai.google.dev/)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)

---

**Last Updated:** January 16, 2026
**Version:** 1.0.0
