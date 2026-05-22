"""Content modeli — Phase 3a (qayta foydalaniluvchi o'quv kontenti).

Spec: docs/03-modules/05-content.md (soddalashtirilgan MVP versiyasi).

ContentItem — o'qituvchi tomonidan yaratiladigan atomik kontent birligi:
- text  : matnli material (rich-text, JSON ko'rinishida `content_data`'da)
- video : video fayl yoki URL (file_url + duration_seconds)
- pdf   : PDF hujjat (file_url, mime application/pdf)
- file  : ixtiyoriy fayl (slayd, arxiv, kod va h.k.)
- link  : tashqi havola (file_url URL sifatida ishlatiladi)

Phase 3b'da Lesson modeli content_item_id orqali ContentItem'larni o'ziga
biriktiradi (versionlash + qayta foydalanish uchun shu sxema saqlanadi).

Phase 3+ ga ko'chirilgan elementlar (TZ § 06-content):
- HLS transcoding pipeline (Phase 5)
- SCORM player + xAPI/LRS (Phase 10)
- OpenSearch indeksatsiyasi (Phase 11)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, SoftDeleteMixin, TimestampMixin


class ContentItem(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Atomik o'quv kontenti (qayta foydalanish uchun).

    Statuslar:
        draft     — yaratilgan, hali tekshiruvga yuborilmagan
        review    — nazoratga yuborilgan (kafedra/dekan)
        published — tasdiqlangan, lessonlarda ishlatish mumkin
        archived  — chiqarib qo'yilgan (eski versiya)

    Versionlash: `parent_id` orqali ChainOfVersions hosil bo'ladi
    (yangi `version` raqami bilan nusxa olinganda).
    """

    __tablename__ = "content_items"

    # Type: text | video | pdf | file | link
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Akademik bog'lanish — fan ixtiyoriy (ko'pgina kontent fan-bog'liq, lekin
    # umumiy resurslar ham bo'lishi mumkin: brand kit, kirish darslari va h.k.).
    subject_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("subjects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    author_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Fayl/URL ma'lumoti — type ga qarab to'ldiriladi.
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Rich-text (text type uchun) yoki qo'shimcha metadata (JSON erkin).
    content_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    language: Mapped[str] = mapped_column(String(10), default="uz-lat", nullable=False)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), default=list, nullable=False
    )

    # Versionlash
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("content_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Workflow status
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    author = relationship(
        "User",
        primaryjoin="ContentItem.author_id == User.id",
        foreign_keys=[author_id],
        lazy="selectin",
    )
    subject = relationship(
        "Subject",
        primaryjoin="ContentItem.subject_id == Subject.id",
        foreign_keys=[subject_id],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<ContentItem id={self.id} type={self.type} status={self.status}>"
