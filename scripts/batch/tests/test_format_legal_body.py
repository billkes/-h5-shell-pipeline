"""Tests for legal body markdown → plain (pipeline), not template TS."""

from __future__ import annotations

from pathlib import Path
import sys

scripts = Path(__file__).resolve().parents[2]
if str(scripts) not in sys.path:
    sys.path.insert(0, str(scripts))

from batch.sync_h5_legal_bundled import md_to_plain


PRIVACY_MD = """# Temioo Privacy Agreement

Local-only academic rehearsal app. Data stored on device. No account required.

## Data Collection

Speech scripts and rehearsal logs remain on your device.

## Contact

support@temioo.app
"""


def test_md_to_plain_preserves_section_blocks() -> None:
    plain = md_to_plain(PRIVACY_MD)
    assert plain.startswith("Temioo Privacy Agreement")
    assert "Data Collection" in plain
    assert "Speech scripts" in plain


def test_vite_legal_format_norm_doc_exists() -> None:
    doc = Path(__file__).resolve().parents[3] / "docs" / "H5壳Vite工程规范.md"
    text = doc.read_text(encoding="utf-8")
    assert "formatLegalBody" in text
    assert "legal-section" in text
