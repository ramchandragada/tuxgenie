# TuxGenie — Claude Code Instructions

## Branching & Release Rule (CRITICAL)

Browser sessions always start on a feature branch (e.g. `claude/browser-editing-tuxgenie-*`).

**After every set of changes is complete, always:**
1. Merge the feature branch into `main`
2. Push `main` to origin
3. The `auto-release.yml` GitHub Actions workflow will then automatically build the `.deb`, tag the release, and publish it so all users can update via `u`

Never leave changes stranded on the feature branch — the user needs all changes on `main` to reach users.

## Project Overview

TuxGenie is a single-file AI-powered Linux assistant (`tuxgenie.py`, ~3000 lines).
- Powered by Claude (Haiku by default, Sonnet on failure)
- Distributed as a `.deb` package built by `create_deb.py`
- Users update via the `u` command inside tuxgenie (fetches from GitHub Releases API)

## Key Files

| File | Purpose |
|------|---------|
| `tuxgenie.py` | Main script — all features, UI, AI engine |
| `create_deb.py` | Builds the `.deb` package (pure stdlib, no dpkg-deb needed) |
| `install.sh` | User-facing installer for double-click installs |
| `pyproject.toml` | PyPI metadata |
| `.github/workflows/auto-release.yml` | Auto-builds + publishes release on push to main |
| `.github/workflows/ci.yml` | Runs tests + linting on PRs |

## Versioning

- Version lives in **one source of truth**: `__version__` in `tuxgenie.py`
- Also update `pyproject.toml` version to match
- `create_deb.py` reads version from env var `TUXGENIE_VERSION` (CI sets this from the git tag)
- Bump minor version (e.g. 4.6.0 → 4.7.0) for new features or fixes

## Cost Optimisation Principles

- Default model: Haiku (cheapest). Escalate to Sonnet only on failure.
- Common commands (apt, systemctl, etc.) bypass Claude entirely via `try_passthrough()`
- Never add Claude calls where direct execution suffices
