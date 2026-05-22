"""Pure-Python TF-IDF + cosine similarity — Phase 9e.

Hech qanday tashqi kutubxonaga muhtoj emas. Qisqa/o'rta matnlar uchun
(essay, code, short_text) maqbul natija beradi. Production'da
`sentence-transformers` semantic similarity bilan almashtirish mumkin
(uzbek tilini ham qo'llaydi).

Foydalanish:
    score = similarity_score(text_a, text_b)   # 0..1
    pct = float(score) * 100  # foiz
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable

# Uzbek/Russian/English stopwords — frequent words filtered out
STOPWORDS: frozenset[str] = frozenset(
    {
        # Uzbek (lat)
        "va", "lekin", "ammo", "biroq", "bilan", "uchun", "ham", "ham,", "ham.",
        "yoki", "agar", "bu", "shu", "u", "men", "siz", "biz", "ular", "u'",
        "ko'p", "kam", "qancha", "hech", "bir", "ikki", "uch", "to'rt", "besh",
        "qaysi", "qachon", "qaerda", "nima", "nega", "qanday", "albatta",
        # Uzbek (cyr)
        "ва", "лекин", "аммо", "бироқ", "билан", "учун", "ҳам", "ёки", "агар",
        "бу", "шу", "у", "мен", "сиз", "биз", "улар", "бир", "икки", "уч",
        # Russian
        "и", "в", "не", "на", "что", "он", "она", "оно", "они", "как", "это",
        "с", "по", "о", "за", "от", "к", "у", "до", "из", "так", "но", "если",
        # English
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "and", "or", "but", "if", "then", "of", "to", "in", "on", "at", "by",
        "for", "with", "as", "this", "that", "these", "those", "i", "you",
        "he", "she", "it", "we", "they", "have", "has", "had", "do", "does",
        "did", "will", "would", "can", "could", "may", "might", "should",
    }
)


def _tokenize(text: str) -> list[str]:
    """Lower-case + word boundary split (Unicode-friendly)."""
    # Saqlash uchun: letters + digits (Unicode), underscore yo'q
    tokens = re.findall(r"[\w']+", text.lower(), flags=re.UNICODE)
    return [t for t in tokens if t and len(t) > 1 and t not in STOPWORDS]


def _term_freq(tokens: list[str]) -> Counter[str]:
    return Counter(tokens)


def _idf(documents: list[list[str]]) -> dict[str, float]:
    """IDF over a corpus: log(N / (1 + df))."""
    n = len(documents)
    df: Counter[str] = Counter()
    for doc in documents:
        for term in set(doc):
            df[term] += 1
    return {term: math.log((n + 1) / (1 + cnt)) + 1.0 for term, cnt in df.items()}


def _tfidf_vec(tf: Counter[str], idf: dict[str, float]) -> dict[str, float]:
    return {term: count * idf.get(term, 0.0) for term, count in tf.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a.keys() & b.keys())
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def similarity_score(text_a: str, text_b: str) -> float:
    """Ikki matn orasidagi TF-IDF cosine similarity (0..1).

    `text_a` va `text_b` qisqa bo'lsa (1-3 so'z), natija past chiqishi normal.
    """
    if not text_a or not text_b:
        return 0.0
    a = _tokenize(text_a)
    b = _tokenize(text_b)
    if not a or not b:
        return 0.0
    idf = _idf([a, b])
    va = _tfidf_vec(_term_freq(a), idf)
    vb = _tfidf_vec(_term_freq(b), idf)
    return _cosine(va, vb)


def best_match(
    candidate: str, corpus: Iterable[tuple[int, str]]
) -> tuple[int | None, float]:
    """`candidate` matnini `corpus` (id, text) bilan solishtirib eng yaqinini topadi.

    Returns (best_id, score). corpus bo'sh bo'lsa (None, 0).
    """
    candidate_tokens = _tokenize(candidate)
    if not candidate_tokens:
        return None, 0.0
    corpus_list = [(i, _tokenize(t)) for i, t in corpus if t]
    corpus_list = [(i, toks) for i, toks in corpus_list if toks]
    if not corpus_list:
        return None, 0.0
    all_docs = [candidate_tokens] + [toks for _, toks in corpus_list]
    idf = _idf(all_docs)
    cand_vec = _tfidf_vec(_term_freq(candidate_tokens), idf)
    best_id: int | None = None
    best_score = 0.0
    for i, toks in corpus_list:
        vec = _tfidf_vec(_term_freq(toks), idf)
        score = _cosine(cand_vec, vec)
        if score > best_score:
            best_score = score
            best_id = i
    return best_id, best_score
