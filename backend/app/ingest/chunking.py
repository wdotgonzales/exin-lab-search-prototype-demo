"""Cut extracted sections into ~500-token chunks for search and citation.

Why chunks: an embedding of a whole 30-page file is too blurry to match a
specific question, and the chat can only quote a few short passages. So we
embed and cite pieces instead.

Rules:
- A chunk never crosses a section, so its page number is exact.
- We cut at paragraph boundaries first, then lines, then sentences, and only
  split mid-sentence when one sentence alone is too long.
- Consecutive chunks overlap by ~50 tokens, so a fact that sits on a boundary
  still appears whole in at least one chunk.
- A section label (e.g. "Sheet: Weights") is repeated at the top of every
  chunk, so each chunk makes sense on its own.
"""

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.ingest.extract import Section

MAX_TOKENS = 500
OVERLAP_TOKENS = 50

# OpenAI's rule of thumb: ~4 characters per token for English text. Exact
# counts don't matter here: chunks only need to be "about 500" and stay far
# below the embedding model's 8,191-token limit. Swap in tiktoken here if
# exact counts are ever needed.
CHARS_PER_TOKEN = 4


def count_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


@dataclass(frozen=True)
class ChunkDraft:
    index: int
    content: str
    token_count: int
    page: int | None


def chunk_sections(
    sections: Iterable[Section],
    max_tokens: int = MAX_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    for section in sections:
        prefix = f"{section.label}\n" if section.label else ""
        budget = max_tokens - count_tokens(prefix)
        for body in _pack(_units(section.text, budget), budget, overlap_tokens):
            content = prefix + body
            drafts.append(
                ChunkDraft(len(drafts), content, count_tokens(content), section.page)
            )
    return drafts


def _units(text: str, budget: int) -> list[str]:
    """Split text into pieces that each fit the budget, keeping them as
    large and natural as possible."""
    units: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if count_tokens(para) <= budget:
            units.append(para)
            continue
        for line in para.split("\n"):
            for sentence in re.split(r"(?<=[.!?])\s+", line.strip()):
                if sentence:
                    units.extend(_hard_split(sentence, budget))
    return units


def _hard_split(text: str, budget: int) -> list[str]:
    """Last resort for one very long sentence: split between words, and
    inside a word only if a single 'word' is itself too long."""
    if count_tokens(text) <= budget:
        return [text]
    limit = budget * CHARS_PER_TOKEN
    pieces: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > limit:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:limit])
            word = word[limit:]
        candidate = f"{current} {word}" if current else word
        if len(candidate) > limit:
            pieces.append(current)
            current = word
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def _pack(units: list[str], budget: int, overlap: int) -> list[str]:
    """Greedily fill chunks with whole units, starting each new chunk with
    the last few units of the previous one (the overlap)."""

    def size(parts: list[str]) -> int:
        return count_tokens("\n".join(parts))

    chunks: list[str] = []
    current: list[str] = []
    for unit in units:
        if current and size([*current, unit]) > budget:
            chunks.append("\n".join(current))
            tail: list[str] = []
            for prev in reversed(current):
                if size([prev, *tail]) > overlap:
                    break
                tail.insert(0, prev)
            current = tail if size([*tail, unit]) <= budget else []
        current.append(unit)
    if current:
        chunks.append("\n".join(current))
    return chunks
