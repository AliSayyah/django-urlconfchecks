"""Command-line entry point for ``python -m tests.fuzz``."""

from __future__ import annotations

import argparse
import sys

from .differential import run_differential
from .robustness import run_robustness
from .stress import run_stress


def _positive(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def _sizes(value):
    values = tuple(_positive(item) for item in value.split(",") if item)
    if not values:
        raise argparse.ArgumentTypeError("provide at least one size")
    return values


def _parser():
    parser = argparse.ArgumentParser(description="Fuzz django-urlconfchecks against Django")
    commands = parser.add_subparsers(dest="mode", required=True)
    differential = commands.add_parser("differential", help="compare checker flags with runtime binding")
    differential.add_argument("--seed", type=int)
    differential.add_argument("--cases", type=_positive, default=2000)
    differential.add_argument("--report")
    commands.add_parser("robustness", help="run hostile callback and converter corpus")
    stress = commands.add_parser("stress", help="measure flat and nested URLconf scaling")
    stress.add_argument("--sizes", type=_sizes, default=(10000, 50000, 100000))
    stress.add_argument("--depths", type=_sizes, default=(100, 500, 900))
    return parser


def main(argv=None):
    """Run one fuzzing mode and return its process exit code."""
    args = _parser().parse_args(argv)
    if args.mode == "differential":
        return run_differential(args.seed, args.cases, args.report).exit_code
    if args.mode == "robustness":
        return run_robustness().exit_code
    return run_stress(args.sizes, args.depths).exit_code


if __name__ == "__main__":
    sys.exit(main())
