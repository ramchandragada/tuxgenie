#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TuxGenie Unified Shell — flagship desktop app.

  ~40% modern control deck (WebKitGTK)  |  ~60% live VTE terminal

Tabs: Home (ask + quick actions) · App Store · My Apps.
Install/Remove clicks feed the live TuxGenie session on the right
(install-app / remove-app). Terminal core is unchanged.
Exit code 3 = GTK/VTE unavailable (launcher falls back further).
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import sys
import threading

APP_ID = "com.tuxgenie.TuxGenie"
VERSION = "7.31.0"
# WebKitGTK routinely eats multiple GB of RSS. On small PCs (Mint XFCE thin
# clients, ≤8 GB laptops) prefer the GTK button deck unless the user forces
# the modern panel with TUXGENIE_FORCE_WEBKIT=1.
_WEBKIT_MIN_RAM_GIB = 8.0
_VTE_SCROLLBACK_LINES = 5000
_LIGHT_PULSE_MS = 8000

# Icon candidates per tile — first name that exists in the theme wins.
# Ordered for Mint XFCE / Mint-Y / Papirus (many "engineering" names are missing).
_TILE_ICON_NAMES = {
    "fix": ("system-run", "applications-system", "gtk-execute"),
    "health": ("utilities-system-monitor", "computer", "applications-system"),
    "network": ("network-wireless", "network-idle", "network-workgroup"),
    "sound": ("audio-volume-high", "audio-card", "multimedia-volume-control"),
    "display": ("video-display", "preferences-desktop-display", "computer"),
    "bluetooth": ("bluetooth", "bluetooth-active", "preferences-system-bluetooth"),
    "printer": ("printer", "printer-network", "devices"),
    "webcam": ("camera-web", "camera-video", "camera-photo"),
    "drivers": ("computer", "preferences-system", "applications-system"),
    "apps": ("system-software-install", "applications-other", "package-x-generic"),
    "updates": ("system-software-update", "view-refresh", "software-update-available"),
    "selfupd": ("view-refresh", "system-reboot", "gtk-refresh"),
    "cloud": ("folder-remote", "network-server", "folder"),
    "security": ("security-high", "locked", "dialog-password"),
    "backup": ("drive-harddisk", "drive-harddisk-usb", "media-removable"),
    "perf": ("utilities-system-monitor", "preferences-system", "applications-system"),
    "disk": ("drive-harddisk", "drive-harddisk-system", "folder"),
    "battery": ("battery", "battery-good", "battery-full"),
    "gaming": ("applications-games", "input-gaming", "applications-other"),
    "suggest": ("help-about", "help-contents", "dialog-information"),
    "settings": ("preferences-system", "gtk-preferences", "applications-system"),
    "menu": ("view-list", "gtk-index", "application-menu"),
    "complete": ("emblem-ok", "gtk-ok", "dialog-ok"),
    "tweaks": ("preferences-desktop", "preferences-system", "applications-system"),
    "extensions": ("preferences-desktop", "applications-other", "package-x-generic"),
    "dsettings": ("preferences-desktop", "preferences-system", "gtk-preferences"),
}
# Always-visible glyph if the icon theme has nothing useful (Mint XFCE gaps).
_TILE_ICON_GLYPH = {
    "fix": "🔧", "health": "❤", "network": "📶", "sound": "🔊",
    "display": "🖥", "bluetooth": "🔵", "printer": "🖨", "webcam": "📷",
    "drivers": "⚙", "apps": "📦", "updates": "↻", "selfupd": "⬆",
    "cloud": "☁", "security": "🛡", "backup": "💾", "perf": "⚡",
    "disk": "💿", "battery": "🔋", "gaming": "🎮", "suggest": "💡",
    "settings": "⚙", "menu": "☰", "complete": "✓", "tweaks": "🎛",
    "extensions": "🧩", "dsettings": "⚙",
}

# Home quick actions — curated Wave A (not the full terminal menu).
# kind=sec = section header; tab = Store pane; kw = feed live CLI keyword.
ACTIONS = [
    {"kind": "sec", "label": "Start here"},
    {"id": "fix", "label": "Fix a problem", "tip": "Describe what's wrong in plain English",
     "kind": "kw", "payload": "fix", "accent": "#0d8a9a"},
    {"id": "apps", "label": "App Store", "tip": "Browse & install apps (VLC, browsers, …)",
     "kind": "tab", "payload": "store", "accent": "#d4620f"},
    {"id": "health", "label": "Health check", "tip": "CPU, RAM, disk, services",
     "kind": "kw", "payload": "health", "accent": "#148f6a"},

    {"kind": "sec", "label": "Fix something"},
    {"id": "network", "label": "Wi-Fi / Internet", "tip": "Can't connect? Safe scan + fixes",
     "kind": "kw", "payload": "network", "accent": "#0b7ea8"},
    {"id": "sound", "label": "Sound / Audio", "tip": "No sound or mic issues",
     "kind": "kw", "payload": "sound", "accent": "#1a8a7a"},
    {"id": "display", "label": "Display", "tip": "Wrong resolution or monitor not detected",
     "kind": "kw", "payload": "display", "accent": "#0c7c8e"},
    {"id": "bluetooth", "label": "Bluetooth", "tip": "Won't pair or keeps disconnecting",
     "kind": "kw", "payload": "bluetooth", "accent": "#156f9a"},
    {"id": "printer", "label": "Printer setup", "tip": "Install a printer or fix printing",
     "kind": "kw", "payload": "printer", "accent": "#1a7a6e"},
    {"id": "webcam", "label": "Webcam fix", "tip": "Camera blank in Zoom / Teams / Meet",
     "kind": "kw", "payload": "webcam", "accent": "#0e7a86"},
    {"id": "drivers", "label": "Drivers / NVIDIA", "tip": "Missing GPU or hardware drivers",
     "kind": "kw", "payload": "drivers", "accent": "#0f6f8c"},

    {"kind": "sec", "label": "Install & update"},
    {"id": "updates", "label": "System updates", "tip": "Check and install OS updates",
     "kind": "kw", "payload": "updates", "accent": "#0d6e8c"},
    {"id": "selfupd", "label": "Update TuxGenie", "tip": "Get the latest TuxGenie release",
     "kind": "kw", "payload": "u", "accent": "#c35508"},
    {"id": "cloud", "label": "Cloud sync", "tip": "Google Drive, Dropbox, OneDrive, and more",
     "kind": "kw", "payload": "cloud", "accent": "#0b6f9a"},

    {"kind": "sec", "label": "Protect & speed"},
    {"id": "security", "label": "Security check", "tip": "Are you protected? Find out now",
     "kind": "kw", "payload": "security", "accent": "#1b6b4a"},
    {"id": "backup", "label": "Backup settings", "tip": "Create or restore a config snapshot",
     "kind": "kw", "payload": "backup", "accent": "#1b7a4a"},
    {"id": "perf", "label": "My PC is slow", "tip": "Scan + safe speed fixes",
     "kind": "kw", "payload": "perf", "accent": "#c45c12"},
    {"id": "disk", "label": "Disk cleanup", "tip": "Running out of storage?",
     "kind": "kw", "payload": "disk", "accent": "#b85a18"},
    {"id": "battery", "label": "Battery & power", "tip": "Draining fast or overheating?",
     "kind": "kw", "payload": "battery", "accent": "#c46a10"},
    {"id": "gaming", "label": "Gaming setup", "tip": "Steam + Proton, GPU, GameMode",
     "kind": "kw", "payload": "gaming", "accent": "#a34b1a"},

    {"kind": "sec", "label": "Guided"},
    {"id": "suggest", "label": "Suggest a setup", "tip": "Not sure? One question → right setup",
     "kind": "kw", "payload": "suggest", "accent": "#0e7c86"},

    {"kind": "sec", "label": "More"},
    {"id": "settings", "label": "Settings", "tip": "AI provider, keys, preferences",
     "kind": "kw", "payload": "s", "accent": "#3d5a80"},
    {"id": "menu", "label": "Show menu", "tip": "Full terminal menu for everything else",
     "kind": "kw", "payload": "menu", "accent": "#1a2744"},
]

# GTK fallback (no WebKit): tab → terminal catalog keyword
_TAB_FALLBACK_KW = {"store": "apps", "myapps": "remove", "store-ai": "ai"}


def compose_home_actions():
    """Static Home chips plus a DE-aware “This desktop” section."""
    extra = []
    try:
        import tuxgenie as _tg
        extra = _tg.de_home_actions()
    except Exception:
        extra = []
    if not extra:
        return list(ACTIONS)
    out = []
    inserted = False
    for a in ACTIONS:
        if (not inserted and a.get("kind") == "sec"
                and a.get("label") == "Fix something"):
            out.extend(extra)
            inserted = True
        out.append(a)
    if not inserted:
        out = extra + list(ACTIONS)
    return out


def _resolve_tuxgenie() -> str:
    """Command that starts the TuxGenie next to this file.

    A checkout or PR copy of tuxgenie-app must drive its sibling
    tuxgenie.py. Preferring `which tuxgenie` first silently ran the
    installed /usr/bin/tuxgenie instead.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(here, "tuxgenie.py")
    if os.path.isfile(cand):
        return "%s %s" % (sys.executable, shlex.quote(cand))
    which = shutil.which("tuxgenie")
    if which:
        return which
    lib = "/usr/lib/tuxgenie/tuxgenie.py"
    if os.path.isfile(lib):
        return "%s %s" % (sys.executable, shlex.quote(lib))
    return "tuxgenie"


def _import_tuxgenie():
    """Load tuxgenie module (sibling file or installed package)."""
    try:
        import tuxgenie as tg  # type: ignore
        return tg
    except Exception:
        pass
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tuxgenie.py")
    if not os.path.isfile(path):
        path = "/usr/lib/tuxgenie/tuxgenie.py"
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("tuxgenie", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    # Avoid anthropic hard-fail in odd envs
    if "anthropic" not in sys.modules:
        import types
        sys.modules["anthropic"] = types.ModuleType("anthropic")
    spec.loader.exec_module(mod)
    return mod


def _load_store_catalogs():
    tg = _import_tuxgenie()
    if tg is None:
        return [], []
    try:
        apps = tg.catalog_gui_rows(tg.APP_CATALOG, kind="app")
        ai = tg.catalog_gui_rows(tg.AI_CATALOG, kind="ai")
        return apps, ai
    except Exception as e:
        print("tuxgenie-app: catalog load failed:", e, file=sys.stderr)
        return [], []


def _load_gi():
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Vte", "2.91")
    from gi.repository import Gtk, Gdk, Vte, GLib, Gio  # noqa: F401
    webkit = None
    for ver in ("4.1", "4.0"):
        try:
            gi.require_version("WebKit2", ver)
            from gi.repository import WebKit2
            webkit = WebKit2
            break
        except Exception:
            continue
    return Gtk, Gdk, Vte, GLib, Gio, webkit


def _host_ram_gib() -> float:
    """Installed RAM in GiB — prefer tuxgenie.host_ram_gib when imported."""
    tg = _import_tuxgenie()
    if tg is not None and hasattr(tg, "host_ram_gib"):
        try:
            return float(tg.host_ram_gib() or 0.0)
        except Exception:
            pass
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / (1024 ** 2)
    except Exception:
        pass
    return 0.0


def _prefer_light_deck() -> bool:
    """True when this PC should skip WebKit to save RAM."""
    if os.environ.get("TUXGENIE_FORCE_WEBKIT", "").strip() in ("1", "true", "yes"):
        return False
    if os.environ.get("TUXGENIE_LIGHT_DECK", "").strip() in ("1", "true", "yes"):
        return True
    ram = _host_ram_gib()
    return 0 < ram < _WEBKIT_MIN_RAM_GIB


def _shell_html(version: str, store_apps: list, ai_apps: list, pulse_ms: int = 8000) -> str:
    """Flagship control deck — brand-first, luminous teal, intentional motion.
    Self-contained: no CDN, no remote fonts, no third-party assets."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>TuxGenie</title>
<meta name="color-scheme" content="light only"/>
<style>
  /* Always-light flagship deck — never follow the desktop dark theme. */
  :root {
    color-scheme: light only;
    --ink: #102028;
    --ink2: #243844;
    --muted: #4a6572;
    --fog: #f4f8fb;
    --paper: #f4fafc;
    --panel: #ffffff;
    --ember: #e85d04;
    --ember2: #ff8a2a;
    --tide0: #043844;
    --tide1: #0a6e7a;
    --tide2: #0d8a96;
    --tide3: #2bb8c4;
    --line: rgba(16,48,60,.16);
    --danger: #c2410c;
    --shadow: 0 18px 44px rgba(16,48,64,.10);
    --ease: cubic-bezier(.22,.9,.24,1);
    --chip-bg: #ffffff;
    --card-bg: #ffffff;
    --input-bg: #ffffff;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; height: 100%;
    font-family: "Ubuntu Sans", "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
    color: var(--ink);
    background: var(--fog);
    color-scheme: light only;
    overflow: hidden;
  }
  .app {
    display: flex; flex-direction: column; height: 100%; min-height: 0;
    position: relative;
    background:
      radial-gradient(880px 380px at 0% -10%, #b8f4f866, transparent 58%),
      radial-gradient(720px 360px at 100% 0%, #ffd7b055, transparent 52%),
      linear-gradient(180deg, #fbfefe 0%, #f3f8fb 46%, #eef4f8 100%);
  }
  .app::before {
    content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .35;
    background-image:
      linear-gradient(rgba(6,90,102,.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(6,90,102,.04) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, #000 20%, transparent 75%);
  }

  /* ── Top brand strip ── */
  .top {
    position: relative; z-index: 2;
    flex: 0 0 auto;
    padding: 12px 18px 0;
  }
  .brandrow {
    display: flex; align-items: flex-end; justify-content: space-between; gap: 12px;
  }
  /* logo-contrast: solid ink-teal on white (no clip-text washout in WebKitGTK) */
  .logo {
    font-size: clamp(2rem, 4.2vw, 2.7rem);
    font-weight: 800; letter-spacing: -.04em; line-height: .95;
    margin: 0;
    color: #03313c;
    animation: brandIn .7s var(--ease) both;
  }
  @keyframes brandIn {
    from { opacity: 0; transform: translateY(10px); letter-spacing: .04em; }
    to { opacity: 1; transform: none; letter-spacing: -.04em; }
  }
  .ver {
    font-size: .72rem; color: var(--muted); font-weight: 600;
    letter-spacing: .04em; text-transform: uppercase;
    padding-bottom: 4px; white-space: nowrap;
  }
  a.site {
    color: var(--tide1); text-decoration: none; border-bottom: 1px solid transparent;
    transition: border-color .2s, color .2s;
  }
  a.site:hover { color: var(--ember); border-bottom-color: var(--ember); }

  .nav {
    display: flex; gap: 4px; margin-top: 10px;
    border-bottom: 1px solid var(--line);
  }
  .nav .nav-tab {
    appearance: none; border: 0; background: transparent; cursor: pointer;
    font: inherit; font-weight: 700; font-size: .86rem; color: var(--muted);
    padding: 10px 14px 12px; position: relative;
    transition: color .2s;
  }
  .nav .nav-tab::after {
    content: ""; position: absolute; left: 14px; right: 14px; bottom: -1px; height: 3px;
    border-radius: 3px 3px 0 0;
    background: linear-gradient(90deg, var(--ember), var(--ember2));
    transform: scaleX(0); transform-origin: left;
    transition: transform .28s var(--ease);
  }
  .nav .nav-tab:hover { color: var(--ink2); }
  .nav .nav-tab.active { color: var(--ink); }
  .nav .nav-tab.active::after { transform: scaleX(1); }
  .nav .nav-tab:focus { outline: none; }
  .nav .nav-tab:focus-visible {
    outline: 2px solid rgba(10,138,150,.45); outline-offset: 2px;
  }

  .panel {
    display: none; flex: 1; min-height: 0; flex-direction: column;
    position: relative; z-index: 1;
  }
  .panel.active { display: flex; animation: panelIn .35s var(--ease) both; }
  @keyframes panelIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: none; }
  }

  /* ── HOME (soft-tighten: compact hero so dials sit closer to Ask) ── */
  .hero {
    position: relative; margin: 8px 14px 0; border-radius: 18px;
    overflow: hidden; min-height: 78px;
    color: var(--ink);
    background: linear-gradient(125deg, #e8fafc 0%, #f7fcff 46%, #fff7ef 100%);
    border: 1px solid rgba(18, 140, 152, .14);
    box-shadow: 0 10px 28px rgba(16,48,64,.07);
    isolation: isolate;
  }
  .hero .aurora {
    position: absolute; inset: -30%;
    background:
      radial-gradient(circle at 18% 28%, #7ee8f066, transparent 42%),
      radial-gradient(circle at 82% 18%, #ffc48a55, transparent 44%),
      radial-gradient(circle at 62% 82%, #9be4ec55, transparent 46%);
    animation: aurora 10s ease-in-out infinite alternate;
  }
  @keyframes aurora {
    from { transform: translate3d(-2%, -1%, 0) rotate(0deg); }
    to { transform: translate3d(3%, 2%, 0) rotate(4deg); }
  }
  .hero svg.wave {
    position: absolute; left: 0; right: 0; bottom: -2px; width: 100%; height: 28px;
    opacity: .5;
  }
  .hero .copy {
    position: relative; z-index: 1; padding: 12px 16px 20px;
    max-width: 34rem;
  }
  .hero h2 {
    margin: 0; font-size: clamp(1.05rem, 2.3vw, 1.35rem);
    font-weight: 700; letter-spacing: -.02em; line-height: 1.15;
    color: var(--ink);
  }
  .hero p {
    margin: 4px 0 0; font-size: clamp(.74rem, 1.5vw, .84rem); opacity: .88; line-height: 1.3;
    max-width: 26rem;
  }
  .ember-line {
    margin-top: 6px; height: 3px; width: 48px; border-radius: 3px;
    background: linear-gradient(90deg, var(--ember), var(--ember2));
    animation: sweep 2.4s var(--ease) infinite alternate;
    transform-origin: left;
  }
  @keyframes sweep {
    from { width: 40px; opacity: .85; }
    to { width: 84px; opacity: 1; }
  }

  .ask {
    margin: -18px 14px 0; position: relative; z-index: 3;
    background: #ffffff;
    border: 1px solid rgba(16,48,60,.10);
    border-radius: 18px;
    padding: 10px 11px 8px;
    box-shadow: 0 16px 36px rgba(16,48,64,.10);
  }
  @supports ((-webkit-backdrop-filter: blur(1px)) or (backdrop-filter: blur(1px))) {
    .ask {
      background: var(--panel);
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
    }
  }
  .ask label {
    display: block; font-size: .68rem; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
    margin: 0 0 6px 4px;
  }
  .row { display: flex; gap: 8px; align-items: stretch; }
  .row input {
    flex: 1; min-width: 0; border: 1px solid var(--line); border-radius: 12px;
    padding: 12px 13px; font-size: clamp(.88rem, 1.8vw, .98rem); background: var(--input-bg); color: var(--ink);
    font-family: inherit;
    transition: border-color .2s, box-shadow .2s;
  }
  .row input:focus {
    outline: none; border-color: var(--tide2);
    box-shadow: 0 0 0 3px rgba(14,168,180,.18);
  }
  .row #askBtn {
    border: 0; border-radius: 12px; padding: 0 16px; flex: 0 0 auto;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, var(--ember), var(--ember2));
    color: #fff; font-weight: 800; font-size: .9rem; cursor: pointer;
    letter-spacing: .01em;
    transition: transform .15s var(--ease), filter .15s;
    animation: breath 2.6s ease-in-out infinite;
  }
  .row #askBtn:hover { filter: brightness(1.05); transform: translateY(-1px); }
  .row #askBtn:active { transform: translateY(1px); }
  .row #askBtn:focus { outline: none; }
  .row #askBtn:focus-visible {
    outline: 2px solid rgba(232,93,4,.45); outline-offset: 2px;
  }
  @keyframes breath {
    0%,100% { box-shadow: 0 8px 18px rgba(232,93,4,.28); }
    50% { box-shadow: 0 10px 26px rgba(255,138,42,.38); }
  }
  .ask-tools {
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px;
    margin-top: 6px; padding: 0 2px;
  }
  .health-cta {
    appearance: none; border: 1px solid rgba(14,168,180,.42);
    background: linear-gradient(135deg, #e8f7f8, #fff);
    color: var(--tide0); font: inherit; font-weight: 800; font-size: .78rem;
    padding: 7px 12px; border-radius: 10px; cursor: pointer;
    letter-spacing: .01em;
    transition: transform .15s var(--ease), box-shadow .15s, border-color .15s;
  }
  .health-cta:hover {
    transform: translateY(-1px);
    border-color: var(--tide2);
    box-shadow: 0 8px 18px rgba(6,90,102,.12);
  }
  .health-cta:active { transform: none; }
  .hint {
    margin: 0; font-size: .72rem; color: var(--muted); flex: 1 1 140px;
  }

  .sec {
    padding: 8px 16px 4px; font-size: .66rem; letter-spacing: .12em;
    text-transform: uppercase; color: var(--muted); font-weight: 800;
  }

  /* System pulse — single-tier 1×4 (never wrap to 2×2; frees Quick Actions) */
  .pulse-wrap {
    flex: 0 0 auto;
    padding: 2px 12px 0;
  }
  .pulse-wrap .sec { padding: 4px 6px 3px; }
  .pulse {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    grid-template-rows: auto;
    grid-auto-flow: column;
    gap: clamp(4px, .8vw, 8px);
  }
  .pulse-card {
    appearance: none; border: 1px solid rgba(16,48,60,.16); border-radius: 16px;
    background:
      radial-gradient(120% 90% at 50% 0%, rgba(10,140,152,.10), transparent 55%),
      #ffffff;
    box-shadow: 0 2px 10px rgba(16,48,64,.06);
    padding: clamp(8px, 1.3vw, 14px) 6px clamp(7px, 1vw, 11px);
    cursor: pointer; text-align: center;
    font: inherit; color: inherit; min-width: 0;
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    transition: transform .18s var(--ease), box-shadow .18s, border-color .18s;
    animation: dialIn .55s var(--ease) both;
  }
  .pulse-card:nth-child(2) { animation-delay: .05s; }
  .pulse-card:nth-child(3) { animation-delay: .1s; }
  .pulse-card:nth-child(4) { animation-delay: .15s; }
  @keyframes dialIn {
    from { opacity: 0; transform: translateY(10px) scale(.96); }
    to { opacity: 1; transform: none; }
  }
  .pulse-card:hover {
    transform: translateY(-3px);
    border-color: rgba(10,138,150,.48);
    box-shadow: 0 14px 30px rgba(3,40,48,.12);
  }
  .pulse-card:active { transform: none; }
  .pulse-card .k {
    font-size: .58rem; font-weight: 800; letter-spacing: .08em;
    text-transform: uppercase; color: var(--muted); margin: 1px 0 0;
    max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .pulse-card .s {
    margin: 0; font-size: clamp(.58rem, 1.15vw, .7rem); color: var(--muted); line-height: 1.2;
    max-width: 100%;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .dial, .pc-badge-wrap {
    position: relative;
    width: clamp(52px, 10vw, 72px);
    height: clamp(52px, 10vw, 72px);
    flex: 0 0 auto;
  }
  .dial svg {
    width: 100%; height: 100%; display: block;
    transform: rotate(-90deg);
  }
  .dial .track {
    fill: none; stroke: #c5d4da; stroke-width: 7;
  }
  .dial .arc {
    fill: none; stroke: var(--tide2); stroke-width: 7;
    stroke-linecap: round;
    stroke-dasharray: 175.93;
    stroke-dashoffset: 175.93;
    transition: stroke-dashoffset .6s var(--ease), stroke .25s, filter .25s;
  }
  .pulse-card.ok .arc {
    stroke: var(--tide2);
    filter: drop-shadow(0 0 5px rgba(14,168,180,.32));
  }
  .pulse-card.elev .arc {
    stroke: var(--ember);
    filter: drop-shadow(0 0 5px rgba(232,93,4,.34));
  }
  .pulse-card.crit .arc {
    stroke: var(--danger);
    filter: drop-shadow(0 0 5px rgba(178,58,34,.36));
  }
  .pulse-card.ok .dial-val { color: var(--tide0); }
  .pulse-card.elev .dial-val { color: #b34708; }
  .pulse-card.crit .dial-val { color: var(--danger); }
  .dial-val {
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: clamp(.78rem, 2vw, 1.1rem); font-weight: 800; letter-spacing: -.03em;
    color: var(--ink); pointer-events: none;
  }
  .pc-badge-wrap {
    display: flex; align-items: center; justify-content: center;
  }
  .pc-badge {
    width: 74%; height: 74%; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: clamp(.7rem, 1.6vw, .85rem); font-weight: 800;
    letter-spacing: .06em; color: #fff;
    background: linear-gradient(145deg, var(--tide2), var(--tide0));
    box-shadow: 0 8px 18px rgba(6,90,102,.22);
  }
  .pulse-card.pc .v {
    margin: 0; max-width: 100%;
    font-size: clamp(.58rem, 1.1vw, .7rem); font-weight: 800;
    letter-spacing: -.01em; color: var(--ink); line-height: 1.15;
    display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 1;
    overflow: hidden;
  }

  .qa-head {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 8px; padding: 8px 14px 2px;
  }
  .qa-head .sec { padding: 0; font-size: .7rem; color: var(--ink2); }
  .qa-head .qa-count {
    font-size: .68rem; font-weight: 700; color: var(--muted); letter-spacing: .01em;
  }

  /* action-cards: flat 2-col tiles (Zorin / WebKitGTK — no native glossy chrome) */
  .grid {
    flex: 1; overflow: auto; padding: 2px 12px 14px;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-flex-direction: column; flex-direction: column;
    -webkit-align-content: flex-start; align-content: flex-start;
    gap: 12px;
  }
  .qa-block { width: 100%; }
  .qa-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .sec-inline {
    width: 100%;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-align: center; -webkit-align-items: center; align-items: center;
    gap: 10px;
    margin: 0 0 7px; padding: 0 2px;
    font-size: .68rem; letter-spacing: .1em;
    text-transform: uppercase; color: var(--tide1); font-weight: 800;
  }
  .sec-inline::after {
    content: ""; -webkit-box-flex: 1; -webkit-flex: 1; flex: 1;
    height: 1px; min-width: 12px;
    background: linear-gradient(90deg, rgba(6,90,102,.22), transparent 88%);
  }
  /* Flat action card — match This PC tiles; never paint a glossy pill */
  .tile {
    -webkit-appearance: none; appearance: none;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-align: start; -webkit-align-items: flex-start; align-items: flex-start;
    gap: 10px;
    width: 100%;
    max-width: none;
    border: 1px solid rgba(16,48,60,.16);
    border-radius: 14px;
    background: var(--card-bg);
    background-image: none;
    margin: 0;
    padding: 11px 12px;
    cursor: pointer;
    text-align: left;
    color: var(--ink);
    font: inherit;
    box-sizing: border-box;
    position: relative;
    box-shadow: 0 1px 3px rgba(16,48,64,.06);
    transition: transform .16s var(--ease), box-shadow .16s, border-color .16s,
      background .16s;
    animation: tileIn .35s var(--ease) both;
    animation-delay: calc(var(--i, 0) * 16ms);
  }
  .tile .ico {
    -webkit-flex: 0 0 34px; flex: 0 0 34px;
    width: 34px; height: 34px;
    border-radius: 10px;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-align: center; -webkit-align-items: center; align-items: center;
    -webkit-box-pack: center; -webkit-justify-content: center; justify-content: center;
    background: var(--ico-bg, rgba(14,168,180,.12));
    color: var(--accent, #0a8a96);
  }
  .tile .ico svg { width: 18px; height: 18px; display: block; }
  .tile .meta { min-width: 0; -webkit-box-flex: 1; -webkit-flex: 1; flex: 1; }
  @keyframes tileIn {
    from { opacity: 0; transform: translateY(5px) scale(.98); }
    to { opacity: 1; transform: none; }
  }
  .tile:hover {
    transform: translateY(-2px);
    border-color: rgba(10,138,150,.34);
    box-shadow: 0 10px 22px rgba(3,40,48,.08);
    background: var(--paper);
  }
  .tile:active { transform: translateY(0); }
  .tile:focus { outline: none; }
  .tile:focus-visible {
    outline: 2px solid rgba(10,138,150,.45);
    outline-offset: 2px;
  }
  .tile .name {
    display: block;
    padding-left: 0;
    font-weight: 800;
    font-size: .84rem;
    line-height: 1.25;
    margin: 0;
    letter-spacing: -.02em;
    color: var(--ink);
    white-space: normal;
  }
  .tile .tip {
    display: block;
    margin: 3px 0 0;
    font-size: .7rem;
    line-height: 1.35;
    font-weight: 600;
    color: var(--muted);
  }

  /* ── STORE / MY APPS ── */
  .store-head {
    padding: 14px 18px 0; flex: 0 0 auto;
  }
  .store-head h2 {
    margin: 0; font-size: 1.35rem; font-weight: 800; letter-spacing: -.02em;
  }
  .store-head p { margin: 4px 0 0; color: var(--muted); font-size: .85rem; }
  .store-bar {
    display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 16px 6px;
    align-items: center;
  }
  .store-bar input {
    flex: 1 1 180px; min-width: 140px;
    border: 1px solid var(--line); border-radius: 12px;
    padding: 11px 14px; font-size: .92rem; background: var(--input-bg);
    font-family: inherit;
  }
  .store-bar input:focus {
    outline: none; border-color: var(--tide2);
    box-shadow: 0 0 0 3px rgba(14,168,180,.16);
  }
  .btn-ghost, .btn-primary {
    border-radius: 12px; padding: 10px 14px; font-weight: 800;
    font-size: .8rem; cursor: pointer; font-family: inherit;
  }
  .btn-primary {
    border: 0; color: #fff;
    background: linear-gradient(135deg, var(--tide1), var(--tide2));
  }
  .btn-ghost {
    border: 1px solid var(--line); background: #fff; color: var(--ink2);
  }
  .chips {
    display: flex; flex-wrap: nowrap; gap: 6px; overflow-x: auto;
    padding: 0 16px 10px; scrollbar-width: thin;
  }
  .chips .chip {
    flex: 0 0 auto; border: 1px solid var(--line); background: var(--chip-bg);
    border-radius: 10px; padding: 7px 12px; font-size: .74rem;
    font-weight: 700; cursor: pointer; color: var(--ink2); white-space: nowrap;
    font-family: inherit; transition: background .15s, color .15s, border-color .15s;
  }
  .chips .chip.on {
    background: var(--tide0); color: #fff; border-color: var(--tide0);
  }
  .chips .chip:focus { outline: none; }
  .chips .chip:focus-visible {
    outline: 2px solid rgba(10,138,150,.45); outline-offset: 2px;
  }
  .cards {
    flex: 1; overflow: auto; padding: 2px 12px 18px;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    align-content: start;
  }
  .card {
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-orient: vertical; -webkit-flex-direction: column; flex-direction: column;
    gap: 9px;
    min-width: 0;
    border: 1px solid var(--line); border-radius: 16px;
    background: #ffffff;
    box-shadow: 0 1px 3px rgba(16,48,64,.05);
    padding: 12px 12px 11px;
    transition: transform .18s var(--ease), box-shadow .18s;
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 14px 30px rgba(3,40,48,.10);
  }
  .card-top {
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-align: center; -webkit-align-items: center; align-items: center;
    gap: 10px; min-width: 0;
  }
  .app-ico {
    -webkit-flex: 0 0 56px; flex: 0 0 56px;
    width: 56px; height: 56px; border-radius: 14px;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-align: center; -webkit-align-items: center; align-items: center;
    -webkit-box-pack: center; -webkit-justify-content: center; justify-content: center;
    background: #f3f7f9;
    box-shadow: inset 0 0 0 1px rgba(16,48,60,.08), 0 6px 14px rgba(16,48,64,.07);
    overflow: hidden;
  }
  .app-ico img { width: 100%; height: 100%; object-fit: contain; display: block; }
  .app-ico.missing {
    background: linear-gradient(180deg, #eef6f8, #e4eef2);
  }
  .card-copy { min-width: 0; -webkit-box-flex: 1; -webkit-flex: 1; flex: 1; }
  .card h3 {
    margin: 0; font-size: .8rem; font-weight: 800; letter-spacing: -.02em;
    line-height: 1.25;
    display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2;
    overflow: hidden;
  }
  .card p {
    margin: 3px 0 0; font-size: .68rem; color: var(--muted); line-height: 1.3;
    display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2;
    overflow: hidden;
  }
  .badges { display: flex; flex-wrap: wrap; gap: 3px; margin-top: 0; }
  .badge {
    font-size: .62rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: .05em; padding: 3px 7px; border-radius: 6px;
    background: #e7f4f6; color: var(--tide0);
  }
  .badge.cat { background: #fff1e6; color: #9a3f08; }
  .card .actions { display: flex; flex-direction: column; gap: 6px; margin-top: auto; }
  .card .act {
    border: 0; border-radius: 10px; padding: 8px 10px; font-weight: 800;
    font-size: .74rem; cursor: pointer; white-space: nowrap; font-family: inherit;
    text-align: center; width: 100%;
  }
  .card .act.install {
    background: linear-gradient(135deg, var(--tide1), var(--tide3)); color: #fff;
  }
  .card .act.remove {
    background: linear-gradient(135deg, #9a3320, var(--danger)); color: #fff;
  }
  .card .act:focus { outline: none; }
  .card .act:focus-visible {
    outline: 2px solid rgba(10,138,150,.45); outline-offset: 2px;
  }
  .empty {
    padding: 36px 16px; text-align: center; color: var(--muted); font-size: .92rem;
    grid-column: 1 / -1;
  }
  .status-bar {
    flex: 0 0 auto;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-align: center; -webkit-align-items: center; align-items: center;
    -webkit-box-pack: justify; -webkit-justify-content: space-between; justify-content: space-between;
    gap: 12px;
    padding: 8px 14px 9px 16px;
    background: #ffffff;
    border-top: 1px solid rgba(16,48,60,.12);
    color: var(--muted); font-size: .74rem; letter-spacing: .01em;
    position: relative; z-index: 2;
  }
  .status {
    -webkit-box-flex: 1; -webkit-flex: 1 1 auto; flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .status strong { color: var(--ink); font-weight: 700; }
  /* Aspera wordmark — company attribution (logo-native colors on the light bar) */
  a.aspera-mark {
    -webkit-flex: 0 0 auto; flex: 0 0 auto;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-align: center; -webkit-align-items: center; align-items: center;
    gap: 7px;
    text-decoration: none;
    opacity: .92;
    transition: opacity .2s;
  }
  a.aspera-mark:hover { opacity: 1; }
  a.aspera-mark .by {
    font-size: .62rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #7a90a0;
  }
  a.aspera-mark svg { display: block; height: 14px; width: auto; }
  @media (max-width: 420px) {
    a.aspera-mark .by { display: none; }
  }
  @media (max-width: 400px) {
    .cards { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .card { padding: 8px 7px 8px; }
    .app-ico { width: 44px; height: 44px; -webkit-flex-basis: 44px; flex-basis: 44px; }
  }
  /* Wide control deck */
  @media (min-width: 720px) {
    .dial, .pc-badge-wrap { width: 72px; height: 72px; }
    .dial-val { font-size: .98rem; }
    .pulse-card { padding: 8px 6px 7px; }
    .qa-row { gap: 10px; }
    .tile { padding: 12px 13px; }
  }
  /* Narrow split: keep the 1×4 row, shrink dials so Quick Actions stay visible */
  @media (max-width: 720px) {
    .dial, .pc-badge-wrap { width: 46px; height: 46px; }
    .dial-val { font-size: .72rem; }
    .pulse-card { padding: 6px 3px 5px; gap: 2px; border-radius: 12px; }
    .pulse-card .s { display: none; }
  }
  /* Narrow laptops / small window split */
  @media (max-width: 480px) {
    .top { padding: 8px 10px 0; }
    .logo { font-size: clamp(1.45rem, 7vw, 2rem); }
    .hero { margin: 6px 10px 0; min-height: 58px; }
    .hero .copy { padding: 8px 12px 14px; }
    .ask { margin: -14px 10px 0; padding: 8px; }
    .row { flex-wrap: wrap; }
    .row #askBtn { flex: 1 1 auto; min-height: 40px; }
    .dial, .pc-badge-wrap { width: 52px; height: 52px; }
    .dial-val { font-size: .76rem; }
    .pulse-card { border-radius: 12px; padding: 6px 3px 6px; gap: 2px; }
    .grid { padding: 2px 8px 8px; gap: 10px; }
    .qa-row { grid-template-columns: 1fr; gap: 7px; }
    .tile { padding: 10px 11px; }
    .tile .name { font-size: .8rem; }
  }
  @media (max-width: 360px) {
    .pulse { gap: 5px; }
    .ver .site { display: none; }
  }
  /* Fit Home without scrolling on typical / short laptops */
  @media (max-height: 900px) {
    .hero p { display: none; }
    .ask-tools .hint { display: none; }
    .pulse-card .s { display: none; }
    .dial, .pc-badge-wrap { width: clamp(46px, 8vh, 64px); height: clamp(46px, 8vh, 64px); }
  }
  @media (max-height: 820px) {
    .hero { min-height: 52px; }
    .hero .copy { padding: 8px 12px 14px; }
    .sec-inline { margin-bottom: 5px; }
    .tile { padding: 9px 10px; }
    .tile .tip { display: none; }
    .qa-head { padding-top: 4px; }
  }
  @media (max-height: 720px) {
    .hero { min-height: 44px; }
    .hero .copy { padding: 6px 12px 10px; }
    .ember-line { margin-top: 3px; display: none; }
    .ask { margin-top: -10px; padding: 7px 9px 6px; }
    .health-cta { padding: 5px 10px; font-size: .72rem; }
    .pulse-wrap .sec { font-size: .58rem; }
    .qa-head .sec { font-size: .64rem; }
    .sec { padding-top: 2px; padding-bottom: 1px; }
    .grid { gap: 8px; padding-bottom: 8px; }
    .qa-row { gap: 6px; }
    .tile .ico { width: 30px; height: 30px; -webkit-flex-basis: 30px; flex-basis: 30px; }
  }
  @media (max-height: 600px) {
    .hero { display: none; }
    .ask { margin: 6px 10px 0; }
    .dial, .pc-badge-wrap { width: 40px; height: 40px; }
    .dial-val { font-size: .68rem; }
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation: none !important;
      transition: none !important;
    }
  }
</style>
</head>
<body>
<div class="app">
  <header class="top">
    <div class="brandrow">
      <h1 class="logo">TuxGenie</h1>
      <div class="ver">v__VERSION__ · <a class="site" href="https://www.tuxgenie.com" id="siteLink">www.tuxgenie.com</a></div>
    </div>
    <nav class="nav" id="tabs">
      <div role="tab" tabindex="0" data-tab="home" class="nav-tab active">Home</div>
      <div role="tab" tabindex="0" data-tab="store" class="nav-tab">App Store</div>
      <div role="tab" tabindex="0" data-tab="myapps" class="nav-tab">My Apps</div>
    </nav>
  </header>

  <section class="panel active" id="tab-home">
    <div class="hero">
      <div class="aurora" aria-hidden="true"></div>
      <svg class="wave" viewBox="0 0 1200 80" preserveAspectRatio="none" aria-hidden="true">
        <path fill="rgba(255,255,255,.72)" d="M0,40 C200,80 400,0 600,40 C800,80 1000,10 1200,40 L1200,80 L0,80 Z">
          <animate attributeName="d" dur="8s" repeatCount="indefinite"
            values="M0,40 C200,80 400,0 600,40 C800,80 1000,10 1200,40 L1200,80 L0,80 Z;
                    M0,48 C220,10 420,70 620,30 C820,0 1020,60 1200,36 L1200,80 L0,80 Z;
                    M0,40 C200,80 400,0 600,40 C800,80 1000,10 1200,40 L1200,80 L0,80 Z"/>
        </path>
      </svg>
      <div class="copy">
        <h2>Linux, in plain English</h2>
        <p>Ask anything — approve every step in the live terminal.</p>
        <div class="ember-line" aria-hidden="true"></div>
      </div>
    </div>

    <div class="ask">
      <label for="q">What do you need?</label>
      <div class="row">
        <input id="q" type="text" placeholder="my wifi is not working" autocomplete="off"/>
        <div id="askBtn" role="button" tabindex="0">Ask →</div>
      </div>
      <div class="ask-tools">
        <div role="button" tabindex="0" class="health-cta" id="healthBtn" title="Run a full health check in the live terminal">Health scan →</div>
        <p class="hint">Try “install chrome” · “why is it slow?” · or browse the App Store</p>
      </div>
    </div>

    <div class="pulse-wrap" id="pulseWrap">
      <div class="sec">This PC</div>
      <div class="pulse" id="pulse" aria-label="System pulse">
        <div role="button" tabindex="0" class="pulse-card ok" data-pulse="cpu" title="Open health check">
          <div class="dial" aria-hidden="true">
            <svg viewBox="0 0 72 72">
              <circle class="track" cx="36" cy="36" r="28"/>
              <circle class="arc" id="pulseCpuArc" cx="36" cy="36" r="28"/>
            </svg>
            <div class="dial-val" id="pulseCpu">—</div>
          </div>
          <div class="k">CPU</div>
          <div class="s" id="pulseCpuS">sampling…</div>
        </div>
        <div role="button" tabindex="0" class="pulse-card ok" data-pulse="mem" title="Open health check">
          <div class="dial" aria-hidden="true">
            <svg viewBox="0 0 72 72">
              <circle class="track" cx="36" cy="36" r="28"/>
              <circle class="arc" id="pulseMemArc" cx="36" cy="36" r="28"/>
            </svg>
            <div class="dial-val" id="pulseMem">—</div>
          </div>
          <div class="k">Memory</div>
          <div class="s" id="pulseMemS">used / total</div>
        </div>
        <div role="button" tabindex="0" class="pulse-card ok" data-pulse="disk" title="Open disk tools">
          <div class="dial" aria-hidden="true">
            <svg viewBox="0 0 72 72">
              <circle class="track" cx="36" cy="36" r="28"/>
              <circle class="arc" id="pulseDiskArc" cx="36" cy="36" r="28"/>
            </svg>
            <div class="dial-val" id="pulseDisk">—</div>
          </div>
          <div class="k">Disk</div>
          <div class="s" id="pulseDiskS">used / total</div>
        </div>
        <div role="button" tabindex="0" class="pulse-card pc" data-pulse="pc" title="PC configuration">
          <div class="pc-badge-wrap" aria-hidden="true">
            <div class="pc-badge">PC</div>
          </div>
          <div class="k">PC config</div>
          <div class="v" id="pulsePc">—</div>
          <div class="s" id="pulsePcS">hardware →</div>
        </div>
      </div>
    </div>

    <div class="qa-head">
      <div class="sec">Quick actions</div>
      <div class="qa-count" id="qaCount"></div>
    </div>
    <div class="grid" id="grid"></div>
  </section>

  <section class="panel" id="tab-store">
    <div class="store-head">
      <h2>App Store</h2>
      <p id="storeBlurb">Search, filter, install. Approve steps in the live terminal.</p>
    </div>
    <div class="store-bar">
      <input id="storeQ" type="search" placeholder="Search — chrome, steam, notes…" autocomplete="off"/>
    </div>
    <div class="chips" id="storeChips"></div>
    <div class="cards" id="storeCards"></div>
  </section>

  <section class="panel" id="tab-myapps">
    <div class="store-head">
      <h2>My Apps</h2>
      <p>Apps installed on this PC. System packages stay hidden.</p>
    </div>
    <div class="store-bar">
      <input id="myQ" type="search" placeholder="Search installed apps…" autocomplete="off"/>
      <div role="button" tabindex="0" class="btn-primary" id="refreshInstalled">Refresh</div>
    </div>
    <div class="cards" id="myCards"></div>
  </section>

  <footer class="status-bar">
    <div class="status" id="status"><strong>Ready</strong> — installs confirm in the live terminal (y/n).</div>
    <a class="aspera-mark" id="asperaLink" href="https://www.tuxgenie.com/aspera-hub.html" title="Aspera Technologies">
      <span class="by">by</span>
      <svg viewBox="0 0 118 22" role="img" aria-label="Aspera">
        <!-- Stylized A (no crossbar) + SPERA — matches Aspera wordmark -->
        <path d="M11 2.2 L1.6 19.8 H5.4 L11 8.2 L16.6 19.8 H20.4 L11 2.2 Z" fill="#8FA4FF"/>
        <text x="26" y="16.2" fill="#1a3048" font-family="Ubuntu, Cantarell, Noto Sans, DejaVu Sans, sans-serif" font-size="13.5" font-weight="700" letter-spacing="2.2">SPERA</text>
      </svg>
    </a>
  </footer>
</div>
<script>
  const ACTIONS = __ACTIONS__;
  const STORE_APPS = __STORE__;
  const AI_APPS = __AI__;
  let storeMode = "apps";
  let storeCat = "All";
  let installed = [];

  const status = document.getElementById("status");
  const q = document.getElementById("q");
  const READY = "<strong>Ready</strong> — installs confirm in the live terminal (y/n).";
  let pulseActions = { cpu: "health", mem: "health", disk: "disk", pc: "hardware" };
  let activeTab = "home";

  function setStatus(msg) { status.innerHTML = msg; }

  function post(msg) {
    try {
      if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.tuxgenie) {
        webkit.messageHandlers.tuxgenie.postMessage(JSON.stringify(msg));
        return true;
      }
    } catch (e) {}
    if (typeof window.tuxgenieSend === "function") {
      window.tuxgenieSend(msg);
      return true;
    }
    setStatus("<strong>Bridge offline</strong> — use the terminal on the right.");
    return false;
  }

  function showTab(name) {
    if (name === "store-ai") { storeMode = "ai"; name = "store"; }
    activeTab = name;
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav .nav-tab").forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-tab") === name);
    });
    const panel = document.getElementById("tab-" + name);
    if (panel) panel.classList.add("active");
    if (name === "home") {
      setStatus(READY);
      post({ op: "system-pulse" });
    }
    if (name === "store") renderStore();
    if (name === "myapps") {
      setStatus("<strong>Scanning</strong> — installed apps…");
      post({ op: "list-installed" });
    }
  }

  const DIAL_C = 175.93; // 2π × r28

  function pctClamp(n) {
    n = Number(n);
    if (!isFinite(n) || n < 0) return 0;
    if (n > 100) return 100;
    return n;
  }

  function severity(pct, warnFlag) {
    const p = pctClamp(pct);
    if (warnFlag || p >= 90) return "crit";
    if (p >= 70) return "elev";
    return "ok";
  }

  function setDial(arcId, pct, warn) {
    const el = document.getElementById(arcId);
    if (!el) return;
    const p = pctClamp(pct);
    el.style.strokeDashoffset = String(DIAL_C * (1 - p / 100));
    const card = el.closest(".pulse-card");
    if (!card) return;
    card.classList.remove("ok", "elev", "crit", "warn");
    card.classList.add(severity(p, warn));
  }

  window.__setPulse = function(p) {
    if (!p || typeof p !== "object") return;
    if (p.actions) pulseActions = p.actions;
    const cpu = document.getElementById("pulseCpu");
    const mem = document.getElementById("pulseMem");
    const disk = document.getElementById("pulseDisk");
    const pc = document.getElementById("pulsePc");
    if (cpu) cpu.textContent = (p.cpu_pct != null ? Math.round(p.cpu_pct) + "%" : "—");
    if (mem) mem.textContent = (p.mem_pct != null ? Math.round(p.mem_pct) + "%" : "—");
    if (disk) disk.textContent = (p.disk_pct != null ? Math.round(p.disk_pct) + "%" : "—");
    if (pc) pc.textContent = p.pc_title || "This PC";
    const cpuS = document.getElementById("pulseCpuS");
    const memS = document.getElementById("pulseMemS");
    const diskS = document.getElementById("pulseDiskS");
    const pcS = document.getElementById("pulsePcS");
    if (cpuS) cpuS.textContent = p.cpu_label || "";
    if (memS) memS.textContent = p.mem_label || "";
    if (diskS) diskS.textContent = p.disk_label || "";
    if (pcS) pcS.textContent = p.pc_label || "hardware details →";
    setDial("pulseCpuArc", p.cpu_pct, p.cpu_warn);
    setDial("pulseMemArc", p.mem_pct, p.mem_warn);
    setDial("pulseDiskArc", p.disk_pct, p.disk_warn);
  };

  function runPulse(card) {
    if (!card) return;
    const key = card.getAttribute("data-pulse");
    const kw = pulseActions[key] || key;
    const labelEl = card.querySelector(".k");
    setStatus("<strong>Starting</strong> — " + ((labelEl && labelEl.textContent) || kw));
    post({ op: "run", kind: "kw", payload: kw });
  }
  document.getElementById("pulseWrap").addEventListener("click", (e) => {
    runPulse(e.target.closest("[data-pulse]"));
  });
  document.getElementById("pulseWrap").addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const card = e.target.closest("[data-pulse]");
    if (!card) return;
    e.preventDefault();
    runPulse(card);
  });

  function runText(text) {
    text = (text || "").trim();
    if (!text) {
      setStatus("<strong>Type something first</strong> — e.g. “my wifi is not working”.");
      q.focus();
      return;
    }
    setStatus("<strong>Sending</strong> — " + text.replace(/[<>&]/g, ""));
    post({ op: "run", kind: "text", payload: text });
  }

  function runAction(a) {
    if (!a || a.kind === "sec") return;
    if (a.kind === "tab") {
      if (a.payload === "store-ai") storeMode = "ai";
      if (a.payload === "store") storeMode = "apps";
      showTab(a.payload === "store-ai" ? "store" : a.payload);
      setStatus("<strong>" + a.label + "</strong> — browse and click Install / Remove.");
      return;
    }
    setStatus("<strong>Starting</strong> — " + a.label);
    post({ op: "run", kind: a.kind || "kw", payload: a.payload, label: a.label });
  }

  const ICONS = {
    fix: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
    health: "M22 12h-4l-3 9L9 3l-3 9H2",
    network: "M5 12.55a11 11 0 0 1 14.08 0M1.42 9a16 16 0 0 1 21.16 0M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01",
    sound: "M11 5L6 9H2v6h4l5 4V5zM19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07",
    display: "M8 3h8a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3zM8 21h8M12 17v4",
    bluetooth: "M6.5 6.5l11 11L12 22V2l5.5 4.5-11 11",
    printer: "M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2M6 14h12v8H6z",
    webcam: "M23 7l-7 5 7 5V7zM3 5h11a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z",
    drivers: "M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83",
    apps: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
    updates: "M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5",
    selfupd: "M12 19V5M5 12l7-7 7 7",
    cloud: "M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z",
    security: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
    backup: "M21 8v13H3V8M1 3h22v5H1zM10 12h4",
    perf: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
    disk: "M22 12H2M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11zM6 16h.01M10 16h.01",
    battery: "M17 6H3a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2zM23 13v-2",
    gaming: "M6 12h4M8 10v4M15 13h.01M18 11h.01M2 8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2z",
    suggest: "M12 2a7 7 0 0 1 4 12.7V17H8v-2.3A7 7 0 0 1 12 2zM9 21h6",
    settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9c.3.7.9 1.2 1.6 1.3H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
    menu: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
    complete: "M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11",
    tweaks: "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6",
    extensions: "M12 2l3 7 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z",
    dsettings: "M3 4h18v12H3zM8 20h8M12 16v4"
  };

  function accentRgb(hex) {
    hex = String(hex || "").replace("#", "");
    if (hex.length !== 6) return null;
    return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
  }

  function makeActionTile(a, i) {
    // DIV not <button>: WebKitGTK often paints blank white buttons
    const el = document.createElement("div");
    el.className = "tile";
    el.setAttribute("role", "button");
    el.setAttribute("tabindex", "0");
    el.style.setProperty("--i", String(i));
    const accent = a.accent || "#0a8a96";
    el.style.setProperty("--accent", accent);
    const rgb = accentRgb(accent);
    if (rgb) {
      el.style.setProperty("--ico-bg", "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + ",0.16)");
    }

    const ico = document.createElement("div");
    ico.className = "ico";
    ico.setAttribute("aria-hidden", "true");
    const path = ICONS[a.id] || ICONS.fix;
    ico.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="' + path + '"/></svg>';
    el.appendChild(ico);

    const meta = document.createElement("div");
    meta.className = "meta";
    const name = document.createElement("div");
    name.className = "name";
    name.appendChild(document.createTextNode(a.label || ""));
    meta.appendChild(name);
    if (a.tip) {
      const tip = document.createElement("div");
      tip.className = "tip";
      tip.appendChild(document.createTextNode(a.tip));
      meta.appendChild(tip);
    }
    el.appendChild(meta);

    el.setAttribute("title", a.tip || a.label || "");
    el.addEventListener("click", () => runAction(a));
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        runAction(a);
      }
    });
    return el;
  }

  const grid = document.getElementById("grid");
  let tileI = 0;
  let row = null;
  ACTIONS.forEach((a) => {
    if (a.kind === "sec") {
      const block = document.createElement("div");
      block.className = "qa-block";
      const sec = document.createElement("div");
      sec.className = "sec-inline";
      sec.appendChild(document.createTextNode(a.label || ""));
      block.appendChild(sec);
      row = document.createElement("div");
      row.className = "qa-row";
      block.appendChild(row);
      grid.appendChild(block);
      return;
    }
    if (!row) {
      row = document.createElement("div");
      row.className = "qa-row";
      grid.appendChild(row);
    }
    row.appendChild(makeActionTile(a, tileI++));
  });
  const qaCount = document.getElementById("qaCount");
  if (qaCount) qaCount.textContent = tileI + " shortcuts";

  function catalogSource() {
    return storeMode === "ai" ? AI_APPS : STORE_APPS;
  }

  function iconForName(name) {
    const all = STORE_APPS.concat(AI_APPS);
    for (let i = 0; i < all.length; i++) {
      if (all[i].name === name && all[i].icon) return all[i].icon;
    }
    return "";
  }

  function makeAppIcon(row) {
    const el = document.createElement("div");
    el.className = "app-ico";
    el.setAttribute("aria-hidden", "true");
    const src = (row && row.icon) || iconForName(row && row.name) || "";
    // data: (legacy / tiny) or file:// from the local icon cache — never https.
    if (src && (src.indexOf("data:image") === 0 || src.indexOf("file://") === 0)) {
      const img = document.createElement("img");
      img.src = src;
      img.alt = "";
      img.loading = "lazy";
      el.appendChild(img);
      return el;
    }
    el.className += " missing";
    return el;
  }

  function uniqueCats(rows) {
    const seen = [];
    rows.forEach(r => { if (r.cat && seen.indexOf(r.cat) < 0) seen.push(r.cat); });
    return seen;
  }

  function onActivate(el, fn) {
    el.addEventListener("click", fn);
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); fn(); }
    });
  }

  function makeChip(text, on, fn) {
    // DIV not <button>: WebKitGTK often paints blank white buttons
    const el = document.createElement("div");
    el.className = "chip" + (on ? " on" : "");
    el.setAttribute("role", "button");
    el.setAttribute("tabindex", "0");
    el.textContent = text;
    onActivate(el, fn);
    return el;
  }

  function renderStoreChips() {
    const chips = document.getElementById("storeChips");
    chips.innerHTML = "";
    chips.appendChild(makeChip("Apps (" + STORE_APPS.length + ")", storeMode === "apps",
      () => { storeMode = "apps"; storeCat = "All"; renderStore(); }));
    chips.appendChild(makeChip("AI tools (" + AI_APPS.length + ")", storeMode === "ai",
      () => { storeMode = "ai"; storeCat = "All"; renderStore(); }));
    const rows = catalogSource();
    ["All"].concat(uniqueCats(rows)).forEach(cat => {
      chips.appendChild(makeChip(cat, cat === storeCat, () => { storeCat = cat; renderStore(); }));
    });
  }

  function renderStore() {
    renderStoreChips();
    const term = (document.getElementById("storeQ").value || "").trim().toLowerCase();
    let rows = catalogSource();
    if (storeCat !== "All") rows = rows.filter(r => r.cat === storeCat);
    if (term) {
      rows = rows.filter(r =>
        r.name.toLowerCase().indexOf(term) >= 0 ||
        (r.desc || "").toLowerCase().indexOf(term) >= 0 ||
        (r.cat || "").toLowerCase().indexOf(term) >= 0
      );
    }
    const box = document.getElementById("storeCards");
    box.innerHTML = "";
    if (!rows.length) {
      box.innerHTML = '<div class="empty">No apps match. Try another search.</div>';
      setStatus("<strong>App Store</strong> — 0 results");
      return;
    }
    rows.forEach(r => {
      const card = document.createElement("div");
      card.className = "card";
      const top = document.createElement("div");
      top.className = "card-top";
      const copy = document.createElement("div");
      copy.className = "card-copy";
      const h = document.createElement("h3");
      h.textContent = r.name;
      const p = document.createElement("p");
      p.textContent = r.desc || "";
      copy.appendChild(h); copy.appendChild(p);
      top.appendChild(makeAppIcon(r));
      top.appendChild(copy);
      const badges = document.createElement("div");
      badges.className = "badges";
      const cat = document.createElement("span");
      cat.className = "badge cat";
      cat.textContent = r.cat;
      badges.appendChild(cat);
      (r.methods || []).slice(0, 2).forEach(m => {
        const b = document.createElement("span");
        b.className = "badge";
        b.textContent = m;
        badges.appendChild(b);
      });
      const actions = document.createElement("div");
      actions.className = "actions";
      const btn = document.createElement("div");
      btn.className = "act install";
      btn.setAttribute("role", "button");
      btn.setAttribute("tabindex", "0");
      btn.textContent = "Install";
      onActivate(btn, () => {
        setStatus("<strong>Install</strong> — " + r.name + " (confirm in terminal →)");
        post({ op: "install", kind: (r.kind || (storeMode === "ai" ? "ai" : "app")), id: r.id, name: r.name });
      });
      actions.appendChild(btn);
      card.appendChild(top);
      card.appendChild(badges);
      card.appendChild(actions);
      box.appendChild(card);
    });
    setStatus("<strong>App Store</strong> — " + rows.length + " " + (storeMode === "ai" ? "AI tools" : "apps"));
  }

  function renderMyApps() {
    const term = (document.getElementById("myQ").value || "").trim().toLowerCase();
    let rows = installed.slice();
    if (term) {
      rows = rows.filter(r =>
        (r.name || "").toLowerCase().indexOf(term) >= 0 ||
        (r.target || "").toLowerCase().indexOf(term) >= 0 ||
        (r.desc || "").toLowerCase().indexOf(term) >= 0
      );
    }
    const box = document.getElementById("myCards");
    box.innerHTML = "";
    if (!rows.length) {
      box.innerHTML = '<div class="empty">No removable apps found (system packages stay hidden).</div>';
      return;
    }
    rows.forEach(r => {
      const card = document.createElement("div");
      card.className = "card";
      const top = document.createElement("div");
      top.className = "card-top";
      const copy = document.createElement("div");
      copy.className = "card-copy";
      const h = document.createElement("h3");
      h.textContent = r.name;
      const p = document.createElement("p");
      p.textContent = r.desc || (r.method + " · " + r.target);
      copy.appendChild(h); copy.appendChild(p);
      top.appendChild(makeAppIcon(r));
      top.appendChild(copy);
      const badges = document.createElement("div");
      badges.className = "badges";
      const m = document.createElement("span");
      m.className = "badge";
      m.textContent = r.method;
      badges.appendChild(m);
      const actions = document.createElement("div");
      actions.className = "actions";
      const btn = document.createElement("div");
      btn.className = "act remove";
      btn.setAttribute("role", "button");
      btn.setAttribute("tabindex", "0");
      btn.textContent = "Remove";
      onActivate(btn, () => {
        const ref = (r.method || "") + ":" + (r.target || "");
        setStatus("<strong>Remove</strong> — " + r.name + " (confirm in terminal →)");
        post({ op: "remove", ref: ref, name: r.name });
      });
      actions.appendChild(btn);
      card.appendChild(top);
      card.appendChild(badges);
      card.appendChild(actions);
      box.appendChild(card);
    });
    setStatus("<strong>My Apps</strong> — " + rows.length + " removable");
  }

  window.__setInstalled = function(rows) {
    installed = Array.isArray(rows) ? rows : [];
    renderMyApps();
  };
  window.__setCatalog = function(store, ai) {
    if (Array.isArray(store)) STORE_APPS = store;
    if (Array.isArray(ai)) AI_APPS = ai;
    if (activeTab === "store") renderStore();
    if (activeTab === "myapps") renderMyApps();
  };

  document.getElementById("tabs").addEventListener("click", (e) => {
    const b = e.target.closest("[data-tab]");
    if (!b) return;
    showTab(b.getAttribute("data-tab"));
  });
  document.getElementById("tabs").addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const b = e.target.closest("[data-tab]");
    if (!b) return;
    e.preventDefault();
    showTab(b.getAttribute("data-tab"));
  });
  onActivate(document.getElementById("askBtn"), () => runText(q.value));
  onActivate(document.getElementById("healthBtn"), () => {
    setStatus("<strong>Starting</strong> — Health scan");
    post({ op: "run", kind: "kw", payload: "health" });
  });
  q.addEventListener("keydown", (e) => { if (e.key === "Enter") runText(q.value); });
  document.getElementById("storeQ").addEventListener("input", renderStore);
  document.getElementById("myQ").addEventListener("input", renderMyApps);
  onActivate(document.getElementById("refreshInstalled"), () => {
    setStatus("<strong>Scanning</strong> — installed apps…");
    post({ op: "list-installed" });
  });
  const storeBlurb = document.getElementById("storeBlurb");
  if (storeBlurb) {
    storeBlurb.textContent = STORE_APPS.length + "+ apps — search, filter, install. Approve steps in the live terminal.";
  }
  try {
    const dpr = window.devicePixelRatio || 1;
    if (dpr >= 1.5) document.documentElement.style.fontSize = (15 + Math.min(dpr, 2)) + "px";
  } catch (e) {}
  const site = document.getElementById("siteLink");
  if (site) {
    site.addEventListener("click", (e) => {
      e.preventDefault();
      post({ op: "open", payload: "https://www.tuxgenie.com" });
    });
  }
  const aspera = document.getElementById("asperaLink");
  if (aspera) {
    aspera.addEventListener("click", (e) => {
      e.preventDefault();
      post({ op: "open", payload: "https://www.tuxgenie.com/aspera-hub.html" });
    });
  }
  post({ op: "system-pulse" });
  setInterval(function() {
    if (activeTab === "home") post({ op: "system-pulse" });
  }, __PULSE_MS__);
  q.focus();
</script>
</body>
</html>
"""
    html = html.replace("__VERSION__", version)
    html = html.replace("__ACTIONS__", json.dumps(compose_home_actions(), ensure_ascii=False))
    html = html.replace("__STORE__", json.dumps(store_apps, ensure_ascii=False))
    html = html.replace("__AI__", json.dumps(ai_apps, ensure_ascii=False))
    html = html.replace("__PULSE_MS__", str(max(3000, int(pulse_ms))))
    return html



class UnifiedShell:
    def __init__(self):
        try:
            Gtk, Gdk, Vte, GLib, Gio, WebKit2 = _load_gi()
        except Exception as e:
            print("tuxgenie-app: GTK/VTE unavailable:", e, file=sys.stderr)
            sys.exit(3)

        self.Gtk = Gtk
        self.Gdk = Gdk
        self.Vte = Vte
        self.GLib = GLib
        self.Gio = Gio
        self.WebKit2 = WebKit2
        self.win = None
        self.term = None
        self.webview = None
        self._pos_set = False
        self._tg = _resolve_tuxgenie()
        self._feed_ready = False
        self._feed_queue = []
        self._store_apps, self._ai_apps = _load_store_catalogs()
        self._left = None
        self._wk_finished = False
        self._deck_fallback_done = False
        self._pulse_widgets = None  # GTK light-deck CPU/mem/disk/PC labels
        self._pulse_actions = {
            "cpu": "health", "mem": "health", "disk": "disk", "pc": "hardware",
        }
        self._light_notebook = None
        self._store_list_box = None
        self._ai_list_box = None
        self._store_search = None
        self._ai_search = None
        self._store_hint = None
        self._store_mode = "browse"  # browse | installed (Apps tab)
        self._store_mode_btns = {}
        self._installed_rows = []
        # Icon prefetch feeds App Store artwork (WebKit + light GTK store).
        self._start_icon_prefetch()

        self.app = Gtk.Application(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.app.connect("activate", self._on_activate)

    def run(self):
        return self.app.run(None)

    def _on_activate(self, app):
        if self.win is not None:
            self.win.present()
            return
        self.win = self.Gtk.ApplicationWindow(application=app, title="TuxGenie")
        self.win.set_default_size(1280, 820)
        for nm in ("tuxgenie", "com.tuxgenie.TuxGenie"):
            try:
                self.win.set_icon_name(nm)
                break
            except Exception:
                pass

        paned = self.Gtk.Paned(orientation=self.Gtk.Orientation.HORIZONTAL)
        paned.set_wide_handle(True)
        self.paned = paned

        left = self._build_left()
        self._left = left
        right = self._build_terminal()
        # GUI stays compact; extra window width goes to the live terminal.
        paned.pack1(left, False, True)
        paned.pack2(right, True, False)
        self.win.add(paned)
        self._apply_light_chrome()
        self.win.connect("size-allocate", self._on_size)
        self.win.show_all()
        self.win.present()
        self._spawn_tuxgenie()
        if self._pulse_widgets is not None:
            self._refresh_pulse_async()
            try:
                self.GLib.timeout_add(_LIGHT_PULSE_MS, self._on_light_pulse_tick)
            except Exception:
                pass

    def _on_light_pulse_tick(self):
        if self._pulse_widgets is None:
            return False
        self._refresh_pulse_async()
        return True

    def _apply_light_chrome(self):
        """Keep GTK chrome light even when the desktop theme is dark."""
        try:
            css = self.Gtk.CssProvider()
            css.load_from_data(
                b"""
                window, headerbar {
                  background-color: #f4f8fb;
                  color: #102028;
                }
                menu, .menu, popover {
                  background-color: #ffffff;
                  color: #102028;
                }
                menuitem, menu menuitem, menuitem label {
                  color: #102028;
                }
                menuitem:hover, menuitem:prelight, menuitem:selected {
                  background-color: #d7eef0;
                  color: #102028;
                }
                button.tg-pulse {
                  background-color: #ffffff;
                  border: 1px solid #d5e3ea;
                  border-radius: 12px;
                  padding: 8px 6px;
                  color: #102028;
                }
                button.tg-pulse:hover {
                  background-color: #e8f6f7;
                  border-color: #0a8a96;
                }
                button.tg-pulse.tg-warn {
                  border-color: #c45c12;
                }
                button.tg-tile {
                  background-color: #ffffff;
                  border: 1px solid #d5e3ea;
                  border-radius: 12px;
                  padding: 6px 8px;
                  color: #102028;
                }
                button.tg-tile:hover {
                  background-color: #e8f6f7;
                  border-color: #0a8a96;
                }
                button.tg-mode-on {
                  background-color: #d7eef0;
                  border-color: #0a8a96;
                  font-weight: bold;
                }
                """
            )
            screen = self.Gdk.Screen.get_default()
            self.Gtk.StyleContext.add_provider_for_screen(
                screen, css, self.Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception:
            pass

    def _start_icon_prefetch(self):
        """Download official catalog icons on first launch, then refresh the store."""
        def work():
            tg = _import_tuxgenie()
            if tg is None or not hasattr(tg, "ensure_catalog_icons"):
                return
            try:
                tg.ensure_catalog_icons()
            except Exception as e:
                print("tuxgenie-app: icon fetch failed:", e, file=sys.stderr)
                return
            apps, ai = _load_store_catalogs()
            self._store_apps, self._ai_apps = apps, ai
            if self.GLib is None:
                return
            self.GLib.idle_add(self._push_catalog, apps, ai)

        threading.Thread(target=work, daemon=True).start()

    def _push_catalog(self, apps, ai):
        """Refresh WebKit and/or light-deck GTK App Store lists after icon fetch."""
        self._store_apps, self._ai_apps = apps, ai
        if self._store_list_box is not None:
            try:
                self._fill_store_list("app")
            except Exception as e:
                print("tuxgenie-app: GTK Apps refresh failed:", e, file=sys.stderr)
        if self._ai_list_box is not None:
            try:
                self._fill_store_list("ai")
            except Exception as e:
                print("tuxgenie-app: GTK AI refresh failed:", e, file=sys.stderr)
        if self.webview is None:
            return False
        payload_store = json.dumps(apps, ensure_ascii=False)
        payload_ai = json.dumps(ai, ensure_ascii=False)
        js = "window.__setCatalog && window.__setCatalog(%s, %s);" % (
            payload_store, payload_ai)
        try:
            self.webview.run_javascript(js, None, None, None)
        except Exception:
            try:
                self.webview.evaluate_javascript(js, -1, None, None, None, None, None)
            except Exception as e:
                print("tuxgenie-app: catalog JS push failed:", e, file=sys.stderr)
        return False

    def _on_size(self, _w, alloc):
        if self._pos_set or alloc.width < 200:
            return
        try:
            self.paned.set_position(int(alloc.width * 0.40))
            self._pos_set = True
        except Exception:
            pass

    def _build_left(self):
        # ≤8 GB PCs: WebKitGTK has been measured at ~3.5 GB RSS alone — skip it.
        if self.WebKit2 is not None and not _prefer_light_deck():
            return self._build_webkit()
        note = None
        if self.WebKit2 is not None and _prefer_light_deck():
            ram = _host_ram_gib()
            # One quiet line — meters/icons are the panel, not the note.
            note = "Light panel · %.0f GB RAM · use the Apps tab to install" % (
                ram or _WEBKIT_MIN_RAM_GIB)
            print(
                "tuxgenie-app: light deck (%.1f GiB RAM). "
                "Set TUXGENIE_FORCE_WEBKIT=1 for the WebKit panel."
                % (ram or 0.0),
                file=sys.stderr,
            )
        return self._build_gtk_fallback(note)

    def _build_webkit(self):
        WebKit2 = self.WebKit2
        view = WebKit2.WebView()
        try:
            settings = view.get_settings()
            settings.set_enable_developer_extras(False)
            settings.set_javascript_can_access_clipboard(False)
            # Keep the UI process lean — page cache + hardware layers are the
            # usual multi-GB RSS culprits on WebKitGTK.
            for name, args in (
                ("set_enable_page_cache", (False,)),
                ("set_enable_dns_prefetching", (False,)),
                ("set_enable_offline_web_application_cache", (False,)),
                ("set_enable_html5_database", (False,)),
                ("set_enable_html5_local_storage", (False,)),
                ("set_enable_smooth_scrolling", (False,)),
                ("set_allow_file_access_from_file_urls", (True,)),
                ("set_allow_universal_access_from_file_urls", (True,)),
            ):
                fn = getattr(settings, name, None)
                if callable(fn):
                    try:
                        fn(*args)
                    except Exception:
                        pass
            try:
                settings.set_cache_model(WebKit2.CacheModel.DOCUMENT_VIEWER)
            except Exception:
                pass
            try:
                # 2 = HardwareAccelerationPolicy.NEVER on WebKit2GTK 4.x
                policy = getattr(WebKit2, "HardwareAccelerationPolicy", None)
                if policy is not None and hasattr(settings, "set_hardware_acceleration_policy"):
                    settings.set_hardware_acceleration_policy(policy.NEVER)
            except Exception:
                pass
        except Exception:
            pass
        try:
            ctx = view.get_context()
            if ctx is not None and hasattr(ctx, "set_cache_model"):
                ctx.set_cache_model(WebKit2.CacheModel.DOCUMENT_VIEWER)
            cm = ctx.get_website_data_manager() if ctx is not None else None
            if cm is not None and hasattr(cm, "set_tls_errors_policy"):
                pass
        except Exception:
            pass
        ucm = view.get_user_content_manager()
        ucm.register_script_message_handler("tuxgenie")
        ucm.connect("script-message-received::tuxgenie", self._on_webkit_msg)
        # Slower pulse on mid-RAM boxes that still use WebKit.
        pulse_ms = 15000 if _host_ram_gib() < 12 else 8000
        html = _shell_html(VERSION, self._store_apps, self._ai_apps, pulse_ms=pulse_ms)
        try:
            view.connect("load-changed", self._on_wk_load)
            view.connect("load-failed", self._on_wk_failed)
        except Exception:
            pass
        # Base URI under /usr/share/tuxgenie so file:// app-icons resolve.
        view.load_html(html, "file:///usr/share/tuxgenie/")
        try:
            self.GLib.timeout_add_seconds(5, self._on_wk_timeout)
        except Exception:
            pass
        frame = self.Gtk.Frame()
        frame.set_shadow_type(self.Gtk.ShadowType.NONE)
        frame.add(view)
        self.webview = view
        return frame

    def _on_wk_load(self, view, event):
        try:
            finished = event == self.WebKit2.LoadEvent.FINISHED
        except Exception:
            finished = False
        if not finished:
            return
        self._wk_finished = True
        try:
            self.GLib.timeout_add(700, self._wk_check_blank, view)
        except Exception:
            pass

    def _on_wk_failed(self, _view, _event, _uri, _err):
        self._swap_deck_to_gtk(
            "The WebKit panel failed to load. Showing the button panel instead. "
            "You can also close this window and run tuxgenie in a terminal.")
        return True

    def _on_wk_timeout(self):
        if self._wk_finished or self._deck_fallback_done:
            return False
        self._swap_deck_to_gtk(
            "The WebKit panel did not finish loading. Showing the button panel instead. "
            "You can also close this window and run tuxgenie in a terminal.")
        return False

    def _wk_check_blank(self, view):
        """A finished load can still paint a blank deck (NVIDIA + X11 / DRI3)."""
        if self._deck_fallback_done or view is None:
            return False
        if self._webkit_surface_blank(view):
            self._swap_deck_to_gtk(
                "The WebKit panel rendered blank. Showing the button panel instead. "
                "You can also close this window and run tuxgenie in a terminal.")
        return False

    def _webkit_surface_blank(self, view) -> bool:
        try:
            region = self.WebKit2.SnapshotRegion.VISIBLE
            opts = self.WebKit2.SnapshotOptions.NONE
        except Exception:
            return False

        holder = {"blank": False, "done": False}

        def _finish(surface):
            try:
                w = surface.get_width()
                h = surface.get_height()
                if w < 20 or h < 20:
                    return
                stride = surface.get_stride()
                buf = surface.get_data()
                pts = (
                    (w // 4, h // 4), (w // 2, h // 2), (3 * w // 4, h // 2),
                    (w // 2, 3 * h // 4), (8, 8),
                )
                samples = []
                for x, y in pts:
                    i = y * stride + x * 4
                    samples.append(bytes(buf[i:i + 3]))
                if len(samples) < 4:
                    return
                base = samples[0]
                uniform = all(
                    max(abs(a - b) for a, b in zip(base, s)) < 18 for s in samples)
                holder["blank"] = bool(uniform)
            except Exception:
                holder["blank"] = False
            holder["done"] = True

        try:
            def _cb(webview, result, _data):
                try:
                    surface = webview.get_snapshot_finish(result)
                except Exception:
                    return
                _finish(surface)
                if holder["blank"]:
                    self._swap_deck_to_gtk(
                        "The WebKit panel rendered blank. Showing the button panel instead. "
                        "You can also close this window and run tuxgenie in a terminal.")

            view.get_snapshot(region, opts, None, _cb, None)
        except Exception:
            return False
        return False

    def _swap_deck_to_gtk(self, reason: str) -> None:
        if self._deck_fallback_done:
            return
        self._deck_fallback_done = True
        print("tuxgenie-app: " + reason, file=sys.stderr)
        try:
            new = self._build_gtk_fallback(reason)
            old = self._left
            if old is not None:
                self.paned.remove(old)
            self._left = new
            self.paned.pack1(new, False, True)
            self.webview = None
            new.show_all()
        except Exception as e:
            print("tuxgenie-app: could not show a control panel (%s)." % e, file=sys.stderr)
            print("tuxgenie-app: Use the terminal on the right, or run `tuxgenie` in a terminal.",
                  file=sys.stderr)

    def _on_webkit_msg(self, _manager, message):
        raw = ""
        try:
            js = message.get_js_value()
            if js is not None:
                try:
                    raw = js.to_json(0)
                except Exception:
                    raw = js.to_string() if hasattr(js, "to_string") else str(js)
        except Exception:
            raw = ""
        if not raw:
            try:
                val = message.get_value() if hasattr(message, "get_value") else None
                if val is not None:
                    raw = str(val)
            except Exception:
                return
        self._handle_payload(raw)

    def _handle_payload(self, raw):
        try:
            msg = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return
        if isinstance(msg, str):
            try:
                msg = json.loads(msg)
            except Exception:
                return
        if not isinstance(msg, dict):
            return
        op = msg.get("op") or "run"
        if op == "open":
            self._open_url((msg.get("payload") or "").strip())
            return
        if op == "list-installed":
            self._refresh_installed_async()
            return
        if op == "system-pulse":
            self._refresh_pulse_async()
            return
        if op == "install":
            kind = (msg.get("kind") or "app").strip().lower()
            eid = msg.get("id")
            if eid is None:
                return
            cmd = "install-ai %s" % eid if kind == "ai" else "install-app %s" % eid
            self.feed_line(cmd)
            return
        if op == "remove":
            ref = (msg.get("ref") or "").strip()
            if ref:
                self.feed_line("remove-app %s" % ref)
            return
        if op != "run":
            return
        kind = msg.get("kind") or "text"
        payload = (msg.get("payload") or "").strip()
        if kind == "tab":
            # Should be handled in JS; ignore if it leaks through
            return
        if kind in ("kw", "text") and payload:
            self.feed_line(payload)

    def _refresh_installed_async(self):
        def work():
            rows = []
            try:
                tg = _import_tuxgenie()
                if tg is not None:
                    apps = tg._installed_user_apps()
                    for a in apps:
                        name = a.get("name") or ""
                        method = a.get("method") or ""
                        target = a.get("target") or ""
                        icon = ""
                        themes = []
                        try:
                            if hasattr(tg, "installed_app_icon_ref"):
                                icon = tg.installed_app_icon_ref(
                                    name, method, target) or ""
                            if hasattr(tg, "installed_app_theme_icons"):
                                themes = list(
                                    tg.installed_app_theme_icons(
                                        name, method, target) or [])
                        except Exception:
                            icon, themes = "", []
                        rows.append({
                            "id": a.get("id"),
                            "name": name,
                            "cat": a.get("cat"),
                            "desc": a.get("desc"),
                            "method": method,
                            "target": target,
                            "root": bool(a.get("root")),
                            "icon": icon,
                            "theme_icons": themes,
                        })
            except Exception as e:
                print("tuxgenie-app: installed scan failed:", e, file=sys.stderr)
            self.GLib.idle_add(self._push_installed, rows)

        threading.Thread(target=work, daemon=True).start()

    def _push_installed(self, rows):
        """Refresh WebKit My Apps and/or light-deck Installed list."""
        self._installed_rows = list(rows or [])
        if self._store_list_box is not None and self._store_mode == "installed":
            try:
                self._fill_store_list("app")
            except Exception as e:
                print("tuxgenie-app: GTK installed refresh failed:", e, file=sys.stderr)
        if self.webview is None:
            return False
        payload = json.dumps(rows, ensure_ascii=False)
        js = "window.__setInstalled && window.__setInstalled(%s);" % payload
        try:
            self.webview.run_javascript(js, None, None, None)
        except Exception:
            try:
                self.webview.evaluate_javascript(js, -1, None, None, None, None, None)
            except Exception as e:
                print("tuxgenie-app: JS push failed:", e, file=sys.stderr)
        return False

    def _refresh_pulse_async(self):
        def work():
            data = {}
            try:
                tg = _import_tuxgenie()
                if tg is not None and hasattr(tg, "gui_system_pulse"):
                    data = tg.gui_system_pulse() or {}
            except Exception as e:
                print("tuxgenie-app: system pulse failed:", e, file=sys.stderr)
            self.GLib.idle_add(self._push_pulse, data)

        threading.Thread(target=work, daemon=True).start()

    def _push_pulse(self, data):
        """Update WebKit and/or GTK light-deck pulse widgets."""
        self._push_pulse_gtk(data)
        if self.webview is None:
            return False
        payload = json.dumps(data or {}, ensure_ascii=False)
        js = "window.__setPulse && window.__setPulse(%s);" % payload
        try:
            self.webview.run_javascript(js, None, None, None)
        except Exception:
            try:
                self.webview.evaluate_javascript(js, -1, None, None, None, None, None)
            except Exception as e:
                print("tuxgenie-app: pulse JS push failed:", e, file=sys.stderr)
        return False

    def _push_pulse_gtk(self, data):
        w = self._pulse_widgets
        if not w or not isinstance(data, dict):
            return False
        if data.get("actions"):
            self._pulse_actions.update(data["actions"])

        def _pct(key):
            try:
                return int(round(float(data.get(key) or 0)))
            except Exception:
                return 0

        cpu_pct, mem_pct, disk_pct = _pct("cpu_pct"), _pct("mem_pct"), _pct("disk_pct")
        try:
            w["cpu_val"].set_markup(
                '<span size="large" weight="bold">%d%%</span>' % cpu_pct)
            w["mem_val"].set_markup(
                '<span size="large" weight="bold">%d%%</span>' % mem_pct)
            w["disk_val"].set_markup(
                '<span size="large" weight="bold">%d%%</span>' % disk_pct)
            w["cpu_sub"].set_text(data.get("cpu_label") or "")
            w["mem_sub"].set_text(data.get("mem_label") or "used / total")
            w["disk_sub"].set_text(data.get("disk_label") or "used / total")
            w["pc_val"].set_markup(
                '<span weight="bold">%s</span>'
                % (data.get("pc_title") or "This PC").replace("&", "&amp;"))
            w["pc_sub"].set_text(data.get("pc_label") or "")
            for key, warn_key, btn_key in (
                ("cpu", "cpu_warn", "cpu_btn"),
                ("mem", "mem_warn", "mem_btn"),
                ("disk", "disk_warn", "disk_btn"),
            ):
                btn = w.get(btn_key)
                if btn is None:
                    continue
                ctx = btn.get_style_context()
                if data.get(warn_key):
                    ctx.add_class("tg-warn")
                else:
                    ctx.remove_class("tg-warn")
        except Exception as e:
            print("tuxgenie-app: pulse GTK update failed:", e, file=sys.stderr)
        return False

    def _open_url(self, url: str):
        if not url.startswith(("https://", "http://")):
            return
        try:
            import subprocess
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as e:
            print("tuxgenie-app: open url failed:", e, file=sys.stderr)

    def _tile_icon_widget(self, action_id: str):
        """Icon (or glyph fallback) for a light-deck tile — always returns a widget."""
        Gtk = self.Gtk
        names = _TILE_ICON_NAMES.get(action_id) or ("applications-system",)
        if isinstance(names, str):
            names = (names,)
        theme = None
        try:
            theme = Gtk.IconTheme.get_default()
        except Exception:
            theme = None
        size = Gtk.IconSize.LARGE_TOOLBAR
        for name in list(names) + ["applications-system", "gtk-missing-image"]:
            try:
                if theme is not None and hasattr(theme, "has_icon"):
                    if not theme.has_icon(name):
                        continue
                img = Gtk.Image.new_from_icon_name(name, size)
                return img
            except Exception:
                continue
        # Glyph fallback — visible even when the XFCE theme is sparse.
        lab = Gtk.Label()
        glyph = _TILE_ICON_GLYPH.get(action_id) or "•"
        try:
            lab.set_markup('<span size="x-large">%s</span>' % glyph)
        except Exception:
            lab.set_text(glyph)
        return lab

    def _build_pulse_strip(self):
        """CPU / RAM / Disk / PC cards for the light GTK deck."""
        Gtk = self.Gtk
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        wrap.set_margin_start(12)
        wrap.set_margin_end(12)
        wrap.set_margin_bottom(8)
        sec = Gtk.Label()
        sec.set_xalign(0)
        sec.set_markup(
            "<span size='small' foreground='#5c7380'><b>This PC</b></span>"
        )
        wrap.pack_start(sec, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        widgets = {}

        def _card(key, title, tip):
            btn = Gtk.Button()
            try:
                btn.get_style_context().add_class("tg-pulse")
            except Exception:
                pass
            btn.set_tooltip_text(tip)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            k = Gtk.Label()
            k.set_markup(
                "<span size='small' foreground='#5c7380'>%s</span>" % title)
            k.set_xalign(0)
            val = Gtk.Label()
            val.set_xalign(0)
            val.set_markup('<span size="large" weight="bold">—</span>')
            sub = Gtk.Label(label="")
            sub.set_xalign(0)
            sub.set_line_wrap(True)
            try:
                sub.set_max_width_chars(14)
            except Exception:
                pass
            box.pack_start(k, False, False, 0)
            box.pack_start(val, False, False, 0)
            box.pack_start(sub, False, False, 0)
            btn.add(box)
            btn.connect("clicked", self._on_pulse_btn, key)
            row.pack_start(btn, True, True, 0)
            widgets["%s_btn" % key] = btn
            widgets["%s_val" % key] = val
            widgets["%s_sub" % key] = sub

        _card("cpu", "CPU", "Open health check")
        _card("mem", "Memory", "Open health check")
        _card("disk", "Disk", "Open disk tools")
        _card("pc", "PC", "PC configuration")
        wrap.pack_start(row, False, False, 0)
        self._pulse_widgets = widgets
        return wrap

    def _on_pulse_btn(self, _btn, key):
        kw = (self._pulse_actions or {}).get(key) or key
        if kw:
            self.feed_line(kw)

    def _build_home_page(self):
        """Ask bar + quick-action tiles for the light Home tab."""
        Gtk = self.Gtk
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        ask_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ask_row.set_margin_start(12)
        ask_row.set_margin_end(12)
        ask_row.set_margin_top(8)
        ask_row.set_margin_bottom(8)
        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("my wifi is not working")
        self._entry.connect("activate", self._on_ask)
        btn = Gtk.Button(label="Ask →")
        btn.connect("clicked", self._on_ask)
        ask_row.pack_start(self._entry, True, True, 0)
        ask_row.pack_start(btn, False, False, 0)
        page.pack_start(ask_row, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        grid = Gtk.FlowBox()
        grid.set_valign(Gtk.Align.START)
        grid.set_max_children_per_line(2)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_homogeneous(True)
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        grid.set_margin_bottom(12)
        for a in compose_home_actions():
            if a.get("kind") == "sec":
                lab = Gtk.Label()
                lab.set_xalign(0)
                lab.set_markup(
                    "<span size='small' foreground='#5c7380'><b>%s</b></span>"
                    % (a.get("label") or "").replace("&", "&amp;")
                )
                lab.set_margin_top(8)
                lab.set_margin_bottom(2)
                grid.add(lab)
                continue
            b = Gtk.Button()
            try:
                b.get_style_context().add_class("tg-tile")
            except Exception:
                pass
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.set_margin_top(6)
            row.set_margin_bottom(6)
            row.set_margin_start(6)
            row.set_margin_end(6)
            ico = self._tile_icon_widget(a.get("id") or "")
            if ico is not None:
                row.pack_start(ico, False, False, 0)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            l1 = Gtk.Label()
            l1.set_xalign(0)
            l1.set_markup("<b>%s</b>" % a["label"].replace("&", "&amp;"))
            l2 = Gtk.Label(label=a.get("tip") or "")
            l2.set_xalign(0)
            l2.set_line_wrap(True)
            box.pack_start(l1, False, False, 0)
            box.pack_start(l2, False, False, 0)
            row.pack_start(box, True, True, 0)
            b.add(row)
            b.connect("clicked", self._on_action_btn, a)
            grid.add(b)
        scroll.add(grid)
        page.pack_start(scroll, True, True, 0)
        return page

    def _catalog_icon_image(self, row: dict):
        """Load catalog / theme / desktop icon — same look for Browse and Installed."""
        Gtk = self.Gtk
        row = row or {}
        ref = row.get("icon") or ""
        path = ""
        if ref.startswith("file://"):
            from urllib.parse import unquote
            path = unquote(ref[7:])
        if path and os.path.isfile(path):
            pixbuf = getattr(self, "GdkPixbuf", None)
            if pixbuf is not None:
                try:
                    pix = pixbuf.Pixbuf.new_from_file_at_scale(
                        path, 32, 32, True)
                    return Gtk.Image.new_from_pixbuf(pix)
                except Exception:
                    pass
            try:
                return Gtk.Image.new_from_file(path)
            except Exception:
                pass

        # Theme / .desktop icons (Installed apps that are not in the catalog cache).
        names = list(row.get("theme_icons") or [])
        target = (row.get("target") or "").strip()
        name = (row.get("name") or "").strip()
        for extra in (target, name.lower().replace(" ", "-"), name.lower()):
            if extra and extra not in names:
                names.append(extra)
        theme = None
        try:
            theme = Gtk.IconTheme.get_default()
        except Exception:
            theme = None
        size = Gtk.IconSize.DND
        for iname in names:
            try:
                if theme is not None and hasattr(theme, "has_icon"):
                    if not theme.has_icon(iname):
                        continue
                return Gtk.Image.new_from_icon_name(iname, size)
            except Exception:
                continue

        # DesktopAppInfo — O(1) lookup matching Mint menu icons for apt/flatpak.
        try:
            Gio = self.Gio
            if Gio is not None:
                desk_ids = []
                if target:
                    desk_ids.append(target + ".desktop")
                    if "." in target:  # flatpak application id
                        desk_ids.append(target.split(".")[-1] + ".desktop")
                if name:
                    desk_ids.append(name.lower().replace(" ", "-") + ".desktop")
                for did in desk_ids:
                    try:
                        info = Gio.DesktopAppInfo.new(did)
                    except Exception:
                        info = None
                    if info is None:
                        continue
                    try:
                        gicon = info.get_icon()
                        if gicon is None:
                            continue
                        return Gtk.Image.new_from_gicon(gicon, size)
                    except Exception:
                        continue
        except Exception:
            pass

        try:
            return Gtk.Image.new_from_icon_name("package-x-generic", size)
        except Exception:
            return Gtk.Label(label="•")

    def _set_store_mode(self, mode: str):
        """Browse catalog or show installed apps (Apps tab only)."""
        mode = "installed" if mode == "installed" else "browse"
        self._store_mode = mode
        for key, btn in (self._store_mode_btns or {}).items():
            try:
                ctx = btn.get_style_context()
                if key == mode:
                    ctx.add_class("tg-mode-on")
                else:
                    ctx.remove_class("tg-mode-on")
            except Exception:
                pass
        if mode == "installed":
            self._refresh_installed_async()
        self._fill_store_list("app")

    def _on_store_mode_btn(self, _btn, mode):
        self._set_store_mode(mode)

    def _update_store_hint(self, kind: str = "app"):
        hint = self._store_hint if kind == "app" else None
        if hint is None and kind != "app":
            return
        if kind == "ai":
            return
        if self._store_mode == "installed":
            n = len(self._installed_rows or [])
            text = (
                "Installed · %d apps — Remove asks for yes/no in the live terminal."
                % n
            )
        else:
            n = len(self._store_apps or [])
            text = (
                "Browse %d items — Install asks for yes/no in the live terminal."
                % n
            )
        try:
            self._store_hint.set_markup(
                "<span size='small' foreground='#5c7380'>%s</span>" % text
            )
        except Exception:
            pass

    def _build_store_page(self, kind: str = "app"):
        """Browsable install list — plus Installed/Remove on the Apps tab."""
        Gtk = self.Gtk
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_margin_top(8)
        page.set_margin_start(10)
        page.set_margin_end(10)
        page.set_margin_bottom(8)

        hint = Gtk.Label()
        hint.set_xalign(0)
        hint.set_line_wrap(True)
        page.pack_start(hint, False, False, 0)

        if kind == "app":
            self._store_hint = hint
            mode_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            self._store_mode_btns = {}
            for mode, label in (("browse", "Browse"), ("installed", "Installed")):
                b = Gtk.Button(label=label)
                try:
                    b.get_style_context().add_class("tg-tile")
                except Exception:
                    pass
                b.connect("clicked", self._on_store_mode_btn, mode)
                mode_row.pack_start(b, False, False, 0)
                self._store_mode_btns[mode] = b
            refresh = Gtk.Button(label="Refresh")
            try:
                refresh.get_style_context().add_class("tg-tile")
            except Exception:
                pass
            refresh.set_tooltip_text("Rescan installed apps")
            refresh.connect(
                "clicked",
                lambda *_: self._refresh_installed_async()
                if self._store_mode == "installed"
                else self._fill_store_list("app"),
            )
            mode_row.pack_end(refresh, False, False, 0)
            page.pack_start(mode_row, False, False, 0)
            self._update_store_hint("app")
            # Highlight Browse by default
            try:
                self._store_mode_btns["browse"].get_style_context().add_class("tg-mode-on")
            except Exception:
                pass
        else:
            n = len(self._ai_apps or [])
            hint.set_markup(
                "<span size='small' foreground='#5c7380'>"
                "Browse %d AI tools — Install asks for yes/no in the live terminal."
                "</span>" % n
            )

        search = Gtk.Entry()
        search.set_placeholder_text(
            "Search apps…" if kind == "app" else "Search AI tools…")
        page.pack_start(search, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        try:
            scroll.set_min_content_height(220)
        except Exception:
            pass
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        try:
            listbox.set_header_func(lambda *_a: None)
        except Exception:
            pass
        scroll.add(listbox)
        page.pack_start(scroll, True, True, 0)

        if kind == "app":
            self._store_list_box = listbox
            self._store_search = search
        else:
            self._ai_list_box = listbox
            self._ai_search = search

        def _on_search(*_a):
            self._fill_store_list(kind)

        search.connect("changed", _on_search)
        self._fill_store_list(kind)
        return page

    def _fill_store_list(self, kind: str = "app"):
        Gtk = self.Gtk
        listbox = self._store_list_box if kind == "app" else self._ai_list_box
        search = self._store_search if kind == "app" else self._ai_search
        installed_mode = kind == "app" and self._store_mode == "installed"
        if installed_mode:
            rows = list(self._installed_rows or [])
        else:
            rows = list(self._store_apps if kind == "app" else self._ai_apps)
        if listbox is None:
            return
        if kind == "app":
            self._update_store_hint("app")
        q = ""
        try:
            q = (search.get_text() if search is not None else "") or ""
        except Exception:
            q = ""
        q = q.strip().lower()
        for child in list(listbox.get_children()):
            listbox.remove(child)

        shown = 0
        for row in rows:
            name = (row.get("name") or "")
            cat = (row.get("cat") or "")
            desc = (row.get("desc") or "")
            method = (row.get("method") or "")
            target = (row.get("target") or "")
            blob = (" ".join([name, cat, desc, method, target])).lower()
            if q and q not in blob:
                continue
            shown += 1
            if shown > 400:
                break
            item = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            box.set_margin_start(6)
            box.set_margin_end(6)
            box.pack_start(self._catalog_icon_image(row), False, False, 0)
            meta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            title = Gtk.Label()
            title.set_xalign(0)
            title.set_markup("<b>%s</b>" % name.replace("&", "&amp;"))
            sub = Gtk.Label()
            sub.set_xalign(0)
            sub.set_line_wrap(True)
            if installed_mode:
                tip = "%s:%s" % (method, target) if method and target else (desc or cat)
            else:
                tip = desc or cat
            if tip:
                sub.set_markup(
                    "<span size='small' foreground='#5c7380'>%s</span>"
                    % tip.replace("&", "&amp;")
                )
            meta.pack_start(title, False, False, 0)
            meta.pack_start(sub, False, False, 0)
            box.pack_start(meta, True, True, 0)
            if installed_mode:
                action = Gtk.Button(label="Remove")
                try:
                    action.get_style_context().add_class("tg-tile")
                except Exception:
                    pass
                ref = "%s:%s" % (method, target) if method and target else ""
                action.set_sensitive(bool(ref))
                action.connect("clicked", self._on_store_remove, ref)
            else:
                action = Gtk.Button(label="Install")
                try:
                    action.get_style_context().add_class("tg-tile")
                except Exception:
                    pass
                action.connect(
                    "clicked", self._on_store_install, kind, row.get("id"))
            box.pack_end(action, False, False, 0)
            item.add(box)
            listbox.add(item)
        if shown == 0:
            empty = Gtk.ListBoxRow()
            if installed_mode:
                msg = (
                    "No installed apps found yet — click Refresh, "
                    "or install something from Browse."
                    if not q
                    else "No installed matches — try another search."
                )
            else:
                msg = "No matches — try another search."
            lab = Gtk.Label(label=msg)
            lab.set_margin_top(12)
            lab.set_margin_bottom(12)
            lab.set_line_wrap(True)
            empty.add(lab)
            listbox.add(empty)
        listbox.show_all()

    def _on_store_install(self, _btn, kind, eid):
        if eid is None:
            return
        cmd = "install-ai %s" % eid if kind == "ai" else "install-app %s" % eid
        self.feed_line(cmd)

    def _on_store_remove(self, _btn, ref):
        ref = (ref or "").strip()
        if not ref:
            return
        self.feed_line("remove-app %s" % ref)

    def _show_light_tab(self, payload: str):
        """Switch light-deck notebook to Apps / AI / Home."""
        nb = self._light_notebook
        if nb is None:
            return False
        page = {"store": 1, "store-ai": 2, "home": 0, "myapps": 1}.get(payload)
        if page is None:
            return False
        try:
            nb.set_current_page(page)
            if payload == "myapps":
                self._set_store_mode("installed")
            elif payload == "store":
                # Keep current mode, but refresh installed cache in background.
                self._refresh_installed_async()
            return True
        except Exception:
            return False

    def _on_light_notebook_switch(self, _nb, _page, page_num):
        # Apps tab (1): rescan installed so Remove stays current.
        if page_num == 1:
            self._refresh_installed_async()
        return False

    def _build_gtk_fallback(self, note=None):
        """Light control deck: pulse + Home/Apps/AI tabs (no WebKit)."""
        Gtk = self.Gtk
        # GdkPixbuf for catalog icons in the Apps list
        try:
            from gi.repository import GdkPixbuf
            self.GdkPixbuf = GdkPixbuf
        except Exception:
            self.GdkPixbuf = None

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hero.set_margin_top(14)
        hero.set_margin_bottom(4)
        hero.set_margin_start(16)
        hero.set_margin_end(16)
        title = Gtk.Label(label="TuxGenie")
        title.set_xalign(0)
        try:
            title.set_markup(
                '<span size="xx-large" weight="bold" foreground="#063642">TuxGenie</span>'
            )
        except Exception:
            pass
        hero.pack_start(title, False, False, 0)
        if note:
            sub = Gtk.Label(label=note)
            sub.set_xalign(0)
            try:
                sub.set_markup(
                    '<span size="small" foreground="#5c7380">%s</span>'
                    % note.replace("&", "&amp;")
                )
            except Exception:
                pass
            hero.pack_start(sub, False, False, 0)
        outer.pack_start(hero, False, False, 0)
        outer.pack_start(self._build_pulse_strip(), False, False, 0)

        nb = Gtk.Notebook()
        try:
            nb.set_tab_pos(Gtk.PositionType.TOP)
        except Exception:
            pass
        nb.append_page(self._build_home_page(), Gtk.Label(label="Home"))
        nb.append_page(self._build_store_page("app"), Gtk.Label(label="Apps"))
        nb.append_page(self._build_store_page("ai"), Gtk.Label(label="AI tools"))
        try:
            nb.connect("switch-page", self._on_light_notebook_switch)
        except Exception:
            pass
        self._light_notebook = nb
        outer.pack_start(nb, True, True, 0)
        # Warm the installed-apps cache so Installed is ready when opened.
        self._refresh_installed_async()
        return outer

    def _on_ask(self, *_args):
        text = (self._entry.get_text() or "").strip()
        if text:
            self.feed_line(text)
            self._entry.set_text("")

    def _on_action_btn(self, _btn, action):
        kind = action.get("kind")
        if kind == "sec":
            return
        payload = (action.get("payload") or "").strip()
        if kind == "tab":
            # Prefer the in-panel Apps/AI tabs; fall back to terminal keywords.
            if self._show_light_tab(payload):
                return
            kw = _TAB_FALLBACK_KW.get(payload, "")
            if kw:
                self.feed_line(kw)
            return
        if kind == "text" and not payload:
            if hasattr(self, "_entry"):
                self._entry.grab_focus()
            return
        if payload:
            self.feed_line(payload)

    def _build_terminal(self):
        Vte = self.Vte
        Gtk = self.Gtk
        Gdk = self.Gdk
        self.term = Vte.Terminal()
        try:
            # Cap scrollback — unlimited (-1) grows without bound on long sessions.
            self.term.set_scrollback_lines(_VTE_SCROLLBACK_LINES)
            self.term.set_mouse_autohide(True)
            self.term.set_scroll_on_keystroke(True)
            self.term.set_scroll_on_output(False)
        except Exception:
            pass
        # The 60% pane is narrower than a full terminal. A 10pt mono font
        # keeps the compact menu from wrapping mid-token ("[8" / "] Webcam").
        try:
            from gi.repository import Pango
            self.term.set_font(Pango.FontDescription.from_string("Ubuntu Mono 10"))
        except Exception:
            try:
                from gi.repository import Pango
                self.term.set_font(Pango.FontDescription.from_string("Monospace 10"))
            except Exception:
                pass
        try:
            rgba = Gdk.RGBA()
            rgba.parse("#0b1520")
            self.term.set_color_background(rgba)
            rgba_fg = Gdk.RGBA()
            rgba_fg.parse("#e8f1f4")
            self.term.set_color_foreground(rgba_fg)
        except Exception:
            pass
        self.term.connect("child-exited", self._on_child_exited)
        self.term.connect("key-press-event", self._on_term_key)
        self.term.connect("button-press-event", self._on_term_button)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        header = Gtk.Label(label="  Live terminal — TuxGenie session")
        header.set_xalign(0)
        try:
            header.set_markup(
                '  <span foreground="#0a6e7a" size="small">'
                "<b>Live terminal</b> — y/n here · "
                "select text then Ctrl+C / Ctrl+Shift+C to copy · "
                "Ctrl+V / Ctrl+Shift+V or right-click to paste</span>"
            )
        except Exception:
            pass
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        try:
            hdr_box.override_background_color(
                Gtk.StateFlags.NORMAL, Gdk.RGBA(0.95, 0.97, 0.98, 1)
            )
        except Exception:
            pass
        hdr_box.pack_start(header, True, True, 0)
        box.pack_start(hdr_box, False, False, 0)

        term_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        term_row.pack_start(self.term, True, True, 0)
        try:
            sb = Gtk.Scrollbar(
                orientation=Gtk.Orientation.VERTICAL,
                adjustment=self.term.get_vadjustment(),
            )
            term_row.pack_start(sb, False, False, 0)
        except Exception:
            pass
        box.pack_start(term_row, True, True, 0)
        return box

    def _spawn_tuxgenie(self):
        run = "%s; echo; read -rp 'Press Enter to close...' _" % self._tg
        try:
            self.term.spawn_async(
                self.Vte.PtyFlags.DEFAULT,
                os.path.expanduser("~"),
                ["/bin/bash", "-lc", run],
                None,
                self.GLib.SpawnFlags.DEFAULT,
                None,
                None,
                -1,
                None,
                self._on_spawned,
            )
        except Exception as e:
            print("tuxgenie-app: spawn failed:", e, file=sys.stderr)
            os._exit(3)

    def _on_spawned(self, *args):
        err = next((a for a in args if isinstance(a, self.GLib.Error)), None)
        if err is not None:
            print("tuxgenie-app: could not start tuxgenie:", err.message, file=sys.stderr)
            os._exit(3)
        self.GLib.timeout_add(400, self._focus_term)
        self.GLib.timeout_add(1600, self._mark_feed_ready)

    def _focus_term(self):
        try:
            self.term.grab_focus()
        except Exception:
            pass
        return False

    def _mark_feed_ready(self):
        self._feed_ready = True
        pending = list(self._feed_queue)
        self._feed_queue.clear()
        for line in pending:
            self._feed_now(line)
        return False

    def feed_line(self, text: str):
        if not text or self.term is None:
            return
        line = text.rstrip("\n")
        if not self._feed_ready:
            self._feed_queue.append(line)
            return
        self._feed_now(line)

    def _feed_now(self, text: str):
        data = (text.rstrip("\n") + "\n").encode("utf-8", "replace")
        try:
            self.term.feed_child_binary(data)
        except Exception:
            try:
                self.term.feed_child(data)
            except TypeError:
                try:
                    self.term.feed_child(data.decode("utf-8"), len(data))
                except Exception:
                    try:
                        self.term.feed_child(data, len(data))
                    except Exception as e:
                        print("tuxgenie-app: feed failed:", e, file=sys.stderr)
                        return
        self._focus_term()

    def _copy(self):
        try:
            self.term.copy_clipboard_format(self.Vte.Format.TEXT)
        except Exception:
            try:
                self.term.copy_clipboard()
            except Exception:
                pass

    def _has_selection(self) -> bool:
        try:
            return bool(self.term.get_has_selection())
        except Exception:
            try:
                return bool(self.term.get_selection_bound() is not None)
            except Exception:
                return False

    def _on_term_key(self, _term, event):
        ctrl = bool(event.state & self.Gdk.ModifierType.CONTROL_MASK)
        shift = bool(event.state & self.Gdk.ModifierType.SHIFT_MASK)
        name = (self.Gdk.keyval_name(event.keyval) or "").lower()
        # Copy: Ctrl+Shift+C always. Plain Ctrl+C copies when text is
        # selected (beginner expectation) and only sends SIGINT otherwise.
        if ctrl and name == "c":
            if shift or self._has_selection():
                self._copy()
                return True
            return False
        # Paste: Ctrl+Shift+V and plain Ctrl+V (API-key paste must work).
        if ctrl and name in ("v", "insert"):
            try:
                self.term.paste_clipboard()
            except Exception:
                pass
            return True
        if shift and name == "insert":
            try:
                self.term.paste_clipboard()
            except Exception:
                pass
            return True
        return False

    def _on_term_button(self, _term, event):
        if event.button == 2:
            try:
                self.term.paste_primary()
            except Exception:
                pass
            return True
        if event.button == 3:
            menu = self.Gtk.Menu()

            def _item(label, cb):
                mi = self.Gtk.MenuItem(label=label)
                mi.connect("activate", lambda *_: cb())
                menu.append(mi)

            _item("Copy", self._copy)
            _item("Paste", lambda: self.term.paste_clipboard())
            _item("Select All", lambda: self.term.select_all())
            menu.show_all()
            try:
                menu.popup_at_pointer(event)
            except Exception:
                menu.popup(None, None, None, None, event.button, event.time)
            return True
        return False

    def _on_child_exited(self, *_args):
        if self.app is not None:
            self.app.quit()


def main():
    return UnifiedShell().run()


if __name__ == "__main__":
    sys.exit(main() or 0)
