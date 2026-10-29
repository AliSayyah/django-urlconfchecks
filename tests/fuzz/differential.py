"""Route-level differential oracle and the seeded command-line driver."""

from __future__ import annotations

import asyncio
import inspect
import random
import re
import secrets
import sys
import types
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import clear_url_caches, resolve

from django_urlconfchecks.check import check_url_signatures

from .generator import Case, RandomChooser, generate_case

SIGNATURE_IDS = frozenset(
    {"urlchecker.E001", "urlchecker.E003", "urlchecker.E004", "urlchecker.E006", "urlchecker.E007", "urlchecker.E008"}
)
TYPE_IDS = frozenset({"urlchecker.E002", "urlchecker.E005"})


@dataclass
class Mismatch:
    """One unexpected checker/oracle disagreement."""

    category: str
    case: Case
    url: str
    checker: tuple[tuple[str, str], ...]
    outcome: str
    detail: str

    @property
    def dedup_key(self) -> tuple[str, tuple[str, ...], str]:
        """Return a root-cause key with names and numbers normalized."""
        ids = tuple(sorted(item[0] for item in self.checker))
        detail = re.sub(r"['`][^'`]+['`]", "<name>", self.detail)
        detail = re.sub(r"\b\d+\b", "<n>", detail)
        root = _root_cause(detail)
        return self.category, ids, root


def _root_cause(detail: str) -> str:
    """Reduce Python's binding text to a stable root cause."""
    for marker in (
        "positional-only",
        "multiple values",
        "unexpected keyword",
        "keyword-only",
        "missing",
        "takes",
    ):
        if marker in detail:
            return marker
    return detail


@dataclass
class DifferentialResult:
    """Result returned by :func:`run_differential`."""

    seed: int
    cases: int
    mismatches: list[Mismatch] = field(default_factory=list)
    crashes: list[str] = field(default_factory=list)
    checker_ids: Counter[str] = field(default_factory=Counter)

    @property
    def exit_code(self) -> int:
        return int(bool(self.mismatches or self.crashes))

    @property
    def unique_mismatches(self) -> list[Mismatch]:
        seen: set[tuple[str, tuple[str, ...], str]] = set()
        result = []
        for mismatch in self.mismatches:
            key = mismatch.dedup_key
            if key not in seen:
                seen.add(key)
                result.append(mismatch)
        return result

    def mismatch_count(self, mismatch: Mismatch) -> int:
        """Count all mismatches represented by one deduplicated reproduction."""
        return sum(item.dedup_key == mismatch.dedup_key for item in self.mismatches)


def _ensure_settings():
    if not settings.configured:
        settings.configure(
            ROOT_URLCONF="tests.fuzz._empty",
            SECRET_KEY="fuzz",
            ALLOWED_HOSTS=["*"],
            INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes", "rest_framework"],
        )
    try:
        import django
        from django.apps import apps

        if not apps.ready:
            django.setup()
    except (ImportError, RuntimeError):
        # DRF is optional and Django's test plugin may already own setup.
        return


def _install(case: Case):
    name = f"tests.fuzz._case_{uuid4().hex}"
    module = types.ModuleType(name)
    module.__dict__["urlpatterns"] = case.urlpatterns
    sys.modules[name] = module
    return name, module


def _call(url: str, method: str = "GET") -> tuple[str, str]:
    try:
        match = resolve(url)
        request = getattr(RequestFactory(), method.lower())(url)
        result = match.func(request, *match.args, **match.kwargs)
        if inspect.isawaitable(result):
            result = asyncio.run(result)
        del result
        return "ok", ""
    except TypeError as exc:
        return "typeerror", str(exc)
    except Exception as exc:  # View bodies are trivial; retain unexpected resolver errors in the report.
        return "other", f"{type(exc).__name__}: {exc}"


def observe_case(case: Case) -> tuple[tuple[str, str], ...]:
    """Resolve and call every generated route variant under its temporary URLconf."""
    _ensure_settings()
    name, _module = _install(case)
    calls = case.calls or tuple((url, "GET") for url in case.variants)
    try:
        with override_settings(ROOT_URLCONF=name, URLCONFCHECKS_SILENCED_VIEWS={}):
            clear_url_caches()
            return tuple(_call(url, method) for url, method in calls)
    finally:
        clear_url_caches()
        sys.modules.pop(name, None)


def _problem_data(problems, pattern) -> tuple[tuple[str, str], ...]:
    return tuple((problem.id, str(problem.msg)) for problem in problems if getattr(problem, "obj", None) is pattern)


def evaluate_case(case: Case) -> tuple[list[Mismatch], list[str], Counter[str]]:
    """Run one built case and return mismatches, crashes, and checker ID counts."""
    _ensure_settings()
    name, _module = _install(case)
    try:
        with override_settings(ROOT_URLCONF=name, URLCONFCHECKS_SILENCED_VIEWS={}):
            clear_url_caches()
            try:
                problems = check_url_signatures(None)
            except Exception as exc:
                return [], [f"{case.shape}: {type(exc).__name__}: {exc}"], Counter()
            return _compare_case(case, problems)
    except Exception as exc:
        return [], [f"{case.shape}: {type(exc).__name__}: {exc}"], Counter()
    finally:
        clear_url_caches()
        sys.modules.pop(name, None)


def _compare_case(case: Case, problems) -> tuple[list[Mismatch], list[str], Counter[str]]:
    """Compare all variants of one case with checker results."""
    counts: Counter[str] = Counter(problem.id for problem in problems)
    checker = _problem_data(problems, case.target_pattern or _first_leaf(case.urlpatterns))
    ids = {item[0] for item in checker}
    signature_flag = bool(ids & SIGNATURE_IDS) or "urlchecker.W004" in ids
    type_flag = bool(ids & TYPE_IDS)
    outcomes = list(observe_case(case))
    mismatches = _binding_mismatch(case, checker, signature_flag, outcomes) if case.binding_checkable else []
    if case.type_checkable and type_flag != case.expected_type_mismatch:
        mismatches.append(Mismatch("type", case, case.variants[0], checker, *outcomes[0]))
    return mismatches, [], counts


def _binding_mismatch(case, checker, signature_flag, outcomes):
    """Return a binding mismatch when route-level oracle and checker disagree."""
    broken = any(outcome == "typeerror" for outcome, _detail in outcomes)
    if broken == signature_flag:
        return []
    outcome, detail = outcomes[0]
    return [Mismatch(_binding_category(case, detail), case, case.variants[0], checker, outcome, detail)]


def _binding_category(case: Case, detail: str) -> str:
    """Label a binding mismatch with the checker ID it should have exercised."""
    if "unexpected keyword" in detail or "positional-only" in detail:
        return "binding:E003"
    if "multiple values" in detail:
        return "binding:E006" if "{" in case.urlpatterns_source else "binding:E003"
    if "takes" in detail or "positional argument" in detail:
        return "binding:E001"
    return "binding"


def _first_leaf(patterns):
    current = patterns
    while current and hasattr(current[0], "url_patterns"):
        current = current[0].url_patterns
    return current[0]


def run_differential(
    seed: int | None = None, cases: int = 2000, report: str | Path | None = None
) -> DifferentialResult:
    """Run seeded cases, print a summary, and optionally write a Markdown report."""
    _ensure_settings()
    actual_seed = secrets.randbits(63) if seed is None else seed
    print(f"seed {actual_seed}")
    result = DifferentialResult(actual_seed, cases)
    chooser = RandomChooser(random.Random(actual_seed))
    for _index in range(cases):
        try:
            case = generate_case(chooser)
            mismatches, crashes, counts = evaluate_case(case)
        except Exception as exc:
            result.crashes.append(f"generation: {type(exc).__name__}: {exc}")
            continue
        result.mismatches.extend(mismatches)
        result.crashes.extend(crashes)
        result.checker_ids.update(counts)
    output = render_report(result)
    print(output)
    if report is not None:
        Path(report).write_text(output, encoding="utf-8")
    return result


def render_report(result: DifferentialResult) -> str:
    """Render a compact summary and self-contained reproductions."""
    lines = [
        f"cases: {result.cases}",
        f"mismatches: {len(result.mismatches)} (distinct {len(result.unique_mismatches)})",
        f"crashes: {len(result.crashes)}",
        "checker ids: " + (", ".join(f"{key}={value}" for key, value in sorted(result.checker_ids.items())) or "none"),
    ]
    categories = Counter(item.category for item in result.mismatches)
    lines.append(
        "mismatches by category: "
        + (", ".join(f"{key}={value}" for key, value in sorted(categories.items())) or "none")
    )
    for index, mismatch in enumerate(result.unique_mismatches, 1):
        lines.extend(
            [
                "",
                f"## Mismatch {index}: {mismatch.category} (count {result.mismatch_count(mismatch)})",
                f"shape: `{mismatch.case.shape}`",
                f"URL: `{mismatch.url}`",
                "",
                "### View source",
                "```python",
                mismatch.case.view_source.rstrip(),
                "```",
                "### urlpatterns source",
                "```python",
                mismatch.case.urlpatterns_source,
                "```",
                "### Checker",
                "```text",
                "\n".join(f"{key}: {value}" for key, value in mismatch.checker) or "(none)",
                "```",
                f"Django outcome: `{mismatch.outcome}` {mismatch.detail}",
            ]
        )
    if result.crashes:
        lines.extend(["", "## Crashes", "```text", *result.crashes, "```"])
    return "\n".join(lines)
