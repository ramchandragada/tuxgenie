# TuxGenie — Claude Code Instructions

## Branching & Release Rule (CRITICAL)

Browser sessions always start on a feature branch (e.g. `claude/browser-editing-tuxgenie-*`).

**After every set of changes is complete, always:**
1. Merge the feature branch into `main`
2. Push `main` to origin
3. The `release.yml` GitHub Actions workflow will then automatically build the `.deb`, tag the release, and publish it so all users can update via `u`

Never leave changes stranded on the feature branch — the user needs all changes on `main` to reach users.

## Project Overview

TuxGenie is a single-file AI-powered Linux assistant (`tuxgenie.py`, ~7500 lines).
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
| `.github/workflows/release.yml` | Auto-builds + publishes release on push to main |
| `.github/workflows/ci.yml` | Runs tests + linting on PRs |

## Versioning

- Version lives in **one source of truth**: `__version__` in `tuxgenie.py`
- Also update `pyproject.toml` version to match
- `create_deb.py` reads version from env var `TUXGENIE_VERSION` (CI sets this from the git tag)
- Bump minor version (e.g. 4.6.0 → 4.7.0) for new features or fixes

## Release Gate — MANDATORY on every version bump

**No version ships unless it passes the gate.** Every time `__version__` is
bumped, the change MUST pass, before it is committed/pushed:

1. `ruff check tuxgenie.py` — clean (lint is enforced; a lint error blocks the release)
2. `pytest tests/` — all pass, **including `tests/test_fundamentals.py`**, which
   asserts the app's core promises: version sync (`__version__` == `pyproject.toml`),
   the banner renders, all free backends construct, catalog + menu integrity,
   dangerous-command blocking, secret scrubbing, and cross-distro prompt adaptation.

This is enforced automatically in `release.yml` (the "Release gate" step): if lint
or tests fail, the `.deb`/wheel are never built and nothing is published. Always run
`ruff check tuxgenie.py && pytest tests/` locally before pushing a version bump —
never rely on the gate alone to catch a mistake.

When adding a genuinely new fundamental guarantee, add a test for it to
`tests/test_fundamentals.py` so the gate keeps protecting it.

## Cross-distro support

TuxGenie must work for **every** Linux user, not just Debian/Ubuntu:
- The AI engine adapts to the detected package manager (`base_ctx()['pkg_mgr']`:
  apt/dnf/pacman/zypper/apk/…). Never hard-code apt in AI guidance.
- First-run setup (`_first_run_setup_steps`) is distro-aware: updates, essentials,
  codecs, Flatpak+Flathub, firewall, NTP — never apt-only.
- Catalog installs are distro-adapted via `_distro_adapt_prompt()` (Flatpak/native
  on non-Debian). Prefer a Flathub app-id in new catalog entries so they work everywhere.
- Universal install: `docs/install.sh` (curl | bash) — `.deb` on Debian-family,
  wheel/PyPI elsewhere. `u` self-update handles both `.deb` and pip installs.
- Note: Flatpak sandboxing is a poor fit for packaging *TuxGenie itself* (needs
  host sudo/apt); Flathub is for *catalog apps*, not the assistant binary.

## Provider startup priority (load_backend)

At every start the provider is chosen by PRIORITY, not by what was last used:
1. **Claude** only when the user explicitly connected it (`provider == "claude"`
   with a key) — then it's sticky. `main()` warns that free options exist.
2. **Ollama** sticky when the user explicitly chose local AI (`provider == "ollama"`)
   AND the local daemon is reachable (Phase C — privacy / offline).
3. Otherwise **always prefer free Gemini, then free OpenAI-compatible cloud
   providers in registry order (Groq, SambaNova, OpenRouter), then Ollama if
   reachable** — regardless of the last saved free cloud provider. Gemini is the
   default whenever its key is present; if only one free key exists, start with
   that provider.
4. If the only key present is Claude's, use it (with the same free-switch hint).

Auto-failover during a session is still free→free only (Gemini → Groq → … →
Ollama when running) and never *silently* uses Claude. But when the whole free
rotation is exhausted and a Claude key is connected, TuxGenie **offers** to
finish the task on Claude — paid, so only after an explicit "yes"
(`_offer_claude_fallback`). It never spends on Claude without consent.
`tests/test_fundamentals`/`test_tuxgenie` lock this.

## Phase C — Local AI + real snapshots

- **Ollama** is a first-class free backend (`_OAI_PROVIDERS["ollama"]`, no API key).
  Settings → 8, setup wizard, and phrases like "use ollama" / "local ai".
- **Config snapshots** (menu 16): create / list / restore `.tar.gz` + JSON
  manifest under `~/.local/share/tuxgenie/backups/`.
- **Undo** (menu 17): restore a snapshot, or deterministic reverse of known
  session commands, with optional AI for leftovers.

## Phase D — Beginner GUI

- `tuxgenie --gui` opens a Tk beginner launcher (needs `python3-tk`).
- Desktop entry (`tuxgenie-gui`) tries `--gui` first; exit 2 falls back to
  VTE app window / terminal (no rewrite of CLI features).
- Buttons shell out to `tuxgenie --feature …`, plain-English one-shots, or
  `--self-update`. "Full assistant" opens `tuxgenie-app` / interactive CLI —
  never re-enters `tuxgenie-gui` (avoids a GUI loop).

## Cost Optimisation Principles

- Default model: Haiku (cheapest). Escalate to Sonnet only on failure.
- Common commands (apt, systemctl, etc.) bypass Claude entirely via `try_passthrough()`
- Never add Claude calls where direct execution suffices
