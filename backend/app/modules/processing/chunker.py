import re
import html
from typing import List, Tuple
from pydantic import BaseModel, Field


class TextChunk(BaseModel):
    chunk_index: int
    section_type: str
    content: str
    token_count: int


def clean_text(text: str) -> str:
    """Cleans HTML entities, removes script/style noise, and normalizes whitespace."""
    if not text:
        return ""
    # Unescape HTML entities
    cleaned = html.unescape(text)
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    # Remove control characters except newline and tab
    cleaned = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", cleaned)
    # Normalize multiple whitespaces per line
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.splitlines()]
    # Normalize excessive empty lines
    cleaned = "\n".join(line for line in lines if line)
    return cleaned.strip()


def estimate_token_count(text: str) -> int:
    """Estimates tokens based on whitespace words and punctuation heuristics (~1.3 tokens/word)."""
    words = text.split()
    return max(1, int(len(words) * 1.3))


def chunk_document(
    title: str,
    summary_raw: str,
    content_raw: str | None = None,
    content_type: str = "paper",
    target_words: int = 350,  # ~450 words / ~600 tokens
    overlap_words: int = 45,  # ~60 tokens
) -> List[TextChunk]:
    """Splits document content into section-aware overlapping chunks preserving provenance."""
    chunks: List[TextChunk] = []
    chunk_index = 0

    clean_title = clean_text(title)
    clean_summary = clean_text(summary_raw)
    clean_body = clean_text(content_raw or "")

    # Always create an overview/abstract chunk as chunk 0
    abstract_section = "abstract" if content_type == "paper" else ("readme" if content_type == "repo" else "overview")
    overview_text = f"Title: {clean_title}\n\nSummary:\n{clean_summary}" if clean_summary else clean_title

    chunks.append(
        TextChunk(
            chunk_index=chunk_index,
            section_type=abstract_section,
            content=overview_text,
            token_count=estimate_token_count(overview_text),
        )
    )
    chunk_index += 1

    # If body text exists and is longer than summary, chunk body
    if clean_body and clean_body != clean_summary:
        # Detect sections if markdown headers present
        sections: List[Tuple[str, str]] = []
        current_section = "article_body"
        if content_type == "paper":
            current_section = "methodology"
        elif content_type == "repo":
            current_section = "readme"

        # Split on markdown headers (# Section or ## Section)
        header_pattern = re.compile(r"^(#{1,3}\s+.*)$", re.MULTILINE)
        parts = header_pattern.split(clean_body)

        if len(parts) > 1:
            for part in parts:
                part_clean = part.strip()
                if not part_clean:
                    continue
                if part_clean.startswith("#"):
                    header_title = part_clean.lstrip("#").strip().lower()
                    if "abstract" in header_title:
                        current_section = "abstract"
                    elif "method" in header_title or "architecture" in header_title or "approach" in header_title:
                        current_section = "methodology"
                    elif "result" in header_title or "benchmark" in header_title or "evaluation" in header_title:
                        current_section = "results"
                    elif "limit" in header_title or "conclusion" in header_title or "discussion" in header_title:
                        current_section = "limitations"
                    else:
                        current_section = "article_body"
                else:
                    sections.append((current_section, part_clean))
        else:
            sections.append((current_section, clean_body))

        # Chunk each section with sliding window
        for sec_type, sec_text in sections:
            words = sec_text.split()
            if not words:
                continue

            if len(words) <= target_words:
                chunk_str = f"[{sec_type.upper()}]\n{sec_text}"
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        section_type=sec_type,
                        content=chunk_str,
                        token_count=estimate_token_count(chunk_str),
                    )
                )
                chunk_index += 1
            else:
                step = target_words - overlap_words
                for start_idx in range(0, len(words), step):
                    window = words[start_idx : start_idx + target_words]
                    chunk_text = " ".join(window)
                    chunk_str = f"[{sec_type.upper()}]\n{chunk_text}"
                    chunks.append(
                        TextChunk(
                            chunk_index=chunk_index,
                            section_type=sec_type,
                            content=chunk_str,
                            token_count=estimate_token_count(chunk_str),
                        )
                    )
                    chunk_index += 1
                    if start_idx + target_words >= len(words):
                        break

    return chunks
