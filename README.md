# Autonomous Researcher (DocuCheck)

> **Multi-Agent AI Research System — Scaffold, Verify & Fact-Check Research on Any Topic**

[![Build Status](https://img.shields.io/badge/build-17%20passed-brightgreen.svg?style=for-the-badge&logo=pytest)](tests)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue.svg?style=for-the-badge&logo=python)](https://python.org)
[![LLM Ensembles](https://img.shields.io/badge/LLMs-Gemini%20%7C%20Claude%20%7C%20GPT--4o%20%7C%20DeepSeek-4285F4.svg?style=for-the-badge)](https://aistudio.google.com)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)

---

![Autonomous Researcher Demo](docs/assets/demo.gif)

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

1. **Research Scaffold** — Generate a verified research framework from any topic.
2. **Improve** — Upload your draft, get specific improvements based on literature evidence.
3. **Fact Check** — Verify every claim in an existing paper or document.

---

## 🛠️ Tech Stack

| Category | Technologies |
| :--- | :--- |
| **Frontend** | Next.js 14, Tailwind CSS, TypeScript |
| **Backend API** | Python 3.11+, FastAPI (Streaming SSE), Pydantic v2, AsyncIO |
| **LLM Orchestration** | Gemini 1.5 Flash, Claude Opus 4.7, GPT-4o, DeepSeek R1, Qwen3-Max |
| **Vector Search & ML** | FAISS (`faiss-cpu`), `sentence-transformers` (`all-MiniLM-L6-v2`), NumPy |
| **Literature Ingestion** | Semantic Scholar API, OpenAlex API, ArXiv API, Tenacity (Retries) |
| **Code Execution Sandbox** | E2B Code Interpreter (`E2B_API_KEY`), Subprocess Sandbox |
| **Testing & Quality** | PyTest 8.x, PyTest-Asyncio, PyTest-Mock |

---

## 🏗️ System Architecture

Autonomous Researcher processes research queries through a plan-execute-verify graph pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│                       Research Topic                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Stage 1: Literature Pipeline                │
│ ──▶ Fetch Papers (Semantic Scholar / OpenAlex / ArXiv)      │
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
│ ┌──────────────────┐    Retrieves vector evidence & executes│
│ │  executor_node   │ ──▶ quantitative code in E2B sandbox   │
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
│                 Stage 3: FastAPI & Next.js                  │
│ ──▶ Streaming JSON via FastAPI SSE                          │
│ ──▶ Interactive Next.js Frontend Dashboard                  │
│ ──▶ Exportable Markdown Audit Reports (Scaffold / Fact-Check)│
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
docucheck/
├── src/
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
│   ├── observability/        # Logging & telemetry hooks
│   └── reviewer/             # Verification review modules
├── tests/
│   ├── test_literature.py    # Ingestion & FAISS cache unit tests
│   └── test_tree.py          # ResearchGraph & node pipeline integration tests
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
   *Note: Autonomous Researcher works out of the box with offline heuristic fallbacks if no API keys are configured.*

---

## 💡 Usage

### API & Output

Autonomous Researcher returns structured JSON via a FastAPI streaming API consumed by a Next.js frontend. Markdown exports available for download.

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

Autonomous Researcher includes a comprehensive test suite covering the literature pipeline, FAISS vector cache, E2B executor, and graph state machine.

Run all tests using `pytest`:

```bash
# Run complete test suite
python -m pytest

# Run with verbose output
python -m pytest -vv

# Run specific test modules
python -m pytest tests/test_tree.py
python -m pytest tests/test_literature.py
```

---

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository (`https://github.com/aryash45/docucheck/fork`).
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
