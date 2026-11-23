import re
from typing import List, Set


def normalize_github_url(url: str) -> str:
    """Normalizes GitHub repository URLs to standard https://github.com/{owner}/{repo}."""
    if not url:
        return ""
    # Strip protocol and leading www.
    cleaned = re.sub(r"^https?://(www\.)?github\.com/", "", url.strip(), flags=re.IGNORECASE)
    # Strip trailing .git
    cleaned = re.sub(r"\.git$", "", cleaned, flags=re.IGNORECASE)
    # Strip subpaths like /tree/main, /blob/master, /issues, etc.
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) >= 2:
        owner = parts[0].strip().lower()
        repo = parts[1].strip().lower()
        return f"https://github.com/{owner}/{repo}"
    return ""


def extract_github_urls(text: str) -> List[str]:
    """Finds all GitHub repository URLs in text."""
    if not text:
        return []
    # Match github.com/owner/repo patterns
    pattern = re.compile(
        r"https?://(?:www\.)?github\.com/[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+",
        re.IGNORECASE,
    )
    matches = pattern.findall(text)
    normalized: Set[str] = set()
    for m in matches:
        norm = normalize_github_url(m)
        if norm:
            normalized.add(norm)
    return sorted(list(normalized))


def normalize_huggingface_url(url: str) -> str:
    """Normalizes Hugging Face model/dataset URLs to https://huggingface.co/{org}/{model}."""
    if not url:
        return ""
    cleaned = re.sub(r"^https?://(www\.)?huggingface\.co/", "", url.strip(), flags=re.IGNORECASE)
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) >= 2:
        org = parts[0].strip().lower()
        model = parts[1].strip().lower()
        return f"https://huggingface.co/{org}/{model}"
    elif len(parts) == 1:
        return f"https://huggingface.co/{parts[0].strip().lower()}"
    return ""


def extract_huggingface_urls(text: str) -> List[str]:
    """Finds all Hugging Face URLs in text."""
    if not text:
        return []
    pattern = re.compile(
        r"https?://(?:www\.)?huggingface\.co/[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+",
        re.IGNORECASE,
    )
    matches = pattern.findall(text)
    normalized: Set[str] = set()
    for m in matches:
        norm = normalize_huggingface_url(m)
        if norm:
            normalized.add(norm)
    return sorted(list(normalized))


def normalize_arxiv_id(raw_id: str) -> str:
    """Normalizes arXiv IDs (e.g. '2403.12345v2' or 'arXiv:2403.12345' -> '2403.12345')."""
    if not raw_id:
        return ""
    clean = raw_id.strip()
    if "/abs/" in clean:
        clean = clean.split("/abs/")[-1]
    # Remove prefix 'arxiv:'
    clean = re.sub(r"^arxiv:\s*", "", clean, flags=re.IGNORECASE)
    # Strip version suffix 'v1', 'v2'
    if "v" in clean and clean.rsplit("v", 1)[-1].isdigit():
        clean = clean.rsplit("v", 1)[0]
    return clean.strip().lower()


def extract_arxiv_ids(text: str) -> List[str]:
    """Extracts valid arXiv identifiers from text (YYMM.NNNNN or legacy math/0211111)."""
    if not text:
        return []
    # Pattern 1: standard modern arXiv ID: e.g. 2401.12345 or 2401.12345v1
    pattern_modern = re.compile(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b", re.IGNORECASE)
    # Pattern 2: explicit arXiv:YYMM.NNNNN
    pattern_explicit = re.compile(r"arxiv:\s*([a-zA-Z\-]+/\d{7}|\d{4}\.\d{4,5}(?:v\d+)?)", re.IGNORECASE)

    found: Set[str] = set()
    for m in pattern_explicit.findall(text):
        norm = normalize_arxiv_id(m)
        if norm:
            found.add(norm)

    for m in pattern_modern.findall(text):
        norm = normalize_arxiv_id(m)
        if norm:
            found.add(norm)

    return sorted(list(found))
