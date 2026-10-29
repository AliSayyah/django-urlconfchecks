"""Maintained differential, robustness, and performance fuzzing tools.

Run this package with ``python -m tests.fuzz``.  The differential oracle compares
the checker with Django's resolver and Python argument binding.  It intentionally
does not count the request-name part of E001 as a mismatch when a generated case
uses a keyword-only or absent request parameter.  W001, W002, W003, and W005 are
diagnostic warnings and W004 is treated as a route flag because it identifies an
optional capture that can make a required parameter fail.
"""

from .differential import DifferentialResult, evaluate_case, observe_case, run_differential
from .generator import (
    Case,
    HypothesisChooser,
    RandomChooser,
    build_drf_router_case,
    build_untyped_converter,
    generate_case,
)
from .robustness import RobustnessResult, run_robustness
from .stress import StressResult, run_stress

__all__ = [
    "Case",
    "DifferentialResult",
    "HypothesisChooser",
    "RandomChooser",
    "RobustnessResult",
    "StressResult",
    "evaluate_case",
    "observe_case",
    "build_drf_router_case",
    "build_untyped_converter",
    "generate_case",
    "run_differential",
    "run_robustness",
    "run_stress",
]
