"""
src/ingestion/__init__.py
--------------------------
Document ingestion package.

Public API
----------
    from src.ingestion.pipeline import IngestionPipeline
    from src.ingestion.parser import DocumentParser, ParsedDocument
    from src.ingestion.chunker import TextChunker, TextChunk
    from src.ingestion.claim_extractor import DocumentClaimExtractor
"""

from .pipeline import IngestionPipeline
from .parser import DocumentParser, ParsedDocument
from .chunker import TextChunker, TextChunk

__all__ = [
    "IngestionPipeline",
    "DocumentParser",
    "ParsedDocument",
    "TextChunker",
    "TextChunk",
]
