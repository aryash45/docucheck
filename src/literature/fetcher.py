"""
Literature fetcher: Semantic Scholar + OpenAlex with FAISS local cache.
Fetches top 50 cited papers for a domain, caches embeddings locally.
"""

import os
import json
import time
import hashlib
import logging
import requests
import numpy as np
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    paper_id: str
    title: str
    abstract: str
    authors: list[str]
    year: int
    citation_count: int
    source: str  # "semantic_scholar" or "openAlex"
    url: str

    def to_text(self) -> str:
        """Convert to text for embedding."""
        return f"{self.title}. {self.abstract}"


class SemanticScholarFetcher:
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        if self.api_key and self.api_key.startswith("your_"):
            self.api_key = None
        self.headers = {}
        if self.api_key:
            self.headers["x-api-key"] = self.api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def search(self, query: str, limit: int = 50) -> list[Paper]:
        """Search for papers by query, sorted by citation count."""
        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": "paperId,title,abstract,authors,year,citationCount,externalIds",
            "sort": "citationCount:desc"
        }

        resp = requests.get(url, params=params, headers=self.headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        papers = []
        for item in data.get("data", []):
            if not item.get("abstract"):
                continue
            papers.append(Paper(
                paper_id=item["paperId"],
                title=item.get("title", ""),
                abstract=item.get("abstract", ""),
                authors=[a["name"] for a in item.get("authors", [])],
                year=item.get("year") or 0,
                citation_count=item.get("citationCount") or 0,
                source="semantic_scholar",
                url=f"https://www.semanticscholar.org/paper/{item['paperId']}"
            ))

        logger.info(f"SemanticScholar: fetched {len(papers)} papers for '{query}'")
        return papers


class OpenAlexFetcher:
    BASE_URL = "https://api.openalex.org"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def search(self, query: str, limit: int = 50) -> list[Paper]:
        """Search OpenAlex for papers."""
        url = f"{self.BASE_URL}/works"
        params = {
            "search": query,
            "per-page": min(limit, 200),
            "sort": "cited_by_count:desc",
            "filter": "has_abstract:true",
            "select": "id,title,abstract_inverted_index,authorships,publication_year,cited_by_count,doi"
        }

        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        papers = []
        for item in data.get("results", []):
            abstract = self._reconstruct_abstract(item.get("abstract_inverted_index"))
            if not abstract:
                continue

            authors = [
                a["author"]["display_name"]
                for a in item.get("authorships", [])
                if a.get("author")
            ]

            doi = item.get("doi", "")
            papers.append(Paper(
                paper_id=item["id"].split("/")[-1],
                title=item.get("title", ""),
                abstract=abstract,
                authors=authors,
                year=item.get("publication_year") or 0,
                citation_count=item.get("cited_by_count") or 0,
                source="openAlex",
                url=doi or item["id"]
            ))

        logger.info(f"OpenAlex: fetched {len(papers)} papers for '{query}'")
        return papers

    def _reconstruct_abstract(self, inverted_index: Optional[dict]) -> str:
        """OpenAlex stores abstracts as inverted index — reconstruct to text."""
        if not inverted_index:
            return ""
        positions = {}
        for word, pos_list in inverted_index.items():
            for pos in pos_list:
                positions[pos] = word
        return " ".join(positions[i] for i in sorted(positions.keys()))


class FAISSCache:
    """Local FAISS cache for paper embeddings — avoids re-embedding on repeat runs."""

    def __init__(self, cache_dir: str = "cache/faiss"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._embedder = None

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedder

    def _cache_key(self, query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()

    def get(self, query: str) -> Optional[list[Paper]]:
        key = self._cache_key(query)
        meta_path = self.cache_dir / f"{key}_meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                data = json.load(f)
            logger.info(f"FAISS cache hit for '{query}'")
            return [Paper(**p) for p in data["papers"]]
        return None

    def set(self, query: str, papers: list[Paper]):
        """Cache papers and their embeddings."""
        import faiss
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        key = self._cache_key(query)

        # Embed all paper texts
        embedder = self._get_embedder()
        texts = [p.to_text() for p in papers]
        embeddings = embedder.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings).astype("float32")

        # Build FAISS index
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)  # inner product = cosine on normalized vecs
        faiss.normalize_L2(embeddings)
        index.add(embeddings)

        # Save index
        faiss.write_index(index, str(self.cache_dir / f"{key}.index"))

        # Save metadata
        meta = {"query": query, "papers": [asdict(p) for p in papers]}
        with open(self.cache_dir / f"{key}_meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Cached {len(papers)} papers + FAISS index for '{query}'")

    def semantic_search(self, query: str, search_query: str, top_k: int = 10) -> list[Paper]:
        """Find most relevant papers from cache using semantic search."""
        import faiss
        key = self._cache_key(query)
        index_path = self.cache_dir / f"{key}.index"
        meta_path = self.cache_dir / f"{key}_meta.json"

        if not index_path.exists():
            return []

        index = faiss.read_index(str(index_path))
        with open(meta_path) as f:
            papers = [Paper(**p) for p in json.load(f)["papers"]]

        embedder = self._get_embedder()
        q_emb = embedder.encode([search_query]).astype("float32")
        faiss.normalize_L2(q_emb)

        scores, indices = index.search(q_emb, min(top_k, len(papers)))
        return [papers[i] for i in indices[0] if i >= 0]


class LiteraturePipeline:
    """
    Main entry point. Fetches from Semantic Scholar + OpenAlex,
    deduplicates, caches in FAISS, returns domain digest.
    """

    def __init__(self, cache_dir: str = "cache/faiss"):
        self.ss = SemanticScholarFetcher()
        self.oa = OpenAlexFetcher()
        self.cache = FAISSCache(cache_dir)

    def fetch(self, query: str, limit_per_source: int = 25) -> list[Paper]:
        """Fetch papers, deduplicate, cache, return sorted by citations."""
        # Check cache first
        cached = self.cache.get(query)
        if cached:
            return cached

        # Fetch from both sources
        ss_papers = []
        oa_papers = []

        try:
            ss_papers = self.ss.search(query, limit=limit_per_source)
            time.sleep(1)  # rate limit
        except Exception as e:
            logger.warning(f"SemanticScholar failed: {e}")

        try:
            oa_papers = self.oa.search(query, limit=limit_per_source)
        except Exception as e:
            logger.warning(f"OpenAlex failed: {e}")

        # Deduplicate by title similarity
        all_papers = self._deduplicate(ss_papers + oa_papers)

        # Sort by citation count
        all_papers.sort(key=lambda p: p.citation_count, reverse=True)
        all_papers = all_papers[:50]  # top 50

        # Cache
        if all_papers:
            self.cache.set(query, all_papers)

        return all_papers

    def generate_digest(self, papers: list[Paper], max_papers: int = 10) -> str:
        """Generate 1-page domain digest from top papers."""
        top = papers[:max_papers]
        lines = ["# Domain Digest\n"]
        for i, p in enumerate(top, 1):
            lines.append(f"## {i}. {p.title} ({p.year})")
            lines.append(f"**Citations:** {p.citation_count} | **Source:** {p.source}")
            lines.append(f"**Authors:** {', '.join(p.authors[:3])}")
            abstract_preview = p.abstract[:300] + "..." if len(p.abstract) > 300 else p.abstract
            lines.append(f"**Abstract:** {abstract_preview}")
            lines.append(f"**URL:** {p.url}\n")
        return "\n".join(lines)

    def _deduplicate(self, papers: list[Paper]) -> list[Paper]:
        """Remove duplicates by normalized title."""
        seen = set()
        unique = []
        for p in papers:
            key = p.title.lower().strip().replace(" ", "")[:50]
            if key not in seen and p.title:
                seen.add(key)
                unique.append(p)
        return unique