"""Tests for the Cloud Drive Manager (feat_cloud_manager) feature.

Each test patches subprocess + input so no real rclone binary is needed and
no real cloud calls are made. The goal is to verify:
- the dashboard renders the right strings,
- the per-action routing constructs the right rclone invocations,
- destructive actions require explicit confirmation,
- Zoho never creates a rclone remote (it has no rclone backend),
- the obscure helper never returns the plaintext on failure.
"""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Patch anthropic SDK to a stub so import doesn't fail without a key
_fake_anthropic = types.ModuleType("anthropic")
sys.modules.setdefault("anthropic", _fake_anthropic)

import tuxgenie as tg


# ── helpers ──────────────────────────────────────────────────────────────────

def _fake_run_cmd(cmd_outputs):
    """Return a function that mocks tg.run_cmd by substring match on the command.

    cmd_outputs is a dict {substring_in_command: (rc, stdout, stderr)}. The
    matching is first-substring-found; if nothing matches we return (0, "", "").
    """
    def _run(cmd, timeout=60):
        for key, val in cmd_outputs.items():
            if key in cmd:
                return val
        return 0, "", ""
    return _run


def _inputs(*answers):
    """Iterator over a sequence of input() answers."""
    it = iter(answers)
    return lambda *_a, **_k: next(it)


# ── _cloud_list_remotes ──────────────────────────────────────────────────────

class TestListRemotes:
    def test_lists_two_remotes(self, monkeypatch):
        monkeypatch.setattr(tg, "run_cmd", _fake_run_cmd({
            "listremotes": (0, "workdrive:\nfamily-photos:\n", ""),
            "config dump": (0, json.dumps({
                "workdrive": {"type": "drive"},
                "family-photos": {"type": "dropbox"},
            }), ""),
        }))
        assert tg._cloud_list_remotes() == [
            ("workdrive", "drive"),
            ("family-photos", "dropbox"),
        ]

    def test_empty(self, monkeypatch):
        monkeypatch.setattr(tg, "run_cmd", _fake_run_cmd({
            "listremotes": (0, "", ""),
            "config dump": (0, "{}", ""),
        }))
        assert tg._cloud_list_remotes() == []

    def test_rclone_missing(self, monkeypatch):
        monkeypatch.setattr(tg, "run_cmd", _fake_run_cmd({
            "listremotes": (127, "", "rclone: command not found"),
        }))
        assert tg._cloud_list_remotes() == []

    def test_unknown_type_passes_through(self, monkeypatch):
        monkeypatch.setattr(tg, "run_cmd", _fake_run_cmd({
            "listremotes": (0, "weirdone:\n", ""),
            "config dump": (0, "{}", ""),
        }))
        assert tg._cloud_list_remotes() == [("weirdone", "?")]


# ── _cloud_render_dashboard ──────────────────────────────────────────────────

class TestDashboardRender:
    def test_renders_remotes(self, capsys):
        tg._cloud_render_dashboard([("workdrive", "drive"), ("photos", "dropbox")])
        out = capsys.readouterr().out
        assert "workdrive" in out
        assert "Google Drive" in out
        assert "photos" in out
        assert "Dropbox" in out
        # All 8 dashboard actions are listed
        for label in ("Add a cloud drive", "Browse a drive", "Backup to a drive",
                      "Two-way sync", "Mount as a folder", "Encrypt a drive",
                      "Remove a drive", "Zoho WorkDrive"):
            assert label in out

    def test_empty_state(self, capsys):
        tg._cloud_render_dashboard([])
        out = capsys.readouterr().out
        assert "No cloud drives connected yet" in out
        # Empty state still shows the action list so user can add one
        assert "Add a cloud drive" in out


# ── _cloud_pretty_type ───────────────────────────────────────────────────────

class TestPrettyType:
    def test_drive(self): assert tg._cloud_pretty_type("drive") == "Google Drive"
    def test_dropbox(self): assert tg._cloud_pretty_type("dropbox") == "Dropbox"
    def test_unknown(self):  assert tg._cloud_pretty_type("xyzzy") == "xyzzy"


# ── _cloud_is_headless ───────────────────────────────────────────────────────

class TestHeadless:
    def test_no_display_no_wayland_no_ssh_is_headless(self, monkeypatch):
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.delenv("SSH_CONNECTION", raising=False)
        monkeypatch.delenv("SSH_TTY", raising=False)
        assert tg._cloud_is_headless() is True

    def test_display_set_is_not_headless(self, monkeypatch):
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.delenv("SSH_CONNECTION", raising=False)
        monkeypatch.delenv("SSH_TTY", raising=False)
        assert tg._cloud_is_headless() is False

    def test_ssh_overrides_display(self, monkeypatch):
        # Even with a DISPLAY set, an SSH session means no real browser
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setenv("SSH_CONNECTION", "1.2.3.4 12345 5.6.7.8 22")
        assert tg._cloud_is_headless() is True


# ── _cloud_remove (confirmation gating) ──────────────────────────────────────

class TestRemoveRequiresConfirm:
    def test_no_confirm_no_agentic_call(self, monkeypatch):
        called = []
        monkeypatch.setattr(tg, "agentic_engine",
                            lambda *a, **k: called.append(a))
        # First input picks drive 1, second declines the confirmation
        monkeypatch.setattr("builtins.input", _inputs("1", "n"))
        tg._cloud_remove(None, {}, [], [("workdrive", "drive")])
        assert called == []   # nothing ran

    def test_confirm_calls_agentic_with_right_command(self, monkeypatch):
        prompts = []
        monkeypatch.setattr(tg, "agentic_engine",
                            lambda backend, prompt, bctx, slog: prompts.append(prompt))
        monkeypatch.setattr("builtins.input", _inputs("1", "y"))
        tg._cloud_remove(None, {}, [], [("workdrive", "drive")])
        assert len(prompts) == 1
        # The prompt must instruct the engine to run `rclone config delete <name>`
        assert "rclone config delete workdrive" in prompts[0]

    def test_pick_cancel_does_nothing(self, monkeypatch):
        called = []
        monkeypatch.setattr(tg, "agentic_engine", lambda *a, **k: called.append(a))
        monkeypatch.setattr("builtins.input", _inputs("q"))
        tg._cloud_remove(None, {}, [], [("workdrive", "drive")])
        assert called == []


# ── Zoho path never creates an rclone remote ────────────────────────────────

class TestZohoNeverCreatesRcloneRemote:
    def test_zoho_install_does_not_call_rclone_config_create(self, monkeypatch):
        prompts = []
        monkeypatch.setattr(tg, "agentic_engine",
                            lambda backend, prompt, bctx, slog: prompts.append(prompt))
        monkeypatch.setattr("builtins.input", _inputs("y"))
        tg._cloud_zoho_path(None, {}, [])
        assert len(prompts) == 1
        # CRITICAL: never pretend Zoho is an rclone backend.
        assert "rclone config create" not in prompts[0]
        # And the install hint must mention TrueSync (Zoho's actual app).
        assert "TrueSync" in prompts[0]

    def test_zoho_decline_does_nothing(self, monkeypatch):
        called = []
        monkeypatch.setattr(tg, "agentic_engine", lambda *a, **k: called.append(a))
        monkeypatch.setattr("builtins.input", _inputs("n"))
        tg._cloud_zoho_path(None, {}, [])
        assert called == []


# ── _cloud_obscure ───────────────────────────────────────────────────────────

class TestObscure:
    def test_returns_obscured_on_success(self, monkeypatch):
        class FakeRun:
            stdout = "OBSCURED\n"
            returncode = 0
        monkeypatch.setattr(tg.subprocess, "run", lambda *a, **k: FakeRun())
        assert tg._cloud_obscure("secret") == "OBSCURED"

    def test_returns_empty_on_failure(self, monkeypatch):
        class FakeRun:
            stdout = ""
            returncode = 1
        monkeypatch.setattr(tg.subprocess, "run", lambda *a, **k: FakeRun())
        # On failure we MUST NOT return the plaintext — empty string signals
        # the caller to abort.
        assert tg._cloud_obscure("secret") == ""

    def test_returns_empty_on_exception(self, monkeypatch):
        def boom(*a, **k): raise OSError("rclone not found")
        monkeypatch.setattr(tg.subprocess, "run", boom)
        assert tg._cloud_obscure("secret") == ""


# ── Add OAuth drive constructs the right command ────────────────────────────

class TestAddOauthCommand:
    def test_desktop_session_uses_browser_flow(self, monkeypatch):
        prompts = []
        monkeypatch.setattr(tg, "agentic_engine",
                            lambda backend, prompt, bctx, slog: prompts.append(prompt))
        monkeypatch.setattr(tg, "_cloud_is_headless", lambda: False)
        monkeypatch.setattr(tg, "_cloud_verify_remote", lambda _n: True)
        tg._cloud_add_oauth(None, {}, [], "workdrive",
                            {"name": "Google Drive", "type": "drive", "auth": "oauth"})
        assert len(prompts) == 1
        # On desktop we use the browser-opening form (no token=)
        assert "rclone config create workdrive drive" in prompts[0]
        assert "token=" not in prompts[0]

    def test_headless_session_uses_paste_flow(self, monkeypatch):
        prompts = []
        monkeypatch.setattr(tg, "agentic_engine",
                            lambda backend, prompt, bctx, slog: prompts.append(prompt))
        monkeypatch.setattr(tg, "_cloud_is_headless", lambda: True)
        monkeypatch.setattr(tg, "_cloud_verify_remote", lambda _n: True)
        # Token paste
        monkeypatch.setattr("builtins.input", _inputs('{"access_token":"abc"}'))
        tg._cloud_add_oauth(None, {}, [], "workdrive",
                            {"name": "Google Drive", "type": "drive", "auth": "oauth"})
        assert len(prompts) == 1
        assert "token=" in prompts[0]
        assert "rclone config create workdrive drive" in prompts[0]


# ── Backup runs dry-run BEFORE the real copy ────────────────────────────────

class TestBackupDryRunFirst:
    def test_copy_mode_runs_dry_run_first_then_real(self, tmp_path, monkeypatch):
        prompts = []
        monkeypatch.setattr(tg, "agentic_engine",
                            lambda backend, prompt, bctx, slog: prompts.append(prompt))
        # Make a real local folder so the existence check passes
        local = tmp_path / "Docs"
        local.mkdir()
        # Pick drive 1, local path, remote path, mode=1 (copy), confirm=y
        monkeypatch.setattr("builtins.input",
                            _inputs("1", str(local), "Docs", "1", "y"))
        tg._cloud_backup(None, {}, [], [("workdrive", "drive")])
        # Two engine invocations: dry-run then real
        assert len(prompts) == 2
        assert "--dry-run" in prompts[0]
        assert "--dry-run" not in prompts[1]
        # Both invocations target the chosen remote
        assert "workdrive:" in prompts[0]
        assert "workdrive:" in prompts[1]

    def test_decline_after_dry_run_skips_real(self, tmp_path, monkeypatch):
        prompts = []
        monkeypatch.setattr(tg, "agentic_engine",
                            lambda backend, prompt, bctx, slog: prompts.append(prompt))
        local = tmp_path / "Docs"
        local.mkdir()
        monkeypatch.setattr("builtins.input",
                            _inputs("1", str(local), "Docs", "1", "n"))
        tg._cloud_backup(None, {}, [], [("workdrive", "drive")])
        # Only the dry-run ran; user declined the real run
        assert len(prompts) == 1
        assert "--dry-run" in prompts[0]


# ── Browse uses lsjson and routes folder picks ──────────────────────────────

class TestBrowse:
    def test_renders_folders_from_lsjson(self, monkeypatch, capsys):
        monkeypatch.setattr(tg, "run_cmd", _fake_run_cmd({
            "lsjson": (0, json.dumps([
                {"Name": "Reports"}, {"Name": "Photos"},
            ]), ""),
        }))
        # Pick drive 1, then quit
        monkeypatch.setattr("builtins.input", _inputs("1", "q"))
        tg._cloud_browse([("workdrive", "drive")])
        out = capsys.readouterr().out
        assert "Reports" in out
        assert "Photos" in out


# ── Provider catalog sanity (no duplicate IDs, all required keys present) ───

class TestProviderCatalog:
    def test_ids_unique(self):
        ids = [p["id"] for p in tg.CLOUD_PROVIDERS]
        assert len(ids) == len(set(ids))

    def test_every_provider_has_required_keys(self):
        for p in tg.CLOUD_PROVIDERS:
            for k in ("id", "name", "type", "auth"):
                assert k in p, f"{p['name']} missing key {k}"

    def test_auth_is_known(self):
        for p in tg.CLOUD_PROVIDERS:
            assert p["auth"] in {"oauth", "creds", "s3"}


# ── Feature is registered in the menu ───────────────────────────────────────

class TestFeatureRegistered:
    def test_in_menu_items(self):
        keys = [row[0] for row in tg.MENU_ITEMS]
        aliases = [row[1] for row in tg.MENU_ITEMS]
        assert "88" in keys
        assert "cloud" in aliases

    def test_function_bound(self):
        for row in tg.MENU_ITEMS:
            if row[0] == "88":
                assert row[4] is tg.feat_cloud_manager
                return
        pytest.fail("88 not in MENU_ITEMS")
