"""Tests for dynamic naming v2 (derive_key + transform_identifier)."""

from __future__ import annotations

import unittest

from batch.naming import (
    FEATURED_RULE_KEYS,
    RULE_PROFILES,
    derive_key,
    meta_from_lock,
    transform_identifier,
    build_rule_meta,
)


def _meta(rule_key: str, seed: str = "eybuf", batch_id: str = "") -> object:
    from batch.naming import NamingMeta, meta_from_lock

    raw = build_rule_meta(rule_key, seed, batch_id=batch_id)
    return meta_from_lock(raw)


class TestDeriveKey(unittest.TestCase):
    def test_deterministic(self) -> None:
        kwargs = dict(
            rule_key="consonant_core",
            package_seed="eybuf",
            entity="local",
            semantic="maxNum",
            role="pre",
            length_range=(2, 4),
        )
        a = derive_key(**kwargs)
        b = derive_key(**kwargs)
        self.assertEqual(a, b)

    def test_length_within_range(self) -> None:
        for semantic in [f"var{i}" for i in range(200)]:
            key = derive_key(
                rule_key="single_initial_triple",
                package_seed="eybuf",
                entity="local",
                semantic=semantic,
                role="mid",
                length_range=(2, 5),
            )
            self.assertGreaterEqual(len(key), 2)
            self.assertLessEqual(len(key), 5)

    def test_different_semantics_differ(self) -> None:
        a = derive_key(
            rule_key="single_initial_triple",
            package_seed="eybuf",
            entity="local",
            semantic="maxNum",
            role="mid",
            length_range=(2, 5),
        )
        b = derive_key(
            rule_key="single_initial_triple",
            package_seed="eybuf",
            entity="local",
            semantic="minNum",
            role="mid",
            length_range=(2, 5),
        )
        self.assertNotEqual(a, b)


class TestTransformAffixPosition(unittest.TestCase):
    def test_prefix_rule_prepends(self) -> None:
        meta = _meta("consonant_core")
        out = transform_identifier(
            rule_key="consonant_core",
            meta=meta,
            entity="local",
            semantic="maxNum",
        )
        self.assertTrue(out.endswith("Num") or "max" in out)
        self.assertNotEqual(out, "maxNum")

    def test_suffix_rule_appends(self) -> None:
        meta = _meta("reverse_initials")
        out = transform_identifier(
            rule_key="reverse_initials",
            meta=meta,
            entity="local",
            semantic="maxNum",
        )
        self.assertTrue(out.startswith("max"))
        self.assertNotEqual(out, "maxNum")

    def test_infix_rule_splits(self) -> None:
        meta = _meta("single_initial_triple")
        max_out = transform_identifier(
            rule_key="single_initial_triple",
            meta=meta,
            entity="local",
            semantic="maxNum",
        )
        min_out = transform_identifier(
            rule_key="single_initial_triple",
            meta=meta,
            entity="local",
            semantic="minNum",
        )
        self.assertNotEqual(max_out, min_out)
        self.assertRegex(max_out, r"^max[a-z]+Num$")

    def test_mirror_rule_wraps(self) -> None:
        meta = _meta("mirror_random")
        out = transform_identifier(
            rule_key="mirror_random",
            meta=meta,
            entity="local",
            semantic="maxNum",
        )
        self.assertIn("max", out)
        self.assertGreater(len(out), len("maxNum"))


class TestJoinStyles(unittest.TestCase):
    def test_snake_file_uses_underscores(self) -> None:
        raw = build_rule_meta("single_initial_triple", "eybuf")
        raw["joinStyles"] = {"file": "snake"}
        meta = meta_from_lock(raw)
        out = transform_identifier(
            rule_key="single_initial_triple",
            meta=meta,
            entity="file",
            semantic="feed_coordinator",
        )
        self.assertIn("_", out)

    def test_dot_join(self) -> None:
        raw = build_rule_meta("single_initial_triple", "eybuf")
        raw["joinStyles"] = {"local": "dot"}
        meta = meta_from_lock(raw)
        out = transform_identifier(
            rule_key="single_initial_triple",
            meta=meta,
            entity="local",
            semantic="maxNum",
        )
        self.assertIn(".", out)


class TestMetaV2(unittest.TestCase):
    def test_build_rule_meta_has_no_static_affix(self) -> None:
        meta = build_rule_meta("single_initial_triple", "bfmt")
        forbidden = {
            "variableMiddleInsert",
            "classSuffix",
            "leftRandom",
            "rightRandom",
            "embedSegment",
            "infix",
            "randomTail",
        }
        self.assertTrue(meta.get("packageSeed"))
        self.assertNotIn("variableMiddleInsert", meta)
        for key in forbidden:
            self.assertNotIn(key, meta)

    def test_featured_four_profiles_exist(self) -> None:
        for key in FEATURED_RULE_KEYS:
            self.assertIn(key, RULE_PROFILES)
            profile = RULE_PROFILES[key]
            self.assertIn(profile["affix"], ("prefix", "suffix", "infix", "mirror"))


class TestEntityCasing(unittest.TestCase):
    def test_class_pascal(self) -> None:
        meta = _meta("consonant_core")
        out = transform_identifier(
            rule_key="consonant_core",
            meta=meta,
            entity="class",
            semantic="feed_coordinator",
        )
        self.assertTrue(out[0].isupper(), out)


if __name__ == "__main__":
    unittest.main()
