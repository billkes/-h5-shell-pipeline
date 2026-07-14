"""Tests for h5 legal MD spec gate."""

from __future__ import annotations

from pathlib import Path
import sys

scripts = Path(__file__).resolve().parents[2]
if str(scripts) not in sys.path:
    sys.path.insert(0, str(scripts))

from batch.h5_legal_md_gate import verify_h5_legal_md, verify_legal_md_pair

_FILLER = (
    "The application keeps puzzle sessions, star balances, paint coin totals, pack unlock "
    "states, export counters, and interface preferences on your device so Studio dashboards, "
    "pack libraries, logbooks, and store checkout remain responsive without cloud accounts. "
)


def _pad(text: str, *, repeats: int = 45) -> str:
    return text + "\n\n" + (_FILLER * repeats)


def sample_privacy_md(main: str) -> str:
    return _pad(
        f"""# {main} Privacy Agreement

Latest Updated: May 18, 2026

Teavoo is rated **18+**.

## Your Rights and Choices

You control local data on your device and may clear it anytime from Settings.

## Information We Collect

We store puzzle progress locally and do not require an account.

## Photos

Export requests photo library permission only when you save a snapshot.

## Purchases

Apple processes in-app purchases; we never receive card numbers.

## Analytics

No third-party analytics SDKs ship in this version.

## Content Safety and Reporting

We maintain **Zero Tolerance** for misuse, apply **filtering methods** to curated packs, provide a **user reporting mechanism**, and aim to act within **24 hours** on substantiated reports.

## Changes

We may update this policy; continued use constitutes acceptance.

## Children's Privacy

Teavoo is intended for users aged **18 and older**. We do not knowingly collect personal information from children under 13.

## Contact Us

Email **{main}@gmail.com** for privacy questions.
"""
    )


def sample_terms_md(main: str) -> str:
    return _pad(
        f"""# {main} User Agreement

Latest Updated: May 18, 2026

These terms govern Teavoo, rated **18+**.

## Service Overview

Local pixel puzzle entertainment without mandatory login.

## License

Personal non-transferable license for casual use on your Apple device.

## Content

Pack artwork is licensed for in-app use; you may export your painted snapshots personally.

## Virtual Currency

Paint Coins are consumable with no cash value outside the app.

## User Obligations

You must be at least **18 years old** and use the app lawfully.

## Prohibited Conduct and Content Safety

We enforce **Zero Tolerance**, maintain **filtering methods**, provide a **user reporting mechanism**, and respond within **24 hours** to substantiated abuse reports.

## Disclaimer

The app is provided as-is for casual recreation.

## Termination

Delete the app to stop using Teavoo.

## Governing Law

Interpreted under generally applicable consumer principles without naming specific regions.

## Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, TEAVOO IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND.

## Contact Us

Email **{main}@gmail.com** for support.
"""
    )


def test_verify_legal_md_pair_passes_style2(tmp_path: Path) -> None:
    main = "Demo"
    issues = verify_legal_md_pair(
        sample_privacy_md(main),
        sample_terms_md(main),
        main_name=main,
        privacy_style=2,
    )
    assert issues == []


def test_verify_legal_md_pair_fails_plain_text_sections(tmp_path: Path) -> None:
    main = "Demo"
    bad = "Demo Privacy Policy\n\nLast updated: July 14, 2026\n\nBody only.\n"
    issues = verify_legal_md_pair(
        bad,
        sample_terms_md(main),
        main_name=main,
        privacy_style=2,
    )
    assert any("missing H1" in i or "H1 must" in i for i in issues)
    assert any("Latest Updated" in i for i in issues)


def test_verify_h5_legal_md_on_project(tmp_path: Path) -> None:
    project = tmp_path / "Demo"
    project.mkdir()
    (project / "本包登记信息.json").write_text(
        '{"packType":"h5_swift_shell","appSlug":"demo","bundleEntryPath":"h5_site/demo/index.html"}',
        encoding="utf-8",
    )
    (project / "功能文档.md").write_text(
        "# Spec\n\n## Screen Inventory\n\n| Route | Screen |\n| /legal | Legal |\n",
        encoding="utf-8",
    )
    main = "Demo"
    (project / f"{main} Privacy Agreement.md").write_text(
        sample_privacy_md(main), encoding="utf-8"
    )
    (project / f"{main} User Agreement.md").write_text(
        sample_terms_md(main), encoding="utf-8"
    )
    assert verify_h5_legal_md(project) == []
