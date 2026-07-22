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


# ── Cancel/back words never reach the AI engines ─────────────────────────────

class TestBackWords:
    def test_is_back(self):
        for w in ["q", "Q", "quit", "back", "cancel", "menu", " EXIT "]:
            assert tg._is_back(w), w
        for w in ["install steam", "q please", "backup", "", "31"]:
            assert not tg._is_back(w), w

    def test_engines_return_without_ai_on_back_word(self, monkeypatch):
        # A bare cancel word must not trigger any API call in either engine.
        called = {"n": 0}
        class FakeClient:
            class messages:
                @staticmethod
                def create(*a, **k):
                    called["n"] += 1
                    raise AssertionError("AI must not be called on a back-word")
        class FakeBackend:
            client = FakeClient(); auto_approve = False; expert_mode = False
            def select_model_for_task(self, *a, **k): pass
            def label(self): return "test"
        b = FakeBackend()
        # agentic_engine
        tg.agentic_engine(b, "q", {}, [])
        # fix_engine
        tg.fix_engine(b, "SYS", [{"role": "user", "content": "back"}], [])
        assert called["n"] == 0


class TestGeminiBackend:
    def test_backend_shape_matches_anthropic(self):
        b = tg.GeminiBackend("fake-key")
        for attr in ("expert_mode", "auto_approve", "auto_model", "model",
                     "base_model", "_no_key", "_session_input_tokens", "client"):
            assert hasattr(b, attr), attr
        assert hasattr(b.client.messages, "create")
        assert callable(b.select_model_for_task)
        assert "Gemini" in b.label()
        assert "free" in b.session_cost_estimate().lower()

    def test_system_to_text(self):
        assert tg._gem_system_to_text("hi") == "hi"
        assert tg._gem_system_to_text([{"type": "text", "text": "a"},
                                       {"type": "text", "text": "b"}]) == "a\n\nb"
        assert tg._gem_system_to_text(None) == ""

    def test_clean_schema_strips_unknown_keys(self):
        s = {"type": "object", "cache_control": {"type": "ephemeral"},
             "properties": {"cmd": {"type": "string", "description": "x"}},
             "required": ["cmd"], "$schema": "http://…"}
        out = tg._gem_clean_schema(s)
        assert "cache_control" not in out and "$schema" not in out
        assert out["properties"]["cmd"]["type"] == "string"
        assert out["required"] == ["cmd"]

    def test_tools_translation(self):
        tools = [{"name": "run_command", "description": "Run a command",
                  "input_schema": {"type": "object",
                                   "properties": {"command": {"type": "string"}},
                                   "required": ["command"]},
                  "cache_control": {"type": "ephemeral"}}]
        decls = tg._gem_tools_from_anthropic(tools)
        assert decls[0]["name"] == "run_command"
        assert decls[0]["parameters"]["properties"]["command"]["type"] == "string"

    def test_contents_maps_tool_result_to_function_name(self):
        # A SIGNED (native Gemini) tool_use → functionCall + functionResponse,
        # with the result mapped back to the function name via the id.
        messages = [
            {"role": "user", "content": "fix my wifi"},
            {"role": "assistant", "content": [tg._GBlock("tool_use", name="run_command",
                                     input={"command": "nmcli"}, id="c1", thought_signature="SIG")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1",
                                          "content": "wlan0 down"}]},
        ]
        contents = tg._gem_contents_from_anthropic(messages)
        assert contents[0] == {"role": "user", "parts": [{"text": "fix my wifi"}]}
        assert contents[1]["role"] == "model"
        assert contents[1]["parts"][0]["functionCall"]["name"] == "run_command"
        fr = contents[2]["parts"][0]["functionResponse"]
        assert fr["name"] == "run_command"          # mapped from id c1, not the id
        assert fr["response"]["result"] == "wlan0 down"

    def test_unsigned_foreign_call_flattened_to_text(self):
        # After a Groq→Gemini failover, tool calls have no thought_signature.
        # They must be flattened to text (Gemini 3.x rejects signature-less
        # functionCall parts), and their results kept as text (no orphaned
        # functionResponse).
        import json as _json
        messages = [
            {"role": "assistant", "content": [tg._GBlock("tool_use", name="run_command",
                                     input={"command": "snap install chromium"}, id="c1")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1",
                                          "content": "chromium installed"}]},
        ]
        blob = _json.dumps(tg._gem_contents_from_anthropic(messages))
        assert "functionCall" not in blob
        assert "functionResponse" not in blob
        assert "snap install chromium" in blob and "chromium installed" in blob

    def test_tool_use_block_has_no_text_attr(self):
        # Regression: agentic_engine does `hasattr(b,'text') and b.text.strip()`.
        # A tool_use block must NOT expose .text (or it crashes on None.strip()).
        tb = tg._GBlock("text", text="hi")
        ub = tg._GBlock("tool_use", name="run_command", input={"command": "x"}, id="c1")
        assert tb.type == "text" and tb.text == "hi"
        assert ub.type == "tool_use" and not hasattr(ub, "text")
        # emulate the exact engine loop that crashed
        for b in (tb, ub):
            if hasattr(b, "text") and b.text.strip():
                pass  # must not raise

    def test_thought_signature_round_trips(self):
        # Gemini 3.x: a functionCall's thoughtSignature must be captured on parse
        # and echoed back on the next request, or tools fail with a 400.
        resp = {"candidates": [{"content": {"parts": [
            {"functionCall": {"name": "run_command", "args": {"command": "ls"}},
             "thoughtSignature": "SIG-ABC"}]}}]}
        blocks, _ = tg._gem_blocks_from_response(resp)
        assert blocks[0].thought_signature == "SIG-ABC"
        # replay: that block, sent back as an assistant turn, must carry the sig
        contents = tg._gem_contents_from_anthropic([{"role": "assistant", "content": blocks}])
        part = contents[0]["parts"][0]
        assert part["functionCall"]["name"] == "run_command"
        assert part["thoughtSignature"] == "SIG-ABC"

    def test_response_parsing(self):
        # text response → end_turn
        blocks, stop = tg._gem_blocks_from_response(
            {"candidates": [{"content": {"parts": [{"text": "hello"}]}, "finishReason": "STOP"}]})
        assert stop == "end_turn" and blocks[0].type == "text" and blocks[0].text == "hello"
        # functionCall → tool_use
        blocks, stop = tg._gem_blocks_from_response(
            {"candidates": [{"content": {"parts": [
                {"functionCall": {"name": "run_command", "args": {"command": "ls"}}}]}}]})
        assert stop == "tool_use" and blocks[0].type == "tool_use"
        assert blocks[0].name == "run_command" and blocks[0].input == {"command": "ls"}

    def test_create_roundtrip_mocked(self, monkeypatch):
        # Full adapter path with the network mocked — proves agentic_engine's
        # backend.client.messages.create(...) contract works for Gemini.
        b = tg.GeminiBackend("fake-key")
        captured = {}
        def fake_gen(contents, system_text, tools_decl, max_tokens):
            captured["contents"] = contents; captured["tools"] = tools_decl
            return {"candidates": [{"content": {"parts": [
                        {"functionCall": {"name": "run_command", "args": {"command": "nmcli dev"}}}]},
                        "finishReason": "STOP"}],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 4}}
        monkeypatch.setattr(b, "_gen", fake_gen)
        resp = b.client.messages.create(
            model="ignored", max_tokens=16000, thinking={"type": "adaptive"},
            system=[{"type": "text", "text": "You are TuxGenie"}],
            tools=[{"name": "run_command", "description": "run",
                    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}}}],
            messages=[{"role": "user", "content": "check my network"}])
        assert resp.stop_reason == "tool_use"
        assert resp.content[0].type == "tool_use" and resp.content[0].name == "run_command"
        assert resp.usage.input_tokens == 10 and resp.usage.output_tokens == 4
        assert captured["tools"][0]["name"] == "run_command"    # tools were translated

    def test_pick_model_prefers_newest_stable_flash(self):
        avail = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.5-pro",
                 "gemini-2.5-flash", "gemini-flash-latest-preview",
                 "text-embedding-004", "imagen-3.0"]
        assert tg._gemini_pick_model(avail) == "gemini-3.5-flash"
        # never returns a non-text model
        assert tg._gemini_pick_model(["text-embedding-004", "imagen-3.0"]) is None
        # falls back to whatever gemini chat model exists
        assert tg._gemini_pick_model(["gemini-4.0-flash"]) == "gemini-4.0-flash"

    def test_gen_auto_heals_on_404(self, monkeypatch):
        # A retired model (404) should trigger discovery + retry with a new model.
        b = tg.GeminiBackend("fake-key")
        b.model = "gemini-2.5-flash"
        monkeypatch.setattr(b, "_resolve_model", lambda: "gemini-3.5-flash")
        monkeypatch.setattr(tg, "save_cfg", lambda *a, **k: None)
        calls = {"n": 0}
        import urllib.error, io
        real_urlopen = tg.urllib.request.urlopen
        def fake_urlopen(req, timeout=0):
            calls["n"] += 1
            if calls["n"] == 1:  # first call → 404 (retired model)
                raise urllib.error.HTTPError(req.full_url, 404, "gone", {},
                                             io.BytesIO(b'{"error":{"message":"no longer available"}}'))
            class R:
                def __enter__(s): return s
                def __exit__(s, *a): pass
                def read(s): return b'{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}'
            return R()
        monkeypatch.setattr(tg.urllib.request, "urlopen", fake_urlopen)
        try:
            out = b._gen([], "sys", None, 100)
        finally:
            monkeypatch.setattr(tg.urllib.request, "urlopen", real_urlopen)
        assert calls["n"] == 2 and b.model == "gemini-3.5-flash"
        assert out["candidates"][0]["content"]["parts"][0]["text"] == "ok"

    def test_ask_text_mocked(self, monkeypatch):
        b = tg.GeminiBackend("fake-key")
        monkeypatch.setattr(b, "_gen", lambda *a, **k:
            {"candidates": [{"content": {"parts": [{"text": '{"plan": "ok"}'}]}}],
             "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 3}})
        out = b.ask("sys", [{"role": "user", "content": "hi"}])
        assert out == '{"plan": "ok"}'
        assert b._session_input_tokens == 5


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

    def test_persona_setups_present_and_wired(self):
        """The guided persona setups (32-35) must be registered and callable."""
        by_num = {num: (kw, fn) for num, kw, name, desc, fn in tg.MENU_ITEMS}
        expected = {
            "32": ("newbie",   "feat_newbie_setup"),
            "33": ("devsetup",  "feat_dev_setup"),
            "34": ("creator",   "feat_creator_setup"),
            "35": ("privacy",   "feat_privacy_setup"),
            "36": ("student",   "feat_student_setup"),
            "37": ("homelab",   "feat_homelab_setup"),
            "38": ("access",    "feat_accessibility_setup"),
            "39": ("suggest",   "feat_suggest_setup"),
            "40": ("env",       "feat_dev_environments"),
        }
        for num, (kw, fnname) in expected.items():
            assert num in by_num, f"menu number {num} missing"
            assert by_num[num][0] == kw, f"{num} keyword mismatch"
            assert callable(by_num[num][1]), f"{num} not callable"
            assert by_num[num][1].__name__ == fnname, f"{num} wrong function"

    def test_compact_menu_is_short_and_complete(self):
        """The startup (compact) menu must fit a laptop screen yet list every
        feature number."""
        import io, re, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tg.show_menu(compact=True)
        out = buf.getvalue()
        assert out.count("\n") <= 25, "compact menu should stay short (one screen)"
        plain = re.sub(r"\x1b\[[0-9;]*m", "", out)
        for num in [str(n) for n in range(1, 41)] + ["77", "88", "99"]:
            # 31 exists; 39/40 exist; every dispatchable number should appear.
            if num in {n for n, *_ in tg.MENU_ITEMS}:
                assert f"[{num}]" in plain, f"compact menu missing [{num}]"

    def test_compact_footer_mentions_100(self):
        import io, re, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tg.show_menu(compact=True)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", buf.getvalue())
        assert "100" in plain, "compact menu should tell users to type 100 for the full menu"

    def test_suggest_keyword_not_shadowed_by_feedback(self):
        """'suggest' must reach feat_suggest_setup, not the feedback form."""
        import os
        src = open(os.path.join(self._ROOT, "tuxgenie.py")).read() if hasattr(self, "_ROOT") \
            else open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "tuxgenie.py")).read()
        # The feedback-alias dispatch line must no longer capture "suggest".
        assert '("f", "feedback", "feature", "suggest")' not in src, \
            "'suggest' must be removed from the feedback aliases so it reaches the setup chooser"

    def test_suggest_routes_to_matching_setup(self, monkeypatch):
        """The plain-language chooser must launch the mapped setup."""
        called = {}
        monkeypatch.setattr(tg, "feat_dev_setup", lambda *a, **k: called.setdefault("dev", True))
        monkeypatch.setattr("builtins.input", lambda *a, **k: "3")  # Coding / development
        tg.feat_suggest_setup(None, {}, None)
        assert called.get("dev"), "option 3 should launch the developer setup"

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


class TestOpenAICompatBackend:
    """Offline checks for the reusable OpenAI-compatible backend (Groq etc.)."""

    def test_message_translation_system_and_text(self):
        m = tg._oai_messages_from_anthropic("SYS", [{"role": "user", "content": "hi"}])
        assert m[0] == {"role": "system", "content": "SYS"}
        assert m[1] == {"role": "user", "content": "hi"}

    def test_tool_use_and_result_roundtrip(self):
        msgs = [
            {"role": "user", "content": "do it"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "ok"},
                {"type": "tool_use", "id": "call_1", "name": "run", "input": {"cmd": "ls"}}]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": "file1"}]},
        ]
        o = tg._oai_messages_from_anthropic("S", msgs)
        assert [x["role"] for x in o] == ["system", "user", "assistant", "tool"]
        assert o[2]["tool_calls"][0]["id"] == "call_1"
        assert o[2]["tool_calls"][0]["function"]["name"] == "run"
        assert o[3]["tool_call_id"] == "call_1" and o[3]["content"] == "file1"

    def test_response_parse_text_and_toolcall(self):
        b, stop = tg._oai_blocks_from_response(
            {"choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}]})
        assert b[0].type == "text" and b[0].text == "hello" and stop == "end_turn"
        b, stop = tg._oai_blocks_from_response({"choices": [{"message": {
            "content": None, "tool_calls": [{"id": "c1", "function": {
                "name": "run", "arguments": '{"cmd":"ls"}'}}]}, "finish_reason": "tool_calls"}]})
        assert stop == "tool_use"
        tu = [x for x in b if x.type == "tool_use"][0]
        assert tu.name == "run" and tu.input == {"cmd": "ls"} and tu.id == "c1"

    def test_text_format_toolcall_is_parsed(self):
        """Llama models sometimes emit the tool call as TEXT
        (<function/run_command>{...}</function>) — we must still run it."""
        resp = {"choices": [{"message": {"content":
            '<function/run_command>{"command": "sudo apt install -y chromium-browser", '
            '"requires_root": true, "risk": "moderate"}</function>'}, "finish_reason": "stop"}]}
        blocks, stop = tg._oai_blocks_from_response(resp)
        assert stop == "tool_use"
        tus = [b for b in blocks if b.type == "tool_use"]
        assert len(tus) == 1 and tus[0].name == "run_command"
        assert tus[0].input["command"].startswith("sudo apt install")
        assert not [b for b in blocks if b.type == "text"]

    def test_text_format_toolcall_with_surrounding_text(self):
        resp = {"choices": [{"message": {"content":
            'Sure!<function=run_command>{"command":"ls"}</function>'}}]}
        blocks, stop = tg._oai_blocks_from_response(resp)
        assert stop == "tool_use"
        assert [b for b in blocks if b.type == "text"][0].text == "Sure!"
        assert [b for b in blocks if b.type == "tool_use"][0].input["command"] == "ls"

    def test_text_format_toolcall_all_llama_variants(self):
        """Llama's text tool-call punctuation varies by model version — parse all."""
        variants = [
            '<function/run_command>{"command":"a"}</function>',
            '<function=run_command>{"command":"a"}</function>',
            '<function(run_command)({"command":"a","requires_root":true})</function>',
        ]
        for content in variants:
            blocks, stop = tg._oai_blocks_from_response(
                {"choices": [{"message": {"content": content}}]})
            tus = [b for b in blocks if b.type == "tool_use"]
            assert stop == "tool_use" and len(tus) == 1, content
            assert tus[0].name == "run_command" and "command" in tus[0].input, content
            assert not [b for b in blocks if b.type == "text"], content

    def test_text_format_toolcall_brace_in_argument(self):
        content = '<function=run_command>{"command": "echo }x", "requires_root": false}</function>'
        blocks, _ = tg._oai_blocks_from_response({"choices": [{"message": {"content": content}}]})
        assert [b for b in blocks if b.type == "tool_use"][0].input["command"] == "echo }x"

    def test_tool_use_block_has_no_text_attr(self):
        # Regression guard (same class of bug fixed for Gemini): tool_use blocks
        # must not carry a .text attribute, or `hasattr(b,'text') and b.text.strip()` crashes.
        b, _ = tg._oai_blocks_from_response({"choices": [{"message": {"content": None,
            "tool_calls": [{"id": "c1", "function": {"name": "run", "arguments": "{}"}}]}}]})
        tu = [x for x in b if x.type == "tool_use"][0]
        assert not hasattr(tu, "text")

    def test_malformed_tool_arguments_dont_crash(self):
        b, _ = tg._oai_blocks_from_response({"choices": [{"message": {"content": None,
            "tool_calls": [{"id": "c1", "function": {"name": "run", "arguments": "not json"}}]}}]})
        tu = [x for x in b if x.type == "tool_use"][0]
        assert tu.input == {}

    def test_model_picker_prefers_versatile(self):
        assert tg._oai_pick_model(
            ["whisper-large-v3", "llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
        ) == "llama-3.3-70b-versatile"

    def test_backend_basics(self):
        be = tg.OpenAICompatBackend(api_key=tg._NO_KEY, provider="groq")
        assert "Groq" in be.label()
        assert be.model == "llama-3.3-70b-versatile"
        assert be._no_key and be.base_url == "https://api.groq.com/openai/v1"

    def test_max_tokens_clamped_for_free_tier(self, monkeypatch):
        """A 16000-token request (Opus-sized) must be clamped so it doesn't trip
        a free tier's tokens-per-minute limit."""
        import json
        be = tg.OpenAICompatBackend(api_key="gsk_" + "x" * 40, provider="groq")
        captured = {}

        class _R:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s):
                return json.dumps({"choices": [{"message": {"content": "ok"},
                                   "finish_reason": "stop"}],
                                   "usage": {"prompt_tokens": 1, "completion_tokens": 1}}).encode()

        def fake_open(req, timeout=0):
            captured["max_tokens"] = json.loads(req.data.decode())["max_tokens"]
            return _R()

        monkeypatch.setattr(tg.urllib.request, "urlopen", fake_open)
        be._gen("sys", [{"role": "user", "content": "hi"}], None, 16000)
        # Groq's free tier is ~12k TPM, so its reservation is kept small.
        assert captured["max_tokens"] == 3072

    def test_headers_have_real_user_agent(self):
        be = tg.OpenAICompatBackend(api_key="gsk_" + "y" * 40, provider="groq")
        h = be._headers()
        assert h["User-Agent"].startswith("TuxGenie/")
        assert "Python-urllib" not in h["User-Agent"]

    def test_429_waits_then_retries(self, monkeypatch):
        """A free-tier TPM 429 with a 'try again in Ns' hint should wait once and
        retry, so the agentic loop continues instead of failing."""
        import io, json, urllib.error
        be = tg.OpenAICompatBackend(api_key="gsk_" + "z" * 40, provider="groq")
        calls = {"n": 0}

        class _OK:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s):
                return json.dumps({"choices": [{"message": {"content": "ok"},
                                   "finish_reason": "stop"}]}).encode()

        def fake_open(req, timeout=0):
            calls["n"] += 1
            if calls["n"] == 1:
                body = json.dumps({"error": {"message": "Rate limit reached … Please try again in 2s."}}).encode()
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, io.BytesIO(body))
            return _OK()

        slept = {}
        monkeypatch.setattr(tg.urllib.request, "urlopen", fake_open)
        monkeypatch.setattr(tg.time, "sleep", lambda s: slept.setdefault("s", s))
        data = be._gen("s", [{"role": "user", "content": "hi"}], None, 3072)
        assert calls["n"] == 2          # retried once
        assert slept.get("s") == 4      # 2s hint + 2s buffer
        assert data.get("choices")      # succeeded on retry

    def test_429_giving_up_message_is_actionable(self, monkeypatch):
        import io, json, urllib.error
        be = tg.OpenAICompatBackend(api_key="gsk_" + "q" * 40, provider="groq")

        def fake_open(req, timeout=0):
            body = json.dumps({"error": {"message": "daily limit exceeded"}}).encode()
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, io.BytesIO(body))
        monkeypatch.setattr(tg.urllib.request, "urlopen", fake_open)
        try:
            be._gen("s", [{"role": "user", "content": "hi"}], None, 3072)
            assert False, "should have raised"
        except RuntimeError as e:
            assert "Settings" in str(e)  # offers the switch-provider escape hatch


class TestKeyChangeRouting:
    """The `k` / Settings[1] key change must be provider-aware and must never
    store a key in the wrong provider's slot (regression: pasting a Gemini key
    while on Gemini used to also write backend=claude + api_key=<gemini key>)."""

    def setup_method(self):
        self._orig_cfg = tg.CFG_FILE
        self._tmpdir = tempfile.mkdtemp()
        tg.CFG_FILE = os.path.join(self._tmpdir, "config.json")

    def teardown_method(self):
        tg.CFG_FILE = self._orig_cfg

    def _run_with_input(self, backend, value, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda *a, **k: value)
        tg.feat_set_api_key(backend)
        return tg.load_cfg()

    def test_gemini_key_on_gemini_saves_only_gemini(self, monkeypatch):
        b = tg.GeminiBackend(api_key=tg._NO_KEY)
        cfg = self._run_with_input(b, "AIza" + "b" * 35, monkeypatch)
        assert cfg.get("provider") == "gemini"
        assert cfg.get("gemini_api_key", "").startswith("AIza")
        # Must NOT have flipped to Claude or stored the key in the Anthropic slot.
        assert cfg.get("backend") != "claude"
        assert "api_key" not in cfg or not cfg["api_key"]

    def test_anthropic_key_on_gemini_routes_to_claude(self, monkeypatch):
        b = tg.GeminiBackend(api_key=tg._NO_KEY)
        akey = "sk-ant-" + "a" * 70
        cfg = self._run_with_input(b, akey, monkeypatch)
        assert cfg.get("provider") == "claude"
        assert cfg.get("api_key") == akey
        # A real Anthropic key must never land in the Gemini slot.
        assert cfg.get("gemini_api_key", "") != akey

    def test_blank_input_changes_nothing(self, monkeypatch):
        b = tg.GeminiBackend(api_key=tg._NO_KEY)
        cfg = self._run_with_input(b, "", monkeypatch)
        assert not cfg.get("gemini_api_key")
        assert not cfg.get("api_key")

    def test_groq_key_on_gemini_routes_to_groq(self, monkeypatch):
        b = tg.GeminiBackend(api_key=tg._NO_KEY)
        gkey = "gsk_" + "a" * 40
        cfg = self._run_with_input(b, gkey, monkeypatch)
        assert cfg.get("provider") == "groq"
        assert cfg.get("groq_api_key") == gkey
        assert cfg.get("gemini_api_key", "") != gkey

    def test_groq_key_on_groq_saves_only_groq(self, monkeypatch):
        b = tg.OpenAICompatBackend(api_key=tg._NO_KEY, provider="groq")
        gkey = "gsk_" + "b" * 40
        cfg = self._run_with_input(b, gkey, monkeypatch)
        assert cfg.get("provider") == "groq"
        assert cfg.get("groq_api_key") == gkey
        assert cfg.get("backend") != "claude"


class TestSetupWizardDefault:
    """Gemini must be the first/default choice; Claude second."""

    def _wizard(self, inputs, monkeypatch):
        it = iter(inputs)
        monkeypatch.setattr("builtins.input", lambda *a, **k: next(it))
        return tg._setup_wizard({})

    def test_enter_defaults_to_gemini(self, monkeypatch):
        # First input = choice (blank → default), second = the key.
        kind, key = self._wizard(["", "AIza" + "z" * 35], monkeypatch)
        assert kind == "gemini"

    def test_one_is_gemini(self, monkeypatch):
        kind, key = self._wizard(["1", "AIza" + "z" * 35], monkeypatch)
        assert kind == "gemini"

    def test_two_is_groq(self, monkeypatch):
        kind, key = self._wizard(["2", "gsk_" + "a" * 40], monkeypatch)
        assert kind == "groq"

    def test_three_is_claude(self, monkeypatch):
        kind, key = self._wizard(["3", "sk-ant-" + "a" * 70], monkeypatch)
        assert kind == "claude"

    def test_s_skips(self, monkeypatch):
        kind, key = self._wizard(["s"], monkeypatch)
        assert kind == "skip"


class TestCatalogPage:
    """The generated website catalog must cover every app, AI tool, cloud
    provider and numbered feature — and stay searchable."""

    def _doc(self):
        import html as _h
        import build_catalog
        return build_catalog.build(), _h.escape

    def test_has_search_box(self):
        doc, _ = self._doc()
        assert 'id="q"' in doc

    def test_covers_all_apps_and_ai_and_cloud(self):
        doc, esc = self._doc()
        for a in tg.APP_CATALOG:
            assert esc(a["name"]) in doc, f"catalog page missing app {a['name']}"
        for a in tg.AI_CATALOG:
            assert esc(a["name"]) in doc, f"catalog page missing AI tool {a['name']}"
        for c in tg.CLOUD_PROVIDERS:
            assert esc(c["name"]) in doc, f"catalog page missing cloud {c['name']}"

    def test_covers_numbered_features(self):
        doc, esc = self._doc()
        for num, kw, name, desc, fn in tg.MENU_ITEMS:
            if str(num).isdigit():
                assert esc(name) in doc, f"catalog page missing feature {name}"


class TestMemoryLabelCleanup:
    """The Memory hint must show the real problem, not a diagnostic-dump blob."""

    def test_strips_diagnostic_dump(self):
        polluted = ("Make my Linux system as fast as possible.\n\nHere is a COMPLETE "
                    "live diagnostic scan collected right now:\n\n[memory]\ntotal")
        assert tg._clean_problem_label(polluted) == "Make my Linux system as fast as possible."

    def test_handles_truncated_legacy_entry(self):
        trunc = ("Make my Linux system as fast as possible.\n\nHere is a COMPLETE "
                 "live diagnostic scan collected right now:\n\n[memory]\ntota")
        assert tg._clean_problem_label(trunc) == "Make my Linux system as fast as possible."

    def test_clean_text_unchanged(self):
        for s in ("install chromium on this pc",
                  "I just switched to Linux — set this machine up with the everyday essentials."):
            assert tg._clean_problem_label(s) == s

    def test_empty(self):
        assert tg._clean_problem_label("") == ""


class TestCompactStepLayout:
    """The agentic step header is compact but keeps all safety info."""

    def _render(self, **kw):
        import io, re, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tg._display_tool_call(**kw)
        return re.sub(r"\x1b\[[0-9;]*m", "", buf.getvalue())

    def test_safe_step_is_two_lines_no_heavy_rule(self):
        out = self._render(cmd="dpkg -l | grep chromium", description="Check if installed",
                           risk="safe", requires_root=False, step_num=1)
        assert "─────" not in out                      # no heavy separator
        assert "Step 1" in out and "SAFE" in out and "Check if installed" in out
        assert "$ dpkg -l | grep chromium" in out
        # header + command = 2 non-empty lines
        assert len([ln for ln in out.splitlines() if ln.strip()]) == 2

    def test_sudo_and_danger_preserved(self):
        out = self._render(cmd="apt purge -y x", description="Remove it",
                           risk="dangerous", requires_root=True, step_num=3)
        assert "[SUDO]" in out and "DANGEROUS" in out and "DESTRUCTIVE" in out


class TestProgressCollapse:
    """apt/snap progress spam collapses to one clean line per task."""

    def test_progress_detection(self):
        assert tg._is_progress_line('Download snap "cups" (1229)          12% 680kB/s 1m07s')
        assert tg._is_progress_line('Ensure prerequisites available                    /')
        assert not tg._is_progress_line("chromium 150.0.7871.114 from Canonical installed")

    def test_stem_strips_changing_parts(self):
        a = tg._progress_stem('Download snap "cups"          12% 680kB/s 1m07s')
        b = tg._progress_stem('Download snap "cups"          40% 1.2MB/s 20.1s')
        assert a == b == 'Download snap "cups"'

    def test_flood_collapses(self):
        lines = (['Ensure prerequisites available            /'] * 40
                 + [f'Download snap "cups"   {p}% {p*10}kB/s' for p in range(100)]
                 + ["chromium installed", "=> Snap installation complete"])
        last = [None]; shown = 0
        for ln in lines:
            if tg._is_progress_line(ln):
                stem = tg._progress_stem(ln)
                if stem and stem == last[0]:
                    continue
                last[0] = stem
            else:
                last[0] = None
            shown += 1
        assert shown == 4, shown   # 2 progress stems + 2 result lines


class TestProviderFailover:
    """Auto-switch on limits/outages: free → free only, never Claude, toggleable."""

    def setup_method(self):
        self._orig = tg.CFG_FILE
        self._dir = tempfile.mkdtemp()
        tg.CFG_FILE = os.path.join(self._dir, "config.json")

    def teardown_method(self):
        tg.CFG_FILE = self._orig

    def test_transient_error_classification(self):
        assert tg._is_transient_ai_error(RuntimeError("Groq limit reached (HTTP 429)."))
        assert tg._is_transient_ai_error(RuntimeError("service unavailable 503"))
        assert not tg._is_transient_ai_error(RuntimeError("API key rejected (HTTP 401)"))

    def test_gemini_limit_message_is_transient(self):
        # Regression: the Gemini 429 message must trigger failover even when
        # Google's raw detail body is empty/unparseable (no "quota" word).
        assert tg._is_transient_ai_error(
            RuntimeError("Gemini free-tier rate limit reached (HTTP 429) — wait a minute "
                         "and retry, or switch provider (Settings → 8). "))
        # And auth/config errors must still NOT fail over.
        assert not tg._is_transient_ai_error(
            RuntimeError("Gemini API key rejected — check it at https://aistudio.google.com/apikey."))

    def test_groq_fails_over_to_gemini(self):
        tg.save_cfg({"groq_api_key": "gsk_" + "x" * 40, "gemini_api_key": "AIza" + "y" * 35})
        nb = tg._failover_backend(tg.OpenAICompatBackend(api_key="gsk_" + "x" * 40, provider="groq"))
        assert nb is not None and tg._provider_name(nb) == "gemini"

    def test_gemini_fails_over_to_groq(self):
        tg.save_cfg({"groq_api_key": "gsk_" + "x" * 40, "gemini_api_key": "AIza" + "y" * 35})
        nb = tg._failover_backend(tg.GeminiBackend(api_key="AIza" + "y" * 35))
        assert nb is not None and tg._provider_name(nb) == "groq"

    def test_never_falls_back_to_claude(self):
        # Only a Claude key present → no free target → must NOT switch.
        tg.save_cfg({"api_key": "sk-ant-" + "a" * 70})
        assert tg._failover_backend(tg.GeminiBackend(api_key="AIza" + "y" * 35)) is None

    def test_single_free_key_has_no_target(self):
        tg.save_cfg({"groq_api_key": "gsk_" + "x" * 40})
        assert tg._failover_backend(tg.OpenAICompatBackend(api_key="gsk_" + "x" * 40, provider="groq")) is None

    def test_toggle_off_disables_failover(self):
        tg.save_cfg({"auto_switch_providers": False,
                     "groq_api_key": "gsk_" + "x" * 40, "gemini_api_key": "AIza" + "y" * 35})
        assert tg._failover_backend(tg.GeminiBackend(api_key="AIza" + "y" * 35)) is None


class TestTransparency:
    """Lock in the 100%-transparency promises so they can't silently regress."""

    _ROOT = os.path.dirname(os.path.dirname(__file__))

    def _src(self):
        return open(os.path.join(self._ROOT, "tuxgenie.py")).read()

    def test_privacy_doc_exists(self):
        path = os.path.join(self._ROOT, "PRIVACY.md")
        assert os.path.exists(path), "PRIVACY.md must exist"
        body = open(path).read().lower()
        # The promises users rely on must be stated explicitly.
        for phrase in ("no telemetry", "chmod 600", "sudo password", "free tier"):
            assert phrase in body, f"PRIVACY.md must mention '{phrase}'"

    def test_no_telemetry_in_source(self):
        """No analytics/telemetry SDKs or phone-home network posts."""
        src = self._src().lower()
        for banned in ("posthog", "mixpanel", "segment.io", "google-analytics"):
            assert banned not in src, f"unexpected telemetry reference: {banned}"

    def test_gemini_free_tier_disclosure_at_point_of_choice(self):
        """Picking Gemini must disclose the free-tier data-usage caveat."""
        src = self._src()
        # Both the setup wizard and the settings provider-switch show it.
        assert src.count("improve their products") >= 2, (
            "Gemini free-tier data note must appear in both the setup wizard "
            "and the Settings provider switch"
        )
