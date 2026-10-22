# DocuCheck

> **Python research graph for document claim extraction and best-effort fact-checking**

[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=for-the-badge&logo=python)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-local%20suite%20offline-2ea44f.svg?style=for-the-badge&logo=pytest)](tests)

---

## 📖 Overview

**Autonomous Researcher** is a multi-agent research system that helps researchers, journalists, and students scaffold, verify, and fact-check research on any topic.

Unlike tools like Undermind or Elicit that merely find and summarize sources, Autonomous Researcher goes further:

- Every claim is verified against academic sources
- Confidence score assigned per claim
- Conflicting sources flagged automatically
- Quantitative claims verified via sandboxed code execution
- Full audit trail for every conclusion

### Operational Modes

1. **Research Scaffold** — Generate a research framework from a topic and literature corpus.
2. **Improve** — Planned; draft improvement is not implemented yet.
3. **Fact Check** — Extract claims from an existing document and check them against supplied literature.

---

## 🛠️ Tech Stack

| Category | Technologies |
| :--- | :--- |
| **Runtime** | Python 3.11+ |
| **LLM assistance** | Gemini 1.5 Flash REST API, with deterministic heuristic fallbacks |
| **Vector Search & ML** | FAISS (`faiss-cpu`), `sentence-transformers` (`all-MiniLM-L6-v2`), NumPy |
| **Literature Ingestion** | Semantic Scholar API, OpenAlex API, requests, Tenacity |
| **Document Ingestion** | PDF, DOCX, Markdown, and plain-text parsing |
| **Code Execution** | Optional E2B Code Interpreter (`E2B_API_KEY`); local fallback for development only |
| **Testing & Quality** | PyTest 8.x with local and integration markers |

The web frontend, FastAPI streaming API, multi-provider LLM ensemble, and ArXiv fetcher remain planned rather than implemented.

---

## 🏗️ System Architecture

DocuCheck currently processes research queries and uploaded documents through a plan-execute-verify graph pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│                       Research Topic                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Stage 1: Literature Pipeline                │
│ ──▶ Fetch Papers (Semantic Scholar / OpenAlex)              │
│ ──▶ Generate Embeddings & Index in FAISS Vector Store       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Stage 2: Research Graph                     │
│                                                             │
│ ┌──────────────────┐    Generates candidate research angles │
│ │  planner_node    │ ──▶                                    │
│ └────────┬─────────┘                                        │
│          │                                                  │
│          ▼                                                  │
│ ┌──────────────────┐    Retrieves evidence & optionally    │
│ │  executor_node   │ ──▶ executes quantitative analysis    │
│ └────────┬─────────┘                                        │
│          │                                                  │
│          ▼                                                  │
│ ┌──────────────────┐    Scores evidence strength & applies  │
│ │  verifier_node   │ ──▶ threshold filters                  │
│ └────────┬─────────┘                                        │
│          │                                                  │
│          ▼                                                  │
│ ┌──────────────────┐    Isolates atomic verifiable claim    │
│ │claim_extractor   │ ──▶ statements                         │
│ └────────┬─────────┘                                        │
│          │                                                  │
│          ▼                                                  │
│ ┌──────────────────┐    Cross-checks claims -> verdict:     │
│ │fact_checker_node │ ──▶ SUPPORTED | REFUTED | UNVERIFIABLE │
│ └──────────────────┘                                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Stage 3: Python output                      │
│ ──▶ Structured state and node-level trace                  │
│ ──▶ Optional Markdown report generation                     │
│ ──▶ Web/API shell planned for a later phase                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
docucheck/
├── src/
│   ├── ingestion/
│   │   ├── parser.py          # PDF, DOCX, Markdown, and text parsing
│   │   ├── chunker.py         # Document chunking helpers
│   │   └── claim_extractor.py # Document claim extraction
│   ├── literature/
│   │   └── fetcher.py        # Semantic Scholar, OpenAlex & FAISS cache
│   ├── sandbox/
│   │   └── executor.py       # E2B cloud sandbox & subprocess fallback
│   ├── tree/
│   │   ├── state.py          # Pipeline state & data models
│   │   ├── nodes.py          # 5 execution nodes (Planner, Executor, etc.)
│   │   └── graph.py          # ResearchGraph pipeline state machine
│   ├── writer/
│   │   └── scaffold_writer.py# Markdown report & fact-check card generator
│   ├── observability/        # Reserved for future logging/telemetry hooks
│   └── reviewer/             # Reserved for future review modules
├── tests/
│   ├── test_ingestion.py     # Local document-ingestion tests
│   ├── test_tree.py          # Local graph and sandbox tests
│   └── test_literature.py    # Marked integration/API/model tests
├── cache/                    # Local literature & FAISS vector cache
├── outputs/                  # Generated scaffold & audit reports
├── .env.example              # Environment variables template
└── requirements.txt          # Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites

* **Python:** `>= 3.11`
* **Git:** `>= 2.30`
* *(Optional)* **Gemini API Key:** For Gemini 1.5 Flash LLM orchestration ([Google AI Studio](https://aistudio.google.com/app/apikey)).
* *(Optional)* **E2B API Key:** For cloud sandbox code execution ([e2b.dev](https://e2b.dev)).
* *(Optional)* **Semantic Scholar API Key:** For higher API rate limits ([Semantic Scholar](https://www.semanticscholar.org/product/api)).

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/aryash45/docucheck.git
   cd docucheck
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # On macOS / Linux
   python3 -m venv venv
   source venv/bin/activate

   # On Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   ```
    *Note: DocuCheck works out of the box with offline heuristic fallbacks if no API keys are configured.*

---

## 💡 Usage

### Python API & Output

DocuCheck returns a structured dictionary from `ResearchGraph.run()` or a `ResearchState` from `run_fact_check_only()`. Markdown report generation is available through the writer module. A web/API shell is planned but is not currently present.

### Running via Python API

```python
from src.literature.fetcher import LiteraturePipeline
from src.tree.graph import ResearchGraph
from src.writer.scaffold_writer import ScaffoldWriter

# 1. Fetch relevant academic literature
pipeline = LiteraturePipeline(cache_dir="cache/literature")
papers = pipeline.fetch(query="Quantum Error Correction", max_results=5)

# 2. Run the Plan-Execute-Verify Research Graph
graph = ResearchGraph(budget_usd=0.50, max_angles=3)
evidence_map = graph.run(topic="Quantum Error Correction", papers=papers)

# 3. Write structured audit cards and scaffold
writer = ScaffoldWriter(output_dir="outputs")
result = writer.write(evidence_map, papers)

print("Generated audit artifacts:")
print(result.summary())
```

---

## 🧪 Testing & Quality Assurance

DocuCheck includes a deterministic local suite plus separately marked integration tests for live literature APIs and FAISS/model downloads.

Run all tests using `pytest`:

```bash
# Run the default local suite; integration tests are excluded by pytest.ini
python -m pytest

# Run the local suite with verbose output
python -m pytest -vv

# Run specific local modules
python -m pytest tests/test_tree.py

# Run the live/API/model integration suite explicitly
python -m pytest -m integration
```

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository (`https://github.com/aryash45/docucheck/fork`).
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.
