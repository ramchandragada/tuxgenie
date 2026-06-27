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
    def test_no_confirm_no_command_runs(self, monkeypatch):
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda *a, **k: runs.append(a) or (0, "", ""))
        # First input picks drive 1, second declines the in-feature confirmation
        monkeypatch.setattr("builtins.input", _inputs("1", "n"))
        tg._cloud_remove(None, {}, [], [("workdrive", "drive")])
        assert runs == []   # nothing ran

    def test_confirm_runs_right_command(self, monkeypatch):
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda cmd, *a, **k: runs.append(cmd) or (0, "", ""))
        monkeypatch.setattr("builtins.input", _inputs("1", "y"))
        tg._cloud_remove(None, {}, [], [("workdrive", "drive")])
        assert len(runs) == 1
        assert "rclone config delete workdrive" in runs[0]

    def test_pick_cancel_does_nothing(self, monkeypatch):
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda *a, **k: runs.append(a) or (0, "", ""))
        monkeypatch.setattr("builtins.input", _inputs("q"))
        tg._cloud_remove(None, {}, [], [("workdrive", "drive")])
        assert runs == []


# ── Zoho path never creates an rclone remote ────────────────────────────────

class TestZohoNeverCreatesRcloneRemote:
    def test_zoho_install_never_creates_rclone_remote(self, monkeypatch, tmp_path):
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda cmd, *a, **k: runs.append(cmd) or (0, "", ""))
        monkeypatch.setattr(tg, "run_cmd", lambda *a, **k: (0, "", ""))
        # Stub the URL-detection so the test doesn't hit the network
        monkeypatch.setattr(tg, "_zoho_find_truesync_deb_url", lambda: None)
        monkeypatch.setattr(tg, "_watch_downloads_for_deb",
                            lambda *a, **k: None)
        # No real browser
        monkeypatch.setattr(tg.subprocess, "Popen", lambda *a, **k: None)
        # Make a fake .deb so the existence check passes
        fake_deb = tmp_path / "zoho.deb"
        fake_deb.write_bytes(b"fake")
        # answer "y" to install, then provide path to fake deb when prompted
        monkeypatch.setattr("builtins.input", _inputs("y", str(fake_deb)))
        tg._cloud_zoho_path(None, {}, [])
        # CRITICAL: never construct an rclone backend for Zoho
        for cmd in runs:
            assert "rclone config create" not in cmd
            assert "rclone " not in cmd or "rclone obscure" in cmd
        # And the install path must use dpkg (TrueSync .deb), not rclone
        assert any("dpkg -i" in c for c in runs)

    def test_zoho_decline_does_nothing(self, monkeypatch):
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda *a, **k: runs.append(a) or (0, "", ""))
        monkeypatch.setattr("builtins.input", _inputs("n"))
        tg._cloud_zoho_path(None, {}, [])
        assert runs == []


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
        runs = []
        # Desktop OAuth goes through the streaming helper, not _cloud_run
        monkeypatch.setattr(tg, "_run_oauth_with_browser_open",
                            lambda cmd, prov_name, timeout=600: runs.append(cmd) or 0)
        monkeypatch.setattr(tg, "_cloud_is_headless", lambda: False)
        monkeypatch.setattr(tg, "_cloud_verify_remote", lambda _n: True)
        # User says yes to "Start sign-in?"
        monkeypatch.setattr("builtins.input", _inputs("y"))
        tg._cloud_add_oauth(None, {}, [], "workdrive",
                            {"name": "Google Drive", "type": "drive", "auth": "oauth"})
        assert len(runs) == 1
        # On desktop we use the browser-opening form (no token=)
        assert "rclone config create workdrive drive" in runs[0]
        assert "token=" not in runs[0]

    def test_headless_session_uses_paste_flow(self, monkeypatch):
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda cmd, *a, **k: runs.append(cmd) or (0, "", ""))
        monkeypatch.setattr(tg, "_cloud_is_headless", lambda: True)
        monkeypatch.setattr(tg, "_cloud_verify_remote", lambda _n: True)
        # Token paste
        monkeypatch.setattr("builtins.input", _inputs('{"access_token":"abc"}'))
        tg._cloud_add_oauth(None, {}, [], "workdrive",
                            {"name": "Google Drive", "type": "drive", "auth": "oauth"})
        assert len(runs) == 1
        assert "token=" in runs[0]
        assert "rclone config create workdrive drive" in runs[0]


# ── Backup runs dry-run BEFORE the real copy ────────────────────────────────

class TestBackupDryRunFirst:
    def test_copy_mode_runs_dry_run_first_then_real(self, tmp_path, monkeypatch):
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda cmd, *a, **k: runs.append(cmd) or (0, "", ""))
        local = tmp_path / "Docs"
        local.mkdir()
        # Pick drive 1, local path, remote path, mode=1 (copy), confirm=y
        monkeypatch.setattr("builtins.input",
                            _inputs("1", str(local), "Docs", "1", "y"))
        tg._cloud_backup(None, {}, [], [("workdrive", "drive")])
        # Two runs: dry-run then real
        assert len(runs) == 2
        assert "--dry-run" in runs[0]
        assert "--dry-run" not in runs[1]
        assert "workdrive:" in runs[0]
        assert "workdrive:" in runs[1]

    def test_decline_after_dry_run_skips_real(self, tmp_path, monkeypatch):
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda cmd, *a, **k: runs.append(cmd) or (0, "", ""))
        local = tmp_path / "Docs"
        local.mkdir()
        monkeypatch.setattr("builtins.input",
                            _inputs("1", str(local), "Docs", "1", "n"))
        tg._cloud_backup(None, {}, [], [("workdrive", "drive")])
        # Only the dry-run ran; user declined the real run
        assert len(runs) == 1
        assert "--dry-run" in runs[0]


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

class TestWorksWithoutAPIKey:
    """The whole Cloud Sync feature must work even when the user has no API
    credits. We achieved this by routing through _cloud_run (direct execution
    with an approval prompt) instead of agentic_engine. This test guards that
    by asserting no cloud helper calls agentic_engine."""

    def test_install_rclone_does_not_call_agentic_engine(self, monkeypatch):
        called = []
        monkeypatch.setattr(tg, "agentic_engine", lambda *a, **k: called.append(a))
        monkeypatch.setattr(tg, "_cloud_run", lambda *a, **k: (0, "", ""))
        monkeypatch.setattr(tg, "_cloud_rclone_installed", lambda: False)
        # User picks [1] Install rclone
        monkeypatch.setattr("builtins.input", _inputs("1"))
        tg._cloud_ensure_rclone(None, {}, [])
        assert called == []

    def test_remove_does_not_call_agentic_engine(self, monkeypatch):
        called = []
        monkeypatch.setattr(tg, "agentic_engine", lambda *a, **k: called.append(a))
        monkeypatch.setattr(tg, "_cloud_run", lambda *a, **k: (0, "", ""))
        monkeypatch.setattr("builtins.input", _inputs("1", "y"))
        tg._cloud_remove(None, {}, [], [("workdrive", "drive")])
        assert called == []

    def test_backup_does_not_call_agentic_engine(self, monkeypatch, tmp_path):
        called = []
        monkeypatch.setattr(tg, "agentic_engine", lambda *a, **k: called.append(a))
        monkeypatch.setattr(tg, "_cloud_run", lambda *a, **k: (0, "", ""))
        local = tmp_path / "Docs"
        local.mkdir()
        monkeypatch.setattr("builtins.input",
                            _inputs("1", str(local), "Docs", "1", "y"))
        tg._cloud_backup(None, {}, [], [("workdrive", "drive")])
        assert called == []


class TestWatchDownloadsForDeb:
    """The watcher is a simple polling loop; verify just that the function
    exists, accepts the right extensions, and times out cleanly. We skip
    mocking the time.sleep loop — too fragile to be worth the test complexity."""

    def test_function_exists(self):
        assert callable(getattr(tg, "_watch_downloads_for_deb", None))

    def test_accepts_extensions_kwarg(self):
        # The function signature must accept extensions= so the Zoho path
        # can pass (.deb, .tar.gz, .tgz)
        import inspect
        sig = inspect.signature(tg._watch_downloads_for_deb)
        assert "extensions" in sig.parameters
        # And the default must include both .deb and .tar.gz
        default = sig.parameters["extensions"].default
        # default is None — actual tuple is built inside; just confirm the
        # body covers tar.gz by reading its source
        src = inspect.getsource(tg._watch_downloads_for_deb)
        assert ".tar.gz" in src

    def test_returns_none_on_immediate_timeout(self, tmp_path, monkeypatch):
        watch = tmp_path / "Downloads"
        watch.mkdir()
        monkeypatch.setattr(tg.time, "sleep", lambda _s: None)
        first = [True]
        def jumpy_time():
            if first[0]:
                first[0] = False
                return 0.0
            return 1000.0
        monkeypatch.setattr(tg.time, "time", jumpy_time)
        assert tg._watch_downloads_for_deb(str(watch), r"zoho", timeout=10) is None


class TestZohoInstallTarball:
    """Verify the .tar.gz extraction flow without running it as root."""

    def _make_tarball(self, tmp_path, with_install_sh=False, with_binary=False):
        """Create a fake TrueSync tarball at <tmp>/zoho.tar.gz."""
        import tarfile
        src = tmp_path / "src" / "ZohoWorkDriveTrueSync"
        src.mkdir(parents=True)
        if with_install_sh:
            (src / "install.sh").write_text("#!/bin/bash\necho ok\n")
        if with_binary:
            (src / "truesync").write_text("#!/bin/bash\nexec true\n")
        tar = tmp_path / "zoho.tar.gz"
        with tarfile.open(tar, "w:gz") as tf:
            tf.add(src, arcname="ZohoWorkDriveTrueSync")
        return tar

    def test_runs_install_sh_when_present(self, tmp_path, monkeypatch):
        tar = self._make_tarball(tmp_path, with_install_sh=True)
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda cmd, *a, **k: runs.append(cmd) or (0, "", ""))
        monkeypatch.setattr(tg, "run_cmd", lambda *a, **k: (0, "", ""))
        ok = tg._zoho_install_tarball(str(tar))
        assert ok
        # Must run the install.sh via bash, not dpkg
        assert any("install.sh" in c for c in runs)
        assert not any("dpkg" in c for c in runs)

    def test_falls_back_to_opt_copy_when_no_installer(self, tmp_path, monkeypatch):
        tar = self._make_tarball(tmp_path, with_binary=True)
        runs = []
        monkeypatch.setattr(tg, "_cloud_run",
                            lambda cmd, *a, **k: runs.append(cmd) or (0, "", ""))
        # run_cmd is used to test for binary existence — return 0 for truesync
        monkeypatch.setattr(tg, "run_cmd",
                            lambda cmd, *a, **k: (0 if "truesync" in cmd else 1, "", ""))
        ok = tg._zoho_install_tarball(str(tar))
        assert ok
        # Must copy to /opt and create the symlink
        assert any("/opt/zoho-truesync" in c for c in runs)
        assert any("ln -sf" in c for c in runs)

    def test_returns_false_on_bad_tarball(self, tmp_path, monkeypatch):
        bad = tmp_path / "not-a-tar.tar.gz"
        bad.write_bytes(b"this is not a tarball")
        monkeypatch.setattr(tg, "_cloud_run", lambda *a, **k: (0, "", ""))
        monkeypatch.setattr(tg, "run_cmd", lambda *a, **k: (1, "", ""))
        assert tg._zoho_install_tarball(str(bad)) is False


class TestZohoTrueSyncAutoDetect:
    def test_finds_deb_url_in_html(self, monkeypatch):
        # The page returns one direct .deb link in raw HTML
        html = ('<html><body>'
                '<a href="https://downloads.zohocdn.com/x/ZohoWorkDrive-TrueSync_amd64.deb">Linux 64-bit</a>'
                '</body></html>')
        class FakeResp:
            def read(self): return html.encode("utf-8")
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(tg.urllib.request, "urlopen",
                            lambda *a, **k: FakeResp())
        # All HEAD checks succeed
        monkeypatch.setattr(tg, "_url_is_alive", lambda url, timeout=10: True)
        found = tg._zoho_find_truesync_deb_url()
        assert found == "https://downloads.zohocdn.com/x/ZohoWorkDrive-TrueSync_amd64.deb"

    def test_returns_none_when_page_has_no_deb_link(self, monkeypatch):
        html = "<html><body>No links here</body></html>"
        class FakeResp:
            def read(self): return html.encode("utf-8")
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(tg.urllib.request, "urlopen",
                            lambda *a, **k: FakeResp())
        monkeypatch.setattr(tg, "_url_is_alive", lambda url, timeout=10: True)
        assert tg._zoho_find_truesync_deb_url() is None

    def test_ranks_zoho_truesync_url_highest(self, monkeypatch):
        # Page links a generic .deb AND a Zoho TrueSync one — TrueSync wins
        html = ('<html>'
                '<a href="https://example.com/random.deb">Other</a>'
                '<a href="https://zoho.com/workdrive/truesync_linux_amd64.deb">TrueSync</a>'
                '</html>')
        class FakeResp:
            def read(self): return html.encode("utf-8")
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(tg.urllib.request, "urlopen",
                            lambda *a, **k: FakeResp())
        monkeypatch.setattr(tg, "_url_is_alive", lambda url, timeout=10: True)
        found = tg._zoho_find_truesync_deb_url()
        assert "truesync" in found.lower()
        assert "random" not in found.lower()

    def test_falls_back_when_url_is_dead(self, monkeypatch):
        # The HTML lists a .deb but it 404s — function should return None
        html = '<html><a href="https://zoho.com/truesync.deb">x</a></html>'
        class FakeResp:
            def read(self): return html.encode("utf-8")
            def __enter__(self): return self
            def __exit__(self, *a): pass
        monkeypatch.setattr(tg.urllib.request, "urlopen",
                            lambda *a, **k: FakeResp())
        monkeypatch.setattr(tg, "_url_is_alive", lambda url, timeout=10: False)
        assert tg._zoho_find_truesync_deb_url() is None


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
