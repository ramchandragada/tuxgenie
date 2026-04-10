#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 ████████╗██╗   ██╗██╗  ██╗ ██████╗ ███████╗███╗   ██╗██╗███████╗
    ██╔══╝██║   ██║╚██╗██╔╝██╔════╝ ██╔════╝████╗  ██║██║██╔════╝
    ██║   ██║   ██║ ╚███╔╝ ██║  ███╗█████╗  ██╔██╗ ██║██║█████╗
    ██║   ██║   ██║ ██╔██╗ ██║   ██║██╔══╝  ██║╚██╗██║██║██╔══╝
    ██║   ╚██████╔╝██╔╝ ██╗╚██████╔╝███████╗██║ ╚████║██║███████╗
    ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚══════╝

TuxGenie v4.6 — Your wish is my command 🐧
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
import subprocess, urllib.request, urllib.error, threading, shutil
try:
    import termios, tty as _tty
    _HAS_TERMIOS = True
except ImportError:
    _HAS_TERMIOS = False

__version__ = "5.22.0"
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Anthropic SDK (auto-installed on first run if missing) ────
try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None

try:
    import readline
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
import builtins
builtins.input = _safe_input

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — ANSI + UI
# ═══════════════════════════════════════════════════════════════════════════════
R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"; ITALIC="\033[3m"
# Standard colours
GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"
CYAN="\033[36m"; BLUE="\033[34m"; MAGENTA="\033[35m"; WHITE="\033[37m"
# Bright / vivid variants — the "light theme" feel
BRED="\033[91m"; BGREEN="\033[92m"; BYELLOW="\033[93m"
BBLUE="\033[94m"; BMAGENTA="\033[95m"; BCYAN="\033[96m"; BWHITE="\033[97m"
# 256-colour extras for a modern palette
ORANGE="\033[38;5;208m"; PINK="\033[38;5;213m"; LIME="\033[38;5;118m"
GOLD="\033[38;5;220m";   CORAL="\033[38;5;203m"; TEAL="\033[38;5;43m"
INDIGO="\033[38;5;135m"; SKY="\033[38;5;117m";   PEACH="\033[38;5;216m"
# Background colours for card/section headers
BG_RED="\033[41m"; BG_GREEN="\033[42m"; BG_BLUE="\033[44m"
BG_MAGENTA="\033[45m"; BG_CYAN="\033[46m"
BG_DARK="\033[48;5;235m";  BG_NAVY="\033[48;5;17m"
BG_PURPLE="\033[48;5;55m"; BG_TEAL="\033[48;5;23m"
BG_ORANGE="\033[48;5;130m";BG_FOREST="\033[48;5;22m"

def C(text, *codes): return "".join(codes)+str(text)+R

def banner():
    _letters = [
        (ORANGE,  "T"), (YELLOW,  "U"), (GREEN,   "X"), (GREEN,   "G"),
        (CYAN,    "E"), (BLUE,    "N"), (MAGENTA, "I"), (RED,     "E"),
    ]
    _logo = "".join(f"{col}{BOLD}{ch}{R}" for col, ch in _letters)
    _line = f"  {DIM}{'─'*66}{R}"

    print(f"""
{_line}
  {CYAN}{BOLD}🐧{R}  {_logo}   {DIM}v{__version__} · Free forever · Powered by Claude{R}
  {BOLD}Your friendly AI assistant for Linux{R}  {DIM}— no experience needed!{R}
{_line}
  {GREEN}{BOLD}✔{R}  {BOLD}Type anything in plain English{R}    {DIM}e.g. "my wifi stopped working"{R}
  {GREEN}{BOLD}✔{R}  {BOLD}Or pick a number from the menu{R}     {DIM}e.g. "2" for Health Check{R}
  {GREEN}{BOLD}✔{R}  {BOLD}Or run any terminal command directly{R}  {DIM}e.g. "ls -la"{R}
{_line}
  {BLUE}{BOLD}🌐 www.tuxgenie.com{R}  {DIM}· Dedicated to Linus Torvalds · Built by Aspera Technologies{R}
{_line}
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
HISTORY_FILE = os.path.join(CFG_DIR, "history.json")
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


def _try_pip_install():
    """Try to install the anthropic SDK using every known pip method.
    Returns True on success."""
    attempts = [
        [sys.executable, "-m", "pip", "install", "anthropic", "--quiet", "--upgrade"],
        [sys.executable, "-m", "pip", "install", "anthropic", "--quiet", "--upgrade", "--break-system-packages"],
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

def _bootstrap_anthropic_sdk():
    """Install the anthropic SDK using every strategy available.
    Tries: existing pip → apt install pip → ensurepip → venv fallback.
    Returns True if the SDK is importable afterward."""
    import importlib

    # Quick check: maybe it's already installed
    try:
        importlib.import_module("anthropic")
        return True
    except ImportError:
        pass

    print(f"  {CYAN}Installing anthropic SDK…{R}")

    # Strategy 1: pip already available
    if _try_pip_install():
        return True

    # Strategy 2: install python3-pip via apt, then retry
    print(f"  {DIM}pip not found — installing python3-pip…{R}")
    subprocess.run(["sudo", "apt-get", "install", "-y", "python3-pip"],
                   capture_output=True)
    if _try_pip_install():
        return True

    # Strategy 3: ensurepip (Python's built-in pip bootstrapper, works offline)
    print(f"  {DIM}Trying ensurepip…{R}")
    try:
        subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"],
                       capture_output=True, timeout=60)
        if _try_pip_install():
            return True
    except Exception:
        pass

    # Strategy 4: create a temporary venv (has its own pip), install there,
    # then add the venv's site-packages to sys.path so we can import
    print(f"  {DIM}Trying venv fallback…{R}")
    venv_dir = os.path.join(os.path.expanduser("~"), ".local", "share",
                            "tuxgenie", ".bootstrap-venv")
    try:
        # Ensure python3-venv is available
        subprocess.run(["sudo", "apt-get", "install", "-y", "python3-venv"],
                       capture_output=True, timeout=120)
    except Exception:
        pass
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
        self.client     = None
        self._session_input_tokens  = 0
        self._session_output_tokens = 0
        if not self._no_key:
            self._init_client(api_key)

    def _init_client(self, api_key):
        """Bootstrap SDK and create Anthropic client."""
        global _anthropic
        if _anthropic is None:
            if not _bootstrap_anthropic_sdk():
                print(f"\n  {RED}{BOLD}Could not install the anthropic SDK.{R}")
                print(f"  TuxGenie will try to fix this automatically…\n")
                print(f"  {CYAN}Running: sudo apt install -y python3-pip python3-venv{R}")
                subprocess.run(["sudo", "apt-get", "install", "-y",
                                "python3-pip", "python3-venv"])
                print(f"\n  {CYAN}Running: pip3 install anthropic{R}")
                subprocess.run([sys.executable, "-m", "pip", "install",
                                "anthropic", "--break-system-packages"])
                try:
                    import anthropic as _anth
                    _anthropic = _anth
                except ImportError:
                    print(f"\n  {RED}{BOLD}Still could not import anthropic.{R}")
                    print(f"  Please run these commands and restart tuxgenie:\n")
                    print(f"    {CYAN}sudo apt install -y python3-pip python3-venv{R}")
                    print(f"    {CYAN}pip3 install anthropic --break-system-packages{R}\n")
                    input(f"  Press Enter to close...")
                    sys.exit(1)
            if _anthropic is None:
                import anthropic as _anth
                _anthropic = _anth
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

    def select_model_for_task(self, user_text: str, round_num: int = 1):
        """Auto-select the cheapest model that can handle the task.
        Round 1 simple tasks → Haiku. Retries or complex → Sonnet."""
        if not self.auto_model:
            return  # user manually picked a model, respect it
        if round_num > 1:
            # If first attempt failed, escalate to Sonnet
            if self.model != _SONNET_MODEL and self.base_model != "claude-opus-4-6":
                self.model = _SONNET_MODEL
            return
        if self.base_model != "claude-opus-4-6":
            self.model = _HAIKU_MODEL
        else:
            self.model = self.base_model

    def ask(self, system, messages, max_tokens=4096):
        """Streaming call — prints a live progress counter while receiving."""
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
        chunks = []
        char_count = 0
        with self.client.messages.stream(
            model=self.model, max_tokens=max_tokens,
            system=system, messages=messages
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
                char_count += len(text)
                print(f"\r  {CYAN}⚡ Receiving… {char_count} chars{R}", end="", flush=True)
        # Track token usage from the stream's final message
        final = stream.get_final_message()
        if final and final.usage:
            self._session_input_tokens  += final.usage.input_tokens
            self._session_output_tokens += final.usage.output_tokens
        print(f"\r  {GREEN}✓ Response received ({char_count} chars)   {R}")
        return "".join(chunks)

    def session_cost_estimate(self) -> str:
        """Return estimated session cost based on tracked tokens."""
        # Pricing per million tokens (approximate, as of 2025)
        model_prices = {
            "claude-opus-4-6":          (15.0, 75.0),   # input, output per 1M tokens
            "claude-sonnet-4-6":        (3.0, 15.0),
            "claude-haiku-4-5-20251001":(0.80, 4.0),
        }
        # Use average pricing since model may switch mid-session
        p_in, p_out = model_prices.get(self.model, (3.0, 15.0))
        cost = (self._session_input_tokens * p_in + self._session_output_tokens * p_out) / 1_000_000
        return (f"Session tokens: ~{self._session_input_tokens:,} in + "
                f"~{self._session_output_tokens:,} out · "
                f"Est. cost: ${cost:.4f}")

# ── Config / API key ─────────────────────────────────────────────────────────
_NO_KEY = "__NO_KEY__"   # sentinel — user chose to skip key setup

def _load_api_key(cfg):
    """Get API key from env, config, old installs, or prompt user."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key: return key
    key = cfg.get("api_key", "").strip()
    if key: return key
    # Migrate from old ai-terminal install
    try:
        old = json.loads(open(os.path.expanduser("~/.config/ai-terminal/config.json")).read())
        k = old.get("api_key","").strip()
        if k:
            ok("API key migrated from ai-terminal — no need to re-enter!")
            return k
    except Exception:
        pass
    # Ask user — with option to skip and add later
    _line = f"  {DIM}{'─'*54}{R}"
    print(f"\n{_line}")
    print(f"  {YELLOW}{BOLD}🔑 Anthropic API Key Setup{R}")
    print(f"{_line}")
    print(f"\n  TuxGenie needs an API key to use AI features")
    print(f"  (diagnosis, fixes, script generation, etc.)\n")
    print(f"  {GREEN}{BOLD}✔{R}  Terminal commands ALWAYS work — no key needed")
    print(f"  {GREEN}{BOLD}✔{R}  250+ Linux commands run free, instantly\n")
    print(f"  Get your free key at: {CYAN}{BOLD}https://console.anthropic.com{R}")
    print(f"  Costs ~ a few cents/session via Anthropic (we earn nothing)\n")
    print(f"  {DIM}Press Enter to skip for now — type {BOLD}k{R}{DIM} anytime to add key later{R}\n")
    try:
        key = input("  Paste API key (or press Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)
    if not key:
        print(f"\n  {YELLOW}Continuing without API key.{R}")
        print(f"  {DIM}Terminal commands work fine. Type {BOLD}k{R}{DIM} whenever you want to enable AI.{R}\n")
        return _NO_KEY
    return key

def load_backend():
    """Load config and return a single AnthropicBackend."""
    cfg = load_cfg()
    key = _load_api_key(cfg)
    model = cfg.get("model", "claude-haiku-4-5-20251001")
    if key != _NO_KEY:
        save_cfg({"api_key": key})   # only persist real keys
    return AnthropicBackend(api_key=key, model=model)

AVAILABLE_MODELS = [
    ("claude-haiku-4-5-20251001", "Fast & cheapest — handles 90% of tasks perfectly (recommended)"),
    ("claude-sonnet-4-6",   "Smarter — for complex debugging (auto-escalates when needed)"),
    ("claude-opus-4-6",     "Most capable — for the hardest problems (costs 20x more)"),
]

def feat_set_api_key(backend):
    """Set or update the Anthropic API key — command: k"""
    hdr("Connect Anthropic API Key")
    if not backend._no_key and backend.api_key:
        masked = backend.api_key[:8] + "…" + backend.api_key[-4:]
        info(f"Current key: {CYAN}{masked}{R}  (AI features are active)")
    else:
        print(f"\n  {YELLOW}No API key set — AI features are currently disabled.{R}")
    print(f"\n  Get your free key at: {CYAN}{BOLD}https://console.anthropic.com{R}")
    print(f"  {DIM}Cost: ~$0.25 per million tokens via Anthropic (Haiku model)")
    print(f"  A typical session costs a fraction of a cent. We earn nothing.{R}\n")
    try:
        key = input("  Paste API key (or press Enter to cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not key:
        warn("No key entered. Nothing changed.")
        return
    backend._set_key(key)

def feat_settings(backend, bctx, slog):
    """Settings: view/change API key and model."""
    hdr("Settings")
    info(f"Backend: {backend.label()}")
    auto_tag = C(" (auto-routing ON)", GREEN) if backend.auto_model else ""
    print(f"  {DIM}Smart model routing:{R}{auto_tag}")
    if backend._session_input_tokens > 0:
        print(f"  {DIM}{backend.session_cost_estimate()}{R}")
    print(f"\n  {C('[1]',CYAN)} Change API key")
    print(f"  {C('[2]',CYAN)} Change model")
    print(f"  {C('[3]',CYAN)} Toggle smart model routing (auto Haiku/Sonnet)")
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
            backend._set_key(key)
            ok("API key updated — active now.")
    elif ch == "2":
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
        print(f"\r  {' ' * (len(self._msg)+10)}\r", end="", flush=True)
    def _spin(self):
        i = 0
        while not self._stop.wait(0.08):
            print(f"\r  {CYAN}{self._FRAMES[i % len(self._FRAMES)]}{R} {self._msg}",
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

CRITICAL — Empty output awareness:
- If a command returns exit code 0 but EMPTY output when output was expected
  (e.g. grep found nothing, curl returned nothing, apt-cache search found
  nothing), treat that as INCONCLUSIVE, not success.
- An empty grep result means the thing you searched for does NOT exist.
- An empty curl result means the download FAILED.

- RETURN ONLY VALID JSON.
"""

DANGER_RE = [
    r"rm\s+-[rf]{1,2}\s+/\s*$",    # rm -rf / (root only)
    r"rm\s+-[rf]{1,2}\s+/\s+\*",  # rm -rf / * (root with wildcard)
    r"rm\s+-[rf]{1,2}\s+~\s*$",   # rm -rf ~ (home root only)
    r"rm\s+-[rf]{1,2}\s+~/\s*$",  # rm -rf ~/ (home root only)
    r"rm\s+--no-preserve-root",   # explicit override of safety guard
    r"\bdd\s+if=", r"\bmkfs\b", r"\bfdisk\b",
    r"\bwipefs\b", r"\bshred\b",
    r">\s*/dev/sd",               # overwrite disk directly
    r":\(\)\{\s*:\|:&\s*\};:",    # fork bomb (with optional spaces)
    r"chmod\s+-[Rr]\s+[0-7]*7[0-7]*\s+/",
    r"chmod\s+777\s+/",
]
def is_dangerous(cmd):
    return any(re.search(p, cmd) for p in DANGER_RE)

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

# Session flag: once user presses 'a', all future safe/moderate passthrough
# commands run without asking. Dangerous commands always ask regardless.
_passthrough_auto = False

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

def try_passthrough(user_input, session_log):
    """
    If user_input looks like a shell command, run it directly without
    calling Claude. Works for ANY command in PATH — not just a fixed list.
    Returns True if handled, False to fall back to AI (natural language).
    """
    cmd = user_input.strip()
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

    print(f"  {CYAN}▶ Running…{R}")
    rc, stdout, stderr = run_cmd_live(exec_cmd, sudo_password=sudo_pw)
    ok("Done.") if rc == 0 else warn(f"Exited with code {rc}.")

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
    import traceback as _tb
    tb_text = _sanitize_tb("".join(_tb.format_exception(exc_type, exc_val, exc_tb)))
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

    def _reader(stream, buf, color):
        try:
            for raw in stream:
                line = raw.decode('utf-8', errors='replace').rstrip('\n')
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
                if line.strip():
                    print(f"  {color}{line}{R}", flush=True)
        except Exception:
            pass
        finally:
            stream.close()

    try:
        proc = subprocess.Popen(
            actual_cmd, shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=8192,
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
        t_out.start(); t_err.start()

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
        t_out.join(5); t_err.join(5)

        return proc.returncode, '\n'.join(stdout_lines), '\n'.join(stderr_lines)
    except Exception as e:
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
            "3-6 sentences. No JSON. No markdown."
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
        answer = answer.strip()
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
    backend.select_model_for_task(user_text, round_num=1)
    print(f"\n  {CYAN}{BOLD}⚡ AI: {backend.label()}{R}")

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
        if analysis:
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
        yes_to_all   = False

        for i, step in enumerate(steps, 1):
            step_failed       = False
            output_has_errors = False
            risk    = step.get("risk", "safe").lower()
            cmd     = step.get("command", "").strip()
            desc    = step.get("description", "")
            root    = step.get("requires_root", False)
            exp_out = step.get("expected_output", "")
            meaning = step.get("what_this_means", "")

            if is_dangerous(cmd):
                risk = "dangerous"

            pct = int(i / len(steps) * 100)
            bar = C("█" * int(pct/5), CYAN) + C("░" * (20 - int(pct/5)), DIM)
            rb  = {"safe":     C(" SAFE ",    GREEN,  BOLD),
                   "moderate": C(" WORKING ", CYAN,   BOLD),
                   "dangerous":C(" RISKY ",   RED,    BOLD),
                  }.get(risk, C(f" {risk.upper()} ", DIM))

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
                # Check output for failure patterns even when rc == 0
                combined_out = (stdout + "\n" + stderr).lower()
                _FAIL_PATTERNS = [
                    "error:", "failed", "not found", "no such file",
                    "permission denied", "unable to locate",
                    "could not resolve", "404 not found", "403 forbidden",
                    "connection refused", "E: ", "dpkg: error",
                    "is not installed", "no candidates",
                ]
                # ── Don't error-check echo payloads in fallback commands ──
                # e.g. `which foo || echo 'foo is not installed'` — the echo is
                # intentional confirmation output, not an actual error.
                if "|| echo" in cmd and rc == 0:
                    output_has_errors = False
                else:
                    output_has_errors = any(p.lower() in combined_out for p in _FAIL_PATTERNS)

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
                    ok("This step completed successfully.")
                elif exit1_is_ok:
                    # grep/which/type exit 1 = "not found" — that's a valid result
                    ok("Nothing found (this is the expected result).")
                elif downloaded_html:
                    warn("Downloaded an HTML page instead of a real file. The AI will fix this.")
                    step_failed = True
                elif rc == 0 and expects_output and empty_output:
                    warn("Command returned empty output — result is inconclusive. The AI will review.")
                    step_failed = True
                elif rc == 0 and output_has_errors:
                    warn("Command ran but output suggests a problem. The AI will review this.")
                    step_failed = True
                elif rc == 127:
                    warn("That program is not installed on this system — the AI will find another way.")
                    step_failed = True
                elif rc == -1:
                    warn("Command timed out. The AI will try a different approach.")
                    step_failed = True
                else:
                    print(C(f"  ✗ Exit {rc}", RED))
                    warn("This step had an issue. The AI will look at this and try to fix it.")
                    step_failed = True

                # ── Auto-mode circuit breaker ──
                # If a step fails, stop auto-running — re-plan is needed
                if step_failed and yes_to_all:
                    yes_to_all = False
                    warn("Auto-mode paused — a step failed. Remaining steps need review.")

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
        verified = False

        if verify_cmd:
            print(f"\n{'─'*60}")
            print(f"  {CYAN}{BOLD}Verifying task completion…{R}")
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
                verified = True
                print(f"\n  {GREEN}{BOLD}✓ VERIFIED — Task completed successfully!{R}")
                if plan.get("needs_synthesis"):
                    _synthesize_findings(backend, user_text, step_outputs)
                elif sc:
                    info(sc)
                print(f"  {DIM}Long live Linux! 🐧{R}")
                _ask_rating()
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
                return

        if rnd >= max_rounds:
            warn(f"We've tried {max_rounds} rounds. If it's still not fixed:")
            info("Try asking on https://askubuntu.com or https://reddit.com/r/linux4noobs")
            return

        # ── Better error feedback to AI ──
        # Clearly tell the AI what failed, what worked, and what NOT to repeat
        failed_steps = [s for s in step_outputs if not s.get("success", True) and not s.get("skipped")]
        passed_steps = [s for s in step_outputs if s.get("success", False)]
        tried_cmds   = [s.get("command","") for s in step_outputs if not s.get("skipped")]

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
    return ctx

# ── FEATURE 1: Fix Issue (general) ───────────────────────────────────────────
def feat_fix(backend, bctx, slog):
    hdr("Fix Issue — Describe your problem")
    try:
        issue = input(f"\n{BOLD}{BLUE}What's the problem?{R} ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not issue: return
    sys_p = BASE_SYS + _sys_ctx_block(bctx)
    fix_engine(backend, sys_p, [{"role":"user","content":issue}], slog)

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
        path = input(f"\n{BOLD}Which file/folder has permission issues? (path or description):{R}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
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
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # List existing backups
    existing = sorted([
        f for f in os.listdir(BACKUPS_DIR) if f.endswith(".tar.gz")
    ], reverse=True)
    if existing:
        section("Existing backups")
        for b in existing[:5]:
            path = os.path.join(BACKUPS_DIR, b)
            size = os.path.getsize(path)
            info(f"{b}  ({size//1024} KB)")

    section("Creating new backup")
    archive = os.path.join(BACKUPS_DIR, f"tuxgenie_backup_{ts}.tar.gz")
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
    if not app:
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
        deb_url = deb_name = None
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith("_all.deb"):
                deb_url  = asset["browser_download_url"]
                deb_name = asset["name"]
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

        _do_update_install(deb_url, deb_name, latest)

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
    """Parse version string '4.1.0' into tuple (4, 1, 0)."""
    try:    return tuple(int(x) for x in str(v).strip().split("."))
    except: return (0,)

def _version_gap(current, latest):
    """Return how many releases behind (major=10, minor=1, patch=1).
    4.2.0→4.2.1 = 1, 4.1→4.2 = 1, 4.0→4.2 = 2, 4.0→5.0 = 10."""
    c, l = _ver(current), _ver(latest)
    if l <= c:
        return 0
    # Pad to 3 elements
    c = c + (0,) * (3 - len(c))
    l = l + (0,) * (3 - len(l))
    # Major version diff counts as 10
    major_gap = (l[0] - c[0]) * 10
    minor_gap = l[1] - c[1]
    patch_gap = l[2] - c[2]
    total = major_gap + minor_gap
    # If only patch changed (same major.minor), still count as 1
    if total == 0 and patch_gap > 0:
        return 1
    return max(total, 0)

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

def _do_update_install(deb_url, deb_name, latest):
    """Download and install a .deb update. Returns True on success."""
    tmp_deb = os.path.join("/tmp", deb_name)
    print(f"\n  {CYAN}▶ Downloading v{latest}…{R}", flush=True)
    try:
        def _progress(count, block, total):
            if total > 0:
                pct = min(100, int(count * block * 100 / total))
                bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                print(f"\r  {CYAN}{bar}{R} {pct}%", end="", flush=True)
        urllib.request.urlretrieve(deb_url, tmp_deb, _progress)
        print()
    except Exception as e:
        err(f"Download failed: {e}"); return False
    ok(f"Downloaded {deb_name}")

    print(f"\n  {CYAN}▶ Installing v{latest}…{R}")
    try:
        inst_pw = get_or_cache_sudo_password()
    except KeyboardInterrupt:
        warn("Installation cancelled."); return False
    rc, _, _ = run_cmd_live(f"sudo dpkg -i {shlex.quote(tmp_deb)}", sudo_password=inst_pw)
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
        latest    = cache["latest"]
        deb_url   = cache.get("deb_url")
        deb_name  = cache.get("deb_name")
        notes     = cache.get("notes", "")
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
            deb_url = deb_name = None
            for asset in data.get("assets", []):
                if asset.get("name", "").endswith("_all.deb"):
                    deb_url  = asset["browser_download_url"]
                    deb_name = asset["name"]
                    break
            # Save to cache
            _save_update_cache({
                "last_check": now, "latest": latest,
                "deb_url": deb_url, "deb_name": deb_name, "notes": notes,
            })
        except Exception:
            # Offline or server error — skip silently, never block the user
            return

    if not latest:
        return

    gap = _version_gap(__version__, latest)

    if gap <= 0:
        return  # Already up to date

    # ── 1 minor version behind: recommend (yellow banner, skippable) ──
    if gap == 1:
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
                _do_update_install(deb_url, deb_name, latest)
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
                _do_update_install(deb_url, deb_name, latest)
                return  # if install failed, loop back to ask again
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

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 8 — SESSION SAVE
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
#  SECTION 9 — MENU + MAIN REPL
# ═══════════════════════════════════════════════════════════════════════════════
MENU_ITEMS = [
    ("1",  "fix",       "Fix Issue",          "Describe any Linux problem",              feat_fix),
    ("2",  "health",    "Health Dashboard",   "Full CPU/RAM/disk/service health scan",   feat_health),
    ("3",  "packages",  "Package Wizard",     "Find & install software by description",  feat_packages),
    ("4",  "network",   "Network Doctor",     "Diagnose & fix connectivity",             feat_network),
    ("5",  "security",  "Security Audit",     "Harden firewall, SSH, open ports",        feat_security),
    ("6",  "disk",      "Disk Detective",     "Find space hogs & clean up safely",       feat_disk),
    ("7",  "drivers",   "Driver Check",       "Detect & install missing drivers",        feat_drivers),
    ("8",  "services",  "Service Manager",    "Optimise startup & running services",     feat_services),
    ("9",  "logs",      "Log Analyser",       "Decode cryptic errors & system logs",     feat_logs),
    ("10", "updates",   "Update Advisor",     "Safe upgrade analysis & ordering",        feat_updates),
    ("11", "script",    "Script Generator",   "Describe a task → get a bash script",     feat_script),
    ("12", "cron",      "Cron Assistant",     "Schedule tasks in plain English",         feat_cron),
    ("13", "perms",     "Permission Doctor",  "Diagnose & fix permission denied errors", feat_perms),
    ("14", "boot",      "Boot Analyser",      "Find why boot is slow & speed it up",     feat_boot),
    ("15", "docker",    "Docker Helper",      "Container troubleshooting & cleanup",     feat_docker),
    ("16", "backup",    "Config Backup",      "Snapshot all system configs to .tar.gz",  feat_backup),
    ("17", "hardware",  "Hardware Info",      "Full hardware report & health check",     feat_hardware),
    ("18", "ssh",       "SSH Wizard",         "Set up & harden SSH securely",            feat_ssh),
    ("19", "processes", "Process Inspector",  "Tame CPU/memory hogs & zombie processes", feat_processes),
    ("20", "rollback",  "Session Rollback",   "Undo changes made in a previous session", feat_rollback),
    ("21", "git",       "Git Helper",         "Understand diffs, fix conflicts, undo commits", feat_git),
    ("22", "sound",     "Sound Fix",          "No audio, mic not working, HDMI sound",   feat_sound),
    ("23", "display",   "Display Fix",        "Wrong resolution, monitor not detected",  feat_display),
    ("24", "bluetooth", "Bluetooth Fix",      "Pairing fails, device not found",         feat_bluetooth),
    ("25", "printer",   "Printer Setup",      "Install printer, fix printing problems",  feat_printer),
    ("26", "webcam",    "Webcam Fix",         "Camera not detected, black screen",       feat_webcam),
    ("27", "appswitch", "App Finder",         "Find Linux equivalents of Windows apps",  feat_appswitch),
    ("28", "battery",   "Battery & Power",    "Improve battery life, fix overheating",   feat_battery),
    ("29", "perf",      "Performance Boost",  "Full audit + apply all safe speed fixes", feat_performance),
    ("s",  "settings",  "Settings",           "Configure API key and model",             feat_settings),
    ("f",  "feedback",  "Feature Request",    "Suggest a new feature",                   feat_feedback),
]

def show_menu():
    def _cat(bg, icon, title, subtitle):
        print(f"\n  {bg}{BWHITE}{BOLD}  {icon} {title}  {R}  {DIM}{subtitle}{R}")

    def _item(num, label, tip):
        # Pad BEFORE adding ANSI codes — otherwise f-string width counts invisible escape chars
        num_s   = f"[{num}]".ljust(5)
        label_s = label.ljust(26)
        print(f"    {BLUE}{BOLD}{num_s}{R}  {BOLD}{label_s}{R}  {DIM}{tip}{R}")

    print(f"\n  {BG_NAVY}{BWHITE}{BOLD}  🐧 What would you like to do today?  {R}")

    _cat(BG_FOREST, "🔧", "FIX & TROUBLESHOOT", "Having a problem? Start here")
    _item("1",  "Fix a Problem",       "Describe what's wrong in plain English")
    _item("4",  "Fix Internet / WiFi", "Can't connect? Slow internet?")
    _item("7",  "Fix Missing Drivers", "WiFi, GPU, or printer not working?")
    _item("13", "Fix Permissions",     "'Permission denied' errors")
    _item("22", "Fix Sound / Audio",   "No sound, mic not working, HDMI audio?")
    _item("23", "Fix Display",         "Wrong resolution, monitor not detected?")
    _item("24", "Fix Bluetooth",       "Device won't pair or keeps disconnecting?")
    _item("25", "Set Up Printer",      "Install printer or fix printing problems")
    _item("26", "Fix Webcam",          "Camera not working in Zoom / Teams / Meet?")

    _cat(BG_TEAL, "🌍", "SWITCHING TO LINUX?", "Coming from Windows or Mac?")
    _item("27", "Find Linux App",      '"What replaces Photoshop / Word / iTunes?"')

    _cat(BG_PURPLE, "📊", "CHECK & MONITOR", "See how your computer is doing")
    _item("2",  "System Health Check", "Is everything running OK?")
    _item("9",  "Explain Error Logs",  "Decode confusing error messages")
    _item("17", "Hardware Info",       "What's inside my computer?")
    _item("19", "Running Programs",    "What's using CPU / memory?")

    _cat(BG_ORANGE, "📦", "INSTALL & UPDATE", "Get software and stay up to date")
    _item("3",  "Install Software",    '"I need a video editor" → installed')
    _item("10", "Check for Updates",   "Keep your system safe and current")

    _cat(BG_NAVY, "🛡️ ", "SECURITY & SAFETY", "Protect your computer")
    _item("5",  "Security Check",      "Are you protected? Find out now")
    _item("16", "Backup Settings",     "Save your config before making changes")
    _item("20", "Undo Changes",        "Oops? Roll back what TuxGenie did")

    _cat(BG_DARK, "⚡", "POWER TOOLS", "For when you're feeling adventurous")
    _item("29", "Performance Boost",   "🚀 Full audit + apply ALL safe speed fixes")
    _item("6",  "Free Up Disk Space",  "Running out of storage?")
    _item("8",  "Manage Services",     "Speed up startup, fix service failures")
    _item("11", "Generate a Script",   '"Back up my files nightly" → bash script')
    _item("12", "Schedule a Task",     "Run things automatically on a schedule")
    _item("14", "Speed Up Boot",       "Computer starts slowly? Fix it")
    _item("15", "Docker Help",         "Container troubleshooting & cleanup")
    _item("18", "SSH Setup",           "Remote access to another computer")
    _item("21", "Git Helper",          "Fix conflicts, undo commits, explain diffs")
    _item("28", "Battery & Power",     "Battery draining fast? Laptop overheating?")

    print(f"""
  {BG_DARK}{BWHITE}  {C('[s]',GOLD,BOLD)} Settings   {C('[u]',BCYAN,BOLD)} Update   {C('[h]',BMAGENTA,BOLD)} History   {C('[f]',PINK,BOLD)} Suggest Feature   {C('[q]',BRED,BOLD)} Quit  {R}

  {BGREEN}{BOLD}💡 TIP:{R} {BOLD}You don't need to pick a number!{R}
     Just type what you need, like:
     {BLUE}{BOLD}\"my wifi is not working\"{R}   {BLUE}{BOLD}\"install chrome\"{R}   {BLUE}{BOLD}\"why is it slow?\"{R}
""")

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

  {GREEN}{BOLD}Or pick a number:{R}  Type a number from the menu (1-28)

  {GREEN}{BOLD}Safety:{R}
    Before running any command, TuxGenie will:
    {GREEN}{BOLD}✓{R} Explain what it does in plain English
    {GREEN}{BOLD}✓{R} Show if it's safe, careful, or risky
    {GREEN}{BOLD}✓{R} Ask for your permission first
    {GREEN}{BOLD}✓{R} You can always say {BOLD}s{R} to skip or {BOLD}q{R} to stop

  {GREEN}{BOLD}Commands:{R}
    {BLUE}{BOLD}help{R}     Show this help
    {BLUE}{BOLD}menu{R}     Show the feature menu
    {BMAGENTA}{BOLD}h{R}        Show recent history (last 10 tasks)
    {BLUE}{BOLD}k{R}        Add / change API key (needed for AI features)
    {BLUE}{BOLD}u{R}        Update TuxGenie to latest version
    {RED}{BOLD}q{R}        Quit TuxGenie
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
  commands and runs them {BOLD}only after you say yes{R}.

  {CYAN}{BOLD}Quick example:{R}
    You type:  {CYAN}\"my wifi is not connecting\"{R}
    TuxGenie:  Finds the problem, explains it, and fixes it

  {YELLOW}{BOLD}🔑 You're always in control:{R}
    Every command is shown to you first. You decide what runs.
    If something looks wrong, just type {BOLD}s{R} to skip it.

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
                if rc == 0:
                    ok(desc)
                else:
                    warn(f"{desc} — had an issue, continuing anyway.")

        print(f"\n  {GREEN}{BOLD}✓ Setup complete! Your Linux is ready.{R}\n")

    try:
        open(flag, "w").write("1")
    except Exception:
        pass

def main():
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
    args = parser.parse_args()

    banner()
    startup_update_check()
    backend = load_backend()

    with Spinner("Collecting system info…"):
        bctx = base_ctx()
    ok("System info collected")
    print(f"  {CYAN}{BOLD}Your system:{R}  {BOLD}{bctx['os']}{R}  {DIM}· {bctx['kernel']} · {bctx['arch']}{R}")

    session_log: list = []
    feature_map      = {num: fn   for num, _, name, _, fn in MENU_ITEMS}
    keyword_map      = {kw:  fn   for _, kw, name, _, fn  in MENU_ITEMS}
    feature_name_map = {num: name for num, _, name, _, _  in MENU_ITEMS}
    feature_kw_map   = {num: kw   for num, kw, _, _, _    in MENU_ITEMS}

    # ── One-shot mode: tuxgenie "describe problem" ────────────────────────────
    if args.issue:
        if not try_passthrough(args.issue, session_log):
            sys_p = BASE_SYS + _sys_ctx_block(bctx)
            fix_engine(backend, sys_p, [{"role": "user", "content": args.issue}], session_log)
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
            choice = input(f"\n  {BGREEN}{BOLD}❯{R} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n  {GOLD}{BOLD}✨ Goodbye! Long Live Linux 🐧{R}")
            if hasattr(backend, '_session_input_tokens') and backend._session_input_tokens > 0:
                print(f"  {DIM}{backend.session_cost_estimate()}{R}")
            print(f"  {DIM}Thank you for using TuxGenie · {BLUE}www.tuxgenie.com{R}{DIM} · Aspera Technologies{R}\n")
            break

        if not choice:
            continue
        if choice.lower() in EXIT_WORDS:
            print(f"\n  {GOLD}{BOLD}✨ Goodbye! Long Live Linux 🐧{R}")
            print(f"  {DIM}Thank you for using TuxGenie · {BLUE}www.tuxgenie.com{R}{DIM} · Aspera Technologies{R}\n")
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

        if choice in feature_map:
            fn = feature_map[choice]
            if fn is None:
                continue
            _active_feature = choice
            fn(backend, bctx, session_log)
            save_session(session_log)
            _history_append(feature_name_map.get(choice, choice), feature_kw_map.get(choice, choice))
            print(f"\n  {DIM}Type a number, describe a problem, or {BLUE}{BOLD}menu{R} {DIM}/ {BLUE}{BOLD}k{R}{DIM}=key / {BLUE}{BOLD}u{R}{DIM}=update / {RED}{BOLD}q{R}{DIM}=quit{R}")
        else:
            # Natural language → try direct passthrough first, then AI
            passed = try_passthrough(choice, session_log)
            if not passed:
                sys_p = BASE_SYS + _sys_ctx_block(bctx)
                fix_engine(backend, sys_p, [{"role": "user", "content": choice}], session_log)
            save_session(session_log)
            _history_append(choice, "terminal" if passed else "fix")
            print(f"\n  {DIM}Type a number, describe a problem, or {BLUE}{BOLD}menu{R} {DIM}/ {BLUE}{BOLD}k{R}{DIM}=key / {BLUE}{BOLD}u{R}{DIM}=update / {RED}{BOLD}q{R}{DIM}=quit{R}")

    save_session(session_log)

if __name__ == "__main__":
    _active_feature = "startup"
    try:
        main()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}{BOLD}Goodbye! Long Live Linux 🐧{R}\n")
    except Exception:
        import sys as _sys
        report_crash(*_sys.exc_info(), feature=_active_feature)
