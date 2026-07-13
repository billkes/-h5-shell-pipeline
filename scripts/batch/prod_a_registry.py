"""产 A 总库 — 飞书 Bitable 在线只读（名称 + 首个商品Code 查重）."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

COL_APP_NAME = "应用主名称"
COL_FULL_NAME = "全称"
COL_FIRST_CODE = "首个商品Code"


@dataclass(frozen=True)
class ProdARegistryEntry:
    app_name: str
    full_name: str
    first_product_code: str


@dataclass
class ProdARegistry:
    """In-memory view of the 产A Bitable table."""

    source: str
    entries: list[ProdARegistryEntry] = field(default_factory=list)

    @property
    def app_names(self) -> set[str]:
        return {e.app_name for e in self.entries}

    @property
    def full_names(self) -> set[str]:
        return {e.full_name for e in self.entries if e.full_name}

    @property
    def main_names(self) -> set[str]:
        return {main for e in self.entries for main in [main_name_from_full(e)] if main}

    @property
    def product_codes(self) -> set[str]:
        return {e.first_product_code for e in self.entries if e.first_product_code}

    def lookup(self, app_name: str) -> ProdARegistryEntry | None:
        key = app_name.strip()
        for entry in self.entries:
            if entry.app_name == key:
                return entry
        return None

    def has_full_name(self, full_name: str) -> bool:
        return full_name.strip() in self.full_names

    def has_product_code(self, code: str) -> bool:
        return code.strip() in self.product_codes

    def has_main_name(self, main: str) -> bool:
        return main.strip() in self.main_names


def main_name_from_full(entry: ProdARegistryEntry) -> str:
    """Parse main name from ``主名 - A & B`` or fall back to app_name."""
    full = (entry.full_name or "").strip()
    if full:
        head = full.split("-", 1)[0].strip()
        if head:
            return head
    return entry.app_name


def subtitle_pair_from_full(full_name: str) -> tuple[str, str] | None:
    """Return (subtitle1, subtitle2) from ``Main - A & B`` if parseable."""
    text = full_name.strip()
    if " - " not in text or "&" not in text:
        return None
    _, rest = text.split(" - ", 1)
    if "&" not in rest:
        return None
    left, right = rest.split("&", 1)
    return left.strip(), right.strip()


def build_prod_a_registry(
    entries: list[ProdARegistryEntry],
    *,
    source: str,
) -> ProdARegistry:
    return ProdARegistry(source=source, entries=list(entries))


def load_prod_a_registry_from_csv(path: Path) -> ProdARegistry:
    """Load from a CSV file (tests / one-off fixtures only)."""
    registry = ProdARegistry(source=str(path))
    if not path.is_file():
        return registry

    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            return registry
        for row in reader:
            app = str(row.get(COL_APP_NAME) or "").strip()
            if not app:
                continue
            full = str(row.get(COL_FULL_NAME) or "").strip()
            code = str(row.get(COL_FIRST_CODE) or "").strip()
            registry.entries.append(
                ProdARegistryEntry(
                    app_name=app,
                    full_name=full,
                    first_product_code=code,
                )
            )
    return registry


def load_prod_a_registry(project_dir: Path | None = None) -> ProdARegistry:
    """Load 产 A 总库 from Feishu Bitable (``config/feishu.yaml``)."""
    from batch.config import _project_root
    from batch.feishu_config import get_prod_a_task_config, load_feishu_config
    from batch.feishu_prod_a import fetch_prod_a_entries

    _ = project_dir or _project_root()
    config = load_feishu_config()
    prod = get_prod_a_task_config(config)
    table_id = str(prod.get("table_id") or "").strip()
    entries = fetch_prod_a_entries(config)
    return build_prod_a_registry(
        entries,
        source=f"feishu:{table_id or 'unknown'}",
    )


def format_registry_summary(registry: ProdARegistry) -> str:
    if not registry.entries:
        return f"产A 总库为空: {registry.source}"
    return (
        f"产A 总库: {registry.source} · "
        f"{len(registry.entries)} 条 · "
        f"{len(registry.full_names)} 个全称 · "
        f"{len(registry.product_codes)} 个商品Code"
    )


def validate_batch_against_registry(
    rows: list[object],
    registry: ProdARegistry,
    *,
    name_attr: str = "name",
    full_name_attr: str = "full_name",
    code_attr: str = "first_product_code",
) -> list[str]:
    """Return human-readable warnings when batch CSV conflicts with 产A 总库."""
    if not registry.entries:
        return [f"警告: 产A 总库未拉取或为空 ({registry.source})，跳过全局查重"]

    warnings: list[str] = []
    batch_codes: dict[str, str] = {}

    for row in rows:
        app = str(getattr(row, name_attr, "") or "").strip()
        full = str(getattr(row, full_name_attr, "") or "").strip()
        code = str(getattr(row, code_attr, "") or "").strip()
        if not app:
            continue

        global_entry = registry.lookup(app)
        if global_entry:
            if full and global_entry.full_name and full != global_entry.full_name:
                warnings.append(
                    f"「{app}」全称与产A总库不一致: "
                    f"批次={full!r} 总库={global_entry.full_name!r}"
                )
            if code and global_entry.first_product_code and code != global_entry.first_product_code:
                warnings.append(
                    f"「{app}」首个商品Code与产A总库不一致: "
                    f"批次={code!r} 总库={global_entry.first_product_code!r}"
                )
        elif full and registry.has_full_name(full):
            warnings.append(f"「{app}」全称 {full!r} 已在产A总库其它应用占用")

        if code:
            owner = batch_codes.get(code)
            if owner and owner != app:
                warnings.append(
                    f"批次内商品Code重复: {code!r}（{owner} vs {app}）"
                )
            batch_codes.setdefault(code, app)

            for entry in registry.entries:
                if entry.first_product_code == code and entry.app_name != app:
                    warnings.append(
                        f"「{app}」商品Code {code!r} 与产A总库「{entry.app_name}」冲突"
                    )
                    break

        if full:
            main = full.split("-", 1)[0].strip() if " - " in full else app
            for entry in registry.entries:
                if entry.app_name == app:
                    continue
                other_main = main_name_from_full(entry)
                if main and other_main and main.lower() == other_main.lower():
                    warnings.append(
                        f"主名字 {main!r} 与产A总库「{entry.app_name}」重复"
                    )
                    break
            pair = subtitle_pair_from_full(full)
            if pair:
                for entry in registry.entries:
                    if entry.app_name == app or not entry.full_name:
                        continue
                    other_pair = subtitle_pair_from_full(entry.full_name)
                    if other_pair and pair == other_pair:
                        warnings.append(
                            f"副标题组合 {pair!r} 与产A总库「{entry.app_name}」重复"
                        )
                        break

    return warnings


def normalize_product_code_token(code: str) -> str:
    """Lowercase alphanumeric token for fuzzy duplicate hints."""
    return re.sub(r"[^a-z0-9]", "", code.lower())
