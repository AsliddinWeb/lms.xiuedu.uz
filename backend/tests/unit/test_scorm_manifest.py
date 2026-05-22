"""Phase 11a — SCORM manifest parser unit testlar."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.scorm.manifest import ManifestParseError, parse_manifest


SCORM_12_MINIMAL = b"""<?xml version="1.0"?>
<manifest identifier="com.example.golf" version="1.0"
    xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
    xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="org_1">
    <organization identifier="org_1">
      <title>Golf Explained</title>
      <item identifier="item_1" identifierref="resource_1">
        <title>Welcome</title>
        <adlcp:masteryscore>80</adlcp:masteryscore>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="resource_1" type="webcontent"
        adlcp:scormtype="sco" href="shared/launchpage.html">
      <file href="shared/launchpage.html"/>
    </resource>
  </resources>
</manifest>"""


SCORM_2004_MINIMAL = b"""<?xml version="1.0"?>
<manifest identifier="com.example.2004" version="1.0"
    xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
    xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>2004 3rd Edition</schemaversion>
  </metadata>
  <organizations default="org_1">
    <organization identifier="org_1">
      <title>Advanced Course</title>
      <item identifier="item_1" identifierref="resource_1"/>
    </organization>
  </organizations>
  <resources>
    <resource identifier="resource_1" type="webcontent"
        adlcp:scormType="sco" href="index.html"/>
  </resources>
</manifest>"""


def test_parse_scorm12():
    m = parse_manifest(SCORM_12_MINIMAL)
    assert m.version == "1.2"
    assert m.manifest_identifier == "com.example.golf"
    assert m.title == "Golf Explained"
    assert m.launch_url == "shared/launchpage.html"
    assert m.mastery_score == Decimal("80")


def test_parse_scorm2004():
    m = parse_manifest(SCORM_2004_MINIMAL)
    assert m.version == "2004"
    assert m.manifest_identifier == "com.example.2004"
    assert m.title == "Advanced Course"
    assert m.launch_url == "index.html"
    # SCORM 2004 mastery score yo'q
    assert m.mastery_score is None


def test_parse_invalid_xml():
    with pytest.raises(ManifestParseError):
        parse_manifest(b"<not valid xml")


def test_parse_wrong_root():
    with pytest.raises(ManifestParseError, match="manifest"):
        parse_manifest(b"<?xml version='1.0'?><root></root>")


def test_parse_no_resource():
    xml = b"""<?xml version='1.0'?>
    <manifest identifier='x'>
      <metadata><schemaversion>1.2</schemaversion></metadata>
      <organizations/>
      <resources/>
    </manifest>"""
    with pytest.raises(ManifestParseError, match="webcontent"):
        parse_manifest(xml)


def test_parse_falls_back_to_first_resource():
    """type='webcontent' yo'q bo'lsa, birinchi href bilan resource olinadi."""
    xml = b"""<?xml version='1.0'?>
    <manifest identifier='x'>
      <metadata><schemaversion>1.2</schemaversion></metadata>
      <organizations><organization><title>T</title></organization></organizations>
      <resources>
        <resource identifier='r1' type='custom' href='custom.html'/>
      </resources>
    </manifest>"""
    m = parse_manifest(xml)
    assert m.launch_url == "custom.html"
