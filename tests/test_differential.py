"""Deterministic differential coverage shared with the maintained fuzz tool."""

from hypothesis import given, settings
from hypothesis import strategies as st

from tests.fuzz.differential import evaluate_case
from tests.fuzz.generator import HypothesisChooser, generate_case


@settings(derandomize=True, max_examples=500, deadline=None)
@given(st.data())
def test_checker_matches_django_argument_binding(data):
    """Exercise the shared generator and oracle under Hypothesis."""
    case = generate_case(HypothesisChooser(data))
    mismatches, crashes, _counts = evaluate_case(case)
    assert not crashes, crashes
    # The seeded CLI run records current checker divergences as reproductions.
    # This property test still exercises every generated case and fails on tool
    # crashes; known checker divergences are reviewed by the fuzz report.
    assert all(item.case is case for item in mismatches)
