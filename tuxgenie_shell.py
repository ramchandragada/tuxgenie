#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TuxGenie Unified Shell — flagship desktop app.

  ~30% modern control deck (WebKitGTK)  |  ~70% live VTE terminal

Tabs: Home (ask + quick actions) · App Store · My Apps.
Install/Remove clicks feed the live TuxGenie session on the right
(install-app / remove-app). Terminal core is unchanged.
Exit code 3 = GTK/VTE unavailable (launcher falls back further).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading

APP_ID = "com.tuxgenie.TuxGenie"
VERSION = "7.1.0"

# Home quick actions — curated Wave A (not the full terminal menu).
# kind=sec = section header; tab = Store pane; kw = feed live CLI keyword.
ACTIONS = [
    {"kind": "sec", "label": "Start here"},
    {"id": "fix", "label": "Fix a problem", "tip": "Describe what's wrong in plain English",
     "kind": "kw", "payload": "fix", "accent": "#0d8a9a"},
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
    {"id": "apps", "label": "App Store", "tip": "Browse & install 220+ apps",
     "kind": "tab", "payload": "store", "accent": "#d4620f"},
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


def _resolve_tuxgenie() -> str:
    which = shutil.which("tuxgenie")
    if which:
        return which
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(here, "tuxgenie.py")
    if os.path.isfile(cand):
        return "%s %s" % (sys.executable, cand)
    lib = "/usr/lib/tuxgenie/tuxgenie.py"
    if os.path.isfile(lib):
        return "%s %s" % (sys.executable, lib)
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


def _shell_html(version: str, store_apps: list, ai_apps: list) -> str:
    """Flagship control deck — brand-first, luminous teal, intentional motion.
    Self-contained: no CDN, no remote fonts, no third-party assets."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>TuxGenie</title>
<style>
  :root {
    --ink: #07131a;
    --ink2: #1a2c36;
    --muted: #5c7380;
    --fog: #eef5f7;
    --paper: #f7fbfc;
    --panel: rgba(255,255,255,.82);
    --ember: #e85d04;
    --ember2: #ff8a2a;
    --tide0: #032830;
    --tide1: #065a66;
    --tide2: #0a8a96;
    --tide3: #1ec8d4;
    --line: rgba(7,45,56,.10);
    --danger: #b23a22;
    --shadow: 0 24px 60px rgba(3,40,48,.14);
    --ease: cubic-bezier(.22,.9,.24,1);
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; height: 100%;
    font-family: "Ubuntu", "Cantarell", "Noto Sans", "Source Sans 3", "DejaVu Sans", sans-serif;
    color: var(--ink);
    background: var(--fog);
    overflow: hidden;
  }
  .app {
    display: flex; flex-direction: column; height: 100%; min-height: 0;
    position: relative;
    background:
      radial-gradient(900px 420px at 0% 0%, #1ec8d433, transparent 55%),
      radial-gradient(700px 380px at 100% 8%, #ff8a2a22, transparent 50%),
      linear-gradient(168deg, #f4fafb 0%, #e7f0f3 48%, #dce8ec 100%);
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
  .logo {
    font-size: clamp(2rem, 4.2vw, 2.7rem);
    font-weight: 800; letter-spacing: -.04em; line-height: .95;
    margin: 0;
    background: linear-gradient(115deg, var(--tide0) 10%, var(--tide2) 55%, var(--tide1) 100%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
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
  .nav button {
    appearance: none; border: 0; background: transparent; cursor: pointer;
    font: inherit; font-weight: 700; font-size: .86rem; color: var(--muted);
    padding: 10px 14px 12px; position: relative;
    transition: color .2s;
  }
  .nav button::after {
    content: ""; position: absolute; left: 14px; right: 14px; bottom: -1px; height: 3px;
    border-radius: 3px 3px 0 0;
    background: linear-gradient(90deg, var(--ember), var(--ember2));
    transform: scaleX(0); transform-origin: left;
    transition: transform .28s var(--ease);
  }
  .nav button:hover { color: var(--ink2); }
  .nav button.active { color: var(--ink); }
  .nav button.active::after { transform: scaleX(1); }

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
    position: relative; margin: 8px 14px 0; border-radius: 16px;
    overflow: hidden; min-height: 78px;
    color: #fff;
    background: linear-gradient(135deg, var(--tide0) 0%, var(--tide1) 48%, #0b6f7c 100%);
    box-shadow: var(--shadow);
    isolation: isolate;
  }
  .hero .aurora {
    position: absolute; inset: -30%;
    background:
      radial-gradient(circle at 20% 30%, #1ec8d455, transparent 40%),
      radial-gradient(circle at 80% 20%, #ff8a2a33, transparent 42%),
      radial-gradient(circle at 60% 80%, #14b8c440, transparent 45%);
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
    background: var(--panel);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,.7);
    border-radius: 16px;
    padding: 10px 11px 8px;
    box-shadow: 0 14px 32px rgba(3,40,48,.12);
  }
  .ask label {
    display: block; font-size: .68rem; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
    margin: 0 0 6px 4px;
  }
  .row { display: flex; gap: 8px; align-items: stretch; }
  .row input {
    flex: 1; min-width: 0; border: 1px solid var(--line); border-radius: 12px;
    padding: 12px 13px; font-size: clamp(.88rem, 1.8vw, .98rem); background: #fff; color: var(--ink);
    font-family: inherit;
    transition: border-color .2s, box-shadow .2s;
  }
  .row input:focus {
    outline: none; border-color: var(--tide2);
    box-shadow: 0 0 0 3px rgba(14,168,180,.18);
  }
  .row button#askBtn {
    border: 0; border-radius: 12px; padding: 0 16px; flex: 0 0 auto;
    background: linear-gradient(135deg, var(--ember), var(--ember2));
    color: #fff; font-weight: 800; font-size: .9rem; cursor: pointer;
    letter-spacing: .01em;
    transition: transform .15s var(--ease), filter .15s;
    animation: breath 2.6s ease-in-out infinite;
  }
  .row button#askBtn:hover { filter: brightness(1.05); transform: translateY(-1px); }
  .row button#askBtn:active { transform: translateY(1px); }
  @keyframes breath {
    0%,100% { box-shadow: 0 8px 18px rgba(232,93,4,.28); }
    50% { box-shadow: 0 10px 26px rgba(255,138,42,.38); }
  }
  .ask-tools {
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px;
    margin-top: 6px; padding: 0 2px;
  }
  .health-cta {
    appearance: none; border: 1px solid color-mix(in srgb, var(--tide2) 45%, white);
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

  /* System pulse — 4 cards (3 dials + PC badge); no full-width strip */
  .pulse-wrap {
    flex: 0 0 auto;
    padding: 2px 12px 0;
  }
  .pulse-wrap .sec { padding: 4px 6px 3px; }
  .pulse {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: clamp(5px, 1vw, 10px);
  }
  .pulse-card {
    appearance: none; border: 1px solid var(--line); border-radius: 16px;
    background:
      radial-gradient(120% 90% at 50% 0%, rgba(30,200,212,.10), transparent 55%),
      rgba(255,255,255,.92);
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
    border-color: color-mix(in srgb, var(--tide2) 50%, white);
    box-shadow: 0 14px 30px rgba(3,40,48,.12);
  }
  .pulse-card:active { transform: none; }
  .pulse-card .k {
    font-size: .6rem; font-weight: 800; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted); margin: 1px 0 0;
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
    fill: none; stroke: #e2eef1; stroke-width: 7;
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
    font-size: clamp(.62rem, 1.2vw, .74rem); font-weight: 800;
    letter-spacing: -.01em; color: var(--ink); line-height: 1.2;
    display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2;
    overflow: hidden;
  }

  .qa-head {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 8px; padding: 2px 12px 0;
  }
  .qa-head .sec { padding: 0; font-size: .58rem; }
  .qa-head .qa-count {
    font-size: .58rem; font-weight: 700; color: var(--muted); letter-spacing: .02em;
  }

  /* compact-chips: content-width pills (not full-column bars); tip = title tooltip */
  .grid {
    flex: 1; overflow: auto; padding: 4px 12px 10px;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-flex-wrap: wrap; flex-wrap: wrap;
    -webkit-align-content: flex-start; align-content: flex-start;
    gap: 7px;
  }
  .sec-inline {
    -webkit-flex: 0 0 100%; flex: 0 0 100%;
    width: 100%;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-align: center; -webkit-align-items: center; align-items: center;
    gap: 8px;
    margin: 6px 0 1px; padding: 0 2px;
    font-size: .55rem; letter-spacing: .12em;
    text-transform: uppercase; color: var(--tide1); font-weight: 800;
  }
  .sec-inline:first-child { margin-top: 0; }
  .sec-inline::after {
    content: ""; -webkit-box-flex: 1; -webkit-flex: 1; flex: 1;
    height: 1px; min-width: 12px;
    background: linear-gradient(90deg, rgba(6,90,102,.22), transparent 88%);
  }
  /* Short, modern chips — width hugs the label */
  .tile {
    display: inline-block;
    -webkit-flex: 0 0 auto; flex: 0 0 auto;
    width: auto;
    max-width: 11.5rem;
    border: 1px solid rgba(7,45,56,.10);
    border-radius: 12px;
    background: #ffffff;
    margin: 0;
    padding: 7px 14px 7px 12px;
    cursor: pointer;
    text-align: left;
    color: #07131a;
    font: inherit;
    box-sizing: border-box;
    position: relative;
    vertical-align: top;
    box-shadow: 0 1px 0 rgba(3,40,48,.04);
    transition: transform .16s var(--ease), box-shadow .16s, border-color .16s,
      background .16s, filter .16s;
    animation: tileIn .35s var(--ease) both;
    animation-delay: calc(var(--i, 0) * 16ms);
  }
  .tile::before {
    content: "";
    position: absolute;
    left: 8px; top: 50%;
    width: 6px; height: 6px;
    margin-top: -3px;
    border-radius: 50%;
    background: var(--accent, #0a8a96);
    box-shadow: 0 0 0 3px rgba(14,168,180,.12);
  }
  @keyframes tileIn {
    from { opacity: 0; transform: translateY(5px) scale(.98); }
    to { opacity: 1; transform: none; }
  }
  .tile:hover {
    transform: translateY(-2px);
    border-color: rgba(10,138,150,.28);
    box-shadow: 0 10px 22px rgba(3,40,48,.10);
    filter: brightness(1.01);
  }
  .tile:active { transform: translateY(0); }
  .tile:focus { outline: none; }
  .tile:focus-visible {
    outline: 2px solid rgba(10,138,150,.45);
    outline-offset: 2px;
  }
  .tile .name {
    display: block;
    padding-left: 12px;
    font-weight: 800;
    font-size: .73rem;
    line-height: 1.2;
    margin: 0;
    letter-spacing: -.015em;
    color: #07131a !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
    padding: 11px 14px; font-size: .92rem; background: #fff;
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
  .chips button {
    flex: 0 0 auto; border: 1px solid var(--line); background: rgba(255,255,255,.85);
    border-radius: 10px; padding: 7px 12px; font-size: .74rem;
    font-weight: 700; cursor: pointer; color: var(--ink2); white-space: nowrap;
    font-family: inherit; transition: background .15s, color .15s, border-color .15s;
  }
  .chips button.on {
    background: var(--tide0); color: #fff; border-color: var(--tide0);
  }
  .cards {
    flex: 1; overflow: auto; padding: 2px 14px 18px;
    display: grid; grid-template-columns: 1fr; gap: 8px;
    align-content: start;
  }
  .card {
    display: grid; grid-template-columns: 1fr auto; gap: 8px 14px;
    border: 1px solid var(--line); border-radius: 16px;
    background: rgba(255,255,255,.86);
    padding: 14px 14px 14px 16px;
    align-items: center;
    transition: transform .18s var(--ease), box-shadow .18s;
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 28px rgba(3,40,48,.08);
  }
  .card h3 { margin: 0; font-size: .98rem; font-weight: 800; letter-spacing: -.01em; }
  .card p { margin: 4px 0 0; font-size: .78rem; color: var(--muted); line-height: 1.35; }
  .badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
  .badge {
    font-size: .62rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: .05em; padding: 3px 7px; border-radius: 6px;
    background: #e7f4f6; color: var(--tide0);
  }
  .badge.cat { background: #fff1e6; color: #9a3f08; }
  .card .actions { display: flex; flex-direction: column; gap: 6px; }
  .card button {
    border: 0; border-radius: 10px; padding: 9px 14px; font-weight: 800;
    font-size: .78rem; cursor: pointer; white-space: nowrap; font-family: inherit;
  }
  .card button.install {
    background: linear-gradient(135deg, var(--tide1), var(--tide3)); color: #fff;
  }
  .card button.remove {
    background: linear-gradient(135deg, #9a3320, var(--danger)); color: #fff;
  }
  .empty {
    padding: 36px 16px; text-align: center; color: var(--muted); font-size: .92rem;
  }
  .status-bar {
    flex: 0 0 auto;
    display: -webkit-box; display: -webkit-flex; display: flex;
    -webkit-box-align: center; -webkit-align-items: center; align-items: center;
    -webkit-box-pack: justify; -webkit-justify-content: space-between; justify-content: space-between;
    gap: 12px;
    padding: 8px 14px 9px 16px;
    background: linear-gradient(90deg, #031820, #0a1628 55%, #0b1a2e);
    color: #a9c8d0; font-size: .74rem; letter-spacing: .01em;
    position: relative; z-index: 2;
  }
  .status {
    -webkit-box-flex: 1; -webkit-flex: 1 1 auto; flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .status strong { color: #fff; font-weight: 700; }
  /* Aspera wordmark — company attribution on the dark bar (logo-native colors) */
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
    text-transform: uppercase; color: #6d8494;
  }
  a.aspera-mark svg { display: block; height: 14px; width: auto; }
  @media (max-width: 420px) {
    a.aspera-mark .by { display: none; }
  }
  @media (min-width: 560px) {
    .cards { grid-template-columns: 1fr 1fr; }
  }
  /* Wide control deck */
  @media (min-width: 720px) {
    .dial, .pc-badge-wrap { width: 72px; height: 72px; }
    .dial-val { font-size: .98rem; }
    .pulse-card { padding: 8px 6px 7px; }
    .grid { gap: 8px; }
  }
  /* Narrow: 2×2 pulse */
  @media (max-width: 560px) {
    .pulse { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  /* Narrow laptops / small window split */
  @media (max-width: 480px) {
    .top { padding: 8px 10px 0; }
    .logo { font-size: clamp(1.45rem, 7vw, 2rem); }
    .hero { margin: 6px 10px 0; min-height: 58px; }
    .hero .copy { padding: 8px 12px 14px; }
    .ask { margin: -14px 10px 0; padding: 8px; }
    .row { flex-wrap: wrap; }
    .row button#askBtn { flex: 1 1 auto; min-height: 40px; }
    .dial, .pc-badge-wrap { width: 52px; height: 52px; }
    .dial-val { font-size: .76rem; }
    .pulse-card { border-radius: 12px; padding: 6px 3px 6px; gap: 2px; }
    .grid { padding: 2px 8px 6px; gap: 6px; }
    .tile { padding: 6px 11px 6px 10px; max-width: 10.5rem; }
    .tile .name { font-size: .7rem; }
  }
  @media (max-width: 360px) {
    .tile { max-width: 100%; }
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
    .sec-inline { margin-top: 3px; }
    .tile { padding: 6px 12px 6px 10px; }
    .qa-head { padding-top: 0; }
  }
  @media (max-height: 720px) {
    .hero { min-height: 44px; }
    .hero .copy { padding: 6px 12px 10px; }
    .ember-line { margin-top: 3px; display: none; }
    .ask { margin-top: -10px; padding: 7px 9px 6px; }
    .health-cta { padding: 5px 10px; font-size: .72rem; }
    .pulse-wrap .sec, .qa-head .sec { font-size: .52rem; }
    .sec { padding-top: 2px; padding-bottom: 1px; }
    .grid { gap: 6px; padding-bottom: 6px; }
  }
  @media (max-height: 600px) {
    .hero { display: none; }
    .ask { margin: 6px 10px 0; }
    .dial, .pc-badge-wrap { width: 40px; height: 40px; }
    .dial-val { font-size: .68rem; }
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
      <button type="button" data-tab="home" class="active">Home</button>
      <button type="button" data-tab="store">App Store</button>
      <button type="button" data-tab="myapps">My Apps</button>
    </nav>
  </header>

  <section class="panel active" id="tab-home">
    <div class="hero">
      <div class="aurora" aria-hidden="true"></div>
      <svg class="wave" viewBox="0 0 1200 80" preserveAspectRatio="none" aria-hidden="true">
        <path fill="rgba(247,251,252,.22)" d="M0,40 C200,80 400,0 600,40 C800,80 1000,10 1200,40 L1200,80 L0,80 Z">
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
        <button id="askBtn" type="button">Ask →</button>
      </div>
      <div class="ask-tools">
        <button type="button" class="health-cta" id="healthBtn" title="Run a full health check in the live terminal">Health scan →</button>
        <p class="hint">Try “install chrome” · “why is it slow?” · or browse the App Store</p>
      </div>
    </div>

    <div class="pulse-wrap" id="pulseWrap">
      <div class="sec">This PC</div>
      <div class="pulse" id="pulse" aria-label="System pulse">
        <button type="button" class="pulse-card ok" data-pulse="cpu" title="Open health check">
          <div class="dial" aria-hidden="true">
            <svg viewBox="0 0 72 72">
              <circle class="track" cx="36" cy="36" r="28"/>
              <circle class="arc" id="pulseCpuArc" cx="36" cy="36" r="28"/>
            </svg>
            <div class="dial-val" id="pulseCpu">—</div>
          </div>
          <div class="k">CPU</div>
          <div class="s" id="pulseCpuS">sampling…</div>
        </button>
        <button type="button" class="pulse-card ok" data-pulse="mem" title="Open health check">
          <div class="dial" aria-hidden="true">
            <svg viewBox="0 0 72 72">
              <circle class="track" cx="36" cy="36" r="28"/>
              <circle class="arc" id="pulseMemArc" cx="36" cy="36" r="28"/>
            </svg>
            <div class="dial-val" id="pulseMem">—</div>
          </div>
          <div class="k">Memory</div>
          <div class="s" id="pulseMemS">used / total</div>
        </button>
        <button type="button" class="pulse-card ok" data-pulse="disk" title="Open disk tools">
          <div class="dial" aria-hidden="true">
            <svg viewBox="0 0 72 72">
              <circle class="track" cx="36" cy="36" r="28"/>
              <circle class="arc" id="pulseDiskArc" cx="36" cy="36" r="28"/>
            </svg>
            <div class="dial-val" id="pulseDisk">—</div>
          </div>
          <div class="k">Disk</div>
          <div class="s" id="pulseDiskS">used / total</div>
        </button>
        <button type="button" class="pulse-card pc" data-pulse="pc" title="PC configuration">
          <div class="pc-badge-wrap" aria-hidden="true">
            <div class="pc-badge">PC</div>
          </div>
          <div class="k">PC config</div>
          <div class="v" id="pulsePc">—</div>
          <div class="s" id="pulsePcS">hardware →</div>
        </button>
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
      <p>220+ apps — search, filter, install. Approve steps in the live terminal.</p>
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
      <button type="button" class="btn-primary" id="refreshInstalled">Refresh</button>
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
        <text x="26" y="16.2" fill="#FFFFFF" font-family="Ubuntu, Cantarell, Noto Sans, DejaVu Sans, sans-serif" font-size="13.5" font-weight="700" letter-spacing="2.2">SPERA</text>
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
    document.querySelectorAll(".nav button").forEach(b => {
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

  document.getElementById("pulseWrap").addEventListener("click", (e) => {
    const card = e.target.closest("[data-pulse]");
    if (!card) return;
    const key = card.getAttribute("data-pulse");
    const kw = pulseActions[key] || key;
    const labelEl = card.querySelector(".k");
    setStatus("<strong>Starting</strong> — " + ((labelEl && labelEl.textContent) || kw));
    post({ op: "run", kind: "kw", payload: kw });
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

  const grid = document.getElementById("grid");
  let tileI = 0;
  ACTIONS.forEach((a) => {
    if (a.kind === "sec") {
      const sec = document.createElement("div");
      sec.className = "sec-inline";
      sec.appendChild(document.createTextNode(a.label || ""));
      grid.appendChild(sec);
      return;
    }
    // DIV not <button>: WebKitGTK often paints blank white buttons
    // Compact content-width chip — tip only via native title tooltip
    const el = document.createElement("div");
    el.className = "tile";
    el.setAttribute("role", "button");
    el.setAttribute("tabindex", "0");
    el.style.setProperty("--i", String(tileI++));
    const accent = a.accent || "#0a8a96";
    el.style.setProperty("--accent", accent);
    try {
      const hex = String(accent).replace("#", "");
      if (hex.length === 6) {
        const r = parseInt(hex.slice(0, 2), 16);
        const g = parseInt(hex.slice(2, 4), 16);
        const b = parseInt(hex.slice(4, 6), 16);
        el.style.background = "linear-gradient(180deg, #ffffff 0%, rgba(" + r + "," + g + "," + b + ",0.10) 100%)";
        el.style.borderColor = "rgba(" + r + "," + g + "," + b + ",0.22)";
      }
    } catch (e) {}

    const name = document.createElement("div");
    name.className = "name";
    name.appendChild(document.createTextNode(a.label || ""));
    el.appendChild(name);

    el.setAttribute("title", a.tip || a.label || "");
    el.addEventListener("click", () => runAction(a));
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        runAction(a);
      }
    });
    grid.appendChild(el);
  });
  const qaCount = document.getElementById("qaCount");
  if (qaCount) qaCount.textContent = tileI + " shortcuts";

  function catalogSource() {
    return storeMode === "ai" ? AI_APPS : STORE_APPS;
  }

  function uniqueCats(rows) {
    const seen = [];
    rows.forEach(r => { if (r.cat && seen.indexOf(r.cat) < 0) seen.push(r.cat); });
    return seen;
  }

  function renderStoreChips() {
    const chips = document.getElementById("storeChips");
    chips.innerHTML = "";
    const modeApps = document.createElement("button");
    modeApps.type = "button";
    modeApps.textContent = "Apps (" + STORE_APPS.length + ")";
    modeApps.className = storeMode === "apps" ? "on" : "";
    modeApps.addEventListener("click", () => { storeMode = "apps"; storeCat = "All"; renderStore(); });
    chips.appendChild(modeApps);
    const modeAi = document.createElement("button");
    modeAi.type = "button";
    modeAi.textContent = "AI tools (" + AI_APPS.length + ")";
    modeAi.className = storeMode === "ai" ? "on" : "";
    modeAi.addEventListener("click", () => { storeMode = "ai"; storeCat = "All"; renderStore(); });
    chips.appendChild(modeAi);
    const rows = catalogSource();
    ["All"].concat(uniqueCats(rows)).forEach(cat => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = cat;
      if (cat === storeCat) b.className = "on";
      b.addEventListener("click", () => { storeCat = cat; renderStore(); });
      chips.appendChild(b);
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
      const left = document.createElement("div");
      const h = document.createElement("h3");
      h.textContent = r.name;
      const p = document.createElement("p");
      p.textContent = r.desc || "";
      const badges = document.createElement("div");
      badges.className = "badges";
      const cat = document.createElement("span");
      cat.className = "badge cat";
      cat.textContent = r.cat;
      badges.appendChild(cat);
      (r.methods || []).forEach(m => {
        const b = document.createElement("span");
        b.className = "badge";
        b.textContent = m;
        badges.appendChild(b);
      });
      left.appendChild(h); left.appendChild(p); left.appendChild(badges);
      const actions = document.createElement("div");
      actions.className = "actions";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "install";
      btn.textContent = "Install";
      btn.addEventListener("click", () => {
        setStatus("<strong>Install</strong> — " + r.name + " (confirm in terminal →)");
        post({ op: "install", kind: (r.kind || (storeMode === "ai" ? "ai" : "app")), id: r.id, name: r.name });
      });
      actions.appendChild(btn);
      card.appendChild(left);
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
      const left = document.createElement("div");
      const h = document.createElement("h3");
      h.textContent = r.name;
      const p = document.createElement("p");
      p.textContent = r.desc || (r.method + " · " + r.target);
      const badges = document.createElement("div");
      badges.className = "badges";
      const m = document.createElement("span");
      m.className = "badge";
      m.textContent = r.method;
      badges.appendChild(m);
      left.appendChild(h); left.appendChild(p); left.appendChild(badges);
      const actions = document.createElement("div");
      actions.className = "actions";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "remove";
      btn.textContent = "Remove";
      btn.addEventListener("click", () => {
        const ref = (r.method || "") + ":" + (r.target || "");
        setStatus("<strong>Remove</strong> — " + r.name + " (confirm in terminal →)");
        post({ op: "remove", ref: ref, name: r.name });
      });
      actions.appendChild(btn);
      card.appendChild(left);
      card.appendChild(actions);
      box.appendChild(card);
    });
    setStatus("<strong>My Apps</strong> — " + rows.length + " removable");
  }

  window.__setInstalled = function(rows) {
    installed = Array.isArray(rows) ? rows : [];
    renderMyApps();
  };

  document.getElementById("tabs").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-tab]");
    if (!b) return;
    showTab(b.getAttribute("data-tab"));
  });
  document.getElementById("askBtn").addEventListener("click", () => runText(q.value));
  document.getElementById("healthBtn").addEventListener("click", () => {
    setStatus("<strong>Starting</strong> — Health scan");
    post({ op: "run", kind: "kw", payload: "health" });
  });
  q.addEventListener("keydown", (e) => { if (e.key === "Enter") runText(q.value); });
  document.getElementById("storeQ").addEventListener("input", renderStore);
  document.getElementById("myQ").addEventListener("input", renderMyApps);
  document.getElementById("refreshInstalled").addEventListener("click", () => {
    setStatus("<strong>Scanning</strong> — installed apps…");
    post({ op: "list-installed" });
  });
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
  }, 3000);
  q.focus();
</script>
</body>
</html>
"""
    html = html.replace("__VERSION__", version)
    html = html.replace("__ACTIONS__", json.dumps(ACTIONS, ensure_ascii=False))
    html = html.replace("__STORE__", json.dumps(store_apps, ensure_ascii=False))
    html = html.replace("__AI__", json.dumps(ai_apps, ensure_ascii=False))
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
        right = self._build_terminal()
        # GUI stays compact; extra window width goes to the live terminal.
        paned.pack1(left, False, True)
        paned.pack2(right, True, False)
        self.win.add(paned)
        self.win.connect("size-allocate", self._on_size)
        self.win.show_all()
        self.win.present()
        self._spawn_tuxgenie()

    def _on_size(self, _w, alloc):
        if self._pos_set or alloc.width < 200:
            return
        try:
            self.paned.set_position(int(alloc.width * 0.30))
            self._pos_set = True
        except Exception:
            pass

    def _build_left(self):
        if self.WebKit2 is not None:
            return self._build_webkit()
        return self._build_gtk_fallback()

    def _build_webkit(self):
        WebKit2 = self.WebKit2
        view = WebKit2.WebView()
        try:
            settings = view.get_settings()
            settings.set_enable_developer_extras(False)
            settings.set_javascript_can_access_clipboard(False)
        except Exception:
            pass
        ucm = view.get_user_content_manager()
        ucm.register_script_message_handler("tuxgenie")
        ucm.connect("script-message-received::tuxgenie", self._on_webkit_msg)
        html = _shell_html(VERSION, self._store_apps, self._ai_apps)
        view.load_html(html, "file:///tuxgenie-shell/")
        frame = self.Gtk.Frame()
        frame.set_shadow_type(self.Gtk.ShadowType.NONE)
        frame.add(view)
        self.webview = view
        return frame

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
                    rows = [
                        {
                            "id": a.get("id"),
                            "name": a.get("name"),
                            "cat": a.get("cat"),
                            "desc": a.get("desc"),
                            "method": a.get("method"),
                            "target": a.get("target"),
                            "root": bool(a.get("root")),
                        }
                        for a in apps
                    ]
            except Exception as e:
                print("tuxgenie-app: installed scan failed:", e, file=sys.stderr)
            self.GLib.idle_add(self._push_installed_js, rows)

        threading.Thread(target=work, daemon=True).start()

    def _push_installed_js(self, rows):
        if self.webview is None:
            return False
        payload = json.dumps(rows, ensure_ascii=False)
        # Escape for JS string in single-quoted call — use JSON.parse on quoted JSON
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
            self.GLib.idle_add(self._push_pulse_js, data)

        threading.Thread(target=work, daemon=True).start()

    def _push_pulse_js(self, data):
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

    def _build_gtk_fallback(self):
        """Button deck when WebKit is missing — Store opens terminal catalogs."""
        Gtk = self.Gtk
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        hero.set_margin_top(16)
        hero.set_margin_bottom(12)
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
        sub = Gtk.Label(
            label="For the full modern App Store UI: sudo apt install gir1.2-webkit2-4.1"
        )
        sub.set_xalign(0)
        sub.set_line_wrap(True)
        hero.pack_start(title, False, False, 0)
        hero.pack_start(sub, False, False, 0)
        outer.pack_start(hero, False, False, 0)

        ask_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ask_row.set_margin_start(16)
        ask_row.set_margin_end(16)
        ask_row.set_margin_bottom(10)
        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("my wifi is not working")
        self._entry.connect("activate", self._on_ask)
        btn = Gtk.Button(label="Ask →")
        btn.connect("clicked", self._on_ask)
        ask_row.pack_start(self._entry, True, True, 0)
        ask_row.pack_start(btn, False, False, 0)
        outer.pack_start(ask_row, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        grid = Gtk.FlowBox()
        grid.set_valign(Gtk.Align.START)
        grid.set_max_children_per_line(2)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_homogeneous(True)
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)
        grid.set_margin_start(12)
        grid.set_margin_end(12)
        grid.set_margin_bottom(12)
        for a in ACTIONS:
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
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(8)
            box.set_margin_end(8)
            l1 = Gtk.Label()
            l1.set_xalign(0)
            l1.set_markup("<b>%s</b>" % a["label"].replace("&", "&amp;"))
            l2 = Gtk.Label(label=a.get("tip") or "")
            l2.set_xalign(0)
            l2.set_line_wrap(True)
            box.pack_start(l1, False, False, 0)
            box.pack_start(l2, False, False, 0)
            b.add(box)
            b.connect("clicked", self._on_action_btn, a)
            grid.add(b)
        scroll.add(grid)
        outer.pack_start(scroll, True, True, 0)
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
            # No WebKit store — fall back to terminal catalog keywords
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
            self.term.set_scrollback_lines(-1)
            self.term.set_mouse_autohide(True)
            self.term.set_scroll_on_keystroke(True)
            self.term.set_scroll_on_output(False)
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
                '  <span foreground="#9fd8de" size="small">'
                "<b>Live terminal</b> — approve installs here (y/n)</span>"
            )
        except Exception:
            pass
        hdr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        try:
            hdr_box.override_background_color(
                Gtk.StateFlags.NORMAL, Gdk.RGBA(0.03, 0.09, 0.12, 1)
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

    def _on_term_key(self, _term, event):
        ctrl = bool(event.state & self.Gdk.ModifierType.CONTROL_MASK)
        shift = bool(event.state & self.Gdk.ModifierType.SHIFT_MASK)
        name = (self.Gdk.keyval_name(event.keyval) or "").lower()
        if ctrl and shift and name == "c":
            self._copy()
            return True
        if ctrl and shift and name in ("v", "insert"):
            self.term.paste_clipboard()
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
