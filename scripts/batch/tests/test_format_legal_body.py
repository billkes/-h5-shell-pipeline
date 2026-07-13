"""Tests for formatLegalBody legal kit helper."""

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


def test_formatLegalBody_ts_exists_in_template() -> None:
    tpl = (
        Path(__file__).resolve().parents[3]
        / "data/static/templates/h5_vite/src/lib/formatLegalBody.ts"
    )
    text = tpl.read_text(encoding="utf-8")
    assert "legal-section" in text
    assert "isLegalSectionHeading" in text
