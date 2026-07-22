"""
Fundamental release-gate checks.

These assert the *core promises* of TuxGenie that must hold on EVERY version
bump. The release workflow (.github/workflows/release.yml) runs the whole test
suite before it will build or publish anything, so if any of these fail, that
version never ships. Keep these fast, deterministic, and about fundamentals —
not niche feature details (those live in test_tuxgenie.py).
"""
import os
import re
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.modules.setdefault("anthropic", types.ModuleType("anthropic"))

import tuxgenie as tg

ROOT = os.path.dirname(os.path.dirname(__file__))


class TestVersionIntegrity:
    def test_version_is_semver(self):
        assert re.match(r"^\d+\.\d+\.\d+$", tg.__version__), tg.__version__

    def test_pyproject_version_matches(self):
        """The single-source-of-truth rule: pyproject.toml must match __version__."""
        txt = open(os.path.join(ROOT, "pyproject.toml")).read()
        m = re.search(r'^version\s*=\s*"([^"]+)"', txt, re.MULTILINE)
        assert m, "no version in pyproject.toml"
        assert m.group(1) == tg.__version__, (
            f"pyproject.toml version {m.group(1)} != tuxgenie __version__ {tg.__version__}")


class TestStartupFundamentals:
    def test_banner_renders(self):
        # Must never raise — it's the first thing every user sees.
        tg.banner()

    def test_base_ctx_reports_a_package_manager(self):
        ctx = tg.base_ctx()
        assert "pkg_mgr" in ctx and "os" in ctx

    def test_all_three_backends_construct(self):
        # The free defaults must always be constructable with a dummy key.
        assert tg.GeminiBackend(api_key="AIza" + "x" * 35) is not None
        assert tg.OpenAICompatBackend(api_key="gsk_" + "x" * 40, provider="groq") is not None


class TestCatalogFundamentals:
    def _check(self, catalog, required):
        ids = [e["id"] for e in catalog]
        assert len(ids) == len(set(ids)), "duplicate ids in catalog"
        for e in catalog:
            assert all(k in e for k in required), f"missing keys in {e.get('name')}"
            assert e["prompt"].strip(), f"empty prompt for {e.get('name')}"

    def test_app_catalog_integrity(self):
        assert len(tg.APP_CATALOG) >= 150
        self._check(tg.APP_CATALOG, ("id", "name", "cat", "prompt", "desc"))

    def test_ai_catalog_integrity(self):
        assert len(tg.AI_CATALOG) >= 10
        self._check(tg.AI_CATALOG, ("id", "name", "cat", "prompt", "desc"))


class TestMenuFundamentals:
    def test_menu_numbers_unique_and_dispatch_valid(self):
        nums = [row[0] for row in tg.MENU_ITEMS]
        assert len(nums) == len(set(nums)), "duplicate menu numbers"
        for row in tg.MENU_ITEMS:
            fn = row[-1]
            assert fn is None or callable(fn), f"menu row {row[0]} has non-callable handler"


class TestSafetyFundamentals:
    def test_dangerous_commands_still_blocked(self):
        assert tg.is_dangerous("rm -rf /")

    def test_scrubber_removes_secrets(self):
        out = tg._sanitize_tb("key AIza" + "Z" * 32 + " and gsk_" + "y" * 40)
        assert "AIza" not in out and "gsk_" not in out


class TestCrossDistroFundamentals:
    def test_prompt_unchanged_on_debian(self):
        p = "Install Foo via apt: foo."
        assert tg._distro_adapt_prompt(p, {"pkg_mgr": "apt", "os": "Ubuntu"}) == p

    def test_prompt_adapted_off_debian(self):
        p = "Install Foo via apt: foo."
        out = tg._distro_adapt_prompt(p, {"pkg_mgr": "dnf", "os": "Fedora"})
        assert "dnf" in out and "Flatpak" in out and out.endswith(p)
