#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TuxGenie Unified Shell — flagship desktop app.

  ~60% modern control deck (WebKitGTK)  |  ~40% live VTE terminal

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
VERSION = "6.86.0"

# Home quick actions. kind=tab switches Store/My Apps; kw feeds the live CLI.
ACTIONS = [
    {"id": "fix", "label": "Fix a problem", "tip": "Describe what's wrong in plain English",
     "kind": "kw", "payload": "fix", "accent": "#0d8a9a"},
    {"id": "health", "label": "Health check", "tip": "CPU, RAM, disk, services",
     "kind": "kw", "payload": "health", "accent": "#148f6a"},
    {"id": "network", "label": "Wi-Fi / Internet", "tip": "Can't connect? Safe scan + fixes",
     "kind": "kw", "payload": "network", "accent": "#0b7ea8"},
    {"id": "sound", "label": "Sound / Audio", "tip": "No sound or mic issues",
     "kind": "kw", "payload": "sound", "accent": "#1a8a7a"},
    {"id": "drivers", "label": "Drivers / NVIDIA", "tip": "Missing GPU or hardware drivers",
     "kind": "kw", "payload": "drivers", "accent": "#0f6f8c"},
    {"id": "perf", "label": "My PC is slow", "tip": "Scan + safe speed fixes",
     "kind": "kw", "payload": "perf", "accent": "#c45c12"},
    {"id": "apps", "label": "App Store", "tip": "Browse & install 220+ apps",
     "kind": "tab", "payload": "store", "accent": "#d4620f"},
    {"id": "remove", "label": "My Apps", "tip": "Uninstall apps from this PC",
     "kind": "tab", "payload": "myapps", "accent": "#b54a2a"},
    {"id": "ai", "label": "AI tools", "tip": "Ollama, Cursor, Claude Code, and more",
     "kind": "tab", "payload": "store-ai", "accent": "#0e7c86"},
    {"id": "backup", "label": "Backup settings", "tip": "Create or restore a config snapshot",
     "kind": "kw", "payload": "backup", "accent": "#1b7a4a"},
    {"id": "updates", "label": "System updates", "tip": "Check and install OS updates",
     "kind": "kw", "payload": "updates", "accent": "#0d6e8c"},
    {"id": "selfupd", "label": "Update TuxGenie", "tip": "Get the latest TuxGenie release",
     "kind": "kw", "payload": "u", "accent": "#c35508"},
    {"id": "settings", "label": "Settings", "tip": "AI provider, keys, preferences",
     "kind": "kw", "payload": "s", "accent": "#3d5a80"},
    {"id": "menu", "label": "Show menu", "tip": "Bring the full terminal menu back",
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
    """Self-contained App Store deck — no external network/CDN."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>TuxGenie</title>
<style>
  :root {
    --ink: #0b1520;
    --muted: #5a6d78;
    --mist: #e8f1f4;
    --panel: rgba(255,255,255,.94);
    --ember: #e85d04;
    --ember2: #ff7a1a;
    --teal0: #063642;
    --teal1: #0a7a8a;
    --teal2: #14b8c4;
    --line: rgba(12,46,56,.12);
    --danger: #b54a2a;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; height: 100%;
    font-family: "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", system-ui, sans-serif;
    color: var(--ink);
    background:
      radial-gradient(1200px 500px at 10% -10%, #1ad0de55, transparent 55%),
      radial-gradient(900px 420px at 110% 0%, #ff7a1a33, transparent 50%),
      linear-gradient(165deg, #f3f8fa 0%, #e6eef2 55%, #dce8ec 100%);
  }
  .app { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .hero {
    flex: 0 0 auto; padding: 16px 18px 10px;
    background: linear-gradient(135deg, var(--teal0), #0a7a8a 55%, #12a3b0);
    color: #fff; position: relative; overflow: hidden;
  }
  .hero::after {
    content: ""; position: absolute; right: -40px; top: -50px;
    width: 180px; height: 180px; border-radius: 50%;
    background: #14b8c455;
  }
  .brand { margin: 0; font-size: 1.75rem; font-weight: 800; letter-spacing: -.02em; }
  .tag { margin: 4px 0 0; opacity: .9; font-size: .92rem; }
  .meta { margin-top: 8px; font-size: .75rem; opacity: .85; }
  a.site { color: #b8eef2; }
  .tabs {
    display: flex; gap: 6px; padding: 10px 12px 0; flex: 0 0 auto;
  }
  .tabs button {
    border: 1px solid var(--line); background: var(--panel);
    border-radius: 999px; padding: 8px 14px; font-weight: 700;
    font-size: .8rem; cursor: pointer; color: var(--ink);
  }
  .tabs button.active {
    background: linear-gradient(135deg, var(--teal1), var(--teal2));
    color: #fff; border-color: transparent;
  }
  .panel { display: none; flex: 1; min-height: 0; flex-direction: column; }
  .panel.active { display: flex; }
  .ask { padding: 12px 16px 8px; }
  .ask h2 { margin: 0 0 8px; font-size: .95rem; }
  .row { display: flex; gap: 8px; }
  .row input {
    flex: 1; border: 1px solid var(--line); border-radius: 12px;
    padding: 12px 14px; font-size: .95rem; background: #fff;
  }
  .row input:focus { outline: none; border-color: var(--teal1); box-shadow: 0 0 0 3px #0a7a8a22; }
  .row button#askBtn, .btn-primary {
    border: 0; border-radius: 12px; padding: 0 16px;
    background: linear-gradient(135deg, var(--ember), var(--ember2));
    color: #fff; font-weight: 700; cursor: pointer;
  }
  .hint { margin: 8px 0 0; font-size: .75rem; color: var(--muted); }
  .sec {
    padding: 6px 16px 4px; font-size: .72rem; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted); font-weight: 700;
  }
  .grid {
    flex: 1; overflow: auto; padding: 4px 12px 16px;
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
    align-content: start;
  }
  .tile {
    position: relative; border: 1px solid var(--line); border-radius: 14px;
    background: var(--panel); padding: 12px 12px 12px 14px;
    cursor: pointer; text-align: left;
    transition: transform .18s, box-shadow .18s;
  }
  .tile::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
    background: var(--accent, var(--teal1));
  }
  .tile:hover { transform: translateY(-2px); box-shadow: 0 14px 30px rgba(6,54,66,.14); }
  .tile .name { font-weight: 700; font-size: .9rem; margin: 0 0 4px; }
  .tile .tip { margin: 0; font-size: .74rem; color: var(--muted); line-height: 1.35; }
  .tile .go {
    display: inline-block; margin-top: 8px; font-size: .72rem; font-weight: 700;
    color: #fff; background: var(--accent, var(--teal1));
    padding: 4px 10px; border-radius: 8px;
  }
  .store-bar {
    display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 12px 6px;
    align-items: center;
  }
  .store-bar input {
    flex: 1 1 160px; min-width: 140px;
    border: 1px solid var(--line); border-radius: 12px;
    padding: 10px 12px; font-size: .9rem; background: #fff;
  }
  .chips {
    display: flex; flex-wrap: nowrap; gap: 6px; overflow-x: auto;
    padding: 0 12px 8px; scrollbar-width: thin;
  }
  .chips button {
    flex: 0 0 auto; border: 1px solid var(--line); background: #fff;
    border-radius: 999px; padding: 6px 12px; font-size: .75rem;
    font-weight: 600; cursor: pointer; color: var(--ink); white-space: nowrap;
  }
  .chips button.on {
    background: var(--teal0); color: #fff; border-color: var(--teal0);
  }
  .cards {
    flex: 1; overflow: auto; padding: 4px 12px 16px;
    display: grid; grid-template-columns: 1fr; gap: 8px;
    align-content: start;
  }
  .card {
    display: grid; grid-template-columns: 1fr auto; gap: 8px 12px;
    border: 1px solid var(--line); border-radius: 14px;
    background: var(--panel); padding: 12px 14px;
    align-items: center;
  }
  .card h3 { margin: 0; font-size: .95rem; }
  .card p { margin: 4px 0 0; font-size: .78rem; color: var(--muted); line-height: 1.35; }
  .badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
  .badge {
    font-size: .65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: .04em; padding: 2px 7px; border-radius: 6px;
    background: #e8f4f6; color: var(--teal0);
  }
  .badge.cat { background: #fff3e8; color: #9a4a10; }
  .card .actions { display: flex; flex-direction: column; gap: 6px; }
  .card button {
    border: 0; border-radius: 10px; padding: 8px 14px; font-weight: 700;
    font-size: .78rem; cursor: pointer; white-space: nowrap;
  }
  .card button.install {
    background: linear-gradient(135deg, var(--teal1), var(--teal2)); color: #fff;
  }
  .card button.remove {
    background: linear-gradient(135deg, #a63d22, var(--danger)); color: #fff;
  }
  .card button:active { transform: translateY(1px); }
  .empty {
    padding: 28px 16px; text-align: center; color: var(--muted); font-size: .9rem;
  }
  .status {
    flex: 0 0 auto; padding: 8px 16px 10px;
    background: linear-gradient(90deg, #071820, #0c2e38);
    color: #b7d4da; font-size: .75rem;
  }
  .status strong { color: #fff; font-weight: 600; }
  @media (min-width: 520px) {
    .cards { grid-template-columns: 1fr 1fr; }
  }
</style>
</head>
<body>
<div class="app">
  <header class="hero">
    <h1 class="brand">TuxGenie</h1>
    <p class="tag">Linux made easy — App Store + live terminal</p>
    <div class="meta">v__VERSION__ ·
      <a class="site" href="https://www.tuxgenie.com" id="siteLink">www.tuxgenie.com</a>
    </div>
  </header>

  <nav class="tabs" id="tabs">
    <button type="button" data-tab="home" class="active">Home</button>
    <button type="button" data-tab="store">App Store</button>
    <button type="button" data-tab="myapps">My Apps</button>
  </nav>

  <section class="panel active" id="tab-home">
    <div class="ask">
      <h2>What do you need?</h2>
      <div class="row">
        <input id="q" type="text" placeholder="my wifi is not working" autocomplete="off"/>
        <button id="askBtn" type="button">Ask →</button>
      </div>
      <p class="hint">Try: “install chrome” · “why is it slow?” · or open the App Store</p>
    </div>
    <div class="sec">Quick actions</div>
    <div class="grid" id="grid"></div>
  </section>

  <section class="panel" id="tab-store">
    <div class="store-bar">
      <input id="storeQ" type="search" placeholder="Search apps — chrome, steam, notes…" autocomplete="off"/>
    </div>
    <div class="chips" id="storeChips"></div>
    <div class="cards" id="storeCards"></div>
  </section>

  <section class="panel" id="tab-myapps">
    <div class="store-bar">
      <input id="myQ" type="search" placeholder="Search installed apps…" autocomplete="off"/>
      <button type="button" class="btn-primary" id="refreshInstalled" style="padding:10px 14px">Refresh</button>
    </div>
    <div class="cards" id="myCards"></div>
  </section>

  <footer class="status" id="status"><strong>Ready</strong> — installs run in the live terminal (approve with y/n).</footer>
</div>
<script>
  const ACTIONS = __ACTIONS__;
  const STORE_APPS = __STORE__;
  const AI_APPS = __AI__;
  let storeMode = "apps"; // apps | ai
  let storeCat = "All";
  let installed = [];

  const status = document.getElementById("status");
  const q = document.getElementById("q");

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
    if (name === "store") { /* keep storeMode */ }
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".tabs button").forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-tab") === name);
    });
    const panel = document.getElementById("tab-" + name);
    if (panel) panel.classList.add("active");
    if (name === "store") renderStore();
    if (name === "myapps") {
      setStatus("<strong>Scanning</strong> — installed apps…");
      post({ op: "list-installed" });
    }
  }

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

  // Home tiles
  const grid = document.getElementById("grid");
  ACTIONS.forEach((a, i) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "tile";
    el.style.setProperty("--accent", a.accent || "#0a7a8a");
    el.innerHTML = '<div class="name"></div><p class="tip"></p><span class="go">Open →</span>';
    el.querySelector(".name").textContent = a.label;
    el.querySelector(".tip").textContent = a.tip;
    el.querySelector(".go").textContent = (a.kind === "tab") ? "Browse →" : "Run →";
    el.addEventListener("click", () => runAction(a));
    grid.appendChild(el);
  });

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

  // Called from Python after scanning
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
        self.win.set_default_size(1240, 780)
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
        paned.pack1(left, True, False)
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
            self.paned.set_position(int(alloc.width * 0.60))
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
            label="Install gir1.2-webkit2-4.1 for the App Store UI — terminal still works"
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
            b = Gtk.Button()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(8)
            box.set_margin_end(8)
            l1 = Gtk.Label()
            l1.set_xalign(0)
            l1.set_markup("<b>%s</b>" % a["label"].replace("&", "&amp;"))
            l2 = Gtk.Label(label=a["tip"])
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
