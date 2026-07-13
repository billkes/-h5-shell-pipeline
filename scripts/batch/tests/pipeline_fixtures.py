"""Minimal shared fixtures for batch unit tests."""

from __future__ import annotations

from batch.csv_tasks import CsvTaskRow


def sample_csv_row(
    name: str = "TestApp",
    *,
    pack_type: str = "h5_swift_shell",
    product_code: str = "Test00",
) -> CsvTaskRow:
    return CsvTaskRow(
        name=name,
        full_name=f"{name} - Demo App",
        state_management="Provider",
        architecture_pattern="MVC",
        naming_obfuscation_rule="倒序声母策略",
        privacy_style="风格1",
        privacy_file="1号",
        git_url=f"https://git.example.com/{name.lower()}.git",
        first_product_code=product_code,
        programming_style="德国人",
        pack_type=pack_type,
        theme_code="B99999",
        theme_cn=f"主题{name}",
        track="工具",
        audience="通用",
        core_scene="日常",
        local_feature="本地功能",
        product_flow="Browse local flow",
    )
