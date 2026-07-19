"""
Tests for tuxgenie.py core logic.
Run with: pytest tests/
"""
import json
import os
import sys
import tempfile

import pytest

# Make tuxgenie importable without running main()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Patch out the SDK import so tests don't need a real API key
import types
_fake_anthropic = types.ModuleType("anthropic")
sys.modules.setdefault("anthropic", _fake_anthropic)

import tuxgenie as tg


# ── is_dangerous ─────────────────────────────────────────────────────────────

class TestIsDangerous:
    def test_rm_rf_root(self):
        assert tg.is_dangerous("rm -rf /")

    def test_rm_rf_subpath(self):
        # rm -rf on a specific subpath — should NOT match the root-only pattern
        assert not tg.is_dangerous("rm -rf /tmp/mydir")

    def test_dd(self):
        assert tg.is_dangerous("dd if=/dev/zero of=/dev/sda")

    def test_mkfs(self):
        assert tg.is_dangerous("mkfs.ext4 /dev/sdb1")

    def test_fdisk(self):
        assert tg.is_dangerous("fdisk /dev/sda")

    def test_wipefs(self):
        assert tg.is_dangerous("wipefs -a /dev/sda")

    def test_shred(self):
        assert tg.is_dangerous("shred -u /dev/sdb")

    def test_fork_bomb(self):
        assert tg.is_dangerous(":(){ :|:& };:")    # with spaces (common form)

    def test_chmod_777_root(self):
        assert tg.is_dangerous("chmod 777 /")

    def test_chmod_recursive_777_root(self):
        assert tg.is_dangerous("chmod -R 777 /")

    def test_safe_command(self):
        assert not tg.is_dangerous("ls -la /home")

    def test_safe_apt(self):
        assert not tg.is_dangerous("apt update && apt upgrade -y")

    def test_safe_systemctl(self):
        assert not tg.is_dangerous("systemctl restart nginx")

    # ── Regression: argv-level bypasses that the regex-only filter missed ──────
    @pytest.mark.parametrize("cmd", [
        "rm -rf /*",                       # glob target
        "rm -Rf /",                        # capital R
        "rm -rfv /etc",                    # extra flag letter + system dir
        "rm -r -f /",                      # split flags
        "rm --recursive --force /",        # long options
        "rm -rf --no-preserve-root /",     # explicit override, flag before path
        "rm -rf /etc/*",                   # system dir via glob
        "rm -rf /home",                    # top-level dir
        "rm -r /usr",                      # recursive without force
        "sudo rm -rf /var",                # sudo prefix
        "dd of=/dev/sda if=/dev/zero",     # of= before if=
        "sudo dd of=/dev/nvme0n1 if=/dev/zero",
        "find / -delete",                  # recursive delete of everything
        "find /var -exec rm {} +",         # exec rm from a system root
        "chmod 0777 /",                    # octal-leading-zero
        "chmod 777 /etc",                  # world-writable system dir
        "echo x | sudo tee /dev/sda",      # device overwrite via tee
        "chown -R root:root /",            # recursive chown of /
        "ls; rm -rf /*",                   # chained after a benign command
        "cd /tmp && rm -rf /",             # chained with &&
        # Recursive rm of a path *inside* a critical system dir bricks the box.
        "rm -rf /boot/grub",               # unbootable
        "rm -rf /usr/bin",                 # deletes core binaries
        "rm -rf /var/lib/dpkg",            # destroys package DB
        "rm -rf /etc/nginx",               # system config subtree
    ])
    def test_blocks_known_bypasses(self, cmd):
        assert tg.is_dangerous(cmd), f"should be BLOCKED: {cmd!r}"

    @pytest.mark.parametrize("cmd", [
        "rm -rf /home/user/project/node_modules",  # user-data sub-path
        "rm -rf build/",
        "rm -rf ./dist",
        "rm -rf /home/user/.cache",
        "rm -f /tmp/foo.log",
        "rm -rf /tmp/build",               # /tmp is not a critical system dir
        "find /tmp -name '*.log' -delete", # delete under a safe root
        "chmod -R 755 /home/user/app",
        "chmod 644 /etc/nginx/nginx.conf", # single file, not the dir
        "dd if=/dev/zero of=/tmp/disk.img bs=1M count=100",  # writing to a file
        "chown -R user:user /home/user/app",
        "tee /tmp/out.txt",
    ])
    def test_allows_legitimate_commands(self, cmd):
        assert not tg.is_dangerous(cmd), f"should be ALLOWED: {cmd!r}"


# ── _version_gap (update severity) ───────────────────────────────────────────

class TestVersionGap:
    def test_patch_bump(self):
        assert tg._version_gap("5.79.0", "5.79.1") == 1

    def test_minor_bump(self):
        assert tg._version_gap("5.79.0", "5.80.0") == 1

    def test_same_version(self):
        assert tg._version_gap("5.79.0", "5.79.0") == 0

    def test_downgrade_is_zero(self):
        assert tg._version_gap("5.79.0", "5.78.0") == 0

    def test_major_bump_forces_update(self):
        # Regression: a major bump whose minor is smaller must NOT cancel out.
        assert tg._version_gap("5.79.0", "6.0.0") >= 10
        assert tg._version_gap("5.79.0", "6.5.0") >= 10
        assert tg._version_gap("5.79.0", "7.0.0") >= 10

    def test_ver_tolerates_suffix_and_v_prefix(self):
        assert tg._ver("5.80.0") == (5, 80, 0)
        assert tg._ver("v5.80.0") == (5, 80, 0)
        assert tg._ver("5.80.0-rc1") == (5, 80, 0)  # not (0,) — would hide updates
        assert tg._ver("5.80.0-rc1") > tg._ver("5.79.0")


# ── Update download verification ─────────────────────────────────────────────

class TestDownloadVerified:
    def _serve(self, monkeypatch, payload):
        import io, contextlib

        class _Resp(io.BytesIO):
            def __init__(self, data):
                super().__init__(data)
                self.headers = {"Content-Length": str(len(data))}
            def read(self, n=-1):
                return super().read(n)

        @contextlib.contextmanager
        def fake_urlopen(url, timeout=0):
            yield _Resp(payload)

        monkeypatch.setattr(tg.urllib.request, "urlopen", fake_urlopen)

    def test_good_digest_passes(self, monkeypatch, tmp_path):
        import hashlib
        payload = b"fake-deb-contents"
        self._serve(monkeypatch, payload)
        digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        dest = str(tmp_path / "x.deb")
        ok, reason = tg._download_verified("http://x/y.deb", dest, digest)
        assert ok, reason

    def test_bad_digest_fails(self, monkeypatch, tmp_path):
        self._serve(monkeypatch, b"tampered-contents")
        dest = str(tmp_path / "x.deb")
        ok, reason = tg._download_verified("http://x/y.deb", dest, "sha256:" + "0" * 64)
        assert not ok and "checksum" in reason

    def test_no_digest_still_ok(self, monkeypatch, tmp_path):
        # Backward-compat: releases without a digest still install (completeness only).
        self._serve(monkeypatch, b"some-bytes")
        dest = str(tmp_path / "x.deb")
        ok, reason = tg._download_verified("http://x/y.deb", dest, None)
        assert ok, reason

    def test_empty_download_fails(self, monkeypatch, tmp_path):
        self._serve(monkeypatch, b"")
        dest = str(tmp_path / "x.deb")
        ok, reason = tg._download_verified("http://x/y.deb", dest, None)
        assert not ok


# ── Crash guard: healthy-checkpoint semantics ────────────────────────────────

class TestCrashGuard:
    def setup_method(self):
        self._orig = tg.CRASH_FILE
        self._tmp = tempfile.mkdtemp()
        tg.CRASH_FILE = os.path.join(self._tmp, "crash.json")

    def teardown_method(self):
        tg.CRASH_FILE = self._orig

    def test_startup_increments_and_checkpoint_resets(self):
        # First run of a version starts the counter at 1.
        tg._crash_guard()
        assert tg._crash_read().get("crashes") == 1
        # A second startup without reaching the healthy checkpoint increments
        # (this is the "crashed during startup again" case).
        tg._crash_guard()
        assert tg._crash_read().get("crashes") == 2
        # Reaching the healthy checkpoint clears it — so a normal run that
        # started fine never accumulates toward a rollback.
        tg._crash_mark_clean()
        assert tg._crash_read().get("crashes") == 0

    def _placeholder(self):
        pass


# ── Catalog integrity (Install Apps [77] / AI Tools [99]) ────────────────────

class TestCatalogs:
    @pytest.mark.parametrize("name", ["APP_CATALOG", "AI_CATALOG"])
    def test_ids_unique_and_contiguous(self, name):
        cat = getattr(tg, name)
        ids = [e["id"] for e in cat]
        assert len(ids) == len(set(ids)), f"{name} has duplicate ids"
        # Contiguous 1..N so ranges like '1-N' select every entry, and the
        # picker's max_id == len(catalog) validation lets every id through.
        assert sorted(ids) == list(range(1, len(cat) + 1)), f"{name} ids not contiguous 1..N"

    @pytest.mark.parametrize("name", ["APP_CATALOG", "AI_CATALOG"])
    def test_entries_well_formed(self, name):
        for e in getattr(tg, name):
            for key in ("id", "name", "cat", "prompt", "desc"):
                assert str(e.get(key, "")).strip(), f"{name} id {e.get('id')} missing {key}"

    def test_selection_parses_full_range(self):
        # 'select all' must map to every catalog id.
        ids = tg._parse_app_selection(f"1-{len(tg.APP_CATALOG)}", max_id=len(tg.APP_CATALOG))
        assert ids == list(range(1, len(tg.APP_CATALOG) + 1))

    def test_new_headliners_present(self):
        app_names = {e["name"] for e in tg.APP_CATALOG}
        ai_names = {e["name"] for e in tg.AI_CATALOG}
        assert {"Bitwarden", "Syncthing", "Lutris", "Wireshark"} <= app_names
        assert {"Cursor", "Windsurf", "Zed", "GitHub Copilot CLI"} <= ai_names


class TestCatalogSearch:
    def _drive(self, monkeypatch, catalog, inputs):
        import io, contextlib
        calls = []
        monkeypatch.setattr(tg, "agentic_engine", lambda *a, **k: calls.append(a))
        it = iter(inputs)
        monkeypatch.setattr("builtins.input", lambda *a, **k: next(it))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tg._run_catalog_picker(None, {}, [], catalog=catalog, title="T",
                                   intro="i", item_label="item(s)", history_tag="x")
        return buf.getvalue(), calls

    def test_search_filters_and_shows_header(self, monkeypatch):
        out, calls = self._drive(monkeypatch, tg.APP_CATALOG, ["photo", "q"])
        assert "result(s) for 'photo'" in out
        assert "RawTherapee" in out          # a photo tool surfaces
        assert calls == []                   # searching never installs

    def test_search_then_cancel_does_not_install(self, monkeypatch):
        out, calls = self._drive(monkeypatch, tg.APP_CATALOG, ["photo", "80", "n"])
        assert calls == []

    def test_no_match_falls_back_to_all(self, monkeypatch):
        out, _ = self._drive(monkeypatch, tg.APP_CATALOG, ["zznope", "q"])
        assert "Nothing matches" in out

    def test_word_finds_ai_tool(self, monkeypatch):
        out, _ = self._drive(monkeypatch, tg.AI_CATALOG, ["cursor", "q"])
        assert "Cursor" in out and "result(s) for 'cursor'" in out


class TestCrashGuardExtra:
    def setup_method(self):
        self._orig = tg.CRASH_FILE
        self._tmp = tempfile.mkdtemp()
        tg.CRASH_FILE = os.path.join(self._tmp, "crash.json")

    def teardown_method(self):
        tg.CRASH_FILE = self._orig

    def test_no_atexit_registration(self):
        # Regression: the counter must NOT be reset via atexit (that reset it
        # even after a real crash, and missed SIGTERM). Ensure _crash_guard
        # does not register an atexit handler.
        import atexit
        seen = []
        orig = atexit.register
        try:
            atexit.register = lambda f, *a, **k: seen.append(f) or orig(f, *a, **k)
            tg._crash_guard()
        finally:
            atexit.register = orig
        assert tg._crash_mark_clean not in seen


# ── Approval gate: read-only detection ───────────────────────────────────────

class TestIsReadOnly:
    @pytest.mark.parametrize("cmd", [
        "systemctl status nginx",
        "journalctl -xe",
        "ls -la /etc",
        "cat /etc/os-release",
        "ps aux | grep python",
        "df -h",
        "ip addr show",
        "docker ps",
        "git status",
        "apt list --installed",
        "dpkg -l",
        "grep -r foo /var/log",
        "find /tmp -name '*.log'",
    ])
    def test_read_only_true(self, cmd):
        assert tg._is_read_only(cmd), f"should be read-only: {cmd!r}"

    @pytest.mark.parametrize("cmd", [
        "systemctl restart nginx",         # mutating sub-command
        "apt install cowsay",              # install
        "sudo systemctl status nginx",     # sudo → always confirm
        "rm -f /tmp/x",                    # not in read-only set
        "docker rm mycontainer",           # mutating
        "git push origin main",            # mutating
        "echo hi > /etc/foo",              # redirection = write
        "sed -i s/a/b/ file",              # in-place edit (sed not read-only)
        "find / -delete",                  # destructive find
        "ip link set eth0 down",           # mutating ip
        "dpkg -i pkg.deb",                 # install
        "sysctl -w vm.swappiness=10",      # write
    ])
    def test_read_only_false(self, cmd):
        assert not tg._is_read_only(cmd), f"should NOT be read-only: {cmd!r}"


class TestApprovalGate:
    class _Backend:
        auto_approve = False

    def test_auto_approve_backend_runs_everything(self):
        b = self._Backend(); b.auto_approve = True
        assert tg._approval_gate("apt install cowsay", False, b, {}) is True

    def test_approve_all_state_runs_everything(self):
        b = self._Backend()
        assert tg._approval_gate("apt install cowsay", False, b, {"all": True}) is True

    def test_read_only_runs_without_prompt(self, monkeypatch):
        b = self._Backend()
        # If this prompted, input() would raise in the test env; it must not.
        monkeypatch.setattr("builtins.input", lambda *a: (_ for _ in ()).throw(AssertionError("prompted")))
        assert tg._approval_gate("systemctl status nginx", False, b, {"all": False}) is True

    def test_mutating_yes(self, monkeypatch):
        b = self._Backend()
        monkeypatch.setattr("sys.stdin", type("T", (), {"isatty": staticmethod(lambda: True)})())
        monkeypatch.setattr("builtins.input", lambda *a: "y")
        assert tg._approval_gate("apt install cowsay", False, b, {"all": False}) is True

    def test_mutating_skip(self, monkeypatch):
        b = self._Backend()
        monkeypatch.setattr("sys.stdin", type("T", (), {"isatty": staticmethod(lambda: True)})())
        monkeypatch.setattr("builtins.input", lambda *a: "n")
        assert tg._approval_gate("apt install cowsay", False, b, {"all": False}) is False

    def test_mutating_approve_all_sets_state(self, monkeypatch):
        b = self._Backend()
        monkeypatch.setattr("sys.stdin", type("T", (), {"isatty": staticmethod(lambda: True)})())
        monkeypatch.setattr("builtins.input", lambda *a: "A")
        state = {"all": False}
        assert tg._approval_gate("apt install cowsay", False, b, state) is True
        assert state["all"] is True

    def test_abort_raises(self, monkeypatch):
        b = self._Backend()
        monkeypatch.setattr("sys.stdin", type("T", (), {"isatty": staticmethod(lambda: True)})())
        monkeypatch.setattr("builtins.input", lambda *a: "a")
        with pytest.raises(tg._AbortSession):
            tg._approval_gate("apt install cowsay", False, b, {"all": False})

    def test_noninteractive_skips_mutation(self, monkeypatch):
        b = self._Backend()
        monkeypatch.setattr("sys.stdin", type("T", (), {"isatty": staticmethod(lambda: False)})())
        assert tg._approval_gate("apt install cowsay", False, b, {"all": False}) is False


# ── clean_json ────────────────────────────────────────────────────────────────

class TestCleanJson:
    def test_strips_json_fence(self):
        raw = "```json\n{\"key\": 1}\n```"
        assert tg.clean_json(raw) == '{"key": 1}'

    def test_strips_plain_fence(self):
        raw = "```\n{\"key\": 1}\n```"
        assert tg.clean_json(raw) == '{"key": 1}'

    def test_no_fence(self):
        raw = '{"key": 1}'
        assert tg.clean_json(raw) == '{"key": 1}'

    def test_strips_whitespace(self):
        raw = '   {"key": 1}   '
        assert tg.clean_json(raw) == '{"key": 1}'

    def test_valid_after_strip(self):
        raw = "```json\n{\"resolved\": false, \"steps\": []}\n```"
        parsed = json.loads(tg.clean_json(raw))
        assert parsed["resolved"] is False
        assert parsed["steps"] == []


# ── Config save/load ──────────────────────────────────────────────────────────

class TestConfig:
    def setup_method(self):
        self._orig_cfg = tg.CFG_FILE
        self._tmpdir = tempfile.mkdtemp()
        tg.CFG_FILE = os.path.join(self._tmpdir, "config.json")

    def teardown_method(self):
        tg.CFG_FILE = self._orig_cfg

    def test_load_empty_returns_dict(self):
        cfg = tg.load_cfg()
        assert isinstance(cfg, dict)

    def test_save_then_load(self):
        tg.save_cfg({"api_key": "test-key-123"})
        cfg = tg.load_cfg()
        assert cfg["api_key"] == "test-key-123"

    def test_save_merges_not_overwrites(self):
        tg.save_cfg({"api_key": "key1"})
        tg.save_cfg({"model": "claude-sonnet-4-6"})
        cfg = tg.load_cfg()
        # Both keys must survive
        assert cfg["api_key"] == "key1"
        assert cfg["model"] == "claude-sonnet-4-6"

    def test_save_chmod_600(self):
        tg.save_cfg({"api_key": "x"})
        mode = oct(os.stat(tg.CFG_FILE).st_mode)
        assert mode.endswith("600"), f"Expected 600, got {mode}"


# ── df parsing (quick_health_check) ──────────────────────────────────────────

class TestDfParsing:
    """
    We test the logic directly by simulating df -Ph output.
    The fix was: use df -Ph for POSIX fixed columns (always 6 fields).
    """
    def _parse_df(self, output):
        """Replicate the parsing logic from quick_health_check."""
        issues = []
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6:
                used_pct = parts[4].replace("%", "")
                if used_pct.isdigit() and int(used_pct) >= 90:
                    issues.append(f"Disk {parts[5]} is {parts[4]} full!")
        return issues

    def test_detects_full_disk(self):
        df_out = (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/sda1        50G   48G  2.0G  96% /\n"
        )
        issues = self._parse_df(df_out)
        assert len(issues) == 1
        assert "/" in issues[0]

    def test_ignores_healthy_disk(self):
        df_out = (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/sda1        50G   10G   40G  20% /\n"
        )
        assert self._parse_df(df_out) == []

    def test_multiple_disks(self):
        df_out = (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/sda1        50G   48G  2.0G  96% /\n"
            "/dev/sdb1       100G   10G   90G  10% /data\n"
            "/dev/sdc1        20G   19G  1.0G  95% /backup\n"
        )
        issues = self._parse_df(df_out)
        assert len(issues) == 2


# ── shlex quoting in feat_perms ───────────────────────────────────────────────

class TestShellQuoting:
    def test_shlex_quote_sanitizes_injection(self):
        import shlex
        malicious = "/home/user; rm -rf /"
        quoted = shlex.quote(malicious)
        # The quoted form should not allow command injection
        assert ";" not in quoted or quoted.startswith("'")
        assert quoted == "'/home/user; rm -rf /'"

    def test_shlex_quote_normal_path(self):
        import shlex
        path = "/home/user/documents"
        assert shlex.quote(path) == "/home/user/documents"

    def test_shlex_quote_path_with_spaces(self):
        import shlex
        path = "/home/my user/my docs"
        quoted = shlex.quote(path)
        assert " " not in quoted or quoted.startswith("'")


# ── Menu / feature map integrity ─────────────────────────────────────────────

class TestMenuIntegrity:
    def test_all_menu_items_have_callable(self):
        for num, kw, name, desc, fn in tg.MENU_ITEMS:
            assert callable(fn), f"Feature {num} '{name}' has no callable"

    def test_no_duplicate_numbers(self):
        nums = [num for num, *_ in tg.MENU_ITEMS]
        assert len(nums) == len(set(nums)), "Duplicate menu numbers found"

    def test_no_duplicate_keywords(self):
        kws = [kw for _, kw, *_ in tg.MENU_ITEMS]
        assert len(kws) == len(set(kws)), "Duplicate menu keywords found"

    def test_git_helper_present(self):
        kws = [kw for _, kw, *_ in tg.MENU_ITEMS]
        assert "git" in kws

    def test_settings_present(self):
        kws = [kw for _, kw, *_ in tg.MENU_ITEMS]
        assert "settings" in kws


# ── Version ───────────────────────────────────────────────────────────────────

class TestVersion:
    def test_version_string_exists(self):
        assert hasattr(tg, "__version__")
        assert tg.__version__[0].isdigit()

    def test_version_format(self):
        parts = tg.__version__.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
