"""Phase 10b — HEMIS student/employee sync helpers uchun unit testlar.

`upsert_student`/`upsert_employee` async va DB ishlatadi — bu test'da faqat
pure helper funksiyalar (hash, classifier extractors, lang mapping) testlanadi.
Integration test alohida `tests/integration/test_hemis_sync.py`-ga qo'shiladi.
"""

from __future__ import annotations

from datetime import date

from app.modules.users.hemis_sync import (
    _classifier_code,
    _classifier_name,
    _hash,
    _hemis_lang_to_local,
    _unix_to_date,
)


# ---- _hash ----

def test_hash_stable_for_same_dict():
    a = {"id": 1, "name": "X"}
    b = {"name": "X", "id": 1}  # order farq
    assert _hash(a) == _hash(b)


def test_hash_changes_when_value_changes():
    a = _hash({"id": 1, "name": "X"})
    b = _hash({"id": 1, "name": "Y"})
    assert a != b


def test_hash_handles_unicode():
    """O'zbekcha matnlarda buzilmasligi"""
    a = _hash({"name": "O'zbekiston"})
    b = _hash({"name": "O'zbekiston"})
    assert a == b


# ---- _classifier_code / _classifier_name ----

def test_classifier_code_extracts():
    assert _classifier_code({"code": "uz", "name": "O'zbek"}) == "uz"


def test_classifier_code_none_when_not_dict():
    assert _classifier_code(None) is None
    assert _classifier_code("string") is None
    assert _classifier_code(123) is None


def test_classifier_code_none_when_no_code_field():
    assert _classifier_code({"name": "X"}) is None


def test_classifier_name_extracts():
    assert _classifier_name({"code": "uz", "name": "O'zbek"}) == "O'zbek"


# ---- _hemis_lang_to_local ----

def test_lang_uz_lat():
    assert _hemis_lang_to_local("uz") == "uz-lat"
    assert _hemis_lang_to_local("UZ") == "uz-lat"
    assert _hemis_lang_to_local("uz-Latn") == "uz-lat"
    assert _hemis_lang_to_local("uz_latn") == "uz-lat"


def test_lang_uz_cyr():
    assert _hemis_lang_to_local("uz-cyrl") == "uz-cyr"
    assert _hemis_lang_to_local("uz_cyrl") == "uz-cyr"


def test_lang_ru_en():
    assert _hemis_lang_to_local("ru") == "ru"
    assert _hemis_lang_to_local("en") == "en"


def test_lang_unknown():
    assert _hemis_lang_to_local("fr") is None
    assert _hemis_lang_to_local(None) is None
    assert _hemis_lang_to_local("") is None


# ---- _unix_to_date ----

def test_unix_to_date_valid():
    # 2000-01-01 00:00 UTC = 946684800
    d = _unix_to_date(946684800)
    assert d == date(2000, 1, 1)


def test_unix_to_date_none():
    assert _unix_to_date(None) is None
    assert _unix_to_date(0) is None  # falsy → None


def test_unix_to_date_invalid():
    # Too large — overflow
    assert _unix_to_date(99999999999999) is None
