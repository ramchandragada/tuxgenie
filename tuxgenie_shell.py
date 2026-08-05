#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TuxGenie Unified Shell — flagship desktop app.

  ~60% modern control deck (WebKitGTK)  |  ~40% live VTE terminal

Clicking an action feeds the already-running TuxGenie session on the right.
No extra terminal windows. Falls back to a GTK button deck if WebKit is missing.
Exit code 3 = GTK/VTE unavailable (launcher falls back further).
"""
from __future__ import annotations

import json
import os
import shutil
import sys

APP_ID = "com.tuxgenie.TuxGenie"
VERSION = "6.83.0"

# Keep in sync with tuxgenie._BEGINNER_GUI_ACTIONS (keywords the live CLI accepts).
ACTIONS = [
    {"id": "fix", "label": "Fix a problem", "tip": "Describe what's wrong in plain English",
     "kind": "text", "payload": "", "accent": "#0d8a9a"},
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
    {"id": "apps", "label": "Install apps", "tip": "200-app catalog — Chrome, Steam, etc.",
     "kind": "kw", "payload": "apps", "accent": "#d4620f"},
    {"id": "remove", "label": "Remove apps", "tip": "Uninstall apps you no longer need",
     "kind": "kw", "payload": "remove", "accent": "#b54a2a"},
    {"id": "ai", "label": "AI tools catalog", "tip": "Ollama, Cursor, Claude Code, and more",
     "kind": "kw", "payload": "ai", "accent": "#0e7c86"},
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


def _resolve_tuxgenie() -> str:
    """Absolute path/command used inside the VTE bash -lc session."""
    which = shutil.which("tuxgenie")
    if which:
        return which
    # Dev / pip: run this repo's tuxgenie.py next to us or on sys.path.
    here = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(here, "tuxgenie.py")
    if os.path.isfile(cand):
        return "%s %s" % (sys.executable, cand)
    lib = "/usr/lib/tuxgenie/tuxgenie.py"
    if os.path.isfile(lib):
        return "%s %s" % (sys.executable, lib)
    return "tuxgenie"


def _load_gi():
    """Import Gtk + Vte; optionally WebKit2. Raises on hard failure."""
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


def _shell_html(version: str) -> str:
    """Ultra-modern control deck — brand-first, animated, teal/ember (no purple)."""
    actions_json = json.dumps(ACTIONS)
    # NOTE: keep this HTML/CSS self-contained; no external network.
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>TuxGenie</title>
<style>
  :root {{
    --ink: #0b1520;
    --muted: #5a6d78;
    --mist: #e8f1f4;
    --panel: rgba(255,255,255,.92);
    --ember: #e85d04;
    --ember2: #ff7a1a;
    --teal0: #063642;
    --teal1: #0a7a8a;
    --teal2: #14b8c4;
    --line: rgba(12,46,56,.12);
    --shadow: 0 18px 50px rgba(6,54,66,.18);
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; height: 100%;
    font-family: "Ubuntu", "Cantarell", "Noto Sans", "DejaVu Sans", system-ui, sans-serif;
    color: var(--ink);
    background:
      radial-gradient(1200px 500px at 10% -10%, #1ad0de55, transparent 55%),
      radial-gradient(900px 420px at 110% 0%, #ff7a1a33, transparent 50%),
      linear-gradient(165deg, #f3f8fa 0%, #e4eef2 45%, #dce9ee 100%);
    overflow: hidden;
  }}
  .app {{
    height: 100%; display: flex; flex-direction: column;
    animation: rise .55s cubic-bezier(.2,.8,.2,1) both;
  }}
  @keyframes rise {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to   {{ opacity: 1; transform: none; }}
  }}
  .hero {{
    position: relative; flex: 0 0 auto;
    padding: 22px 22px 18px;
    color: #fff;
    background: linear-gradient(135deg, var(--teal0) 0%, var(--teal1) 55%, var(--teal2) 100%);
    overflow: hidden;
  }}
  .hero::before, .hero::after {{
    content: ""; position: absolute; border-radius: 50%;
    filter: blur(2px); pointer-events: none;
  }}
  .hero::before {{
    width: 220px; height: 220px; right: -40px; top: -70px;
    background: #14b8c488;
    animation: drift 7s ease-in-out infinite alternate;
  }}
  .hero::after {{
    width: 160px; height: 160px; left: -50px; bottom: -80px;
    background: #ff7a1a33;
    animation: drift 9s ease-in-out infinite alternate-reverse;
  }}
  @keyframes drift {{
    from {{ transform: translate(0,0) scale(1); }}
    to   {{ transform: translate(-18px, 10px) scale(1.06); }}
  }}
  .brand {{
    position: relative; z-index: 1;
    font-size: 2rem; font-weight: 800; letter-spacing: -.03em;
    margin: 0 0 4px; text-shadow: 0 2px 18px rgba(0,0,0,.2);
  }}
  .tag {{
    position: relative; z-index: 1;
    margin: 0; opacity: .92; font-size: .95rem; font-weight: 500;
  }}
  .underline {{
    position: relative; z-index: 1;
    margin-top: 12px; height: 3px; width: 140px; border-radius: 99px;
    background: linear-gradient(90deg, var(--ember), var(--ember2), transparent);
    animation: sweep 2.4s ease-in-out infinite;
    transform-origin: left center;
  }}
  @keyframes sweep {{
    0%,100% {{ transform: scaleX(.7); opacity: .85; }}
    50% {{ transform: scaleX(1.15); opacity: 1; }}
  }}
  .meta {{
    position: relative; z-index: 1;
    margin-top: 10px; font-size: .75rem; opacity: .75;
  }}
  .ask {{
    margin: 14px 16px 8px; padding: 14px 14px 12px;
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 16px; box-shadow: var(--shadow);
    border-left: 4px solid var(--ember);
    backdrop-filter: blur(8px);
  }}
  .ask h2 {{
    margin: 0 0 8px; font-size: .78rem; letter-spacing: .08em;
    text-transform: uppercase; color: var(--muted); font-weight: 700;
  }}
  .row {{ display: flex; gap: 8px; }}
  .row input {{
    flex: 1; border: 1px solid var(--line); border-radius: 12px;
    padding: 12px 14px; font-size: .95rem; outline: none;
    background: #fff; color: var(--ink);
    transition: border-color .2s, box-shadow .2s;
  }}
  .row input:focus {{
    border-color: var(--teal1);
    box-shadow: 0 0 0 3px #0a7a8a22;
  }}
  .row button#askBtn {{
    border: 0; border-radius: 12px; padding: 0 18px;
    background: linear-gradient(135deg, var(--ember), var(--ember2));
    color: #fff; font-weight: 700; cursor: pointer;
    box-shadow: 0 8px 20px #e85d0444;
    transition: transform .15s, filter .15s;
    animation: breath 2.2s ease-in-out infinite;
  }}
  .row button#askBtn:hover {{ transform: translateY(-1px); filter: brightness(1.05); }}
  .row button#askBtn:active {{ transform: translateY(1px); }}
  @keyframes breath {{
    0%,100% {{ box-shadow: 0 8px 20px #e85d0444; }}
    50% {{ box-shadow: 0 10px 28px #ff7a1a66; }}
  }}
  .hint {{
    margin: 8px 0 0; font-size: .75rem; color: var(--muted);
  }}
  .sec {{
    padding: 6px 18px 4px; font-size: .72rem; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted); font-weight: 700;
  }}
  .grid {{
    flex: 1; overflow: auto; padding: 4px 12px 16px;
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
    align-content: start;
  }}
  .tile {{
    position: relative; border: 1px solid var(--line); border-radius: 14px;
    background: var(--panel); padding: 12px 12px 12px 14px;
    cursor: pointer; overflow: hidden;
    transition: transform .18s, box-shadow .18s, border-color .18s;
    animation: tileIn .45s cubic-bezier(.2,.8,.2,1) both;
    animation-delay: calc(var(--i, 0) * 35ms);
  }}
  @keyframes tileIn {{
    from {{ opacity: 0; transform: translateY(10px) scale(.98); }}
    to {{ opacity: 1; transform: none; }}
  }}
  .tile::before {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
    background: var(--accent, var(--teal1));
  }}
  .tile:hover {{
    transform: translateY(-2px);
    border-color: color-mix(in srgb, var(--accent) 45%, white);
    box-shadow: 0 14px 30px rgba(6,54,66,.14);
  }}
  .tile:active {{ transform: translateY(0); }}
  .tile .name {{ font-weight: 700; font-size: .92rem; margin: 0 0 4px; }}
  .tile .tip {{ margin: 0; font-size: .75rem; color: var(--muted); line-height: 1.35; }}
  .tile .go {{
    display: inline-block; margin-top: 8px; font-size: .72rem; font-weight: 700;
    color: #fff; background: var(--accent, var(--teal1));
    padding: 4px 10px; border-radius: 999px;
  }}
  .status {{
    flex: 0 0 auto; padding: 8px 16px 10px;
    background: linear-gradient(90deg, #071820, #0c2e38);
    color: #b7d4da; font-size: .75rem;
  }}
  .status strong {{ color: #fff; font-weight: 600; }}
  @media (max-width: 420px) {{
    .grid {{ grid-template-columns: 1fr; }}
    .brand {{ font-size: 1.6rem; }}
  }}
</style>
</head>
<body>
<div class="app">
  <header class="hero">
    <h1 class="brand">TuxGenie</h1>
    <p class="tag">Linux made easy — ask in plain English</p>
    <div class="underline"></div>
    <div class="meta">v{version} · live terminal on the right · free forever</div>
  </header>

  <section class="ask">
    <h2>What do you need?</h2>
    <div class="row">
      <input id="q" type="text" placeholder="my wifi is not working" autocomplete="off"/>
      <button id="askBtn" type="button">Ask →</button>
    </div>
    <p class="hint">Try: “install chrome” · “why is it slow?” · “no sound”</p>
  </section>

  <div class="sec">Quick actions</div>
  <div class="grid" id="grid"></div>
  <footer class="status" id="status"><strong>Ready</strong> — pick an action; it runs in the live terminal.</footer>
</div>
<script>
  const ACTIONS = {actions_json};
  const grid = document.getElementById('grid');
  const status = document.getElementById('status');
  const q = document.getElementById('q');

  function setStatus(msg) {{
    status.innerHTML = msg;
  }}

  function post(msg) {{
    try {{
      if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.tuxgenie) {{
        webkit.messageHandlers.tuxgenie.postMessage(JSON.stringify(msg));
        return true;
      }}
    }} catch (e) {{}}
    // GTK fallback injects window.tuxgenieSend
    if (typeof window.tuxgenieSend === 'function') {{
      window.tuxgenieSend(msg);
      return true;
    }}
    setStatus('<strong>Bridge offline</strong> — use the terminal on the right.');
    return false;
  }}

  function runText(text) {{
    text = (text || '').trim();
    if (!text) {{
      setStatus('<strong>Type something first</strong> — e.g. “my wifi is not working”.');
      q.focus();
      return;
    }}
    setStatus('<strong>Sending</strong> — ' + text.replace(/[<>&]/g, ''));
    post({{ op: 'run', kind: 'text', payload: text }});
  }}

  function runAction(a) {{
    setStatus('<strong>Starting</strong> — ' + a.label);
    if (a.kind === 'text') {{
      q.focus();
      setStatus('<strong>Type your problem</strong> above, then Ask →');
      return;
    }}
    post({{ op: 'run', kind: a.kind, payload: a.payload, label: a.label }});
  }}

  ACTIONS.forEach((a, i) => {{
    const el = document.createElement('button');
    el.type = 'button';
    el.className = 'tile';
    el.style.setProperty('--accent', a.accent || '#0a7a8a');
    el.style.setProperty('--i', i);
    el.innerHTML = '<div class="name"></div><p class="tip"></p><span class="go">Open →</span>';
    el.querySelector('.name').textContent = a.label;
    el.querySelector('.tip').textContent = a.tip;
    el.addEventListener('click', () => runAction(a));
    grid.appendChild(el);
  }});

  document.getElementById('askBtn').addEventListener('click', () => runText(q.value));
  q.addEventListener('keydown', (e) => {{
    if (e.key === 'Enter') runText(q.value);
  }});
  q.focus();
</script>
</body>
</html>
"""


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
        self._pos_set = False
        self._tg = _resolve_tuxgenie()

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
        self.win.set_default_size(1180, 740)
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
        # resize=True, shrink=False on both so neither collapses to nothing
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
        # ~60% GUI / ~40% terminal
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
        html = _shell_html(VERSION)
        view.load_html(html, "file:///tuxgenie-shell/")
        frame = self.Gtk.Frame()
        frame.set_shadow_type(self.Gtk.ShadowType.NONE)
        frame.add(view)
        self.webview = view
        return frame

    def _on_webkit_msg(self, _manager, message):
        try:
            js = message.get_js_value()
            raw = js.to_string() if js is not None else ""
        except Exception:
            try:
                raw = str(message)
            except Exception:
                return
        self._handle_payload(raw)

    def _handle_payload(self, raw):
        try:
            msg = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return
        if not isinstance(msg, dict):
            return
        if msg.get("op") != "run":
            return
        kind = msg.get("kind") or "text"
        payload = (msg.get("payload") or "").strip()
        if kind == "kw" and payload:
            self.feed_line(payload)
        elif kind == "text" and payload:
            self.feed_line(payload)
        elif kind == "text":
            # Focus ask — nothing to feed
            pass

    def _build_gtk_fallback(self):
        """Button deck when WebKit is not installed — still split with VTE."""
        Gtk = self.Gtk
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        hero.set_margin_top(16)
        hero.set_margin_bottom(12)
        hero.set_margin_start(16)
        hero.set_margin_end(16)
        title = Gtk.Label(label="TuxGenie")
        title.get_style_context().add_class("title")
        title.set_xalign(0)
        try:
            title.set_markup(
                '<span size="xx-large" weight="bold" foreground="#063642">TuxGenie</span>'
            )
        except Exception:
            pass
        sub = Gtk.Label(label="Linux made easy — live terminal on the right")
        sub.set_xalign(0)
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
            l1 = Gtk.Label(label=a["label"])
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
        if action.get("kind") == "text":
            if hasattr(self, "_entry"):
                self._entry.grab_focus()
            return
        payload = (action.get("payload") or "").strip()
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
        # Dark teal terminal palette — matches brand, easy on the eyes
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
                "<b>Live terminal</b> — approve steps here</span>"
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
        # Give the prompt a moment, then nudge focus to the terminal briefly
        self.GLib.timeout_add(400, self._focus_term)

    def _focus_term(self):
        try:
            self.term.grab_focus()
        except Exception:
            pass
        return False

    def feed_line(self, text: str):
        """Type a line into the live TuxGenie session (as if the user typed it)."""
        if not text or self.term is None:
            return
        data = (text.rstrip("\n") + "\n").encode("utf-8", "replace")
        try:
            # VTE ≥ 0.52
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
