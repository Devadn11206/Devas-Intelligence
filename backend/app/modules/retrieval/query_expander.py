"""Domain-Aware Technical Query Expander.

Provides deterministic, sub-5ms acronym expansion and technical term enrichment
across AI, Scientific Machine Learning (SciML), and Systems Engineering.
"""

import re
from typing import Dict, List, Set, Tuple


TECHNICAL_GLOSSARY: Dict[str, List[str]] = {
    # Scientific Machine Learning (SciML) & Differential Equations
    "pinn": [
        "physics-informed neural networks",
        "partial differential equations",
        "deepxde",
    ],
    "pinns": [
        "physics-informed neural networks",
        "partial differential equations",
        "deepxde",
    ],
    "physics-informed neural networks": ["pinn", "pinns", "partial differential equations"],
    "fno": [
        "fourier neural operator",
        "neural operators",
    ],
    "fnos": [
        "fourier neural operator",
        "neural operators",
    ],
    "fourier neural operator": ["fno", "neural operators"],
    "neural operators": ["fno", "fourier neural operator", "deeponet"],
    "nlse": [
        "nonlinear schrodinger equation",
        "optical fiber wave",
    ],
    "hnls": [
        "nonlinear schrodinger equation",
        "higher-order nonlinear schrodinger",
        "optical fiber wave",
    ],
    "nonlinear schrodinger equation": ["nlse", "hnls", "solitons", "optical fiber wave"],

    # Graph Neural Networks & Spatio-Temporal Modeling
    "gnn": [
        "graph neural network",
        "message passing neural network",
    ],
    "gnns": [
        "graph neural network",
        "message passing neural network",
    ],
    "graph neural network": ["gnn", "message passing neural network"],
    "st-gnn": [
        "spatio-temporal graph neural network",
        "spatial temporal graph neural network",
    ],
    "stgnn": [
        "spatio-temporal graph neural network",
        "spatial temporal graph neural network",
    ],
    "spatio-temporal graph neural network": ["st-gnn", "stgnn", "traffic forecasting"],

    # Large Language Models & Post-Training
    "llm": [
        "large language model",
    ],
    "llms": [
        "large language model",
        "large language models",
    ],
    "large language model": ["llm", "llms"],
    "rag": [
        "retrieval-augmented generation",
    ],
    "retrieval-augmented generation": ["rag", "vector search", "hybrid retrieval"],
    "vllm": [
        "pagedattention",
        "llm inference",
        "kv cache",
    ],
    "pagedattention": ["vllm", "kv cache", "llm inference"],
    "moe": [
        "mixture of experts",
    ],
    "mixture of experts": ["moe", "sparse gating"],
    "rlhf": [
        "reinforcement learning post-training",
        "reinforcement learning from human feedback",
        "preference optimization",
    ],
    "dpo": [
        "direct preference optimization",
        "reinforcement learning post-training",
        "preference optimization",
    ],
    "grpo": [
        "group relative policy optimization",
        "reinforcement learning post-training",
        "preference optimization",
    ],
    "preference optimization": ["dpo", "grpo", "rlhf"],

    # Sensing & Systems
    "imu": [
        "inertial measurement unit",
        "human activity recognition",
        "accelerometer gyroscope",
    ],
    "har": [
        "human activity recognition",
        "inertial measurement unit",
    ],
    "human activity recognition": ["har", "imu", "inertial measurement unit"],
    "inertial measurement unit": ["imu", "har", "accelerometer"],
}


def expand_technical_query(query: str) -> Dict[str, any]:
    """Expands technical acronyms and domain terms deterministically in < 5ms.

    Returns:
        dict containing:
            - original_query: str
            - expanded_terms: List[str]
            - lexical_query: str (formatted for tsquery / ILIKE / tags)
            - semantic_query: str (enriched prompt for dense embedding)
    """
    if not query or not query.strip():
        return {
            "original_query": query,
            "expanded_terms": [],
            "lexical_query": query,
            "semantic_query": query,
        }

    clean_q = query.strip()
    lowered = clean_q.lower()

    # Extract distinct alphanumeric token words
    tokens = re.findall(r"[a-zA-Z0-9_\-\.]+", lowered)

    expanded_terms_set: Set[str] = set()

    # 1. Exact phrase check against technical glossary
    if lowered in TECHNICAL_GLOSSARY:
        for term in TECHNICAL_GLOSSARY[lowered]:
            expanded_terms_set.add(term)

    # 2. Token-by-token check
    for token in tokens:
        # Check standard token
        if token in TECHNICAL_GLOSSARY:
            for term in TECHNICAL_GLOSSARY[token]:
                expanded_terms_set.add(term)
        # Check stripped token without punctuation
        token_strip = token.strip(".-_")
        if token_strip in TECHNICAL_GLOSSARY:
            for term in TECHNICAL_GLOSSARY[token_strip]:
                expanded_terms_set.add(term)

    # Filter out anything identical to the original query
    expanded_terms = [t for t in sorted(expanded_terms_set) if t != lowered]

    # Build enriched lexical search string
    # E.g. "PINNs (physics-informed neural networks OR partial differential equations)"
    if expanded_terms:
        # For lexical search, quote multi-word phrases
        lexical_parts = [clean_q]
        for t in expanded_terms:
            if " " in t:
                lexical_parts.append(f'"{t}"')
            else:
                lexical_parts.append(t)
        lexical_query = " OR ".join(lexical_parts)
        semantic_query = f"{clean_q} ({', '.join(expanded_terms[:4])})"
    else:
        lexical_query = clean_q
        semantic_query = clean_q

    return {
        "original_query": clean_q,
        "expanded_terms": expanded_terms,
        "lexical_query": lexical_query,
        "semantic_query": semantic_query,
    }
