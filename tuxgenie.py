#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 ████████╗██╗   ██╗██╗  ██╗ ██████╗ ███████╗███╗   ██╗██╗███████╗
    ██╔══╝██║   ██║╚██╗██╔╝██╔════╝ ██╔════╝████╗  ██║██║██╔════╝
    ██║   ██║   ██║ ╚███╔╝ ██║  ███╗█████╗  ██╔██╗ ██║██║█████╗
    ██║   ██║   ██║ ██╔██╗ ██║   ██║██╔══╝  ██║╚██╗██║██║██╔══╝
    ██║   ╚██████╔╝██╔╝ ██╗╚██████╔╝███████╗██║ ╚████║██║███████╗
    ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚══════╝

TuxGenie v4.2 — Your wish is my command 🐧
AI-powered Linux assistant · Powered by Claude · Free forever

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
  "We are committed to making the world a better place, one command
   at a time." — https://github.com/ramchandragada/tuxgenie
"""

import os, sys, json, re, stat, tarfile, datetime, textwrap, time, shlex, argparse
import subprocess, urllib.request, urllib.error, threading
try:
    import termios, tty as _tty
    _HAS_TERMIOS = True
except ImportError:
    _HAS_TERMIOS = False

__version__ = "4.2.0"
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

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — ANSI + UI
# ═══════════════════════════════════════════════════════════════════════════════
R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"
CYAN="\033[36m"; BLUE="\033[34m"; MAGENTA="\033[35m"; WHITE="\033[37m"
BG_RED="\033[41m"; BG_GREEN="\033[42m"; BG_BLUE="\033[44m"

def C(text, *codes): return "".join(codes)+str(text)+R

def banner():
    print(f"""
{BLUE}{BOLD}
  ████████╗██╗   ██╗██╗  ██╗ ██████╗ ███████╗███╗   ██╗██╗███████╗
     ██╔══╝██║   ██║╚██╗██╔╝██╔════╝ ██╔════╝████╗  ██║██║██╔════╝
     ██║   ██║   ██║ ╚███╔╝ ██║  ███╗█████╗  ██╔██╗ ██║██║█████╗
     ██║   ██║   ██║ ██╔██╗ ██║   ██║██╔══╝  ██║╚██╗██║██║██╔══╝
     ██║   ╚██████╔╝██╔╝ ██╗╚██████╔╝███████╗██║ ╚████║██║███████╗
     ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚══════╝{R}
{MAGENTA}{BOLD}        Your AI assistant for Linux — no experience needed 🐧{R}
{DIM}        v{__version__} · Free forever · Powered by Claude{R}

{GREEN}{BOLD}  Welcome!{R} TuxGenie helps you fix, manage, and understand your
  Linux computer using plain English. Just describe what you need
  and TuxGenie will guide you step by step.

  {CYAN}Nothing runs without your permission.{R} You're always in control.

{DIM}  Dedicated to Linus Torvalds — Creator of the Linux Kernel 🐧
  Built with love by Aspera Technologies · Open Source · Free Forever{R}
""")

def hdr(title, width=64):
    print(f"\n{BLUE}{BOLD}{'─'*width}{R}")
    print(f"{BLUE}{BOLD}  {title}{R}")
    print(f"{BLUE}{BOLD}{'─'*width}{R}")

def section(title):
    print(f"\n{CYAN}{BOLD}  ▸ {title}{R}")

def ok(msg):  print(f"  {C('✓', GREEN, BOLD)} {msg}")
def warn(msg):print(f"  {C('⚠', YELLOW, BOLD)} {msg}")
def err(msg): print(f"  {C('✗', RED, BOLD)} {msg}")
def info(msg):print(f"  {C('·', BLUE)} {msg}")

def trunc(text, max_lines):
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    hidden = len(lines) - max_lines
    return "\n".join(lines[:max_lines]) + f"\n{C(f'  … [{hidden} more lines]', DIM)}"

def print_output(rc, stdout, stderr):
    if stdout:
        print(f"\n{C('  OUTPUT:', GREEN)}\n{DIM}{trunc(stdout,25)}{R}")
    if rc != 0 and stderr:
        print(f"\n{C('  STDERR:', RED)}\n{DIM}{trunc(stderr,10)}{R}")
    print(C("  ✓ OK", GREEN) if rc == 0 else C(f"  ✗ Exit {rc}", RED))

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — CONFIG  (persistent API key + session log path)
# ═══════════════════════════════════════════════════════════════════════════════
CFG_DIR      = os.path.expanduser("~/.config/tuxgenie")
CFG_FILE     = os.path.join(CFG_DIR, "config.json")
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
# Simple tasks (install X, update, restart service) use Haiku (~80% cheaper).
# Complex tasks (debugging, security audit, multi-step fixes) use Sonnet.
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

def _classify_task(text: str) -> str:
    """Return 'haiku' for simple tasks, 'sonnet' for complex ones."""
    t = text.lower()
    complex_score = sum(1 for k in _COMPLEX_KEYWORDS if k in t)
    simple_score  = sum(1 for k in _SIMPLE_KEYWORDS  if k in t)
    if complex_score > simple_score:
        return "sonnet"
    if simple_score > 0 and complex_score == 0:
        return "haiku"
    return "sonnet"  # default to sonnet when uncertain

class AnthropicBackend:
    def __init__(self, api_key, model="claude-sonnet-4-6"):
        global _anthropic
        if _anthropic is None:
            print("  Installing anthropic SDK…")
            installed = False
            # Try all known methods to install anthropic
            attempts = [
                [sys.executable, "-m", "pip", "install", "anthropic", "--quiet", "--upgrade"],
                [sys.executable, "-m", "pip", "install", "anthropic", "--quiet", "--upgrade", "--break-system-packages"],
                ["pip3", "install", "anthropic", "--quiet", "--upgrade"],
                ["pip3", "install", "anthropic", "--quiet", "--upgrade", "--break-system-packages"],
            ]
            for attempt in attempts:
                try:
                    if subprocess.run(attempt, capture_output=True).returncode == 0:
                        installed = True; break
                except FileNotFoundError:
                    continue
            if not installed:
                # pip itself missing — try installing it first via apt
                print("  pip not found — installing it now…")
                subprocess.run(["sudo", "apt-get", "install", "-y", "python3-pip"],
                               capture_output=True)
                for attempt in attempts:
                    try:
                        if subprocess.run(attempt, capture_output=True).returncode == 0:
                            installed = True; break
                    except FileNotFoundError:
                        continue
            if not installed:
                print(f"\n  {RED}{BOLD}Could not install the anthropic SDK.{R}")
                print(f"  Please run this command manually and restart tuxgenie:")
                print(f"\n    {CYAN}sudo apt install python3-pip && pip3 install anthropic{R}\n")
                sys.exit(1)
            import anthropic as _anth
            _anthropic = _anth
        self.model  = model
        self.base_model = model  # user's chosen model (for settings)
        self.auto_model = True   # enable smart model routing by default
        self.client = _anthropic.Anthropic(api_key=api_key)
        self._session_input_tokens  = 0
        self._session_output_tokens = 0

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
        complexity = _classify_task(user_text)
        if complexity == "haiku" and self.base_model != "claude-opus-4-6":
            self.model = _HAIKU_MODEL
        else:
            self.model = self.base_model

    def ask(self, system, messages, max_tokens=4096):
        """Streaming call — prints a live progress counter while receiving."""
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
def _load_api_key(cfg):
    """Get API key from env, config, old installs, or prompt user."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key: return key
    key = cfg.get("api_key", "").strip()
    if key: return key
    # Migrate from old tiers config
    for t in ("tier1","tier2","tier3"):
        tc = cfg.get("tiers",{}).get(t,{})
        if tc.get("backend") == "anthropic" and tc.get("api_key","").strip():
            return tc["api_key"].strip()
    for field in ("tier1_api_key","tier2_api_key","tier3_api_key"):
        k = cfg.get(field,"").strip()
        if k: return k
    # Migrate from old ai-terminal install
    try:
        old = json.loads(open(os.path.expanduser("~/.config/ai-terminal/config.json")).read())
        k = old.get("api_key","").strip()
        if k:
            ok("API key migrated from ai-terminal — no need to re-enter!")
            return k
    except Exception:
        pass
    # Ask user
    print(f"\n  Get your API key at: {CYAN}https://console.anthropic.com{R}\n")
    try:
        key = input("  Paste Anthropic API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)
    if not key:
        print(C("No key provided.", RED)); sys.exit(1)
    return key

def load_backend():
    """Load config and return a single AnthropicBackend."""
    cfg = load_cfg()
    key = _load_api_key(cfg)
    model = cfg.get("model", "claude-sonnet-4-6")
    save_cfg({"api_key": key})
    return AnthropicBackend(api_key=key, model=model)

AVAILABLE_MODELS = [
    ("claude-opus-4-6",     "Most capable — best for complex tasks (slower, costs more)"),
    ("claude-sonnet-4-6",   "Best balance of speed and capability (recommended)"),
    ("claude-haiku-4-5-20251001", "Fastest and cheapest — good for simple tasks"),
]

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
            save_cfg({"api_key": key})
            backend.client = _anthropic.Anthropic(api_key=key)
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
  "resolved": false
}

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
- RETURN ONLY VALID JSON.
"""

DANGER_RE = [
    r"rm\s+-[rf]{1,2}\s+/",       # rm -rf /anything
    r"rm\s+-[rf]{1,2}\s+~",       # rm -rf ~/anything
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

def ask_ai(backend, system, messages, max_tokens=4096):
    return backend.ask(system, messages, max_tokens=max_tokens)

def clean_json(text):
    text = re.sub(r"^```(?:json)?\s*\n?","",text.strip(),flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$","",text.strip(),flags=re.MULTILINE)
    return text.strip()

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
    subprocess.Popen(f"xdg-open {shlex.quote(url)} 2>/dev/null",
                     shell=True, start_new_session=True)

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
        print(f"  {DIM}Share TuxGenie → https://github.com/{_GITHUB_REPO}{R}")
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

def feat_feedback():
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

def step_prompt(cmd, risk, yes_to_all):
    hard_danger = is_dangerous(cmd)
    if yes_to_all and not hard_danger and risk != "dangerous":
        print(C("  ⚡ Running automatically…", CYAN))
        return "run"
    # Beginner-friendly safety explanation
    safety = {
        "safe":      (GREEN,  "SAFE — just looks at info, changes nothing"),
        "moderate":  (YELLOW, "CAREFUL — makes a change, but it's reversible"),
        "dangerous": (RED,    "RISKY — this could break things if wrong"),
    }
    col, explain = safety.get(risk.lower(), (DIM, ""))
    print(f"\n  {col}{BOLD}  {explain}  {R}")
    while True:
        try:
            print(f"\n    {C('y',GREEN,BOLD)} = yes, run it    {C('s',YELLOW,BOLD)} = skip this step    {C('q',RED,BOLD)} = stop everything")
            if not hard_danger and risk != "dangerous":
                print(f"    {C('a',CYAN,BOLD)} = run all safe steps automatically")
            ch = input(f"\n  {BOLD}Your choice:{R} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "abort"
        if ch in ("y","yes"):
            return "run"
        if ch in ("a","all") and not hard_danger and risk != "dangerous":
            return "run_all"
        if ch in ("a","all"):
            warn("This step needs explicit 'y' because it could be risky."); continue
        if ch in ("n","no","skip","s"):
            return "skip"
        if ch in ("abort","q","exit","quit","stop"):
            return "abort"
        if len(ch) > 10:
            warn("It looks like you pasted a command. Please use this prompt to approve/skip steps.")
            print(C("  If you want to run your own commands, press q to quit this task first.", DIM))
        else:
            print(C("  Just type: y, s, or q", DIM))

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

def fix_engine(backend, system, messages, session_log, max_rounds=10):
    """
    Runs the AI→display→execute→iterate loop.
    backend: AnthropicBackend instance
    session_log: list, commands are appended for rollback.
    """
    if not backend:
        err("No AI backend configured. Run settings to set up your API key.")
        return

    # ── Smart model routing: pick cheapest model for the task ──
    user_text = messages[0].get("content", "") if messages else ""
    backend.select_model_for_task(user_text, round_num=1)
    print(f"\n  {CYAN}{BOLD}⚡ AI: {backend.label()}{R}")

    for rnd in range(1, max_rounds+1):
        hdr(f"Round {rnd}/{max_rounds}")

        # Escalate model on retry rounds (Haiku failed → Sonnet)
        if rnd > 1:
            backend.select_model_for_task(user_text, round_num=rnd)

        # Prune old messages to prevent token bloat
        messages = _prune_messages(messages)

        # Dynamic max_tokens: simple tasks need less output
        out_tokens = 2048 if _classify_task(user_text) == "haiku" else 4096

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

        step_outputs    = []
        aborted         = False
        yes_to_all      = False

        for i, step in enumerate(steps, 1):
            step_failed     = False
            output_has_errors = False
            risk    = step.get("risk","safe").lower()
            cmd     = step.get("command","").strip()
            desc    = step.get("description","")
            root    = step.get("requires_root", False)
            exp_out = step.get("expected_output","")
            meaning = step.get("what_this_means","")

            if is_dangerous(cmd):
                risk = "dangerous"

            # Visual safety badge
            rb = {
                "safe":     C(" ✓ SAFE ",      GREEN,  BOLD),
                "moderate": C(" ⚠ CAREFUL ",   YELLOW, BOLD),
                "dangerous":C(" ✗ RISKY ",      RED,    BOLD),
            }.get(risk, C(f" {risk.upper()} ", DIM))
            root_b = f"  {C('🔑 needs admin password', YELLOW)}" if root else ""

            pct = int(i / len(steps) * 100)
            bar_filled = int(pct / 5)
            bar = C("█" * bar_filled, CYAN) + C("░" * (20 - bar_filled), DIM)
            print(f"\n{'─'*60}")
            print(f"  {BOLD}Step {i} of {len(steps)}{R}  {rb}  {bar} {CYAN}{BOLD}{pct}%{R}")
            print(f"  {desc}")
            if root_b:
                print(root_b)
            if meaning:
                print(f"  {CYAN}→ What happens:{R} {meaning}")
            if cmd:
                print(f"\n  {DIM}Command:{R} {C(cmd,CYAN)}")
            if exp_out:
                print(f"  {DIM}You should see:{R} {exp_out}")
            if risk == "dangerous":
                print(f"\n  {BG_RED}{BOLD}  ⚠  WARNING: This could cause damage — read carefully!  ⚠  {R}")

            if not cmd:
                info("(just information — nothing to run)"); continue

            choice = step_prompt(cmd, risk, yes_to_all)

            if choice == "run_all":
                yes_to_all = True
                choice     = "run"
                ok("Auto-mode ON — safe steps will run without asking.")
                warn("Risky steps will still ask you first.")

            if choice == "abort":
                warn("Stopped. Nothing else will run."); aborted = True; break

            if choice == "skip":
                print(C("  ↳ Skipped this step.", YELLOW))
                step_outputs.append({"step":i,"command":cmd,"skipped":True})
                continue

            sudo_pw = None
            if cmd.strip().startswith("sudo"):
                try:
                    sudo_pw = get_or_cache_sudo_password()
                except KeyboardInterrupt:
                    warn("Stopped. Nothing else will run."); aborted = True
                if aborted:
                    break

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
                output_has_errors = any(p.lower() in combined_out for p in _FAIL_PATTERNS)

                if rc == 0 and not output_has_errors:
                    ok("This step completed successfully.")
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

            entry = {"step":i,"command":cmd,"returncode":rc,
                     "stdout":stdout[:1500],"stderr":stderr[:500],
                     "success": rc == 0 and not output_has_errors}
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
            v_has_errors = any(p.lower() in v_combined for p in [
                "error:", "not found", "not installed", "no such file",
                "failed", "inactive", "dead",
            ])
            if v_rc == 0 and not v_has_errors:
                verified = True
                print(f"\n  {GREEN}{BOLD}✓ VERIFIED — Task completed successfully!{R}")
                if sc:
                    info(sc)
                print(f"  {DIM}Long live Linux! 🐧{R}")
                _ask_rating()
                return
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

        feedback = "NOT YET RESOLVED.\n\n"
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
    ok("Data collected")

    sys_p = BASE_SYS + """
Additional instructions for HEALTH CHECK mode:
- Analyse CPU, memory, disk, failed services, zombie processes, temperatures.
- Report any anomalies or warnings.
- If everything looks healthy, say so explicitly and return resolved:true.
- Suggest preventive maintenance steps even if nothing is broken.
""" + _sys_ctx_block(ctx)

    msg = "Please perform a full system health check and report any issues or warnings."
    fix_engine(backend, sys_p, [{"role":"user","content":msg}], slog)

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
    hdr("Update Advisor — Safe upgrade analysis")
    with Spinner("Checking for updates…"):
        ctx = {**bctx, **update_ctx()}
    ok("Update info collected")
    sys_p = BASE_SYS + """
Additional instructions for UPDATE ADVISOR mode:
- List pending updates grouped by: Security (critical), Major version bumps, Regular updates.
- Warn about packages that commonly cause breakage on upgrade.
- Recommend a safe upgrade order.
- Suggest taking a snapshot/backup before major updates.
- If no updates available, confirm system is up to date.
""" + _sys_ctx_block(ctx)
    msg = "Analyse pending updates and tell me which are safe to apply and in what order."
    fix_engine(backend, sys_p, [{"role":"user","content":msg}], slog)

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
    ok("Hardware info collected")

    sys_p = f"""You are TuxGenie, hardware expert.
Analyse the system hardware and produce a clear, structured report.

Return JSON with:
- analysis: comprehensive plain-English hardware summary
- steps: [checks to verify hardware health, benchmark commands, optional upgrades]
- success_check: "Your hardware report is complete"
- resolved: false (so we can show all steps)

System data: {json.dumps(ctx, indent=2)}
RETURN ONLY VALID JSON."""

    msg = "Give me a complete hardware report and flag any concerns."
    fix_engine(backend, sys_p, [{"role":"user","content":msg}], slog)

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
    hdr("Process Inspector — Tame runaway processes")
    ps_ctx = {
        **bctx,
        "top_cpu":    _r("ps aux --sort=-%cpu | head -15"),
        "top_mem":    _r("ps aux --sort=-%mem | head -15"),
        "zombies":    _r("ps aux | awk '$8==\"Z\"'"),
        "load_avg":   _r("cat /proc/loadavg"),
        "open_files": _r("lsof 2>/dev/null | wc -l"),
        "threads":    _r("ps -eLf | wc -l"),
    }
    try:
        problem = input(f"\n{BOLD}Describe the issue (or Enter for general analysis):{R}\n{C('(e.g. 100% CPU, out of memory, zombie processes)',DIM)}\n> ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not problem:
        problem = "Analyse processes: find CPU/memory hogs, zombies, and suggest fixes."

    sys_p = BASE_SYS + """
Additional instructions for PROCESS INSPECTOR mode:
- Identify which process is the problem and WHY it's misbehaving.
- Suggest: nice/renice, kill signals (SIGTERM before SIGKILL), ulimits.
- For memory leaks: identify the process and suggest restart/update.
- Explain zombie processes and how to clean them up safely.
- Provide commands to monitor the fix in real time.
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
    fix_engine(backend, sys_p, [{"role": "user", "content": problem}], slog)

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
    fix_engine(backend, sys_p, [{"role": "user", "content": problem}], slog)

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
    fix_engine(backend, sys_p, [{"role": "user", "content": problem}], slog)

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
    fix_engine(backend, sys_p, [{"role": "user", "content": problem}], slog)

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
            "wake_locks":    "cat /proc/wakelocks 2>/dev/null | head -10",
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
    fix_engine(backend, sys_p, [{"role": "user", "content": problem}], slog)

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
    fix_engine(backend, sys_p, [{"role": "user", "content": problem}], slog)

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
    fix_engine(backend, sys_p, [{"role": "user", "content": problem}], slog)

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
        notes  = (data.get("body") or "")[:400].strip()
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
            info("Download: https://github.com/ramchandragada/tuxgenie/releases/latest")
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
        info("Manual download: https://github.com/ramchandragada/tuxgenie/releases/latest")
    except Exception as e:
        warn(f"Update check failed: {e}")

# ── Startup update check ─────────────────────────────────────────────────────
_UPDATE_CACHE = os.path.join(CFG_DIR, "update_check.json")

def _ver(v):
    """Parse version string '4.1.0' into tuple (4, 1, 0)."""
    try:    return tuple(int(x) for x in str(v).strip().split("."))
    except: return (0,)

def _version_gap(current, latest):
    """Return how many minor versions behind: 4.0→4.2 = 2, 4.0→5.0 = 10."""
    c, l = _ver(current), _ver(latest)
    if l <= c:
        return 0
    # Major version diff counts as 10 minors
    return (l[0] - c[0]) * 10 + (l[1] if len(l) > 1 else 0) - (c[1] if len(c) > 1 else 0)

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
    # Check cache — only hit the network once per day
    cache = _load_update_cache()
    last_check = cache.get("last_check", 0)
    now = time.time()
    one_day = 86400

    if now - last_check < one_day and cache.get("latest"):
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
            notes  = (data.get("body") or "")[:300].strip()
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
    ("s",  "settings",  "Settings",           "Configure API key and model",             feat_settings),
    ("f",  "feedback",  "Feature Request",    "Suggest a new feature",                   None),
]

def show_menu():
    W = 70
    print(f"\n{BLUE}{BOLD}{'━'*W}{R}")
    print(f"{BLUE}{BOLD}  What would you like to do?{R}")
    print(f"{BLUE}{BOLD}{'━'*W}{R}")

    # Grouped categories for beginners
    print(f"\n  {GREEN}{BOLD}🔧 FIX & TROUBLESHOOT{R}  {DIM}— Having a problem? Start here{R}")
    print(f"    {C('[1]',CYAN,BOLD)}  Fix a Problem         {DIM}Describe what's wrong in plain English{R}")
    print(f"    {C('[4]',CYAN,BOLD)}  Fix Internet/WiFi     {DIM}Can't connect? Slow internet?{R}")
    print(f"    {C('[7]',CYAN,BOLD)}  Fix Missing Drivers   {DIM}WiFi, GPU, printer not working?{R}")
    print(f"    {C('[13]',CYAN,BOLD)} Fix Permissions       {DIM}'Permission denied' errors{R}")
    print(f"    {C('[22]',CYAN,BOLD)} Fix Sound/Audio       {DIM}No sound, mic not working, HDMI audio?{R}")
    print(f"    {C('[23]',CYAN,BOLD)} Fix Display/Screen    {DIM}Wrong resolution, monitor not detected?{R}")
    print(f"    {C('[24]',CYAN,BOLD)} Fix Bluetooth         {DIM}Device won't pair, keeps disconnecting?{R}")
    print(f"    {C('[25]',CYAN,BOLD)} Set Up Printer        {DIM}Install printer or fix printing problems{R}")
    print(f"    {C('[26]',CYAN,BOLD)} Fix Webcam            {DIM}Camera not working in Zoom/Teams/Meet?{R}")

    print(f"\n  {GREEN}{BOLD}🌍 SWITCHING TO LINUX?{R}  {DIM}— Coming from Windows or Mac?{R}")
    print(f"    {C('[27]',CYAN,BOLD)} Find Linux App        {DIM}\"What replaces Photoshop/Word/iTunes?\" {R}")

    print(f"\n  {CYAN}{BOLD}📊 CHECK & MONITOR{R}  {DIM}— See how your computer is doing{R}")
    print(f"    {C('[2]',CYAN,BOLD)}  System Health Check   {DIM}Is everything running OK?{R}")
    print(f"    {C('[9]',CYAN,BOLD)}  Explain Error Logs    {DIM}Decode confusing error messages{R}")
    print(f"    {C('[17]',CYAN,BOLD)} Hardware Info          {DIM}What's inside my computer?{R}")
    print(f"    {C('[19]',CYAN,BOLD)} Running Programs       {DIM}What's using CPU/memory?{R}")

    print(f"\n  {MAGENTA}{BOLD}📦 INSTALL & UPDATE{R}  {DIM}— Get software and stay up to date{R}")
    print(f"    {C('[3]',CYAN,BOLD)}  Install Software      {DIM}\"I need a video editor\" → done{R}")
    print(f"    {C('[10]',CYAN,BOLD)} Check for Updates      {DIM}Keep your system safe and current{R}")

    print(f"\n  {YELLOW}{BOLD}🛡️  SECURITY & SAFETY{R}  {DIM}— Protect your computer{R}")
    print(f"    {C('[5]',CYAN,BOLD)}  Security Check        {DIM}Are you protected? Find out{R}")
    print(f"    {C('[16]',CYAN,BOLD)} Backup Settings        {DIM}Save your config before changes{R}")
    print(f"    {C('[20]',CYAN,BOLD)} Undo Changes           {DIM}Oops? Roll back what TuxGenie did{R}")

    print(f"\n  {BLUE}{BOLD}⚡ POWER TOOLS{R}  {DIM}— For when you're feeling adventurous{R}")
    print(f"    {C('[6]',CYAN,BOLD)}  Free Up Disk Space    {DIM}Running out of storage?{R}")
    print(f"    {C('[8]',CYAN,BOLD)}  Manage Services       {DIM}Speed up startup, fix failures{R}")
    print(f"    {C('[11]',CYAN,BOLD)} Generate a Script      {DIM}\"Back up my files nightly\" → script{R}")
    print(f"    {C('[12]',CYAN,BOLD)} Schedule a Task        {DIM}Run things automatically{R}")
    print(f"    {C('[14]',CYAN,BOLD)} Speed Up Boot          {DIM}Computer starts slowly?{R}")
    print(f"    {C('[15]',CYAN,BOLD)} Docker Help            {DIM}Container troubleshooting{R}")
    print(f"    {C('[18]',CYAN,BOLD)} SSH Setup              {DIM}Remote access to another computer{R}")
    print(f"    {C('[21]',CYAN,BOLD)} Git Helper             {DIM}Fix conflicts, undo commits, explain diffs{R}")
    print(f"    {C('[28]',CYAN,BOLD)} Battery & Power        {DIM}Battery draining fast? Laptop overheating?{R}")

    print(f"\n  {C('[s]',DIM,BOLD)} Settings    {C('[u]',CYAN,BOLD)} Update    {C('[f]',MAGENTA,BOLD)} Suggest a Feature    {C('[q]',RED,BOLD)} Quit")
    print(f"{BLUE}{BOLD}{'━'*W}{R}")
    print(f"""
  {GREEN}{BOLD}💡 EASY TIP:{R} You don't need to pick a number!
     Just type what you need in plain English, like:
     {CYAN}\"my wifi is not working\"{R}  or  {CYAN}\"install chrome\"{R}  or  {CYAN}\"why is it slow?\"{R}
""")

EXIT_WORDS = {"exit","quit","q","bye","logout"}
HELP_WORDS = {"help","h","?","how","what"}

def show_help():
    """Quick help for absolute beginners."""
    print(f"""
{BLUE}{BOLD}{'━'*60}{R}
{BLUE}{BOLD}  How to use TuxGenie{R}
{BLUE}{BOLD}{'━'*60}{R}

  {GREEN}{BOLD}The easy way:{R}  Just type what you need in plain English!

    Examples:
      {CYAN}my wifi stopped working{R}
      {CYAN}install google chrome{R}
      {CYAN}my computer is slow{R}
      {CYAN}how much disk space do I have{R}
      {CYAN}update everything{R}

  {GREEN}{BOLD}Or pick a number:{R}  Type a number from the menu (1-20)

  {GREEN}{BOLD}Safety:{R}
    Before running any command, TuxGenie will:
    {GREEN}✓{R} Explain what it does in plain English
    {GREEN}✓{R} Show if it's safe, careful, or risky
    {GREEN}✓{R} Ask for your permission first
    {GREEN}✓{R} You can always say {BOLD}s{R} to skip or {BOLD}q{R} to stop

  {GREEN}{BOLD}Commands:{R}
    {C('help',CYAN)}     Show this help
    {C('menu',CYAN)}     Show the feature menu
    {C('s',CYAN)}        Change API key
    {C('q',CYAN)}        Quit TuxGenie
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
    print(f"  {DIM}Your system: {bctx['os']} · {bctx['kernel']} · {bctx['arch']}{R}")

    session_log: list = []
    feature_map = {num: fn   for num, _, name, _, fn in MENU_ITEMS}
    keyword_map = {kw:  fn   for _, kw, name, _, fn  in MENU_ITEMS}

    # ── One-shot mode: tuxgenie "describe problem" ────────────────────────────
    if args.issue:
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

    while True:
        try:
            choice = input(f"\n  {BOLD}{BLUE}TuxGenie >{R} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n  {YELLOW}{BOLD}Goodbye! Long Live Linux 🐧{R}")
            if hasattr(backend, '_session_input_tokens') and backend._session_input_tokens > 0:
                print(f"  {DIM}{backend.session_cost_estimate()}{R}")
            print(f"  {DIM}Thank you for using TuxGenie by Aspera Technologies.{R}\n")
            break

        if not choice:
            continue
        if choice.lower() in EXIT_WORDS:
            print(f"\n  {YELLOW}{BOLD}Goodbye! Long Live Linux 🐧{R}")
            print(f"  {DIM}Thank you for using TuxGenie by Aspera Technologies.{R}\n")
            break
        if choice.lower() in HELP_WORDS:
            show_help(); continue
        if choice.lower() == "menu":
            show_menu(); continue
        if choice.lower() in ("u", "update"):
            feat_self_update(); continue
        if choice.lower() in ("f", "feedback", "feature", "suggest"):
            feat_feedback(); continue

        if choice in feature_map:
            fn = feature_map[choice]
            if fn is None:
                continue
            _active_feature = choice
            fn(backend, bctx, session_log)
            save_session(session_log)
            print(f"\n  {DIM}Type a number, describe a problem, or type {BOLD}menu{R}{DIM} / {BOLD}help{R}{DIM} / {BOLD}q{R}")
        else:
            # Natural language → Fix Issue directly
            sys_p = BASE_SYS + _sys_ctx_block(bctx)
            fix_engine(backend, sys_p, [{"role": "user", "content": choice}], session_log)
            save_session(session_log)
            print(f"\n  {DIM}Type a number, describe a problem, or type {BOLD}menu{R}{DIM} / {BOLD}help{R}{DIM} / {BOLD}q{R}")

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
