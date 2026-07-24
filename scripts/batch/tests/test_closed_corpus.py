"""Closed corpus: H5 agent docs live inside the package workspace."""

from __future__ import annotations

from pathlib import Path

from batch.agent_spec_index import (
    prepare_agent_prompt_files,
    write_agent_brain_focus,
)
from batch.config import BatchConfig
from batch.prompts import PromptBuilder, _PM_UI_PLAN_BRAIN_FOCUS, _PROGRAMMER_BRAIN_FOCUS
from batch.workspace import H5_SHELL_WORKSPACE_DOCS, copy_workspace_docs


# Paths / titles that steer Agents out of the package workspace.
_FORBIDDEN_AGENT_STEERS = (
    "[[rules/",
    "H5壳批前准备总计划",
    "H5壳Flutter交付自检清单",
    "h5_overlay_router_kit",
    "4.3代码防关联策略",
    "03-差异化与过审",
    "商店图与主题功能适配说明",
    "Flutter差异化开发规则",
    "工具包Flutter产品要求",
    "global-brain/",
    "2_领域/",
)


def test_h5_shell_workspace_docs_exist_in_repo() -> None:
    root = Path(__file__).resolve().parents[3]
    docs = root / "docs"
    missing = [n for n in H5_SHELL_WORKSPACE_DOCS if not (docs / n).is_file()]
    assert not missing, f"Missing closed-corpus sources under docs/: {missing}"


def test_closed_corpus_docs_do_not_steer_agents_outside() -> None:
    """Closed-corpus sources must not hard-link missing or out-of-repo Agent paths."""
    root = Path(__file__).resolve().parents[3]
    docs = root / "docs"
    issues: list[str] = []
    for name in H5_SHELL_WORKSPACE_DOCS:
        text = (docs / name).read_text(encoding="utf-8")
        for pat in _FORBIDDEN_AGENT_STEERS:
            if pat in text:
                issues.append(f"{name}: forbidden steer `{pat}`")
        # Repo-prefix paths confuse Agents (workspace copies omit docs/).
        for needle in ("`docs/H5壳", "`docs/法律", "docs/H5壳", "docs/法律协议"):
            if needle in text and "勿" not in text[max(0, text.find(needle) - 40) : text.find(needle) + 80]:
                # Allow explicit forbid lines that mention docs/rules only.
                if "docs/rules" in needle:
                    continue
                if needle.startswith("`docs/") or needle.startswith("docs/H5") or needle.startswith("docs/法律"):
                    # skip if the hit is only inside a 勿 sentence nearby — already checked
                    idx = 0
                    while True:
                        i = text.find(needle, idx)
                        if i < 0:
                            break
                        window = text[max(0, i - 60) : i + len(needle) + 60]
                        if "勿" not in window:
                            issues.append(f"{name}: repo-prefix path `{needle}`")
                        idx = i + len(needle)
    assert not issues, "Closed-corpus Agent steers:\n  " + "\n  ".join(issues)


def test_copy_workspace_docs_closes_h5_corpus(tmp_path: Path) -> None:
    cfg = BatchConfig.from_env()
    copy_workspace_docs(cfg, tmp_path, "Lensoo", "h5_swift_shell")
    missing = [n for n in H5_SHELL_WORKSPACE_DOCS if not (tmp_path / n).is_file()]
    assert not missing, f"Not copied into workspace: {missing}"
    assert (tmp_path / "法律协议规范.md").is_file()
    assert (tmp_path / "H5壳启动闪屏规范.md").is_file()
    assert (tmp_path / "H5壳Swift实现规范.md").is_file()
    assert (tmp_path / "data" / "static" / "h5_snippets" / "bridge" / "browserMock.ts").is_file()
    assert (tmp_path / "data" / "static" / "h5_snippets" / "legal" / "legalLinks.ts").is_file()
    assert not (tmp_path / "docs" / "rules").exists()


def test_brain_focus_is_workspace_closed() -> None:
    assert "01_tech_common" not in _PM_UI_PLAN_BRAIN_FOCUS
    assert "02_audit_risk" not in _PM_UI_PLAN_BRAIN_FOCUS
    assert "docs/rules" not in _PM_UI_PLAN_BRAIN_FOCUS
    assert "法律协议规范.md" in _PM_UI_PLAN_BRAIN_FOCUS
    assert "01_tech_common" not in _PROGRAMMER_BRAIN_FOCUS
    assert "H5-Bridge协议.md" in _PROGRAMMER_BRAIN_FOCUS


def test_write_agent_brain_focus_rejects_repo_rules(tmp_path: Path) -> None:
    path = write_agent_brain_focus(
        tmp_path,
        role_slug="build-agent-plan-spec",
        role_focus=_PM_UI_PLAN_BRAIN_FOCUS,
    )
    text = path.read_text(encoding="utf-8")
    assert "docs/rules" in text  # explicit forbid
    assert "Stay inside" in text or "this package workspace" in text
    assert "global-brain" not in text
    assert "whitelisted" not in text


def test_filled_plan_spec_prompt_has_no_open_corpus_paths() -> None:
    cfg = BatchConfig.from_env()
    prompts = PromptBuilder(cfg)
    text = prompts.build_agent_plan_spec_phase(
        resume=False,
        name="Lensoo",
        desc="demo",
        product_req_doc="H5壳Flutter产品要求.md",
        csv_full_name="Lensoo",
    )
    assert "docs/法律协议规范.md" not in text
    assert "`.cursor/rules/*.mdc` · `docs/rules/`" not in text
    assert "法律协议规范.md" in text
    assert "do **not** open repo `docs/rules/`" in text


def test_prepare_agent_prompt_files_indexes_workspace_norms(tmp_path: Path) -> None:
    cfg = BatchConfig.from_env()
    copy_workspace_docs(cfg, tmp_path, "Lensoo", "h5_swift_shell")
    index, brain = prepare_agent_prompt_files(
        tmp_path,
        phase="plan_spec",
        app_name="Lensoo",
        pack_type="h5_swift_shell",
        role_slug="build-agent-plan-spec",
        role_focus=_PM_UI_PLAN_BRAIN_FOCUS,
    )
    body = index.read_text(encoding="utf-8")
    brain_text = brain.read_text(encoding="utf-8")
    assert "法律协议规范.md" in body
    assert "docs/法律协议规范.md" not in body
    assert "Stay inside" in brain_text
    assert "do **not** open repo" in brain_text.lower() or "Do **not** open repo" in brain_text
    assert "global-brain" not in brain_text
