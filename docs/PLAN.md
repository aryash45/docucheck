# DocuCheck Product and Engineering Plan

Date: 2026-10-22  
Scope: planning only. Primary wedge is Mode 3: fact-check an uploaded document with claim-by-claim verdicts, cited passage evidence, and an audit trail. Mode 1 scaffold generation remains secondary.

## Executive direction

DocuCheck should become a narrow, credible document fact-checking tool before it becomes a general research agent. The near-term product user should be someone who already has a document or draft and wants to know: "Which claims are supported, contradicted, or unverifiable, and what exact passage proves that?" The strongest resume story will come from measured verification quality, citation integrity, and honest abstention, not from a broad UI or inflated agent claims.

Quality work should precede the web shell. The current implementation has a critical Mode 3 correctness bug that makes uploaded-document fact-checking return an apparently successful empty result. Fix that first, then build an eval harness, then add passage-level evidence and citation-integrity metrics. Only then wrap it in a web product.

---

## Verification work performed

### Commands run

| Check | Result | Notes |
| --- | --- | --- |
| `set GEMINI_API_KEY=your_dummy& set E2B_API_KEY=your_dummy& python -m pytest tests/test_ingestion.py tests/test_tree.py -q` | PASS: 39 passed, 5 warnings | Important local path with LLM/E2B disabled so tests exercise offline fallbacks. |
| `python -m pytest tests/test_literature.py -q` | TIMED OUT after two tests | API-facing Semantic Scholar/OpenAlex tests completed first; suite did not reach FAISS before timeout. This is an environment/test-design issue, not proof FAISS is broken. |
| `python -m pytest tests/test_literature.py::test_faiss_cache -q -s` | PASS: 1 passed, 2 warnings in 93.41s | FAISS is installed in this environment and works, but first model load is slow and reaches Hugging Face. |
| Direct Mode 3 reproduction via `ResearchGraph().run_fact_check_only(state)` | CONFIRMED bug | One ingested claim becomes zero claims and zero verifications with `ok` trace events. |

### Direct Mode 3 reproduction output

```text
before_claims 1 ['ingested_claim_0']
after_claims 0 []
verifications 0
trace [('claim_extractor', 'ok', {'papers': 1, 'angles': 0, 'evidence': 0, 'scores': 0, 'claims': 1, 'verifications': 0, 'errors': 0}, {'papers': 1, 'angles': 0, 'evidence': 0, 'scores': 0, 'claims': 0, 'verifications': 0, 'errors': 0}), ('fact_checker', 'ok', {'papers': 1, 'angles': 0, 'evidence': 0, 'scores': 0, 'claims': 0, 'verifications': 0, 'errors': 0}, {'papers': 1, 'angles': 0, 'evidence': 0, 'scores': 0, 'claims': 0, 'verifications': 0, 'errors': 0})]
errors []
```

---

## Verified findings

### Required known facts

| # | Status | Finding | Evidence |
| --- | --- | --- | --- |
| 1 | CONFIRMED | `run_fact_check_only` runs `claim_extractor_node`, which overwrites ingested claims from Mode 3. With empty `state.evidence`, it sets `state.claims = []`, then fact checking runs over zero claims and reports no errors. | `_FACT_CHECK_PIPELINE` includes `claim_extractor` and `fact_checker` in `src/tree/graph.py:114-117`; `run_fact_check_only` loops over that pipeline in `src/tree/graph.py:235-237`; `claim_extractor_node` builds claims from `state.evidence` and assigns `state.claims = claims` in `src/tree/nodes.py:395-419`; direct reproduction above shows before=1, after=0, verifications=0, trace status=`ok`. |
| 2 | CONFIRMED | `_verify_claim` gives the LLM only the first 200 characters of each relevant abstract. The heuristic fallback marks support on `overlap >= 3` shared words and marks contradiction if an abstract contains words such as `however`, `contrary`, `disagree`, or `refute`. | Context construction uses `abstract = getattr(p, "abstract", "")[:200]` in `src/tree/nodes.py:504-506`; support threshold is `if overlap >= 3` in `src/tree/nodes.py:549-550`; contradiction keyword check is in `src/tree/nodes.py:552-553`. |
| 3 | CONFIRMED | Trace events are appended only after a node finishes. There is no subscription hook, streaming callback, or per-claim progress event. | `_run_traced_node` calls the node first at `src/tree/graph.py:84`, then appends `PipelineTraceEvent` at `src/tree/graph.py:92-101`; trace model has node-level fields only in `src/tree/state.py:69-77`. |
| 4 | CONFIRMED | `src/observability/`, `src/reviewer/`, and `red_team/` contain only `.gitkeep`. | Directory listing showed only `.gitkeep` in each. |
| 5 | CONFIRMED | README claims a Next.js frontend, FastAPI streaming, multiple LLMs, a "17 passed" badge, and a demo gif; these do not exist in the repo. Only Gemini is called in code. | README badge at `README.md:5`; demo gif reference at `README.md:13`; Next.js/FastAPI claims at `README.md:41-42`, `README.md:98-100`, `README.md:182`; LLM ensemble claims at `README.md:8`, `README.md:43`; Gemini endpoint appears in `src/tree/nodes.py:30-33` and `src/ingestion/claim_extractor.py:20-23`; no frontend/API files were present in the repo listing. |
| 6 | CONFIRMED | `src/sandbox/__init.py` is an empty typo duplicate alongside `src/sandbox/__init__.py`. | Directory listing showed both `src/sandbox/__init.py` and `src/sandbox/__init__.py`; both names listed in the same directory. |
| 7 | CONFIRMED | Claim IDs differ by mode: ingestion uses `ingested_claim_{i}`, graph extraction uses `claim_{counter_start + i}`. | Ingestion IDs in `src/ingestion/claim_extractor.py:204`; graph IDs in `src/tree/nodes.py:460`. |
| 8 | PARTIAL | FAISS-dependent tests can fail or stall for environment reasons. In this environment, FAISS and sentence-transformers are installed and `test_faiss_cache` passed, but the full literature suite timed out in API-facing tests before FAISS on the first run. The FAISS test also loads/downloads `all-MiniLM-L6-v2`, making it slow and network-sensitive. | FAISS imports occur inside `FAISSCache.set` and `semantic_search` at `src/literature/fetcher.py:168`, `src/literature/fetcher.py:196`; embedding model load is `SentenceTransformer("all-MiniLM-L6-v2")` at `src/literature/fetcher.py:149-150`; `test_faiss_cache` calls `cache.set` and `semantic_search` in `tests/test_literature.py:115-132`; focused run passed in 93.41s. |

### Additional bugs and risks, ranked by severity

| Severity | Risk | Why it matters | Evidence | First mitigation |
| --- | --- | --- | --- | --- |
| Critical | Mode 3 silently returns successful empty fact-checks | Primary wedge is broken; users see no error and may trust the result. | Reproduction above; trace status remains `ok`. | Regression test first, then skip claim extraction in fact-check-only mode or make `claim_extractor_node` preserve pre-populated claims when `state.evidence` is empty and `state.claims` already exists. |
| Critical | Heuristic verifier can confidently support claims based on word overlap | Produces confident-looking but weak verdicts. | `overlap >= 3` support threshold in `src/tree/nodes.py:549-550`; confidence can reach 0.85 when supporting papers exist in `src/tree/nodes.py:557-559`. | Add passage retrieval and entailment-style evidence scoring; introduce confidently-wrong metric. |
| High | Evidence is paper-title/abstract-level, not passage-level | Fails parity target and cannot support claim-by-claim auditability. | `ClaimVerification` only stores source title lists in `src/tree/state.py:56-65`; output only includes `supported_by` in `src/tree/state.py:180-187`. | Add `PassageEvidence` model with quote, location, direction, source metadata, and score. |
| High | LLM failures silently fall back to heuristics | A degraded result can look normal unless logs are inspected. | `_call_gemini` returns `None` when no key or error in `src/tree/nodes.py:38-59`; ingestion helper also returns `None` on error in `src/ingestion/claim_extractor.py:25-43`. | Add explicit `model_status`/`fallback_used` in output and trace. |
| High | Local subprocess sandbox is unsafe for public uploads | It runs Python snippets with current interpreter; not a production sandbox. | `_LocalExecutor` warns "Not a real sandbox" at `src/sandbox/executor.py:71-76`; uses `subprocess.run([sys.executable, "-c", full_code])` at `src/sandbox/executor.py:81-91`. | Disable local subprocess in public server mode; require E2B or remove code execution from web path. |
| High | Upload parsing lacks product-grade validation | Unknown binary files are read entirely into memory and decoded. | Unknown fallback does `raw = path.read_bytes()` in `src/ingestion/parser.py:227-229`; no size or MIME validation in `parse` at `src/ingestion/parser.py:92-112`. | Add upload limits, MIME/extension allowlist, filename sanitization, and max extracted text length. |
| Medium | Mutable default argument in ingestion API | `papers: list = []` can cause surprising shared state patterns. | `IngestionPipeline.run(..., papers: list = [])` in `src/ingestion/pipeline.py:57-61`. | Change to `papers: list | None = None` in Phase 0. |
| Medium | Literature fetch swallows source failures | Fetch can return partial/empty results with warnings only. | Fetch catches exceptions and logs warnings at `src/literature/fetcher.py:241-247`. | Add source status to output and eval logs. |
| Medium | README overclaims erode credibility | Resume/project readers will compare repo to README. | See README lines in known fact #5. | Honesty pass in Phase 0. |
| Medium | Tests depend on live APIs and model downloads | CI may be flaky; failures are hard to classify. | `test_literature.py` tries live APIs then falls back at `tests/test_literature.py:70-89`; FAISS test loads embeddings. | Split unit tests from integration tests; mark live/model tests separately. |
| Low | ArXiv is claimed but not implemented | Scope/credibility mismatch. | README claims ArXiv at `README.md:45`, `README.md:63`; literature pipeline creates Semantic Scholar and OpenAlex fetchers only at `src/literature/fetcher.py:223-224`. | Remove from README until implemented. |

---

## Phased roadmap

### Phase 0: correctness and honesty fixes

Goal: make the primary wedge stop lying. End with a local demo where an ingested claim survives Mode 3 and gets a verification record.

| Order | Task | Files touched | Acceptance criteria | Estimate | Risks |
| --- | --- | --- | --- | --- | --- |
| 0.1 | Add regression test reproducing Mode 3 claim wipeout | `tests/test_tree.py` or new `tests/test_fact_check_mode.py` | Test starts with one `ingested_claim_0`, runs `run_fact_check_only`, and fails until at least one claim and one verification remain. | 0.5 day | Must disable live Gemini/E2B in test. |
| 0.2 | Fix fact-check-only pipeline | `src/tree/graph.py`, maybe `src/tree/nodes.py` | `run_fact_check_only` preserves pre-populated `state.claims`; claim IDs remain stable; trace shows fact-check work. | 0.5 day | Avoid breaking Mode 1 claim extraction. |
| 0.3 | Add guardrail for empty fact-check results | `src/tree/graph.py`, `src/tree/state.py` | If input claims >0 and output claims/verifications=0, output contains an explicit error or raises in strict mode. | 0.5 day | Decide whether API should raise or return failed run status later. |
| 0.4 | Remove typo package file | `src/sandbox/__init.py` | File removed; imports still pass. | 0.1 day | Low. |
| 0.5 | Fix mutable default argument | `src/ingestion/pipeline.py`, tests | `papers=None` internally becomes `[]`; tests pass. | 0.2 day | Low. |
| 0.6 | README honesty pass | `README.md` | Remove/mark as planned: Next.js, FastAPI, multi-LLM, ArXiv, demo gif, "every claim verified", "conflicts flagged". Test badge matches actual focused test count or is removed. | 0.5 day | Marketing may look less flashy, but credibility improves. |
| 0.7 | Split tests into local vs integration markers | `pytest.ini` or test files | Local suite avoids live APIs/model downloads by default; FAISS/model/API tests are marked. | 0.5 day | Requires small test cleanup. |

Demonstrable at end: run a tiny text/doc ingestion, show extracted claim, preserved claim ID, verdict, trace, and honest README.

### Phase 1: eval harness

Goal: stop guessing. Every future feature must improve or trade off measured metrics on a fixed eval set.

| Order | Task | Files touched | Acceptance criteria | Estimate | Risks |
| --- | --- | --- | --- | --- | --- |
| 1.1 | Define eval data schema | `evals/schema.py`, `evals/README.md`, sample JSONL | JSONL supports claim text, gold label, gold evidence quote/location/source, allowed sources, notes. | 0.5 day | Avoid overbuilding. |
| 1.2 | Add tiny smoke eval set | `evals/data/smoke.jsonl` | 10-20 hand-labeled examples spanning supported/refuted/unverifiable; no proprietary data. | 1 day | Label quality. |
| 1.3 | Add runner for heuristic path | `evals/run_eval.py`, `src/tree/*` adapters | Produces `outputs/evals/<timestamp>/metrics.json` and per-claim predictions JSONL. | 1 day | Need deterministic key-disabled mode. |
| 1.4 | Add metrics calculator | `evals/metrics.py` | Reports accuracy, per-class precision/recall/F1, abstention rate, confidently-wrong rate, retrieval recall when evidence labels exist. | 1 day | Small sample means metrics are noisy; label as smoke. |
| 1.5 | Add metrics changelog | `evals/results/CHANGELOG.md` or `outputs/evals/index.jsonl` | Each run logs git SHA, config, model/fallback status, dataset, metrics, notes. | 0.5 day | Must not commit large outputs. |
| 1.6 | Add LLM-path baseline switch | `evals/run_eval.py` | Can run with Gemini key or with forced fallback; records provider/model. | 0.5 day | Cost and nondeterminism. |

Demonstrable at end: one command runs an eval and produces a metrics JSON and changelog entry for heuristic vs LLM path.

### Phase 2: parity milestone

Goal: reach narrow table-stakes parity for uploaded-document claim verification: passage evidence, directions, resolving citations, and structured per-claim output. End with a small head-to-head comparison against 1-2 existing tools on a shared claim set.

| Order | Task | Files touched | Acceptance criteria | Estimate | Risks |
| --- | --- | --- | --- | --- | --- |
| 2.1 | Add passage/chunk IDs with locations | `src/ingestion/chunker.py`, `src/ingestion/parser.py`, state models | Each extracted chunk has stable `doc_id`, `chunk_id`, char offsets, page if available. | 1-2 days | PDF page mapping may be approximate. |
| 2.2 | Add `PassageEvidence` model | `src/tree/state.py`, writer/tests | Per claim output includes quote, source id/title/url, page/offset, direction, score. | 1 day | Backward compatibility with writer. |
| 2.3 | Passage retrieval per claim | new `src/retrieval/` or `src/tree/evidence.py` | For each claim, top-k passages are retrieved from source papers/documents; retrieval recall measured on eval. | 2-3 days | Current literature pipeline stores abstracts only, not full papers. |
| 2.4 | Evidence direction classifier | `src/tree/nodes.py` or new verifier module | Each evidence item is `supporting`, `contradicting`, or `neutral`; per-claim counts are output. | 2 days | LLM prompt variance; heuristic fallback needs low confidence. |
| 2.5 | Citation link resolver | `src/literature/fetcher.py`, new `src/citations/` | Each source has a URL/DOI/OpenAlex/S2 link; liveness/existence status stored. | 1-2 days | Rate limits; DOI links may redirect. |
| 2.6 | Structured per-claim output and markdown | `src/writer/scaffold_writer.py`, maybe new fact-check writer | JSON and markdown show claim, verdict, confidence, evidence rows, direction counts, citation statuses. | 1 day | Keep output compact. |
| 2.7 | Eval parity metrics | `evals/*` | Metrics include retrieval recall, citation link resolution rate, evidence-direction accuracy. | 1 day | Need enough labels. |
| 2.8 | Head-to-head comparison | `evals/comparisons/` document | Run same small claim set through DocuCheck and 1-2 tools manually; record visible features and measured outputs where export allows. | 1-2 days | Vendor tools may not expose structured outputs; do not overclaim. |

Demonstrable at end: upload/ingest a document, see each claim with verdict, passage quote, location, supporting/contradicting/neutral counts, live citation status, and a parity comparison table.

### Phase 3: differentiation features, all measured

Goal: become visibly better on verifiability, not just another summarized report generator.

| Order | Feature | Files touched | Metric | Acceptance criteria | Estimate | Risks |
| --- | --- | --- | --- | --- | --- | --- |
| 3.1 | Citation-integrity checks | new `src/citations/integrity.py`, state/writer/evals | Citation-integrity detection rate on real vs corrupted citations | For each cited passage, output link liveness, existence in index, and support match; document citation health score is computed. | 2-3 days | Support match needs NLI/LLM; false positives. |
| 3.2 | Honest abstention policy | verifier/evals | Abstention rate, unverifiable precision/recall, confidently-wrong rate | Unverifiable is first-class; low evidence cannot become supported merely from overlap. | 1-2 days | Users may dislike more abstentions; explain clearly. |
| 3.3 | Independent reviewer/red-team node | `src/reviewer/`, graph hooks/state | Reviewer disagreement rate; error catch rate on eval | A second prompt/provider reviews claim, evidence, and verdict, returning structured agreement/disagreement/rationale. | 2 days | Multi-model cost; provider choice. |
| 3.4 | Conflict and one-sidedness detection | verifier/reviewer/evals | Conflict detection precision/recall; one-sided retrieval flag rate | Flag when retrieval finds both sides, or only one side for claims with known controversy. | 2-3 days | Requires labels for contested claims. |
| 3.5 | Source quality signals | literature/state/writer | Coverage rate for venue/citations/retraction fields; impact on correctness | Show venue, citation count, source type, optional retraction status if available. | 1-2 days | Retraction data source choice. |
| 3.6 | Exportable audit trail per verdict | writer/observability | Audit completeness rate | Every verdict has machine-readable trace: claim, retrieved passages, model prompts status, reviewer decision, citation checks. | 1-2 days | Avoid leaking secrets/prompts if public. |

Demonstrable at end: an eval report showing metric deltas per feature, plus a document-level citation health score and per-verdict audit export.

### Phase 4: product shell

Goal: make it usable as a web tool without hiding quality limitations. This phase comes after Phases 1-3 unless user interviews prove that a UI is needed earlier for data collection.

| Order | Task | Files touched | Acceptance criteria | Estimate | Risks |
| --- | --- | --- | --- | --- | --- |
| 4.1 | Event hook in graph runner | `src/tree/graph.py`, state | Graph accepts `on_event(event)` and emits node start/end plus per-claim events. Existing trace still works. | 1 day | Must not block pipeline. |
| 4.2 | JSONL logger | `src/observability/jsonl.py` | One hook writes append-only `trace.jsonl` with run_id, timestamps, event type. | 0.5 day | File locking on Windows/server. |
| 4.3 | Run folder writer | `src/runs/` | Each run gets folder with `input.json`, `output.json`, `trace.jsonl`, `status.json`, markdown outputs. | 1 day | Cleanup policy. |
| 4.4 | FastAPI background runs | `src/api/app.py` | `POST /fact-check` queues run; request returns `run_id` quickly; blocking requests code runs in background thread/process. | 2 days | Thread safety; cancellation. |
| 4.5 | Run states | API/run store | States: queued/running/done/failed; failures include safe error message. | 0.5 day | Partial outputs. |
| 4.6 | SSE progress | API/events | `GET /runs/{id}/events` streams trace/progress; per-claim events visible. | 1 day | Browser reconnect behavior. |
| 4.7 | API endpoints | API/tests | Implement `POST /research/scaffold`, `POST /fact-check`, `GET /runs/{id}`, `GET /runs/{id}/events`, `GET /runs/{id}/artifacts/{name}`. | 1-2 days | Keep Mode 1 secondary. |
| 4.8 | Minimal frontend | `web/` or `app.py` Streamlit | Upload document, show extracted claims before checking, start run, show progress timeline and results table. | 2-3 days | Avoid Next.js unless needed; Streamlit/static HTML may be enough. |
| 4.9 | Upload validation | API/parser | Size/type/filename limits enforced; rejected uploads have clear errors. | 1 day | PDF parsing edge cases. |
| 4.10 | Docker deploy | `Dockerfile`, `docker-compose.yml` | One-command local deploy; public mode disables subprocess sandbox. | 1 day | Model downloads inflate image; prefer runtime cache. |

Demonstrable at end: user uploads a document in a browser, reviews extracted claims, starts a background fact-check, watches per-claim progress, and downloads JSON/markdown audit artifacts.

### Phase 5: user validation

Goal: validate the wedge with 5-10 real users before adding accounts, billing, or collaboration.

| Order | Task | Files touched | Acceptance criteria | Estimate | Risks |
| --- | --- | --- | --- | --- | --- |
| 5.1 | Define target user script | `docs/user-research.md` | Interview guide focuses on their document workflow, trust needs, acceptable false positives/abstentions. | 0.5 day | Vague user segment. |
| 5.2 | Recruit 5-10 users | none or docs | At least five sessions with real uploaded or representative documents. | 1-2 weeks calendar | Recruiting. |
| 5.3 | Instrument feedback | product shell, docs | Capture task success, time saved, corrections, trust score, must-have requests. | 1 day | Privacy. |
| 5.4 | Decide next scope | `docs/PLAN.md` update | Evidence-based choice: improve quality, add UI affordance, or stop. | 0.5 day | Confirmation bias. |

Demonstrable at end: user-validation summary with top pain points, retention signals, and a prioritized next-build list.

---

## Eval design

### Label schema

Use JSONL, one claim per line.

```json
{
  "id": "claim_001",
  "domain": "chosen_target_domain",
  "document_id": "doc_001",
  "claim": "The intervention reduced mortality by 20%.",
  "gold_label": "supported|refuted|unverifiable",
  "gold_evidence": [
    {
      "source_id": "paper_or_doc_id",
      "source_title": "...",
      "url": "...",
      "quote": "Exact supporting or contradicting passage.",
      "location": {"page": 3, "char_start": 1200, "char_end": 1320},
      "direction": "supporting|contradicting|neutral"
    }
  ],
  "allowed_sources": ["source_id_1", "source_id_2"],
  "notes": "Why this label was chosen."
}
```

### Data sources

| Source | Use | Caveat |
| --- | --- | --- |
| SciFact | Scientific claim verification with evidence labels; good for the core wedge. | Confirm license and exact schema before importing. |
| FEVER | General claim verification for label diversity and refutation behavior. | Wikipedia domain differs from academic/document fact-checking. |
| Hand-labeled target-domain documents | Best product-fit signal. Use 20-50 initial claims from the chosen user domain. | Requires careful labeling and privacy handling. |
| Synthetic corrupted citations | Needed for citation-integrity detection: start from real citations, corrupt links/passages/claim alignment. | Must label as synthetic; do not mix with real-world accuracy metrics. |

### Metrics

| Metric | Definition | Why it matters |
| --- | --- | --- |
| Accuracy | Correct verdict / total claims | Basic headline, but not enough alone. |
| Per-class precision/recall/F1 | For supported, refuted, unverifiable | Prevents hiding bad refutation or abstention behind overall accuracy. |
| Confidently-wrong rate | Wrong predictions with confidence above chosen threshold | Resume-worthy safety metric; directly tied to trust. |
| Abstention rate | Percent predicted unverifiable | Measures honesty and utility tradeoff. |
| Unverifiable precision | Of claims marked unverifiable, how many truly lack evidence | Prevents lazy abstention. |
| Citation-integrity detection rate | Corrupted citations detected / corrupted citations | Measures differentiation feature. |
| Link resolution rate | Resolved source links / cited source links | Parity requirement. |
| Retrieval recall@k | Gold evidence passage present in top-k retrieved passages | Diagnoses retrieval vs reasoning failures. |
| Evidence-direction accuracy | Correct supporting/contradicting/neutral classification | Parity requirement. |
| Audit completeness rate | Claims with complete verdict, evidence, trace, source status | Product trust metric. |

### Baselines

| Baseline | Description | Purpose |
| --- | --- | --- |
| Current heuristic path | API keys disabled; keyword overlap fallback. | Minimum baseline; likely weak but deterministic. |
| LLM path | Gemini enabled with fixed prompt/version captured. | Measures improvement from LLM reasoning. |
| Passage retrieval only | Retrieve evidence but use simple scoring. | Separates retrieval quality from verdict reasoning. |
| Reviewer-enabled path | Main verifier plus independent reviewer. | Measures Phase 3 differentiation. |

### Metrics changelog

Every eval run should write:

- `outputs/evals/<timestamp>/config.json`: git SHA, branch, dataset, provider/model, prompt version, thresholds, environment flags.
- `outputs/evals/<timestamp>/predictions.jsonl`: claim id, prediction, confidence, evidence ids, trace id, errors/fallback flags.
- `outputs/evals/<timestamp>/metrics.json`: all metrics above.
- `outputs/evals/index.jsonl`: one summary row per run.
- `evals/results/CHANGELOG.md`: manually curated table for resume/demo: date, git SHA, dataset, major change, headline metric deltas.

Do not invent target numbers. The resume should report measured values only after this harness exists.

---

## Web architecture plan

### Event hook design

Current trace appends after node completion. Replace/extend with a single event hook:

```python
def on_event(event: PipelineEvent) -> None:
    ...
```

Event types:

- `run.queued`
- `run.started`
- `node.started`
- `node.finished`
- `claim.started`
- `claim.retrieved_evidence`
- `claim.verdict_started`
- `claim.verdict_finished`
- `claim.review_started`
- `claim.review_finished`
- `run.finished`
- `run.failed`

One hook should fan out to:

1. in-memory subscriber queue for SSE,
2. JSONL logger,
3. run-folder status writer,
4. existing final trace list.

The graph should never know about FastAPI directly. It emits events; adapters decide where they go.

### Handling blocking code in FastAPI

The current code uses blocking `requests`, local filesystem, embedding model loads, and optional subprocess/E2B calls. Do not run it in the request handler.

Smallest working design:

- FastAPI receives request and validates upload.
- It writes `input.json` and uploaded file into `outputs/runs/<run_id>/`.
- It schedules the run with `BackgroundTasks` or a bounded `ThreadPoolExecutor`.
- Request returns `202 Accepted` with `run_id`.
- Worker updates `status.json` and emits events to a per-run queue.
- SSE endpoint reads from queue and replays `trace.jsonl` on reconnect.

If multiple concurrent users appear, replace in-process background tasks with a small job queue. Do not add a database until users require it.

### API endpoints

| Endpoint | Purpose | Request | Response |
| --- | --- | --- | --- |
| `POST /fact-check` | Primary wedge: upload document and optional corpus/topic | multipart file + topic + max_claims + budget | `202 {run_id, status_url, events_url}` |
| `POST /research/scaffold` | Secondary Mode 1 | JSON topic + max_results + budget | `202 {run_id, status_url, events_url}` |
| `GET /runs/{id}` | Run metadata/status | none | status, timestamps, progress counts, artifact links, safe errors |
| `GET /runs/{id}/events` | SSE stream | none | event stream with node and per-claim progress |
| `GET /runs/{id}/output` | Final structured result | none | `output.json` |
| `GET /runs/{id}/artifacts/{name}` | Download markdown/trace | artifact name | file download if allowed |

### Per-run folder layout

```text
outputs/runs/<run_id>/
  input.json
  upload/<safe_filename>
  status.json
  trace.jsonl
  output.json
  claims.json
  evidence.jsonl
  fact_check.md
  sources.md
```

### Per-claim progress events

For web UX, emit progress after each claim, not just after each graph node:

```json
{"type":"claim.verdict_finished","run_id":"...","claim_id":"ingested_claim_3","verdict":"SUPPORTED","confidence":0.72,"evidence_count":4,"duration_ms":1830}
```

---

## Cost and safety plan

### Cost estimate approach

Do not publish fixed cost claims yet. Add instrumentation that records:

- number of extracted claims,
- retrieved passages per claim,
- prompt/input tokens per claim,
- output tokens per claim,
- reviewer tokens if enabled,
- provider/model pricing snapshot used for estimate,
- total estimated cost per document.

Initial formula:

```text
estimated_cost = sum(input_tokens / 1_000_000 * input_price_per_million)
               + sum(output_tokens / 1_000_000 * output_price_per_million)
               + external sandbox/search costs
```

Budget caps:

- Per document: max claims checked, max passages per claim, max LLM calls, max wall-clock time.
- Per run: configurable dollar cap; stop with `failed_budget_exceeded` or mark remaining claims as not checked.
- Per IP/session in public demo: request rate and daily run cap.

### Timeouts

| Component | Plan |
| --- | --- |
| External HTTP APIs | Keep explicit timeouts; expose source timeout in trace. Current `requests.get(..., timeout=30)` exists for literature APIs at `src/literature/fetcher.py:59`, `src/literature/fetcher.py:97`. |
| LLM calls | Keep per-call timeout; add retries with cap and trace fallback status. |
| Whole run | Max run duration; background worker marks failed if exceeded. |
| Per claim | Max retrieval + verification duration; claim can become `UNVERIFIABLE` with timeout reason only if product policy allows. |

### Upload validation

Before parsing:

- accept only `.pdf`, `.docx`, `.txt`, `.md` initially,
- enforce max file size,
- sanitize filename and store under generated run folder,
- inspect MIME where practical,
- cap extracted text length and page count,
- reject encrypted/password PDFs with clear error,
- never read unknown binary files through fallback in public mode,
- do not log document contents by default.

### Sandbox safety

- Public web mode must disable local subprocess sandbox. Current `_LocalExecutor` explicitly says it is not a real sandbox (`src/sandbox/executor.py:71-76`) and uses `subprocess.run` (`src/sandbox/executor.py:85`).
- For public deployment, either require E2B-only execution or disable quantitative code execution entirely for document fact-checking.
- Never execute code extracted from uploaded documents.

### Secrets handling

- Keep API keys in environment variables only.
- Never write keys to `input.json`, `trace.jsonl`, prompts, or error responses.
- Scrub exception messages before returning to users.
- Add `.env` to `.gitignore` remains necessary; do not read or print `.env` in normal operation.

---

## Resume plan

Use only measured claims after the eval harness exists.

### Target bullets and exact metrics to produce

1. **Built an evidence-grounded document fact-checking system for scientific/technical drafts, evaluating [N] claims across [DATASETS/DOMAIN] with measured accuracy [X%], per-class F1 [supported/refuted/unverifiable], and confidently-wrong rate [Y%].**
   - Metrics needed: N claims, dataset names, accuracy, per-class precision/recall/F1, confidently-wrong rate.

2. **Implemented passage-level citation verification with resolvable source links, achieving retrieval recall@k [X%], citation link resolution rate [Y%], and corrupted-citation detection rate [Z%].**
   - Metrics needed: retrieval recall@k, link resolution rate, citation-integrity detection rate on real vs corrupted citations.

3. **Added an auditable multi-stage verification pipeline with per-claim progress, independent reviewer checks, and exportable JSON/Markdown reports, improving [PRIMARY METRIC] from [A] to [B] on a fixed eval set.**
   - Metrics needed: before/after metric from eval changelog, reviewer disagreement/error-catch rate, audit completeness rate.

### README claims to trim until true

- Remove Next.js frontend and FastAPI streaming claims until Phase 4 exists.
- Remove multi-LLM ensemble claims until non-Gemini providers are implemented and tested.
- Remove ArXiv from literature ingestion until an ArXiv fetcher exists.
- Remove or update the `17 passed` badge; current local important suite is 39 passed with API keys disabled, while literature tests include slow/live integration behavior.
- Remove demo gif reference until `docs/assets/demo.gif` exists.
- Replace "every claim is verified" and "conflicting sources flagged automatically" with a narrower honest statement after Phase 0/2.

---

## Competitor notes

These notes are based on public search snippets and official-looking pages found during planning, not hands-on product testing. Do not claim a vendor feature unless verified on that vendor's own page or through a live trial.

| Tool/source | Publicly observed parity claim | What was not verified | Relevance to DocuCheck |
| --- | --- | --- | --- |
| Elicit (`https://elicit.com/`) | Public result says Elicit searches academic papers and generates structured reports with citations. | I did not verify passage-level quotes, citation liveness, per-claim verdict schemas, or exported evidence direction counts. | Parity comparison should test: citation links, structured evidence extraction, claim-level outputs. |
| Undermind (`https://www.undermind.ai/`) | Public result says it reads full texts/figures and cites every source. | I did not verify uploaded-document fact-checking, passage quotes per verdict, or contradiction counts. | Strong comparator for literature/source coverage, not necessarily document claim verification. |
| OpenAI Deep Research (`https://chatgpt.com/features/deep-research/`, `https://openai.com/index/introducing-deep-research/`) | Public result says source-based research and structured reports with citations. | I did not verify claim-by-claim verdicts, evidence direction counts, or citation-integrity checks. | Useful comparator for user expectations around cited reports; DocuCheck should differentiate on verifiability metrics. |
| Gemini Deep Research (`https://ai.google.dev/gemini-api/docs/deep-research`, `https://gemini.google/.../deep-research/`) | Public result says it plans, explores sources, and produces detailed cited reports. | I did not verify uploaded-document claim checking, structured per-claim evidence, or citation support validation. | Useful comparator because current code already uses Gemini, but product claims must distinguish DocuCheck from generic research reports. |

Parity features checked against competitors at a high level: cited reports, source-backed outputs, academic/literature search.  
Could not verify: passage-level quote+location per verdict, supporting/contradicting/neutral counts, citation liveness, source existence in an index, or support-match validation.  
Vendor claims needing confirmation from official pages/live trial: exact export formats, whether citations resolve reliably, whether uploaded documents are fact-checked claim-by-claim, and whether tools abstain honestly.

---

## Open questions for the owner

Ranked by how much each changes the plan:

1. **Target user and domain:** Is the first user a student checking essays, a researcher checking paper drafts, a journalist checking sourced claims, or a policy/medical/scientific analyst? This determines datasets, evidence sources, UI language, and acceptable abstention.
2. **Timeline:** Is the goal a resume demo in weeks, a user-facing beta in 1-2 months, or a production-grade tool? This changes how much Phase 1/2 depth is required before the web shell.
3. **LLM provider and budget:** Can the system use paid Gemini/OpenAI/Claude calls for eval and production? If not, Phase 2 must lean on open/local models and simpler heuristics.
4. **Hosting budget:** Is a public demo expected? If yes, disable local sandbox and design around small background workers, upload caps, and cost limits.
5. **Corpus source:** Should fact-checking use only the uploaded document's citations, a user-provided paper set, Semantic Scholar/OpenAlex abstracts, or full-text PDFs? Passage-level evidence depends on this.
6. **Privacy expectations:** Can uploaded documents be sent to hosted LLMs, or must processing stay local/private?
7. **Comparison tools:** Which 1-2 competitors matter most for the resume/demo: Elicit, Undermind, ChatGPT Deep Research, Gemini Deep Research, Perplexity, or something domain-specific?

---

## Recommended immediate next move

Do Phase 0 only. Specifically: write the Mode 3 regression test first, fix the claim wipeout, add a guardrail for empty successful runs, and make the README honest. Then build the eval harness before adding the web shell.
