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
