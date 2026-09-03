"""Tests for the tag-derived release versioning.

These pin the rules that make a mislabelled tag impossible: the version comes
from the tags, beta numbers never repeat, and a minor or major bump is only
ever explicit.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "workflows"))

from next_version import (  # noqa: E402
    bump_from_trailer,
    latest_stable,
    next_beta,
    resolve,
)

TAGS = ["v3.3.0", "v4.0.0", "v4.0.1", "v4.0.2b1", "v4.0.2b2", "v3.3.0-beta"]


class TestLatestStable:
    def test_picks_the_highest_stable_tag(self):
        assert latest_stable(TAGS) == "4.0.1"

    def test_ignores_prerelease_and_beta_tags(self):
        # v4.0.2b2 is higher but unreleased; the base must stay 4.0.1.
        assert latest_stable(["v1.0.0", "v2.0.0b9", "v1.9.9-beta"]) == "1.0.0"

    def test_compares_numerically_not_lexically(self):
        assert latest_stable(["v1.9.0", "v1.10.0"]) == "1.10.0"

    def test_unreleased_repo_starts_at_zero(self):
        assert latest_stable(["nightly", "v-broken"]) == "0.0.0"


class TestBetaNumbering:
    def test_first_beta_for_a_base_is_b1(self):
        assert next_beta(TAGS, "4.1.0") == "4.1.0b1"

    def test_continues_after_the_highest_existing_beta(self):
        assert next_beta(TAGS, "4.0.2") == "4.0.2b3"

    def test_never_reuses_a_number_pypi_has_seen(self):
        # PyPI versions are immutable, so N must strictly increase.
        used = next_beta(TAGS, "4.0.2")
        assert used not in TAGS and f"v{used}" not in TAGS

    def test_counts_only_betas_of_the_same_base(self):
        assert next_beta(["v9.9.9b7"], "1.0.0") == "1.0.0b1"


class TestResolve:
    def test_stable_defaults_to_a_patch_bump(self):
        assert resolve("stable", TAGS, "patch") == "4.0.2"

    def test_beta_is_a_prerelease_of_the_same_next_version(self):
        assert resolve("beta", TAGS, "patch") == "4.0.2b3"

    @pytest.mark.parametrize(
        "level,expected", [("patch", "4.0.2"), ("minor", "4.1.0"), ("major", "5.0.0")]
    )
    def test_bump_levels(self, level, expected):
        assert resolve("stable", TAGS, level) == expected

    def test_unknown_channel_raises(self):
        with pytest.raises(ValueError, match="Unknown channel"):
            resolve("nightly", TAGS, "patch")


class TestExplicitBumpOnly:
    """update_version_metadata.bump_semver: a minor or major is never inferred."""

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("feat!: drop python 3.10", None),
            ("feat: add a flag\n\nBREAKING CHANGE: nope", None),
            ("chore: release\n\nRelease-Bump: minor", "minor"),
            ("chore: release\n\nrelease-bump: MAJOR", "major"),
            ("", None),
        ],
    )
    def test_only_a_trailer_selects_the_level(self, message, expected):
        assert bump_from_trailer(message) == expected
