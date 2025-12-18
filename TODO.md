# Roadmap / Ideas

## Ready to Build (high value, low risk)
- **Severity gating flags**: Add `--fail-on [warning|error]` and `--no-warnings` so CI can be strict or lenient without code changes.
- **Deduplicate converter warnings**: Emit unknown-converter (W002) only once per converter class per run to keep logs readable on large URL sets.
- **Output ergonomics**: Group findings by module/view, sort by severity, and prepend a short summary block (counts + top offenders) in human mode.
- **Inline tips**: When raising E002/E005, include the expected type/shape and the offending type/value to reduce guesswork.

## Nice-to-Have (adoption & DX)
- **Discovery command**: `urlconfchecks --list-routes` to show routes and inferred types, aiding onboarding and debugging.
- **Settings hinting**: Add `--settings` option and clearer error messaging when Django settings aren’t configured.
- **Export formats**: Support `--format sarif` (and/or `jsonlines`) so findings integrate with GitHub Code Scanning and other tooling.
- **Pre-commit quick mode**: `--changed-only` to check only routes touched in the current git diff for faster local/CI runs.

## Deprioritized / Won’t Do Now
- **RegexPattern support**: Legacy and deprecated in Django; skip with a single informational warning rather than full parsing.
