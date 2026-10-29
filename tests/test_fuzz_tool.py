"""Small smoke tests that keep the maintained fuzzing tool runnable."""

import importlib.util
import random
import subprocess
import sys
from collections import Counter

from tests.fuzz.differential import evaluate_case, observe_case, run_differential
from tests.fuzz.generator import RandomChooser, generate_case
from tests.fuzz.robustness import run_robustness
from tests.fuzz.stress import run_stress


def test_differential_driver_smoke():
    result = run_differential(seed=123, cases=100)
    assert result.exit_code == 0
    assert not result.mismatches
    assert not result.crashes


def test_robustness_corpus_smoke():
    assert run_robustness().exit_code == 0


def test_stress_driver_smoke():
    result = run_stress((10, 20), (2, 5))
    assert result.exit_code == 0


def test_cli_entry_point_smoke():
    result = subprocess.run(
        [sys.executable, "-m", "tests.fuzz", "differential", "--seed", "1", "--cases", "50"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("seed 1\n")


def test_seeded_generator_coverage_guard():
    """Keep the case dimensions and checker IDs from silently shrinking."""
    families, routes, ids, broken, clean = _coverage_sample()
    expected_families = _expected_families()
    expected_routes = {
        "static",
        "int",
        "str",
        "slug",
        "uuid",
        "path",
        "custom",
        "named",
        "unnamed",
        "optional",
        "alt",
        "lookaround",
    }
    expected_ids = {f"urlchecker.E00{index}" for index in (1, 2, 3, 4, 5, 6, 7)} | {"urlchecker.W004"}
    assert expected_families <= families.keys()
    assert expected_routes <= routes.keys()
    assert expected_ids <= ids.keys()
    assert broken and clean


def _coverage_sample():
    """Collect dimensions, checker IDs, and oracle outcomes."""
    chooser = RandomChooser(random.Random(20261029))
    families, routes, ids = Counter(), Counter(), Counter()
    broken = clean = 0
    for _index in range(500):
        case = generate_case(chooser)
        families[case.shape.split(":", 1)[0]] += 1
        routes[case.shape.split(":", 2)[1]] += 1
        mismatches, crashes, checker_ids = evaluate_case(case)
        assert not crashes and not mismatches
        ids.update(checker_ids)
        if any(status == "typeerror" for status, _detail in observe_case(case)):
            broken += 1
        else:
            clean += 1
    return families, routes, ids, broken, clean


def _expected_families():
    """Return installed view families."""
    families = {"function", "cbv", "async", "decorated", "partial"}
    if importlib.util.find_spec("rest_framework") is not None:
        families.add("drf")
    return families
