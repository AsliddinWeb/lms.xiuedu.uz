"""SCORM `imsmanifest.xml` parser — Phase 11a.

SCORM 1.2 va SCORM 2004 manifestlarni parse qiladi. Asosiy ma'lumotlar:
    - SCORM version
    - manifest_identifier
    - title
    - launch_url (first <resource type='webcontent' href='...'>)
    - mastery_score (faqat SCORM 1.2)

Boshqa elementlar (sequencing, prerequisites) hozircha skip qilinadi —
oddiy linear flow uchun launch_url yetarli.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ParsedManifest:
    version: str  # '1.2' | '2004'
    manifest_identifier: str | None
    title: str | None
    description: str | None
    launch_url: str  # relative to ZIP root, e.g. 'shared/launchpage.html'
    mastery_score: Decimal | None


class ManifestParseError(Exception):
    """imsmanifest.xml parse qilib bo'lmadi."""


# SCORM namespace prefiksi turli versiyalarda farq qiladi
_NS_HINTS = {
    "imscp": "imscp",
    "ims": "ims",
    "adlcp": "adlcp",
}


def _strip_ns(tag: str) -> str:
    """`{namespace}element` → `element`."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _detect_version(root: ET.Element) -> str:
    """SCORM versiyani aniqlash.

    SCORM 1.2: schemaversion 1.2 yoki adlcp namespace v1p3
    SCORM 2004: schemaversion 2004 yoki imscp_v1p1
    """
    for meta in root.iter():
        if _strip_ns(meta.tag) == "schemaversion":
            ver = (meta.text or "").strip()
            if ver.startswith("1.2"):
                return "1.2"
            if "2004" in ver or ver.startswith("CAM 1.3"):
                return "2004"
    # Fallback: namespacelarga qarab
    if any(
        "adlcp_v1p3" in v or "imscp_v1p1" in v for v in root.attrib.values()
    ):
        return "2004"
    return "1.2"


def _find_first_resource_href(root: ET.Element) -> str | None:
    """`<resource type='webcontent' href='index.html'>` topish.

    Birinchi `webcontent` resursi launch_url sifatida olinadi.
    """
    for el in root.iter():
        if _strip_ns(el.tag) != "resource":
            continue
        rtype = el.attrib.get("type", "")
        href = el.attrib.get("href")
        if href and ("webcontent" in rtype or rtype.endswith("sco")):
            return href
    # Fallback: birinchi href bilan resource
    for el in root.iter():
        if _strip_ns(el.tag) == "resource" and el.attrib.get("href"):
            return el.attrib["href"]
    return None


def _find_title(root: ET.Element) -> str | None:
    """`<organization>/<title>` yoki birinchi `<title>` topish."""
    # Prefer organization title
    for org in root.iter():
        if _strip_ns(org.tag) == "organization":
            for child in org:
                if _strip_ns(child.tag) == "title" and child.text:
                    return child.text.strip()
    # Fallback to any title
    for el in root.iter():
        if _strip_ns(el.tag) == "title" and el.text:
            return el.text.strip()
    return None


def _find_mastery_score(root: ET.Element) -> Decimal | None:
    """SCORM 1.2 `<adlcp:masteryscore>` qiymati (0-100)."""
    for el in root.iter():
        if _strip_ns(el.tag) == "masteryscore" and el.text:
            try:
                return Decimal(el.text.strip())
            except (ValueError, ArithmeticError):
                continue
    return None


def parse_manifest(xml_bytes: bytes) -> ParsedManifest:
    """`imsmanifest.xml` bytes → ParsedManifest."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ManifestParseError(f"XML parse xatosi: {exc}") from exc

    if _strip_ns(root.tag) != "manifest":
        raise ManifestParseError(
            f"Root element 'manifest' bo'lishi kerak, lekin: {_strip_ns(root.tag)}"
        )

    version = _detect_version(root)
    manifest_id = root.attrib.get("identifier")
    title = _find_title(root)
    launch_url = _find_first_resource_href(root)
    if not launch_url:
        raise ManifestParseError(
            "Manifest'da webcontent resursi topilmadi — SCORM paket buzuq"
        )

    mastery = _find_mastery_score(root) if version == "1.2" else None

    return ParsedManifest(
        version=version,
        manifest_identifier=manifest_id,
        title=title,
        description=None,
        launch_url=launch_url,
        mastery_score=mastery,
    )
