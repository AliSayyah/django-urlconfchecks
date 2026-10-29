"""Scaling and deep-include checks for the URL signature checker."""

from __future__ import annotations

import gc
import resource
import time
import types
from dataclasses import dataclass, field
from uuid import uuid4

from django.conf import settings
from django.http import HttpResponse
from django.test.utils import override_settings
from django.urls import clear_url_caches, include, path, resolve

from django_urlconfchecks.check import check_url_signatures


@dataclass
class StressRow:
    """One timing observation."""

    kind: str
    size: int
    seconds: float
    rss_mb: float
    status: str


@dataclass
class StressResult:
    """Stress run output."""

    rows: list[StressRow] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    superlinear: bool = False

    @property
    def exit_code(self):
        return int(bool(self.failures))


def _ensure_settings():
    if not settings.configured:
        settings.configure(ROOT_URLCONF="tests.fuzz._empty", SECRET_KEY="fuzz", ALLOWED_HOSTS=["*"])


def _view(request):
    return HttpResponse()


def _flat(size):
    return [path(f"{index}/", _view) for index in range(size)]


def _nested(depth):
    patterns = [path("leaf/", _view)]
    for _index in range(depth):
        patterns = [path("x/", include(patterns))]
    return patterns


def _module(patterns):
    name = f"tests.fuzz._stress_{uuid4().hex}"
    module = types.ModuleType(name)
    module.__dict__["urlpatterns"] = patterns
    import sys

    sys.modules[name] = module
    return name


def _measure(module_name, kind, size):
    clear_url_caches()
    gc.collect()
    start = time.perf_counter()
    status = "ok"
    try:
        check_url_signatures(None)
    except Exception as exc:
        status = f"{type(exc).__name__}: {exc}"
    seconds = time.perf_counter() - start
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return StressRow(kind, size, seconds, rss, status)


def _deep_check(depth, result):
    patterns = _nested(depth)
    module_name = _module(patterns)
    url = "/" + "x/" * depth + "leaf/"
    try:
        with override_settings(ROOT_URLCONF=module_name, URLCONFCHECKS_SILENCED_VIEWS={}):
            clear_url_caches()
            start = time.perf_counter()
            try:
                check_url_signatures(None)
                checked = True
            except Exception as exc:
                checked = False
                check_error = f"{type(exc).__name__}: {exc}"
            try:
                resolve(url)
                django_ok = True
            except Exception as exc:
                django_ok = False
                del exc
            seconds = time.perf_counter() - start
    finally:
        clear_url_caches()
        import sys

        sys.modules.pop(module_name, None)
    if django_ok and not checked:
        result.failures.append(f"depth {depth}: checker {check_error}, Django resolved")
    return StressRow(
        "nested",
        depth,
        seconds,
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "ok" if checked else check_error,
    )


def run_stress(
    sizes: tuple[int, ...] = (10000, 50000, 100000), depths: tuple[int, ...] = (100, 500, 900)
) -> StressResult:
    """Measure flat URLconfs and compare deep includes with Django."""
    _ensure_settings()
    result = StressResult()
    for size in sizes:
        module_name = _module(_flat(size))
        try:
            with override_settings(ROOT_URLCONF=module_name, URLCONFCHECKS_SILENCED_VIEWS={}):
                result.rows.append(_measure(module_name, "flat", size))
        finally:
            clear_url_caches()
            import sys

            sys.modules.pop(module_name, None)
    for depth in depths:
        result.rows.append(_deep_check(depth, result))
    flat = [row for row in result.rows if row.kind == "flat" and row.seconds > 0]
    if len(flat) >= 2:
        smallest, largest = flat[0], flat[-1]
        result.superlinear = (largest.seconds / largest.size) > 2 * (smallest.seconds / smallest.size)
    print("kind   size   seconds   rss_mb   status")
    for row in result.rows:
        print(f"{row.kind:6} {row.size:6} {row.seconds:8.4f} {row.rss_mb:8.1f} {row.status}")
    if result.superlinear:
        print("flag: time per route grows by more than 2x")
    return result
