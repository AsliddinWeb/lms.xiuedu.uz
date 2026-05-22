"""Phase 10f — HEMIS data sync uchun unit testlar.

`run_sync` dispatcher pure logic — `SUPPORTED_SYNC_TYPES` ro'yxati,
`ValueError` on unknown entity. To'liq DB integration testi alohida
(integration suite'da).
"""

from __future__ import annotations

import pytest

from app.integrations.hemis.data_sync import SUPPORTED_SYNC_TYPES, run_sync


def test_supported_sync_types_complete():
    """Hozir ko'rsatilgan 4 entity sync qilinishi mumkin."""
    assert set(SUPPORTED_SYNC_TYPES) == {"students", "employees", "departments", "groups"}


@pytest.mark.asyncio
async def test_run_sync_rejects_unknown_entity():
    """Yo'q bo'lgan entity → ValueError."""
    with pytest.raises(ValueError, match="Unknown sync entity"):
        await run_sync(None, "unknown_entity")  # type: ignore[arg-type]


def test_supported_entities_strings_lowercase():
    """Entity nomlari konsistent: lowercase, plural."""
    for e in SUPPORTED_SYNC_TYPES:
        assert e.islower()
        assert e.endswith("s")
