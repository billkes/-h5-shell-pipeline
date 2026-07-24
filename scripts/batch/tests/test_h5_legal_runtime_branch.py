"""Tests for legal URL runtime-branch fake-URL gate."""

from __future__ import annotations

import json
from pathlib import Path

from batch.h5_legal_ui import verify_h5_legal_no_fake_urls


def _vite_legal_project(root: Path, *, legal_ts: str) -> Path:
    project = root / "App"
    h5 = project / "h5"
    (h5 / "src" / "legal").mkdir(parents=True)
    (h5 / "package.json").write_text('{"name":"app"}\n', encoding="utf-8")
    (project / "本包登记信息.json").write_text(
        json.dumps(
            {
                "packType": "h5_swift_shell",
                "codeAntiCorrelation": {"dartCodePrefix": "demo"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project / "功能文档.md").write_text(
        "## Screen Inventory\n\n| Route | Name |\n|---|---|\n| #/welcome | Welcome |\n| #/legal | Legal |\n",
        encoding="utf-8",
    )
    (h5 / "src" / "legal" / "legalLinks.ts").write_text(legal_ts, encoding="utf-8")
    (h5 / "src" / "App.vue").write_text("<template></template>\n", encoding="utf-8")
    return project


def test_empty_legal_links_pass(tmp_path: Path) -> None:
    project = _vite_legal_project(
        tmp_path,
        legal_ts=(
            "export const legalLinks = { privacyUrl: '', termsUrl: '' }\n"
            "export function isExternalLegalUrl(url: unknown): url is string {\n"
            "  return typeof url === 'string' && /^https:\\/\\//i.test(url.trim())\n"
            "}\n"
        ),
    )
    assert verify_h5_legal_no_fake_urls(project) == []


def test_example_com_legal_url_fails(tmp_path: Path) -> None:
    project = _vite_legal_project(
        tmp_path,
        legal_ts=(
            "export const legalLinks = {\n"
            "  privacyUrl: 'https://example.com/privacy',\n"
            "  termsUrl: '',\n"
            "}\n"
        ),
    )
    issues = verify_h5_legal_no_fake_urls(project)
    assert any("LEGAL_URL" in i for i in issues)
