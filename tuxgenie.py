#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 ████████╗██╗   ██╗██╗  ██╗ ██████╗ ███████╗███╗   ██╗██╗███████╗
    ██╔══╝██║   ██║╚██╗██╔╝██╔════╝ ██╔════╝████╗  ██║██║██╔════╝
    ██║   ██║   ██║ ╚███╔╝ ██║  ███╗█████╗  ██╔██╗ ██║██║█████╗
    ██║   ██║   ██║ ██╔██╗ ██║   ██║██╔══╝  ██║╚██╗██║██║██╔══╝
    ██║   ╚██████╔╝██╔╝ ██╗╚██████╔╝███████╗██║ ╚████║██║███████╗
    ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚══════╝

TuxGenie — Your wish is my command 🐧
AI-powered Linux assistant · Powered by Claude · Free forever
www.tuxgenie.com

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DEDICATED TO LINUS TORVALDS
  Creator of the Linux Kernel — the greatest gift ever given to
  computing. His work powers servers, supercomputers, smartphones,
  satellites, and the entire modern internet. We believe Linus
  Torvalds deserves the Nobel Prize for his monumental contribution
  to technology and to humanity. Long live Linux. Long live Linus.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Built with ❤  by Aspera Technologies Pte Ltd
  Free to use · Free to modify · Free to share · Open Source forever
  www.tuxgenie.com
  "We are committed to making the world a better place, one command
   at a time." — https://github.com/ramchandragada/tuxgenie
"""

import os, sys, json, re, stat, tarfile, datetime, textwrap, time, shlex, argparse
import subprocess, urllib.request, urllib.error, threading, shutil, traceback
try:
    import termios, tty as _tty
    _HAS_TERMIOS = True
except ImportError:
    _HAS_TERMIOS = False

__version__ = "5.93.0"
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Anthropic SDK (auto-installed on first run if missing) ────
try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None

try:
    import readline  # noqa: F401 — imported for its input()-editing/history side effect
except ImportError:
    pass

def _rl(ansi_str):
    """Wrap ANSI escape codes for readline-safe input() prompts.
    Without this, readline miscounts prompt width and text disappears
    or wraps incorrectly when the user types long input."""
    return re.sub(r'(\033\[[0-9;]*m)', r'\001\1\002', ansi_str)

# Override builtin input to auto-fix ANSI prompts for readline
_builtin_input = input
def _safe_input(prompt=""):
    """input() replacement that auto-wraps ANSI codes for readline."""
    if '\033[' in prompt:
        prompt = _rl(prompt)
    return _builtin_input(prompt)
import builtins  # noqa: E402 — must follow _safe_input definition to override input()
builtins.input = _safe_input

# Words that mean "go back to the menu / cancel" at any feature prompt. These
# are never treated as a task or sent to the AI — every screen honours them.
_BACK_WORDS = {"q", "quit", "exit", "back", "cancel", "menu"}
def _is_back(s):
    return isinstance(s, str) and s.strip().lower() in _BACK_WORDS

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — ANSI + UI  (light-theme palette — always white bg, dark text)
# ═══════════════════════════════════════════════════════════════════════════════
# Light-theme base — applied at startup and restored after every reset
_LBG = "\033[48;2;248;249;252m"   # near-white background (cool off-white)
_LFG = "\033[38;2;20;25;46m"      # near-black navy foreground

# R resets attributes then immediately restores the light-theme base colours.
# This makes the light theme "sticky" — every {R} in every print call keeps us
# on the white background, overriding whatever the system terminal theme is.
R      = f"\033[0m{_LBG}{_LFG}"
BOLD   = "\033[1m"
DIM    = "\033[38;2;108;116;145m"  # medium blue-gray (secondary / hint text)
ITALIC = "\033[3m"

# Core UI colours — all dark enough to be crisp on white background
GREEN   = "\033[38;2;22;132;58m"   # forest green
YELLOW  = "\033[38;2;172;115;0m"   # amber
RED     = "\033[38;2;185;20;20m"   # dark crimson
CYAN    = "\033[38;2;0;128;145m"   # dark teal
BLUE    = "\033[38;2;18;80;198m"   # royal blue
MAGENTA = "\033[38;2;148;10;168m"  # dark magenta
WHITE   = "\033[38;2;20;25;46m"    # = _LFG (near-black)

# Vivid variants — still dark enough for white-bg readability
BRED    = "\033[38;2;198;22;22m"
BGREEN  = "\033[38;2;22;158;68m"
BYELLOW = "\033[38;2;198;132;0m"
BBLUE   = "\033[38;2;22;98;218m"
BMAGENTA= "\033[38;2;162;18;182m"
BCYAN   = "\033[38;2;0;152;170m"
BWHITE  = "\033[97m"               # true bright-white — only ever on dark bg headers

# Accent colours
ORANGE  = "\033[38;2;195;85;8m"
PINK    = "\033[38;2;178;16;135m"
LIME    = "\033[38;2;45;168;48m"
GOLD    = "\033[38;2;172;122;0m"
CORAL   = "\033[38;2;188;55;40m"
TEAL    = "\033[38;2;0;125;130m"
INDIGO  = "\033[38;2;78;8;178m"
SKY     = "\033[38;2;20;118;205m"
PEACH   = "\033[38;2;188;68;50m"

# Section-header backgrounds — kept dark so BWHITE title text pops on any terminal
BG_RED     = "\033[41m"
BG_GREEN   = "\033[42m"
BG_BLUE    = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN    = "\033[46m"
BG_DARK    = "\033[48;2;50;60;85m"     # dark slate-blue (section header)
BG_NAVY    = "\033[48;2;12;42;115m"    # deep navy
BG_PURPLE  = "\033[48;2;88;12;150m"    # deep purple
BG_TEAL    = "\033[48;2;0;100;110m"    # deep teal
BG_ORANGE  = "\033[48;2;170;75;8m"     # deep amber-brown
BG_FOREST  = "\033[48;2;18;90;45m"     # deep forest green

def C(text, *codes): return "".join(codes)+str(text)+R

def _init_light_theme():
    """Force the terminal into light mode (white bg, dark navy text).

    Uses OSC 10/11/12 to change the terminal's *actual* default fg/bg/cursor
    colours — this fills the ENTIRE terminal viewport, not just the cells
    where TuxGenie writes characters. Per-cell `_LBG`/`_LFG` is also written
    as a fallback for terminals that don't honour OSC."""
    # Skip if stdout isn't a TTY — escape codes pollute pipes / files / log capture.
    if not sys.stdout.isatty():
        return
    # OSC 11 = default background, 10 = default foreground, 12 = cursor
    sys.stdout.write("\033]11;#f8f9fc\033\\")
    sys.stdout.write("\033]10;#14192e\033\\")
    sys.stdout.write("\033]12;#14192e\033\\")
    # Wipe whatever was on the screen (previous shell prompts, etc.) so the
    # new background fills the visible area cleanly.
    sys.stdout.write("\033[2J\033[H")
    # Per-cell colours as a fallback / belt-and-braces
    sys.stdout.write(_LBG + _LFG)
    sys.stdout.flush()

def _restore_default_theme():
    """Restore the terminal's default colours on exit.
    OSC 110/111/112 reset 10/11/12 back to the user's theme defaults."""
    try:
        sys.stdout.write("\033]110\033\\")   # reset default fg
        sys.stdout.write("\033]111\033\\")   # reset default bg
        sys.stdout.write("\033]112\033\\")   # reset cursor colour
        sys.stdout.write("\033[0m")
        sys.stdout.flush()
    except Exception:
        pass

def banner():
    _letters = [
        (ORANGE,  "T"), (YELLOW,  "U"), (GREEN,   "X"), (GREEN,   "G"),
        (CYAN,    "E"), (BLUE,    "N"), (MAGENTA, "I"), (RED,     "E"),
    ]
    _logo = "".join(f"{col}{BOLD}{ch}{R}" for col, ch in _letters)
    _bar  = f"  {DIM}{'─' * 66}{R}"

    print(f"""
{_bar}
  {CYAN}{BOLD}🐧{R}  {_logo}   {DIM}v{__version__} · Powered by Claude · Free forever{R}
  {DIM}Your friendly AI assistant for Linux  ·  No experience needed{R}
{_bar}
  {BGREEN}{BOLD}✔{R}  {BOLD}Just type what you need in plain English{R}
     {DIM}e.g.{R} {BLUE}\"my wifi stopped working\"{R}  ·  {BLUE}\"install chrome\"{R}  ·  {BLUE}\"why is it slow?\"{R}
  {BGREEN}{BOLD}✔{R}  {BOLD}Or pick a number from the menu{R}  {DIM}(type{R} {BOLD}menu{R} {DIM}to see it again){R}
  {BGREEN}{BOLD}✔{R}  {BOLD}Or run any Linux command directly{R}  {DIM}e.g.{R} {BLUE}\"ls -la\"{R}
{_bar}
  {BLUE}{BOLD}🌐 www.tuxgenie.com{R}  {DIM}· Dedicated to Linus Torvalds · Built by Aspera Technologies{R}
{_bar}
""")

def hdr(title, width=64):
    pad = width - len(title) - 3
    print(f"\n  {BG_NAVY}{BWHITE}{BOLD}  🔷 {title}  {' '*max(pad,0)}{R}")

def section(title):
    print(f"\n  {CYAN}{BOLD}┄┄ {title} ┄┄{R}")

def ok(msg):  print(f"  {GREEN}{BOLD}✔{R}  {msg}")
def warn(msg):print(f"  {YELLOW}{BOLD}⚠{R}  {msg}")
def err(msg): print(f"  {RED}{BOLD}✘{R}  {msg}")
def info(msg):print(f"  {CYAN}ℹ{R}  {msg}")

def trunc(text, max_lines):
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    hidden = len(lines) - max_lines
    return "\n".join(lines[:max_lines]) + f"\n{C(f'  … [{hidden} more lines]', DIM)}"

def print_output(rc, stdout, stderr):
    if stdout:
        print(f"\n  {TEAL}{BOLD}OUTPUT{R}\n{DIM}{trunc(stdout,25)}{R}")
    if rc != 0 and stderr:
        print(f"\n  {CORAL}{BOLD}STDERR{R}\n{DIM}{trunc(stderr,10)}{R}")
    print(f"  {BGREEN}{BOLD}✔ Done{R}" if rc == 0 else f"  {BRED}{BOLD}✘ Exit {rc}{R}")

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — CONFIG  (persistent API key + session log path)
# ═══════════════════════════════════════════════════════════════════════════════
CFG_DIR      = os.path.expanduser("~/.config/tuxgenie")
CFG_FILE     = os.path.join(CFG_DIR, "config.json")
HISTORY_FILE = os.path.join(CFG_DIR, "history.json")   # user prompts
ACTIONS_FILE = os.path.join(CFG_DIR, "actions.json")   # commands run by AI
FINGERPRINT_FILE = os.path.join(CFG_DIR, "fingerprint.json")  # cached system info
MEMORY_FILE  = os.path.join(CFG_DIR, "memory.json")    # cross-session solved issues
COMMUNITY_FIXES_PATHS = [                                # read-only fixes shipped with the .deb
    "/usr/share/tuxgenie/community_fixes.json",
    "/usr/local/share/tuxgenie/community_fixes.json",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "community_fixes.json"),
]
DIGEST_FILE  = os.path.join(CFG_DIR, "digest.json")    # weekly health digest last-run
CRASH_FILE   = os.path.join(CFG_DIR, "crash.json")     # crash guard counter
PREV_VER_BAK = os.path.join(CFG_DIR, "tuxgenie.bak")   # last-known-good backup
DATA_DIR     = os.path.expanduser("~/.local/share/tuxgenie")
SESSIONS_DIR = os.path.join(DATA_DIR, "sessions")
BACKUPS_DIR  = os.path.join(DATA_DIR, "backups")

for _d in (CFG_DIR, DATA_DIR, SESSIONS_DIR, BACKUPS_DIR):
    os.makedirs(_d, exist_ok=True)

def load_cfg() -> dict:
    try:
        return json.loads(open(CFG_FILE).read())
    except Exception:
        return {}

def save_cfg(updates: dict):
    existing = load_cfg()
    existing.update(updates)
    with open(CFG_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    os.chmod(CFG_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 600

# ── Backend ──────────────────────────────────────────────────────────────────

# ── Smart model routing ───────────────────────────────────────────────────────
# Haiku handles ALL tasks by default (~80% cheaper than Sonnet).
# Sonnet is only used as a fallback when Haiku fails on a task.
# This keeps costs at ~$1.50/user/month even at scale (200+ users).
_SIMPLE_KEYWORDS = [
    "install", "update", "upgrade", "remove", "uninstall", "restart",
    "start", "stop", "enable", "disable", "reboot", "shutdown",
    "open", "launch", "check for updates", "free up", "clean",
]
_COMPLEX_KEYWORDS = [
    "debug", "diagnose", "not working", "error", "fail", "broken",
    "security", "audit", "slow", "crash", "permission", "boot",
    "network", "can't connect", "won't", "doesn't", "conflict",
]
_HAIKU_MODEL  = "claude-haiku-4-5-20251001"
_SONNET_MODEL = "claude-sonnet-4-6"
_OPUS_MODEL   = "claude-opus-4-8"
_GEMINI_MODEL = "gemini-3.5-flash"   # Google's current free-tier model (auto-heals if retired)


def _try_pip_install():
    """Try to install the anthropic SDK using every known pip method.
    Returns True if pip exits 0 (package installed to disk)."""
    attempts = [
        [sys.executable, "-m", "pip", "install", "anthropic", "--quiet", "--user"],
        [sys.executable, "-m", "pip", "install", "anthropic", "--quiet", "--upgrade"],
        [sys.executable, "-m", "pip", "install", "anthropic", "--quiet", "--upgrade", "--break-system-packages"],
        ["pip3", "install", "anthropic", "--quiet", "--user"],
        ["pip3", "install", "anthropic", "--quiet", "--upgrade"],
        ["pip3", "install", "anthropic", "--quiet", "--upgrade", "--break-system-packages"],
    ]
    for attempt in attempts:
        try:
            if subprocess.run(attempt, capture_output=True).returncode == 0:
                return True
        except FileNotFoundError:
            continue
    return False

def _can_import_anthropic():
    """Check if anthropic is importable, refreshing the import cache first."""
    import importlib
    importlib.invalidate_caches()
    # Also ensure ~/.local/lib/.../site-packages is on sys.path (--user installs)
    try:
        import site
        user_site = site.getusersitepackages()
        if user_site not in sys.path:
            sys.path.insert(0, user_site)
    except Exception:
        pass
    try:
        importlib.import_module("anthropic")
        return True
    except Exception:
        # Catch broader than ImportError: a partial/corrupt install can raise
        # AttributeError or other errors deep in dependency init. Treat any
        # failure as "not importable" so the bootstrap continues to recover.
        return False

def _apt_install(packages, label=None):
    """Install the first package in `packages` that apt accepts.
    Output is shown (not captured) so the user sees progress and any errors.
    If every attempt fails, runs `apt-get update` once and retries.
    Returns True if any package installed cleanly."""
    if label:
        print(f"  {DIM}Installing {label} (sudo may prompt for password)…{R}")
    def _try(pkgs):
        for pkg in pkgs:
            try:
                rc = subprocess.run(
                    ["sudo", "apt-get", "install", "-y", "-q", pkg],
                    timeout=300,
                ).returncode
                if rc == 0:
                    return True
            except Exception:
                continue
        return False
    if _try(packages):
        return True
    print(f"  {DIM}Refreshing apt package index…{R}")
    try:
        subprocess.run(["sudo", "apt-get", "update", "-q"], timeout=180)
    except Exception:
        pass
    return _try(packages)

def _venv_can_create():
    """Check whether `python3 -m venv` can actually create a venv with pip on
    this system. Returns True only if a throwaway venv builds cleanly."""
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(
                [sys.executable, "-m", "venv", os.path.join(td, "probe")],
                capture_output=True, timeout=60,
            )
            return r.returncode == 0
    except Exception:
        return False

def _bootstrap_anthropic_sdk():
    """Install the anthropic SDK using every strategy available.
    Tries: existing pip → --user install → apt install pip → ensurepip → venv fallback.
    Returns True if the SDK is importable afterward."""
    # Quick check: maybe it's already installed
    if _can_import_anthropic():
        return True

    print(f"  {CYAN}Installing anthropic SDK…{R}")

    # Strategy 1: pip already available (tries --user first, then system-wide)
    if _try_pip_install() and _can_import_anthropic():
        return True

    # Strategy 2: install python3-pip via apt, then retry
    print(f"  {DIM}pip not found — installing python3-pip…{R}")
    _apt_install(["python3-pip"])
    if _try_pip_install() and _can_import_anthropic():
        return True

    # Strategy 3: ensurepip (Python's built-in pip bootstrapper, works offline)
    print(f"  {DIM}Trying ensurepip…{R}")
    try:
        subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"],
                       capture_output=True, timeout=60)
        if _try_pip_install() and _can_import_anthropic():
            return True
    except Exception:
        pass

    # Strategy 4: create a temporary venv (has its own pip), install there,
    # then add the venv's site-packages to sys.path so we can import.
    print(f"  {DIM}Trying venv fallback…{R}")
    # On Debian/Ubuntu, ensurepip is split into a separate package. The
    # version-specific name (python3.12-venv) is sometimes the only one apt can
    # resolve on minimal images, so try both.
    py_ver_pkg = f"python{sys.version_info.major}.{sys.version_info.minor}-venv"
    if not _venv_can_create():
        _apt_install([py_ver_pkg, "python3-venv"], label="python3-venv")

    import importlib
    venv_dir = os.path.join(os.path.expanduser("~"), ".local", "share",
                            "tuxgenie", ".bootstrap-venv")
    try:
        import venv as _venv_mod
        _venv_mod.create(venv_dir, with_pip=True, clear=True)
        venv_pip = os.path.join(venv_dir, "bin", "pip")
        rc = subprocess.run([venv_pip, "install", "anthropic", "--quiet"],
                            capture_output=True, timeout=120).returncode
        if rc == 0:
            # Find the venv's site-packages and add to path
            venv_py = os.path.join(venv_dir, "bin", "python3")
            result = subprocess.run(
                [venv_py, "-c",
                 "import site; print(site.getsitepackages()[0])"],
                capture_output=True, text=True, timeout=10)
            venv_site = result.stdout.strip()
            if venv_site and os.path.isdir(venv_site):
                sys.path.insert(0, venv_site)
                importlib.invalidate_caches()
                try:
                    importlib.import_module("anthropic")
                    return True
                except ImportError:
                    pass
    except Exception:
        pass

    return False

class AnthropicBackend:
    def __init__(self, api_key, model="claude-haiku-4-5-20251001"):
        self._no_key    = (api_key == _NO_KEY)
        self.api_key    = "" if self._no_key else api_key
        self.model      = model
        self.base_model = model
        self.auto_model = True
        self.expert_mode = False   # compact output — skip beginner explanations
        self.auto_approve = False  # when True, run AI commands without per-step approval
        self.client     = None
        self._session_input_tokens         = 0
        self._session_output_tokens        = 0
        self._session_cache_creation_tokens = 0   # written to cache (~1.25x cost)
        self._session_cache_read_tokens     = 0   # served from cache (~0.1x cost)
        if not self._no_key:
            self._init_client(api_key)

    def _init_client(self, api_key):
        """Bootstrap SDK and create Anthropic client."""
        global _anthropic
        if _anthropic is None:
            py_ver_pkg = f"python{sys.version_info.major}.{sys.version_info.minor}-venv"
            if not _bootstrap_anthropic_sdk():
                print(f"\n  {RED}{BOLD}Could not install the anthropic SDK.{R}")
                print(f"  TuxGenie will try to fix this automatically…\n")
                print(f"  {CYAN}Running: sudo apt update && sudo apt install -y python3-pip {py_ver_pkg} python3-venv{R}")
                subprocess.run(["sudo", "apt-get", "update", "-q"])
                subprocess.run(["sudo", "apt-get", "install", "-y",
                                "python3-pip", py_ver_pkg, "python3-venv"])
                print(f"\n  {CYAN}Running: pip3 install anthropic{R}")
                subprocess.run([sys.executable, "-m", "pip", "install",
                                "anthropic", "--break-system-packages"])
            # Single guarded import path. Both bootstrap-succeeded and
            # bootstrap-failed-then-sudo-fallback flows end here. The probe
            # inside _bootstrap_anthropic_sdk can return True under sys.path
            # mutations that don't fully carry over, so we must not assume
            # the import will succeed unconditionally.
            try:
                import anthropic as _anth
                _anthropic = _anth
            except Exception:
                print(f"\n  {RED}{BOLD}Could not import the anthropic SDK.{R}")
                print(f"  Please run these commands and restart tuxgenie:\n")
                print(f"    {CYAN}sudo apt update{R}")
                print(f"    {CYAN}sudo apt install -y python3-pip {py_ver_pkg} python3-venv{R}")
                print(f"    {CYAN}pip3 install anthropic --break-system-packages{R}\n")
                input(f"  Press Enter to close...")
                sys.exit(1)
        self.client  = _anthropic.Anthropic(api_key=api_key)
        self.api_key = api_key
        self._no_key = False

    def _set_key(self, key):
        """Set a new API key, save to config, and re-init the client."""
        self._init_client(key)
        save_cfg({"api_key": key})
        ok(f"API key saved! AI features are now enabled. Type a question or pick a menu number.")

    def label(self):
        return f"Anthropic · {self.model}"

    # Hints that a request likely needs Sonnet-level reasoning even on round 1.
    # Multi-step installs, network/boot diagnostics, kernel/driver issues — Haiku
    # often produces shallow plans that fail and force a retry. Starting at Sonnet
    # avoids the wasted Haiku call.
    _COMPLEX_HINTS = (
        "install ", "uninstall ", "remove ", "configure ", "set up ",
        "boot ", "kernel", "driver", "wifi", "bluetooth", "audio",
        "graphics", "gpu", "nvidia", "amdgpu", "compile", "kernel panic",
        "secure boot", "dual boot", "encrypt", "luks", "lvm",
        "systemd", "service ", "cron", "nginx", "apache", "docker",
        "permission denied", "won't start", "won't boot", "fails to",
    )

    def select_model_for_task(self, user_text: str, round_num: int = 1):
        """Auto-select the cheapest model that can handle the task.
        Round 1 simple tasks → Haiku. Complex tasks or retries → Sonnet."""
        if not self.auto_model:
            return  # user manually picked a model, respect it
        if round_num > 1:
            if self.model != _SONNET_MODEL and self.base_model != _OPUS_MODEL:
                self.model = _SONNET_MODEL
            return
        if self.base_model == _OPUS_MODEL:
            self.model = self.base_model
            return
        text = (user_text or "").lower()
        if any(h in text for h in self._COMPLEX_HINTS):
            self.model = _SONNET_MODEL
        else:
            self.model = _HAIKU_MODEL

    def ask(self, system, messages, max_tokens=4096, cache_system=False):
        """Streaming call — prints a live progress counter while receiving.

        cache_system=True wraps the system prompt in a cache_control block,
        cutting input cost ~90% on repeated calls with the same system prompt.
        Only effective when the system prompt exceeds the model's cache minimum
        (4096 tokens for Opus/Haiku, 2048 for Sonnet)."""
        if self._no_key:
            print(f"\n  {YELLOW}{BOLD}🔑 AI features need an Anthropic API key.{R}")
            print(f"  {DIM}Terminal commands work without a key — always free.{R}")
            print(f"  Get your free key at: {CYAN}https://console.anthropic.com{R}\n")
            try:
                key = input("  Paste API key now (or press Enter to cancel): ").strip()
            except (EOFError, KeyboardInterrupt):
                return ""
            if not key:
                info(f"Cancelled. Type {BOLD}k{R} at the menu anytime to add your key.")
                return ""
            self._set_key(key)
        if cache_system and isinstance(system, str):
            system = [{"type": "text", "text": system,
                       "cache_control": {"type": "ephemeral"}}]
        chunks = []
        char_count = 0
        with self.client.messages.stream(
            model=self.model, max_tokens=max_tokens,
            system=system, messages=messages
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
                char_count += len(text)
                print(f"\r  {CYAN}⚡ Receiving… {char_count} chars{R}   ", end="", flush=True)
        final = stream.get_final_message()
        if final and final.usage:
            self._record_usage(final.usage)
        print(f"\r  {GREEN}✓ Response received ({char_count} chars)   {R}")
        return "".join(chunks)

    def _record_usage(self, usage):
        """Accumulate per-session token counts (regular + cache)."""
        self._session_input_tokens          += getattr(usage, "input_tokens", 0) or 0
        self._session_output_tokens         += getattr(usage, "output_tokens", 0) or 0
        self._session_cache_creation_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self._session_cache_read_tokens     += getattr(usage, "cache_read_input_tokens", 0) or 0

    def session_cost_estimate(self) -> str:
        """Return estimated session cost based on tracked tokens."""
        # Pricing per million tokens (approximate, as of 2026)
        model_prices = {
            "claude-opus-4-8":          (5.0, 25.0),    # input, output per 1M tokens
            "claude-sonnet-4-6":        (3.0, 15.0),
            "claude-haiku-4-5-20251001":(0.80, 4.0),
        }
        # Use average pricing since model may switch mid-session
        p_in, p_out = model_prices.get(self.model, (3.0, 15.0))
        # Cache writes cost ~1.25x base input; reads cost ~0.1x.
        cost = (
            self._session_input_tokens          * p_in
          + self._session_output_tokens         * p_out
          + self._session_cache_creation_tokens * p_in * 1.25
          + self._session_cache_read_tokens     * p_in * 0.10
        ) / 1_000_000
        line = (f"Session tokens: ~{self._session_input_tokens:,} in + "
                f"~{self._session_output_tokens:,} out · "
                f"Est. cost: ${cost:.4f}")
        if self._session_cache_read_tokens or self._session_cache_creation_tokens:
            saved = self._session_cache_read_tokens * p_in * 0.90 / 1_000_000
            line += (f"\n  Cache: {self._session_cache_read_tokens:,} read + "
                     f"{self._session_cache_creation_tokens:,} written · "
                     f"saved ~${saved:.4f}")
        return line

# ── Anthropic error classification ───────────────────────────────────────────
def _classify_anthropic_error(exc):
    """Map an Anthropic SDK exception to ('billing'|'auth'|'network'|'other', user_msg)."""
    msg = str(exc).lower()
    if "credit balance" in msg or "billing" in msg or "insufficient" in msg or "quota" in msg:
        return "billing", "Your Anthropic API balance is empty"
    if "authentication" in msg or "invalid api" in msg or "invalid x-api-key" in msg or "401" in msg:
        return "auth", "Your Anthropic API key is invalid"
    if "connection" in msg or "timeout" in msg or "timed out" in msg or "network" in msg:
        return "network", "Could not reach the Anthropic API"
    return "other", str(exc)


# ═══════════════════════════════════════════════════════════════════════════════
#  Google Gemini backend — FREE-TIER option (no credit card needed)
# ═══════════════════════════════════════════════════════════════════════════════
# A drop-in sibling of AnthropicBackend. It presents the SAME interface the two
# engines use — .ask() (text, for fix_engine) and .client.messages.create()
# (Anthropic-shaped, for agentic_engine) — translating to Google's REST API
# underneath via urllib (no extra dependency). Claude's path is untouched; this
# is only used when the user opts into Gemini. The translation helpers are pure
# functions so they can be unit-tested without hitting the network.
_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


class _GBlock:
    """Mimics an Anthropic content block for the engines. Matches the real SDK's
    duck typing: a text block exposes ONLY .text; a tool_use block exposes ONLY
    .name/.input/.id. (Setting .text=None on tool_use blocks made engine code
    like `hasattr(b,'text') and b.text.strip()` crash — the SDK's tool_use
    blocks have no .text attribute at all.)"""
    def __init__(self, type, text=None, name=None, input=None, id=None, thought_signature=None):
        self.type = type
        # Gemini 3.x returns an opaque 'thoughtSignature' on parts that MUST be
        # echoed back on the next turn or function calling fails with a 400.
        self.thought_signature = thought_signature
        if type == "text":
            self.text = "" if text is None else text
        else:
            self.name = name; self.input = input; self.id = id


class _GUsage:
    def __init__(self, in_tok, out_tok):
        self.input_tokens = in_tok; self.output_tokens = out_tok
        self.cache_creation_input_tokens = 0; self.cache_read_input_tokens = 0


class _GResponse:
    def __init__(self, content, stop_reason, usage):
        self.content = content; self.stop_reason = stop_reason; self.usage = usage


def _gem_system_to_text(system):
    """Anthropic 'system' (str or list of text blocks) → a plain string."""
    if not system:
        return ""
    if isinstance(system, str):
        return system
    parts = []
    for blk in system:
        parts.append(blk.get("text", "") if isinstance(blk, dict) else (getattr(blk, "text", "") or ""))
    return "\n\n".join(p for p in parts if p)


def _gem_clean_schema(schema):
    """Strip keys Gemini's function schema rejects (cache_control, $schema, …)."""
    if not isinstance(schema, dict):
        return schema
    allowed = {"type", "description", "enum", "items", "properties", "required", "nullable", "format"}
    out = {}
    for k, v in schema.items():
        if k not in allowed:
            continue
        if k == "properties" and isinstance(v, dict):
            out[k] = {pk: _gem_clean_schema(pv) for pk, pv in v.items()}
        elif k == "items":
            out[k] = _gem_clean_schema(v)
        else:
            out[k] = v
    return out


def _gem_tools_from_anthropic(tools):
    """Anthropic tools → Gemini functionDeclarations."""
    if not tools:
        return None
    decls = []
    for t in tools:
        name = t.get("name"); desc = t.get("description", ""); schema = t.get("input_schema") or {}
        decl = {"name": name, "description": desc}
        params = _gem_clean_schema(schema)
        if params.get("properties"):
            decl["parameters"] = params
        decls.append(decl)
    return decls


def _gem_bget(b, key, default=None):
    """Read a field from a block that may be a dict or a _GBlock object."""
    return b.get(key, default) if isinstance(b, dict) else getattr(b, key, default)


def _gem_contents_from_anthropic(messages):
    """Anthropic messages → Gemini 'contents'. Builds a tool_use_id→name map so
    tool_result parts can carry the function name Gemini's functionResponse needs."""
    id2name = {}
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            for b in content:
                if _gem_bget(b, "type") == "tool_use":
                    bid = _gem_bget(b, "id")
                    if bid:
                        id2name[bid] = _gem_bget(b, "name")
    contents = []
    for m in messages:
        grole = "model" if m.get("role") == "assistant" else "user"
        content = m.get("content")
        parts = []
        if isinstance(content, str):
            if content:
                parts.append({"text": content})
        else:
            for b in content:
                typ = _gem_bget(b, "type")
                if typ == "text":
                    txt = _gem_bget(b, "text", "")
                    if txt:
                        part = {"text": txt}
                        sig = _gem_bget(b, "thought_signature")
                        if sig:
                            part["thoughtSignature"] = sig
                        parts.append(part)
                elif typ == "tool_use":
                    part = {"functionCall": {"name": _gem_bget(b, "name"),
                                             "args": _gem_bget(b, "input") or {}}}
                    sig = _gem_bget(b, "thought_signature")
                    if sig:                       # Gemini 3.x requires echoing this back
                        part["thoughtSignature"] = sig
                    parts.append(part)
                elif typ == "tool_result":
                    resc = _gem_bget(b, "content", "")
                    if isinstance(resc, list):
                        resc = "".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in resc)
                    if not isinstance(resc, str):
                        resc = json.dumps(resc)
                    nm = id2name.get(_gem_bget(b, "tool_use_id"), "run_command")
                    parts.append({"functionResponse": {"name": nm, "response": {"result": resc}}})
        if parts:
            contents.append({"role": grole, "parts": parts})
    return contents


def _gem_blocks_from_response(data):
    """Gemini generateContent response → (Anthropic-shaped blocks, stop_reason)."""
    cand = (data.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    blocks = []; has_call = False; idx = 0
    for p in parts:
        sig = p.get("thoughtSignature")
        if p.get("text"):
            blocks.append(_GBlock("text", text=p["text"], thought_signature=sig))
        elif "functionCall" in p:
            has_call = True; idx += 1
            fc = p["functionCall"]
            blocks.append(_GBlock("tool_use", name=fc.get("name"),
                                  input=fc.get("args") or {}, id=f"gemcall_{idx}",
                                  thought_signature=sig))
    fr = cand.get("finishReason", "")
    stop = "tool_use" if has_call else ("max_tokens" if fr == "MAX_TOKENS" else "end_turn")
    if not blocks:
        blocks.append(_GBlock("text", text=""))
    return blocks, stop


def _gem_usage(data):
    um = data.get("usageMetadata") or {}
    return _GUsage(um.get("promptTokenCount", 0) or 0, um.get("candidatesTokenCount", 0) or 0)


def _gemini_list_models(api_key):
    """Ask Google which models this key can use for generateContent."""
    req = urllib.request.Request(f"{_GEMINI_ENDPOINT}?pageSize=200",
                                 headers={"x-goog-api-key": api_key})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [(m.get("name", "") or "").replace("models/", "")
            for m in data.get("models", [])
            if "generateContent" in (m.get("supportedGenerationMethods") or [])]


def _gemini_pick_model(available):
    """Choose the best general chat model: newest full 'flash' preferred, stable
    over preview/experimental, skipping non-text (vision/embedding/tts/image)."""
    def score(name):
        n = name.lower()
        if "gemini" not in n:
            return -1000
        if any(x in n for x in ("vision", "embedding", "imagen", "tts", "image", "aqa", "learnlm")):
            return -1000
        s = 100 if "flash" in n else (60 if "pro" in n else 0)
        m = re.search(r'(\d+)\.(\d+)', n)
        if m:
            s += int(m.group(1)) * 10 + int(m.group(2))
        if "lite" in n:
            s -= 2            # full flash beats flash-lite for agentic reasoning
        if "exp" in n or "preview" in n:
            s -= 6            # prefer stable
        if "latest" in n:
            s += 1
        return s
    cands = [m for m in (available or []) if score(m) > -1000]
    return max(cands, key=score) if cands else None


class _GeminiMessages:
    def __init__(self, backend):
        self._b = backend

    def create(self, **kw):
        return self._b._create(kw.get("system"), kw.get("tools"),
                               kw.get("messages"), kw.get("max_tokens", 4096))


class _GeminiClient:
    def __init__(self, backend):
        self.messages = _GeminiMessages(backend)


class GeminiBackend:
    """Google Gemini backend (free tier). Mirrors AnthropicBackend's interface."""
    def __init__(self, api_key, model=_GEMINI_MODEL):
        self._no_key = (api_key == _NO_KEY)
        self.api_key = "" if self._no_key else api_key
        self.model = model or _GEMINI_MODEL
        self.base_model = self.model
        self.auto_model = False   # single model — no Haiku/Sonnet routing
        self.expert_mode = False
        self.auto_approve = False
        self.client = _GeminiClient(self)
        self._session_input_tokens = 0
        self._session_output_tokens = 0
        self._session_cache_creation_tokens = 0
        self._session_cache_read_tokens = 0

    def label(self):
        return f"Google Gemini · {self.model} (free)"

    def select_model_for_task(self, user_text="", round_num=1):
        return  # Gemini uses one model; nothing to route

    def _set_key(self, key):
        self.api_key = key; self._no_key = False
        save_cfg({"provider": "gemini", "gemini_api_key": key})
        ok("Gemini key saved! AI features are now enabled (free tier).")

    def _record_usage(self, usage):
        self._session_input_tokens  += getattr(usage, "input_tokens", 0) or 0
        self._session_output_tokens += getattr(usage, "output_tokens", 0) or 0

    def session_cost_estimate(self) -> str:
        return (f"Google Gemini free tier · no API charges  "
                f"(session: ~{self._session_input_tokens:,} in + ~{self._session_output_tokens:,} out tokens)")

    def _resolve_model(self):
        """Ask Google for an available model when the current one is retired."""
        try:
            return _gemini_pick_model(_gemini_list_models(self.api_key))
        except Exception:
            return None

    def _gen(self, contents, system_text, tools_decl, max_tokens, _retry=True):
        body = {"contents": contents,
                "generationConfig": {"maxOutputTokens": max(max_tokens or 4096, 1), "temperature": 0.6}}
        if system_text:
            body["systemInstruction"] = {"parts": [{"text": system_text}]}
        if tools_decl:
            body["tools"] = [{"functionDeclarations": tools_decl}]
        url = f"{_GEMINI_ENDPOINT}/{self.model}:generateContent"
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(e.read().decode()).get("error", {}).get("message", "")
            except Exception:
                pass
            # Model retired/unavailable → discover a working one and retry once.
            if e.code == 404 and _retry:
                alt = self._resolve_model()
                if alt and alt != self.model:
                    print(f"\r  {DIM}Gemini model updated to {alt} (previous one was retired).{R}")
                    self.model = alt; self.base_model = alt
                    save_cfg({"gemini_model": alt})
                    return self._gen(contents, system_text, tools_decl, max_tokens, _retry=False)
                raise RuntimeError(f"Gemini model unavailable and no alternative found for this key. {detail}")
            if e.code in (400, 403) and ("key" in detail.lower() or e.code == 403):
                raise RuntimeError(f"Gemini API key rejected — check it at https://aistudio.google.com/apikey. {detail}")
            if e.code == 429:
                raise RuntimeError(f"Gemini free-tier limit hit — wait a minute and retry. {detail}")
            raise RuntimeError(f"Gemini API error {e.code}: {detail or e}")

    def _prompt_for_key(self):
        print(f"\n  {YELLOW}{BOLD}🔑 AI features need a Google Gemini API key.{R}")
        print(f"  {DIM}It's free — no credit card. Get one at:{R} {CYAN}https://aistudio.google.com/apikey{R}\n")
        try:
            key = input("  Paste Gemini key now (or press Enter to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            return False
        if not key:
            info(f"Cancelled. Type {BOLD}k{R} at the menu anytime to add your key.")
            return False
        self._set_key(key)
        return True

    def ask(self, system, messages, max_tokens=4096, cache_system=False):
        """Text completion — used by fix_engine (returns a plain string)."""
        if self._no_key and not self._prompt_for_key():
            return ""
        print(f"\r  {CYAN}⚡ Asking Gemini…{R}   ", end="", flush=True)
        data = self._gen(_gem_contents_from_anthropic(messages),
                         _gem_system_to_text(system), None, max_tokens)
        self._record_usage(_gem_usage(data))
        blocks, _ = _gem_blocks_from_response(data)
        text = "".join(b.text for b in blocks if b.type == "text" and b.text)
        print(f"\r  {GREEN}✓ Response received ({len(text)} chars)   {R}")
        return text

    def _create(self, system, tools, messages, max_tokens):
        """Anthropic-shaped tool-use call — used by agentic_engine."""
        if self._no_key and not self._prompt_for_key():
            return _GResponse([_GBlock("text", text="")], "end_turn", _GUsage(0, 0))
        data = self._gen(_gem_contents_from_anthropic(messages),
                         _gem_system_to_text(system),
                         _gem_tools_from_anthropic(tools), max_tokens or 4096)
        blocks, stop = _gem_blocks_from_response(data)
        return _GResponse(blocks, stop, _gem_usage(data))


# ── Config / API key ─────────────────────────────────────────────────────────
_NO_KEY = "__NO_KEY__"   # sentinel — user chose to skip key setup

def _migrate_old_key():
    """Pull an API key from the old ai-terminal install if one exists."""
    try:
        old = json.loads(open(os.path.expanduser("~/.config/ai-terminal/config.json")).read())
        k = old.get("api_key","").strip()
        if k:
            ok("API key migrated from ai-terminal — no need to re-enter!")
            return k
    except Exception:
        pass
    return ""

def _load_api_key(cfg):
    """Get API key from env, config, or migration."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key: return key
    key = cfg.get("api_key", "").strip()
    if key: return key
    return _migrate_old_key()

def _setup_wizard(cfg):
    """First-run wizard. Lets the user choose Claude (best) or Gemini (free),
    or skip. Returns ('claude'|'gemini', api_key) | ('skip', None)."""
    _line = f"  {DIM}{'─'*58}{R}"
    print(f"\n{_line}")
    print(f"  {GREEN}{BOLD}🐧 TuxGenie — Quick Setup{R}")
    print(f"{_line}")
    print(f"\n  TuxGenie uses an AI to understand and fix Linux problems.")
    print(f"  Pick one — you can change it anytime in Settings:\n")
    print(f"  {C('[1]',CYAN,BOLD)} {BOLD}Claude{R} (Anthropic) — best quality")
    print(f"      {DIM}Free trial credit, then ~$0.01/session · console.anthropic.com{R}")
    print(f"  {C('[2]',CYAN,BOLD)} {BOLD}Google Gemini{R} — {GREEN}free tier, no credit card{R} {DIM}(beta){R}")
    print(f"      {DIM}Get a free key at aistudio.google.com/apikey{R}\n")
    try:
        choice = input(f"  Choose {BOLD}1{R} or {BOLD}2{R} (or press {BOLD}Enter{R} to skip for now): ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)
    if choice == "2":
        print(f"\n  {DIM}Free Gemini key: {CYAN}https://aistudio.google.com/apikey{R}")
        print(f"  {DIM}Heads-up: on Google's {BOLD}free{R}{DIM} tier, Google may use your prompts")
        print(f"  {DIM}& responses to improve their products. Great for everyday use —")
        print(f"  {DIM}pick Claude for confidential machines. Full details: PRIVACY.md{R}")
        try:
            key = input("  Paste your Gemini API key: ").strip()
        except (EOFError, KeyboardInterrupt):
            return ("skip", None)
        return ("gemini", key) if key else ("skip", None)
    if choice == "1":
        print(f"\n  {DIM}Free Claude key: {CYAN}https://console.anthropic.com{R}")
        try:
            key = input("  Paste your Anthropic API key: ").strip()
        except (EOFError, KeyboardInterrupt):
            return ("skip", None)
        return ("claude", key) if key else ("skip", None)
    print(f"\n  {YELLOW}Continuing without AI.{R}")
    print(f"  {DIM}Type {BOLD}k{R}{DIM} anytime to add a key later.{R}\n")
    return ("skip", None)


def _make_backend(cfg, provider, key):
    """Build the right backend and apply shared user preferences."""
    if provider == "gemini":
        b = GeminiBackend(api_key=key, model=cfg.get("gemini_model", _GEMINI_MODEL))
    else:
        b = AnthropicBackend(api_key=key, model=cfg.get("model", _HAIKU_MODEL))
    b.expert_mode  = bool(cfg.get("expert_mode", False))
    b.auto_approve = bool(cfg.get("auto_approve", False))
    return b


def load_backend():
    """Load config and return the configured backend. Defaults to Claude and is
    fully back-compatible: existing installs (api_key set, no 'provider') load
    exactly as before. Gemini is only used when the user opts into it."""
    cfg = load_cfg()
    provider = cfg.get("provider", "")

    # 1. Explicit Gemini provider with a saved/env key.
    if provider == "gemini":
        gkey = (os.environ.get("GEMINI_API_KEY", "").strip()
                or os.environ.get("GOOGLE_API_KEY", "").strip()
                or cfg.get("gemini_api_key", "").strip())
        if gkey:
            save_cfg({"provider": "gemini", "gemini_api_key": gkey})
            return _make_backend(cfg, "gemini", gkey)

    # 2. Saved/env Claude key (the default, unchanged path).
    key = _load_api_key(cfg)
    if key:
        save_cfg({"api_key": key, "provider": "claude", "backend": "claude"})
        return _make_backend(cfg, "claude", key)

    # 3. A Gemini key in the env even without an explicit provider.
    gkey = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    if gkey:
        save_cfg({"provider": "gemini", "gemini_api_key": gkey})
        return _make_backend(cfg, "gemini", gkey)

    # 4. First run — ask which AI to use.
    kind, value = _setup_wizard(cfg)
    if kind == "gemini":
        save_cfg({"provider": "gemini", "gemini_api_key": value})
        return _make_backend(cfg, "gemini", value)
    if kind == "claude":
        save_cfg({"provider": "claude", "backend": "claude", "api_key": value})
        return _make_backend(cfg, "claude", value)
    save_cfg({"backend": "none"})
    return _make_backend(cfg, "claude", _NO_KEY)

AVAILABLE_MODELS = [
    ("claude-haiku-4-5-20251001", "Fast & cheapest — handles 90% of tasks perfectly (recommended)"),
    ("claude-sonnet-4-6",   "Smarter — for complex debugging (auto-escalates when needed)"),
    ("claude-opus-4-8",     "Most capable — for the hardest problems (costs ~6x more)"),
]

def feat_set_api_key(backend):
    """Add or change the Anthropic API key — command: k"""
    hdr("Claude API Key")
    info(f"Current: {backend.label()}")
    print(f"\n  Get your key at: {CYAN}{BOLD}https://console.anthropic.com{R}")
    print(f"  {DIM}Sign-up is free. Anthropic charges by usage (a few cents/session).{R}\n")
    try:
        key = input("  Paste API key (or press Enter to cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not key:
        warn("No key entered. Nothing changed.")
        return
    if not re.match(r'^sk-ant-[a-zA-Z0-9_\-]{60,}$', key):
        warn("That doesn't look like a valid Anthropic API key.")
        info("Keys start with  sk-ant-api03-…  and are ~100 characters long.")
        try:
            confirm = input("  Save it anyway? [y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"
        if confirm not in ("y", "yes"):
            warn("Key not saved.")
            return
    save_cfg({"backend": "claude", "api_key": key})
    backend._set_key(key)
    ok("Claude key saved.")

def feat_settings(backend, bctx, slog):
    """Settings: view/change API key and model."""
    hdr("Settings")
    info(f"Backend: {backend.label()}")
    auto_tag    = C(" ON", GREEN)  if backend.auto_model  else C(" OFF", YELLOW)
    expert_tag  = C(" ON", GREEN)  if backend.expert_mode else C(" OFF", DIM)
    approve_tag = C(" ON", YELLOW) if backend.auto_approve else C(" OFF", GREEN)
    cfg         = load_cfg()
    history_on  = not cfg.get("disable_history", False)
    history_tag = C(" ON", GREEN) if history_on else C(" OFF", YELLOW)
    print(f"  {DIM}Smart model routing:{R}{auto_tag}")
    print(f"  {DIM}Expert mode (compact output):{R}{expert_tag}")
    print(f"  {DIM}Cross-session memory:{R}{history_tag}")
    print(f"  {DIM}Auto-approve AI commands (skip per-step confirm):{R}{approve_tag}")
    if backend._session_input_tokens > 0:
        print(f"  {DIM}{backend.session_cost_estimate()}{R}")
    print(f"\n  {C('[1]',CYAN)} Change API key")
    print(f"  {C('[2]',CYAN)} Change model")
    print(f"  {C('[3]',CYAN)} Toggle smart model routing (auto Haiku/Sonnet)")
    print(f"  {C('[4]',CYAN)} Toggle expert mode  {DIM}(compact output — skip beginner explanations){R}")
    print(f"  {C('[5]',CYAN)} Toggle cross-session memory  {DIM}(remember past commands & system info){R}")
    print(f"  {C('[6]',CYAN)} Clear stored memory  {DIM}(wipe action log + fingerprint){R}")
    print(f"  {C('[7]',CYAN)} Toggle auto-approve  {DIM}(run AI commands without asking — advanced){R}")
    print(f"  {C('[8]',CYAN)} Switch AI provider  {DIM}(Claude · or Google Gemini — free tier){R}")
    print(f"  {C('[q]',DIM)} Back to menu")
    try:
        ch = input(f"\n  {BOLD}Choice:{R} ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if ch == "1":
        try:
            key = input("  Paste new Anthropic API key: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if key:
            if not re.match(r'^sk-ant-[a-zA-Z0-9_\-]{60,}$', key):
                warn("That doesn't look like a valid Anthropic key (should start with sk-ant-…).")
                try:
                    confirm = input("  Save anyway? [y/n]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    confirm = "n"
                if confirm not in ("y", "yes"):
                    warn("Key not saved."); return
            backend._set_key(key)
            ok("API key updated — active now.")
    elif ch == "2":
        if isinstance(backend, GeminiBackend):
            info("Model selection applies to Claude. You're on Google Gemini (single free model).")
            return
        print(f"\n  {BOLD}Choose a model:{R}")
        for i, (mid, desc) in enumerate(AVAILABLE_MODELS, 1):
            current = C(" ← current", GREEN) if mid == backend.model else ""
            print(f"  {C(f'[{i}]', CYAN)} {mid}{current}")
            print(f"       {DIM}{desc}{R}")
        try:
            sel = input(f"\n  {BOLD}Choice [1-{len(AVAILABLE_MODELS)}]:{R} ").strip()
            idx = int(sel) - 1
            if 0 <= idx < len(AVAILABLE_MODELS):
                chosen = AVAILABLE_MODELS[idx][0]
                backend.model = chosen
                backend.base_model = chosen
                backend.auto_model = False  # manual selection disables auto-routing
                save_cfg({"model": chosen})
                ok(f"Model set to {chosen}")
                info("Smart model routing disabled (you chose a specific model).")
            else:
                warn("Invalid selection.")
        except (ValueError, EOFError, KeyboardInterrupt):
            warn("Invalid selection.")
    elif ch == "3":
        backend.auto_model = not backend.auto_model
        if backend.auto_model:
            ok("Smart model routing ON — Haiku for simple tasks, Sonnet for complex ones (saves ~80% on simple tasks).")
        else:
            ok(f"Smart model routing OFF — always using {backend.base_model}.")
    elif ch == "4":
        backend.expert_mode = not backend.expert_mode
        save_cfg({"expert_mode": backend.expert_mode})
        if backend.expert_mode:
            ok("Expert mode ON — compact output, no beginner explanations.")
        else:
            ok("Expert mode OFF — full output with friendly explanations.")
    elif ch == "5":
        new_state = not load_cfg().get("disable_history", False)
        save_cfg({"disable_history": new_state})
        if new_state:
            ok("Cross-session memory OFF — no commands or system info will be saved.")
            info("Already-stored data is kept until you wipe it (option 6).")
        else:
            ok("Cross-session memory ON — TuxGenie will remember past commands and system info.")
    elif ch == "6":
        try:
            confirm = input(f"\n  {YELLOW}Wipe stored action log and system fingerprint? [y/n]:{R} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if confirm in ("y", "yes"):
            _action_log_clear()
            try:
                if os.path.exists(FINGERPRINT_FILE):
                    os.remove(FINGERPRINT_FILE)
                if os.path.exists(HISTORY_FILE):
                    os.remove(HISTORY_FILE)
            except Exception:
                pass
            ok("Stored memory wiped.")
        else:
            info("Cancelled — nothing was wiped.")
    elif ch == "7":
        backend.auto_approve = not backend.auto_approve
        save_cfg({"auto_approve": backend.auto_approve})
        if backend.auto_approve:
            warn("Auto-approve ON — AI commands run without asking (dangerous ones are still blocked).")
        else:
            ok("Auto-approve OFF — you'll be asked before any command that changes your system.")
    elif ch == "8":
        cur = "Google Gemini (free)" if isinstance(backend, GeminiBackend) else "Claude (Anthropic)"
        print(f"\n  {DIM}Currently using: {BOLD}{cur}{R}")
        print(f"  {C('[1]',CYAN)} Claude (Anthropic) — best quality, ~$0.01/session")
        print(f"      {DIM}Get a key: {CYAN}https://console.anthropic.com{R}")
        print(f"  {C('[2]',CYAN)} Google Gemini — {GREEN}free tier, no credit card{R} {DIM}(beta){R}")
        print(f"      {DIM}Get a free key: {CYAN}https://aistudio.google.com/apikey{R}")
        try:
            p = input(f"\n  {BOLD}Choose provider [1/2] (or Enter to cancel):{R} ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if p == "1":
            k = load_cfg().get("api_key", "").strip()
            if not k:
                print(f"  {DIM}Get your key at: {CYAN}https://console.anthropic.com{R}")
                try:
                    k = input("  Paste your Anthropic API key (sk-ant-…): ").strip()
                except (EOFError, KeyboardInterrupt):
                    return
                if not k:
                    warn("No key entered — provider unchanged."); return
            save_cfg({"provider": "claude", "api_key": k})
            ok("Switched to Claude. Restart TuxGenie for it to take effect.")
        elif p == "2":
            print(f"  {DIM}Note: on Google's {BOLD}free{R}{DIM} tier, Google may use your prompts &")
            print(f"  {DIM}responses to improve their products. Prefer Claude for sensitive")
            print(f"  {DIM}systems. Full details in PRIVACY.md.{R}")
            k = load_cfg().get("gemini_api_key", "").strip()
            if not k:
                print(f"  {DIM}Free Gemini key: {CYAN}https://aistudio.google.com/apikey{R}")
                try:
                    k = input("  Paste your Gemini API key: ").strip()
                except (EOFError, KeyboardInterrupt):
                    return
                if not k:
                    warn("No key entered — provider unchanged."); return
            save_cfg({"provider": "gemini", "gemini_api_key": k})
            ok("Switched to Google Gemini (free tier). Restart TuxGenie for it to take effect.")
        else:
            info("Provider unchanged.")

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — SYSTEM CONTEXT COLLECTORS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Spinner — shows activity while waiting ───────────────────────────────────
class Spinner:
    """Animated spinner that runs in a background thread."""
    _FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    def __init__(self, msg=""):
        self._msg = msg; self._stop = threading.Event(); self._t = None
    def __enter__(self):
        self._stop.clear()
        self._t = threading.Thread(target=self._spin, daemon=True)
        self._t.start(); return self
    def __exit__(self, *_):
        self._stop.set()
        self._t.join(timeout=3)   # never hang forever
        sys.stdout.write(f'\r  {" " * (len(self._msg)+10)}\n')
        sys.stdout.flush()
    def _spin(self):
        i = 0
        while not self._stop.wait(0.08):
            print(f"\r  {BLUE}{self._FRAMES[i % len(self._FRAMES)]}{R} {DIM}{self._msg}{R}",
                  end="", flush=True)
            i += 1

def _r(cmd, t=6):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=t)
        return (r.stdout.strip() or r.stderr.strip())[:1000]
    except Exception:
        return ""

def _parallel_ctx(cmds_dict: dict, timeout=6) -> dict:
    """Run multiple shell commands in parallel and return {key: output}."""
    result = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(_r, cmd, timeout): key
                   for key, cmd in cmds_dict.items()}
        for f in as_completed(futures):
            result[futures[f]] = f.result()
    return result

def _load_fingerprint() -> dict:
    """Return the cached system fingerprint (or empty dict if none / disabled)."""
    if load_cfg().get("disable_history"):
        return {}
    try:
        return json.loads(open(FINGERPRINT_FILE).read())
    except Exception:
        return {}


def _save_fingerprint(fp: dict):
    if load_cfg().get("disable_history"):
        return
    try:
        with open(FINGERPRINT_FILE, "w") as f:
            json.dump(fp, f, indent=2)
        os.chmod(FINGERPRINT_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def collect_fingerprint(force: bool = False) -> dict:
    """Collect a deeper picture of the system: hardware, GPU, audio, network,
    and the apps the user has installed. Cached for 24h to avoid running
    the probes every launch — refresh by deleting FINGERPRINT_FILE or
    passing force=True. All probes are read-only and timeout-bounded."""
    if not force:
        existing = _load_fingerprint()
        if existing:
            ts = existing.get("_collected_at", 0)
            if time.time() - ts < 86400:  # 24h
                return existing
    cmds = {
        "ram":          "free -h | awk 'NR==2{print $2 \" total / \" $3 \" used\"}'",
        "swap":         "free -h | awk 'NR==3{print $2 \" total / \" $3 \" used\"}'",
        "cpu":          "lscpu 2>/dev/null | grep -E 'Model name|^CPU\\(s\\)' | head -2 | tr '\\n' ' | '",
        "disk":         "df -h / 2>/dev/null | awk 'NR==2{print $2 \" total / \" $3 \" used (\" $5 \" full)\"}'",
        "gpu":          "lspci 2>/dev/null | grep -iE 'vga|3d|display' | head -3",
        "audio":        "lspci 2>/dev/null | grep -i audio | head -2",
        "network":      "ip -brief addr show 2>/dev/null | grep -v ' lo ' | head -5",
        "default_route":"ip route 2>/dev/null | awk '/default/{print $3, \"via\", $5; exit}'",
        # Top installed apps — keep it small so the system prompt doesn't bloat
        "apt_apps":     "dpkg-query -W -f='${Package}\\n' 2>/dev/null | head -30 | tr '\\n' ' '",
        "snap_apps":    "snap list 2>/dev/null | awk 'NR>1{print $1}' | head -20 | tr '\\n' ' '",
        "flatpak_apps": "flatpak list --app --columns=application 2>/dev/null | head -20 | tr '\\n' ' '",
        "kernel":       "uname -r",
        "boot_time":    "uptime -s 2>/dev/null",
        "session_type": "echo $XDG_SESSION_TYPE",
    }
    fp = _parallel_ctx(cmds)
    fp = {k: v for k, v in fp.items() if v and v.strip()}
    fp["_collected_at"] = int(time.time())
    _save_fingerprint(fp)
    return fp


def base_ctx() -> dict:
    pretty = ""
    try:
        for line in open("/etc/os-release"):
            if line.startswith("PRETTY_NAME="):
                pretty = line.split("=",1)[1].strip().strip('"')
    except Exception:
        pretty = _r("uname -s")
    pkg = "unknown"
    for pm in ("apt","dnf","pacman","zypper","apk","emerge","brew"):
        if _r(f"command -v {pm}"):
            pkg = pm; break
    return {
        "os":      pretty or "unknown",
        "kernel":  _r("uname -r"),
        "arch":    _r("uname -m"),
        "user":    os.environ.get("USER", os.environ.get("USERNAME","unknown")),
        "is_root": os.geteuid()==0 if hasattr(os,"geteuid") else False,
        "hostname":_r("hostname"),
        "uptime":  _r("uptime -p"),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP","none"),
        "pkg_mgr": pkg,
        "shell":   os.environ.get("SHELL","unknown"),
    }

def health_ctx() -> dict:
    return _parallel_ctx({
        "cpu_usage":       "top -bn1 | grep 'Cpu(s)' | awk '{print $2+$4\"%\"}'",
        "memory":          "free -h",
        "disk":            "df -h",
        "load":            "uptime",
        "failed_services": "systemctl --failed --no-pager 2>/dev/null",
        "dmesg_errors":    "dmesg -l err,crit,alert,emerg 2>/dev/null | tail -20",
        "top_procs_cpu":   "ps aux --sort=-%cpu | head -8",
        "top_procs_mem":   "ps aux --sort=-%mem | head -8",
        "zombie_procs":    "ps aux | awk '$8==\"Z\"' | wc -l",
        "temp":            "sensors 2>/dev/null | grep -E 'Core|Package' | head -6",
    })

def network_ctx() -> dict:
    gw = _r("ip route | awk '/default/{print $3; exit}'")
    cmds = {
        "interfaces":    "ip -brief addr show",
        "routes":        "ip route show",
        "dns":           "cat /etc/resolv.conf | grep nameserver",
        "ping_8888":     "ping -c2 -W2 8.8.8.8 2>&1",
        "ping_google":   "ping -c2 -W2 google.com 2>&1",
        "listening":     "ss -tuln",
        "wifi_info":     "iwconfig 2>/dev/null || nmcli dev 2>/dev/null | head -10",
        "firewall":      "ufw status 2>/dev/null || iptables -L INPUT -n 2>/dev/null | head -15",
    }
    if gw:
        cmds["ping_gateway"] = f"ping -c2 -W2 {gw} 2>&1"
    result = _parallel_ctx(cmds)
    if not gw:
        result["ping_gateway"] = "no gateway"
    return result

def security_ctx() -> dict:
    return _parallel_ctx({
        "open_ports":     "ss -tuln",
        "firewall":       "ufw status verbose 2>/dev/null || iptables -L -n 2>/dev/null | head -30",
        "ssh_config":     "grep -vE '^#|^$' /etc/ssh/sshd_config 2>/dev/null",
        "sudo_users":     "grep -E '^sudo|^wheel|^admin' /etc/group 2>/dev/null",
        "passwd_shadow":  "awk -F: '$2==\"!\"||$2==\"*\"||$2==\"!!\"' /etc/shadow 2>/dev/null | cut -d: -f1 | head -10",
        "suid_files":     "find /usr /bin /sbin -perm -4000 -type f 2>/dev/null",
        "failed_logins":  "grep -i 'failed\\|invalid' /var/log/auth.log 2>/dev/null | tail -10 || journalctl -u sshd -p warning -n 10 2>/dev/null",
        "last_logins":    "last -10 2>/dev/null",
        "cron_world":     "find /etc/cron* /var/spool/cron -perm -o+w 2>/dev/null",
        "listening_procs":"ss -tulnp 2>/dev/null",
    })

def disk_ctx() -> dict:
    return _parallel_ctx({
        "df":             "df -h",
        "inodes":         "df -i",
        "top_dirs_root":  "du -sh /* 2>/dev/null | sort -rh | head -12",
        "top_dirs_var":   "du -sh /var/* 2>/dev/null | sort -rh | head -10",
        "top_dirs_home":  "du -sh $HOME/.* $HOME/* 2>/dev/null | sort -rh | head -10",
        "old_logs":       "find /var/log -name '*.gz' -o -name '*.old' -o -name '*.1' 2>/dev/null | head -20",
        "journal_size":   "journalctl --disk-usage 2>/dev/null",
        "apt_cache":      "du -sh /var/cache/apt/ 2>/dev/null",
        "trash":          "du -sh ~/.local/share/Trash 2>/dev/null",
        "large_files":    "find / -xdev -size +100M -type f 2>/dev/null | head -15",
    })

def driver_ctx() -> dict:
    return _parallel_ctx({
        "pci":          "lspci 2>/dev/null",
        "usb":          "lsusb 2>/dev/null",
        "gpu":          "lspci 2>/dev/null | grep -iE 'VGA|3D|Display'",
        "wifi_card":    "lspci 2>/dev/null | grep -i network; lsusb 2>/dev/null | grep -iE 'wireless|wifi|802.11'",
        "audio":        "lspci 2>/dev/null | grep -i audio; aplay -l 2>/dev/null",
        "loaded_mods":  "lsmod | head -30",
        "dmesg_fw":     "dmesg 2>/dev/null | grep -i 'firmware\\|driver\\|error' | tail -20",
        "gpu_driver":   "glxinfo 2>/dev/null | grep renderer || lspci -k 2>/dev/null | grep -A2 VGA",
        "printers":     "lpstat -p 2>/dev/null || echo 'No CUPS'",
    })

def service_ctx() -> dict:
    return _parallel_ctx({
        "running":        "systemctl list-units --type=service --state=running --no-pager 2>/dev/null",
        "failed":         "systemctl --failed --no-pager 2>/dev/null",
        "enabled":        "systemctl list-unit-files --state=enabled --no-pager 2>/dev/null | head -30",
        "startup_time":   "systemd-analyze 2>/dev/null",
        "blame_top":      "systemd-analyze blame 2>/dev/null | head -15",
        "critical_chain": "systemd-analyze critical-chain 2>/dev/null | head -20",
        "memory_per_svc": "systemctl list-units --type=service --state=running --no-pager 2>/dev/null | head -20",
    })

def log_ctx(user_error: str = "") -> dict:
    result = _parallel_ctx({
        "journal_errors": "journalctl -p err -n 40 --no-pager 2>/dev/null",
        "journal_boot":   "journalctl -b -p warning --no-pager 2>/dev/null | head -30",
        "syslog":         "tail -40 /var/log/syslog 2>/dev/null || tail -40 /var/log/messages 2>/dev/null",
        "auth_log":       "tail -20 /var/log/auth.log 2>/dev/null",
        "dmesg_err":      "dmesg -l err,crit 2>/dev/null | tail -20",
        "kern_log":       "tail -20 /var/log/kern.log 2>/dev/null",
    })
    result["user_error"] = user_error
    return result

def update_ctx() -> dict:
    pkg = base_ctx().get("pkg_mgr", "unknown")
    cmds = {"snap_updates": "snap refresh --list 2>/dev/null",
            "flatpak_updates": "flatpak remote-ls --updates 2>/dev/null | head -10"}
    if pkg == "apt":
        cmds.update({
            "upgradable":    "apt list --upgradable 2>/dev/null | head -30",
            "security_only": "apt list --upgradable 2>/dev/null | grep -i security",
            "held":          "apt-mark showhold 2>/dev/null",
            "autoremove":    "apt-get --dry-run autoremove 2>/dev/null | tail -8",
            "last_upgrade":  "ls -lt /var/log/apt/history.log* 2>/dev/null | head -3",
            "apt_history":   "grep -h 'Upgrade:\\|Install:' /var/log/apt/history.log 2>/dev/null | tail -10",
        })
    elif pkg == "dnf":
        cmds.update({
            "upgradable":    "dnf check-update 2>/dev/null | head -30",
            "security_only": "dnf updateinfo list security 2>/dev/null | head -20",
            "held":          "dnf versionlock list 2>/dev/null",
            "autoremove":    "dnf autoremove --assumeno 2>/dev/null | tail -8",
        })
    elif pkg == "pacman":
        cmds.update({
            "upgradable":    "pacman -Qu 2>/dev/null | head -30",
            "aur_updates":   "yay -Qu 2>/dev/null | head -20 || paru -Qu 2>/dev/null | head -20",
        })
    elif pkg == "zypper":
        cmds.update({
            "upgradable":    "zypper list-updates 2>/dev/null | head -30",
            "security_only": "zypper list-updates -t patch 2>/dev/null | head -20",
        })
    return _parallel_ctx(cmds)

def hardware_ctx() -> dict:
    return _parallel_ctx({
        "cpu":       "lscpu | grep -E 'Model name|CPU\\(s\\)|Thread|MHz|Cache'",
        "memory":    "free -h && echo '---' && cat /proc/meminfo | grep -E 'MemTotal|MemFree|SwapTotal'",
        "disks":     "lsblk -d -o NAME,SIZE,MODEL,ROTA,TYPE",
        "gpu":       "lspci | grep -iE 'VGA|3D|Display|GPU'",
        "mobo":      "dmidecode -t baseboard 2>/dev/null | grep -E 'Manufacturer|Product Name'",
        "bios":      "dmidecode -t bios 2>/dev/null | grep -E 'Vendor|Version|Release'",
        "temps":     "sensors 2>/dev/null | head -20",
        "battery":   "upower -i $(upower -e | grep battery) 2>/dev/null | head -15",
        "usb":       "lsusb 2>/dev/null",
        "pci":       "lspci 2>/dev/null",
    })

def boot_ctx() -> dict:
    return _parallel_ctx({
        "total_time":     "systemd-analyze 2>/dev/null",
        "blame":          "systemd-analyze blame 2>/dev/null | head -20",
        "critical_chain": "systemd-analyze critical-chain 2>/dev/null",
        "failed":         "systemctl --failed --no-pager 2>/dev/null",
        "warnings":       "journalctl -b -p warning --no-pager 2>/dev/null | head -25",
        "dmesg_slow":     "dmesg 2>/dev/null | grep -i 'timeout\\|slow\\|error' | head -15",
    })

def docker_ctx() -> dict:
    if not _r("command -v docker"):
        return {"docker_installed": False}
    result = _parallel_ctx({
        "version":    "docker version --format '{{.Server.Version}}' 2>/dev/null",
        "containers": "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' 2>/dev/null",
        "images":     "docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' 2>/dev/null | head -15",
        "disk":       "docker system df 2>/dev/null",
        "networks":   "docker network ls 2>/dev/null",
        "compose":    "docker compose version 2>/dev/null || docker-compose version 2>/dev/null",
        "errors":     "journalctl -u docker -p err -n 20 --no-pager 2>/dev/null",
    })
    result["docker_installed"] = True
    return result

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — CLAUDE API + DANGER CHECK + STEP PROMPT
# ═══════════════════════════════════════════════════════════════════════════════
BASE_SYS = """You are TuxGenie — a friendly, patient Linux assistant.
The user is likely a BEGINNER who is using Linux for the first time.
They may not know what sudo, apt, systemctl, or any command means.

Your job: explain everything in plain English like you're helping a friend
who has never used a terminal before. No jargon without explanation.

RETURN ONLY VALID JSON — no markdown fences, no extra text outside the JSON.

Schema:
{
  "analysis": "<Simple, friendly explanation of what's going on. Use analogies.
               Example: 'Your disk is like a cupboard — it's 95% full, so
               things are slowing down. Let's clean out what you don't need.'>",
  "steps": [
    {
      "description": "<What this does in everyday language.
                       BAD: 'Flush DNS cache and restart resolved'
                       GOOD: 'This clears your computer's memory of website
                              addresses so it can look them up fresh — like
                              clearing a phone's autocomplete.'>",
      "command": "<exact shell command>",
      "risk": "safe | moderate | dangerous",
      "requires_root": true | false,
      "what_this_means": "<One sentence: what will happen when this runs.
                           Example: 'This will show you which programs are
                           using the most memory — nothing is changed.'
                           Example: 'This will restart your WiFi — you'll
                           lose connection for about 5 seconds.'>",
      "expected_output": "<optional: what success looks like, in plain words>"
    }
  ],
  "verify_command": "<A command that PROVES the task is done. Must return exit
                      code 0 ONLY on real success. Examples:
                      - Install task: 'dpkg -s brave-browser && which brave-browser'
                      - Fix WiFi: 'ping -c2 8.8.8.8'
                      - Start service: 'systemctl is-active --quiet nginx'
                      - Update task: 'apt list --upgradable 2>/dev/null | grep -c upgradable'
                      NEVER use '|| echo' or '|| true' — the command MUST fail
                      if the task is NOT actually done.>",
  "success_check": "<how the user can tell the issue is fixed, in plain words>",
  "needs_synthesis": false,
  "resolved": false
}

- Set needs_synthesis to TRUE for INFO-GATHERING tasks (checking RAM, hardware, disk usage,
  processes, logs, battery, etc.) — tasks where the goal is to ANSWER A QUESTION using
  gathered data. The engine will call you again with the actual outputs to give a direct answer.
- Set needs_synthesis to FALSE for ACTION tasks (install, remove, fix, configure, restart).

Rules:
- ALWAYS start with safe, read-only checks before making any changes.
- ALWAYS include a verify_command that PROVES the task succeeded. This will be
  run automatically — do NOT rely on the user to check.
- dangerous = rm -rf, dd if=, mkfs, fdisk, wipefs, shred, chmod 777 /
- requires_root: true for anything needing sudo (explain: "needs admin access").
- Use the correct package manager for the detected distro.
- One action per step — small, understandable chunks.
- If already resolved, return steps:[] and resolved:true.
- Keep descriptions SHORT but CLEAR. A beginner should understand every step.
- When a step needs sudo, add to description: "(needs admin password)"

CRITICAL — Apps that need their own repo (NOT in Ubuntu default apt):
The following apps are NOT in Ubuntu's default apt repositories.
Do NOT run 'apt-cache search' or 'apt install' for them without first adding their repo:
  brave-browser       → add https://brave-browser-apt-release.s3.brave.com/ repo
  opera-stable        → add https://deb.opera.com/opera-stable/ repo
  vivaldi-stable      → add https://repo.vivaldi.com/archive/deb/ repo
  google-chrome-stable → add https://dl.google.com/linux/chrome/deb/ repo
  microsoft-edge-stable → add https://packages.microsoft.com/repos/edge repo
  code (VS Code)      → add https://packages.microsoft.com/repos/code repo
  slack-desktop       → download .deb from https://slack.com/downloads/linux
  zoom                → download .deb from https://zoom.us/download
  discord             → download .deb from https://discord.com/download
For these, your FIRST steps must be: add GPG key → add repo → apt update → apt install.

CRITICAL — Preventing failures:
- NEVER fabricate or guess download URLs. If you don't know the exact URL,
  use the system package manager (apt/dnf/pacman) or search for it first:
  e.g. 'apt-cache search brave' or 'flatpak search brave' BEFORE trying to install.
- ALWAYS verify a package/app name exists before trying to install it:
  e.g. 'apt-cache show <pkg>' or 'snap info <pkg>' as a first step.
- If a previous round FAILED, you MUST try a COMPLETELY DIFFERENT approach.
  Do NOT repeat the same method with minor tweaks. If apt failed, try snap.
  If snap failed, try flatpak. If flatpak failed, try downloading from the
  official website. Exhaust all methods.
- Each step that depends on a previous step must check that the previous step
  actually worked. For example, do NOT run 'sudo dpkg -i file.deb' without
  first checking 'test -s file.deb' (file exists and is not empty).

CRITICAL — Handling websites and downloads:
- Many download pages use JavaScript to render content. curl/wget will ONLY
  get the static HTML, which may NOT contain actual download links.
- When you curl a download page, CAREFULLY analyze what you actually received.
  If the output is mostly HTML/CSS/JS scaffolding with no real .deb/.rpm/.tar
  links visible, that means the page is JavaScript-rendered and curl CANNOT
  get the real links.
- NEVER invent or guess a download URL like 'app-linux-x64.deb' — if you
  cannot find the EXACT URL in the page content, say so honestly.
- After downloading a file, ALWAYS verify it's the right type:
  'file downloaded_file' to check if it's actually a .deb/binary and NOT an
  HTML page saved with a wrong extension.
- If a downloaded file is actually HTML (not a real package), DELETE it and
  report the failure — do NOT try to install it.

CRITICAL — Knowing when to stop:
- Some apps genuinely DO NOT have a Linux desktop version. If after checking
  apt, snap, flatpak, and the official website you find NO Linux package,
  you MUST say so honestly: "This app is not available for Linux."
- Suggest alternatives: web app version, similar Linux apps, or Wine/browser.
- Do NOT endlessly retry different download URL guesses. 2 failed download
  attempts = the app likely has no Linux version. Stop and tell the user.
- Set resolved:true when you've given the user an honest, final answer —
  even if that answer is "not available for Linux."

CRITICAL — Removing / uninstalling apps:
- For ANY remove/uninstall request, your FIRST and ONLY step in round 1 must
  be a single broad search that finds HOW the app is installed:
    find ~ /opt /usr/local /usr/bin -iname '*<appname>*' 2>/dev/null; \
    dpkg -l 2>/dev/null | grep -i <appname>; \
    snap list 2>/dev/null | grep -i <appname>; \
    flatpak list 2>/dev/null | grep -i <appname>; \
    which <appname> 2>/dev/null
- Read the output of that search and ONLY use the removal method that matches
  what was actually found:
    • Found an AppImage in ~/Downloads or ~/.local/bin → delete the file +
      its .desktop shortcut
    • Found in dpkg output → apt purge
    • Found in snap list → snap remove
    • Found in flatpak list → flatpak uninstall
    • Found in /opt or ~/.local → rm the directory + .desktop shortcut
- Do NOT blindly try apt, then snap, then flatpak one-by-one when the first
  broad search already tells you exactly how it was installed.

CRITICAL — Empty output awareness:
- If a command returns exit code 0 but EMPTY output when output was expected
  (e.g. grep found nothing, curl returned nothing, apt-cache search found
  nothing), treat that as INCONCLUSIVE, not success.
- An empty grep result means the thing you searched for does NOT exist.
- An empty curl result means the download FAILED.

- RETURN ONLY VALID JSON.
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  AGENTIC ENGINE — True tool-use architecture (superior to Warp and all others)
#  Claude calls run_command one step at a time, sees real results, and genuinely
#  diagnoses instead of blindly generating a batch plan upfront.
# ═══════════════════════════════════════════════════════════════════════════════

AGENTIC_TOOLS = [
    {
        "name": "run_command",
        "description": "Run a shell command on the user's Linux system. Use this to diagnose and fix problems step by step. Each call should be purposeful — react to what you find.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Exact shell command to run"
                },
                "description": {
                    "type": "string",
                    "description": "Plain English explanation of what this command does and why — must be understandable by a complete beginner"
                },
                "risk": {
                    "type": "string",
                    "enum": ["safe", "moderate", "dangerous"],
                    "description": "safe=read-only, moderate=changes config/state, dangerous=destructive/irreversible"
                },
                "requires_root": {
                    "type": "boolean",
                    "description": "True if this command needs sudo/root access"
                }
            },
            "required": ["command", "description", "risk"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file on the user's system (logs, config files, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path or ~ path to the file"
                }
            },
            "required": ["path"]
        }
    }
]

AGENTIC_SYS = """You are TuxGenie, an AI assistant that fixes Linux problems for complete beginners.

You have two tools: run_command (run shell commands) and read_file (read files).

HOW TO WORK:
- Think step by step. DIAGNOSE before you FIX.
- Start with safe, read-only commands to understand the actual state of the system.
- Each command result informs what you do next — react to what you find, never plan
  all steps upfront.
- After fixing, run a command that PROVES the fix worked (e.g. ping for network,
  dpkg -s for install, systemctl is-active for services).
- Be honest if you cannot fix something.

COMMUNICATION:
- The user is a complete Linux beginner — they may not know what sudo, apt, systemctl,
  or any command means. Explain like you're helping a friend who has never opened a terminal.
- The description field of every tool call must be beginner-readable:
  BAD:  "Flush the DNS resolver cache"
  GOOD: "Clear your computer's memory of website addresses so it looks them up fresh"
- After finishing, give a short plain-English summary of what happened and what was fixed.

SAFETY:
- Never run destructive commands (rm -rf /, dd if=, mkfs, fdisk, wipefs, shred, chmod 777 /)
- Mark anything that changes system state as moderate or dangerous risk.
- Set requires_root: true for anything needing sudo.
- One action per tool call — small, understandable chunks.

REMOVING / UNINSTALLING APPS:
- FIRST step: run a single broad search to find HOW the app is installed:
    find ~ /opt /usr/local /usr/bin -iname '*<appname>*' 2>/dev/null; \\
    dpkg -l 2>/dev/null | grep -i <appname>; \\
    snap list 2>/dev/null | grep -i <appname>; \\
    flatpak list 2>/dev/null | grep -i <appname>; \\
    which <appname> 2>/dev/null
- Then ONLY use the removal method that matches what was found.
- Do NOT blindly try apt, then snap, then flatpak one-by-one.

INSTALLING APPS:
- ALWAYS verify a package name exists before trying to install it (apt-cache show,
  snap info, flatpak search).
- NEVER fabricate or guess download URLs. If you can't find the exact URL, say so.
- After downloading a file, verify its type with 'file <downloaded_file>'.
- If after checking apt, snap, flatpak, and the official website there is NO Linux
  package, say so honestly. Suggest alternatives (web app, Wine, similar Linux apps).

EMPTY OUTPUT:
- If a command returns exit code 0 but empty output when output was expected
  (grep found nothing, curl returned nothing), treat that as "not found", not success.

KNOWING WHEN TO STOP:
- If 2 different approaches failed for the same goal, stop and tell the user honestly
  what happened and what their options are. Do NOT endlessly retry.
"""


def _display_tool_call(cmd, description, risk, requires_root, step_num):
    """Show the user what Claude wants to do before running it."""
    risk_colour = {"safe": GREEN, "moderate": YELLOW, "dangerous": RED}.get(risk, CYAN)
    sudo_badge  = f"  {RED}{BOLD}[SUDO NEEDED]{R}" if requires_root else ""
    print(f"\n  {'─'*60}")
    print(f"  {CYAN}{BOLD}Step {step_num}{R}  {risk_colour}{BOLD}{risk.upper()}{R}{sudo_badge}")
    print(f"  {description}")
    print(f"  {DIM}$ {cmd}{R}")
    if risk == "dangerous":
        print(f"\n  {BG_RED}{BOLD}  ⚠  DESTRUCTIVE — review carefully  {R}")


def _handle_tool_call(block, sudo_pw, step_counter, backend=None, approve_state=None):
    """Execute a single tool call from the agentic engine.
    Uses run_cmd_live for real-time streaming output and proper sudo handling."""
    name = block.name
    inp  = block.input
    if approve_state is None:
        approve_state = {}

    if name == "run_command":
        cmd           = inp["command"]
        description   = inp.get("description", "")
        risk          = inp.get("risk", "safe")
        requires_root = inp.get("requires_root", False)

        _display_tool_call(cmd, description, risk, requires_root, step_counter[0])
        step_counter[0] += 1

        if is_dangerous(cmd):
            print(f"  {RED}✗  Blocked by TuxGenie safety filter.{R}")
            return "BLOCKED by TuxGenie safety filter — command matches a dangerous pattern."

        # Ask before running anything that could change the system (read-only
        # commands run automatically). _AbortSession propagates to the engine.
        if not _approval_gate(cmd, requires_root, backend, approve_state):
            print(f"  {YELLOW}⤷  Skipped by you.{R}")
            return ("SKIPPED by the user — they chose not to run this command. Do not "
                    "retry it; suggest a different approach or ask what they'd prefer.")

        # Use run_cmd_live for real-time output streaming + proper sudo handling
        actual_cmd = cmd
        if requires_root and not cmd.strip().startswith("sudo"):
            actual_cmd = f"sudo {cmd}"

        # Heavy package-manager / release-upgrade commands need a much longer
        # timeout than the default — apt upgrade routinely takes 10-60 minutes.
        # Without this Claude's tool-call would be SIGKILLed at 120s.
        _HEAVY_RE = re.compile(
            r'^\s*(?:sudo\s+)?'
            r'(?:apt(?:-get)?|dnf|yum|pacman|zypper|snap|flatpak)'
            r'(?:\s+-{1,2}[A-Za-z0-9-]+)*'
            r'\s+(?:upgrade|full-upgrade|dist-upgrade|install|reinstall|remove|autoremove|'
            r'purge|update|refresh|-S\b|-Syu\b|system-upgrade|do-release-upgrade)',
            re.IGNORECASE)
        _RELEASE_RE = re.compile(r'^\s*(?:sudo\s+)?do-release-upgrade\b', re.IGNORECASE)
        tool_timeout = 3600 if (_HEAVY_RE.search(actual_cmd) or _RELEASE_RE.search(actual_cmd)) else 300

        print(f"  {DIM}▶ Running…{R}")
        rc, stdout, stderr = run_cmd_live(
            actual_cmd,
            sudo_password=sudo_pw if requires_root else None,
            timeout=tool_timeout
        )
        output = (stdout or "") + (stderr or "")
        output = output.strip() or "(no output)"

        if rc == 0:
            print(f"  {GREEN}✔  Done{R}")
        elif rc == -1 and "Cancelled" in (stderr or ""):
            print(f"  {YELLOW}⚠  Cancelled by user{R}")
        else:
            print(f"  {YELLOW}⚠  Exit code {rc}{R}")

        # Persist for cross-session memory (no output, no secrets — just cmd + rc)
        _action_log_append(cmd, rc, "agentic")

        return output[:4000]   # cap what goes back to Claude

    elif name == "read_file":
        path = os.path.realpath(os.path.expanduser(inp["path"]))
        # Block paths that contain private credentials or sensitive system data
        _DENIED_PREFIXES = (
            os.path.expanduser("~/.ssh"),
            os.path.expanduser("~/.gnupg"),
            os.path.expanduser("~/.aws"),
            os.path.expanduser("~/.config/gcloud"),
            os.path.expanduser("~/.kube"),
            os.path.expanduser("~/.netrc"),
        )
        _DENIED_FILES = {
            "/etc/shadow", "/etc/gshadow", "/etc/sudoers",
            "/proc/keys", "/proc/key-users",
        }
        if (any(path.startswith(p) for p in _DENIED_PREFIXES)
                or path in _DENIED_FILES
                or path.endswith((".pem", ".key", ".p12", ".pfx"))):
            print(f"\n  {'─'*60}")
            print(f"  {RED}⚠  Blocked: {path} contains sensitive credentials.{R}")
            return f"BLOCKED: TuxGenie does not read credential files ({path})."
        try:
            with open(path) as f:
                content = f.read(8000)
            print(f"\n  {'─'*60}")
            print(f"  {CYAN}{BOLD}Read file{R}  {DIM}{path}{R}")
            return content
        except Exception as e:
            print(f"\n  {'─'*60}")
            print(f"  {YELLOW}Could not read {path}: {e}{R}")
            return f"Could not read file: {e}"

    return f"Unknown tool: {name}"


def agentic_engine(backend, task: str, ctx: dict, session_log: list, max_turns: int = 25):
    """Full agentic fix engine using Claude's native tool_use API.
    Claude calls run_command one step at a time, sees real output, and
    diagnoses/fixes based on actual results — no upfront batch planning.
    Powered by Opus 4.7 with adaptive thinking and prompt caching.

    Optimizations:
    - Prompt caching: tools + system are cached once; per-turn breakpoints on
      the latest user message let subsequent turns read everything before for
      ~0.1x cost. Saves the bulk of input tokens on long agentic loops.
    - Adaptive thinking + effort=xhigh: 4.7 dynamically allocates thinking
      tokens; xhigh is the recommended setting for coding/agentic work.
    """
    # A bare "q"/"back"/"cancel" is not a task — return to the menu, no AI call.
    if _is_back(task):
        return
    # ── Cross-session memory recall ─────────────────────────────────────────
    # Search for similar issues the user has had before and show a hint.
    # The AI also sees this via _mem_block() in the system prompt.
    _past = _mem_search(task)
    if _past:
        print(f"\n  {BMAGENTA}{BOLD}🧠 Memory:{R}  Similar issue resolved before:\n")
        for _e in _past[:2]:
            _steps = _e.get("steps", [])
            print(f"  {DIM}[{_e.get('ts','')}]{R}  {_e.get('problem','')}")
            if _steps:
                print(f"  {CYAN}→ Previously fixed by:{R} {_steps[0]}")
                if len(_steps) > 1:
                    print(f"  {DIM}  + {len(_steps)-1} more step(s){R}")
        print()

    # System prompt + tools are stable across the whole loop — cache them.
    system_blocks = [{
        "type": "text",
        "text": AGENTIC_SYS + _sys_ctx_block(ctx),
        "cache_control": {"type": "ephemeral"},
    }]
    # The last tool definition gets a cache_control so the entire tools array
    # is cached together with system. (Tools render before system in the prefix.)
    tools = [dict(t) for t in AGENTIC_TOOLS]
    tools[-1] = {**tools[-1], "cache_control": {"type": "ephemeral"}}

    messages = [{"role": "user", "content": task}]
    sudo_pw  = None
    step_counter = [1]
    approve_state = {"all": False}   # session-wide "yes to all" toggle

    _is_anthropic = isinstance(backend, AnthropicBackend)
    _ai_label = f"Anthropic · {_OPUS_MODEL}  ·  adaptive thinking" if _is_anthropic else backend.label()
    print(f"\n  {CYAN}{BOLD}⚡ AI: {_ai_label}{R}")

    def _create_request():
        # cache_control on the last block of the most recent user message
        # so the next turn can read the whole accumulated prefix back.
        msgs = [dict(m) for m in messages]
        last = msgs[-1]
        if last["role"] == "user":
            content = last["content"]
            if isinstance(content, str):
                content = [{"type": "text", "text": content,
                            "cache_control": {"type": "ephemeral"}}]
            elif isinstance(content, list) and content:
                content = [dict(b) for b in content]
                content[-1] = {**content[-1], "cache_control": {"type": "ephemeral"}}
            last["content"] = content
            msgs[-1] = last
        # Some Anthropic SDK versions don't accept thinking/output_config kwargs.
        # Try the rich call first, fall back to a basic create() if the SDK rejects them.
        try:
            return backend.client.messages.create(
                model        = _OPUS_MODEL,
                max_tokens   = 16000,
                thinking     = {"type": "adaptive"},
                output_config= {"effort": "xhigh"},
                system       = system_blocks,
                tools        = tools,
                messages     = msgs,
            )
        except TypeError:
            return backend.client.messages.create(
                model        = _OPUS_MODEL,
                max_tokens   = 16000,
                system       = system_blocks,
                tools        = tools,
                messages     = msgs,
            )

    try:
        for turn in range(max_turns):
            print(f"  {DIM}🤔 Thinking…{R}", end="\r", flush=True)
            try:
                response = _create_request()
            except KeyboardInterrupt:
                print(f"\n  {YELLOW}Cancelled.{R}")
                return
            except Exception as e:
                print(" " * 40, end="\r")
                kind, msg = _classify_anthropic_error(e)
                if kind == "billing":
                    print(f"  {RED}API error: {msg}.{R}")
                    print(f"  {DIM}Top up: https://console.anthropic.com/settings/billing{R}")
                elif kind == "auth":
                    print(f"  {RED}API error: {msg}.{R}")
                    print(f"  {DIM}Press {BOLD}k{R}{DIM} to set a new key.{R}")
                else:
                    print(f"  {RED}API error: {e}{R}")
                return

            # Track usage (regular + cache tokens) so session cost is accurate.
            if getattr(response, "usage", None):
                backend._record_usage(response.usage)

            print(" " * 40, end="\r", flush=True)

            # Show any text Claude produced (explanations between tool calls)
            for block in response.content:
                if hasattr(block, "text") and block.text.strip():
                    print()
                    for line in block.text.strip().splitlines():
                        print(f"  {line}")

            # Claude finished — no more tool calls
            if response.stop_reason == "end_turn":
                print(f"\n  {GREEN}{BOLD}✓  Done{R}")
                _ask_rating()
                return

            # Claude wants to use tools
            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                # Fetch sudo once if any tool call in this turn needs root
                if sudo_pw is None:
                    for block in response.content:
                        if getattr(block, "type", None) == "tool_use":
                            if block.input.get("requires_root"):
                                try:
                                    sudo_pw = get_or_cache_sudo_password()
                                except KeyboardInterrupt:
                                    print(f"\n  {YELLOW}Cancelled.{R}")
                                    return
                                break

                tool_results = []
                for block in response.content:
                    if getattr(block, "type", None) == "tool_use":
                        result = _handle_tool_call(block, sudo_pw, step_counter, backend, approve_state)
                        session_log.append({"command": block.input.get("command", ""), "source": "agentic"})
                        tool_results.append({
                            "type":        "tool_result",
                            "tool_use_id": block.id,
                            "content":     result
                        })

                messages.append({"role": "user", "content": tool_results})
                continue

            # Any other stop_reason (max_tokens, stop_sequence, refusal, …):
            # don't keep looping with the same prompt. Bail out with a useful
            # message so the user knows why we stopped.
            print(f"\n  {YELLOW}AI stopped: {response.stop_reason}.{R}")
            if response.stop_reason == "max_tokens":
                print(f"  {DIM}Response was cut off mid-stream. Try rephrasing your request more concisely.{R}")
            return

        print(f"\n  {YELLOW}Reached {max_turns} steps without completing. "
              f"The problem may need manual investigation.{R}")

    except _AbortSession:
        print(f"\n  {YELLOW}Stopped at your request.{R}")
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}Cancelled by user.{R}")
    finally:
        _restore_terminal()


DANGER_RE = [
    # ── Disk/filesystem destruction ──────────────────────────────────────────
    r"rm\s+-[rf]{1,2}\s+/\s*$",                     # rm -rf /
    r"rm\s+-[rf]{1,2}\s+/\s+\*",                    # rm -rf / *
    r"rm\s+-[rf]{1,2}\s+~\s*$",                     # rm -rf ~
    r"rm\s+-[rf]{1,2}\s+~/\s*$",                    # rm -rf ~/
    r"rm\s+--no-preserve-root",                      # explicit safety override
    # (Recursive rm of a whole system dir is caught precisely by the argv layer
    #  below, so deep sub-paths like /home/user/project stay allowed.)
    r"\bmkfs\b", r"\bfdisk\b",
    r"\bwipefs\b", r"\bshred\b", r"\btruncate\b.*\s/dev/",
    r">\s*/dev/sd", r">\s*/dev/nvme", r">\s*/dev/vd",
    # ── Fork bombs / resource exhaustion ────────────────────────────────────
    r":\(\)\{\s*:\|:&\s*\};:",                       # classic fork bomb
    r"\(\)\s*\{\s*\w+\s*\|\s*\w+\s*&\s*\}",         # alternate fork bomb form
    # ── Privilege escalation to root shell ──────────────────────────────────
    r"sudo\s+(?:bash|sh|dash|zsh|ksh|csh|tcsh|fish)\b",  # sudo <shell>
    r"sudo\s+-[si]\b",                               # sudo -s / sudo -i
    # ── Subshell injection inside privileged commands ────────────────────────
    r"sudo\b.*\$\(",                                 # sudo ... $( )
    r"sudo\b.*`",                                    # sudo ... `backtick`
    # ── Dangerous permission changes ─────────────────────────────────────────
    # (chmod of / or a system dir is caught precisely by the argv layer; this
    #  rule stays for the specific case of loosening perms on credential files.)
    r"chmod\s+[0-7]*[2367][0-7]*\s+/etc/(?:passwd|shadow|sudoers)",
]
# ── Argv-aware danger analysis ──────────────────────────────────────────────
# Regexes alone can't catch flag reorderings (rm -Rf, rm -r -f, --recursive),
# glob targets (rm -rf /*), or argument order (dd of=… if=…). This second layer
# tokenises each simple command and reasons about its argv, so destructive
# intent is caught regardless of spelling. It only ever *adds* blocks.

# Paths whose recursive deletion / permission-change / device-write is
# catastrophic. A target is compared after stripping a trailing "/*" and "/".
_PROTECTED_TARGETS = {
    "/", "~", os.path.expanduser("~"),
    "/boot", "/etc", "/usr", "/lib", "/lib64", "/bin", "/sbin",
    "/var", "/sys", "/proc", "/dev", "/run", "/opt", "/home", "/root",
}
# System directories where recursively deleting even a SUB-path (e.g.
# /boot/grub, /usr/bin, /var/lib/dpkg) can brick the machine. User-data trees
# (/home/<user>/…, /root/…, /tmp, /mnt, /media) are intentionally NOT here, so
# ordinary cleanup like `rm -rf ~/project/node_modules` stays allowed.
_CRITICAL_SYSTEM_DIRS = (
    "/boot", "/etc", "/usr", "/lib", "/lib64", "/bin", "/sbin",
    "/var", "/sys", "/proc", "/dev", "/run", "/opt",
)
_BLOCK_DEVICE_RE = re.compile(r"^/dev/(?:sd[a-z]|nvme\d|vd[a-z]|mmcblk\d|hd[a-z]|disk\d)", re.IGNORECASE)


def _hits_protected_path(target: str) -> bool:
    """True if `target` is a protected dir itself, or a path inside a critical
    system directory. User-data sub-paths (~/…, /home/x/…, /tmp/…) are allowed."""
    t = _norm_target(target)
    if t in _PROTECTED_TARGETS:
        return True
    return any(t == d or t.startswith(d + "/") for d in _CRITICAL_SYSTEM_DIRS)


def _norm_target(tok: str) -> str:
    """Normalise an rm/chmod/find target for comparison against protected paths.
    'rm -rf /etc/*' and '/etc/' both reduce to '/etc'."""
    t = tok.strip().strip('"').strip("'")
    if t.endswith("/*"):
        t = t[:-2] or "/"
    t = t.rstrip("/") or "/"
    return t


def _split_simple_commands(cmd: str):
    """Break a shell line into simple commands on ; && || | and newlines, then
    tokenise each. Falls back to a naive split on shlex failure so we fail safe
    (an unparseable fragment is still handed to the argv checks)."""
    out = []
    for part in re.split(r"\|\||&&|;|\||\n", cmd):
        part = part.strip()
        if not part:
            continue
        try:
            toks = shlex.split(part)
        except ValueError:
            toks = part.split()
        if toks and toks[0] == "sudo":
            toks = toks[1:]
            # skip sudo's own options (e.g. -S, -u user) to reach the real argv
            while toks and toks[0].startswith("-"):
                dropped = toks.pop(0)
                if dropped in ("-u", "--user", "-g", "--group") and toks:
                    toks.pop(0)
        if toks:
            out.append(toks)
    return out


def _rm_is_dangerous(toks) -> bool:
    short = "".join(t[1:] for t in toks[1:] if t.startswith("-") and not t.startswith("--"))
    longs = [t for t in toks[1:] if t.startswith("--")]
    recursive = ("r" in short.lower()) or ("--recursive" in longs)
    if "--no-preserve-root" in longs:
        return True
    # Recursing into a protected dir — or any path inside a critical system dir —
    # is catastrophic whether or not -f is given (-r alone still deletes writable
    # files). User-data sub-paths (~/…, /home/x/…, /tmp/…) stay allowed.
    if recursive:
        for t in (x for x in toks[1:] if not x.startswith("-")):
            if _hits_protected_path(t):
                return True
    return False


def _argv_is_dangerous(toks) -> bool:
    if not toks:
        return False
    prog = os.path.basename(toks[0])
    args = toks[1:]

    if prog == "rm":
        return _rm_is_dangerous(toks)

    if prog == "dd":
        # Writing to a raw block device wipes it — order of if=/of= is irrelevant.
        for a in args:
            if a.startswith("of=") and _BLOCK_DEVICE_RE.match(a[3:]):
                return True

    if prog in ("mkfs", "wipefs", "shred", "fdisk", "sgdisk", "parted", "blkdiscard"):
        if any(_BLOCK_DEVICE_RE.match(a) for a in args):
            return True

    if prog == "chmod":
        # Changing perms on / or a top-level system dir (esp. recursively) is
        # a classic way to render a system unbootable / world-writable.
        for t in (x for x in args if not x.startswith("-")):
            if _norm_target(t) in _PROTECTED_TARGETS:
                return True

    if prog == "chown":
        recursive = any(a in ("-R", "--recursive") or (a.startswith("-") and "R" in a) for a in args)
        if recursive:
            for t in (x for x in args if not x.startswith("-")):
                if _norm_target(t) in _PROTECTED_TARGETS:
                    return True

    if prog == "find":
        destructive = ("-delete" in args) or ("-exec" in args and "rm" in args)
        if destructive:
            root = next((a for a in args if not a.startswith("-")), None)
            if root is not None and _hits_protected_path(root):
                return True

    if prog == "tee":
        if any(_BLOCK_DEVICE_RE.match(_norm_target(a)) for a in args):
            return True

    return False


def is_dangerous(cmd):
    # Layer 1: fast regex denylist (redirects to devices, sudo shells, etc.)
    if any(re.search(p, cmd) for p in DANGER_RE):
        return True
    # Layer 1b: whitespace-tolerant classic fork bomb, e.g. ": () { : | : & } ; :"
    if re.search(r":\(\)\{:\|:&\};:", re.sub(r"\s+", "", cmd)):
        return True
    # Layer 2: argv-aware analysis of each simple command in the pipeline/chain.
    try:
        for toks in _split_simple_commands(cmd):
            if _argv_is_dangerous(toks):
                return True
    except Exception:
        # Never let the safety check itself crash — but do not silently pass a
        # command we failed to analyse if it *looks* destructive.
        return bool(re.search(r"\b(rm|dd|mkfs|wipefs|shred)\b", cmd))
    return False


# ── Per-step approval gate ──────────────────────────────────────────────────
# The safety promise is "TuxGenie never changes your system without your OK".
# is_dangerous() hard-blocks catastrophic commands, but ordinary state-changing
# ones (installs, service restarts, edits) still need consent. To keep diagnosis
# fast, read-only commands run automatically; anything that could change the
# system is shown and confirmed. Power users can set auto_approve to opt out.

class _AbortSession(Exception):
    """Raised when the user chooses to abort the whole AI session at a prompt."""


# Tools that only read/report state. Dual-use tools (systemctl, ip, docker, git,
# apt…) are listed here but guarded by _WRITE_SUBCMDS below.
_READ_ONLY_CMDS = {
    "ls", "dir", "cat", "bat", "head", "tail", "less", "more", "zcat", "zless",
    "grep", "egrep", "fgrep", "zgrep", "rg", "ag", "cut", "sort", "uniq", "wc",
    "find", "locate", "which", "whereis", "type", "file", "stat", "readlink",
    "realpath", "pwd", "tree", "du", "df", "free", "ps", "pgrep", "pidof", "top",
    "htop", "uptime", "uname", "hostname", "whoami", "id", "groups", "who", "w",
    "last", "date", "echo", "printf", "env", "printenv", "locale", "true", "false",
    "systemctl", "journalctl", "dmesg", "loginctl", "timedatectl",
    "ip", "ifconfig", "ss", "netstat", "route", "arp", "ping", "ping6",
    "traceroute", "tracepath", "dig", "nslookup", "host", "getent", "nmcli",
    "iw", "iwconfig", "rfkill", "lsblk", "lsusb", "lspci", "lscpu", "lsmod",
    "blkid", "findmnt", "modinfo", "sensors", "acpi", "dmidecode", "lshw",
    "upower", "inxi", "vmstat", "iostat", "mpstat", "dpkg", "dpkg-query",
    "apt-cache", "apt", "snap", "flatpak", "pip", "pip3", "conda", "docker",
    "podman", "kubectl", "git", "ldd", "sysctl", "cmp", "diff", "nproc",
    "getconf", "tty", "column", "xxd", "od", "strings", "md5sum", "sha256sum",
}

# Sub-commands / flags that turn an otherwise read-only tool into a mutating one.
_WRITE_SUBCMDS = {
    "systemctl":  {"start", "stop", "restart", "reload", "reload-or-restart",
                   "enable", "disable", "mask", "unmask", "set-default", "isolate",
                   "kill", "daemon-reload", "daemon-reexec", "edit", "set-property",
                   "reset-failed", "poweroff", "reboot", "halt", "suspend"},
    "loginctl":   {"lock-session", "terminate-session", "kill-session", "poweroff", "reboot"},
    "timedatectl": {"set-time", "set-timezone", "set-ntp", "set-local-rtc"},
    "ip":         {"add", "del", "delete", "set", "flush", "change", "replace"},
    "nmcli":      {"up", "down", "add", "del", "delete", "modify", "edit",
                   "connect", "disconnect"},
    "rfkill":     {"block", "unblock"},
    "docker":     {"run", "rm", "rmi", "stop", "start", "kill", "exec", "build",
                   "pull", "push", "prune", "system", "volume", "network", "create",
                   "restart", "commit", "tag", "load", "import", "compose"},
    "podman":     {"run", "rm", "rmi", "stop", "start", "kill", "exec", "build",
                   "pull", "push", "prune"},
    "kubectl":    {"apply", "delete", "create", "edit", "scale", "patch", "replace",
                   "drain", "cordon", "uncordon"},
    "git":        {"push", "reset", "clean", "rebase", "commit", "checkout", "switch",
                   "merge", "rm", "mv", "stash", "cherry-pick", "revert", "am",
                   "apply", "gc", "prune"},
    "snap":       {"install", "remove", "refresh", "revert", "disable", "enable", "alias"},
    "flatpak":    {"install", "uninstall", "update", "remove", "override"},
    "apt":        {"install", "remove", "purge", "upgrade", "full-upgrade",
                   "autoremove", "update", "dist-upgrade"},
    "pip":        {"install", "uninstall"},
    "pip3":       {"install", "uninstall"},
    "conda":      {"install", "remove", "update", "create"},
    "dpkg":       {"-i", "--install", "-r", "--remove", "-P", "--purge",
                   "--configure", "--unpack"},
    "sysctl":     {"-w", "--write", "-p", "--load"},
}


def _is_read_only(cmd: str) -> bool:
    """Conservative: True only when we're confident the command cannot change
    system state (no sudo, no redirection/tee, no known write sub-command).
    Anything we can't be sure about returns False so the user is asked."""
    s = cmd.strip()
    if not s:
        return False
    if re.search(r"\bsudo\b", s):
        return False
    if re.search(r"(?<!\d)>>?", s) or re.search(r"\btee\b", s):   # writes to a file/device
        return False
    try:
        simple = _split_simple_commands(s)
    except Exception:
        return False
    if not simple:
        return False
    for toks in simple:
        if not toks:
            return False
        prog = os.path.basename(toks[0])
        if prog not in _READ_ONLY_CMDS:
            return False
        rest = toks[1:]
        writes = _WRITE_SUBCMDS.get(prog)
        if writes and any(a in writes for a in rest):
            return False
        if prog == "find" and any(a in ("-delete", "-exec", "-execdir", "-fprint", "-fprintf") for a in rest):
            return False
    return True


def _approval_gate(cmd, requires_root, backend, approve_state):
    """Decide whether to run an AI-proposed command. Returns True to run, False
    to skip; raises _AbortSession to stop the whole session. Read-only commands
    run silently; state-changing ones are confirmed unless auto_approve is set."""
    if getattr(backend, "auto_approve", False) or approve_state.get("all"):
        return True
    if not requires_root and _is_read_only(cmd):
        return True
    if not sys.stdin.isatty():
        print(f"  {YELLOW}⚠  Skipped — needs your approval but the session is non-interactive.{R}")
        return False
    prompt = (f"  {BOLD}Run this?{R} [{C('y',GREEN,BOLD)}=yes  {C('n',YELLOW,BOLD)}=skip  "
              f"{C('a',RED,BOLD)}=abort  {C('A',CYAN,BOLD)}=yes to all]: ")
    try:
        raw = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise _AbortSession()
    ans = raw.lower()
    if raw == "A" or ans in ("all", "yes-all", "yall"):
        approve_state["all"] = True
        return True
    if ans in ("a", "abort", "q", "quit"):
        raise _AbortSession()
    if ans in ("", "y", "yes"):
        return True
    return False


# ── Passthrough: commands that run directly without calling Claude ─────────────
# Each entry: (compiled_regex, risk_level, human_readable_description)
# Risk levels: "safe" | "moderate" | "dangerous"
_PASSTHROUGH = [
    # ── apt / apt-get ──────────────────────────────────────────────────────────
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+update\s*$"),
     "safe",     "Refresh package lists from repositories"),
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+upgrade\s*$"),
     "moderate", "Upgrade all installed packages"),
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+dist-upgrade\s*$"),
     "moderate", "Full distribution upgrade"),
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+full-upgrade\s*$"),
     "moderate", "Full upgrade (removes conflicting packages)"),
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+autoremove(?:\s+--purge)?\s*$"),
     "moderate", "Remove unused dependency packages"),
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+autoclean\s*$"),
     "safe",     "Remove outdated cached package files"),
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+clean\s*$"),
     "safe",     "Clear entire local package cache"),
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+install\s+[\w\-\+\.\~]+(?:\s+[\w\-\+\.\~]+)*\s*$"),
     "moderate", "Install package(s)"),
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+remove\s+[\w\-\+\.]+(?:\s+[\w\-\+\.]+)*\s*$"),
     "moderate", "Remove package(s)"),
    (re.compile(r"^\s*sudo\s+apt(?:-get)?\s+purge\s+[\w\-\+\.]+(?:\s+[\w\-\+\.]+)*\s*$"),
     "moderate", "Purge package(s) and their config files"),
    (re.compile(r"^\s*apt(?:-cache)?\s+search\s+.+$"),
     "safe",     "Search for packages"),
    (re.compile(r"^\s*apt(?:-cache)?\s+show\s+[\w\-\.]+\s*$"),
     "safe",     "Show package details"),
    # ── systemctl ──────────────────────────────────────────────────────────────
    (re.compile(r"^\s*(?:sudo\s+)?systemctl\s+status\s+[\w\.\-@\\]+\s*$"),
     "safe",     "Check service status"),
    (re.compile(r"^\s*sudo\s+systemctl\s+start\s+[\w\.\-@\\]+\s*$"),
     "moderate", "Start service"),
    (re.compile(r"^\s*sudo\s+systemctl\s+stop\s+[\w\.\-@\\]+\s*$"),
     "moderate", "Stop service"),
    (re.compile(r"^\s*sudo\s+systemctl\s+restart\s+[\w\.\-@\\]+\s*$"),
     "moderate", "Restart service"),
    (re.compile(r"^\s*sudo\s+systemctl\s+reload\s+[\w\.\-@\\]+\s*$"),
     "moderate", "Reload service configuration"),
    (re.compile(r"^\s*sudo\s+systemctl\s+enable\s+[\w\.\-@\\]+\s*$"),
     "moderate", "Enable service to start at boot"),
    (re.compile(r"^\s*sudo\s+systemctl\s+disable\s+[\w\.\-@\\]+\s*$"),
     "moderate", "Disable service from starting at boot"),
    (re.compile(r"^\s*(?:sudo\s+)?systemctl\s+list-units(?:\s+--\S+)*\s*$"),
     "safe",     "List active systemd units"),
    # ── snap ───────────────────────────────────────────────────────────────────
    (re.compile(r"^\s*sudo\s+snap\s+install\s+[\w\-\.]+(?:\s+--[\w\-=]+)*\s*$"),
     "moderate", "Install snap package"),
    (re.compile(r"^\s*sudo\s+snap\s+remove\s+[\w\-\.]+\s*$"),
     "moderate", "Remove snap package"),
    (re.compile(r"^\s*sudo\s+snap\s+refresh\s*(?:[\w\-\.]+)?\s*$"),
     "moderate", "Update snap package(s)"),
    (re.compile(r"^\s*snap\s+list\s*$"),
     "safe",     "List installed snaps"),
    (re.compile(r"^\s*snap\s+find\s+.+$"),
     "safe",     "Search for snaps"),
    # ── flatpak ────────────────────────────────────────────────────────────────
    (re.compile(r"^\s*flatpak\s+install\s+(?:--[\w\-]+\s+)*[\w\.\-]+\s*$"),
     "moderate", "Install flatpak app"),
    (re.compile(r"^\s*flatpak\s+remove\s+[\w\.\-]+\s*$"),
     "moderate", "Remove flatpak app"),
    (re.compile(r"^\s*flatpak\s+update\s*$"),
     "moderate", "Update all flatpak apps"),
    (re.compile(r"^\s*flatpak\s+list\s*$"),
     "safe",     "List installed flatpaks"),
    # ── system info (read-only) ────────────────────────────────────────────────
    (re.compile(r"^\s*df(?:\s+-[hHiTa]+)?\s*$"),
     "safe",     "Show disk space usage"),
    (re.compile(r"^\s*free(?:\s+-[hmgbkst]+)?\s*$"),
     "safe",     "Show memory usage"),
    (re.compile(r"^\s*uptime\s*$"),
     "safe",     "Show system uptime and load"),
    (re.compile(r"^\s*uname(?:\s+-[a-zA-Z]+)?\s*$"),
     "safe",     "Show kernel/OS info"),
    (re.compile(r"^\s*lsb_release(?:\s+-[a-z]+)?\s*$"),
     "safe",     "Show Linux distribution info"),
    (re.compile(r"^\s*top\s*$"),
     "safe",     "Interactive process viewer"),
    (re.compile(r"^\s*htop\s*$"),
     "safe",     "Interactive process viewer (htop)"),
    (re.compile(r"^\s*ps\s+(?:aux|auxf|ef|e|u)\s*$"),
     "safe",     "List running processes"),
    (re.compile(r"^\s*lscpu\s*$"),
     "safe",     "Show CPU information"),
    (re.compile(r"^\s*lsblk(?:\s+-\w+)?\s*$"),
     "safe",     "Show block devices"),
    (re.compile(r"^\s*lsusb(?:\s+-v)?\s*$"),
     "safe",     "List USB devices"),
    (re.compile(r"^\s*lspci(?:\s+-[a-z]+)?\s*$"),
     "safe",     "List PCI devices"),
    # ── networking ────────────────────────────────────────────────────────────
    (re.compile(r"^\s*ip\s+(?:addr|address|link|route|r|neigh|a)\s*$"),
     "safe",     "Show network interfaces/routes"),
    (re.compile(r"^\s*ifconfig\s*$"),
     "safe",     "Show network interfaces"),
    (re.compile(r"^\s*ping\s+(?:-c\s+\d+\s+)?[\w\.\-]+\s*$"),
     "safe",     "Ping a host"),
    (re.compile(r"^\s*netstat(?:\s+-\w+)?\s*$"),
     "safe",     "Show network connections"),
    (re.compile(r"^\s*ss(?:\s+-\w+)?\s*$"),
     "safe",     "Show socket statistics"),
    (re.compile(r"^\s*nslookup\s+[\w\.\-]+\s*$"),
     "safe",     "DNS lookup"),
    (re.compile(r"^\s*dig\s+[\w\.\-]+(?:\s+\w+)?\s*$"),
     "safe",     "DNS query"),
    (re.compile(r"^\s*traceroute\s+[\w\.\-]+\s*$"),
     "safe",     "Trace network route to host"),
    (re.compile(r"^\s*curl\s+-[Iss]+\s+https?://[\w\.\-/]+\s*$"),
     "safe",     "HTTP request (info/headers only)"),
    # ── logs ──────────────────────────────────────────────────────────────────
    (re.compile(r"^\s*(?:sudo\s+)?journalctl(?:\s+(?:-[a-zA-Z]+|--\S+|[\w\.\-@]+))*\s*$"),
     "safe",     "View systemd journal logs"),
    (re.compile(r"^\s*(?:sudo\s+)?dmesg(?:\s+-[a-zA-Z]+)?\s*$"),
     "safe",     "View kernel ring buffer (boot messages)"),
    # ── reboot / shutdown (dangerous) ─────────────────────────────────────────
    (re.compile(r"^\s*sudo\s+reboot\s*$"),
     "dangerous", "Reboot the system now"),
    (re.compile(r"^\s*sudo\s+shutdown\s+-[hrP]\s+(?:now|\d+)\s*(?:.*)$"),
     "dangerous", "Shut down the system"),
    (re.compile(r"^\s*sudo\s+poweroff\s*$"),
     "dangerous", "Power off the system"),
]

# Commands whose first word is an interactive full-screen app — don't run
# inside TuxGenie's output stream, just inform the user.
_INTERACTIVE_CMDS = frozenset([
    "vim", "vi", "nano", "emacs", "less", "more", "man",
    "top", "htop", "btop", "iotop", "iftop", "nethogs", "atop", "glances",
    "mc", "ranger", "ncdu", "mutt", "irssi", "tmux", "screen",
    "nmtui", "cfdisk", "parted", "gdisk", "cgdisk",
    "ftp", "sftp", "telnet",
])

# Auto-inject -y for package managers that prompt interactively.
# User already confirmed at TuxGenie level — second prompt is redundant.
_NEEDS_YES_RE = re.compile(
    r"^\s*(?:sudo\s+)?apt(?:-get)?\s+(?:upgrade|dist-upgrade|full-upgrade|install|remove|purge|autoremove)\b"
    r"|^\s*sudo\s+snap\s+(?:install|remove|refresh)\b"
    r"|^\s*(?:sudo\s+)?flatpak\s+(?:install|remove|update)\b"
    r"|^\s*(?:sudo\s+)?dnf\s+(?:install|remove|upgrade|update)\b"
    r"|^\s*(?:sudo\s+)?yum\s+(?:install|remove|upgrade|update)\b"
    r"|^\s*(?:sudo\s+)?pacman\s+-S\b"
    r"|^\s*(?:sudo\s+)?zypper\s+(?:install|remove|update)\b"
)

# Shell builtins — no file in PATH but valid bash commands.
_SHELL_BUILTINS = frozenset([
    'history', 'alias', 'unalias', 'export', 'declare', 'typeset',
    'local', 'readonly', 'set', 'unset', 'shopt', 'let', 'eval',
    'source', '.', 'type', 'command', 'builtin', 'enable', 'help',
    'jobs', 'bg', 'fg', 'wait', 'disown', 'suspend', 'times',
    'dirs', 'pushd', 'popd', 'hash', 'ulimit', 'umask',
    'getopts', 'caller', 'fc', 'bind', 'compgen', 'complete',
    'cd', 'pwd', 'echo', 'printf', 'test', 'true', 'false',
    'kill', 'trap', 'read', 'mapfile', 'readarray',
    'exec', 'logout', 'newgrp', 'login',
    # bash keyword constructs (type -t returns 'keyword')
    'if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do',
    'done', 'case', 'esac', 'in', 'function', 'select', 'until',
    'return', 'break', 'continue', 'coproc', 'time', '[[', ']]',
])

# Comprehensive set of known Linux executables.
# Ensures detection works even when the tool is not installed on the
# current machine — covers every command in the user's workflow.
_KNOWN_LINUX_CMDS = frozenset([
    # File & directory
    'ls','ll','la','dir','vdir','cat','tac','nl','od','xxd','strings',
    'head','tail','less','more','most','bat','cp','mv','rm','mkdir',
    'rmdir','touch','ln','readlink','realpath','basename','dirname',
    'stat','file','tree','du','df','lsof','truncate','dd','sync',
    'shred','wipe','install','mktemp',
    # Search
    'grep','egrep','fgrep','rg','ag','ack','find','locate','updatedb',
    'which','whereis','type','whatis','apropos',
    # Text processing
    'awk','gawk','sed','cut','sort','uniq','wc','tr','diff','patch',
    'comm','join','paste','fold','fmt','pr','expand','unexpand',
    'split','csplit','tee','xargs','column','rev','nl','od','hexdump',
    # Archives & compression
    'tar','zip','unzip','gzip','gunzip','bzip2','bunzip2','xz','unxz',
    'zcat','zless','7z','7za','7zr','rar','unrar','ar','cpio',
    # Network
    'ping','ping6','traceroute','tracepath','mtr','ss','netstat',
    'ip','ifconfig','iwconfig','nmcli','nmtui','ethtool','brctl',
    'arp','arping','route','dig','nslookup','host','dnsdomainname',
    'whois','curl','wget','nc','ncat','nmap','tcpdump','wireshark',
    'tshark','iptraf','nethogs','iftop','bmon','vnstat','speedtest',
    'ssh','scp','rsync','sftp','ftp','smbclient','nfs','mount.nfs',
    # Firewall & security
    'ufw','iptables','ip6tables','firewall-cmd','nft','fail2ban-client',
    'openssl','gpg','gpg2','ssh-keygen','ssh-copy-id','ssh-agent',
    'certbot','chroot',
    # Process & system
    'ps','pstree','pgrep','pkill','killall','nice','renice','nohup',
    'watch','timeout','strace','ltrace','perf','ldd','nm','objdump',
    'uptime','top','htop','btop','atop','iotop','iftop','glances','nethogs',
    'vmstat','iostat','sar','mpstat','dstat','sysstat','nmon','bmon',
    'free','who','w','last','lastlog','faillog','ac','users',
    # Hardware & kernel
    'lshw','lsusb','lspci','lscpu','lsblk','lsmod','lsdev',
    'modprobe','modinfo','rmmod','insmod','depmod',
    'dmidecode','hwinfo','inxi','sensors','acpi','acpitool',
    'uname','arch','udevadm','dmesg',
    # Disk & storage
    'fdisk','gdisk','cfdisk','cgdisk','parted','gparted',
    'mkfs','mkfs.ext4','mkfs.xfs','mkfs.btrfs','mkfs.vfat',
    'fsck','e2fsck','xfs_repair','badblocks','tune2fs','resize2fs',
    'blkid','findmnt','mount','umount','mountpoint',
    'losetup','swapon','swapoff','mkswap',
    'hdparm','smartctl','nvme','lvm','pvdisplay','vgdisplay','lvdisplay',
    # Package managers
    'apt','apt-get','apt-cache','dpkg','dpkg-query',
    'snap','flatpak','appimage',
    'dnf','yum','rpm','rpm2cpio',
    'pacman','yay','paru','makepkg',
    'zypper','rpm','emerge','portage',
    'pip','pip3','pipx','conda','brew','nix','guix',
    # System management
    'systemctl','service','journalctl','timedatectl','localectl',
    'hostnamectl','loginctl','machinectl','systemd-analyze',
    'init','telinit','runlevel','chkconfig','update-rc.d',
    'crontab','at','atq','atrm','batch',
    'shutdown','reboot','poweroff','halt','suspend','hibernate',
    # User management
    'adduser','useradd','userdel','usermod','passwd','chpasswd',
    'groupadd','groupdel','groupmod','gpasswd','newgrp',
    'su','sudo','doas','visudo','vipw','vigr',
    'chage','chfn','chsh','whoami','who','id','groups','getent',
    # Permissions & ACL
    'chmod','chown','chgrp','chattr','lsattr','getfacl','setfacl',
    'umask','newuidmap','newgidmap',
    # System info
    'date','cal','hwclock','timedatectl','uptime','hostname',
    'uname','lsb_release','os-release','bc','expr','factor',
    'seq','shuf','yes','sleep','timeout',
    # Crypto & hashing
    'md5sum','sha1sum','sha256sum','sha512sum','sha224sum','sha384sum',
    'sum','cksum','b2sum','base64','base32',
    # Terminal & session
    'clear','reset','tput','stty','script','scriptreplay',
    'wall','write','mesg','talk','tty','w',
    'tmux','screen','byobu','zellij',
    # Scripting utilities
    'bash','sh','zsh','fish','dash','ksh','tcsh',
    'env','printenv','nohup','xargs','parallel','flock',
    'logger','notify-send','zenity','dialog','whiptail',
    # Editors (non-interactive listing)
    'ed','ex','grep',
    # Version control
    'git','svn','hg','cvs','bzr',
    # Containers & VMs
    'docker','docker-compose','podman','buildah','skopeo',
    'kubectl','helm','k3s','minikube','vagrant','virtualbox',
    # Monitoring
    'prometheus','grafana','netdata','zabbix',
    # Web servers
    'nginx','apache2','httpd','caddy','lighttpd',
    # Databases
    'mysql','mysqldump','mysqladmin','psql','pg_dump','sqlite3',
    'redis-cli','mongosh','mongo',
    # Misc
    'bc','dc','units','cal','ncal','banner','figlet','lolcat',
    'fortune','cowsay','sl','cmatrix',
    'ffmpeg','imagemagick','convert','identify','exiftool',
    'jq','yq','xmllint','csvtool',
    'make','cmake','gcc','g++','clang','python3','python','node','npm',
    'cargo','go','java','javac','mvn','gradle',
])

_NL_UPDATE_RE = re.compile(
    r"^\s*(?:please\s+)?"
    r"(?:"
        r"(?:update|upgrade)\s+"
        r"(?:my|this|the)?\s*"
        r"(?:pc|system|computer|laptop|machine|os|distro|"
        r"everything|all|all\s+packages|all\s+apps|all\s+software|"
        r"packages|apps|software)"
    r"|"
        r"system\s+(?:update|upgrade)"
    r"|"
        r"(?:check|run)\s+(?:for\s+)?(?:system\s+)?(?:update|updates|upgrade|upgrades)"
    r")"
    r"\s*[.!?]?\s*$",
    re.IGNORECASE,
)

# Dist-upgrade phrases: "upgrade to 26.04 LTS", "upgrade ubuntu to next LTS", etc.
# Anchored on 'upgrade'/'update' + 'to' + version-signal. The .{0,80}? in the middle
# lets extra words like "recently released" through while limiting blast radius.
# We require either .04 or an explicit "lts" / "next"/"latest" keyword so we don't
# accidentally catch "upgrade my app to v2.0" type sentences.
_NL_DIST_UPGRADE_RE = re.compile(
    r"^\s*(?:please\s+|i\s+(?:want|need|would\s+like)\s+(?:to\s+))?"
    r"(?:upgrade|update)\b.{0,80}?"
    r"to\s+(?:\w+\s+){0,3}(?:ubuntu\s+)?"
    r"(?:\d{2}\.04\b|\d{2}(?:\.\d{2})?\s*lts|next\s+(?:lts|ubuntu)|latest\s+(?:lts|ubuntu))"
    r"\s*[.!?]?\s*$",
    re.IGNORECASE,
)

def _system_update_cmd_for_phrase(text: str):
    """If the user's natural-language input means 'update my system', return the
    right command for this distro. Otherwise None."""
    if not _NL_UPDATE_RE.match(text or ""):
        return None
    if shutil.which("apt-get") or shutil.which("apt"):
        return "sudo apt-get update -q && sudo apt-get upgrade -y"
    if shutil.which("dnf"):
        return "sudo dnf upgrade -y"
    if shutil.which("pacman"):
        return "sudo pacman -Syu --noconfirm"
    if shutil.which("zypper"):
        return "sudo zypper --non-interactive update"
    if shutil.which("apk"):
        return "sudo apk update && sudo apk upgrade"
    if shutil.which("xbps-install"):
        return "sudo xbps-install -Su -y"
    return None


def _run_dist_upgrade():
    """Run an Ubuntu/Debian distribution upgrade via do-release-upgrade.
    Uses os.system() so the interactive TUI gets the real terminal TTY —
    subprocess.Popen with pipes would break the interactive installer."""
    if not shutil.which("do-release-upgrade"):
        err("'do-release-upgrade' is not available on this system.")
        info("This upgrade tool is Ubuntu/Debian-specific.")
        return

    print(f"\n  {BG_NAVY}{BWHITE}{BOLD}  🚀 Ubuntu Distribution Upgrade  {R}\n")

    # Quick disk-space pre-check
    free_gb = "?"
    try:
        res = subprocess.run(
            "df --output=avail -BG / | tail -1",
            shell=True, capture_output=True, text=True, timeout=5
        )
        raw = res.stdout.strip().rstrip("G")
        free_gb = raw if raw.isdigit() else "?"
    except Exception:
        pass

    gb = int(free_gb) if free_gb.isdigit() else 0
    gb_col = GREEN if gb >= 15 else (YELLOW if gb >= 10 else RED)

    warn("This replaces your entire OS and cannot be safely interrupted.")
    print(f"  {DIM}Free space on /:{R}  {gb_col}{BOLD}{free_gb} GB{R}  {DIM}(10 GB minimum recommended){R}")
    warn("Ensure you have AC power and a stable internet connection.")
    warn("The upgrade takes 1–2 hours — back up important files first.")
    print()

    try:
        ans = input(
            f"  {BOLD}Start the upgrade now?{R}  "
            f"{C('yes', GREEN, BOLD)} / {C('no', RED, BOLD)}: "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if ans not in ("y", "yes"):
        info("Upgrade cancelled — staying on current release.")
        return

    print(f"\n  {CYAN}Handing over to Ubuntu's upgrade tool…{R}")
    print(f"  {DIM}Follow the prompts in the upgrade TUI. TuxGenie resumes when it's done.{R}\n")

    # os.system() runs in the same terminal session — do-release-upgrade gets a real TTY
    # Plain do-release-upgrade only — never -d (would move LTS users to a dev release).
    rc = os.system("sudo do-release-upgrade")

    print()
    if rc == 0:
        ok(f"{BOLD}Upgrade complete!{R} Welcome to the new Ubuntu release.")
        info("A reboot is recommended: sudo reboot")
    else:
        warn(f"Upgrade exited with code {rc}. Some steps may need attention.")
        info("Check the log: /var/log/dist-upgrade/main.log")


def _looks_like_command(text):
    """
    Return (True, first_word) if text looks like a shell command.
    Detects: executables in PATH, absolute/relative paths, shell builtins.
    Returns (False, '') for natural language input.
    """
    stripped = text.strip()
    if not stripped:
        return False, ''
    try:
        parts = shlex.split(stripped)
    except ValueError:
        return False, ''
    if not parts:
        return False, ''

    first = parts[0]
    # Unwrap privilege escalation prefixes
    idx = 0
    while idx < len(parts) and parts[idx] in ('sudo', 'doas', 'pkexec'):
        idx += 1
    effective = parts[idx] if idx < len(parts) else first

    # Absolute path
    if effective.startswith('/'):
        return os.path.isfile(effective), effective

    # Relative path (./foo or ../foo)
    if effective.startswith('./') or effective.startswith('../'):
        return os.path.isfile(effective), effective

    # Common English words/verbs that share names with system utilities.
    # Must be checked BEFORE builtins so "set up a printer", "help me with git",
    # "install chrome browser" all go to AI instead of running as commands.
    _ENGLISH_WORDS = frozenset([
        'install', 'select', 'find', 'locate', 'link', 'sort', 'cut',
        'diff', 'touch', 'stat', 'head', 'tail', 'join', 'split',
        'test', 'time', 'wait', 'watch', 'run', 'start', 'stop',
        'open', 'close', 'show', 'list', 'check', 'fix', 'help',
        'make', 'build', 'clean', 'reset', 'update', 'upgrade',
        'set', 'get', 'put',
    ])
    if effective in _ENGLISH_WORDS:
        rest = stripped[len(effective):].strip()
        if rest:
            words_after = rest.split()
            # Flags (start with -) or paths (start with / ~ .) indicate a real command
            has_flag = any(w.startswith('-') for w in words_after)
            has_path = any(w.startswith('/') or w.startswith('~') or w.startswith('.') for w in words_after)
            if not has_flag and not has_path:
                return False, ''  # Plain English phrase → send to AI
        # Has flags/paths, or no rest → treat as command if it exists
        if effective in _SHELL_BUILTINS:
            return True, effective
        if shutil.which(effective):
            return True, effective
        return False, ''

    # Shell builtins (no file in PATH but valid bash commands)
    if effective in _SHELL_BUILTINS:
        return True, effective

    # Look up in PATH
    if shutil.which(effective):
        return True, effective

    # Known Linux command — even if not installed on this machine,
    # treat it as a command so it runs (and fails gracefully) rather
    # than being sent to AI. Covers tools on the user's machine that
    # may be absent in the dev environment.
    if effective in _KNOWN_LINUX_CMDS:
        return True, effective

    # Last resort: ask bash itself if it knows this command
    # Catches functions, aliases loaded in .bashrc, and edge cases
    try:
        probe = subprocess.run(
            ['bash', '-c', f'type -t {shlex.quote(effective)} 2>/dev/null'],
            capture_output=True, text=True, timeout=2)
        if probe.stdout.strip() in ('file', 'builtin', 'function', 'alias', 'keyword'):
            return True, effective
    except Exception:
        pass

    return False, ''

def _classify_cmd_risk(cmd, effective_word):
    """
    Classify the risk level of a command.
    Returns 'safe' | 'moderate' | 'dangerous'.
    """
    # Hard-coded danger patterns always win
    if is_dangerous(cmd):
        return 'dangerous'

    # Check _PASSTHROUGH list for known risk labels
    for pattern, risk, _ in _PASSTHROUGH:
        if pattern.match(cmd):
            return risk

    # Heuristics for unknown commands
    # sudo + destructive verbs → moderate
    if re.search(r'\bsudo\b', cmd):
        return 'moderate'

    # Pure read-only commands
    _READ_ONLY = frozenset([
        'ls', 'cat', 'less', 'more', 'head', 'tail', 'grep', 'find',
        'echo', 'printf', 'pwd', 'whoami', 'id', 'date', 'uptime',
        'df', 'du', 'free', 'ps', 'top', 'htop', 'uname', 'lscpu',
        'lsblk', 'lsusb', 'lspci', 'ip', 'ifconfig', 'ss', 'netstat',
        'ping', 'dig', 'nslookup', 'traceroute', 'curl', 'wget',
        'git', 'docker', 'systemctl', 'journalctl', 'dmesg',
        'which', 'whereis', 'type', 'file', 'stat', 'wc', 'sort',
        'uniq', 'cut', 'awk', 'sed', 'tr', 'diff', 'comm',
        'env', 'printenv', 'set', 'export', 'history',
    ])
    if effective_word in _READ_ONLY:
        return 'safe'

    return 'moderate'

def try_passthrough(user_input, session_log, backend=None, bctx=None):
    """
    If user_input looks like a shell command, run it directly without
    calling Claude. Works for ANY command in PATH — not just a fixed list.
    Returns True if handled, False to fall back to AI (natural language).
    On failure, offers AI explanation if backend is available.
    """
    cmd = user_input.strip()

    # Natural-language system update — run the right command for this distro
    # without burning AI tokens. "update this pc", "upgrade my system", etc.
    sys_update_cmd = _system_update_cmd_for_phrase(cmd)
    if sys_update_cmd:
        print(f"\n  {CYAN}⚡ {sys_update_cmd}{R}")
        sudo_pw = None
        if sys_update_cmd.lstrip().startswith("sudo "):
            try:
                sudo_pw = get_or_cache_sudo_password()
            except KeyboardInterrupt:
                return True
        # System updates can take 5+ minutes; allow a generous timeout
        rc, _stdout, _stderr = run_cmd_live(sys_update_cmd, sudo_password=sudo_pw, timeout=900)
        if rc == 0:
            ok("System is up to date.")
        else:
            err(f"Update failed (exit code {rc}). Try running it in a terminal.")
        return True

    # Distribution upgrade: "upgrade to 26.04 LTS" (NL) or direct do-release-upgrade command.
    # do-release-upgrade is a full-screen interactive TUI that needs a real TTY — we hand
    # control to it via os.system() rather than the subprocess-pipe path used by run_cmd_live().
    _is_direct_dru = bool(re.match(r"^\s*(?:sudo\s+)?do-release-upgrade\b", cmd, re.IGNORECASE))
    if _NL_DIST_UPGRADE_RE.match(cmd) or _is_direct_dru:
        _run_dist_upgrade()
        return True

    is_cmd, effective_word = _looks_like_command(cmd)

    if not is_cmd:
        return False  # Natural language — let AI handle it

    # Full-screen interactive apps can't run inside our output stream
    if effective_word in _INTERACTIVE_CMDS:
        print(f"\n  {YELLOW}'{effective_word}' is an interactive app — open a terminal to run it.{R}")
        return True

    risk   = _classify_cmd_risk(cmd, effective_word)
    danger = risk == 'dangerous'

    # Show what we're running (transparency), but never ask for permission
    print(f"\n  {CYAN}⚡ {cmd}{R}")

    # Dangerous commands (rm -rf /, fork bomb, disk wipe) — only these get blocked
    if danger:
        print(f"  {RED}{BOLD}⚠  Blocked: this command could permanently destroy data.{R}")
        print(f"  {DIM}Run it manually in a terminal if you are certain.{R}")
        return True

    # ── Special handling for shell builtins that need context ──────────────
    # 'history' — bash subprocess has no history; read ~/.bash_history directly
    if effective_word == 'history':
        hist_file = os.path.expanduser('~/.bash_history')
        try:
            lines = open(hist_file).read().splitlines()
            # Support: history, history 20, history -20
            args = cmd.split()[1:]
            n = 500
            if args:
                try: n = abs(int(args[-1]))
                except ValueError: pass
            shown = lines[-n:]
            start = max(1, len(lines) - n + 1)
            for idx2, l in enumerate(shown, start):
                print(f"  {DIM}{idx2:5d}  {l}{R}")
        except FileNotFoundError:
            print(f"  {DIM}(no bash history found){R}")
        ok("Done.")
        return True

    # 'cd' — cannot change TuxGenie's working dir but acknowledge it
    if effective_word == 'cd':
        parts2 = shlex.split(cmd)
        target = parts2[1] if len(parts2) > 1 else os.path.expanduser('~')
        target = os.path.expanduser(target)
        if os.path.isdir(target):
            os.chdir(target)
            ok(f"Directory: {os.getcwd()}")
        else:
            warn(f"cd: {target}: No such directory")
        return True

    # Get sudo password once (cached for the whole session)
    sudo_pw = None
    if re.match(r'^\s*sudo\b', cmd):
        try:
            sudo_pw = get_or_cache_sudo_password()
        except KeyboardInterrupt:
            warn("Cancelled."); return True

    # Inject -y for package managers so their internal prompt doesn't abort
    exec_cmd = cmd
    if _NEEDS_YES_RE.match(cmd) and '-y' not in cmd and '--yes' not in cmd:
        exec_cmd = re.sub(
            r'((?:sudo\s+)?(?:apt(?:-get)?|snap|flatpak|dnf|yum|pacman|zypper)\s+\S+)',
            r'\1 -y', cmd, count=1)

    # Shell builtins that aren't already handled above need bash -i to run
    if effective_word in _SHELL_BUILTINS and not shutil.which(effective_word):
        exec_cmd = f'bash -i -c {shlex.quote(exec_cmd)} 2>&1'

    # Long-running operations need a much bigger timeout than the default.
    # Match apt/dnf/yum/pacman/zypper with any flags between the binary and
    # the action verb (e.g. "sudo apt -y upgrade", "apt-get --yes install foo").
    _HEAVY_PKG_RE = re.compile(
        r'^\s*(?:sudo\s+)?'
        r'(?:apt(?:-get)?|dnf|yum|pacman|zypper|snap|flatpak)'
        r'(?:\s+-{1,2}[A-Za-z0-9-]+)*'
        r'\s+(?:upgrade|full-upgrade|dist-upgrade|install|reinstall|remove|autoremove|'
        r'purge|update|refresh|-S\b|-Syu\b|system-upgrade|do-release-upgrade)',
        re.IGNORECASE)
    _HEAVY_RELEASE_RE = re.compile(
        r'^\s*(?:sudo\s+)?do-release-upgrade\b', re.IGNORECASE)
    cmd_timeout = (3600 if (_HEAVY_PKG_RE.search(exec_cmd) or
                            _HEAVY_RELEASE_RE.search(exec_cmd)) else None)
    if cmd_timeout:
        print(f"  {YELLOW}⚠  This may take 10–60 minutes. Please wait…{R}")

    print(f"  {CYAN}▶ Running…{R}")
    rc, stdout, stderr = run_cmd_live(exec_cmd, sudo_password=sudo_pw,
                                      **({"timeout": cmd_timeout} if cmd_timeout else {}))

    if rc == 0:
        ok("Done.")
    else:
        # Track for the !! shortcut
        global _last_failed
        _last_failed = {"cmd": cmd, "rc": rc,
                        "stdout": stdout[:1500], "stderr": stderr[:600]}
        print(f"  {BRED}{BOLD}✘{R}  Exit {rc}")
        combined = (stderr or stdout).strip()
        if combined:
            for ln in combined.splitlines()[:5]:
                print(f"  {DIM}{ln}{R}")
        print(f"  {DIM}Type {BOLD}!!{R}{DIM} to ask AI to diagnose and fix this{R}")

    session_log.append({"command": cmd, "rc": rc, "source": "passthrough"})
    return True

def ask_ai(backend, system, messages, max_tokens=4096):
    return backend.ask(system, messages, max_tokens=max_tokens)

def clean_json(text):
    """Extract valid JSON from AI response, even if surrounded by extra text."""
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # If it parses directly, great
    try:
        json.loads(text)
        return text
    except (json.JSONDecodeError, ValueError):
        pass

    # Find the outermost { ... } block (the actual JSON object)
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]

    # Fallback: return from first { to end
    return text[start:]

def run_cmd(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)

# ── Community feedback helpers ───────────────────────────────────────────────

_GITHUB_REPO = "ramchandragada/tuxgenie"

def _open_github_issue(title, body, labels="bug"):
    """Open browser with a pre-filled GitHub issue — no token, no server."""
    import urllib.parse
    url = ("https://github.com/" + _GITHUB_REPO + "/issues/new?"
           + urllib.parse.urlencode({"title": title, "body": body, "labels": labels}))
    subprocess.Popen(["xdg-open", url],
                     start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _sanitize_tb(tb_text):
    """Strip personal info from a traceback before showing/sending it."""
    home = os.path.expanduser("~")
    tb_text = tb_text.replace(home, "~")
    tb_text = re.sub(r'sk-ant-[A-Za-z0-9_\-]{10,}', '[API_KEY_REDACTED]', tb_text)
    # Redact cached sudo password if it appears in any repr/locals dump
    if _SESSION_SUDO_PW:
        tb_text = tb_text.replace(_SESSION_SUDO_PW, '[SUDO_PW_REDACTED]')
    return tb_text

def _ask_rating():
    """Ask a quick 1-5 rating after a successful fix; offer to report if low."""
    print(f"\n  {CYAN}Quick question — how helpful was TuxGenie today?{R}")
    print(f"  {C('5',YELLOW,BOLD)} = Amazing  {C('3',YELLOW)} = OK  {C('1',DIM)} = Didn't help")
    try:
        r = input(f"  Rate 1–5 (or Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not r or r not in ("1","2","3","4","5"):
        return
    if r in ("4","5"):
        print(f"  {GREEN}{BOLD}Thank you! That means a lot. ⭐{R}")
        print(f"  {DIM}Share TuxGenie → {BLUE}{BOLD}www.tuxgenie.com{R}{DIM} · https://github.com/{_GITHUB_REPO}{R}")
    else:
        print(f"  {YELLOW}Sorry it wasn't more helpful — let's make it better.{R}")
        try:
            fb = input(f"  What went wrong? (optional, Enter to skip):\n  > ").strip()
        except (EOFError, KeyboardInterrupt):
            fb = ""
        if fb:
            try:
                ans = input(f"  Open GitHub to report this? [{C('y',GREEN,BOLD)}/{C('n',DIM)}]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                ans = "n"
            if ans in ("y","yes"):
                _open_github_issue(
                    f"[Feedback] Fix didn't work: {fb[:60]}",
                    f"## Feedback — Fix Didn't Help\n\n**Rating:** {r}/5\n\n**What went wrong:**\n{fb}\n\n**Version:** {__version__}\n",
                    labels="feedback"
                )
                ok("Opening GitHub — review and click Submit Issue.")

def report_crash(exc_type, exc_val, exc_tb, feature="unknown"):
    """Offer to report an unexpected crash as a GitHub issue."""
    tb_text = _sanitize_tb("".join(traceback.format_exception(exc_type, exc_val, exc_tb)))
    err_summary = f"{exc_type.__name__}: {str(exc_val)[:120]}"

    print(f"\n{BG_RED}{BOLD}  ⚠  TuxGenie hit an unexpected error  {R}")
    print(f"\n  {RED}{err_summary}{R}")
    print(f"\n  {YELLOW}Report this so we can fix it?{R}")
    print(f"  {DIM}Only this info will be sent — nothing personal:{R}")
    print(f"  {DIM}  · Error: {err_summary}{R}")
    print(f"  {DIM}  · Feature: {feature}{R}")
    print(f"  {DIM}  · Version: {__version__}{R}")
    print(f"  {DIM}  · OS: (your distro + kernel, from system info){R}")
    try:
        ans = input(f"\n  Open GitHub to report? [{C('y',GREEN,BOLD)} = yes / {C('n',DIM)} = no]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"
    if ans in ("y","yes"):
        body = (f"## Bug Report (auto-generated)\n\n"
                f"**Version:** {__version__}\n**Feature:** {feature}\n\n"
                f"## Error\n```\n{tb_text[:3000]}\n```\n\n"
                f"## Steps to reproduce\n(What were you doing when this happened?)\n")
        _open_github_issue(f"[Bug] {err_summary[:80]}", body, labels="bug")
        ok("Opening GitHub — review and click Submit Issue. Thank you!")
    else:
        info(f"Report manually: https://github.com/{_GITHUB_REPO}/issues")

def feat_feedback(backend=None, bctx=None, slog=None):
    """Let user submit a feature request directly from the app."""
    hdr("Submit Feature Request — Shape the future of TuxGenie")
    print(f"\n  {DIM}Your ideas help make TuxGenie better for everyone worldwide.{R}")
    print(f"  {DIM}This opens GitHub in your browser with your idea pre-filled.{R}")
    print(f"  {DIM}(You'll need a free GitHub account to submit — it takes 30 seconds){R}\n")
    try:
        idea = input(f"  {BOLD}What feature would you like?{R}\n"
                     f"  {C('(e.g. VPN setup, gaming guide, auto backup)',DIM)}\n  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not idea:
        return
    try:
        detail = input(f"\n  {DIM}Any more detail? (optional, Enter to skip):{R}\n  > ").strip()
    except (EOFError, KeyboardInterrupt):
        detail = ""
    body = (f"## Feature Request\n\n**What would you like TuxGenie to do?**\n{idea}\n\n"
            + (f"**More detail:**\n{detail}\n\n" if detail else "")
            + f"**TuxGenie Version:** {__version__}\n\n---\n*Submitted from within TuxGenie*\n")
    print(f"\n  {CYAN}Opening GitHub in your browser…{R}")
    _open_github_issue(f"[Feature Request] {idea[:70]}", body, labels="enhancement")
    ok("Review your request and click 'Submit new issue' — thank you! 🐧")

def feat_share_fix(backend=None, bctx=None, slog=None):
    """Let the user contribute their most recent verified fix back to the
    community knowledge base. The maintainer reviews each submission and
    appends accepted ones to community_fixes.json, which ships in every .deb."""
    hdr("Share a Fix — make TuxGenie smarter for everyone")
    data = _mem_load()
    solved = data.get("solved", [])
    if not solved:
        info("No saved fixes on this machine yet. Solve a problem first, then come back.")
        return
    # Show the most recent 5; user picks one (default = latest).
    recent = solved[-5:][::-1]
    print(f"\n  {DIM}Your most recent saved fixes:{R}\n")
    for i, e in enumerate(recent, 1):
        prob = e.get("problem", "")[:70]
        ts   = e.get("ts", "")
        print(f"  {C(str(i), CYAN, BOLD)}. [{ts}] {prob}")
    try:
        pick = _safe_input(f"\n  Which one to share? [1-{len(recent)}, Enter for 1] ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        return
    try:
        idx = int(pick) - 1
        chosen = recent[idx]
    except (ValueError, IndexError):
        warn("Invalid choice."); return

    print(f"\n  {BOLD}This is what will be shared (review before submitting):{R}\n")
    print(f"  {DIM}Problem:{R}     {chosen.get('problem','')}")
    if chosen.get("failing_cmd"):
        print(f"  {DIM}Failing cmd:{R} {chosen['failing_cmd']}")
    if chosen.get("error"):
        print(f"  {DIM}Error:{R}       {chosen['error'][:200]}")
    print(f"  {DIM}Fix steps:{R}")
    for c in chosen.get("steps", []):
        print(f"    $ {c}")
    print(f"\n  {YELLOW}Nothing is sent until YOU click 'Submit' on the GitHub page.{R}")
    print(f"  {DIM}A maintainer reviews each submission before it ships in the next release.{R}")
    try:
        ans = _safe_input(f"\n  Open GitHub to submit this fix? [{C('y',GREEN,BOLD)}/{C('n',DIM)}] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if ans not in ("y", "yes"):
        info("Cancelled — nothing was shared.")
        return

    body_lines = [
        "## Community Fix Submission",
        "",
        "*Submitted from inside TuxGenie via `share-fix`. A maintainer will review "
        "this and (if accepted) bundle it into `community_fixes.json` in the next release.*",
        "",
        f"**Problem:** {chosen.get('problem','')}",
    ]
    if chosen.get("failing_cmd"):
        body_lines += ["", f"**Failing command:** `{chosen['failing_cmd']}`"]
    if chosen.get("error"):
        body_lines += ["", "**Error excerpt:**", "```", chosen["error"][:600], "```"]
    body_lines += ["", "**Working fix:**", "```bash"]
    body_lines += chosen.get("steps", [])
    body_lines += ["```", "", f"**TuxGenie version:** {__version__}",
                   "",
                   "### Proposed JSON entry",
                   "```json",
                   json.dumps({
                       "problem": chosen.get("problem", ""),
                       "failing_cmd": chosen.get("failing_cmd", ""),
                       "error": chosen.get("error", ""),
                       "steps": chosen.get("steps", []),
                   }, indent=2),
                   "```"]
    _open_github_issue(
        f"[Community Fix] {chosen.get('problem','')[:60]}",
        "\n".join(body_lines),
        labels="community-fix",
    )
    ok("Opening GitHub — review and click 'Submit new issue'. Thank you for teaching the Genie! 🧞")

# GUI launcher commands — these open windows and must not flood the terminal
_GUI_LAUNCHERS = (
    "xdg-open", "gnome-open", "gio open",
    "firefox", "google-chrome", "chromium", "chromium-browser",
    "nautilus", "thunar", "nemo", "dolphin", "pcmanfm",
    "gedit", "kate", "mousepad", "geany", "code",
    "gnome-terminal", "xterm", "konsole",
)

def is_gui_cmd(cmd):
    s = cmd.strip()
    return any(s == g or s.startswith(g + " ") for g in _GUI_LAUNCHERS)

def get_sudo_password():
    """Prompt for sudo password, echoing * for each character typed."""
    print(f"\n  {C('🔑 Enter sudo (admin) password:', YELLOW, BOLD)}", end=" ", flush=True)
    password = []
    if _HAS_TERMIOS:
        try:
            fd = sys.stdin.fileno()
            old_attrs = termios.tcgetattr(fd)
            try:
                _tty.setraw(fd)
                while True:
                    ch = sys.stdin.read(1)
                    if ch in ('\r', '\n'):
                        break
                    elif ch in ('\x7f', '\x08'):   # backspace
                        if password:
                            password.pop()
                            print('\b \b', end='', flush=True)
                    elif ch == '\x03':             # Ctrl-C
                        raise KeyboardInterrupt
                    else:
                        password.append(ch)
                        print('*', end='', flush=True)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
        except KeyboardInterrupt:
            print()
            raise
        except Exception:
            import getpass
            password = list(getpass.getpass(""))
    else:
        import getpass
        password = list(getpass.getpass(""))
    print()
    return ''.join(password)

# Session-level sudo password cache — ask once, reuse for all steps
_SESSION_SUDO_PW = None

def get_or_cache_sudo_password():
    """Return verified sudo password, prompting only once per session."""
    global _SESSION_SUDO_PW
    if _SESSION_SUDO_PW is not None:
        # Refresh the sudo timestamp silently so it doesn't expire mid-session
        run_cmd_live("sudo -S -v", sudo_password=_SESSION_SUDO_PW, timeout=10)
        return _SESSION_SUDO_PW
    for _attempt in range(3):
        try:
            pw = get_sudo_password()
        except KeyboardInterrupt:
            raise
        rc, _, err_txt = run_cmd_live("sudo -S -v", sudo_password=pw, timeout=10)
        if rc == 0:
            _SESSION_SUDO_PW = pw
            return _SESSION_SUDO_PW
        err_low = err_txt.lower()
        if "incorrect" in err_low or "sorry" in err_low or rc == 1:
            if _attempt < 2:
                print(f"\n  {C('✗ Wrong password — please try again.', RED, BOLD)}")
            else:
                warn("Password incorrect 3 times. Cannot proceed with this step.")
                raise KeyboardInterrupt
        else:
            # Some other non-auth error — accept and proceed
            _SESSION_SUDO_PW = pw
            return _SESSION_SUDO_PW
    raise KeyboardInterrupt

def _restore_terminal():
    """Restore sane tty settings after a subprocess may have altered them."""
    try:
        subprocess.run(['stty', 'sane'], capture_output=True)
    except Exception:
        pass


_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_APT_PCT_RE = re.compile(r'Progress:\s*\[\s*(\d+)%\s*\]')


class _LiveProgress:
    """One-line live status: spinner + elapsed time + parsed apt % + last action.
    Sits below streaming output and refreshes ~3x/sec so the user never wonders
    if a long install has hung. Output lines slide in above it.
    Falls back to a no-op when stdout is not a tty (CI, redirected logs)."""

    def __init__(self):
        self.start = time.time()
        self.lock = threading.Lock()
        self.done = threading.Event()
        self.last_action = ""
        self.apt_pct = None
        self._frames = 0
        self.visible = False
        self.is_tty = bool(getattr(sys.stdout, "isatty", lambda: False)())

    def _format(self):
        elapsed = int(time.time() - self.start)
        t = f"{elapsed}s" if elapsed < 60 else f"{elapsed//60}m{elapsed%60:02d}s"
        spin = _SPINNER_FRAMES[self._frames % len(_SPINNER_FRAMES)]
        self._frames += 1
        parts = [f"{spin} {t}"]
        if self.apt_pct is not None:
            parts.append(f"{self.apt_pct}%")
        if self.last_action:
            parts.append(self.last_action[:60])
        return f"  {DIM}{' · '.join(parts)}{R}"

    def _draw(self):
        if not self.is_tty:
            return
        sys.stdout.write("\r\x1b[K" + self._format())
        sys.stdout.flush()
        self.visible = True

    def _erase(self):
        if not self.is_tty:
            return
        if self.visible:
            sys.stdout.write("\r\x1b[K")
            sys.stdout.flush()
            self.visible = False

    def loop(self):
        """Run in a daemon thread until .done is set."""
        while not self.done.wait(0.3):
            with self.lock:
                self._draw()
        with self.lock:
            self._erase()

    def print_line(self, text):
        """Print a normal output line, sliding it in above the live status."""
        with self.lock:
            self._erase()
            print(text, flush=True)

    def feed(self, raw_line):
        """Update progress hints from a raw output line."""
        m = _APT_PCT_RE.search(raw_line)
        if m:
            try:
                self.apt_pct = int(m.group(1))
            except ValueError:
                pass
            return
        l = raw_line.strip()
        if l and len(l) > 3:
            self.last_action = l[:70]


def run_cmd_live(cmd, sudo_password=None, timeout=120):
    """Run a command and stream its output line-by-line in real time.
    Returns (returncode, stdout_str, stderr_str)."""
    actual_cmd = cmd
    if sudo_password is not None:
        # sudo -S reads the password from stdin (one line)
        actual_cmd = re.sub(r'^(\s*sudo\s+)', r'\1-S ', actual_cmd, count=1)

    stdout_lines = []
    stderr_lines = []

    # Noise patterns to suppress from terminal output (still kept in buf for AI)
    _NOISE = (
        "WARNING: apt does not have a stable CLI interface",
        "VMware: No 3D",
        "vaInitialize failed",
        "TensorFlow Lite XNNPACK",
        "ContextResult::kTransientFailure",
        "Created TensorFlow",
        "Fontconfig error",
        "GpuControl.CreateCommandBuffer",
        "shared_memory_switch",
        "DEPRECATED_ENDPOINT",
        "gpu/vaapi",
        "gpu/ipc",
        "ERROR:media/",
        "ERROR:gpu/",
        "ERROR:google_apis/",
        "ERROR:base/",
    )

    # Escape sequences that change terminal state — strip before printing
    # (e.g. enter/exit alternate screen, show/hide cursor, set title)
    _TERM_STATE_ESC = re.compile(
        r'\x1b\[\?[0-9;]*[hl]'   # mode set/reset: ?1049h (alt screen), ?25l (cursor)
        r'|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)'  # OSC sequences (set title, etc.)
        r'|\x1b[()][A-B0-2]'     # charset designations
    )

    def _safe_line(line):
        """Strip terminal-state escape sequences from a line of command output."""
        return _TERM_STATE_ESC.sub('', line)

    progress = _LiveProgress()

    def _reader(stream, buf, color):
        pending = b''
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                pending += chunk
                # Split on both \n and \r so apt's carriage-return progress lines print
                while True:
                    for sep in (b'\n', b'\r'):
                        idx = pending.find(sep)
                        if idx != -1:
                            raw = pending[:idx]
                            pending = pending[idx + 1:]
                            break
                    else:
                        break
                    line = raw.decode('utf-8', errors='replace').rstrip('\r\n')
                    buf.append(line)
                    # Suppress sudo password prompts that sudo -S emits to stderr
                    if sudo_password is not None and (
                        '[sudo]' in line or
                        'password for' in line.lower() or
                        'sorry, try again' in line.lower() or
                        'sudo:' in line.lower()
                    ):
                        continue
                    # Suppress known noise / internal app errors
                    if any(n in line for n in _NOISE):
                        continue
                    safe = _safe_line(line)
                    if safe.strip():
                        progress.feed(safe)
                        progress.print_line(f"  {color}{safe}{R}")
        except Exception:
            pass
        finally:
            try:
                # Flush any trailing partial line that never got terminated
                if pending:
                    line = pending.decode('utf-8', errors='replace').rstrip('\r\n')
                    if line:
                        buf.append(line)
                        safe = _safe_line(line)
                        if safe.strip() and not any(n in line for n in _NOISE):
                            progress.print_line(f"  {color}{safe}{R}")
            except Exception:
                pass
            stream.close()

    try:
        proc_env = os.environ.copy()
        # Only apt/dpkg need plain-text mode — setting these globally has no
        # effect elsewhere but we keep them scoped to be tidy.
        if re.search(r'\b(?:apt|apt-get|dpkg|aptitude|do-release-upgrade)\b', actual_cmd):
            proc_env.update({
                'DEBIAN_FRONTEND': 'noninteractive',
                'APT_LISTCHANGES_FRONTEND': 'none',
                'DPKG_COLORS': 'never',
            })
        proc = subprocess.Popen(
            actual_cmd, shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=proc_env,
            bufsize=0,
        )
        if sudo_password is not None:
            try:
                proc.stdin.write((sudo_password + '\n').encode())
                proc.stdin.flush()
            except Exception:
                pass
        try:
            proc.stdin.close()
        except Exception:
            pass

        t_out = threading.Thread(target=_reader, args=(proc.stdout, stdout_lines, DIM),        daemon=True)
        t_err = threading.Thread(target=_reader, args=(proc.stderr, stderr_lines, YELLOW+DIM), daemon=True)
        t_prog = threading.Thread(target=progress.loop, daemon=True)
        t_out.start(); t_err.start(); t_prog.start()

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        except KeyboardInterrupt:
            # Ctrl+C — kill the child process but don't exit TuxGenie
            proc.kill()
            proc.wait()
            progress.done.set(); t_prog.join(1)
            t_out.join(2); t_err.join(2)
            _restore_terminal()
            print(f"\n  {YELLOW}Command cancelled.{R}")
            return -1, '\n'.join(stdout_lines), 'Cancelled by user'
        progress.done.set(); t_prog.join(1)
        t_out.join(5); t_err.join(5)

        return proc.returncode, '\n'.join(stdout_lines), '\n'.join(stderr_lines)
    except KeyboardInterrupt:
        progress.done.set()
        _restore_terminal()
        print(f"\n  {YELLOW}Cancelled.{R}")
        return -1, '', 'Cancelled by user'
    except Exception as e:
        progress.done.set()
        return -1, '', str(e)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — CORE FIX ENGINE  (shared by all features)
# ═══════════════════════════════════════════════════════════════════════════════
def _prune_messages(messages, max_keep=6):
    """Keep conversation history bounded to save tokens.
    Keeps: first user message (the original task) + last max_keep messages."""
    if len(messages) <= max_keep + 1:
        return messages
    # Always keep the first message (original task description)
    return [messages[0]] + messages[-(max_keep):]

def _synthesize_findings(backend, question: str, step_outputs: list):
    """
    After steps complete, call Haiku with the actual outputs to generate
    either a direct answer (info tasks) or a Warp-style action summary.
    """
    parts = []
    for s in step_outputs:
        cmd = s.get("command", "")
        out = (s.get("stdout", "") or "").strip()
        if cmd and out:
            parts.append(f"$ {cmd}\n{out[:600]}")
        elif cmd:
            parts.append(f"$ {cmd}\n(ran successfully, no output)")
    if not parts:
        return
    data_block = "\n\n".join(parts)

    # Detect if this was an ACTION task (modifying system) vs INFO task (reading)
    all_cmds = " ".join(s.get("command", "") for s in step_outputs)
    _action_markers = ("apt ", "apt-get", "systemctl ", "sysctl -w", "dpkg ", "snap ",
                       "pip ", "tee /", "sed -i", "update-", " install", " remove",
                       "chmod ", "chown ", "rm ", "mv ", "cp /", "echo >", ">> /")
    is_action = any(m in all_cmds for m in _action_markers)

    if is_action:
        synth_system = (
            "You are TuxGenie. Commands were just run on the user's Linux system. "
            "Write a clear completion summary in plain text using these EXACT section labels "
            "(one per line, keep each section to 2-4 bullet points max):\n\n"
            "✓ Changes made:\n"
            "  • [what changed — include before/after values where the outputs show them]\n\n"
            "⚡ Still to watch:\n"
            "  • [what is still limited, slow, or could be improved based on the data]\n\n"
            "→ Next steps:\n"
            "  • [2-3 concrete things the user should do now]\n\n"
            "Be specific — use real numbers from the outputs. No JSON. No markdown headers. "
            "Use ONLY these bullet characters: • ✓ ⚡ → — never use ❯. "
            "Under 12 lines total."
        )
        synth_content = (
            f"Task performed: {question}\n\n"
            f"Commands run and their outputs:\n{data_block}\n\n"
            "Write the completion summary."
        )
        header = f"\n  {GREEN}{BOLD}What happened:{R}\n"
    else:
        synth_system = (
            "You are TuxGenie. The user asked a question and commands were run to gather data. "
            "Give a direct, specific plain-English answer using ONLY the real data from the outputs. "
            "Be concrete — use the actual numbers and values. "
            "Do NOT say 'run these commands', 'look it up online', or give generic advice. "
            "3-6 sentences. No JSON. No markdown. Never use the ❯ character."
        )
        synth_content = (
            f"User's question: {question}\n\n"
            f"Data gathered from the system:\n{data_block}\n\n"
            "Answer the user's question directly using this data."
        )
        header = f"\n  {GREEN}{BOLD}Here's what we found:{R}\n"

    try:
        answer = ask_ai(backend, synth_system,
                        [{"role": "user", "content": synth_content}], max_tokens=500)
        # Sanitize AI output: replace ❯ (TuxGenie's own prompt char) with →
        # so the model can't accidentally inject our input prompt into displayed text
        answer = answer.strip().replace('❯', '→')
        if answer:
            print(header)
            for line in answer.splitlines():
                line = line.strip()
                if not line:
                    print()
                    continue
                if len(line) > 72:
                    for wrapped in textwrap.wrap(line, width=72):
                        print(f"  {wrapped}")
                else:
                    print(f"  {line}")
            print()
    except Exception:
        pass


def fix_engine(backend, system, messages, session_log, max_rounds=10):
    """
    Runs the AI→display→execute→iterate loop.
    backend: AnthropicBackend instance
    session_log: list, commands are appended for rollback.
    """
    if not backend:
        err("No AI backend configured. Run settings to set up your API key.")
        return

    # ── Smart model routing: start with Haiku, escalate on failure ──
    user_text = messages[0].get("content", "") if messages else ""

    # A bare "q"/"back"/"cancel" is not a task — return to the menu, no AI call.
    if _is_back(user_text):
        return

    # ── Genie Memory: try a saved fix first (zero API cost when it works) ──
    recalled = _mem_recall(user_text)
    if recalled and _mem_apply_recalled(recalled):
        return

    backend.select_model_for_task(user_text, round_num=1)
    print(f"\n  {CYAN}{BOLD}⚡ AI: {backend.label()}{R}")

    approve_state = {"all": False}   # session-wide "yes to all" toggle

    for rnd in range(1, max_rounds+1):
        hdr(f"Round {rnd}/{max_rounds}")

        # Escalate model on retry rounds (Haiku failed → Sonnet)
        if rnd > 1:
            prev_m = backend.model
            backend.select_model_for_task(user_text, round_num=rnd)
            if backend.model != prev_m:
                print(f"  {YELLOW}↑ Escalating to {backend.model} for better results{R}")

        # Prune old messages to prevent token bloat
        messages = _prune_messages(messages)

        # Dynamic max_tokens based on model
        out_tokens = 3072 if "haiku" in backend.model else 4096

        try:
            raw = ask_ai(backend, system, messages, max_tokens=out_tokens)
        except RuntimeError as e:
            msg = str(e)
            if "401" in msg or "403" in msg or "invalid_api_key" in msg.lower():
                err("Auth failed. Delete ~/.config/tuxgenie/config.json to reset backend.")
            elif "429" in msg:
                warn("Rate limited — please wait a moment and try again.")
            else:
                err(f"API error: {msg[:200]}")
            return
        except (urllib.error.URLError, OSError) as e:
            eno = getattr(e, "errno", None)
            if eno == 11:
                err("Network busy (EAGAIN). Retried 4 times but still failed. Check your internet connection or try again in a moment.")
            elif eno in (111, 61):
                err("Connection refused. Check your internet connection.")
            else:
                err(f"Network error: {e}  — Check your connection or backend.")
            return
        except Exception as e:
            err(f"Unexpected error: {e}"); return

        try:
            plan = json.loads(clean_json(raw))
        except json.JSONDecodeError as e:
            err(f"Could not parse response: {e}")
            print(C(raw[:400], DIM)); return

        analysis = plan.get("analysis","")
        if analysis and not backend.expert_mode:
            print(f"\n{BOLD}Analysis:{R} {analysis}")

        if plan.get("resolved", False):
            ok("Already resolved! Nothing to do.")
            sc = plan.get("success_check","")
            if sc: info(f"Verify: {C(sc, CYAN)}")
            return

        steps = plan.get("steps",[])
        if not steps:
            warn("No steps returned — issue may already be resolved.")
            return

        step_outputs = []
        aborted      = False

        for i, step in enumerate(steps, 1):
            output_has_errors = False
            risk    = step.get("risk", "safe").lower()
            cmd     = step.get("command", "").strip()
            desc    = step.get("description", "")
            meaning = step.get("what_this_means", "")

            if is_dangerous(cmd):
                risk = "dangerous"

            pct = int(i / len(steps) * 100)
            bar = C("█" * int(pct/5), CYAN) + C("░" * (20 - int(pct/5)), DIM)
            rb  = {"safe":     C(" SAFE ",    GREEN,  BOLD),
                   "moderate": C(" WORKING ", CYAN,   BOLD),
                   "dangerous":C(" RISKY ",   RED,    BOLD),
                  }.get(risk, C(f" {risk.upper()} ", DIM))

            if backend.expert_mode:
                if cmd:
                    print(f"\n  {DIM}[{i}/{len(steps)}]{R}  {DIM}$ {cmd}{R}")
            else:
                print(f"\n{'─'*60}")
                print(f"  {BOLD}Step {i}/{len(steps)}{R}  {rb}  {bar} {CYAN}{BOLD}{pct}%{R}")
                print(f"  {desc}")
                if meaning:
                    print(f"  {DIM}→ {meaning}{R}")
                if cmd:
                    print(f"  {DIM}$ {cmd}{R}")

            if not cmd:
                info("(informational — nothing to run)"); continue

            # Block only genuinely destructive commands (DANGER_RE matches)
            if risk == "dangerous":
                print(f"\n  {BG_RED}{BOLD}  ⚠  This command could permanently destroy data.  {R}")
                print(f"  {RED}Skipping for safety. Run manually if you are certain.{R}")
                step_outputs.append({"step": i, "command": cmd, "skipped": True})
                continue

            # Ask before running anything that changes the system (read-only
            # steps run automatically). Power users can set auto_approve to skip.
            _needs_root = cmd.strip().startswith("sudo") or step.get("requires_root", False)
            try:
                if not _approval_gate(cmd, _needs_root, backend, approve_state):
                    info("Skipped.")
                    step_outputs.append({"step": i, "command": cmd, "skipped": True})
                    continue
            except _AbortSession:
                warn("Stopped."); aborted = True
                break

            # Get sudo password once — cached for the whole session
            sudo_pw = None
            if cmd.strip().startswith("sudo"):
                try:
                    sudo_pw = get_or_cache_sudo_password()
                except KeyboardInterrupt:
                    warn("Stopped."); aborted = True
                if aborted:
                    break

            expects_output = False
            empty_output = False
            downloaded_html = False
            output_has_errors = False
            exit1_is_ok = False

            if is_gui_cmd(cmd):
                # Launch GUI apps silently in background — never flood the terminal
                print(f"\n  {CYAN}▶ Launching app…{R}")
                subprocess.Popen(
                    cmd + " >/dev/null 2>&1",
                    shell=True,
                    start_new_session=True,
                )
                time.sleep(0.8)
                rc, stdout, stderr = 0, "App launched in background.", ""
                ok("App launched! Check your taskbar or desktop.")
            else:
                print(f"\n  {CYAN}▶ Running…{R}")
                rc, stdout, stderr = run_cmd_live(cmd, sudo_password=sudo_pw)

                # ── Smart success detection ──
                # Check output for failure patterns even when rc == 0.
                # Patterns are anchored to start-of-line (or after whitespace) so
                # they don't fire on package descriptions like "firefox/jammy ..."
                # or on legitimate uses of "is not installed" inside a verification.
                combined_out = (stdout + "\n" + stderr)
                _FAIL_RES = [
                    re.compile(r'(?im)^\s*(?:error|fatal):'),
                    re.compile(r'(?im)^\s*E:\s'),
                    re.compile(r'(?im)^\s*dpkg:\s+error'),
                    re.compile(r'(?im)^\s*\S+:\s+command not found'),
                    re.compile(r'(?im)^\s*permission denied'),
                    re.compile(r'(?im)^\s*unable to locate package'),
                    re.compile(r'(?im)^\s*could not resolve host'),
                    re.compile(r'(?im)\b404 not found\b'),
                    re.compile(r'(?im)\b403 forbidden\b'),
                    re.compile(r'(?im)connection refused'),
                    re.compile(r'(?im)^\s*no such file or directory'),
                    re.compile(r'(?im)^\s*failed to fetch'),
                ]
                # ── Don't error-check echo payloads in fallback commands ──
                # e.g. `which foo || echo 'foo is not installed'` — the echo is
                # intentional confirmation output, not an actual error.
                # Also: dpkg -s / systemctl is-active routinely print "not installed"
                # / "inactive" as legitimate result strings, not failures.
                _result_string_cmds = ("dpkg -s", "dpkg-query", "systemctl is-active",
                                       "systemctl is-enabled", "snap info")
                if "|| echo" in cmd and rc == 0:
                    output_has_errors = False
                elif any(cmd.strip().startswith(c) for c in _result_string_cmds) and rc in (0, 1, 3):
                    output_has_errors = False
                else:
                    output_has_errors = any(r.search(combined_out) for r in _FAIL_RES)

                # ── Empty output detection ──
                # Commands that produce no output when output was expected
                _EXPECTS_OUTPUT = [
                    "grep", "curl", "wget", "apt-cache search",
                    "apt-cache show", "snap info", "flatpak search",
                    "which", "find", "locate", "dpkg -s", "dpkg -l",
                    "cat ", "head ", "tail ",
                ]
                expects_output = any(cmd.strip().startswith(k) or
                                     (" | " in cmd and k in cmd)
                                     for k in _EXPECTS_OUTPUT)
                empty_output = not stdout.strip() and not stderr.strip()

                # ── Downloaded file type check ──
                # Detect if a downloaded file is actually HTML (not a real package)
                downloaded_html = False
                if ("curl" in cmd or "wget" in cmd) and rc == 0 and stdout.strip():
                    out_lower = stdout.strip().lower()
                    if (out_lower.startswith("<!doctype") or
                        out_lower.startswith("<html") or
                        "<head>" in out_lower[:500]):
                        downloaded_html = True

                # ── Exit-1 from probe/search commands is "nothing found", not an error ──
                _PROBE_CMDS = ("grep", "find ", "which ", "type ", "snap list", "flatpak list",
                               "dpkg -l", "dpkg-query", "apt-cache search", "apt-cache show",
                               "snap info", "flatpak search", "locate ")
                is_probe = any(cmd.strip().startswith(k) or k in cmd
                               for k in _PROBE_CMDS)
                exit1_is_ok = is_probe and rc == 1

                if rc == 0 and not output_has_errors and not (expects_output and empty_output) and not downloaded_html:
                    if not backend.expert_mode:
                        ok("This step completed successfully.")
                elif exit1_is_ok:
                    # grep/which/type exit 1 = "not found" — that's a valid result
                    if not backend.expert_mode:
                        ok("Nothing found (this is the expected result).")
                elif downloaded_html:
                    warn("Downloaded an HTML page instead of a real file. The AI will fix this.")
                elif rc == 0 and expects_output and empty_output:
                    warn("Command returned empty output — result is inconclusive. The AI will review.")
                elif rc == 0 and output_has_errors:
                    warn("Command ran but output suggests a problem. The AI will review this.")
                elif rc == 127:
                    warn("That program is not installed on this system — the AI will find another way.")
                elif rc == -1:
                    warn("Command timed out. The AI will try a different approach.")
                else:
                    print(C(f"  ✗ Exit {rc}", RED))
                    warn("This step had an issue. The AI will look at this and try to fix it.")

            step_ok = (exit1_is_ok or (rc == 0 and not output_has_errors
                       and not (expects_output and empty_output)
                       and not downloaded_html))
            entry = {"step":i,"command":cmd,"returncode":rc,
                     "stdout":stdout[:1500],"stderr":stderr[:500],
                     "success": step_ok}
            if downloaded_html:
                entry["note"] = "Downloaded HTML page instead of real file"
            if expects_output and empty_output:
                entry["note"] = "Empty output — result inconclusive"
            step_outputs.append(entry)
            session_log.append(entry)

        if aborted:
            return

        # ── Auto-verification ──
        # Run verify_command to PROVE the task is done, don't just ask the user
        verify_cmd = plan.get("verify_command", "").strip()
        sc = plan.get("success_check", "")
        any_step_failed = any(
            not s.get("success", True) for s in step_outputs if not s.get("skipped")
        )

        if verify_cmd:
            if not backend.expert_mode:
                print(f"\n{'─'*60}")
            print(f"  {CYAN}{BOLD}Verifying…{R}" if backend.expert_mode else f"  {CYAN}{BOLD}Verifying task completion…{R}")
            sudo_pw_v = None
            if verify_cmd.strip().startswith("sudo"):
                try:
                    sudo_pw_v = get_or_cache_sudo_password()
                except KeyboardInterrupt:
                    pass
            v_rc, v_stdout, v_stderr = run_cmd_live(verify_cmd, sudo_password=sudo_pw_v, timeout=30)
            v_combined = (v_stdout + "\n" + v_stderr).lower()
            # "not found" / "not installed" are SUCCESS signals for removal tasks —
            # don't count them as errors here; let v_rc decide pass/fail
            v_has_errors = any(p.lower() in v_combined for p in [
                "error:", "no such file", "failed", "inactive", "dead",
            ])
            # ── Stronger verification: empty output = not verified ──
            v_empty = not v_stdout.strip() and not v_stderr.strip()
            # Reject weak verify commands that use || echo or || true
            v_is_weak = ("|| echo" in verify_cmd or "|| true" in verify_cmd
                         or "|| :" in verify_cmd)
            # If all steps passed and verify exits 0 (even empty), accept it —
            # empty output on exit 0 often means "nothing found" (removal success)
            v_steps_all_ok = not any_step_failed
            if v_rc == 0 and not v_has_errors and not v_is_weak and (not v_empty or v_steps_all_ok):
                print(f"\n  {GREEN}{BOLD}✓ VERIFIED — Task completed successfully!{R}")
                if plan.get("needs_synthesis"):
                    _synthesize_findings(backend, user_text, step_outputs)
                elif sc:
                    info(sc)
                print(f"  {DIM}Long live Linux! 🐧{R}")
                _ask_rating()
                _failed_for_mem = next((s for s in step_outputs if not s.get("success", True) and not s.get("skipped")), {})
                _mem_record_fix(
                    user_text,
                    [s.get("command", "") for s in step_outputs if s.get("success")],
                    failing_cmd=_failed_for_mem.get("command", ""),
                    error_excerpt=(_failed_for_mem.get("stderr") or _failed_for_mem.get("stdout") or "")[:400],
                )
                return
            else:
                if v_is_weak:
                    warn("Weak verify command rejected — needs a real check.")
                elif v_empty:
                    warn("Verification returned no output — cannot confirm success.")
                else:
                    warn("Verification failed — task is NOT yet complete.")
                # Add verification output to step_outputs for the AI
                step_outputs.append({
                    "step": "verify", "command": verify_cmd,
                    "returncode": v_rc,
                    "stdout": v_stdout[:2000], "stderr": v_stderr[:1000],
                    "success": False
                })
        elif not any_step_failed:
            # No verify_command but all steps passed — ask user as fallback
            if plan.get("needs_synthesis"):
                _synthesize_findings(backend, user_text, step_outputs)
                print(f"  {DIM}Long live Linux! 🐧{R}")
                _ask_rating()
                _failed_for_mem = next((s for s in step_outputs if not s.get("success", True) and not s.get("skipped")), {})
                _mem_record_fix(
                    user_text,
                    [s.get("command", "") for s in step_outputs if s.get("success")],
                    failing_cmd=_failed_for_mem.get("command", ""),
                    error_excerpt=(_failed_for_mem.get("stderr") or _failed_for_mem.get("stdout") or "")[:400],
                )
                return
            if sc:
                print(f"\n  {CYAN}{BOLD}How to check if it worked:{R} {sc}")
            try:
                time.sleep(0.3)
                sys.stdout.flush()
                print(f"\n{'─'*60}")
                print(f"\n  {GREEN}{BOLD}Did that fix your problem?{R}")
                ans = input(f"  Type {C('y',GREEN,BOLD)} for yes, {C('n',YELLOW,BOLD)} to keep trying: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!"); sys.exit(0)
            if ans in ("y", "yes"):
                print(f"\n  {GREEN}{BOLD}🎉 Great! Glad it's working now!{R}")
                print(f"  {DIM}Long live Linux! 🐧{R}")
                _ask_rating()
                _failed_for_mem = next((s for s in step_outputs if not s.get("success", True) and not s.get("skipped")), {})
                _mem_record_fix(
                    user_text,
                    [s.get("command", "") for s in step_outputs if s.get("success")],
                    failing_cmd=_failed_for_mem.get("command", ""),
                    error_excerpt=(_failed_for_mem.get("stderr") or _failed_for_mem.get("stdout") or "")[:400],
                )
                return

        if rnd >= max_rounds:
            warn(f"We've tried {max_rounds} rounds. If it's still not fixed:")
            info("Try asking on https://askubuntu.com or https://reddit.com/r/linux4noobs")
            return

        # ── Better error feedback to AI ──
        # Clearly tell the AI what failed, what worked, and what NOT to repeat
        failed_steps = [s for s in step_outputs if not s.get("success", True) and not s.get("skipped")]
        passed_steps = [s for s in step_outputs if s.get("success", False)]

        # ── Count download failures across all rounds for early-stop ──
        all_cmds_so_far = " ".join(m.get("content","") for m in messages if m.get("role") == "user")
        download_failures = sum(1 for s in failed_steps
                                if any(k in s.get("command","") for k in ("curl","wget","download")))
        # Check all rounds by counting "404" and "not found" mentions in conversation
        total_404s = all_cmds_so_far.lower().count("404") + all_cmds_so_far.lower().count("not found")

        feedback = "NOT YET RESOLVED.\n\n"

        # ── Early stop: too many download failures → app likely doesn't exist ──
        if download_failures >= 2 or total_404s >= 3:
            feedback += (
                "IMPORTANT: Multiple download attempts have FAILED (404 / not found). "
                "This strongly suggests the app does NOT have a Linux desktop version. "
                "You MUST either:\n"
                "  1. Confirm the app is NOT available for Linux and tell the user honestly.\n"
                "     Suggest: web app version, similar Linux alternatives, or Wine.\n"
                "     Set resolved:true with a clear explanation.\n"
                "  2. ONLY if you are CERTAIN a Linux version exists, provide the EXACT "
                "verified URL (not a guess).\n"
                "Do NOT try another wget/curl with a guessed URL.\n\n"
            )

        if failed_steps:
            feedback += "FAILED steps (DO NOT repeat these commands or approaches):\n"
            for s in failed_steps:
                feedback += f"  - Command: {s.get('command','')}\n"
                feedback += f"    Exit code: {s.get('returncode','?')}\n"
                err_out = s.get('stderr','') or s.get('stdout','')
                if err_out:
                    feedback += f"    Error: {err_out[:500]}\n"
        if passed_steps:
            feedback += "\nSteps that WORKED (do not redo these):\n"
            for s in passed_steps:
                feedback += f"  - {s.get('command','')}\n"
        feedback += (
            "\nYou MUST try a COMPLETELY DIFFERENT approach or method.\n"
            "Do NOT repeat any of the above failed commands with minor tweaks.\n"
            "If the previous approach used apt, try snap or flatpak or downloading "
            "from the official website. Exhaust all alternatives.\n"
            "Include a verify_command that PROVES the task is done.\n"
        )

        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": feedback})

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — 20 FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

def _lang_note() -> str:
    """Return a language instruction for the AI if the system is non-English."""
    lang = (os.environ.get("LANG") or os.environ.get("LANGUAGE") or "en_US").split(".")[0]
    code = lang.split("_")[0].lower()
    if code in ("en", "c", "posix", ""):
        return ""
    return (f"\n\nLANGUAGE INSTRUCTION: The user's system language is '{lang}'. "
            "Write ALL analysis, descriptions, explanations, and step descriptions in that language. "
            "Keep shell commands, package names, and file paths in English only.\n")

def _sys_ctx_block(extra: dict) -> str:
    ctx = "\n\nSYSTEM CONTEXT:\n" + json.dumps(extra, indent=2)
    ctx += _lang_note()
    # Distro-aware reminder
    pm = extra.get("pkg_mgr", "")
    if pm and pm != "apt":
        ctx += f"\n\nDISTRO NOTE: This system uses '{pm}' as the package manager. Use '{pm}' commands (NOT apt) for all package operations.\n"
    # Cross-session memory: what the user has done before, and what's installed.
    # These blocks live INSIDE the cached system prompt, so they cost nothing
    # on cache hits but give the model real continuity across tasks/sessions.
    fp = _load_fingerprint()
    if fp:
        ctx += "\n\nINSTALLED ENVIRONMENT (collected once per session):\n" + json.dumps(fp, indent=2)
    ctx += _mem_block()
    ctx += _recent_tasks_block()
    ctx += _recent_actions_block()
    return ctx

# ── FEATURE 1: Fix Issue (general) ───────────────────────────────────────────
def feat_fix(backend, bctx, slog):
    hdr("Fix Issue — Describe your problem")
    try:
        issue = input(f"\n{BOLD}{BLUE}What's the problem?{R} ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not issue: return
    agentic_engine(backend, issue, bctx, slog)

# ── FEATURE 2: Health Dashboard ───────────────────────────────────────────────
def feat_health(backend, bctx, slog):
    hdr("Health Dashboard — Full system scan")
    with Spinner("Collecting health data…"):
        ctx = {**bctx, **health_ctx()}

    # ── Display directly — no AI needed for basic health data ──
    section("System Overview")
    print(f"  {DIM}OS:{R}      {ctx.get('os','?')}")
    print(f"  {DIM}Kernel:{R}  {ctx.get('kernel','?')}  ·  {ctx.get('arch','?')}")
    print(f"  {DIM}Uptime:{R}  {ctx.get('uptime','?')}")

    section("CPU & Memory")
    for line in ctx.get('cpu_usage','').splitlines()[:3]:
        if line.strip(): print(f"  {line}")
    for line in ctx.get('memory','').splitlines()[:3]:
        if line.strip(): print(f"  {line}")

    section("Disk Space")
    for line in ctx.get('disk','').splitlines():
        if line.strip():
            pct = re.search(r'(\d+)%', line)
            col = RED if pct and int(pct.group(1)) >= 90 else (YELLOW if pct and int(pct.group(1)) >= 75 else GREEN)
            print(f"  {col}{line}{R}")

    section("Failed Services")
    failed = ctx.get('failed_services','').strip()
    if failed and 'failed' in failed.lower():
        for line in failed.splitlines()[:10]:
            if line.strip(): print(f"  {RED}{line}{R}")
    else:
        ok("No failed services")

    section("Temperatures")
    temps = ctx.get('temps','').strip()
    if temps:
        for line in temps.splitlines()[:8]:
            if line.strip(): print(f"  {line}")
    else:
        print(f"  {DIM}(temperature sensors not available){R}")

    # If any issues found, let AI suggest fixes
    has_issues = (
        any(int(m.group(1)) >= 90 for m in [re.search(r'(\d+)%', l) for l in ctx.get('disk','').splitlines() if l] if m)
        or ('failed' in failed.lower() if failed else False)
    )
    if has_issues:
        print(f"\n  {YELLOW}{BOLD}Issues detected — asking Claude for recommendations…{R}")
        sys_p = BASE_SYS + "\nHealth check found issues. Suggest specific fixes." + _sys_ctx_block(ctx)
        fix_engine(backend, sys_p, [{"role":"user","content":"Fix the issues found in the health check."}], slog)
    else:
        print(f"\n  {GREEN}{BOLD}✓ System looks healthy!{R}")

# ── FEATURE 3: Package Wizard ─────────────────────────────────────────────────
def feat_packages(backend, bctx, slog):
    hdr("Package Wizard — Find & install software")
    try:
        want = input(f"\n{BOLD}What do you want to do?{R} {C('(e.g. edit videos, browse web, code Python)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not want: return

    installed = _r("dpkg --get-selections 2>/dev/null | head -50 || rpm -qa 2>/dev/null | head -50 || pacman -Q 2>/dev/null | head -50")
    sys_p = BASE_SYS + f"""
Additional instructions for PACKAGE WIZARD mode:
- Recommend the BEST package(s) for the user's goal on their distro ({bctx.get('pkg_mgr','apt')}).
- Consider: ease of use, stability, popularity, licence.
- Provide install command, a one-line description, and any post-install setup steps.
- If multiple options exist, pick the best one first and mention alternatives.
- Currently installed packages (sample): {installed[:500]}

IMPORTANT — these popular apps are NOT in Ubuntu's default apt repos and need their own repo added first:
  brave-browser  → add https://brave-browser-apt-release.s3.brave.com/ repo + keyring first
  opera-stable   → add https://deb.opera.com/opera-stable/ repo + keyring first
  vivaldi-stable → add https://repo.vivaldi.com/archive/deb/ repo + keyring first
  google-chrome-stable → add https://dl.google.com/linux/chrome/deb/ repo first
  microsoft-edge-stable → add https://packages.microsoft.com/repos/edge repo first
  code (VS Code) → add https://packages.microsoft.com/repos/code repo first
  slack-desktop  → download .deb from https://slack.com/downloads/linux
  zoom           → download .deb from https://zoom.us/download
  discord        → download .deb from https://discord.com/download
Do NOT try apt-cache search or apt install for these without adding their repo first.
""" + _sys_ctx_block(bctx)

    fix_engine(backend, sys_p, [{"role":"user","content":want}], slog)

# ── FEATURE 4: Network Doctor ─────────────────────────────────────────────────
def feat_network(backend, bctx, slog):
    hdr("Network Doctor — Diagnose connectivity")
    with Spinner("Running network diagnostics…"):
        ctx = {**bctx, **network_ctx()}
    ok("Diagnostics collected")
    try:
        problem = input(f"\n{BOLD}Describe the network problem (or press Enter for full scan):{R} ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "Diagnose my network and report any issues or misconfigurations."

    sys_p = BASE_SYS + """
Additional instructions for NETWORK DOCTOR mode:
- Diagnose connectivity layer by layer: interface → link → gateway → DNS → internet.
- Check firewall rules, DNS resolution, routing table.
- For each issue found, provide a clear fix.
- Explain WHY each step helps — this is educational.
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE 5: Security Audit ─────────────────────────────────────────────────
def feat_security(backend, bctx, slog):
    hdr("Security Audit — Harden your system")
    with Spinner("Collecting security data…"):
        ctx = {**bctx, **security_ctx()}
    ok("Security data collected")
    warn("This will check firewall, SSH, open ports, SUID files, login history.")
    sys_p = BASE_SYS + """
Additional instructions for SECURITY AUDIT mode:
- Check: firewall status, SSH hardening, open ports, SUID/SGID files, failed logins.
- Start with safe read-only checks; suggest hardening steps with moderate/dangerous risk labels.
- Explain each risk in plain language.
- Provide an overall security score (1-10) in the analysis field.
- Prioritise fixes by severity: Critical → High → Medium → Low.
""" + _sys_ctx_block(ctx)
    msg = "Run a comprehensive security audit and suggest hardening steps."
    fix_engine(backend, sys_p, [{"role":"user","content":msg}], slog)

# ── FEATURE 6: Disk Detective ─────────────────────────────────────────────────
def feat_disk(backend, bctx, slog):
    hdr("Disk Detective — Free up space")
    with Spinner("Scanning disk usage…"):
        ctx = {**bctx, **disk_ctx()}
    ok("Disk data collected")
    sys_p = BASE_SYS + """
Additional instructions for DISK DETECTIVE mode:
- Identify top space consumers clearly.
- Suggest safe cleanup: apt/dnf cache, journal logs, old kernels, trash, temp files.
- Flag large files that might be accidental (core dumps, old backups, VM images).
- Do NOT suggest deleting files without explaining what they are.
- Start with read-only du/df commands before any cleanup.
""" + _sys_ctx_block(ctx)
    msg = "Find what is using disk space and help me free up space safely."
    fix_engine(backend, sys_p, [{"role":"user","content":msg}], slog)

# ── FEATURE 7: Driver Check ───────────────────────────────────────────────────
def feat_drivers(backend, bctx, slog):
    hdr("Driver Check — Detect missing drivers")
    with Spinner("Scanning hardware…"):
        ctx = {**bctx, **driver_ctx()}
    ok("Hardware scanned")
    sys_p = BASE_SYS + """
Additional instructions for DRIVER CHECK mode:
- Identify all hardware devices and check if they have working drivers.
- Flag devices with missing/broken firmware or kernel modules.
- Provide specific install commands for missing drivers on this distro.
- For NVIDIA/AMD GPUs: recommend the optimal driver for gaming vs general use.
- For WiFi adapters: identify chipset and recommend working drivers.
""" + _sys_ctx_block(ctx)
    msg = "Check all hardware for missing or problematic drivers and fix them."
    fix_engine(backend, sys_p, [{"role":"user","content":msg}], slog)

# ── FEATURE 8: Service Manager ────────────────────────────────────────────────
def feat_services(backend, bctx, slog):
    hdr("Service Manager — Optimise startup & services")
    with Spinner("Analysing services…"):
        ctx = {**bctx, **service_ctx()}
    ok("Services analysed")
    sys_p = BASE_SYS + """
Additional instructions for SERVICE MANAGER mode:
- Identify services that are failing, slow to start, or unnecessary.
- Suggest which services can safely be disabled to improve boot time & RAM usage.
- Explain what each flagged service does before suggesting to disable it.
- Never suggest disabling critical system services without a strong warning.
- Show estimated boot time savings where possible.
""" + _sys_ctx_block(ctx)
    msg = "Analyse my running services, fix failures, and optimise startup time."
    fix_engine(backend, sys_p, [{"role":"user","content":msg}], slog)

# ── FEATURE 9: Log Analyser ───────────────────────────────────────────────────
def feat_logs(backend, bctx, slog):
    hdr("Log Analyser — Decode errors")
    try:
        paste = input(f"\n{BOLD}Paste an error message (or press Enter to scan recent logs):{R}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    with Spinner("Reading logs…"):
        ctx = {**bctx, **log_ctx(paste)}
    ok("Logs collected")
    sys_p = BASE_SYS + """
Additional instructions for LOG ANALYSER mode:
- Decode cryptic error messages into plain English.
- Identify the ROOT CAUSE, not just symptoms.
- Cross-reference multiple log sources to find the chain of events.
- Explain what each error means and why it happened.
- Provide targeted fixes for each error found.
""" + _sys_ctx_block(ctx)
    msg = paste if paste else "Analyse my system logs and explain any errors or warnings."
    fix_engine(backend, sys_p, [{"role":"user","content":msg}], slog)

# ── FEATURE 10: Update Advisor ────────────────────────────────────────────────
def feat_updates(backend, bctx, slog):
    hdr("Check for Updates — Keep your system current")
    pkg = bctx.get('pkg_mgr', 'apt')

    # ── Run update directly — no AI needed ──
    print(f"\n  {CYAN}Refreshing package lists…{R}")
    sudo_pw = None
    try:
        sudo_pw = get_or_cache_sudo_password()
    except KeyboardInterrupt:
        return

    if pkg == 'apt':
        run_cmd_live("sudo apt-get update -q", sudo_password=sudo_pw)
        rc, out, _ = run_cmd_live("apt list --upgradable 2>/dev/null | tail -n +2", sudo_password=None)
        lines = [l for l in out.splitlines() if l.strip()]
        if lines:
            print(f"\n  {YELLOW}{BOLD}{len(lines)} update(s) available:{R}")
            for l in lines[:20]: print(f"  {DIM}{l}{R}")
            try:
                ch = input(f"\n  {BOLD}Install all updates now? [y/n]:{R} ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return
            if ch in ('y', 'yes'):
                print(f"\n  {CYAN}▶ Installing updates…{R}")
                run_cmd_live("sudo apt-get upgrade -y", sudo_password=sudo_pw)
                run_cmd_live("sudo apt-get autoremove -y", sudo_password=sudo_pw)
                ok("System fully updated.")
        else:
            ok("System is up to date.")
    elif pkg in ('dnf', 'yum'):
        run_cmd_live(f"sudo {pkg} check-update", sudo_password=sudo_pw)
        try:
            ch = input(f"\n  {BOLD}Install all updates? [y/n]:{R} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ch in ('y', 'yes'):
            run_cmd_live(f"sudo {pkg} upgrade -y", sudo_password=sudo_pw)
            ok("System updated.")
    elif pkg == 'pacman':
        run_cmd_live("sudo pacman -Syu --noconfirm", sudo_password=sudo_pw)
        ok("System updated.")
    else:
        # Fallback for unknown package managers — let AI handle
        with Spinner("Checking for updates…"):
            ctx = {**bctx, **update_ctx()}
        sys_p = BASE_SYS + "\nCheck for and apply system updates." + _sys_ctx_block(ctx)
        fix_engine(backend, sys_p, [{"role":"user","content":"Update my system."}], slog)

# ── FEATURE: Upgrade OS to Latest Version ────────────────────────────────────
def feat_os_upgrade(backend, bctx, slog):
    hdr("Upgrade OS to Latest Version")
    pkg = bctx.get('pkg_mgr', 'apt')
    os_str = bctx.get('os', 'Unknown OS')

    print(f"\n  {BOLD}Current OS:{R} {DIM}{os_str}{R}")
    print(f"\n  {YELLOW}{BOLD}⚠  This is a MAJOR upgrade — not just package updates.{R}")
    print(f"  {DIM}It will move your entire OS to the next major version.{R}")
    print(f"  {DIM}• Can take 30–90 minutes{R}")
    print(f"  {DIM}• Requires a reboot when done{R}")
    print(f"  {DIM}• Close all other applications first{R}")
    print(f"  {DIM}• Keep your laptop plugged in{R}")
    print(f"  {DIM}• Do NOT interrupt once started{R}")

    try:
        ch = input(f"\n  {BOLD}Continue? [y/n]:{R} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if ch not in ('y', 'yes'):
        return

    sudo_pw = None
    try:
        sudo_pw = get_or_cache_sudo_password()
    except KeyboardInterrupt:
        return

    if pkg == 'apt':
        has_release_upgrade = bool(shutil.which('do-release-upgrade'))

        # Step 1 — bring current packages fully up to date first
        print(f"\n  {CYAN}Step 1/3 — Updating current packages first (required before upgrade)…{R}")
        print(f"  {YELLOW}⚠  This may take 10–60 minutes. Please wait…{R}")
        run_cmd_live("sudo apt-get update -q", sudo_password=sudo_pw, timeout=120)
        run_cmd_live("sudo apt-get upgrade -y", sudo_password=sudo_pw, timeout=3600)
        run_cmd_live("sudo apt-get dist-upgrade -y", sudo_password=sudo_pw, timeout=3600)
        run_cmd_live("sudo apt-get autoremove -y", sudo_password=sudo_pw, timeout=300)

        # Step 2 — ensure the upgrade tool is installed
        print(f"\n  {CYAN}Step 2/3 — Ensuring upgrade tool is installed…{R}")
        run_cmd_live("sudo apt-get install -y update-manager-core", sudo_password=sudo_pw, timeout=120)

        if has_release_upgrade:
            # Ubuntu: hand off to do-release-upgrade for a proper interactive upgrade
            print(f"\n  {CYAN}Step 3/3 — Starting Ubuntu release upgrade…{R}")
            print(f"  {DIM}TuxGenie will hand off to the Ubuntu upgrade tool.{R}")
            print(f"  {DIM}Follow the prompts in this terminal window.{R}\n")
            rc = os.system("sudo do-release-upgrade")
            if rc == 0:
                ok("OS upgrade complete! Please reboot your system.")
                print(f"\n  {BOLD}Run: {CYAN}sudo reboot{R}")
            else:
                warn(f"Upgrade finished with code {rc}. Review the output above for details.")
                print(f"  {DIM}You can retry later with: sudo do-release-upgrade{R}")
        else:
            # Debian / non-Ubuntu: sources.list is already at new release after dist-upgrade
            print(f"\n  {CYAN}Step 3/3 — Applying full distribution upgrade…{R}")
            print(f"  {YELLOW}⚠  This may take 30–90 minutes. Please wait…{R}")
            run_cmd_live("sudo apt-get dist-upgrade -y", sudo_password=sudo_pw, timeout=7200)
            run_cmd_live("sudo apt-get autoremove -y --purge", sudo_password=sudo_pw, timeout=300)
            ok("Distribution upgrade complete! Please reboot your system.")
            print(f"\n  {BOLD}Run: {CYAN}sudo reboot{R}")

    elif pkg in ('dnf', 'yum'):
        rc2, ver_out, _ = run_cmd("rpm -E %fedora 2>/dev/null", timeout=5)
        try:
            current_ver = int(ver_out.strip())
            next_ver = current_ver + 1
            print(f"\n  {DIM}Fedora {current_ver} → Fedora {next_ver}{R}")
        except (ValueError, TypeError):
            current_ver, next_ver = None, None

        # Step 1 — update current system
        print(f"\n  {CYAN}Step 1/3 — Updating current packages…{R}")
        run_cmd_live(f"sudo {pkg} upgrade -y", sudo_password=sudo_pw, timeout=3600)

        # Step 2 — install upgrade plugin
        print(f"\n  {CYAN}Step 2/3 — Installing system-upgrade plugin…{R}")
        run_cmd_live(f"sudo {pkg} install -y dnf-plugin-system-upgrade", sudo_password=sudo_pw, timeout=300)

        if next_ver:
            # Step 3 — download new release packages
            print(f"\n  {CYAN}Step 3/3 — Downloading Fedora {next_ver} packages (2–4 GB)…{R}")
            print(f"  {YELLOW}⚠  This may take 30–60 minutes. Please wait…{R}")
            rc3, _, _ = run_cmd_live(
                f"sudo {pkg} system-upgrade download --releasever={next_ver} -y",
                sudo_password=sudo_pw, timeout=7200)
            if rc3 == 0:
                ok(f"Packages downloaded. System will reboot to apply the upgrade.")
                try:
                    ch2 = input(f"\n  {BOLD}Reboot now to complete upgrade? [y/n]:{R} ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    return
                if ch2 in ('y', 'yes'):
                    run_cmd_live(f"sudo {pkg} system-upgrade reboot", sudo_password=sudo_pw, timeout=30)
                else:
                    info(f"Run 'sudo {pkg} system-upgrade reboot' when ready.")
            else:
                warn("Download failed. Check your internet connection and try again.")
        else:
            warn("Could not determine current Fedora version. Try: sudo dnf system-upgrade download --releasever=<version> -y")

    elif pkg == 'pacman':
        print(f"\n  {DIM}Arch Linux is a rolling release — there is no version upgrade.{R}")
        print(f"  {DIM}Running a full system sync instead (pacman -Syu).{R}")
        try:
            ch3 = input(f"\n  {BOLD}Run full system upgrade? [y/n]:{R} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ch3 in ('y', 'yes'):
            print(f"  {YELLOW}⚠  This may take a while. Please wait…{R}")
            run_cmd_live("sudo pacman -Syu --noconfirm", sudo_password=sudo_pw, timeout=3600)
            ok("System upgraded. A reboot is recommended.")

    else:
        sys_p = (BASE_SYS + f"""
The user wants to upgrade their OS to the latest major version.
Current OS: {os_str} · pkg: {pkg}

Provide safe, step-by-step commands to upgrade to the latest OS release.
RETURN ONLY VALID JSON.""")
        fix_engine(backend, sys_p,
                   [{"role": "user", "content": "Upgrade my OS to the latest version."}], slog)

# ── FEATURE 11: Script Generator ─────────────────────────────────────────────
def feat_script(backend, bctx, slog):
    hdr("Script Generator — Natural language → bash script")
    try:
        task = input(f"\n{BOLD}Describe what you want to automate:{R}\n{C('(e.g. back up /home to external drive every night)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not task: return

    sys_p = f"""You are TuxGenie, expert bash script writer.
The user describes a task. You write a complete, production-quality bash script.

Return JSON:
{{
  "analysis": "<what the script does>",
  "steps": [
    {{
      "description": "Save script to file",
      "command": "cat > ~/tuxgenie_script.sh << 'SCRIPT'\\n<full script here>\\nSCRIPT",
      "risk": "safe",
      "requires_root": false,
      "expected_output": "Script file created"
    }},
    {{
      "description": "Make it executable",
      "command": "chmod +x ~/tuxgenie_script.sh",
      "risk": "safe",
      "requires_root": false
    }}
  ],
  "success_check": "Run: bash ~/tuxgenie_script.sh",
  "resolved": false
}}

Script requirements:
- Add #!/bin/bash and set -euo pipefail
- Add comments explaining each section
- Handle errors gracefully
- Use variables for paths/settings at the top
- System: {bctx.get('os')} · pkg: {bctx.get('pkg_mgr')}
RETURN ONLY VALID JSON."""

    fix_engine(backend, sys_p, [{"role":"user","content":task}], slog)

# ── FEATURE 12: Cron Assistant ────────────────────────────────────────────────
def feat_cron(backend, bctx, slog):
    hdr("Cron Assistant — Schedule tasks easily")
    try:
        task = input(f"\n{BOLD}What should run, and when?{R}\n{C('(e.g. clean temp files every Sunday at 3am)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not task: return

    existing = _r("crontab -l 2>/dev/null")
    sys_p = f"""You are TuxGenie, cron expert.
User describes a scheduled task in plain English. Generate the cron entry and add it.

Return JSON with steps that:
1. Show the cron expression with an explanation (safe step, just echo)
2. Add it via 'crontab -l | {{ cat; echo "<entry>"; }} | crontab -'
3. Verify with 'crontab -l'

Existing crontab: {existing or '(empty)'}
System: {bctx.get('os')} · user: {bctx.get('user')}
RETURN ONLY VALID JSON."""

    fix_engine(backend, sys_p, [{"role":"user","content":task}], slog)

# ── FEATURE 13: Permission Doctor ────────────────────────────────────────────
def feat_perms(backend, bctx, slog):
    hdr("Permission Doctor — Fix permission issues")
    try:
        path = input(f"\n{BOLD}Which file/folder has permission issues? (path or description, or 'q' to go back):{R}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if _is_back(path): return
    if not path: path = "my home directory"

    safe_path = shlex.quote(path)
    ls_out = _r(f"ls -la {safe_path} 2>/dev/null || ls -la $(dirname {safe_path}) 2>/dev/null")
    stat_out = _r(f"stat {safe_path} 2>/dev/null")
    ctx = {**bctx, "path":path, "ls_output":ls_out, "stat_output":stat_out,
           "current_user":_r("whoami"), "groups":_r("groups")}

    sys_p = BASE_SYS + """
Additional instructions for PERMISSION DOCTOR mode:
- Explain current permissions in plain English (who can read/write/execute).
- Identify what's wrong and why it causes the issue.
- Provide the minimal permission fix — avoid overly permissive settings.
- Explain the chmod/chown command syntax used.
- Warn if the path is system-critical.
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":f"Fix permissions for: {path}"}], slog)

# ── FEATURE 14: Boot Analyser ─────────────────────────────────────────────────
def feat_boot(backend, bctx, slog):
    hdr("Boot Analyser — Speed up slow boot")
    with Spinner("Analysing boot sequence…"):
        ctx = {**bctx, **boot_ctx()}
    ok("Boot data collected")
    sys_p = BASE_SYS + """
Additional instructions for BOOT ANALYSER mode:
- Identify the top slowest services and explain why they're slow.
- Suggest safe services to disable or delay.
- Look for failed units causing timeouts.
- Show potential boot time improvement in seconds.
- Never suggest disabling networking, display-manager, or critical boot services
  without a very clear warning.
""" + _sys_ctx_block(ctx)
    msg = "Analyse my boot time and help me make it faster."
    fix_engine(backend, sys_p, [{"role":"user","content":msg}], slog)

# ── FEATURE 15: Docker Helper ─────────────────────────────────────────────────
def feat_docker(backend, bctx, slog):
    hdr("Docker Helper — Container troubleshooting")
    with Spinner("Collecting Docker info…"):
        ctx = {**bctx, **docker_ctx()}
    ok("Docker info collected")
    if not ctx.get("docker_installed", True):
        warn("Docker is not installed.")
        try:
            install = input("  Install Docker? [y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if install not in ("y","yes"): return
    try:
        problem = input(f"\n{BOLD}Describe the Docker problem (or Enter for general check):{R}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "Check Docker health, clean unused images/containers, and fix any issues."

    sys_p = BASE_SYS + """
Additional instructions for DOCKER HELPER mode:
- Diagnose container failures, networking, volume mounts, resource limits.
- Suggest docker system prune commands with clear explanation of what gets deleted.
- For docker-compose issues, check the compose file and environment.
- Explain Docker networking concepts when relevant.
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE 16: Config Backup ─────────────────────────────────────────────────
BACKUP_PATHS = [
    "/etc/ssh", "/etc/nginx", "/etc/apache2", "/etc/mysql",
    "/etc/postgresql", "/etc/fstab", "/etc/hosts", "/etc/hostname",
    "/etc/network", "/etc/NetworkManager", "/etc/crontab", "/etc/cron.d",
    "/etc/systemd/system", "/etc/ufw", "/etc/iptables",
    "~/.bashrc", "~/.zshrc", "~/.profile", "~/.ssh/config",
]

def feat_backup(backend, bctx, slog):
    hdr("Config Backup — Snapshot your configs")

    # When running as root via sudo re-exec, save the backup to the original
    # user's home, not /root/. SUDO_USER is set by sudo to the invoking user.
    backup_dir = BACKUPS_DIR
    if os.geteuid() == 0 and os.environ.get("SUDO_USER"):
        try:
            import pwd
            sudo_user = os.environ["SUDO_USER"]
            user_home = pwd.getpwnam(sudo_user).pw_dir
            backup_dir = os.path.join(user_home, ".config", "tuxgenie", "data", "backups")
            os.makedirs(backup_dir, exist_ok=True)
        except Exception:
            backup_dir = BACKUPS_DIR  # fall back to root's home if SUDO_USER lookup fails

    # Many BACKUP_PATHS (e.g. /etc/ssh, /etc/sudoers.d) require root to read.
    # Without sudo we'd silently skip everything and leave the user with an
    # almost-empty tarball that looks like a successful backup. Re-exec under
    # sudo so the snapshot is actually useful.
    if os.geteuid() != 0:
        try:
            warn("Most config files in /etc require root to read.")
            ans = input(f"  {BOLD}Re-run backup with sudo for a complete snapshot?{R} [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if ans in ("", "y", "yes"):
            try:
                sudo_pw = get_or_cache_sudo_password()
            except KeyboardInterrupt:
                return
            if sudo_pw:
                # Hand off to a sudo'd python that runs the same feature directly.
                # Use sys.executable + actual .py file so this works under both .deb
                # and pip installs (sys.argv[0] under pip is an entry-point script,
                # not the Python source file).
                py_file = os.path.abspath(__file__)
                cmd = [
                    "sudo", "-S", "-p", "",
                    sys.executable, py_file,
                    "--feature", "backup",
                ]
                try:
                    subprocess.run(cmd, input=sudo_pw + "\n", text=True)
                except Exception as e:
                    err(f"Sudo re-exec failed: {e}")
                return
        warn("Continuing without sudo — protected paths will be skipped.")

    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # List existing backups
    try:
        existing = sorted([
            f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")
        ], reverse=True)
    except FileNotFoundError:
        existing = []
    if existing:
        section("Existing backups")
        for b in existing[:5]:
            path = os.path.join(backup_dir, b)
            size = os.path.getsize(path)
            info(f"{b}  ({size//1024} KB)")

    section("Creating new backup")
    archive = os.path.join(backup_dir, f"tuxgenie_backup_{ts}.tar.gz")
    backed  = []
    skipped = []

    with tarfile.open(archive, "w:gz") as tar:
        for p in BACKUP_PATHS:
            expanded = os.path.expanduser(p)
            if os.path.exists(expanded):
                try:
                    tar.add(expanded, arcname=expanded.lstrip("/"),
                            recursive=True)
                    backed.append(expanded)
                except Exception as e:
                    skipped.append(f"{expanded} ({e})")
            else:
                skipped.append(f"{expanded} (not found)")

    # If we're running as root via sudo, chown the archive back to the
    # original user so they can read/delete it from their normal session.
    if os.geteuid() == 0 and os.environ.get("SUDO_USER"):
        try:
            import pwd
            pw = pwd.getpwnam(os.environ["SUDO_USER"])
            os.chown(archive, pw.pw_uid, pw.pw_gid)
        except Exception:
            pass

    size_kb = os.path.getsize(archive) // 1024
    ok(f"Backup saved: {archive}  ({size_kb} KB)")
    section("Backed up")
    for b in backed:
        print(f"    {C('✓', GREEN)} {b}")
    if skipped:
        section("Skipped (not found on this system)")
        for s in skipped[:8]:
            print(f"    {C('·', DIM)} {s}")

    print(f"\n{DIM}  Restore with: sudo tar -xzf {archive} -C /{R}")

# ── FEATURE 17: Hardware Info ─────────────────────────────────────────────────
def feat_hardware(backend, bctx, slog):
    hdr("Hardware Info — Full system report")
    with Spinner("Gathering hardware info…"):
        ctx = {**bctx, **hardware_ctx()}

    # ── Display directly — pure data, no AI needed ──
    section("CPU")
    for line in ctx.get('cpu','').splitlines()[:6]:
        if line.strip(): print(f"  {line}")

    section("Memory")
    for line in ctx.get('memory','').splitlines()[:4]:
        if line.strip(): print(f"  {line}")

    section("Storage")
    for line in ctx.get('disks','').splitlines()[:10]:
        if line.strip(): print(f"  {line}")

    section("Graphics")
    for line in ctx.get('gpu','').splitlines()[:6]:
        if line.strip(): print(f"  {line}")

    section("Network Interfaces")
    for line in ctx.get('network','').splitlines()[:8]:
        if line.strip(): print(f"  {line}")

    section("USB Devices")
    for line in ctx.get('usb','').splitlines()[:8]:
        if line.strip(): print(f"  {line}")

    ok("Hardware report complete. Ask TuxGenie if you need help with any device.")

# ── FEATURE 18: SSH Setup Wizard ─────────────────────────────────────────────
def feat_ssh(backend, bctx, slog):
    hdr("SSH Setup Wizard — Secure remote access")
    ssh_ctx = {
        **bctx,
        "sshd_config":   _r("cat /etc/ssh/sshd_config 2>/dev/null"),
        "ssh_keys":      _r("ls -la ~/.ssh/ 2>/dev/null"),
        "sshd_running":  _r("systemctl is-active sshd 2>/dev/null || systemctl is-active ssh 2>/dev/null"),
        "authorized":    _r("cat ~/.ssh/authorized_keys 2>/dev/null | head -5"),
    }
    try:
        goal = input(f"\n{BOLD}What do you need?{R} {C('(e.g. passwordless login, harden SSH, generate keys, fix connection)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not goal: goal = "Set up SSH securely with key-based auth and harden the config."

    sys_p = BASE_SYS + """
Additional instructions for SSH SETUP WIZARD mode:
- Guide through SSH key generation, copying, and sshd_config hardening.
- Always back up sshd_config before modifying.
- Recommend: disable PasswordAuthentication, disable root login, use non-default port.
- Explain each hardening option in plain language.
- IMPORTANT: always test with 'sshd -t' before restarting SSH to avoid lockout.
""" + _sys_ctx_block(ssh_ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":goal}], slog)

# ── FEATURE 19: Process Inspector ────────────────────────────────────────────
def feat_processes(backend, bctx, slog):
    hdr("Process Inspector — Running programs")
    with Spinner("Collecting process data…"):
        top_cpu = _r("ps aux --sort=-%cpu | head -16")
        top_mem = _r("ps aux --sort=-%mem | head -16")
        load    = _r("cat /proc/loadavg")
        zombies = _r("ps aux | awk '$8==\"Z\"' | wc -l").strip()

    section("Load Average")
    print(f"  {load}")

    section("Top by CPU")
    for line in top_cpu.splitlines()[:12]:
        if line.strip(): print(f"  {DIM}{line}{R}")

    section("Top by Memory")
    for line in top_mem.splitlines()[:12]:
        if line.strip(): print(f"  {DIM}{line}{R}")

    if zombies and zombies != '0':
        print(f"\n  {YELLOW}⚠  {zombies} zombie process(es) detected{R}")

    # Only call AI if user has a specific problem to solve
    try:
        problem = input(f"\n  {BOLD}Any specific issue? (Enter to finish):{R} ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        return

    ps_ctx = {**bctx, "top_cpu": top_cpu, "top_mem": top_mem,
              "load_avg": load, "zombies": zombies}
    sys_p = BASE_SYS + """
Additional instructions for PROCESS INSPECTOR mode:
- Identify which process is the problem and WHY it's misbehaving.
- Suggest: nice/renice, kill signals (SIGTERM before SIGKILL).
- For memory leaks: identify the process and suggest restart/update.
""" + _sys_ctx_block(ps_ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE 20: Session Rollback ─────────────────────────────────────────────
def feat_rollback(backend, bctx, current_slog):
    hdr("Session Rollback — Undo changes")

    # Collect sessions
    session_files = sorted([
        f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")
    ], reverse=True)

    if not session_files and not current_slog:
        warn("No recorded sessions found. Nothing to roll back.")
        return

    options = []
    if current_slog:
        options.append(("current session", current_slog))

    for sf in session_files[:5]:
        path = os.path.join(SESSIONS_DIR, sf)
        try:
            data = json.loads(open(path).read())
            cmds = data.get("commands",[])
            if cmds:
                options.append((sf.replace(".json",""), cmds))
        except Exception:
            pass

    if not options:
        warn("No commands recorded to roll back."); return

    section("Available sessions")
    for i,(name,cmds) in enumerate(options,1):
        run_count = len([c for c in cmds if not c.get("skipped")])
        info(f"[{i}] {name}  ({run_count} commands ran)")

    try:
        ch = input(f"\n{BOLD}Select session to roll back [1-{len(options)}]:{R} ").strip()
        idx = int(ch) - 1
        if idx < 0 or idx >= len(options):
            raise ValueError
    except (ValueError, EOFError, KeyboardInterrupt):
        warn("Invalid selection."); return

    name, cmds = options[idx]
    ran = [c for c in cmds if not c.get("skipped") and c.get("returncode",1)==0]
    if not ran:
        warn("No successfully executed commands to undo."); return

    section("Commands to undo")
    for c in ran:
        print(f"    {C('$',CYAN)} {c['command']}")

    sys_p = f"""You are TuxGenie. The user wants to UNDO the following commands that were run on their Linux system.
Generate undo/rollback steps for each command where possible.
Explain clearly when a command cannot be undone (e.g. deleted files, already removed packages).

Commands that were run:
{json.dumps(ran, indent=2)}

System: {json.dumps(bctx, indent=2)}

Return the standard JSON fix plan with rollback steps.
RETURN ONLY VALID JSON."""

    fix_engine(backend, sys_p,
               [{"role":"user","content":"Undo all the changes from my last session."}],
               current_slog)

# ── FEATURE 21: Git Helper ───────────────────────────────────────────────────
def feat_git(backend, bctx, slog):
    hdr("Git Helper — Understand and fix Git problems")
    if not _r("command -v git"):
        warn("Git is not installed.")
        try:
            inst = input("  Install git now? [y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if inst not in ("y", "yes"):
            return

    git_ctx = {
        **bctx,
        "git_version":  _r("git --version 2>/dev/null"),
        "git_status":   _r("git status 2>/dev/null"),
        "git_log":      _r("git log --oneline -10 2>/dev/null"),
        "git_branches": _r("git branch -a 2>/dev/null"),
        "git_remotes":  _r("git remote -v 2>/dev/null"),
        "git_diff":     _r("git diff --stat 2>/dev/null"),
        "git_stash":    _r("git stash list 2>/dev/null"),
        "git_config":   _r("git config --list --local 2>/dev/null"),
    }
    try:
        problem = input(
            f"\n{BOLD}What do you need help with?{R} "
            f"{C('(e.g. fix merge conflict, undo last commit, explain this diff, push rejected)',DIM)}\n> "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "Give me an overview of my repo status and suggest any actions needed."

    sys_p = BASE_SYS + """
Additional instructions for GIT HELPER mode:
- Explain Git concepts in plain language — avoid jargon without explanation.
- For merge conflicts: show how to resolve each conflicted file step by step.
- For undoing changes: always explain what will be LOST before running destructive commands.
- Suggest commit message best practices when relevant.
- Never force-push to main/master without a very explicit warning.
- Use 'git diff', 'git log', 'git status' as safe diagnostic first steps.
""" + _sys_ctx_block(git_ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE 24: Bluetooth Fix ────────────────────────────────────────────────
def feat_bluetooth(backend, bctx, slog):
    hdr("Bluetooth Fix — Fix pairing & connection problems")
    with Spinner("Scanning Bluetooth system…"):
        ctx = {**bctx, **_parallel_ctx({
            "bt_hardware":   "lspci | grep -i bluetooth 2>/dev/null; lsusb | grep -i bluetooth 2>/dev/null",
            "bt_service":    "systemctl status bluetooth 2>/dev/null | head -8",
            "bt_devices":    "bluetoothctl devices 2>/dev/null",
            "bt_info":       "bluetoothctl show 2>/dev/null | head -15",
            "rfkill":        "rfkill list 2>/dev/null",
            "bt_module":     "lsmod | grep -i bluetooth 2>/dev/null",
            "dmesg_bt":      "dmesg | grep -iE 'bluetooth|hci|btusb' | tail -15 2>/dev/null",
            "bt_log":        "journalctl -u bluetooth -n 20 --no-pager 2>/dev/null",
        })}
    try:
        problem = input(f"\n{BOLD}What's the Bluetooth problem? (or Enter for general fix):{R}\n"
                        f"{C('(e.g. headphones wont connect, device not found, keeps disconnecting)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "Bluetooth is not working. Diagnose and fix the issue."
    sys_p = BASE_SYS + """
Additional instructions for BLUETOOTH FIX mode:
- Most common causes: bluetooth service not running, device blocked by rfkill, wrong pairing state, missing firmware.
- For 'device not found': check if bluetooth is powered on (bluetoothctl power on), check rfkill.
- For 'wont pair': try removing the device first (bluetoothctl remove), then re-pair.
- For 'keeps disconnecting': check power management settings, check firmware updates.
- For 'no bluetooth at all': check if hardware is rfkill-blocked or driver is missing.
- Translate terms: 'bluetooth service' = 'the program that manages bluetooth', 'rfkill' = 'a software switch that can turn off bluetooth'.
- bluetoothctl is safe to use; guide user through the interactive steps clearly.
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE 25: Printer Setup ─────────────────────────────────────────────────
def feat_printer(backend, bctx, slog):
    hdr("Printer Setup — Install and fix printers")
    with Spinner("Checking print system…"):
        ctx = {**bctx, **_parallel_ctx({
            "cups_status":   "systemctl status cups 2>/dev/null | head -8",
            "printers":      "lpstat -p 2>/dev/null || echo 'no printers configured'",
            "cups_version":  "cups-config --version 2>/dev/null",
            "usb_printers":  "lsusb | grep -i print 2>/dev/null",
            "network_devs":  "avahi-browse -art 2>/dev/null | grep -i print | head -10 2>/dev/null",
            "printer_pkgs":  "dpkg -l | grep -iE 'cups|hplip|brother|epson|canon|printer' 2>/dev/null | head -15",
            "cups_log":      "journalctl -u cups -n 20 --no-pager 2>/dev/null",
            "ppd_files":     "ls /etc/cups/ppd/ 2>/dev/null",
        })}
    try:
        problem = input(f"\n{BOLD}Describe your printer issue (or Enter to set up a new printer):{R}\n"
                        f"{C('(e.g. printer not detected, prints blank pages, HP printer, network printer)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "Help me set up my printer on Linux."
    sys_p = BASE_SYS + """
Additional instructions for PRINTER SETUP mode:
- CUPS is the print system on Linux — explain it as 'the program that talks to your printer'.
- For USB printers: check if detected with lsusb, then install manufacturer driver (hplip for HP, etc.).
- For network printers: use CUPS web interface (http://localhost:631) or lpstat/lpadmin commands.
- For HP printers: hplip is the best driver — guide through hp-setup if needed.
- For Brother/Canon/Epson: often need manufacturer .deb driver from their website.
- For 'blank pages' or 'wrong output': often a wrong PPD/driver — guide through re-adding with correct driver.
- Explain CUPS web UI (localhost:631) as 'a website on your own computer for managing printers'.
- Keep the user confident — printer setup on Linux is famously tricky but we can do it step by step.
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE 26: Webcam Fix ────────────────────────────────────────────────────
def feat_webcam(backend, bctx, slog):
    hdr("Webcam Fix — Fix camera for video calls")
    with Spinner("Checking camera system…"):
        ctx = {**bctx, **_parallel_ctx({
            "video_devices": "ls -la /dev/video* 2>/dev/null",
            "usb_cameras":   "lsusb | grep -iE 'camera|webcam|video|logitech|microsoft' 2>/dev/null",
            "v4l_devices":   "v4l2-ctl --list-devices 2>/dev/null",
            "camera_module": "lsmod | grep -iE 'uvcvideo|camera|v4l' 2>/dev/null",
            "dmesg_cam":     "dmesg | grep -iE 'camera|webcam|uvc|video' | tail -10 2>/dev/null",
            "pipewire_cam":  "pw-cli list-objects 2>/dev/null | grep -i camera | head -5 2>/dev/null",
            "apps_using":    "fuser /dev/video0 2>/dev/null",
        })}
    try:
        problem = input(f"\n{BOLD}What's the webcam problem? (or Enter for general fix):{R}\n"
                        f"{C('(e.g. camera not detected, black screen in Zoom, wrong camera selected)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "My webcam is not working. Diagnose and fix the issue."
    sys_p = BASE_SYS + """
Additional instructions for WEBCAM FIX mode:
- Most common causes: wrong /dev/video device, uvcvideo driver missing, another app holding the camera, PipeWire permissions.
- For 'not detected': check lsusb and /dev/video*, check if uvcvideo module is loaded.
- For 'black screen in app': check if another app is using the camera (fuser), check PipeWire/permissions.
- For 'wrong camera': most apps let you select camera in settings — guide through that first before touching drivers.
- v4l2-ctl can test camera: explain as 'a tool to check if your camera is working at the system level'.
- Explain /dev/video0 as 'the address Linux gives your camera'.
- For Zoom/Teams/Meet: often a browser permission issue first — guide through that before system changes.
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE 27: App Switcher — Linux equivalents ──────────────────────────────
def feat_appswitch(backend, bctx, slog):
    hdr("App Finder — Find Linux alternatives to Windows/Mac apps")
    try:
        app = input(f"\n{BOLD}What app or software are you looking for?{R}\n"
                    f"{C('(e.g. Photoshop, Microsoft Word, After Effects, iTunes, Notepad++)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not app or _is_back(app):
        return
    sys_p = BASE_SYS + """
Additional instructions for APP FINDER mode:
- The user is switching from Windows or Mac and needs Linux equivalents.
- For each recommendation: explain what it is, how similar it is to the original, and how to install it.
- Recommend FREE and open source options first, then mention any paid options if much better.
- Be honest about gaps — if Linux doesn't have a perfect equivalent, say so clearly and suggest the best alternative.
- For creative apps (Photoshop, Premiere, etc.): recommend GIMP, Inkscape, Kdenlive etc. but acknowledge the learning curve honestly.
- For Office apps: LibreOffice is usually the answer — explain it handles .docx/.xlsx files.
- For gaming: mention Steam, Proton compatibility, and Lutris where relevant.
- For proprietary apps with no Linux version: mention browser-based alternatives or running via Wine/Bottles.
- After recommending, provide the install command for the top recommendation automatically as the first step.
- Keep a positive, encouraging tone — Linux has great software, just sometimes different names.
""" + _sys_ctx_block(bctx)
    fix_engine(backend, sys_p, [{"role": "user", "content":
        f"I used to use '{app}' on Windows/Mac. What should I use on Linux? "
        f"Please recommend the best alternatives and help me install the top one."}], slog)

# ── FEATURE 28: Battery & Power Management ────────────────────────────────────
def feat_battery(backend, bctx, slog):
    hdr("Battery & Power — Improve battery life & power settings")
    with Spinner("Reading power info…"):
        ctx = {**bctx, **_parallel_ctx({
            "battery":       "upower -i $(upower -e | grep battery) 2>/dev/null",
            "power_profile": "powerprofilesctl status 2>/dev/null || tlp-stat -s 2>/dev/null | head -10",
            "tlp":           "systemctl status tlp 2>/dev/null | head -6",
            "thermald":      "systemctl status thermald 2>/dev/null | head -6",
            "cpu_governor":  "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null",
            "cpu_freq":      "cat /proc/cpuinfo | grep 'cpu MHz' | head -4 2>/dev/null",
            "temps":         "sensors 2>/dev/null | grep -iE 'core|package|temp' | head -8",
            "power_supply":  "ls /sys/class/power_supply/ 2>/dev/null",
            "screen_bright": "cat /sys/class/backlight/*/brightness 2>/dev/null | head -3",
            "wake_locks":    "cat /sys/kernel/debug/wakeup_sources 2>/dev/null | head -10",
            "suspend_mode":  "cat /sys/power/state 2>/dev/null",
        })}
    try:
        problem = input(f"\n{BOLD}What's the power/battery issue? (or Enter for general optimisation):{R}\n"
                        f"{C('(e.g. battery drains fast, laptop overheating, wont sleep, screen brightness)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "Optimise my laptop's battery life and power settings."
    sys_p = BASE_SYS + """
Additional instructions for BATTERY & POWER mode:
- Most impactful fixes: install TLP (background power manager), set CPU governor to powersave, reduce screen brightness.
- Explain TLP as 'a background program that automatically saves battery — you install it and forget it'.
- For overheating: thermald and CPU frequency scaling are the main tools.
- For 'won't sleep': check power settings, logind.conf, and any wake locks.
- For battery health: explain charge cycles and capacity fade in plain terms.
- Power profiles daemon (if present) is the modern way — explain 'power saver', 'balanced', 'performance' modes.
- Explain CPU governor simply: 'performance = full speed always, powersave = slows down when idle to save battery'.
- Always install TLP if not present on laptops — it's one of the best Linux battery improvements.
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE 31: Gaming Setup ──────────────────────────────────────────────────
def feat_gaming_setup(backend, bctx, slog):
    hdr("Gaming Setup — Get your PC ready to game on Linux")
    with Spinner("Checking your graphics & gaming readiness…"):
        ctx = {**bctx, **_parallel_ctx({
            "gpu":          "lspci | grep -iE 'vga|3d|display'",
            "gl_renderer":  "glxinfo 2>/dev/null | grep -i 'opengl renderer' | head -1",
            "gl_version":   "glxinfo 2>/dev/null | grep -i 'opengl version' | head -1",
            "vulkan":       "vulkaninfo --summary 2>/dev/null | grep -iE 'deviceName|driverName|apiVersion' | head -8",
            "nvidia":       "nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null",
            "steam":        "command -v steam >/dev/null && echo installed || echo missing",
            "gamemode":     "command -v gamemoded >/dev/null && echo installed || echo missing",
            "mangohud":     "command -v mangohud >/dev/null && echo installed || echo missing",
            "gamescope":    "command -v gamescope >/dev/null && echo installed || echo missing",
            "flatpak":      "command -v flatpak >/dev/null && (flatpak remotes 2>/dev/null | grep -qi flathub && echo 'flatpak+flathub' || echo 'flatpak-no-flathub') || echo 'no-flatpak'",
            "controllers":  "ls /dev/input/js* 2>/dev/null; lsusb | grep -iE 'controller|gamepad|xbox|playstation|sony|8bitdo|nintendo|logitech' | head -5",
            "multilib":     "dpkg --print-foreign-architectures 2>/dev/null; grep -h '^\\[multilib\\]' /etc/pacman.conf 2>/dev/null",
            "cpu_governor": "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null",
            "mem":          "free -h | awk '/Mem:/{print $2}'",
            "kernel":       "uname -r",
        })}
    try:
        want = input(f"\n{BOLD}What do you want to set up? (Enter = full game-ready setup · 'q' = back):{R}\n"
                     f"{C('(e.g. install Steam, enable Proton, fix my GPU drivers, set up my controller)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not want:
        want = "Get this machine fully ready for gaming on Linux."
    sys_p = BASE_SYS + """
Additional instructions for GAMING SETUP mode:
- Goal: make the machine game-ready. Detect the GPU vendor from the context and act accordingly:
  * NVIDIA → install the proprietary driver for this distro (e.g. nvidia-driver / nvidia on the distro's recommended channel) and the 32-bit libs; explain a reboot is needed.
  * AMD / Intel → the open Mesa stack is best; ensure Mesa + Vulkan (mesa-vulkan-drivers / vulkan-radeon / vulkan-intel) and the 32-bit variants are installed.
- Enable 32-bit support where the distro needs it (dpkg --add-architecture i386 on Debian/Ubuntu; the [multilib] repo on Arch) — many games and Proton need it.
- Install Steam. Explain that Steam Play / Proton is enabled inside Steam: Settings → Compatibility → "Enable Steam Play for all other titles" — this is a GUI toggle the user does once (you cannot flip it from the terminal), so guide them clearly.
- Install performance helpers: GameMode (gamemode) and MangoHud (mangohud, the FPS/temperature overlay). Mention gamescope for a gaming session/upscaling on Wayland if relevant.
- Controllers usually work out of the box via the kernel. For Xbox controllers over Bluetooth, xpadneo improves support — offer it. For 8BitDo/PlayStation, note they generally work; suggest testing with an evtest/jstest.
- Point the user to Heroic (Epic/GOG), Lutris, and Bottles for non-Steam games (they're in the app catalog [77] under Gaming), and to protondb.com to check how a specific game runs.
- For free/open-source games, mention they can install titles like SuperTuxKart, 0 A.D., or Veloren from the app catalog [77].
- Prefer the distro's package manager; use Flathub for GUI tools when that's the cleanest path. Keep each step explained in plain language — many gamers are new to Linux.
- Do NOT attempt to download or install pirated games, ROMs, or commercial titles directly; those come from stores the user owns.
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":want}], slog)

# ── FEATURE 22: Sound Fix ────────────────────────────────────────────────────
def feat_sound(backend, bctx, slog):
    hdr("Sound Fix — Fix audio problems")
    with Spinner("Checking audio system…"):
        ctx = {**bctx, **_parallel_ctx({
            "audio_hw":       "lspci | grep -i audio 2>/dev/null",
            "usb_audio":      "lsusb | grep -i audio 2>/dev/null",
            "alsa_devices":   "aplay -l 2>/dev/null",
            "alsa_controls":  "amixer scontrols 2>/dev/null | head -20",
            "pulse_info":     "pactl info 2>/dev/null",
            "pulse_sinks":    "pactl list sinks short 2>/dev/null",
            "pulse_sources":  "pactl list sources short 2>/dev/null",
            "pipewire_ver":   "pipewire --version 2>/dev/null",
            "pw_status":      "systemctl --user status pipewire 2>/dev/null | head -6",
            "pa_status":      "systemctl --user status pulseaudio 2>/dev/null | head -6",
            "default_sink":   "pactl get-default-sink 2>/dev/null",
            "default_source": "pactl get-default-source 2>/dev/null",
            "dmesg_audio":    "dmesg | grep -iE 'audio|sound|snd_|hdmi' | tail -10 2>/dev/null",
            "loaded_modules": "lsmod | grep snd | head -15",
        })}
    try:
        problem = input(f"\n{BOLD}What's the audio problem? (or press Enter for general fix):{R}\n"
                        f"{C('(e.g. no sound, mic not working, HDMI audio, crackling noise)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "Audio is not working. Diagnose and fix the issue."
    sys_p = BASE_SYS + """
Additional instructions for SOUND FIX mode:
- Most common causes: wrong output device selected, audio service not running, channels muted, missing driver.
- Check if PipeWire or PulseAudio is in use and troubleshoot accordingly.
- For 'no sound': verify correct output device is selected, check mute state, check service status.
- For 'mic not working': check input sources, check if muted in amixer/pavucontrol.
- For HDMI audio: check if HDMI sink appears in pactl and explain how to switch to it.
- Prefer restarting just the audio service over rebooting.
- Translate jargon: say "sound card" not "ALSA device", "audio service" not "PulseAudio daemon", "output device" not "sink".
- Commands like pactl set-default-sink and amixer sset are safe and reversible.
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE 23: Display Fix ───────────────────────────────────────────────────
def feat_display(backend, bctx, slog):
    hdr("Display Fix — Fix screen & monitor problems")
    with Spinner("Checking display setup…"):
        ctx = {**bctx, **_parallel_ctx({
            "xrandr_full":    "xrandr 2>/dev/null",
            "monitors":       "xrandr --listmonitors 2>/dev/null",
            "connected":      "xrandr 2>/dev/null | grep ' connected'",
            "gpu_info":       "lspci | grep -iE 'vga|3d|display|graphics' 2>/dev/null",
            "nvidia_smi":     "nvidia-smi 2>/dev/null | head -8",
            "session_type":   "echo ${XDG_SESSION_TYPE:-unknown}",
            "desktop":        "echo ${XDG_CURRENT_DESKTOP:-unknown}",
            "resolution":     "xdpyinfo 2>/dev/null | grep -i dimensions",
            "xorg_errors":    "grep -E '\\(EE\\)|\\(WW\\)' /var/log/Xorg.0.log 2>/dev/null | tail -15",
            "dmesg_gpu":      "dmesg | grep -iE 'drm|nvidia|amdgpu|i915|radeon' | tail -15 2>/dev/null",
            "gpu_driver":     "glxinfo 2>/dev/null | grep -iE 'renderer|vendor' | head -3",
            "wayland_disp":   "wayland-info 2>/dev/null | head -10",
        })}
    try:
        problem = input(f"\n{BOLD}What's the display problem? (or press Enter for general fix):{R}\n"
                        f"{C('(e.g. wrong resolution, second monitor not detected, HDMI not working, screen too small)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "Diagnose display setup and fix any issues found."
    sys_p = BASE_SYS + """
Additional instructions for DISPLAY FIX mode:
- Common issues: wrong resolution, external monitor not detected, HDMI/DisplayPort not working, scaling/DPI, GPU driver problems.
- Check if Wayland or X11 is in use — xrandr only works on X11; Wayland needs different tools.
- For resolution: use xrandr to list and set modes; explain modes in plain English (e.g. "1920x1080 is Full HD").
- For second monitor not detected: check xrandr output; if not listed, may need GPU driver fix.
- For HDMI: if not in xrandr output, suspect driver issue; if listed but blank, try xrandr --auto.
- For scaling/HiDPI: explain GDK_SCALE, QT_SCALE_FACTOR in plain English ("makes everything bigger").
- NEVER remove GPU drivers without a fallback plan — user could lose their display entirely.
- Explain terms simply: "display driver" not "DRM/KMS", "screen refresh rate" not "Hz modeline".
""" + _sys_ctx_block(ctx)
    fix_engine(backend, sys_p, [{"role":"user","content":problem}], slog)

# ── FEATURE: Self-Update ──────────────────────────────────────────────────────
_UPDATE_URL = "https://api.github.com/repos/ramchandragada/tuxgenie/releases/latest"

def feat_self_update():
    """Check for a newer TuxGenie release and install it automatically."""
    hdr("Update TuxGenie — Check for newer version")
    print(f"\n  Installed version: {CYAN}{BOLD}v{__version__}{R}")
    print(f"  {DIM}Checking for updates…{R}", flush=True)

    try:
        req = urllib.request.Request(
            _UPDATE_URL, headers={"User-Agent": f"TuxGenie/{__version__}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        latest = data.get("tag_name", "").lstrip("v").strip()
        notes  = _strip_md((data.get("body") or "")[:400].strip())
        deb_url = deb_name = deb_digest = None
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith("_all.deb"):
                deb_url    = asset["browser_download_url"]
                deb_name   = asset["name"]
                deb_digest = asset.get("digest")   # "sha256:..." from GitHub
                break

        if not latest:
            warn("Could not read version from server."); return

        if _ver(latest) <= _ver(__version__):
            ok(f"You are already on the latest version (v{__version__}). Nothing to do!")
            # Clear cache so startup check doesn't nag
            _save_update_cache({"last_check": time.time(), "latest": latest})
            return

        print(f"\n  {GREEN}{BOLD}New version available: v{latest}{R}")
        if notes:
            print(f"\n  {DIM}What's new:\n  {notes}{R}")

        if not deb_url:
            warn("No .deb found in the release — please update manually.")
            info(f"Download: {BLUE}{BOLD}www.tuxgenie.com{R}  or  https://github.com/ramchandragada/tuxgenie/releases/latest")
            return

        try:
            ans = input(f"\n  Update now? [{C('y',GREEN,BOLD)} = yes  {C('n',RED,BOLD)} = later]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ans not in ("y", "yes"):
            info("Update cancelled. Run option [u] anytime to update later."); return

        _do_update_install(deb_url, deb_name, latest, deb_digest)

    except urllib.error.URLError:
        warn("Could not reach the update server — check your internet connection.")
        info(f"Download at: {BLUE}{BOLD}www.tuxgenie.com{R}")
    except Exception as e:
        warn(f"Update check failed: {e}")

# ── Startup update check ─────────────────────────────────────────────────────
_UPDATE_CACHE = os.path.join(CFG_DIR, "update_check.json")

def _strip_md(text: str) -> str:
    """Remove common markdown so release notes display cleanly in a terminal."""
    text = re.sub(r'```[a-z]*\n?', '', text)        # fenced code blocks
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # headings
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)    # bold
    text = re.sub(r'\*(.+?)\*',   r'\1', text)       # italic
    text = re.sub(r'`(.+?)`',     r'\1', text)        # inline code
    text = re.sub(r'^\s*[-*]\s+', '· ', text, flags=re.MULTILINE)  # bullets
    text = re.sub(r'\n{3,}', '\n\n', text)           # collapse blank lines
    return text.strip()

def _ver(v):
    """Parse a version string into a comparable int tuple.
    '4.1.0' → (4,1,0); tolerates suffixes like '5.80.0-rc1' → (5,80,0)
    instead of collapsing the whole thing to (0,) and hiding a real update."""
    try:
        parts = []
        for seg in str(v).strip().lstrip("v").split("."):
            m = re.match(r"\d+", seg)
            parts.append(int(m.group()) if m else 0)
        return tuple(parts) if parts else (0,)
    except Exception:
        return (0,)

def _version_gap(current, latest):
    """Return how big the update is: major bump ≥ 10 (forced), minor ≥ 1, patch 1.
    4.2.0→4.2.1 = 1, 4.1→4.2 = 1, 4.0→4.2 = 2, 4.0→5.0 = 10, 5.79.0→6.0.0 = 10.

    Must be monotonic in severity: a major bump ALWAYS outranks any minor/patch
    delta, even when the new minor is numerically smaller (5.79.0 → 6.0.0). The
    old additive formula let the negative minor delta cancel the major gap, so
    every user was silently stranded when the next major line shipped."""
    c, l = _ver(current), _ver(latest)
    if l <= c:
        return 0
    # Pad to 3 elements
    c = c + (0,) * (3 - len(c))
    l = l + (0,) * (3 - len(l))
    if l[0] != c[0]:                       # any major bump → forced-update range
        return max((l[0] - c[0]) * 10, 10)
    if l[1] != c[1]:                       # minor bump
        return max(l[1] - c[1], 1)
    return 1                               # patch-only (l > c already guaranteed)

def _load_update_cache():
    """Load last update check result from disk."""
    try:
        with open(_UPDATE_CACHE) as f:
            return json.load(f)
    except Exception:
        return {}

def _save_update_cache(data):
    """Save update check result to disk."""
    try:
        os.makedirs(CFG_DIR, exist_ok=True)
        with open(_UPDATE_CACHE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def _download_verified(url, dest, expected_digest=None, progress=False):
    """Stream `url` to `dest`, verifying completeness and (when provided) a
    GitHub 'sha256:...' asset digest before the file is ever handed to dpkg.
    Returns (True, "") on success or (False, reason). This is the gate that
    stops a truncated download or a tampered/redirected payload from being
    installed as root."""
    import hashlib
    h = hashlib.sha256()
    total = 0
    done = 0
    try:
        with urllib.request.urlopen(url, timeout=60) as resp, open(dest, "wb") as out:
            total = int(resp.headers.get("Content-Length", 0) or 0)
            last_pct = -1
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if progress and total > 0:
                    pct = min(100, int(done * 100 / total))
                    if pct != last_pct:
                        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                        print(f"\r  {CYAN}{bar}{R} {pct}%", end="", flush=True)
                        last_pct = pct
        if progress and total > 0:
            print()
    except Exception as e:
        return False, f"download error: {e}"
    # Completeness — a partial download must never reach dpkg.
    if total > 0 and done != total:
        return False, f"incomplete download ({done}/{total} bytes)"
    if done == 0:
        return False, "empty download"
    # Authenticity/integrity — must match the release's published SHA-256.
    if expected_digest:
        want = expected_digest.split(":", 1)[-1].strip().lower()
        got  = h.hexdigest().lower()
        if want and want != got:
            return False, f"checksum mismatch (expected {want[:12]}…, got {got[:12]}…)"
    return True, ""


def _try_silent_update(deb_url, deb_name, latest, expected_digest=None) -> bool:
    """Attempt a fully silent auto-update using cached sudo credentials.

    Uses `sudo -n` (non-interactive) so it never prompts for a password.
    Returns True and re-execs if successful; returns False to let the caller
    fall back to the interactive prompt.
    """
    # Reject anything that isn't a plain semver — defence against a tampered API response
    if not re.match(r'^\d+\.\d+\.\d+$', latest):
        return False
    # Test whether sudo is usable without a password right now
    probe = subprocess.run(
        ["sudo", "-n", "true"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if probe.returncode != 0:
        return False   # no cached credentials — caller will prompt

    # Non-deb systems: try pip install --user (no sudo needed)
    if not shutil.which("dpkg"):
        rc = subprocess.run(
            ["pip3", "install", f"tuxgenie=={latest}",
             "--quiet", "--user", "--break-system-packages"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        if rc != 0:
            rc = subprocess.run(
                ["pip3", "install", f"tuxgenie=={latest}", "--quiet", "--user"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ).returncode
        if rc == 0:
            print(f"\n  {GREEN}{BOLD}🎉 Auto-updated to v{latest}!{R}  {DIM}Restarting…{R}\n")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        return rc == 0

    # Deb systems: download to a unique temp file, VERIFY, then sudo -n dpkg -i
    import tempfile
    fd, tmp_deb = tempfile.mkstemp(suffix=".deb", prefix="tuxgenie_upd_")
    os.close(fd)
    okdl, reason = _download_verified(deb_url, tmp_deb, expected_digest)
    if not okdl:
        # A silent update must never install an unverified/partial file.
        try: os.unlink(tmp_deb)
        except OSError: pass
        return False

    _save_version_backup()   # save current version before replacing
    rc = subprocess.run(
        ["sudo", "-n", "dpkg", "-i", tmp_deb],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode
    try: os.unlink(tmp_deb)
    except OSError: pass

    if rc == 0:
        print(f"\n  {GREEN}{BOLD}🎉 Auto-updated to v{latest}!{R}  {DIM}Restarting…{R}\n")
        os.execv(sys.executable, [sys.executable] + sys.argv)
    return rc == 0


def _do_update_install(deb_url, deb_name, latest, expected_digest=None):
    """Download and install a .deb update, or pip upgrade on non-deb systems."""
    # Validate version string before using it anywhere to prevent injection
    if not re.match(r'^\d+\.\d+\.\d+$', latest):
        err(f"Update server returned an invalid version string: {latest!r}")
        return False

    # Non-deb systems (Fedora, Arch, openSUSE, etc.) — upgrade via pip
    if not shutil.which("dpkg"):
        print(f"\n  {CYAN}▶ Upgrading via pip (non-deb system)…{R}")
        pkg = f"tuxgenie=={latest}"
        # Use list-form (no shell=True) to prevent injection via the version string
        rc = subprocess.run(
            ["pip3", "install", pkg, "--break-system-packages"],
            capture_output=True).returncode
        if rc != 0:
            rc = subprocess.run(
                ["pip3", "install", pkg],
                capture_output=True).returncode
        if rc == 0:
            print(f"\n  {GREEN}{BOLD}🎉 TuxGenie updated to v{latest}!{R}")
            print(f"  {YELLOW}Restarting TuxGenie…{R}\n")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            err("pip upgrade failed.")
            info("Try manually:  pip3 install --upgrade tuxgenie")
        return rc == 0

    # Use mkstemp for a unique, non-guessable temp path to prevent TOCTOU attacks
    # where a local attacker could pre-create /tmp/<predictable_name>.deb
    import tempfile
    fd, tmp_deb = tempfile.mkstemp(suffix=".deb", prefix="tuxgenie_upd_")
    os.close(fd)
    print(f"\n  {CYAN}▶ Downloading v{latest}…{R}", flush=True)
    okdl, reason = _download_verified(deb_url, tmp_deb, expected_digest, progress=True)
    if not okdl:
        try: os.unlink(tmp_deb)
        except OSError: pass
        err(f"Download failed — not installing: {reason}")
        info("This can be a flaky connection or a bad mirror. Try again, or "
             "download manually from www.tuxgenie.com")
        return False
    if expected_digest:
        ok(f"Downloaded {deb_name}  {DIM}(SHA-256 verified){R}")
    else:
        ok(f"Downloaded {deb_name}")
    _save_version_backup()   # save current version before replacing

    print(f"\n  {CYAN}▶ Installing v{latest}…{R}")
    try:
        inst_pw = get_or_cache_sudo_password()
    except KeyboardInterrupt:
        try: os.unlink(tmp_deb)
        except OSError: pass
        warn("Installation cancelled."); return False
    rc, _, _ = run_cmd_live(f"sudo dpkg -i {shlex.quote(tmp_deb)}", sudo_password=inst_pw)
    try: os.unlink(tmp_deb)
    except OSError: pass
    if rc == 0:
        print(f"\n  {GREEN}{BOLD}🎉 TuxGenie updated to v{latest}!{R}")
        print(f"  {YELLOW}Restarting TuxGenie…{R}\n")
        # Re-exec ourselves so the new version takes over
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        err("Installation failed.")
        info(f"Try manually:  sudo dpkg -i {tmp_deb}")
        return False

def startup_update_check():
    """Check for updates on startup. Runs at most once per day.
    - 1 minor version behind → recommend update (yellow banner)
    - 2+ minor versions behind → force update (red banner, blocks until updated)
    - Offline → skip silently, never block the user
    """
    # Check cache — only hit the network once every 4 hours
    cache = _load_update_cache()
    last_check = cache.get("last_check", 0)
    now = time.time()
    cache_ttl = 14400  # 4 hours — catches new releases quickly without hammering API

    if now - last_check < cache_ttl and cache.get("latest"):
        # Use cached result
        latest     = cache["latest"]
        deb_url    = cache.get("deb_url")
        deb_name   = cache.get("deb_name")
        deb_digest = cache.get("deb_digest")
        notes      = cache.get("notes", "")
    else:
        # Fetch from GitHub (with short timeout to not slow startup)
        try:
            req = urllib.request.Request(
                _UPDATE_URL,
                headers={"User-Agent": f"TuxGenie/{__version__}"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            latest = data.get("tag_name", "").lstrip("v").strip()
            notes  = _strip_md((data.get("body") or "")[:300].strip())
            deb_url = deb_name = deb_digest = None
            for asset in data.get("assets", []):
                if asset.get("name", "").endswith("_all.deb"):
                    deb_url    = asset["browser_download_url"]
                    deb_name   = asset["name"]
                    deb_digest = asset.get("digest")   # "sha256:..." from GitHub
                    break
            # Save to cache
            _save_update_cache({
                "last_check": now, "latest": latest,
                "deb_url": deb_url, "deb_name": deb_name,
                "deb_digest": deb_digest, "notes": notes,
            })
        except Exception:
            # Offline or server error — skip silently, never block the user
            return

    if not latest:
        return

    gap = _version_gap(__version__, latest)

    if gap <= 0:
        return  # Already up to date

    # ── 1 minor version behind: try silent auto-update first ──────────────────
    if gap == 1:
        if deb_url and deb_name:
            # Silent path: works when sudo credentials are cached (15-min window)
            if _try_silent_update(deb_url, deb_name, latest, deb_digest):
                return  # re-exec already happened inside _try_silent_update
        # Silent update wasn't possible — show the yellow banner and ask
        print(f"\n  {YELLOW}{BOLD}┌─────────────────────────────────────────────┐{R}")
        print(f"  {YELLOW}{BOLD}│  Update available: v{__version__} → v{latest:<10s}      │{R}")
        print(f"  {YELLOW}{BOLD}└─────────────────────────────────────────────┘{R}")
        if notes:
            print(f"  {DIM}{notes[:150]}{R}")
        if deb_url and deb_name:
            try:
                ans = input(f"\n  Update now? [{C('y',GREEN,BOLD)} = yes  {C('Enter',DIM)} = skip]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return
            if ans in ("y", "yes"):
                _do_update_install(deb_url, deb_name, latest, deb_digest)
        else:
            info("Update: pip install --upgrade tuxgenie")
        print()
        return

    # ── 2+ minor versions behind: force update (red banner, blocks) ──
    print(f"\n  {BG_RED}{BOLD}  ┌──────────────────────────────────────────────────────┐  {R}")
    print(f"  {BG_RED}{BOLD}  │  UPDATE REQUIRED: v{__version__} → v{latest:<10s}                │  {R}")
    print(f"  {BG_RED}{BOLD}  │  Your version is {gap} releases behind.                  │  {R}")
    print(f"  {BG_RED}{BOLD}  │  Please update to continue using TuxGenie.            │  {R}")
    print(f"  {BG_RED}{BOLD}  └──────────────────────────────────────────────────────┘  {R}")
    if notes:
        print(f"  {DIM}{notes[:200]}{R}")

    if deb_url and deb_name:
        while True:
            try:
                ans = input(f"\n  {BOLD}Update now? [{C('y',GREEN,BOLD)} = yes  {C('q',RED,BOLD)} = quit]: {R}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print(f"\n  {RED}Update required to continue. Exiting.{R}")
                sys.exit(0)
            if ans in ("y", "yes"):
                # On success _do_update_install re-execs and never returns. On
                # failure it returns False — loop back and ask again instead of
                # falling through into the app on an out-of-date (blocked) version.
                _do_update_install(deb_url, deb_name, latest, deb_digest)
                print(C("  Update did not complete — let's try again.", YELLOW))
                continue
            if ans in ("q", "quit", "exit"):
                print(f"\n  {RED}Update required to continue. Exiting.{R}")
                sys.exit(0)
            print(C("  Please type y to update or q to quit.", DIM))
    else:
        err("No .deb available. Please update manually:")
        info("pip install --upgrade tuxgenie")
        info("Then restart tuxgenie.")
        sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — PROACTIVE STARTUP HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════
def quick_health_check():
    """5-second scan — warns about critical issues on startup."""
    issues = []

    # Disk > 90% — use df -P for POSIX-standard fixed columns
    try:
        for line in _r("df -Ph").splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6:
                used_pct = parts[4].replace("%", "")
                if used_pct.isdigit() and int(used_pct) >= 90:
                    issues.append(f"Disk {parts[5]} is {parts[4]} full!")
    except Exception:
        pass

    # Failed services
    failed = _r("systemctl --failed --no-pager 2>/dev/null | grep failed | wc -l").strip()
    if failed.isdigit() and int(failed) > 0:
        issues.append(f"{failed} systemd service(s) have failed")

    # High load
    try:
        load = _r("awk '{print $1}' /proc/loadavg").strip()
        cpus = _r("nproc").strip()
        if load and cpus and float(load) > float(cpus) * 2:
            issues.append(f"High load average: {load} (CPUs: {cpus})")
    except Exception:
        pass

    if issues:
        print(f"\n{BG_RED}{BOLD}  ⚠  HEALTH ALERTS  {R}")
        for i in issues:
            warn(i)
        print(C("  → Run option [2] Health Dashboard for details\n", YELLOW))

def _weekly_digest(force: bool = False):
    """Show a compact weekly health digest — auto-skips if run <7 days ago."""
    today = datetime.date.today().isoformat()
    try:
        data = json.loads(open(DIGEST_FILE).read())
        last = data.get("last_run", "")
        if not force and last:
            delta = (datetime.date.today() - datetime.date.fromisoformat(last)).days
            if delta < 7:
                return
    except Exception:
        pass

    # ── Collect metrics ────────────────────────────────────────────────────────
    # Disk — only show mounts ≥60% full (skip pseudo-filesystems)
    disk_lines = []
    try:
        for line in _r("df -Ph --output=pcent,target,size,used,avail 2>/dev/null").splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2:
                continue
            mount = parts[1] if len(parts) >= 2 else ""
            if any(skip in mount for skip in ("/proc", "/sys", "/dev", "/run", "udev", "tmpfs", "snap")):
                continue
            pct_s = parts[0].replace("%", "")
            if pct_s.isdigit() and int(pct_s) >= 60:
                col = RED if int(pct_s) >= 90 else (YELLOW if int(pct_s) >= 80 else CYAN)
                size = parts[2] if len(parts) >= 3 else "?"
                avail = parts[4] if len(parts) >= 5 else "?"
                disk_lines.append(f"{col}{mount}{R}  {parts[0]} used  ({avail} free of {size})")
    except Exception:
        pass

    # Memory
    mem_str = ""
    try:
        for line in _r("free -h").splitlines():
            if line.startswith("Mem:"):
                p = line.split()
                mem_str = f"{p[2]} / {p[1]} used"
                break
    except Exception:
        pass

    # Failed services
    failed_count = 0
    failed_names = []
    try:
        raw = _r("systemctl --failed --no-pager --no-legend 2>/dev/null").strip()
        for line in raw.splitlines():
            if "failed" in line.lower():
                failed_count += 1
                name = line.split()[0] if line.split() else ""
                if name:
                    failed_names.append(name)
    except Exception:
        pass

    # Pending updates
    updates = 0
    try:
        out = _r("apt list --upgradable 2>/dev/null").strip()
        updates = max(0, len([l for l in out.splitlines() if "/" in l]))
    except Exception:
        pass

    # Uptime
    uptime_str = ""
    try:
        uptime_str = _r("uptime -p").strip().replace("up ", "")
    except Exception:
        pass

    # ── Print digest ──────────────────────────────────────────────────────────
    bar = "─" * 56
    week_label = datetime.date.today().strftime("%B %d, %Y")
    print(f"\n  {BOLD}{BMAGENTA}📊 Weekly Health Digest{R}  {DIM}{week_label}{R}")
    print(f"  {DIM}{bar}{R}")

    # Disk
    if disk_lines:
        print(f"  {BOLD}Disk{R}")
        for dl in disk_lines:
            print(f"    {dl}")
    else:
        print(f"  {BOLD}Disk{R}      {GREEN}All partitions below 60%{R}")

    # Memory
    if mem_str:
        print(f"  {BOLD}Memory{R}    {mem_str}")

    # Services
    if failed_count:
        names = ", ".join(failed_names[:3]) + ("…" if len(failed_names) > 3 else "")
        print(f"  {BOLD}Services{R}  {RED}{failed_count} failed:{R} {names}")
        print(f"            {DIM}→ Run option [2] Health Dashboard to investigate{R}")
    else:
        print(f"  {BOLD}Services{R}  {GREEN}All running{R}")

    # Updates
    if updates > 0:
        col = YELLOW if updates < 20 else RED
        print(f"  {BOLD}Updates{R}   {col}{updates} package{'s' if updates != 1 else ''} pending{R}  {DIM}(run: sudo apt upgrade){R}")
    else:
        print(f"  {BOLD}Updates{R}   {GREEN}System up to date{R}")

    # Uptime
    if uptime_str:
        print(f"  {BOLD}Uptime{R}    {uptime_str}")

    # Summary line
    has_critical = any(p.replace("%","").isdigit() and int(p.replace("%","")) >= 90
                       for line in _r("df -Ph 2>/dev/null").splitlines()[1:]
                       for p in [line.split()[4] if len(line.split()) >= 5 else "0"])
    if failed_count or has_critical:
        print(f"\n  {RED}{BOLD}⚠  Issues found — run option [2] for details{R}")
    else:
        print(f"\n  {GREEN}{BOLD}✓  System looking good!{R}  {DIM}Next digest in 7 days.{R}")
    print(f"  {DIM}{bar}{R}\n")

    # Save timestamp
    try:
        with open(DIGEST_FILE, "w") as f:
            json.dump({"last_run": today}, f)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 8 — CRASH GUARD
# ═══════════════════════════════════════════════════════════════════════════════
_CRASH_THRESHOLD = 3
_SYSTEM_PY = "/usr/lib/tuxgenie/tuxgenie.py"

def _crash_read() -> dict:
    try:
        return json.loads(open(CRASH_FILE).read())
    except Exception:
        return {}

def _crash_write(data: dict):
    try:
        with open(CRASH_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def _crash_mark_clean():
    """Reset the crash counter once this version has proven it can start.

    Called from an explicit 'healthy state' checkpoint (after startup succeeds),
    NOT from atexit. atexit was wrong in both directions: it fired after a
    top-level-caught crash (resetting the counter so real startup crashes never
    reached the rollback threshold), and it did NOT fire on SIGTERM/SIGHUP
    (closing the terminal), so benign exits were miscounted as crashes."""
    data = _crash_read()
    if data.get("version") == __version__ and data.get("crashes", 0):
        data["crashes"] = 0
        _crash_write(data)

def _save_version_backup():
    """Copy the running tuxgenie.py to PREV_VER_BAK before an update."""
    src = _SYSTEM_PY if os.path.exists(_SYSTEM_PY) else os.path.abspath(__file__)
    try:
        import shutil as _sh
        _sh.copy2(src, PREV_VER_BAK)
    except Exception:
        pass

def _crash_guard():
    """Call at startup. Increments the crash counter; triggers rollback at the
    threshold. The counter is cleared later by _crash_mark_clean() once the app
    reaches a healthy interactive state — so only crashes that happen DURING
    startup (a genuinely broken version) ever accumulate toward a rollback."""
    data = _crash_read()
    ver  = data.get("version", "")
    crashes = data.get("crashes", 0)

    if ver != __version__:
        # New version just installed — start fresh counter
        _crash_write({"version": __version__, "crashes": 1})
        return

    crashes += 1
    _crash_write({"version": __version__, "crashes": crashes})

    if crashes < _CRASH_THRESHOLD:
        return

    # ── 3 consecutive crashes — roll back ────────────────────────────────────
    sys.stdout.write("\033[0m\n")   # reset terminal in case theme wasn't set yet
    print(f"\n  ⚠  TuxGenie v{__version__} has crashed {crashes} times in a row.")
    print(f"  Rolling back to the previous version automatically…\n")

    if not os.path.exists(PREV_VER_BAK):
        print(f"  No backup found at {PREV_VER_BAK}.")
        _crash_write({"version": __version__, "crashes": 0})   # prevent infinite loop
        print(f"  Run:  tuxgenie-update   to reinstall the latest version.")
        sys.exit(1)

    # Verify the backup actually compiles before clobbering the current install
    # — otherwise we trade a crashing version for a syntactically-broken one.
    try:
        py_compile_check = subprocess.run(
            [sys.executable, "-m", "py_compile", PREV_VER_BAK],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if py_compile_check.returncode != 0:
            print(f"  Backup at {PREV_VER_BAK} has syntax errors — refusing to roll back.")
            print(f"  Run:  tuxgenie-update   to reinstall the latest version.")
            _crash_write({"version": __version__, "crashes": 0})   # prevent infinite loop
            sys.exit(1)
    except Exception:
        # If the compile check itself fails, fall through to the rollback —
        # corrupted python install is its own problem.
        pass

    # Try sudo -n (cached credentials)
    probe = subprocess.run(["sudo", "-n", "true"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode == 0:
        rc = subprocess.run(
            ["sudo", "-n", "cp", PREV_VER_BAK, _SYSTEM_PY],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        if rc == 0:
            # Reset counter for the backup version so it gets a fresh start
            _crash_write({"version": "rollback", "crashes": 0})
            print(f"  ✓  Rolled back. Restarting TuxGenie…\n")
            os.execv(sys.executable, [sys.executable] + sys.argv)

    # sudo not available — give the user the manual command.
    # Reset the crash counter so next run gets a clean start — otherwise
    # the guard would fire again immediately and tuxgenie would be permanently
    # locked out on machines without cached sudo credentials.
    _crash_write({"version": __version__, "crashes": 0})
    print(f"  Could not auto-rollback (sudo credentials not cached).")
    print(f"  Run this to fix it:")
    print(f"\n    sudo cp {PREV_VER_BAK} {_SYSTEM_PY}\n")
    print(f"  Then run: tuxgenie")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 9 — SESSION SAVE
# ═══════════════════════════════════════════════════════════════════════════════
def save_session(slog: list):
    if not slog:
        return
    ts  = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = os.path.join(SESSIONS_DIR, f"{ts}.json")
    with open(out,"w") as f:
        json.dump({"timestamp":ts,"commands":slog}, f, indent=2)

def _history_append(task: str, feature: str):
    """Append one interaction to the persistent history log (capped at 50)."""
    if load_cfg().get("disable_history"):
        return
    try:
        try:
            entries = json.loads(open(HISTORY_FILE).read())
        except Exception:
            entries = []
        entries.append({
            "ts":      datetime.datetime.now().strftime("%b %d  %H:%M"),
            "task":    task.strip()[:80],
            "feature": feature,
        })
        entries = entries[-50:]
        with open(HISTORY_FILE, "w") as f:
            json.dump(entries, f)
    except Exception:
        pass


def _action_log_append(command: str, exit_code: int, source: str = "agentic"):
    """Append a single command execution to the persistent action log.
    Logs ONLY: timestamp, command (truncated), exit code, source.
    Never logs command output or file contents — privacy first.
    Capped at 200 entries; honours the disable_history config flag."""
    if load_cfg().get("disable_history"):
        return
    if not command or not command.strip():
        return
    try:
        try:
            entries = json.loads(open(ACTIONS_FILE).read())
        except Exception:
            entries = []
        entries.append({
            "ts":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "cmd":  command.strip()[:200],
            "rc":   int(exit_code) if exit_code is not None else None,
            "src":  source,
        })
        entries = entries[-200:]
        with open(ACTIONS_FILE, "w") as f:
            json.dump(entries, f)
        os.chmod(ACTIONS_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def _action_log_recent(n: int = 15):
    """Return up to n most-recent action entries (newest last)."""
    try:
        entries = json.loads(open(ACTIONS_FILE).read())
        return entries[-n:]
    except Exception:
        return []


def _action_log_clear():
    """Wipe the persistent action log."""
    try:
        if os.path.exists(ACTIONS_FILE):
            os.remove(ACTIONS_FILE)
    except Exception:
        pass


def _recent_actions_block(n: int = 15) -> str:
    """Render the last n actions as a system-prompt block.
    Returns empty string if nothing to show — caller can append blindly."""
    actions = _action_log_recent(n)
    if not actions:
        return ""
    lines = []
    for a in actions:
        ts  = a.get("ts", "")
        cmd = a.get("cmd", "")
        rc  = a.get("rc", "?")
        marker = "✓" if rc == 0 else ("✗" if rc not in (0, None) else "•")
        lines.append(f"  {ts}  {marker} {cmd}")
    return ("\n\nRECENT ACTIONS (commands previously run on this system, "
            "newest last — use to avoid repeating work or to remember "
            "state from earlier sessions):\n" + "\n".join(lines))


def _recent_tasks_block(n: int = 8) -> str:
    """Render the last n user-prompt tasks as a system-prompt block."""
    try:
        entries = json.loads(open(HISTORY_FILE).read())[-n:]
    except Exception:
        return ""
    if not entries:
        return ""
    lines = [f"  {e.get('ts','')}  {e.get('task','')}" for e in entries]
    return ("\n\nRECENT TASKS (what the user has previously asked TuxGenie "
            "to do — use this for continuity):\n" + "\n".join(lines))

# ── Cross-session memory: problem → solution pairs ────────────────────────────

def _mem_load() -> dict:
    """Load cross-session memory (solved issues). Returns {solved:[...]}."""
    if load_cfg().get("disable_history"):
        return {"solved": []}
    try:
        return json.loads(open(MEMORY_FILE).read())
    except Exception:
        return {"solved": []}

def _mem_save(data: dict):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=2)
        os.chmod(MEMORY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass

def _mem_record_fix(problem: str, successful_steps: list,
                    failing_cmd: str = "", error_excerpt: str = ""):
    """Save a successfully resolved issue to cross-session memory.
    Called after the user confirms a fix worked (or verify_command passes).
    failing_cmd / error_excerpt help future signature matching when the user
    phrases the same problem differently."""
    if load_cfg().get("disable_history"):
        return
    if not problem or not successful_steps:
        return
    data    = _mem_load()
    solved  = data.get("solved", [])
    p_lower = problem.lower().strip()
    # Remove any previous entry for the same problem (keep the latest fix)
    solved  = [s for s in solved if s.get("problem", "").lower() != p_lower]
    entry = {
        "ts":      datetime.datetime.now().strftime("%Y-%m-%d"),
        "problem": problem.strip()[:120],
        "steps":   [s for s in successful_steps if s][:5],
        "hit_count": 1,
        "verified": True,
    }
    if failing_cmd:
        entry["failing_cmd"] = failing_cmd.strip()[:200]
    if error_excerpt:
        entry["error"] = error_excerpt.strip()[:400]
    solved.append(entry)
    data["solved"] = solved[-100:]   # cap at 100 resolved issues
    _mem_save(data)

def _community_fixes_load() -> list:
    """Load read-only community fixes bundled with the .deb. Never raises."""
    for p in COMMUNITY_FIXES_PATHS:
        try:
            if os.path.exists(p):
                doc = json.loads(open(p).read())
                fixes = doc.get("entries") or doc.get("solved") or []
                return [f for f in fixes if isinstance(f, dict)]
        except Exception:
            continue
    return []

def _mem_recall(problem: str):
    """Look up a strong match for `problem` across local + community memory.
    Returns the best entry if score >= 3 (or exact text match), else None.
    The caller offers to re-apply the saved fix before paying for a Claude call."""
    if load_cfg().get("disable_history"):
        return None
    if not problem:
        return None
    p_lower = problem.lower().strip()
    _STOP  = {"the","this","my","your","not","working","please","how","can",
              "why","what","make","get","run","fix","help","need","want",
              "have","been","is","are","was","it","on","in","to","a","an"}
    q_words = set(re.findall(r'\b\w{3,}\b', p_lower)) - _STOP
    if not q_words:
        return None
    local     = _mem_load().get("solved", [])
    community = _community_fixes_load()
    # Local entries win on tie — user's own machine knows its quirks best.
    candidates = [("local", e) for e in local] + [("community", e) for e in community]
    # Threshold scales with query length so a short query like "wifi broken"
    # (1–2 content words after stop-word removal) can still match, while a
    # long query needs a strong overlap to avoid false positives.
    threshold = min(3, max(1, len(q_words)))
    best = None
    best_score = 0
    for source, e in candidates:
        prob = (e.get("problem") or "").lower().strip()
        if not prob or not e.get("steps"):
            continue
        if prob == p_lower:
            return {"source": source, "entry": e, "score": 999}
        e_text = prob + " " + " ".join(e.get("steps", []))
        e_words = set(re.findall(r'\b\w{3,}\b', e_text.lower()))
        score = len(q_words & e_words)
        if score > best_score:
            best_score = score
            best = {"source": source, "entry": e, "score": score}
    return best if best and best_score >= threshold else None

def _mem_apply_recalled(recalled: dict) -> bool:
    """Run the steps from a recalled fix. Returns True if every step exits 0.
    On failure we fall back to the normal Claude-driven loop in fix_engine."""
    entry  = recalled["entry"]
    source = recalled["source"]
    steps  = [s for s in entry.get("steps", []) if s]
    if not steps:
        return False
    src_label = "your own past fix" if source == "local" else "the community knowledge base"
    print(f"\n  {GOLD}{BOLD}🧞 Genie Memory{R}")
    print(f"  {DIM}I've solved a similar problem before (from {src_label}).{R}")
    print(f"  {DIM}Saved fix:{R}")
    for i, c in enumerate(steps, 1):
        print(f"    {DIM}{i}. $ {c}{R}")
    try:
        ans = _safe_input(f"\n  Apply this saved fix? [{C('Y',GREEN,BOLD)}/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    if ans in ("n", "no"):
        info("Skipping saved fix — asking the AI fresh.")
        return False

    sudo_pw = None
    all_ok = True
    for i, cmd in enumerate(steps, 1):
        if cmd.strip().startswith("sudo") and sudo_pw is None:
            try:
                sudo_pw = get_or_cache_sudo_password()
            except KeyboardInterrupt:
                return False
        print(f"\n  {CYAN}▶ [{i}/{len(steps)}] $ {cmd}{R}")
        rc, _, _ = run_cmd_live(cmd, sudo_password=sudo_pw)
        if rc != 0:
            warn(f"Saved step failed (exit {rc}) — letting the AI take over.")
            all_ok = False
            break
    if all_ok:
        # Bump hit_count on the local copy so we can see which fixes pay off.
        if source == "local":
            try:
                data = _mem_load()
                for s in data.get("solved", []):
                    if s.get("problem") == entry.get("problem"):
                        s["hit_count"] = int(s.get("hit_count", 1)) + 1
                        s["last_used"] = datetime.datetime.now().strftime("%Y-%m-%d")
                        break
                _mem_save(data)
            except Exception:
                pass
        # Cache the last successful recall so `share-fix` knows what to share.
        try:
            cfg = load_cfg()
            cfg["last_applied_fix"] = {
                "problem": entry.get("problem", ""),
                "steps":   steps,
                "source":  source,
                "ts":      datetime.datetime.now().strftime("%Y-%m-%d"),
            }
            save_cfg(cfg)
        except Exception:
            pass
        print(f"\n  {GREEN}{BOLD}✓ Fixed using saved memory — no AI call needed.{R}")
        print(f"  {DIM}Long live Linux! 🐧{R}")
        return True
    return False

def _mem_search(query: str, n: int = 3) -> list:
    """Keyword search in solved issues. Returns up to n relevant matches."""
    data   = _mem_load()
    solved = data.get("solved", [])
    if not solved or not query:
        return []
    _STOP  = {"the","this","my","your","not","working","please","how","can",
              "why","what","make","get","run","fix","help","need","want",
              "have","been","is","are","was","it","on","in","to","a","an"}
    q_words = set(re.findall(r'\b\w{3,}\b', query.lower())) - _STOP
    if not q_words:
        return []
    scored = []
    for entry in solved:
        e_text  = (entry.get("problem", "") + " " +
                   " ".join(entry.get("steps", []))).lower()
        e_words = set(re.findall(r'\b\w{3,}\b', e_text))
        score   = len(q_words & e_words)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:n]]

def _mem_block() -> str:
    """Return a system-prompt block of previously solved issues for the AI."""
    data   = _mem_load()
    solved = data.get("solved", [])
    if not solved:
        return ""
    lines = []
    for e in solved[-10:]:   # last 10 resolved issues
        ts    = e.get("ts", "")
        prob  = e.get("problem", "")
        steps = e.get("steps", [])
        step_str = " → ".join(steps[:2]) if steps else "(fix not recorded)"
        lines.append(f"  [{ts}] {prob}  →  {step_str}")
    return ("\n\nPREVIOUSLY RESOLVED ISSUES (suggest proven fixes first when "
            "the user's problem looks familiar):\n" + "\n".join(lines))

def show_history():
    """Display the last 10 interactions."""
    try:
        entries = json.loads(open(HISTORY_FILE).read())
    except Exception:
        entries = []

    print(f"\n  {BG_NAVY}{BWHITE}{BOLD}  📋 Recent History  {R}")
    if not entries:
        print(f"\n  {DIM}No history yet — use TuxGenie to fix something first!{R}\n")
        return

    recent = list(reversed(entries[-10:]))
    print()
    for i, e in enumerate(recent, 1):
        ts      = e.get("ts", "")
        task    = e.get("task", "")
        feature = e.get("feature", "")
        num_s   = f"{i}.".ljust(4)
        feat_s  = f"  {DIM}[{feature}]{R}" if feature else ""
        print(f"  {BLUE}{BOLD}{num_s}{R}  {DIM}{ts}{R}  {BOLD}{task}{R}{feat_s}")
    print()

def feat_performance(backend, bctx, slog):
    """
    Agentic Performance Boost — collects all diagnostic data upfront (no AI),
    feeds it to Claude in one shot, applies all safe fixes, then generates
    a Warp-style before/after summary.
    """
    hdr("Performance Boost — Full System Audit")
    print(f"\n  {CYAN}{BOLD}Phase 1/3  Scanning your system…{R}  {DIM}(~5 seconds){R}\n")

    # ── Collect all diagnostics upfront (parallel, no AI needed) ──────────────
    _probes = [
        ("memory",      "free -h"),
        ("meminfo",     "grep -E 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree|Buffers:|^Cached:' /proc/meminfo"),
        ("top_mem",     "ps aux --sort=-%mem --no-headers | head -12"),
        ("top_cpu",     "ps aux --sort=-%cpu --no-headers | head -8"),
        ("load",        "uptime"),
        ("swappiness",  "sysctl vm.swappiness"),
        ("cpu_gov",     "cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null | sort | uniq -c || echo 'no cpufreq'"),
        ("on_ac",       "cat /sys/class/power_supply/AC/online 2>/dev/null || echo 'desktop'"),
        ("boot_time",   "systemd-analyze 2>/dev/null | head -2"),
        ("boot_blame",  "systemd-analyze blame 2>/dev/null | head -15"),
        ("disk",        "df -h | grep -v 'tmpfs\\|udev\\|loop'"),
        ("failed_svc",  "systemctl list-units --state=failed --no-pager 2>/dev/null | head -10"),
        ("enabled_svc", "systemctl list-unit-files --state=enabled --no-pager 2>/dev/null | grep '\\.service' | grep -v '@'"),
        ("snap",        "snap list 2>/dev/null"),
        ("apt_cache",   "du -sh /var/cache/apt/archives/ 2>/dev/null"),
        ("journal",     "journalctl --disk-usage 2>/dev/null"),
        ("zram",        "swapon --show 2>/dev/null"),
        ("iowait",      "vmstat 1 2 2>/dev/null | tail -1"),
    ]

    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(run_cmd_live, cmd, None, 8): key for key, cmd in _probes}
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                _, stdout, stderr = fut.result()
                results[key] = (stdout.strip() or stderr.strip() or "(no output)")
            except Exception:
                results[key] = "(error)"

    ok("System scan complete")

    # ── Display quick baseline summary ────────────────────────────────────────
    _mem_line = results.get("memory", "").splitlines()
    _mem_row  = next((l for l in _mem_line if l.startswith("Mem:")), "")
    _swap_row = next((l for l in _mem_line if l.startswith("Swap:")), "")
    _load     = results.get("load", "").split("load average:")[-1].strip()
    _swap_val = results.get("swappiness", "").split("=")[-1].strip()
    _boot_line = next((l for l in results.get("boot_time","").splitlines() if "graphical" in l or "reached" in l), "")

    print(f"\n  {BOLD}Baseline:{R}")
    if _mem_row:  print(f"  {DIM}RAM  {R}  {_mem_row.split()[1:6]}")
    if _swap_row: print(f"  {DIM}Swap {R}  {_swap_row.split()[1:5]}")
    if _load:     print(f"  {DIM}Load {R}  {_load}")
    if _swap_val: print(f"  {DIM}Swappiness {R}  {_swap_val}")
    if _boot_line:print(f"  {DIM}Boot {R}  {_boot_line.strip()}")

    # ── Phase 2: Feed everything to Claude ────────────────────────────────────
    print(f"\n  {CYAN}{BOLD}Phase 2/3  AI analysing bottlenecks…{R}")
    data_block = "\n\n".join(f"[{k}]\n{v}" for k, v in results.items())

    perf_prompt = f"""Make my Linux system as fast as possible.

Here is a COMPLETE live diagnostic scan collected right now:

{data_block}

Analyse every section above. Identify ALL bottlenecks. Apply every safe, reversible fix.

FIXES TO APPLY (only those actually needed based on the data):
- vm.swappiness → 10 if currently >20 AND swap is being used (persist via /etc/sysctl.d/)
- Add zram compressed swap if: swap is heavily used AND no zram exists already (use zram-config or zramctl)
- CPU governor → performance if currently powersave/ondemand AND on_ac=1 (desktop/plugged in)
- Disable NetworkManager-wait-online.service if it's in boot blame taking >3s
- Disable other slow boot services (only non-critical ones — NOT ssh, ufw, cron, NetworkManager itself)
- apt autoremove + apt clean if apt_cache is large or orphaned packages exist
- journalctl --vacuum-time=7d if journal size is >200MB
- Drop page/dentry/inode caches if memory pressure is high: echo 3 > /proc/sys/vm/drop_caches

DO NOT suggest: upgrading RAM, replacing apps, reinstalling the OS.
Set needs_synthesis: true so a full before/after summary is generated."""

    fix_engine(backend, BASE_SYS + _sys_ctx_block(bctx),
               [{"role": "user", "content": perf_prompt}], slog)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 8b — QUICK APP CATALOG (1-30 shortcuts)
# ═══════════════════════════════════════════════════════════════════════════════

# Each entry: (id, name, category, install prompt, short description).
# The prompt is fed to the agentic engine — Claude figures out apt vs snap vs
# flatpak vs vendor repo based on the user's distro & system context.
# Keep prompts short and unambiguous; let the model resolve the install method.
APP_CATALOG = [
    # ── Browsers ─────────────────────────────────────────────────────────────
    {"id": 1,  "name": "Brave Browser",       "cat": "Browsers",       "prompt": "Install Brave Browser",                                                                                                         "desc": "Privacy-focused Chromium browser"},
    {"id": 2,  "name": "Google Chrome",       "cat": "Browsers",       "prompt": "Install Google Chrome (stable)",                                                                                                "desc": "Google's web browser"},
    {"id": 3,  "name": "Mozilla Firefox",     "cat": "Browsers",       "prompt": "Install the latest Mozilla Firefox",                                                                                            "desc": "Open-source web browser"},
    {"id": 4,  "name": "Vivaldi",             "cat": "Browsers",       "prompt": "Install Vivaldi browser",                                                                                                       "desc": "Highly customisable Chromium browser"},
    {"id": 5,  "name": "Ulaa Browser",        "cat": "Browsers",       "prompt": "Install Ulaa Browser using the official installer: wget -O /tmp/install-ulaa-browser.sh 'https://ulaa.com/release/linux/stable/install-ulaa-browser.sh?isDownload=true' && bash /tmp/install-ulaa-browser.sh", "desc": "Privacy-first Indian browser by Zoho"},
    # ── Communication ────────────────────────────────────────────────────────
    {"id": 6,  "name": "Slack",               "cat": "Communication",  "prompt": "Install the Slack desktop app",                                                                                                 "desc": "Team chat and collaboration"},
    {"id": 7,  "name": "Discord",             "cat": "Communication",  "prompt": "Install Discord desktop",                                                                                                       "desc": "Voice and text chat"},
    {"id": 8,  "name": "Telegram Desktop",    "cat": "Communication",  "prompt": "Install Telegram Desktop",                                                                                                      "desc": "Fast encrypted messenger"},
    {"id": 9,  "name": "Signal Desktop",      "cat": "Communication",  "prompt": "Install Signal Desktop from the official Signal apt repository (signal.org) on Debian/Ubuntu, or flatpak from Flathub otherwise", "desc": "Private, end-to-end encrypted messaging"},
    {"id": 10, "name": "Zoom",                "cat": "Communication",  "prompt": "Install Zoom video conferencing",                                                                                               "desc": "Video meetings"},
    {"id": 11, "name": "Microsoft Teams",     "cat": "Communication",  "prompt": "Install Microsoft Teams for Linux",                                                                                             "desc": "Microsoft's team chat"},
    {"id": 12, "name": "Rambox",              "cat": "Communication",  "prompt": "Install Rambox multi-service messaging hub — download the latest .deb from https://github.com/ramboxapp/rambox/releases or use flatpak from Flathub", "desc": "All-in-one workspace for messaging apps"},
    {"id": 13, "name": "Arattai",             "cat": "Communication",  "prompt": "Install Arattai Tamil community chat app — go to https://www.arattai.in/download.html, download the Linux .deb package and install it with dpkg; fall back to AppImage if no .deb is available", "desc": "Tamil community chat app"},
    # ── Office & Notes ───────────────────────────────────────────────────────
    {"id": 14, "name": "LibreOffice",         "cat": "Office & Notes", "prompt": "Install the latest LibreOffice (full suite)",                                                                                   "desc": "Free office suite (Writer, Calc, Impress)"},
    {"id": 15, "name": "OnlyOffice",          "cat": "Office & Notes", "prompt": "Install OnlyOffice Desktop Editors",                                                                                            "desc": "Best MS Office format compatibility"},
    {"id": 16, "name": "WPS Office",          "cat": "Office & Notes", "prompt": "Install WPS Office",                                                                                                            "desc": "Strong .docx/.xlsx compatibility"},
    {"id": 17, "name": "Thunderbird",         "cat": "Office & Notes", "prompt": "Install Mozilla Thunderbird email client via apt on Debian/Ubuntu, dnf on Fedora, or flatpak from Flathub",                     "desc": "Full-featured email client"},
    {"id": 18, "name": "Obsidian",            "cat": "Office & Notes", "prompt": "Install Obsidian notes app — download the latest .deb from https://obsidian.md or use flatpak from Flathub",                   "desc": "Markdown notes / second brain"},
    {"id": 19, "name": "Joplin",              "cat": "Office & Notes", "prompt": "Install Joplin encrypted note-taking app using the official installer script from joplinapp.org",                               "desc": "Encrypted, cross-device note-taking"},
    {"id": 64, "name": "Zoho Mail",           "cat": "Office & Notes", "prompt": "Install Zoho Mail on Linux. Zoho does not ship an official native Linux desktop app, so install it as a PWA / web app: detect the user's installed browser (prefer Brave or Chrome, then Vivaldi/Ulaa, then Firefox), use Chromium-based --app=https://mail.zoho.com to create a standalone window, and write a /usr/share/applications/zoho-mail.desktop launcher with the Zoho Mail icon (download from https://www.zoho.com/mail/img/favicon.ico if no icon is bundled) so it appears in the application menu. Skip cleanly if no supported browser is installed.", "desc": "Zoho's professional email — installed as a PWA"},
    # ── Media ────────────────────────────────────────────────────────────────
    {"id": 20, "name": "VLC Media Player",    "cat": "Media",          "prompt": "Install VLC media player",                                                                                                      "desc": "Plays virtually any video/audio format"},
    {"id": 21, "name": "MPV",                 "cat": "Media",          "prompt": "Install MPV media player",                                                                                                      "desc": "Lightweight scriptable video player"},
    {"id": 22, "name": "Spotify",             "cat": "Media",          "prompt": "Install the Spotify desktop client",                                                                                            "desc": "Music streaming"},
    {"id": 23, "name": "Stremio",             "cat": "Media",          "prompt": "Install Stremio streaming hub — use flatpak from Flathub or download from https://www.stremio.com/downloads",                   "desc": "All-in-one streaming hub"},
    # ── Audio / Video Creation ───────────────────────────────────────────────
    {"id": 24, "name": "OBS Studio",          "cat": "AV Creation",    "prompt": "Install OBS Studio",                                                                                                            "desc": "Screen recording and live streaming"},
    {"id": 25, "name": "Kdenlive",            "cat": "AV Creation",    "prompt": "Install Kdenlive video editor via apt on Debian/Ubuntu, dnf on Fedora, or flatpak from Flathub",                               "desc": "Non-linear video editor"},
    {"id": 26, "name": "HandBrake",           "cat": "AV Creation",    "prompt": "Install HandBrake video transcoder via flatpak from Flathub or the official PPA on Ubuntu",                                    "desc": "Open-source video transcoder"},
    {"id": 27, "name": "Audacity",            "cat": "AV Creation",    "prompt": "Install Audacity",                                                                                                              "desc": "Audio editor and recorder"},
    # ── Graphics ────────────────────────────────────────────────────────────
    {"id": 28, "name": "GIMP",                "cat": "Graphics",       "prompt": "Install GIMP",                                                                                                                  "desc": "Image editor (Photoshop alternative)"},
    {"id": 29, "name": "Inkscape",            "cat": "Graphics",       "prompt": "Install Inkscape vector graphics editor via apt on Debian/Ubuntu or flatpak from Flathub",                                     "desc": "Vector graphics editor (Illustrator alternative)"},
    {"id": 30, "name": "Krita",               "cat": "Graphics",       "prompt": "Install Krita digital painting app via apt, snap, or flatpak from Flathub",                                                    "desc": "Professional digital painting"},
    {"id": 31, "name": "Darktable",           "cat": "Graphics",       "prompt": "Install Darktable RAW photo workflow software via apt on Debian/Ubuntu or flatpak from Flathub",                               "desc": "RAW photo editor (Lightroom alternative)"},
    {"id": 32, "name": "Blender",             "cat": "Graphics",       "prompt": "Install Blender 3D modelling software via snap (snap install blender --classic) or flatpak from Flathub",                     "desc": "3D modelling, animation, rendering"},
    # ── Remote Access ────────────────────────────────────────────────────────
    {"id": 33, "name": "AnyDesk",             "cat": "Remote Access",  "prompt": "Install AnyDesk remote desktop client",                                                                                         "desc": "Fast remote desktop access"},
    {"id": 34, "name": "TeamViewer",          "cat": "Remote Access",  "prompt": "Install TeamViewer",                                                                                                            "desc": "Remote desktop and support"},
    {"id": 35, "name": "RustDesk",            "cat": "Remote Access",  "prompt": "Install RustDesk",                                                                                                              "desc": "Open-source, self-hostable remote desktop"},
    # ── Developer Tools ──────────────────────────────────────────────────────
    {"id": 36, "name": "Visual Studio Code",  "cat": "Developer",      "prompt": "Install Visual Studio Code (VS Code)",                                                                                          "desc": "Microsoft's code editor"},
    {"id": 37, "name": "Sublime Text",        "cat": "Developer",      "prompt": "Install Sublime Text",                                                                                                          "desc": "Fast, minimal code editor"},
    {"id": 38, "name": "Git",                 "cat": "Developer",      "prompt": "Install Git version control via the system package manager and configure global user.name / user.email",                        "desc": "Version control system"},
    {"id": 39, "name": "Docker",              "cat": "Developer",      "prompt": "Install Docker Engine and the docker-compose plugin",                                                                           "desc": "Containers for development"},
    {"id": 40, "name": "Node.js (LTS)",       "cat": "Developer",      "prompt": "Install Node.js LTS via the official NodeSource repo",                                                                          "desc": "JavaScript runtime"},
    {"id": 41, "name": "DBeaver",             "cat": "Developer",      "prompt": "Install DBeaver Community Edition universal database GUI — download the .deb from dbeaver.io or use flatpak from Flathub",     "desc": "Universal database GUI"},
    {"id": 42, "name": "Bruno",               "cat": "Developer",      "prompt": "Install Bruno open-source API client from usebruno.com — download the .deb or use flatpak from Flathub",                       "desc": "Open-source API testing (Postman alternative)"},
    {"id": 43, "name": "Postman",             "cat": "Developer",      "prompt": "Install Postman API client",                                                                                                    "desc": "HTTP API testing tool"},
    {"id": 44, "name": "Kitty Terminal",      "cat": "Developer",      "prompt": "Install Kitty GPU-accelerated terminal using the official installer: curl -L https://sw.kovidgoyal.net/kitty/installer.sh | sh /dev/stdin", "desc": "Fast, GPU-accelerated terminal emulator"},
    {"id": 45, "name": "Lazygit",             "cat": "Developer",      "prompt": "Install Lazygit TUI for git — download the latest binary release from https://github.com/jesseduffield/lazygit/releases and install to /usr/local/bin", "desc": "Terminal UI for Git"},
    # ── System Tools ─────────────────────────────────────────────────────────
    {"id": 46, "name": "Timeshift",           "cat": "System Tools",   "prompt": "Install Timeshift system snapshot tool via apt (sudo apt install timeshift) on Debian/Ubuntu or dnf on Fedora",                "desc": "System snapshots & restore (like Time Machine)"},
    {"id": 47, "name": "Stacer",              "cat": "System Tools",   "prompt": "Install Stacer system optimizer — download the latest .deb from https://github.com/oguzhaninan/Stacer/releases and install it", "desc": "System optimizer, cleaner, and monitor"},
    {"id": 48, "name": "GParted",             "cat": "System Tools",   "prompt": "Install GParted partition manager via apt (sudo apt install gparted) on Debian/Ubuntu",                                         "desc": "Graphical partition editor"},
    {"id": 49, "name": "BleachBit",           "cat": "System Tools",   "prompt": "Install BleachBit system cleaner via apt (sudo apt install bleachbit) on Debian/Ubuntu or download from bleachbit.org",         "desc": "Free disk space & protect privacy"},
    {"id": 50, "name": "Synaptic",            "cat": "System Tools",   "prompt": "Install Synaptic package manager GUI via apt (sudo apt install synaptic) on Debian/Ubuntu",                                     "desc": "GUI frontend for apt"},
    # ── Files & Sync ─────────────────────────────────────────────────────────
    {"id": 51, "name": "FileZilla",           "cat": "Files & Sync",   "prompt": "Install FileZilla FTP/SFTP client via apt (sudo apt install filezilla) on Debian/Ubuntu or the system package manager",         "desc": "FTP / SFTP / FTPS client"},
    {"id": 52, "name": "Rclone",              "cat": "Files & Sync",   "prompt": "Install Rclone cloud sync tool using the official installer: curl https://rclone.org/install.sh | sudo bash",                   "desc": "Sync files to any cloud (Drive, S3, Dropbox…)"},
    {"id": 53, "name": "Nextcloud Client",    "cat": "Files & Sync",   "prompt": "Install Nextcloud desktop sync client via apt (sudo apt install nextcloud-desktop) or flatpak from Flathub",                    "desc": "Self-hosted cloud storage sync"},
    {"id": 54, "name": "qBittorrent",         "cat": "Files & Sync",   "prompt": "Install qBittorrent via apt (sudo apt install qbittorrent) on Debian/Ubuntu",                                                   "desc": "Open-source BitTorrent client"},
    {"id": 55, "name": "KeePassXC",           "cat": "Files & Sync",   "prompt": "Install KeePassXC password manager via apt (sudo apt install keepassxc) or flatpak from Flathub",                              "desc": "Offline password manager"},
    # ── Utilities ────────────────────────────────────────────────────────────
    {"id": 56, "name": "Flameshot",           "cat": "Utilities",      "prompt": "Install Flameshot screenshot tool via apt (sudo apt install flameshot) on Debian/Ubuntu",                                       "desc": "Screenshot tool with annotation"},
    {"id": 57, "name": "CopyQ",               "cat": "Utilities",      "prompt": "Install CopyQ clipboard manager via apt (sudo apt install copyq) on Debian/Ubuntu or flatpak from Flathub",                    "desc": "Advanced clipboard manager with history"},
    {"id": 58, "name": "Ventoy",              "cat": "Utilities",      "prompt": "Install Ventoy multi-ISO bootable USB creator — download the latest release from https://github.com/ventoy/Ventoy/releases, extract and run the install script", "desc": "Create multi-boot USB drives"},
    {"id": 59, "name": "Calibre",             "cat": "Utilities",      "prompt": "Install Calibre ebook management software using the official installer: wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sudo sh /dev/stdin", "desc": "Ebook library manager and converter"},
    {"id": 60, "name": "Steam",               "cat": "Utilities",      "prompt": "Install the Steam game client",                                                                                                 "desc": "Gaming platform with Proton (play Windows games)"},
    {"id": 61, "name": "btop / htop",         "cat": "Utilities",      "prompt": "Install btop and htop system monitors",                                                                                         "desc": "Beautiful real-time system monitors"},
    {"id": 62, "name": "neofetch",            "cat": "Utilities",      "prompt": "Install neofetch",                                                                                                              "desc": "System info banner on terminal launch"},
    {"id": 63, "name": "Dev Essentials Pack", "cat": "Utilities",      "prompt": "Install build-essential, curl, wget, git, unzip, htop, tree",                                                                  "desc": "Essential dev tools in one shot"},

    # ═══ Expanded catalog — verified install methods (2026) ═══════════════════
    # ── More Browsers ─────────────────────────────────────────────────────────
    {"id": 65, "name": "LibreWolf",           "cat": "Browsers",       "prompt": "Install LibreWolf, a privacy-hardened Firefox fork, via flatpak from Flathub (io.gitlab.librewolf-community). On Debian/Ubuntu the official extrepo/apt repo also works.", "desc": "Privacy-hardened Firefox fork"},
    {"id": 66, "name": "Zen Browser",         "cat": "Browsers",       "prompt": "Install Zen Browser, a calm Arc-style Firefox-based browser, via flatpak from Flathub: app.zen_browser.zen. Fall back to the official tarball from https://zen-browser.app.", "desc": "Beautiful Arc-style Firefox browser"},
    {"id": 67, "name": "Tor Browser",         "cat": "Browsers",       "prompt": "Install Tor Browser for anonymous browsing via flatpak from Flathub (org.torproject.torbrowser-launcher), or the distro's torbrowser-launcher package.", "desc": "Anonymous browsing over Tor"},
    {"id": 68, "name": "Microsoft Edge",      "cat": "Browsers",       "prompt": "Install Microsoft Edge (proprietary Chromium browser) from Microsoft's official repo at https://packages.microsoft.com/repos/edge — add the signing key and apt source, then install microsoft-edge-stable. Debian/Ubuntu only.", "desc": "Microsoft's Chromium browser (proprietary)"},
    # ── More Communication ─────────────────────────────────────────────────────
    {"id": 69, "name": "Element",             "cat": "Communication",  "prompt": "Install Element, a secure Matrix chat client, via flatpak from Flathub: im.riot.Riot. On Debian/Ubuntu the official element.io apt repo also works.", "desc": "Secure Matrix team chat"},
    {"id": 70, "name": "Ferdium",             "cat": "Communication",  "prompt": "Install Ferdium, an all-in-one hub that combines many messaging services, via flatpak from Flathub: org.ferdium.Ferdium.", "desc": "All-in-one messaging hub"},
    # ── More Office & Notes ─────────────────────────────────────────────────────
    {"id": 71, "name": "Logseq",              "cat": "Office & Notes", "prompt": "Install Logseq, a privacy-first outliner and knowledge base, via flatpak from Flathub: com.logseq.Logseq.", "desc": "Privacy-first outliner / knowledge base"},
    {"id": 72, "name": "Zotero",              "cat": "Office & Notes", "prompt": "Install Zotero reference and citation manager via flatpak from Flathub: org.zotero.Zotero.", "desc": "Reference & citation manager"},
    {"id": 73, "name": "Standard Notes",      "cat": "Office & Notes", "prompt": "Install Standard Notes, an encrypted note-taking app, via flatpak from Flathub: org.standardnotes.standardnotes.", "desc": "Encrypted, cross-device notes"},
    {"id": 74, "name": "Xournal++",           "cat": "Office & Notes", "prompt": "Install Xournal++ for handwritten notes and PDF annotation via apt (xournalpp) on Debian/Ubuntu, or flatpak from Flathub: com.github.xournalpp.xournalpp.", "desc": "Handwrite notes & annotate PDFs"},
    # ── More Media ──────────────────────────────────────────────────────────────
    {"id": 75, "name": "Jellyfin Media Player","cat": "Media",         "prompt": "Install Jellyfin Media Player, the desktop client for the open-source Jellyfin media server, via flatpak from Flathub: com.github.iwalton3.jellyfin-media-player.", "desc": "Desktop client for Jellyfin"},
    {"id": 76, "name": "Strawberry",          "cat": "Media",          "prompt": "Install Strawberry music player via apt (strawberry) on Debian/Ubuntu or flatpak from Flathub: org.strawberrymusicplayer.strawberry.", "desc": "Music player for audio collectors"},
    # ── More AV Creation ────────────────────────────────────────────────────────
    {"id": 77, "name": "Shotcut",             "cat": "AV Creation",    "prompt": "Install Shotcut, a cross-platform video editor, via flatpak from Flathub: org.shotcut.Shotcut.", "desc": "Free cross-platform video editor"},
    # ── More Graphics ───────────────────────────────────────────────────────────
    {"id": 78, "name": "Pinta",               "cat": "Graphics",       "prompt": "Install Pinta, a simple Paint.NET-style image editor, via flatpak from Flathub: com.github.PintaProject.Pinta.", "desc": "Simple image editor (Paint.NET-like)"},
    {"id": 79, "name": "digiKam",             "cat": "Graphics",       "prompt": "Install digiKam professional photo management via flatpak from Flathub: org.kde.digikam.", "desc": "Pro photo management suite"},
    {"id": 80, "name": "RawTherapee",         "cat": "Graphics",       "prompt": "Install RawTherapee RAW photo developer via flatpak from Flathub: com.rawtherapee.RawTherapee.", "desc": "RAW photo developer (Lightroom alt)"},
    {"id": 81, "name": "Scribus",             "cat": "Graphics",       "prompt": "Install Scribus open-source desktop publishing via apt (scribus) or flatpak from Flathub: net.scribus.Scribus.", "desc": "Desktop publishing (InDesign alt)"},
    {"id": 82, "name": "Upscayl",             "cat": "Graphics",       "prompt": "Install Upscayl, an AI image upscaler, via flatpak from Flathub: org.upscayl.Upscayl, or the AppImage from https://github.com/upscayl/upscayl/releases.", "desc": "AI image upscaler"},
    # ── More Developer Tools ────────────────────────────────────────────────────
    {"id": 83, "name": "Neovim",              "cat": "Developer",      "prompt": "Install Neovim. For the latest version prefer flatpak (io.neovim.nvim) or the official GitHub release; apt (neovim) works but may be older.", "desc": "Hyperextensible Vim-based editor"},
    {"id": 84, "name": "GitHub CLI (gh)",     "cat": "Developer",      "prompt": "Install the GitHub CLI (gh) from GitHub's official apt repo at https://cli.github.com/packages — add the signing key and apt source, then install gh. On Fedora use dnf, on Arch use pacman.", "desc": "GitHub from the command line"},
    {"id": 85, "name": "Insomnia",            "cat": "Developer",      "prompt": "Install Insomnia API client via flatpak from Flathub: rest.insomnia.Insomnia.", "desc": "REST/GraphQL API client (Postman alt)"},
    {"id": 86, "name": "Meld",                "cat": "Developer",      "prompt": "Install Meld visual diff and merge tool via apt (meld) or flatpak from Flathub: org.gnome.meld.", "desc": "Visual diff & merge tool"},
    {"id": 87, "name": "Zellij",              "cat": "Developer",      "prompt": "Install Zellij, a modern terminal workspace/multiplexer, using the official install script: bash <(curl -L https://zellij.dev/launch), or the prebuilt binary from https://github.com/zellij-org/zellij/releases placed in /usr/local/bin.", "desc": "Modern terminal workspace"},
    {"id": 88, "name": "Tabby Terminal",      "cat": "Developer",      "prompt": "Install Tabby, the open-source terminal & SSH client by Eugeny (NOT TabbyML). Download the latest .deb from https://github.com/Eugeny/tabby/releases and install it with apt/dpkg.", "desc": "Modern terminal & SSH client"},
    {"id": 89, "name": "JetBrains Toolbox",   "cat": "Developer",      "prompt": "Install JetBrains Toolbox (proprietary freeware manager for IntelliJ, PyCharm, etc.) — download the official tarball from https://www.jetbrains.com/toolbox-app/, extract it, and run the jetbrains-toolbox binary.", "desc": "Manager for JetBrains IDEs"},
    {"id": 90, "name": "Podman",              "cat": "Developer",      "prompt": "Install Podman, the daemonless container engine, via apt (podman) on Debian/Ubuntu or the system package manager.", "desc": "Daemonless container engine"},
    {"id": 91, "name": "Modern CLI Pack",     "cat": "Developer",      "prompt": "Install a bundle of fast modern CLI tools via the package manager: ripgrep, fd-find, bat, eza, fzf, zoxide. Note: on Debian/Ubuntu bat runs as 'batcat' and fd-find as 'fdfind'; if eza isn't in the repo, add its official repo or fetch the GitHub binary.", "desc": "ripgrep · fd · bat · eza · fzf · zoxide"},
    # ── More System Tools ───────────────────────────────────────────────────────
    {"id": 92, "name": "Flatpak + Flathub",   "cat": "System Tools",   "prompt": "Install Flatpak and enable the Flathub app store: install the flatpak package, then run flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo. Tell the user to re-login so Flathub apps appear.", "desc": "Enable the universal Flathub app store"},
    {"id": 93, "name": "GNOME Tweaks",        "cat": "System Tools",   "prompt": "Install GNOME Tweaks for advanced desktop settings via apt (gnome-tweaks) on GNOME-based systems.", "desc": "Advanced GNOME settings"},
    {"id": 94, "name": "Cockpit",             "cat": "System Tools",   "prompt": "Install Cockpit, a web-based server admin dashboard, via apt (cockpit). Afterwards tell the user to open https://localhost:9090.", "desc": "Web-based server admin dashboard"},
    {"id": 95, "name": "Fastfetch",           "cat": "System Tools",   "prompt": "Install Fastfetch (a fast neofetch replacement) via apt (fastfetch) on Ubuntu 24.04+/Debian 13+; on older releases use the PPA ppa:zhangsongcui3371/fastfetch or the GitHub .deb.", "desc": "Fast system-info banner"},
    # ── More Files & Sync ───────────────────────────────────────────────────────
    {"id": 96, "name": "Syncthing",           "cat": "Files & Sync",   "prompt": "Install Syncthing continuous file sync from the official apt repo at https://apt.syncthing.net — add the key and source, then install syncthing and enable the user service.", "desc": "Continuous peer-to-peer file sync"},
    {"id": 97, "name": "LocalSend",           "cat": "Files & Sync",   "prompt": "Install LocalSend (AirDrop-style local file sharing) via flatpak from Flathub: org.localsend.localsend_app.", "desc": "AirDrop-style local file sharing"},
    {"id": 98, "name": "Cryptomator",         "cat": "Files & Sync",   "prompt": "Install Cryptomator for encrypted cloud vaults via flatpak from Flathub: org.cryptomator.Cryptomator.", "desc": "Encrypt files before cloud upload"},
    {"id": 99, "name": "Bitwarden",           "cat": "Files & Sync",   "prompt": "Install the Bitwarden desktop password manager via flatpak from Flathub: com.bitwarden.desktop.", "desc": "Open-source password manager"},
    {"id": 100,"name": "Déjà Dup Backups",    "cat": "Files & Sync",   "prompt": "Install Déjà Dup, a simple encrypted backup tool, via apt (deja-dup) or flatpak from Flathub: org.gnome.DejaDup.", "desc": "Simple, encrypted backups"},
    # ── More Utilities ──────────────────────────────────────────────────────────
    {"id": 101,"name": "balenaEtcher",        "cat": "Utilities",      "prompt": "Install balenaEtcher to flash OS images to USB/SD cards — download the latest .deb (or AppImage) from https://github.com/balena-io/etcher/releases and install it.", "desc": "Flash OS images to USB / SD"},
    {"id": 102,"name": "Kooha",               "cat": "Utilities",      "prompt": "Install Kooha, a simple Wayland-friendly screen recorder, via flatpak from Flathub: io.github.seadve.Kooha.", "desc": "Simple screen recorder"},
    {"id": 103,"name": "Czkawka",             "cat": "Utilities",      "prompt": "Install Czkawka duplicate-file and clutter finder via flatpak from Flathub: com.github.qarmin.czkawka.", "desc": "Find duplicate files & free space"},
    {"id": 104,"name": "OnionShare",          "cat": "Utilities",      "prompt": "Install OnionShare to share files anonymously over Tor via flatpak from Flathub: org.onionshare.OnionShare, or apt (onionshare).", "desc": "Share files anonymously over Tor"},
    # ── Gaming ──────────────────────────────────────────────────────────────────
    {"id": 105,"name": "Lutris",              "cat": "Gaming",         "prompt": "Install Lutris, the open gaming platform/launcher, via flatpak from Flathub (net.lutris.Lutris) or apt (lutris).", "desc": "Open gaming platform / launcher"},
    {"id": 106,"name": "Heroic Games Launcher","cat": "Gaming",        "prompt": "Install Heroic Games Launcher (Epic, GOG, Amazon games) via flatpak from Flathub: com.heroicgameslauncher.hgl.", "desc": "Epic / GOG / Amazon games launcher"},
    {"id": 107,"name": "Bottles",             "cat": "Gaming",         "prompt": "Install Bottles to run Windows software and games via Wine, via flatpak from Flathub (the only officially supported method): com.usebottles.bottles.", "desc": "Run Windows apps/games via Wine"},
    {"id": 108,"name": "ProtonUp-Qt",         "cat": "Gaming",         "prompt": "Install ProtonUp-Qt to install and manage Proton-GE / Wine-GE compatibility tools via flatpak from Flathub: net.davidotek.pupgui2.", "desc": "Manage Proton-GE for Steam/Lutris"},
    # ── Security ────────────────────────────────────────────────────────────────
    {"id": 109,"name": "Gufw Firewall",       "cat": "Security",       "prompt": "Install Gufw, a graphical firewall (UFW) frontend, via apt (gufw). Tell the user to enable the firewall inside the app.", "desc": "Easy graphical firewall"},
    {"id": 110,"name": "ClamAV + ClamTk",     "cat": "Security",       "prompt": "Install the ClamAV antivirus engine and the ClamTk GUI via apt (clamav clamtk), then update the virus database with freshclam.", "desc": "Open-source antivirus + GUI"},
    {"id": 111,"name": "Wireshark",           "cat": "Security",       "prompt": "Install Wireshark network protocol analyzer via apt (wireshark). If prompted, allow non-root packet capture.", "desc": "Network protocol analyzer"},
    # ── Games — Free & Open-Source (all installable via Flathub; verified IDs) ──
    {"id": 112,"name": "SuperTuxKart",        "cat": "Games — Free & Open-Source", "prompt": "Install SuperTuxKart, a 3D open-source kart racer, via flatpak from Flathub: net.supertuxkart.SuperTuxKart (or apt: supertuxkart).", "desc": "3D kart racer (Mario Kart-like)"},
    {"id": 113,"name": "0 A.D.",              "cat": "Games — Free & Open-Source", "prompt": "Install 0 A.D., a free historical real-time strategy game, via flatpak from Flathub: com.play0ad.zeroad (or apt: 0ad).", "desc": "Historical RTS (Age of Empires-like)"},
    {"id": 114,"name": "Luanti (Minetest)",   "cat": "Games — Free & Open-Source", "prompt": "Install Luanti (formerly Minetest), a block-based voxel sandbox game platform, via flatpak from Flathub: org.luanti.luanti.", "desc": "Voxel sandbox (Minecraft-like)"},
    {"id": 115,"name": "Battle for Wesnoth",  "cat": "Games — Free & Open-Source", "prompt": "Install The Battle for Wesnoth, a turn-based fantasy strategy game, via flatpak from Flathub: org.wesnoth.Wesnoth (or apt: wesnoth).", "desc": "Turn-based fantasy strategy"},
    {"id": 116,"name": "Xonotic",             "cat": "Games — Free & Open-Source", "prompt": "Install Xonotic, a fast free arena first-person shooter, via flatpak from Flathub: org.xonotic.Xonotic.", "desc": "Fast arena FPS (Quake-like)"},
    {"id": 117,"name": "OpenTTD",             "cat": "Games — Free & Open-Source", "prompt": "Install OpenTTD, an open-source Transport Tycoon Deluxe, via flatpak from Flathub: org.openttd.OpenTTD (or apt: openttd).", "desc": "Transport business sim"},
    {"id": 118,"name": "Warzone 2100",        "cat": "Games — Free & Open-Source", "prompt": "Install Warzone 2100, a modernized classic 3D real-time strategy game, via flatpak from Flathub: net.wz2100.wz2100 (or apt: warzone2100).", "desc": "3D real-time strategy"},
    {"id": 119,"name": "Veloren",             "cat": "Games — Free & Open-Source", "prompt": "Install Veloren, an action-adventure voxel RPG, via flatpak from Flathub: net.veloren.veloren.", "desc": "Multiplayer voxel action-RPG"},
    {"id": 120,"name": "Mindustry",           "cat": "Games — Free & Open-Source", "prompt": "Install Mindustry, a sandbox tower-defense and factory builder, via flatpak from Flathub: com.github.Anuken.Mindustry.", "desc": "Tower-defense + factory builder"},
    {"id": 121,"name": "OpenRA",              "cat": "Games — Free & Open-Source", "prompt": "Install OpenRA, a modernized Command & Conquer-style RTS, via flatpak from Flathub: net.openra.OpenRA.", "desc": "Classic C&C-style RTS, rebuilt"},
    {"id": 122,"name": "Shattered Pixel Dungeon","cat": "Games — Free & Open-Source", "prompt": "Install Shattered Pixel Dungeon, a traditional roguelike dungeon crawler, via flatpak from Flathub: com.shatteredpixel.shatteredpixeldungeon.", "desc": "Roguelike dungeon crawler"},
    {"id": 123,"name": "SuperTux",            "cat": "Games — Free & Open-Source", "prompt": "Install SuperTux, a classic jump-and-run platformer starring Tux, via flatpak from Flathub: org.supertuxproject.SuperTux (or apt: supertux).", "desc": "2D platformer (Super Mario-like)"},
    {"id": 124,"name": "Endless Sky",         "cat": "Games — Free & Open-Source", "prompt": "Install Endless Sky, a space trading, exploration and combat game, via flatpak from Flathub: io.github.endless_sky.endless_sky (or apt: endless-sky).", "desc": "Space trading & combat"},
    {"id": 125,"name": "Hedgewars",           "cat": "Games — Free & Open-Source", "prompt": "Install Hedgewars, turn-based artillery combat, via flatpak from Flathub: org.hedgewars.Hedgewars (or apt: hedgewars).", "desc": "Turn-based artillery (Worms-like)"},
    {"id": 126,"name": "Widelands",           "cat": "Games — Free & Open-Source", "prompt": "Install Widelands, a Settlers-style economy strategy game, via flatpak from Flathub: org.widelands.Widelands (or apt: widelands).", "desc": "Settlers-style economy strategy"},
    {"id": 127,"name": "Freeciv",             "cat": "Games — Free & Open-Source", "prompt": "Install Freeciv, a Civilization-style turn-based 4X strategy game. Prefer apt (freeciv) on Debian/Ubuntu, or flatpak from Flathub using the GTK client: org.freeciv.gtk322.", "desc": "Civilization-style 4X strategy"},
    {"id": 128,"name": "Cataclysm: DDA",      "cat": "Games — Free & Open-Source", "prompt": "Install Cataclysm: Dark Days Ahead, a turn-based post-apocalyptic survival roguelike, via flatpak from Flathub: org.cataclysmdda.CataclysmDDA.", "desc": "Post-apocalyptic survival roguelike"},
]


def _parse_app_selection(sel: str, max_id: int = None):
    """Parse '1', '1,5,14', '1-5', or '1,5-7,10' into [1, 5, 6, 7, 10].
    Returns a sorted unique list of valid catalog ids (1..max_id).
    Defaults to len(APP_CATALOG) for backwards compatibility."""
    if max_id is None:
        max_id = len(APP_CATALOG)
    ids = set()
    for chunk in sel.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            try:
                start_s, end_s = chunk.split("-", 1)
                start, end = int(start_s), int(end_s)
                if start > end:
                    start, end = end, start
                for n in range(start, end + 1):
                    if 1 <= n <= max_id:
                        ids.add(n)
            except ValueError:
                continue
        else:
            try:
                n = int(chunk)
                if 1 <= n <= max_id:
                    ids.add(n)
            except ValueError:
                continue
    return sorted(ids)


def _run_catalog_picker(backend, bctx, slog, *, catalog, title, intro, item_label, history_tag):
    """Shared multi-select picker used by both Install Apps ([30]) and AI Tools
    ([40]). Renders the catalog grouped by category, accepts numbers/ranges,
    confirms, then runs each prompt through the agentic engine."""
    hdr(title)
    print(f"\n  {DIM}{intro}{R}")

    def _render(entries):
        # Group by category, preserving the order each category first appears.
        # Rendering an arbitrary subset lets us show live search results too.
        cats, by_cat = [], {}
        for entry in entries:
            if entry["cat"] not in by_cat:
                by_cat[entry["cat"]] = []
                cats.append(entry["cat"])
            by_cat[entry["cat"]].append(entry)
        for cat in cats:
            print(f"\n  {BOLD}{CYAN}{cat.upper()}{R}")
            for entry in by_cat[cat]:
                num = f"[{entry['id']:>3}]"
                name = f"{BOLD}{entry['name']}{R}".ljust(38 + len(BOLD) + len(R))
                print(f"   {C(num, GREEN)}  {name}  {DIM}{entry['desc']}{R}")

    def _match(term):
        t = term.lower()
        return [e for e in catalog
                if t in e["name"].lower() or t in e["desc"].lower() or t in e["cat"].lower()]

    # Search-and-select loop: a word filters the list; numbers/ranges select.
    term = ""
    chosen = None
    while chosen is None:
        entries = catalog if not term else _match(term)
        if term and not entries:
            warn(f"Nothing matches '{term}'. Showing everything.")
            term, entries = "", catalog
        if term:
            print(f"\n  {BOLD}{GREEN}🔎 {len(entries)} result(s) for '{term}'{R}   "
                  f"{DIM}(type {BOLD}*{R}{DIM} to show all again){R}")
        _render(entries)
        print(f"\n  {DIM}Pick numbers ('1'  '1,3,5'  '1-5'), or type a word to "
              f"{BOLD}search{R}{DIM} (e.g. 'photo', 'browser', 'backup'). 'q' cancels.{R}")
        try:
            sel = input(f"\n  {BOLD}Pick {item_label} or search:{R} ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        low = sel.lower()
        if not sel or low in ("q", "quit", "exit", "back"):
            return
        if sel == "*" or low in ("all", "clear", "reset"):
            term = ""
            continue
        if sel.startswith("/"):                       # explicit search: "/photo"
            term = sel[1:].strip()
            continue
        if not any(ch.isdigit() for ch in sel):       # any word → search
            term = sel
            continue
        ids = _parse_app_selection(sel, max_id=len(catalog))
        if not ids:
            if any(ch.isalpha() for ch in sel):        # e.g. "3d printing" → search
                term = sel
                continue
            warn(f"Couldn't parse '{sel}'. Use numbers like '1' or '1,5,14', or type a word to search.")
            continue
        chosen = [e for e in catalog if e["id"] in ids]
    print(f"\n  {BOLD}You're about to install {len(chosen)} {item_label}:{R}")
    for entry in chosen:
        print(f"   {GREEN}•{R} {BOLD}{entry['name']}{R}  {DIM}({entry['cat']}){R}")
    try:
        confirm = input(f"\n  {BOLD}Proceed?{R} [y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return
    if confirm not in ("y", "yes"):
        info("Cancelled — nothing was installed.")
        return

    for i, entry in enumerate(chosen, 1):
        section(f"[{i}/{len(chosen)}] Installing {entry['name']}")
        try:
            agentic_engine(backend, entry["prompt"], bctx, slog)
        except KeyboardInterrupt:
            warn(f"Cancelled. Skipping remaining {item_label}.")
            return
        _history_append(f"Install {entry['name']}", history_tag)

    if len(chosen) > 1:
        print(f"\n  {GREEN}{BOLD}✓ Finished installing {len(chosen)} {item_label}.{R}")


def feat_install_apps(backend, bctx, slog):
    """Quick app installer — 128-app catalog covering browsers, communication,
    office, media, graphics, developer tools, system tools, files & sync,
    utilities, gaming, security, and free/open-source games. Each entry maps to a
    natural-language install prompt;
    the agentic engine picks the right method (apt / snap / flatpak / vendor
    repo) for the user's distro and confirms before running anything."""
    _run_catalog_picker(
        backend, bctx, slog,
        catalog=APP_CATALOG,
        title="Install Apps — Quick Catalog",
        intro="Pick one or more apps. TuxGenie picks the right install method "
              "for your distro and shows every command before running it.",
        item_label="app(s)",
        history_tag="install_apps",
    )


AI_CATALOG = [
    # ── AI Code Editors ───────────────────────────────────────────────────────
    {"id": 1,  "name": "Cursor",                "cat": "AI Editors",      "prompt": "Install Cursor, the AI-first code editor (a VS Code fork by Anysphere). Download the official Linux AppImage from https://cursor.com/download (x64), save it under ~/Applications, make it executable, and create a ~/.local/share/applications/cursor.desktop launcher so it shows in the app menu. Optionally also install the Cursor CLI agent with: curl https://cursor.com/install -fsS | bash.", "desc": "AI-first code editor (VS Code fork)"},
    {"id": 2,  "name": "Windsurf",              "cat": "AI Editors",      "prompt": "Install Windsurf, the agentic AI code editor. Use the official apt repo: add the key from https://windsurf-stable.codeiumdata.com/wVxQEIWkwPUEAGf3/windsurf.gpg, add the deb source 'https://windsurf-stable.codeiumdata.com/wVxQEIWkwPUEAGf3/apt stable main', then apt update && apt install windsurf. If that URL has changed, get current instructions from https://windsurf.com/download.", "desc": "Agentic AI code editor"},
    {"id": 3,  "name": "Zed",                   "cat": "AI Editors",      "prompt": "Install Zed, the fast open-source code editor with built-in AI, using the official installer: curl -f https://zed.dev/install.sh | sh.", "desc": "Fast open-source editor with AI"},
    # ── Coding AI (CLIs & agents) ───────────────────────────────────────────────
    {"id": 4,  "name": "Claude Code",           "cat": "Coding AI",       "prompt": "Install Anthropic's Claude Code CLI globally via npm (npm install -g @anthropic-ai/claude-code). Make sure Node.js LTS is installed first. Tell the user to set the ANTHROPIC_API_KEY env var afterwards.", "desc": "Anthropic's terminal coding agent"},
    {"id": 5,  "name": "OpenAI Codex CLI",      "cat": "Coding AI",       "prompt": "Install OpenAI Codex CLI, a terminal coding agent, globally via npm: npm install -g @openai/codex. Ensure Node.js LTS is installed first, then tell the user to sign in or set their OpenAI API key.", "desc": "OpenAI's terminal coding agent"},
    {"id": 6,  "name": "Gemini CLI",            "cat": "Coding AI",       "prompt": "Install Google's Gemini CLI globally via npm: npm install -g @google/gemini-cli. Ensure Node.js 18+ is installed first.", "desc": "Google Gemini AI in your terminal"},
    {"id": 7,  "name": "GitHub Copilot CLI",    "cat": "Coding AI",       "prompt": "Install GitHub's agentic Copilot CLI via npm: npm install -g @github/copilot (needs Node.js 22+); it launches with the 'copilot' command. Do NOT use the retired 'gh extension install github/gh-copilot' — that is deprecated.", "desc": "GitHub's agentic AI coding CLI"},
    {"id": 8,  "name": "Aider",                 "cat": "Coding AI",       "prompt": "Install aider-chat (the AI pair-programmer for the terminal). Prefer pipx (pipx install aider-chat) so it lives in its own venv. Make sure pipx and Python 3 are installed first.", "desc": "AI pair-programmer in your terminal"},
    {"id": 9,  "name": "Goose",                 "cat": "Coding AI",       "prompt": "Install Goose, the open-source on-machine AI agent (Agentic AI Foundation), using the official installer: curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | bash. Docs are at goose-docs.ai.", "desc": "Open-source local AI agent"},
    {"id": 10, "name": "Cline",                 "cat": "Coding AI",       "prompt": "Install Cline, the autonomous AI coding agent for VS Code: code --install-extension saoudrizwan.claude-dev. Install VS Code first if it isn't present.", "desc": "Autonomous AI agent for VS Code"},
    {"id": 11, "name": "Continue.dev",          "cat": "Coding AI",       "prompt": "Install the Continue.dev open-source AI extension for VS Code: code --install-extension Continue.continue. Make sure VS Code is installed first; if not, install it first.", "desc": "Open-source AI extension for VS Code"},
    # ── Local LLMs — run AI offline, no API key needed ──────────────────────────
    {"id": 12, "name": "Ollama",                "cat": "Local LLMs",      "prompt": "Install Ollama on this Linux system using the official installer from https://ollama.com/install.sh. After install, verify the ollama service is running and report the local API URL.", "desc": "Run local LLMs offline (Llama, Mistral, Qwen)"},
    {"id": 13, "name": "GPT4All",               "cat": "Local LLMs",      "prompt": "Install GPT4All by Nomic to run local LLMs offline with a desktop GUI. Download the official Linux installer from https://github.com/nomic-ai/gpt4all/releases and run it.", "desc": "Run local LLMs offline (desktop GUI)"},
    {"id": 14, "name": "Msty",                  "cat": "Local LLMs",      "prompt": "Install Msty, a desktop app for local and cloud AI chat. Download the official Linux AppImage or .deb from https://msty.ai (see https://docs.msty.app) and install it, creating a launcher entry if it's an AppImage.", "desc": "Local + cloud AI chat, one app"},
    {"id": 15, "name": "Jan",                   "cat": "Local LLMs",      "prompt": "Install Jan AI desktop app for Linux from the official GitHub releases (jan.ai). Prefer the .deb on Debian/Ubuntu or the AppImage otherwise; create a desktop entry if AppImage.", "desc": "Open-source ChatGPT alternative"},
    {"id": 16, "name": "LM Studio",             "cat": "Local LLMs",      "prompt": "Install LM Studio for Linux: download the official AppImage from lmstudio.ai, place it under ~/Applications, make it executable, and create a .desktop entry so it appears in the launcher.", "desc": "GUI to download and run any GGUF model"},
    # ── AI Web UIs & Servers ────────────────────────────────────────────────────
    {"id": 17, "name": "Open WebUI",            "cat": "AI Web UIs & Servers", "prompt": "Install Open WebUI (a ChatGPT-style web UI for Ollama) using the official Docker container: docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main. Tell the user to open http://localhost:3000 once running.", "desc": "ChatGPT-style browser UI for local models"},
    {"id": 18, "name": "LocalAI",               "cat": "AI Web UIs & Servers", "prompt": "Install LocalAI, a self-hosted OpenAI-compatible API server, via Docker: docker run -d -p 8080:8080 --name local-ai --restart always localai/localai:latest. Ensure Docker is installed first, then tell the user the API is at http://localhost:8080.", "desc": "Self-hosted OpenAI-compatible API"},
    # ── AI Terminals ──────────────────────────────────────────────────────────
    {"id": 19, "name": "Warp",                  "cat": "AI Terminals",    "prompt": "Install Warp, the AI-powered modern terminal, from its official apt repo: add the key from https://releases.warp.dev/linux/keys/warp.asc, add the deb source 'https://releases.warp.dev/linux/deb stable main', then apt update && apt install warp-terminal. (Downloading the official .deb and running 'apt install ./warp-terminal.deb' also sets up the repo.)", "desc": "AI-powered modern terminal"},
    # ── Voice & Speech ──────────────────────────────────────────────────────────
    {"id": 20, "name": "Whisper",               "cat": "Voice & Speech",  "prompt": "Install OpenAI Whisper for offline speech-to-text via pipx (pipx install openai-whisper) and ensure ffmpeg is also installed via apt.", "desc": "Offline speech-to-text"},
    # ── Cloud AI Apps ─────────────────────────────────────────────────────────
    {"id": 21, "name": "ChatGPT Desktop",       "cat": "Cloud AI Apps",   "prompt": "Install a ChatGPT desktop client for Linux. If no official OpenAI .deb exists yet for this distro, install the well-maintained community 'chatgpt' Snap (sudo snap install chatgpt-desktop) or a Flatpak as a clearly-labelled alternative — explain to the user it is community-maintained.", "desc": "Desktop client for OpenAI ChatGPT"},
    # ── Starter Pack ────────────────────────────────────────────────────────────
    {"id": 22, "name": "Local AI Starter Pack", "cat": "Starter Packs",   "prompt": "Set up a complete local AI stack on this machine in three steps: 1) Install Ollama via the official installer (https://ollama.com/install.sh). 2) Pull the llama3.2:3b model (small, fast, fits on most laptops). 3) Install Open WebUI via the official Docker container on port 3000. At the end, tell the user the local URL to open and how to start chatting.", "desc": "Ollama + Open WebUI + llama3.2:3b — zero to local AI"},
]


# ── FEATURE 88: Cloud Drive Manager ──────────────────────────────────────────
# Guided rclone wrapper for non-technical users. Persistent dashboard with a
# provider picker, browse, backup/sync, mount, encrypt, remove. Every
# state-changing rclone command goes through _cloud_run(), which shows the
# command, asks y/n/skip, then runs it directly via run_cmd_live — so this
# whole feature works even when the user has no API credits (deterministic
# tasks shouldn't need Claude). Passwords are read via getpass, piped through
# `rclone obscure`, and the plaintext never leaves the local function.

CLOUD_MOUNTS_FILE = os.path.join(CFG_DIR, "cloud-mounts.json")

CLOUD_PROVIDERS = [
    {"id": 1, "name": "Google Drive",            "type": "drive",    "auth": "oauth"},
    {"id": 2, "name": "Dropbox",                 "type": "dropbox",  "auth": "oauth"},
    {"id": 3, "name": "OneDrive",                "type": "onedrive", "auth": "oauth"},
    {"id": 4, "name": "Box",                     "type": "box",      "auth": "oauth"},
    {"id": 5, "name": "pCloud",                  "type": "pcloud",   "auth": "oauth"},
    {"id": 6, "name": "Nextcloud / WebDAV",      "type": "webdav",   "auth": "creds"},
    {"id": 7, "name": "Amazon S3 / S3-compatible","type": "s3",      "auth": "s3"},
]

_PRETTY_TYPE = {
    "drive": "Google Drive", "dropbox": "Dropbox", "onedrive": "OneDrive",
    "box": "Box", "pcloud": "pCloud", "webdav": "WebDAV / Nextcloud",
    "s3": "Amazon S3 / S3-compat", "crypt": "Encrypted overlay",
}

def _cloud_pretty_type(t): return _PRETTY_TYPE.get(t, t)

def _cloud_rclone_installed():
    return shutil.which("rclone") is not None

def _cloud_is_headless():
    """Best-effort headless detection — no GUI session or active SSH."""
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return True
    return not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

def _cloud_load_mounts():
    try:
        return json.loads(open(CLOUD_MOUNTS_FILE).read())
    except Exception:
        return []

def _cloud_save_mounts(mounts):
    try:
        with open(CLOUD_MOUNTS_FILE, "w") as f:
            json.dump(mounts, f)
    except Exception:
        pass

def _cloud_list_remotes():
    """Return [(name, type), ...] from `rclone listremotes` + `config dump`."""
    rc, out, _ = run_cmd("rclone listremotes")
    if rc != 0:
        return []
    names = [ln.rstrip(":").strip() for ln in out.splitlines() if ln.strip()]
    types = {}
    rc, out, _ = run_cmd("rclone config dump")
    if rc == 0:
        try:
            for nm, conf in json.loads(out).items():
                types[nm] = conf.get("type", "?")
        except Exception:
            pass
    return [(n, types.get(n, "?")) for n in names]

def _cloud_obscure(plain):
    """Run `rclone obscure` on a plaintext password — never log/print the result."""
    try:
        r = subprocess.run(["rclone", "obscure", plain],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""

def _cloud_verify_remote(name):
    rc, _, _ = run_cmd(f"rclone lsd {shlex.quote(name)}: --max-depth 1", timeout=30)
    return rc == 0

def _cloud_run(cmd, what="", sudo=False, timeout=120, capture=False, hide_in_print=()):
    """Approval-gated direct command runner for the Cloud Sync feature.

    Replaces routing through agentic_engine for deterministic rclone commands —
    works without an API key and never asks Claude to interpret what we asked
    for. Mirrors the existing safety model: shows the command, asks for y/n/s,
    runs it with sudo if needed.

    Args:
        cmd:    the command to run (shell string).
        what:   plain-English description shown above the command.
        sudo:   if True, ensures sudo_pw is fetched even if cmd doesn't start with sudo.
        timeout: seconds before SIGKILL.
        capture: if True, returns stdout/stderr without printing them (for verifies).
        hide_in_print: substrings of `cmd` to redact when SHOWING the command
                       (so obscured passwords or tokens don't appear on screen).

    Returns:
        (rc, stdout, stderr). rc=-1 means user skipped/cancelled.
    """
    display_cmd = cmd
    for h in hide_in_print:
        if h:
            display_cmd = display_cmd.replace(h, "***")
    if what:
        print(f"\n  {CYAN}▶{R} {BOLD}{what}{R}")
    print(f"  {DIM}$ {display_cmd}{R}")
    try:
        ans = input(f"  {BOLD}Run it?{R} {C('[y]',GREEN,BOLD)} yes  "
                    f"{C('[n]',RED,BOLD)} no  {C('[s]',YELLOW,BOLD)} skip: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return -1, "", "Cancelled"
    if ans in ("n", "no"):
        info("Cancelled."); return -1, "", "Cancelled by user"
    if ans in ("s", "skip"):
        info("Skipped."); return -1, "", "Skipped by user"
    if ans not in ("y", "yes", ""):
        info("Cancelled."); return -1, "", "Cancelled"

    sudo_pw = None
    if sudo or cmd.strip().startswith("sudo"):
        try:
            sudo_pw = get_or_cache_sudo_password()
        except KeyboardInterrupt:
            return -1, "", "Cancelled"

    if capture:
        rc, stdout, stderr = run_cmd(cmd, timeout=timeout)
    else:
        print(f"  {CYAN}▶ Running…{R}")
        rc, stdout, stderr = run_cmd_live(cmd, sudo_password=sudo_pw, timeout=timeout)
    if rc == 0:
        ok("Done.")
    elif rc == -1:
        warn(f"Cancelled or timed out after {timeout}s.")
    else:
        warn(f"Exit {rc}.")
    return rc, stdout, stderr


def _cloud_render_dashboard(remotes):
    hdr("Cloud Sync — your drives in one place")
    section(f"Your cloud drives  ({len(remotes)})")
    if not remotes:
        print(f"    {DIM}No cloud drives connected yet.{R}")
        print(f"    {DIM}Press [1] below to add your first one (takes ~1 minute).{R}")
    else:
        for i, (name, t) in enumerate(remotes, 1):
            print(f"    {BLUE}{BOLD}{i}.{R}  {BOLD}{name.ljust(20)}{R}  "
                  f"{DIM}{_cloud_pretty_type(t).ljust(22)}{R}  {GREEN}{BOLD}✔ connected{R}")
    print(f"\n  {BOLD}What would you like to do?{R}")
    rows = [
        ("1", "Add a cloud drive",   "Google Drive · Dropbox · OneDrive · …"),
        ("2", "Browse a drive",      "Walk folders without opening a browser"),
        ("3", "Backup to a drive",   "One-way copy — safe, never deletes"),
        ("4", "Two-way sync",        "Keep a folder in sync both ways"),
        ("5", "Mount as a folder",   "Appears in your file manager"),
        ("6", "Encrypt a drive",     "Filenames + contents encrypted"),
        ("7", "Remove a drive",      "Disconnect this drive from TuxGenie"),
        ("8", "Zoho WorkDrive",      "Special path — uses Zoho's own app"),
    ]
    for n, label, tip in rows:
        print(f"    {BLUE}{BOLD}[{n}]{R}  {BOLD}{label.ljust(22)}{R}  {DIM}{tip}{R}")
    print(f"\n    {BLUE}{BOLD}[q]{R}  {BOLD}Back to main menu{R}")

def _cloud_ensure_rclone(backend, bctx, slog):
    if _cloud_rclone_installed():
        return True
    hdr("Cloud Sync — rclone not installed")
    print(f"  {YELLOW}{BOLD}⚠{R}  rclone isn't installed yet. TuxGenie needs it to talk to your")
    print(f"     cloud drives. It's a single ~50 MB binary from rclone.org.\n")
    print(f"    {BLUE}{BOLD}[1]{R}  {BOLD}Install rclone (recommended){R}")
    print(f"    {BLUE}{BOLD}[q]{R}  {BOLD}Back to main menu{R}")
    try:
        ans = input(f"\n  ❯ ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if ans != "1":
        return False
    _cloud_run(
        "curl https://rclone.org/install.sh | sudo bash",
        what="Download and install rclone from the official site (~50 MB).",
        sudo=True, timeout=600,
    )
    return _cloud_rclone_installed()

def _cloud_pick_remote(remotes, prompt_text):
    if not remotes:
        warn("No cloud drives yet. Use [1] Add a cloud drive first.")
        return None
    print(f"\n  {BOLD}{prompt_text}{R}")
    for i, (name, t) in enumerate(remotes, 1):
        print(f"    {BLUE}{BOLD}[{i}]{R}  {BOLD}{name}{R}  {DIM}({_cloud_pretty_type(t)}){R}")
    print(f"    {BLUE}{BOLD}[q]{R}  Cancel")
    try:
        sel = input(f"\n  ❯ ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if sel in ("q", "back", "", "quit"):
        return None
    try:
        idx = int(sel) - 1
        if 0 <= idx < len(remotes):
            return remotes[idx][0]
    except ValueError:
        pass
    warn("Invalid choice.")
    return None

def _cloud_add_drive(backend, bctx, slog):
    hdr("Add a cloud drive")
    print(f"  {BOLD}Which cloud drive do you want to add?{R}\n")
    for p in CLOUD_PROVIDERS:
        print(f"    {BLUE}{BOLD}[{p['id']}]{R}  {BOLD}{p['name']}{R}")
    print(f"\n    {BLUE}{BOLD}[q]{R}  Cancel")
    try:
        sel = input(f"\n  ❯ ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if sel in ("q", "", "back"):
        return
    try:
        prov = next(p for p in CLOUD_PROVIDERS if p["id"] == int(sel))
    except (StopIteration, ValueError):
        warn("Invalid choice."); return
    default_name = re.sub(r'\W+', '', prov['name'].lower().split()[0])
    try:
        raw_name = input(f"\n  {BOLD}Name for this drive (lowercase, no spaces) "
                         f"[{default_name}]:{R}\n  ❯ ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(); return
    name = re.sub(r'\W+', '', raw_name) or default_name
    if prov["auth"] == "oauth":
        _cloud_add_oauth(backend, bctx, slog, name, prov)
    elif prov["auth"] == "creds":
        _cloud_add_webdav(backend, bctx, slog, name, prov)
    elif prov["auth"] == "s3":
        _cloud_add_s3(backend, bctx, slog, name, prov)

def _run_oauth_with_browser_open(cmd, prov_name, timeout=600):
    """Stream rclone's OAuth flow, auto-open the localhost callback URL in a
    browser the moment rclone prints it, and keep the user informed about
    what's happening. Without this, users see "Waiting for code…" and think
    the app has hung — when in fact rclone is patiently waiting for them to
    finish sign-in in a browser they may not have noticed.
    """
    print(f"\n  {CYAN}▶ Running rclone — watch for the sign-in link below…{R}\n")
    proc = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    opened_url = None
    url_re = re.compile(r'(http://127\.0\.0\.1:\d+/auth\?[^\s]+)')
    start = time.time()
    try:
        for line in iter(proc.stdout.readline, ''):
            print(f"  {DIM}{line.rstrip()}{R}")
            if not opened_url:
                m = url_re.search(line)
                if m:
                    opened_url = m.group(1)
                    print(f"\n  {BG_GREEN}{BWHITE}{BOLD}  ★  Sign-in URL detected — opening your browser…  {R}")
                    print(f"  {DIM}If it doesn't open, copy this into a browser yourself:{R}")
                    print(f"  {BOLD}{BLUE}{opened_url}{R}\n")
                    try:
                        subprocess.Popen(
                            ["xdg-open", opened_url],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True,
                        )
                    except Exception:
                        pass
                    print(f"  {YELLOW}{BOLD}⏳  Waiting for you to finish sign-in in the browser…{R}")
                    print(f"  {DIM}(Press Ctrl-C here to cancel.){R}\n")
            if time.time() - start > timeout:
                proc.terminate()
                warn(f"Timed out after {timeout//60} minutes waiting for sign-in.")
                return -1
        proc.wait()
        return proc.returncode
    except KeyboardInterrupt:
        proc.terminate()
        print(f"\n  {YELLOW}Cancelled — sign-in aborted.{R}")
        return -1


def _cloud_add_oauth(backend, bctx, slog, name, prov):
    if _cloud_is_headless():
        section("Headless session detected")
        print(f"  No graphical browser available here. To sign in:")
        print(f"    {CYAN}1.{R}  On a desktop machine with a browser, run:  "
              f"{BOLD}rclone authorize \"{prov['type']}\"{R}")
        print(f"    {CYAN}2.{R}  Sign in to {prov['name']} when the browser opens")
        print(f"    {CYAN}3.{R}  Copy the JSON token printed in the terminal")
        try:
            tok = input(f"\n  {BOLD}Paste the token (or Enter to cancel):{R}\n  ❯ ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); return
        if not tok:
            return
        cmd = f"rclone config create {shlex.quote(name)} {prov['type']} token={shlex.quote(tok)}"
        _cloud_run(cmd, what=f"Add {prov['name']} drive '{name}' to rclone.", timeout=60)
    else:
        section(f"Sign in to {prov['name']}")
        print(f"  {BG_NAVY}{BWHITE}{BOLD}  Here's what's about to happen:  {R}")
        print(f"    {CYAN}1.{R}  rclone will print a sign-in URL like {DIM}http://127.0.0.1:...{R}")
        print(f"    {CYAN}2.{R}  TuxGenie will open it in your browser automatically.")
        print(f"    {CYAN}3.{R}  You sign in to {prov['name']} and click {BOLD}Allow{R}.")
        print(f"    {CYAN}4.{R}  This screen will finish on its own — no need to come back here.")
        print(f"\n  {DIM}If anything stalls, press Ctrl-C to cancel and try again.{R}")
        cmd = f"rclone config create {shlex.quote(name)} {prov['type']}"
        print(f"\n  {DIM}$ {cmd}{R}")
        try:
            ans = input(f"  {BOLD}Start sign-in?{R} {C('[y]',GREEN,BOLD)} yes  "
                        f"{C('[n]',RED,BOLD)} no: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(); return
        if ans not in ("y", "yes", ""):
            info("Cancelled."); return
        rc = _run_oauth_with_browser_open(cmd, prov['name'], timeout=600)
        if rc == 0:
            ok("Sign-in complete.")
        else:
            warn("Sign-in didn't finish. Try again or use the headless paste flow.")
    if _cloud_verify_remote(name):
        ok(f"Drive '{name}' added and verified.")
    else:
        warn(f"Drive '{name}' was not verified. Try Browse to test it.")

def _cloud_add_webdav(backend, bctx, slog, name, prov):
    import getpass as _gp
    try:
        url = input(f"\n  {BOLD}WebDAV URL{R}\n  "
                    f"{DIM}(Nextcloud: https://your-server/remote.php/dav/files/USERNAME){R}\n  ❯ ").strip()
        user = input(f"  {BOLD}Username:{R}\n  ❯ ").strip()
        pw = _gp.getpass(f"  Password (won't be shown): ")
    except (EOFError, KeyboardInterrupt):
        print(); return
    if not url or not user or not pw:
        warn("URL, username and password are all required."); return
    obscured = _cloud_obscure(pw)
    if not obscured:
        err("Could not obscure the password. Is rclone working?"); return
    cmd = (f"rclone config create {shlex.quote(name)} webdav "
           f"url={shlex.quote(url)} user={shlex.quote(user)} "
           f"pass={shlex.quote(obscured)} vendor=nextcloud")
    _cloud_run(
        cmd, what=f"Add WebDAV drive '{name}' (password is already obscured).",
        timeout=120, hide_in_print=(shlex.quote(obscured),),
    )
    if _cloud_verify_remote(name):
        ok(f"Drive '{name}' added and verified.")
    else:
        warn(f"Drive '{name}' created but verification failed. Check the URL/credentials.")

def _cloud_add_s3(backend, bctx, slog, name, prov):
    import getpass as _gp
    print(f"\n  {BOLD}S3 provider:{R}  [1] AWS  [2] Backblaze B2  [3] Wasabi  "
          f"[4] DigitalOcean Spaces  [5] Other")
    try:
        sp = input(f"  ❯ ").strip()
        access_key = input(f"  {BOLD}Access Key ID:{R}\n  ❯ ").strip()
        secret = _gp.getpass(f"  Secret Access Key (won't be shown): ")
        region = input(f"  {BOLD}Region (e.g. us-east-1, blank for default):{R}\n  ❯ ").strip()
        endpoint = input(f"  {BOLD}Custom endpoint URL (blank if AWS):{R}\n  ❯ ").strip()
    except (EOFError, KeyboardInterrupt):
        print(); return
    if not access_key or not secret:
        warn("Access key and secret are required."); return
    provider_map = {"1": "AWS", "2": "Other", "3": "Wasabi", "4": "DigitalOcean", "5": "Other"}
    provider_str = provider_map.get(sp, "AWS")
    parts = [
        "rclone config create", shlex.quote(name), "s3",
        f"provider={provider_str}",
        f"access_key_id={shlex.quote(access_key)}",
        f"secret_access_key={shlex.quote(secret)}",
    ]
    if region:   parts.append(f"region={shlex.quote(region)}")
    if endpoint: parts.append(f"endpoint={shlex.quote(endpoint)}")
    cmd = " ".join(parts)
    _cloud_run(
        cmd, what=f"Add S3 drive '{name}'.", timeout=120,
        hide_in_print=(shlex.quote(secret),),
    )
    if _cloud_verify_remote(name):
        ok(f"Drive '{name}' added and verified.")
    else:
        warn(f"Drive '{name}' created but verification failed. Check the credentials/endpoint.")

def _cloud_browse(remotes):
    name = _cloud_pick_remote(remotes, "Which drive do you want to browse?")
    if not name:
        return
    path = ""
    while True:
        section(f"Browsing  {name}:/{path}")
        rclone_path = f"{shlex.quote(name)}:{shlex.quote(path)}" if path else f"{shlex.quote(name)}:"
        rc, out, _ = run_cmd(f"rclone lsjson {rclone_path} --dirs-only", timeout=30)
        if rc != 0:
            err("Could not list folders."); return
        try:
            items = json.loads(out)
        except Exception:
            items = []
        if not items:
            print(f"  {DIM}(no folders here){R}")
        else:
            for i, it in enumerate(items, 1):
                print(f"    {BLUE}{BOLD}[{i}]{R}  \U0001F4C1 {it.get('Name', '?')}")
        print(f"\n    {BLUE}{BOLD}[u]{R}  Up one level    {BLUE}{BOLD}[q]{R}  Done")
        try:
            sel = input(f"\n  ❯ ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(); return
        if sel in ("q", ""):
            return
        if sel == "u":
            path = path.rsplit("/", 1)[0] if "/" in path else ""
            continue
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(items):
                folder = items[idx].get("Name") or items[idx].get("Path")
                path = f"{path}/{folder}" if path else folder
        except ValueError:
            warn("Invalid choice.")

def _cloud_backup(backend, bctx, slog, remotes):
    name = _cloud_pick_remote(remotes, "Backup TO which drive?")
    if not name:
        return
    try:
        local = input(f"\n  {BOLD}Which local folder?{R} [~/Documents]\n  ❯ ").strip() \
                or "~/Documents"
    except (EOFError, KeyboardInterrupt):
        print(); return
    local = os.path.expanduser(local)
    if not os.path.isdir(local):
        warn(f"Folder '{local}' doesn't exist."); return
    try:
        remote_path = input(f"  {BOLD}Save it on the drive as what?{R} "
                            f"[{os.path.basename(local)}]\n  ❯ ").strip() \
                      or os.path.basename(local)
    except (EOFError, KeyboardInterrupt):
        print(); return
    print(f"\n  {BOLD}Mode:{R}")
    print(f"    {BLUE}{BOLD}[1]{R}  {GREEN}Copy{R}  "
          f"= upload new/changed files. {BOLD}NEVER deletes anything on the cloud.{R}")
    print(f"    {BLUE}{BOLD}[2]{R}  {YELLOW}Sync{R}  "
          f"= mirror exactly. {BOLD}Files deleted locally WILL be deleted on the cloud.{R}")
    try:
        mode = input(f"\n  ❯ ").strip()
    except (EOFError, KeyboardInterrupt):
        print(); return
    if mode not in ("1", "2"):
        warn("Invalid choice."); return
    verb = "copy" if mode == "1" else "sync"
    target = f"{shlex.quote(name)}:{shlex.quote(remote_path)}"
    dry  = f"rclone {verb} {shlex.quote(local)} {target} --dry-run"
    real = f"rclone {verb} {shlex.quote(local)} {target} -P"
    section("Step 1/2 — Dry run (nothing will be changed)")
    _cloud_run(dry, what="Preview what would change. No files will be modified.",
               timeout=600)
    if verb == "sync":
        print(f"\n  {BG_RED}{BOLD}  ⚠  SYNC will delete cloud files that are not present locally.  {R}")
    try:
        confirm = input(f"\n  {BOLD}Proceed with the real run?{R} [y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(); return
    if confirm not in ("y", "yes"):
        info("Cancelled. Nothing was changed."); return
    section("Step 2/2 — Real run")
    _cloud_run(real, what="Run the actual transfer with live progress.",
               timeout=86400)

def _cloud_bisync(backend, bctx, slog, remotes):
    name = _cloud_pick_remote(remotes, "Two-way sync with which drive?")
    if not name:
        return
    try:
        local = input(f"\n  {BOLD}Which local folder?{R}\n  ❯ ").strip()
    except (EOFError, KeyboardInterrupt):
        print(); return
    local = os.path.expanduser(local)
    if not os.path.isdir(local):
        warn(f"Folder '{local}' doesn't exist."); return
    try:
        remote_path = input(f"  {BOLD}Remote folder name on {name}:{R} "
                            f"[{os.path.basename(local)}]\n  ❯ ").strip() \
                      or os.path.basename(local)
    except (EOFError, KeyboardInterrupt):
        print(); return
    target = f"{shlex.quote(name)}:{shlex.quote(remote_path)}"
    print(f"\n  {BG_RED}{BOLD}  ⚠  Two-way sync makes BOTH sides match.  {R}")
    print(f"  {YELLOW}Files deleted on either side may be deleted on the other.{R}")
    print(f"  {YELLOW}First-time setup needs --resync to baseline both sides.{R}")
    try:
        first = input(f"\n  {BOLD}Is this the first time syncing this pair?{R} [y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(); return
    cmd = (f"rclone bisync {shlex.quote(local)} {target} --resync -P"
           if first in ("y", "yes")
           else f"rclone bisync {shlex.quote(local)} {target} -P")
    what = ("Initial two-way sync — baselines both sides."
            if first in ("y", "yes")
            else "Two-way sync — propagates changes both directions.")
    _cloud_run(cmd, what=what, timeout=86400)

def _cloud_mount(backend, bctx, slog, remotes):
    mounts = _cloud_load_mounts()
    active = [m for m in mounts if os.path.ismount(m.get("mountpoint", ""))]
    if active:
        section("Active mounts")
        for i, m in enumerate(active, 1):
            print(f"    {BLUE}{BOLD}[u{i}]{R}  Unmount  {BOLD}{m['mountpoint']}{R}  "
                  f"{DIM}({m['remote']}){R}")
        print(f"    {DIM}— or pick a drive below to add another mount —{R}")
    name = _cloud_pick_remote(remotes, "Mount which drive?")
    if not name:
        # User may have typed u1/u2 to unmount; check active list
        return
    default_mp = os.path.expanduser(f"~/cloud-{name}")
    try:
        mp = input(f"\n  {BOLD}Mount it at which folder?{R} [{default_mp}]\n  ❯ ").strip() \
             or default_mp
    except (EOFError, KeyboardInterrupt):
        print(); return
    mp = os.path.expanduser(mp)
    try:
        os.makedirs(mp, exist_ok=True)
    except Exception as e:
        err(f"Could not create mountpoint: {e}"); return
    cmd = f"rclone mount {shlex.quote(name)}: {shlex.quote(mp)} --vfs-cache-mode full --daemon"
    print(f"\n  {DIM}This will run in the background. Open your file manager and look for{R} {BOLD}{mp}{R}")
    rc, _, _ = _cloud_run(cmd, what=f"Mount '{name}:' at {mp} as a background daemon.",
                          timeout=30)
    if rc == 0:
        mounts = _cloud_load_mounts()
        mounts.append({"remote": name, "mountpoint": mp, "started": time.time()})
        _cloud_save_mounts(mounts)

def _cloud_encrypt(backend, bctx, slog, remotes):
    name = _cloud_pick_remote(remotes, "Add encryption ON TOP OF which existing drive?")
    if not name:
        return
    import getpass as _gp
    print(f"\n  {BG_RED}{BOLD}  ⚠  IMPORTANT: if you lose this password, the data is gone forever.  {R}")
    print(f"  TuxGenie cannot recover it. Anthropic cannot recover it. Nobody can.")
    print(f"  Write it down somewhere safe (or save it in your password manager).\n")
    try:
        confirm = input(f"  {BOLD}Understood?{R} [y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(); return
    if confirm not in ("y", "yes"):
        info("Cancelled."); return
    try:
        pw  = _gp.getpass(f"  Choose an encryption password (won't be shown): ")
        pw2 = _gp.getpass(f"  Repeat it: ")
    except (EOFError, KeyboardInterrupt):
        print(); return
    if pw != pw2:
        err("Passwords don't match. Try again."); return
    if len(pw) < 12:
        warn("Password is short. Strongly recommend 16+ characters.")
        try:
            ok_short = input(f"  Use it anyway? [y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ok_short not in ("y", "yes"):
            return
    obscured = _cloud_obscure(pw)
    if not obscured:
        err("Could not obscure the password."); return
    enc_name = f"{name}-encrypted"
    cmd = (f"rclone config create {shlex.quote(enc_name)} crypt "
           f"remote={shlex.quote(name + ':')} "
           f"password={shlex.quote(obscured)} "
           f"filename_encryption=standard")
    _cloud_run(
        cmd, what=f"Create encrypted overlay '{enc_name}' over '{name}:'.",
        timeout=60, hide_in_print=(shlex.quote(obscured),),
    )

def _cloud_remove(backend, bctx, slog, remotes):
    name = _cloud_pick_remote(remotes, "Remove which drive?")
    if not name:
        return
    print(f"\n  {YELLOW}This only disconnects '{name}' from TuxGenie. Your cloud data stays.{R}")
    try:
        confirm = input(f"  {BOLD}Really remove '{name}'?{R} [y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(); return
    if confirm not in ("y", "yes"):
        info("Cancelled."); return
    _cloud_run(f"rclone config delete {shlex.quote(name)}",
               what=f"Delete '{name}' from rclone config.", timeout=15)

_ZOHO_DOWNLOAD_PAGES = (
    "https://www.zoho.com/workdrive/desktop-sync.html",
    "https://www.zoho.com/workdrive/desktop-sync-app.html",
)

def _url_is_alive(url, timeout=10):
    """HEAD-check a URL. Returns True for 2xx/3xx."""
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "Mozilla/5.0 (TuxGenie)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False

def _zoho_find_truesync_deb_url():
    """Scrape Zoho's TrueSync download page for the current .deb URL.

    Best-effort: Zoho's page rendering varies (some markup is JS-injected),
    so we look in BOTH the HTML and the linked JS bundles. If we still can't
    find anything, return None and the caller falls back to opening the page
    in a browser."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    def _fetch(url):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""

    pool = []   # candidate URLs to try
    for page in _ZOHO_DOWNLOAD_PAGES:
        html = _fetch(page)
        if not html:
            continue
        # 1. Direct .deb links in the HTML
        for m in re.finditer(r'https?://[^\s"\'<>()]+\.deb\b', html):
            pool.append(m.group(0))
        # 2. Walk linked JS bundles — Zoho often hides the real URL there
        for js_url in re.findall(r'src=["\'](https?://[^"\']+\.js)["\']', html)[:8]:
            js = _fetch(js_url)
            for m in re.finditer(r'https?://[^\s"\'<>()]+\.deb\b', js):
                pool.append(m.group(0))

    # Prefer URLs that look related to Zoho + TrueSync, then probe live-ness
    seen = set()
    ranked = []
    for url in pool:
        if url in seen:
            continue
        seen.add(url)
        score = 0
        u = url.lower()
        if "zoho"     in u: score += 3
        if "truesync" in u: score += 2
        if "workdrive"in u: score += 2
        if "linux"    in u or "amd64" in u or "x86_64" in u: score += 1
        ranked.append((score, url))
    ranked.sort(reverse=True)
    for _score, url in ranked:
        if _url_is_alive(url):
            return url
    return None

def _watch_downloads_for_deb(watch_dir, name_re, timeout=600, extensions=None):
    """Watch a directory for a new package matching name_re. Returns its full
    path once the file is fully written (size stable for several ticks), or
    None if the user cancels or we time out.

    extensions: tuple of acceptable suffixes (default: .deb, .tar.gz, .tgz).
    Zoho TrueSync for Linux ships as a .tar.gz, not a .deb — so we accept
    either and the caller routes by suffix.

    The name kept its "_deb" suffix for backwards compatibility with tests
    that already monkeypatch it; the docstring is the source of truth."""
    if extensions is None:
        extensions = (".deb", ".tar.gz", ".tgz")
    try:
        os.makedirs(watch_dir, exist_ok=True)
        baseline = set(os.listdir(watch_dir))
    except Exception:
        baseline = set()
    pretty_exts = " / ".join(extensions)
    print(f"\n  {YELLOW}{BOLD}⏳  Watching {watch_dir} for {pretty_exts}…{R}")
    print(f"  {DIM}As soon as it finishes downloading, TuxGenie will install it.{R}")
    print(f"  {DIM}Press Ctrl-C to skip and type the path manually.{R}\n")
    pat = re.compile(name_re, re.IGNORECASE)
    spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    start = time.time()
    try:
        i = 0
        while time.time() - start < timeout:
            try:
                current = os.listdir(watch_dir)
            except Exception:
                current = []
            matches = [
                f for f in current
                if f not in baseline
                and any(f.lower().endswith(ext) for ext in extensions)
                and pat.search(f)
            ]
            if matches:
                matches.sort(key=lambda f: -os.path.getmtime(os.path.join(watch_dir, f)))
                target = os.path.join(watch_dir, matches[0])
                print(f"\r  {GREEN}{BOLD}✔  Found: {matches[0]}{R}" + " " * 30)
                print(f"  {DIM}Waiting for download to finish writing…{R}")
                last_size, stable = -1, 0
                while stable < 3:
                    try:
                        sz = os.path.getsize(target)
                    except OSError:
                        sz = -1
                    if sz == last_size and sz > 0:
                        stable += 1
                    else:
                        stable = 0
                        last_size = sz
                    time.sleep(0.5)
                return target
            elapsed = int(time.time() - start)
            print(f"\r  {CYAN}{spinner[i % len(spinner)]}{R}  Waiting for download… ({elapsed}s)  ",
                  end="", flush=True)
            i += 1
            time.sleep(0.4)
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}Cancelled watching.{R}")
        return None
    print(f"\n  {YELLOW}Timed out after {timeout//60} min.{R}")
    return None


def _zoho_install_tarball(tar_path):
    """Install a Zoho TrueSync .tar.gz: extract → run install.sh if present,
    otherwise copy contents to /opt/zoho-truesync/ and symlink the binary
    into /usr/local/bin/."""
    import tempfile, tarfile
    extract_to = tempfile.mkdtemp(prefix="zoho_truesync_")
    print(f"  {DIM}Extracting to {extract_to}…{R}")
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            tf.extractall(extract_to)
    except Exception as e:
        err(f"Could not extract tarball: {e}")
        return False

    # Find the top-level extracted directory
    entries = [os.path.join(extract_to, e) for e in os.listdir(extract_to)]
    dirs = [e for e in entries if os.path.isdir(e)]
    pkg_root = dirs[0] if len(dirs) == 1 else extract_to

    # Look for an installer script first — Zoho ships one for desktop sync
    installer = None
    for name in ("install.sh", "setup.sh", "TrueSync.sh", "install"):
        p = os.path.join(pkg_root, name)
        if os.path.isfile(p):
            installer = p
            break

    if installer:
        info(f"Found installer: {os.path.basename(installer)}")
        os.chmod(installer, 0o755)
        rc, _, _ = _cloud_run(
            f"sudo bash {shlex.quote(installer)}",
            what=f"Run Zoho's bundled installer ({os.path.basename(installer)}).",
            sudo=True, timeout=600,
        )
        return rc == 0

    # No installer — copy the package contents to /opt/zoho-truesync/
    info("No installer script in the tarball; copying contents to /opt/zoho-truesync/.")
    rc, _, _ = _cloud_run(
        f"sudo rm -rf /opt/zoho-truesync && sudo mkdir -p /opt/zoho-truesync && "
        f"sudo cp -r {shlex.quote(pkg_root)}/* /opt/zoho-truesync/",
        what="Copy Zoho TrueSync into /opt/zoho-truesync/.",
        sudo=True, timeout=120,
    )
    if rc != 0:
        return False

    # Symlink any obvious binary into /usr/local/bin so the user can run it
    for binname in ("truesync", "TrueSync", "ZohoWorkDriveTrueSync",
                    "zohoworkdrive-truesync", "WorkDriveTrueSync"):
        candidate = f"/opt/zoho-truesync/{binname}"
        rc, _, _ = run_cmd(f"test -f {shlex.quote(candidate)}", timeout=5)
        if rc == 0:
            _cloud_run(
                f"sudo ln -sf {shlex.quote(candidate)} /usr/local/bin/{binname}",
                what=f"Add 'truesync' to your PATH.",
                sudo=True, timeout=10,
            )
            break
    return True


def _cloud_zoho_download_deb(url, dest):
    """Stream-download with a progress bar. Returns True on success."""
    try:
        with urllib.request.urlopen(url, timeout=120) as resp, open(dest, "wb") as out:
            total = int(resp.headers.get("Content-Length", 0) or 0)
            done, last_pct = 0, -1
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if total > 0:
                    pct = min(100, int(done * 100 / total))
                    if pct != last_pct:
                        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                        print(f"\r  {CYAN}{bar}{R} {pct}%  "
                              f"{done//1024//1024} MB / {total//1024//1024} MB",
                              end="", flush=True)
                        last_pct = pct
        print()
        return True
    except Exception as e:
        err(f"Download failed: {e}")
        return False

def _cloud_zoho_path(backend, bctx, slog):
    hdr("Zoho WorkDrive — TrueSync app")
    print(f"  {YELLOW}rclone doesn't have a Zoho WorkDrive backend.{R}")
    print(f"  But Zoho ships their own desktop sync app called {BOLD}TrueSync{R}.")
    print(f"  TuxGenie will install it for you — no manual extraction needed.\n")
    print(f"  {DIM}Distributed as a Linux .tar.gz from zoho.com/workdrive/desktop-sync.html{R}")
    try:
        ans = input(f"\n  {BOLD}Install Zoho WorkDrive TrueSync?{R} [y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(); return
    if ans not in ("y", "yes"):
        return

    section("Step 1 — Finding the TrueSync download")
    print(f"  {DIM}Probing Zoho's CDN…{R}")
    download_url = _zoho_find_truesync_deb_url()   # function name kept for back-compat; matches .deb OR .tar.gz
    pkg_path = None
    we_downloaded = False
    if not download_url:
        info("Auto-detect didn't find a direct URL (Zoho's page is JS-rendered).")
        info("Opening the download page in your browser — just click the Linux button.")
        info("TuxGenie will spot the file in ~/Downloads and install it automatically.")
        try:
            subprocess.Popen(["xdg-open", "https://www.zoho.com/workdrive/desktop-sync.html"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except Exception:
            pass
        watch_dir = os.path.expanduser("~/Downloads")
        pkg_path = _watch_downloads_for_deb(
            watch_dir, name_re=r"(zoho|truesync|workdrive)", timeout=600,
            extensions=(".deb", ".tar.gz", ".tgz"),
        )
        if not pkg_path:
            try:
                p = input(f"\n  {BOLD}Type the path to the downloaded file "
                          f"(.deb or .tar.gz, or Enter to cancel):{R}\n  ❯ ").strip()
            except (EOFError, KeyboardInterrupt):
                print(); return
            if not p:
                return
            pkg_path = os.path.expanduser(p)
            if not os.path.isfile(pkg_path):
                warn(f"File not found: {pkg_path}"); return
    else:
        ok(f"Found: {download_url}")
        section("Step 2 — Downloading TrueSync")
        import tempfile
        # Pick the suffix from the URL so the extractor can route correctly
        suffix = ".tar.gz" if download_url.lower().endswith((".tar.gz", ".tgz")) else ".deb"
        fd, pkg_path = tempfile.mkstemp(suffix=suffix, prefix="zoho_truesync_")
        os.close(fd)
        if not _cloud_zoho_download_deb(download_url, pkg_path):
            try: os.unlink(pkg_path)
            except OSError: pass
            return
        we_downloaded = True
        ok(f"Downloaded to {pkg_path}")

    section("Installing TrueSync")
    if pkg_path.lower().endswith((".tar.gz", ".tgz")):
        # Tarball flow: extract + run install.sh or copy to /opt
        success = _zoho_install_tarball(pkg_path)
    else:
        # .deb flow
        rc, _, _ = _cloud_run(
            f"sudo dpkg -i {shlex.quote(pkg_path)}",
            what="Install the Zoho TrueSync .deb.",
            sudo=True, timeout=300,
        )
        if rc != 0:
            info("dpkg flagged missing dependencies — running apt to fix them…")
            _cloud_run("sudo apt install -f -y",
                       what="Pull in any libraries TrueSync needs.",
                       sudo=True, timeout=600)
        success = (rc == 0)

    # Only clean up files WE downloaded; never delete user-provided files
    if we_downloaded:
        try: os.unlink(pkg_path)
        except OSError: pass

    rc, _, _ = run_cmd(
        "which truesync || ls /opt/Zoho* 2>/dev/null || ls /opt/zoho-truesync 2>/dev/null"
    )
    if rc == 0:
        ok("Zoho TrueSync installed! Look for 'TrueSync' in your app menu.")
    elif success:
        info("Installer ran. If TrueSync doesn't appear in your menu, log out and back in.")
    else:
        warn("Installation didn't complete cleanly. Check the output above.")

def feat_cloud_manager(backend, bctx, slog):
    """Cloud Drive Manager — guided rclone wrapper for non-technical users.
    Persistent dashboard with provider picker, browse, backup, sync, mount, encrypt, remove."""
    while True:
        if not _cloud_ensure_rclone(backend, bctx, slog):
            return
        remotes = _cloud_list_remotes()
        _cloud_render_dashboard(remotes)
        try:
            choice = input(f"\n  ❯ ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice in ("q", "quit", "back", "exit", ""):
            return
        try:
            if   choice == "1": _cloud_add_drive(backend, bctx, slog)
            elif choice == "2": _cloud_browse(remotes)
            elif choice == "3": _cloud_backup(backend, bctx, slog, remotes)
            elif choice == "4": _cloud_bisync(backend, bctx, slog, remotes)
            elif choice == "5": _cloud_mount(backend, bctx, slog, remotes)
            elif choice == "6": _cloud_encrypt(backend, bctx, slog, remotes)
            elif choice == "7": _cloud_remove(backend, bctx, slog, remotes)
            elif choice == "8": _cloud_zoho_path(backend, bctx, slog)
            else: warn("Invalid choice.")
        except KeyboardInterrupt:
            print(f"\n  {YELLOW}Cancelled — back to Cloud Sync menu.{R}")
        _history_append("Cloud Sync", "cloud")


def feat_install_ai_tools(backend, bctx, slog):
    """Quick AI-tools installer — categorised list of popular AI apps.
    Same UX as Install Apps: numbers, ranges, multi-select, confirm.
    Each entry is a natural-language install prompt for the agentic engine."""
    _run_catalog_picker(
        backend, bctx, slog,
        catalog=AI_CATALOG,
        title="AI Tools — Quick Catalog",
        intro="Pick one or more AI tools — AI code editors and coding agents, "
              "local offline LLMs, self-hosted UIs, then cloud apps.",
        item_label="AI tool(s)",
        history_tag="install_ai_tools",
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 9 — MENU + MAIN REPL
# ═══════════════════════════════════════════════════════════════════════════════
_MONITOR_SERVICE = "tuxgenie-monitor"
_MONITOR_SERVICE_FILE = os.path.expanduser(
    f"~/.config/systemd/user/{_MONITOR_SERVICE}.service"
)

# Units / message fragments that are noisy and rarely need user action
_MONITOR_NOISE_UNITS = {
    "audit", "kernel", "avahi-daemon", "avahi-daemon.service",
    "colord", "colord.service", "upowerd", "upowerd.service",
    "rtkit-daemon", "rtkit-daemon.service", "packagekit",
    "packagekit.service", "fwupd", "fwupd.service",
}
_MONITOR_NOISE_MSGS = (
    "deprecated", "no such file or directory", "not found in cache",
    "ignored", "error code 0", "warning:", "dbus-daemon",
    "org.freedesktop", "apparmor", "audit:",
)


def _monitor_daemon():
    """Daemon loop — streams journalctl errors and fires notify-send."""
    import subprocess as _sp
    cooldown: dict = {}          # unit -> last notification time
    COOLDOWN_SECS = 600          # 10 minutes per unit

    cmd = [
        "journalctl", "-f", "-p", "err",
        "--output=json", "--no-pager", "--no-hostname",
    ]
    try:
        proc = _sp.Popen(cmd, stdout=_sp.PIPE, stderr=_sp.DEVNULL, text=True)
    except Exception as e:
        sys.exit(f"tuxgenie-monitor: cannot start journalctl: {e}")

    for raw in proc.stdout:
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except Exception:
            continue

        unit    = (entry.get("_SYSTEMD_UNIT") or entry.get("UNIT") or
                   entry.get("SYSLOG_IDENTIFIER") or "unknown")
        message = entry.get("MESSAGE") or ""

        # Skip noise
        unit_base = unit.lower().replace(".service", "")
        if unit_base in _MONITOR_NOISE_UNITS:
            continue
        msg_lower = message.lower()
        if any(n in msg_lower for n in _MONITOR_NOISE_MSGS):
            continue
        # Skip kernel / audit lines that sneak through
        if unit_base in ("kernel", "audit"):
            continue

        now = time.time()
        if now - cooldown.get(unit, 0) < COOLDOWN_SECS:
            continue
        cooldown[unit] = now

        # Trim message for notification
        short_msg = message[:120].replace('"', "'")
        body = f"{short_msg}\n\nType  tuxgenie  to investigate & fix."

        try:
            _sp.run(
                [
                    "notify-send",
                    "--app-name=TuxGenie",
                    "--icon=dialog-error",
                    "--urgency=normal",
                    f"⚠ TuxGenie: {unit}",
                    body,
                ],
                timeout=5,
                check=False,
            )
        except Exception:
            pass


def feat_monitor(*_args, **_kwargs):
    """Install / manage the TuxGenie background error monitor (systemd user service)."""
    hdr("Error Monitor — background daemon")

    SERVICE_CONTENT = f"""\
[Unit]
Description=TuxGenie proactive error monitor
Documentation=https://github.com/ramchandragada/tuxgenie
After=graphical-session.target network.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={shlex.quote(sys.executable)} {shlex.quote(os.path.abspath(sys.argv[0]))} --monitor
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""

    # ── Check current status ──────────────────────────────────────────────────
    active = _r(f"systemctl --user is-active {_MONITOR_SERVICE} 2>/dev/null").strip()
    enabled = _r(f"systemctl --user is-enabled {_MONITOR_SERVICE} 2>/dev/null").strip()
    is_running = active == "active"
    is_enabled = enabled == "enabled"

    if is_running:
        print(f"  {GREEN}{BOLD}● Monitor is running{R}  {DIM}(status: {active}, enabled: {enabled}){R}")
    else:
        print(f"  {YELLOW}{BOLD}○ Monitor is not running{R}  {DIM}(status: {active}){R}")

    print(f"\n  {DIM}Watches journalctl for system errors and fires a desktop")
    print(f"  notification so you can fix problems before they get worse.{R}\n")

    # ── Check notify-send ─────────────────────────────────────────────────────
    has_notify = shutil.which("notify-send") is not None
    if not has_notify:
        warn("notify-send not found — notifications won't appear on desktop.")
        print(f"  {DIM}Install with:{R}  sudo apt install libnotify-bin\n")

    choices = []
    if not is_running:
        choices.append(("1", "Install & start the monitor"))
    else:
        choices.append(("1", "Restart the monitor"))
    if is_running or is_enabled:
        choices.append(("2", "Stop & disable the monitor"))
    choices.append(("3", "View recent monitor log"))
    choices.append(("q", "Back"))

    for k, v in choices:
        print(f"  {CYAN}{BOLD}[{k}]{R}  {v}")

    try:
        ans = input(f"\n  Choice: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return

    if ans == "q":
        return

    if ans == "1":
        # Write service file
        svc_dir = os.path.dirname(_MONITOR_SERVICE_FILE)
        os.makedirs(svc_dir, exist_ok=True)
        try:
            with open(_MONITOR_SERVICE_FILE, "w") as f:
                f.write(SERVICE_CONTENT)
            ok(f"Service file written: {_MONITOR_SERVICE_FILE}")
        except Exception as e:
            err(f"Could not write service file: {e}"); return

        os.system("systemctl --user daemon-reload 2>/dev/null")
        rc2 = os.system(f"systemctl --user enable --now {_MONITOR_SERVICE} 2>/dev/null")
        if rc2 == 0:
            ok("Monitor enabled and started!")
            print(f"  {DIM}You'll see a desktop notification whenever a system error occurs.{R}")
            if not has_notify:
                warn("Install libnotify-bin first so notifications actually appear:")
                print(f"    sudo apt install libnotify-bin")
        else:
            warn("Could not start service — check: systemctl --user status tuxgenie-monitor")

    elif ans == "2":
        os.system(f"systemctl --user disable --now {_MONITOR_SERVICE} 2>/dev/null")
        try:
            os.remove(_MONITOR_SERVICE_FILE)
        except Exception:
            pass
        os.system("systemctl --user daemon-reload 2>/dev/null")
        ok("Monitor stopped and disabled.")

    elif ans == "3":
        print(f"\n  {DIM}Last 30 log lines:{R}\n")
        os.system(f"journalctl --user -u {_MONITOR_SERVICE} -n 30 --no-pager 2>/dev/null")


def feat_shell_integration(*_args, **_kwargs):
    """Install the tg() shell function into .bashrc / .zshrc.
    After installation users can type  tg!!  after any failed command
    in any terminal to invoke TuxGenie — command: i"""

    hdr("Shell Integration — tg!! shortcut")

    _SNIPPET = r"""
# ── TuxGenie shell integration ──────────────────────────────────
# Installed by: tuxgenie (i → Shell Integration)
# After any failed command, type:   tg!!   or   tg fix
# Shorthand for tuxgenie anywhere:  tg "install chrome"
_tg_last_exit=0
_tg_last_cmd=""

if [[ -n "${BASH_VERSION:-}" ]]; then
    _tg_precmd() {
        _tg_last_exit=$?
        _tg_last_cmd="$(HISTTIMEFORMAT='' history 1 2>/dev/null | \
            sed 's/^[[:space:]]*[0-9]*[[:space:]]*//' || true)"
    }
    PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND; }_tg_precmd"
elif [[ -n "${ZSH_VERSION:-}" ]]; then
    _tg_preexec() { _tg_last_cmd="$1"; }
    _tg_precmd()  { _tg_last_exit=$?; }
    autoload -Uz add-zsh-hook 2>/dev/null
    add-zsh-hook preexec _tg_preexec
    add-zsh-hook precmd  _tg_precmd
fi

tg() {
    case "${1:-}" in
        "!!" | fix | why)
            if [[ "${_tg_last_exit:-0}" -ne 0 ]]; then
                tuxgenie "!! The command '$_tg_last_cmd' failed with exit code $_tg_last_exit. Please diagnose and fix it."
            else
                printf "  \033[38;2;22;132;58m✔\033[0m  Last command succeeded — nothing to fix.\n"
            fi ;;
        "") tuxgenie ;;
        *)  tuxgenie "$@" ;;
    esac
}
# ────────────────────────────────────────────────────────────────
"""

    _MARKER = "# ── TuxGenie shell integration ──"
    shell    = os.environ.get("SHELL", "/bin/bash")
    bash_rc  = os.path.expanduser("~/.bashrc")
    zsh_rc   = os.path.expanduser("~/.zshrc")
    targets  = ([zsh_rc, bash_rc] if "zsh" in shell else [bash_rc, zsh_rc])

    installed = []
    for rc_file in targets:
        if not os.path.exists(rc_file):
            continue
        try:
            content = open(rc_file).read()
        except Exception:
            continue
        if _MARKER in content:
            ok(f"Already installed in {rc_file}")
            installed.append(rc_file)
        else:
            try:
                with open(rc_file, "a") as fh:
                    fh.write("\n" + _SNIPPET)
                ok(f"Installed tg() in {rc_file}")
                installed.append(rc_file)
            except Exception as e:
                err(f"Could not write to {rc_file}: {e}")

    if not installed:
        try:
            with open(bash_rc, "a") as fh:
                fh.write("\n" + _SNIPPET)
            ok(f"Installed tg() in {bash_rc}")
        except Exception as e:
            err(f"Could not install shell integration: {e}")
            return

    print(f"""
  {BOLD}Restart your terminal (or run: source ~/.bashrc), then use:{R}

  {BGREEN}{BOLD}  tg!!{R}              {DIM}after any failed command — AI diagnoses and fixes{R}
  {BGREEN}{BOLD}  tg fix{R}            {DIM}same thing, easier to type{R}
  {BGREEN}{BOLD}  tg "question"{R}     {DIM}shorthand for tuxgenie from anywhere{R}

  {DIM}Works in any terminal — Warp, GNOME Terminal, Kitty, etc.{R}
  {DIM}Supports bash and zsh.{R}
""")


MENU_ITEMS = [
    # ── START HERE ───────────────────────────────────────────────
    ("1",  "fix",       "Fix a Problem",      "Describe what's wrong in plain English",         feat_fix),
    ("2",  "health",    "Health Check",       "System CPU/RAM/disk/service health scan",        feat_health),
    # ── FIX SOMETHING ────────────────────────────────────────────
    ("3",  "network",   "Internet / WiFi",    "Diagnose & fix connectivity",                    feat_network),
    ("4",  "sound",     "Sound / Audio",      "No audio, mic not working, HDMI sound",          feat_sound),
    ("5",  "display",   "Display",            "Wrong resolution, monitor not detected",         feat_display),
    ("6",  "bluetooth", "Bluetooth",          "Pairing fails, device not found",                feat_bluetooth),
    ("7",  "printer",   "Printer Setup",      "Install printer, fix printing problems",         feat_printer),
    ("8",  "webcam",    "Webcam Fix",         "Camera not detected, black screen",              feat_webcam),
    ("9",  "drivers",   "Missing Drivers",    "Detect & install missing drivers",               feat_drivers),
    ("10", "perms",     "Permissions",        "Diagnose & fix permission denied errors",        feat_perms),
    # ── INSTALL & UPDATE ─────────────────────────────────────────
    ("11", "packages",  "Install Software",   "Find & install software by description",         feat_packages),
    ("12", "updates",   "Check for Updates",  "Safe upgrade analysis & ordering",               feat_updates),
    ("13", "osupgrade", "Upgrade OS Version", "Upgrade Ubuntu/Fedora/Debian to latest release", feat_os_upgrade),
    ("14", "appswitch", "Find Linux App",     "Find Linux equivalents of Windows apps",         feat_appswitch),
    # ── PROTECT & RECOVER ────────────────────────────────────────
    ("15", "security",  "Security Check",     "Harden firewall, SSH, open ports",               feat_security),
    ("16", "backup",    "Backup Settings",    "Snapshot all system configs to .tar.gz",         feat_backup),
    ("17", "rollback",  "Undo Changes",       "Undo changes made in a previous session",        feat_rollback),
    # ── SPEED & MAINTENANCE ──────────────────────────────────────
    ("18", "perf",      "Performance Boost",  "Full audit + apply all safe speed fixes",        feat_performance),
    ("19", "disk",      "Disk Cleanup",       "Find space hogs & clean up safely",              feat_disk),
    ("20", "boot",      "Speed Up Boot",      "Find why boot is slow & speed it up",            feat_boot),
    ("21", "battery",   "Battery & Power",    "Improve battery life, fix overheating",          feat_battery),
    ("22", "services",  "Manage Services",    "Optimise startup & running services",            feat_services),
    # ── INSPECT ──────────────────────────────────────────────────
    ("23", "hardware",  "Hardware Info",      "Full hardware report & health check",            feat_hardware),
    ("24", "processes", "Running Programs",   "Tame CPU/memory hogs & zombie processes",        feat_processes),
    ("25", "logs",      "Explain Logs",       "Decode cryptic errors & system logs",            feat_logs),
    # ── FOR DEVELOPERS ───────────────────────────────────────────
    ("26", "script",    "Generate Script",    "Describe a task → get a bash script",            feat_script),
    ("27", "cron",      "Schedule Task",      "Schedule tasks in plain English",                feat_cron),
    ("28", "docker",    "Docker Help",        "Container troubleshooting & cleanup",            feat_docker),
    ("29", "ssh",       "SSH Setup",          "Set up & harden SSH securely",                   feat_ssh),
    ("30", "git",       "Git Helper",         "Understand diffs, fix conflicts, undo commits",  feat_git),
    # ── Gaming ───────────────────────────────────────────────────────────────
    ("31", "gaming",    "Gaming Setup",       "Get game-ready: Steam+Proton, GPU drivers, GameMode", feat_gaming_setup),
    # ── HEADLINE CATALOGS — catchy numbers so they stand out ─────
    ("77", "apps",      "Install Apps",       "128-app catalog (Brave, Signal, Blender, Bitwarden, Steam, SuperTuxKart…)", feat_install_apps),
    ("88", "cloud",     "Cloud Sync",         "Google Drive · Dropbox · OneDrive · S3 · WebDAV",   feat_cloud_manager),
    ("99", "ai",        "AI Tools",           "22 tools: Cursor, Windsurf, Zed, Ollama, Claude Code, Copilot CLI…", feat_install_ai_tools),
    # ── LETTER SHORTCUTS ─────────────────────────────────────────
    ("s",  "settings",  "Settings",           "Configure API key and model",                    feat_settings),
    ("i",  "shell",     "Shell Integration",  "Install tg!! shortcut in your terminal",         feat_shell_integration),
    ("m",  "monitor",   "Error Monitor",      "Background daemon: notify on system errors",     feat_monitor),
    ("f",  "feedback",  "Feature Request",    "Suggest a new feature",                          feat_feedback),
]


def show_menu():
    def _cat(bg, icon, title, subtitle):
        # No background box — the coloured backgrounds washed the bright-white
        # title out on many terminals. Use one consistent dark, high-contrast
        # colour for every category heading instead (bg arg kept for callers).
        print(f"\n  {INDIGO}{BOLD}{icon} {title}{R}  {DIM}{subtitle}{R}")

    def _item(num, label, tip):
        # Pad BEFORE adding ANSI codes — otherwise f-string width counts invisible escape chars
        num_s   = f"[{num}]".ljust(5)
        label_s = label.ljust(26)
        print(f"    {BLUE}{BOLD}{num_s}{R}  {BOLD}{label_s}{R}  {DIM}{tip}{R}")

    print(f"\n  {INDIGO}{BOLD}🐧 What would you like to do today?{R}")

    _cat(BG_FOREST, "🚀", "START HERE", "The two most-used features")
    _item("1",  "Fix a Problem",       "Describe what's wrong in plain English")
    _item("2",  "Health Check",        "Is everything running OK?")

    _cat(BG_FOREST, "🔧", "FIX SOMETHING", "Common things that go wrong")
    _item("3",  "Internet / WiFi",     "Can't connect? Slow internet?")
    _item("4",  "Sound / Audio",       "No sound, mic not working, HDMI audio?")
    _item("5",  "Display",             "Wrong resolution, monitor not detected?")
    _item("6",  "Bluetooth",           "Device won't pair or keeps disconnecting?")
    _item("7",  "Printer Setup",       "Install printer or fix printing problems")
    _item("8",  "Webcam Fix",          "Camera not working in Zoom / Teams / Meet?")
    _item("9",  "Missing Drivers",     "WiFi, GPU, or printer not working?")
    _item("10", "Permissions",         "'Permission denied' errors")

    _cat(BG_ORANGE, "📦", "INSTALL & UPDATE", "Get software and stay up to date")
    _item("11", "Install Software",    '"I need a video editor" → installed')
    _item("12", "Check for Updates",   "Keep your system safe and current")
    _item("13", "Upgrade OS Version",  "Move to Ubuntu 26 / Fedora 42 / latest release")
    _item("14", "Find Linux App",      '"What replaces Photoshop / Word / iTunes?"')

    _cat(BG_NAVY, "🛡️ ", "PROTECT & RECOVER", "Stay safe and reversible")
    _item("15", "Security Check",      "Are you protected? Find out now")
    _item("16", "Backup Settings",     "Save your config before making changes")
    _item("17", "Undo Changes",        "Oops? Roll back what TuxGenie did")

    _cat(BG_DARK, "⚡", "SPEED & MAINTENANCE", "Keep your computer fast")
    _item("18", "Performance Boost",   "🚀 Full audit + apply ALL safe speed fixes")
    _item("19", "Disk Cleanup",        "Running out of storage?")
    _item("20", "Speed Up Boot",       "Computer starts slowly? Fix it")
    _item("21", "Battery & Power",     "Battery draining fast? Laptop overheating?")
    _item("22", "Manage Services",     "Speed up startup, fix service failures")

    _cat(BG_PURPLE, "📊", "INSPECT", "See how your computer is doing")
    _item("23", "Hardware Info",       "What's inside my computer?")
    _item("24", "Running Programs",    "What's using CPU / memory?")
    _item("25", "Explain Logs",        "Decode confusing error messages")

    _cat(BG_TEAL, "⚙️ ", "FOR DEVELOPERS", "Power-user tools")
    _item("26", "Generate Script",     '"Back up my files nightly" → bash script')
    _item("27", "Schedule Task",       "Run things automatically on a schedule")
    _item("28", "Docker Help",         "Container troubleshooting & cleanup")
    _item("29", "SSH Setup",           "Remote access to another computer")
    _item("30", "Git Helper",          "Fix conflicts, undo commits, explain diffs")

    _cat(BG_FOREST, "🎮", "GAMING", "Play on Linux")
    _item("31", "Gaming Setup",        "Steam + Proton, GPU drivers, GameMode — get game-ready")
    print(f"    {DIM}🎮 Free games — SuperTuxKart, 0 A.D., Minetest, Veloren… — live in the App Catalog ({BOLD}77{R}{DIM}).{R}")

    _cat(BG_MAGENTA, "🎁", "ONE-TAP CATALOGS", "Headline picks — install bundles by number")
    _item("77", "Install Apps",        "🎁 128 apps: Brave, Signal, Blender, Bitwarden, Steam, games & more…")
    _item("88", "Cloud Sync",          "☁  Google Drive · Dropbox · OneDrive · S3 · WebDAV — one place")
    _item("99", "AI Tools",            "🤖 22 tools: Cursor, Windsurf, Zed, Ollama, Claude Code, Copilot CLI, GPT4All…")

    print(f"""
  {DIM}{'─' * 65}{R}
  {C('[s]',GOLD,BOLD)} Settings  ·  {C('[i]',LIME,BOLD)} Shell Integration  ·  {C('[u]',BCYAN,BOLD)} Update  ·  {C('[h]',BMAGENTA,BOLD)} History  ·  {C('[q]',BRED,BOLD)} Quit

  {BGREEN}{BOLD}💡 TIP:{R} {BOLD}You don't need to pick a number!{R}
     Just type what you need, like:
     {BLUE}\"my wifi is not working\"{R}   {BLUE}\"install chrome\"{R}   {BLUE}\"why is it slow?\"{R}
""")

# Last failed passthrough command — used by the !! fix shortcut
_last_failed: dict = {}

EXIT_WORDS = {"exit","quit","q","bye","logout"}
HELP_WORDS = {"help","?","how","what"}

def show_help():
    """Quick help for absolute beginners."""
    print(f"""
{BLUE}{BOLD}{'━'*60}{R}
{BLUE}{BOLD}  How to use TuxGenie{R}
{BLUE}{BOLD}{'━'*60}{R}

  {GREEN}{BOLD}The easy way:{R}  Just type what you need in plain English!

    Examples:
      {BLUE}{BOLD}my wifi stopped working{R}
      {BLUE}{BOLD}install google chrome{R}
      {BLUE}{BOLD}my computer is slow{R}
      {BLUE}{BOLD}how much disk space do I have{R}
      {BLUE}{BOLD}update everything{R}

  {GREEN}{BOLD}Or pick a number:{R}  Type 1-31, or 77 for Apps, 99 for AI Tools

  {GREEN}{BOLD}Safety:{R}
    {GREEN}{BOLD}✓{R} Every command is shown before it runs
    {GREEN}{BOLD}✓{R} Each step shows its risk level (safe / working / risky)
    {GREEN}{BOLD}✓{R} Dangerous commands are always blocked
    {GREEN}{BOLD}✓{R} Press {BOLD}Ctrl-C{R} anytime to stop

  {GREEN}{BOLD}Commands:{R}
    {BLUE}{BOLD}help{R}      Show this help
    {BLUE}{BOLD}menu{R}      Show the feature menu
    {BMAGENTA}{BOLD}h{R}         Show recent history (last 10 tasks)
    {BLUE}{BOLD}k{R}         Add / change API key (needed for AI features)
    {BLUE}{BOLD}u{R}         Update TuxGenie to latest version
    {GOLD}{BOLD}share-fix{R} Contribute a saved fix to the community 🧞
    {RED}{BOLD}q{R}         Quit TuxGenie
""")

def first_run_check():
    """Show one-time welcome + optional setup wizard for brand new users."""
    flag = os.path.join(CFG_DIR, ".welcomed")
    if os.path.exists(flag):
        return

    print(f"""
{GREEN}{BOLD}{'━'*60}{R}
{GREEN}{BOLD}  🎉  First time? Welcome to TuxGenie!{R}
{GREEN}{BOLD}{'━'*60}{R}

  TuxGenie is like having a Linux expert sitting next to you.
  Tell it what you need in plain English — it figures out the
  commands, explains what each one does, and runs them for you.

  {CYAN}{BOLD}Quick example:{R}
    You type:  {CYAN}\"my wifi is not connecting\"{R}
    TuxGenie:  Finds the problem, explains it, and fixes it

  {YELLOW}{BOLD}🔑 You're always in control:{R}
    Every command is shown before it runs.
    Dangerous operations are always blocked.
    Press {BOLD}Ctrl-C{R} anytime to stop.

  {DIM}Type {BOLD}help{R}{DIM} anytime to see tips.{R}
""")

    # Offer first-time setup wizard
    try:
        ans = input(f"  {GREEN}{BOLD}Would you like a quick setup to get your Linux ready?{R} [{C('y',GREEN,BOLD)}/{C('n',DIM)}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"

    if ans in ("y", "yes"):
        print(f"\n  {CYAN}{BOLD}Running First-Time Setup…{R}")
        print(f"  {DIM}This will update your system, install essentials, and set up basic security.{R}\n")

        setup_steps = [
            ("Update package list",        "sudo apt-get update -q",                              "safe"),
            ("Install system updates",     "sudo apt-get upgrade -y",                             "moderate"),
            ("Install useful tools",       "sudo apt-get install -y curl wget git unzip htop",    "safe"),
            ("Install media codecs",       "sudo apt-get install -y ubuntu-restricted-extras 2>/dev/null || sudo apt-get install -y mint-meta-codecs 2>/dev/null || true", "safe"),
            ("Enable firewall",            "sudo ufw enable && sudo ufw status",                  "moderate"),
            ("Sync system clock",          "sudo timedatectl set-ntp true",                       "safe"),
        ]

        for desc, cmd, risk in setup_steps:
            print(f"\n  {DIM}▸ {desc}{R}")
            try:
                ch = input(f"    Run this? [{C('y',GREEN,BOLD)}/{C('s',YELLOW,BOLD)}=skip/{C('q',RED,BOLD)}=quit setup]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if ch in ("q", "quit"):
                break
            if ch in ("s", "skip", "n"):
                print(C("    ↳ Skipped.", DIM)); continue
            if ch in ("y", "yes", ""):
                sudo_pw = None
                if cmd.strip().startswith("sudo"):
                    try:
                        sudo_pw = get_or_cache_sudo_password()
                    except KeyboardInterrupt:
                        break
                print(f"  {CYAN}▶ Running…{R}")
                rc, _, _ = run_cmd_live(cmd, sudo_password=sudo_pw)
                _restore_terminal()
                if rc == 0:
                    ok(desc)
                else:
                    warn(f"{desc} — had an issue, continuing anyway.")

        print(f"\n  {GREEN}{BOLD}✓ Setup complete! Your Linux is ready.{R}\n")

    try:
        open(flag, "w").write("1")
    except Exception:
        pass

_active_feature = "startup"


def main():
    global _active_feature, _last_failed
    _crash_guard()   # increment crash counter; rolls back if 3 consecutive crashes
    parser = argparse.ArgumentParser(
        prog="tuxgenie",
        description="TuxGenie — AI-powered Linux assistant powered by Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  tuxgenie                          # Interactive menu
  tuxgenie "my wifi is not working" # One-shot fix (no menu)
  tuxgenie --feature health         # Run a specific feature directly
""",
    )
    parser.add_argument("--version", action="version", version=f"TuxGenie {__version__}")
    parser.add_argument(
        "issue", nargs="?", default=None,
        help="Describe your problem in plain English for a one-shot fix"
    )
    parser.add_argument(
        "--feature", "-f", metavar="NAME",
        help="Run a specific feature directly (e.g. health, network, disk, git, security)"
    )
    parser.add_argument(
        "--digest", action="store_true",
        help="Show the weekly health digest (force-runs even if <7 days since last)"
    )
    parser.add_argument(
        "--monitor", action="store_true",
        help="Run the background error monitor daemon (used by the systemd user service)"
    )
    args = parser.parse_args()

    # ── Pipe mode: journalctl -xe | tuxgenie explain ─────────────────────────
    if not sys.stdin.isatty():
        piped = sys.stdin.read(8000).strip()
        if piped:
            _init_light_theme()
            backend = load_backend()
            with Spinner("Collecting system info…"):
                bctx = base_ctx()
            verb = args.issue or "explain"
            issue = f"{verb}\n\nPIPED INPUT:\n{piped}"
            _crash_mark_clean()   # startup succeeded — this version is healthy
            agentic_engine(backend, issue, bctx, [])
            return

    # ── Monitor daemon mode: tuxgenie --monitor ──────────────────────────────
    if args.monitor:
        _crash_mark_clean()   # reached daemon entry — startup is healthy
        _monitor_daemon()
        return

    # ── Digest-only mode: tuxgenie --digest ──────────────────────────────────
    if args.digest:
        _init_light_theme()
        _crash_mark_clean()
        _weekly_digest(force=True)
        return

    _init_light_theme()
    banner()
    startup_update_check()
    backend = load_backend()

    with Spinner("Collecting system info…"):
        bctx = base_ctx()
        # Refresh the deeper fingerprint (installed apps, GPU, etc.) in the
        # background — cached for 24h so most launches are no-ops. Failures
        # never block startup; the agentic engine just runs without it.
        try:
            threading.Thread(target=collect_fingerprint, daemon=True).start()
        except Exception:
            pass
    ok("System info collected")
    # Startup fully succeeded — clear the crash counter so only crashes that
    # happen *during* startup accumulate toward an automatic rollback.
    _crash_mark_clean()
    print(f"  {CYAN}{BOLD}Your system:{R}  {BOLD}{bctx['os']}{R}  {DIM}· {bctx['kernel']} · {bctx['arch']}{R}")

    session_log: list = []
    feature_map      = {num: fn   for num, _, name, _, fn in MENU_ITEMS}
    keyword_map      = {kw:  fn   for _, kw, name, _, fn  in MENU_ITEMS}
    feature_name_map = {num: name for num, _, name, _, _  in MENU_ITEMS}
    feature_kw_map   = {num: kw   for num, kw, _, _, _    in MENU_ITEMS}

    # ── One-shot mode: tuxgenie "describe problem" ────────────────────────────
    if args.issue:
        if args.issue.lower() in ("share-fix", "sharefix"):
            feat_share_fix()
            return
        if not try_passthrough(args.issue, session_log, backend, bctx):
            agentic_engine(backend, args.issue, bctx, session_log)
        save_session(session_log)
        return

    # ── Direct feature mode: tuxgenie --feature health ────────────────────────
    if args.feature:
        fn = keyword_map.get(args.feature.lower())
        if fn:
            fn(backend, bctx, session_log)
            save_session(session_log)
        else:
            valid = ", ".join(kw for _, kw, _, _, _ in MENU_ITEMS)
            print(f"{RED}Unknown feature '{args.feature}'.{R}\nValid: {valid}")
            sys.exit(1)
        return

    # ── Interactive mode ──────────────────────────────────────────────────────
    first_run_check()
    quick_health_check()
    _weekly_digest()
    show_menu()
    if backend._no_key:
        _line = f"  {DIM}{'─'*54}{R}"
        print(f"\n{_line}")
        print(f"  {YELLOW}{BOLD}⚠  No API key — AI features are disabled{R}")
        print(f"  {GREEN}✔  Terminal commands work fine without a key{R}")
        print(f"  {DIM}Type {BOLD}k{R}{DIM} to add your Anthropic key anytime{R}")
        print(f"{_line}")

    while True:
        try:
            _xm = f" {DIM}[expert]{R}" if backend.expert_mode else ""
            choice = input(f"\n  {BGREEN}{BOLD}❯{R}{_xm} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n  {GOLD}{BOLD}✨ Goodbye! Long Live Linux 🐧{R}")
            if hasattr(backend, '_session_input_tokens') and backend._session_input_tokens > 0:
                print(f"  {DIM}{backend.session_cost_estimate()}{R}")
            print(f"  {DIM}Thank you for using TuxGenie · {BLUE}www.tuxgenie.com{R}{DIM} · Aspera Technologies{R}\n")
            _restore_default_theme()   # restore terminal on exit
            break

        if not choice:
            continue
        if choice.lower() in EXIT_WORDS:
            print(f"\n  {GOLD}{BOLD}✨ Goodbye! Long Live Linux 🐧{R}")
            print(f"  {DIM}Thank you for using TuxGenie · {BLUE}www.tuxgenie.com{R}{DIM} · Aspera Technologies{R}\n")
            _restore_default_theme()   # restore terminal on exit
            break
        if choice.lower() in HELP_WORDS:
            show_help(); continue
        if choice.lower() in ("h", "history", "hist"):
            show_history(); continue
        if choice.lower() == "menu":
            show_menu(); continue
        if choice.lower() in ("u", "update"):
            feat_self_update(); continue
        if choice.lower() in ("k", "key", "apikey", "addkey", "setkey", "connect"):
            feat_set_api_key(backend); continue
        if choice.lower() in ("f", "feedback", "feature", "suggest"):
            feat_feedback(); continue
        if choice.lower() in ("share-fix", "sharefix", "share"):
            feat_share_fix(); continue
        if choice.lower() in ("i", "shell", "shellsetup", "integrate"):
            feat_shell_integration(); continue
        if choice.lower() in ("m", "monitor"):
            feat_monitor(); continue

        # !! — fix the last failed command (or handle "!! fix: ..." from tg shell function)
        if choice in ("!!", "fix", "why") or choice.lower().startswith("!! "):
            if choice.lower().startswith("!! "):
                # Input came from the external tg shell function — pass straight to AI
                agentic_engine(backend, choice, bctx, session_log)
            elif _last_failed:
                err_out = (_last_failed.get("stderr") or _last_failed.get("stdout", "")).strip()
                ctx = (
                    f"The command I just ran failed:\n"
                    f"  Command: {_last_failed['cmd']}\n"
                    f"  Exit code: {_last_failed['rc']}\n"
                )
                if err_out:
                    ctx += f"  Error output:\n{err_out[:800]}\n\n"
                ctx += "Please explain what went wrong in plain English and fix it."
                agentic_engine(backend, ctx, bctx, session_log)
                save_session(session_log)
                _last_failed = {}
            else:
                info("No failed command to fix yet — run a command first.")
            continue

        try:
            if choice in feature_map:
                fn = feature_map[choice]
                if fn is None:
                    continue
                _active_feature = choice
                fn(backend, bctx, session_log)
                save_session(session_log)
                _history_append(feature_name_map.get(choice, choice), feature_kw_map.get(choice, choice))
            else:
                # Natural language → try direct passthrough first, then agentic AI
                passed = try_passthrough(choice, session_log, backend, bctx)
                if not passed:
                    agentic_engine(backend, choice, bctx, session_log)
                save_session(session_log)
                _history_append(choice, "terminal" if passed else "fix")
            _restore_terminal()   # clean up terminal state after commands ran
        except KeyboardInterrupt:
            _restore_terminal()
            print(f"\n  {YELLOW}Cancelled — back to menu.{R}")
            continue
        print(f"\n  {DIM}Type a number, describe a problem, or{R} {BOLD}menu{R} {DIM}·{R} {BOLD}k{R}{DIM}=key{R} {DIM}·{R} {BOLD}u{R}{DIM}=update{R} {DIM}·{R} {RED}{BOLD}q{R}{DIM}=quit{R}")

    save_session(session_log)

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        _restore_default_theme()
        print(f"\n\n  {YELLOW}{BOLD}Goodbye! Long Live Linux 🐧{R}\n")
    except Exception:
        import sys as _sys
        report_crash(*_sys.exc_info(), feature=_active_feature)
