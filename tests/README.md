# Test files for DocuCheck

This directory contains test files and test suites for DocuCheck.

## Running tests

```bash
python -m pytest tests/
```

## Test structure

- `test_extractor.py` - Tests for PDF text extraction and claim extraction
- `test_verifier.py` - Tests for consistency checking and fact verification
- `test_reporter.py` - Tests for HTML report generation
- `test_caching.py` - Tests for caching functionality
- `test_integration.py` - End-to-end integration tests
