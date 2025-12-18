# Configuration

You can set defaults for `django-urlconfchecks` in your `pyproject.toml` so teams don’t have to repeat CLI flags.

```toml
[tool.urlconfchecks]
# Suppress human-readable output; exit codes still reflect errors.
quiet = true

# Output format. Supported: "json" (default remains human output).
format = "json"

# Merge additional silencers with built-in defaults.
# Key: glob for view import path; Value: comma-separated error codes.
silenced_views = { "myproj.views.legacy_view" = "E002" }
```

Notes

- CLI flags always win: `urlconfchecks --quiet` overrides `quiet = false` and vice versa.
- You can point to a specific config file with `URLCONFCHECKS_PYPROJECT=/path/to/pyproject.toml`.
- Built-in silencers (e.g., Django contrib views without type hints) stay active; custom silencers are merged.
