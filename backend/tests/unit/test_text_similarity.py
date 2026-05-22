"""Phase 9e — TF-IDF + cosine similarity unit testlari."""

from __future__ import annotations

from app.core.text_similarity import best_match, similarity_score


def test_identical_texts_high():
    s = similarity_score("Algoritm — bu aniq qadamlar ketma-ketligi.", "Algoritm — bu aniq qadamlar ketma-ketligi.")
    assert s > 0.95


def test_completely_different_low():
    s = similarity_score(
        "Quyosh tizimida sakkizta sayyora bor.",
        "Hammurapi qonunlari milodgacha 1750-yilda yozilgan.",
    )
    assert s < 0.2


def test_partial_overlap_medium():
    s = similarity_score(
        "Python dasturlash tili ob'ektga yo'naltirilgan.",
        "Python tili ob'ektga yo'naltirilgan dastur yozish uchun ishlatiladi.",
    )
    assert 0.3 < s < 0.95


def test_empty_returns_zero():
    assert similarity_score("", "anything") == 0.0
    assert similarity_score("anything", "") == 0.0


def test_best_match_picks_closest():
    candidate = "Algoritm bu aniq qadamlar to'plami"
    corpus = [
        (1, "Quyosh juda issiq"),
        (2, "Algoritm — aniq qadamlar ketma-ketligi"),
        (3, "Hech qanday algoritmga aloqasi yo'q matn"),
    ]
    best_id, score = best_match(candidate, corpus)
    assert best_id == 2
    assert score > 0.3


def test_best_match_empty_corpus():
    best_id, score = best_match("any text", [])
    assert best_id is None
    assert score == 0.0


def test_case_insensitive():
    s1 = similarity_score("ALGORITHM", "algorithm")
    assert s1 > 0.9
