"""Tests for h5_perf_audit."""

from pathlib import Path

from batch.h5_perf_audit import collect_h5_perf_warnings


def _write_register(tmp_path: Path) -> None:
    (tmp_path / "本包登记信息.json").write_text(
        '{"packType":"h5_swift_shell","h5SiteEntry":"rolioo/index.html"}',
        encoding="utf-8",
    )


def test_perf_warn_out_in_transition(tmp_path: Path) -> None:
    _write_register(tmp_path)
    (tmp_path / "h5" / "src" / "layouts").mkdir(parents=True)
    (tmp_path / "h5" / "src" / "layouts" / "TabLayout.vue").write_text(
        '<transition mode="out-in">',
        encoding="utf-8",
    )
    warns = collect_h5_perf_warnings(tmp_path)
    assert any("out-in" in w for w in warns)


def test_perf_warn_native_audio_without_player(tmp_path: Path) -> None:
    _write_register(tmp_path)
    (tmp_path / "h5" / "src" / "components").mkdir(parents=True)
    (tmp_path / "h5" / "src" / "components" / "X.vue").write_text(
        '<audio controls src="x" />',
        encoding="utf-8",
    )
    warns = collect_h5_perf_warnings(tmp_path)
    assert any("AudioPlayer" in w for w in warns)
