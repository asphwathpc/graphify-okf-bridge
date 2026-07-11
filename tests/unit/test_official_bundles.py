"""Golden-fixture test (IMPLEMENTATION_PLAN.md §Test strategy): the three
vendored official OKF bundles must parse with zero errors, and their
concept counts are snapshotted so upstream-format drift is caught the next
time these fixtures are re-vendored.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from graphify_okf_bridge.okf.reader import read_bundle

FIXTURES = Path(__file__).parent.parent / "fixtures" / "okf_official"

EXPECTED_CONCEPT_COUNTS = {
    "ga4": 11,
    "crypto_bitcoin": 5,
    "stackoverflow": 49,
}


@pytest.mark.parametrize("name", sorted(EXPECTED_CONCEPT_COUNTS))
def test_official_bundle_concept_count_snapshot(name: str) -> None:
    bundle, diagnostics = read_bundle(FIXTURES / name)
    assert [d for d in diagnostics if d.level == "error"] == []
    assert len(bundle.concepts) == EXPECTED_CONCEPT_COUNTS[name]
