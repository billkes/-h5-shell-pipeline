"""Soft warnings for WKWebView perf / overlay stacking (post-build checklist)."""

from __future__ import annotations

import re
from pathlib import Path

from batch.h5_legal_ui import is_h5_shell_project


def _read_h5_tree(project: Path) -> str:
    h5_src = project / "h5" / "src"
    if not h5_src.is_dir():
        return ""
    chunks: list[str] = []
    for path in h5_src.rglob("*"):
        if not path.is_file() or path.suffix not in {".vue", ".css", ".ts"}:
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def collect_h5_perf_warnings(project: Path) -> list[str]:
    """Non-blocking perf/stack hints for h5_shell post-build review."""
    project = project.expanduser().resolve()
    if not is_h5_shell_project(project):
        return []

    text = _read_h5_tree(project)
    if not text:
        return []

    warnings: list[str] = []

    if re.search(r'mode\s*=\s*["\']out-in["\']', text):
        warnings.append(
            "PERF: Tab transition mode=out-in 易与 keep-alive 冲突导致切 Tab 卡顿（建议去掉 out-in）"
        )

    if "keep-alive" not in text and "TabLayout" in text:
        warnings.append(
            "PERF: 存在 TabLayout 但未发现 keep-alive（子页返回可能重挂大 DOM）"
        )

    if "defineOptions({ name: 'TabLayout' })" not in text and "TabLayout" in text:
        if re.search(r"keep-alive[^>]*include", text):
            warnings.append(
                "PERF: App 级 keep-alive 缓存 TabLayout 须 defineOptions({ name: 'TabLayout' })"
            )

    backdrop_hits = len(re.findall(r"backdrop-filter\s*:", text, re.I))
    if backdrop_hits > 2:
        warnings.append(
            f"PERF: backdrop-filter 出现 {backdrop_hits} 处（建议 Dock/TopBar/遮罩改实色渐变）"
        )

    if re.search(r"animation\s*:[^;]*infinite", text) and not re.search(
        r"animation\s*:\s*none", text
    ):
        warnings.append(
            "PERF: 仍存在 CSS infinite 动画（功能页 ambient 建议 :not(splash/welcome) 静化）"
        )

    if re.search(r"z-index\s*:\s*1[34]0", text) and "--dnmrl-z-media" not in text:
        warnings.append(
            "LAYER: 存在 z-index 130–149 但未定义 --dnmrl-z-media（拍照 sheet 可能被 event-veil 遮挡）"
        )

    if "AudioPlayer" not in text and re.search(r"<audio\b", text, re.I):
        warnings.append("FLAVOR: 使用 <audio> 但未引入 AudioPlayer 自定义组件")

    return warnings
