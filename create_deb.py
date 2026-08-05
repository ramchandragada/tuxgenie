#!/usr/bin/env python3
"""
create_deb.py - Builds tuxgenie_3.0.0_all.deb without dpkg-deb.

A .deb file is an ar archive containing:
  debian-binary   - version string "2.0"
  control.tar.gz  - DEBIAN/ metadata (control, postinst, prerm, postrm, md5sums)
  data.tar.gz     - the actual installed files (/usr/bin/tuxgenie, /usr/lib/..., etc.)

Run: python3 create_deb.py
"""

import io
import os
import sys
import gzip
import tarfile
import hashlib
import zlib
import struct
import math

# ── Icon generator (pure stdlib - no Pillow needed) ──────────────────────────

def _generate_tuxgenie_icon(size):
    """
    Draw the TuxGenie icon at any size using only Python stdlib.

    Design (scales with 'size', master grid is 64x64):
      - Vibrant blue-to-indigo gradient circle background
      - Large centred Tux penguin (black body, white belly, orange beak/feet)
      - Classic eye detail (white patches → black pupils → white shine)
      - Wings as side flippers
      - Small gold star sparkle top-right (48px+)
    """
    img = [[[0, 0, 0, 0] for _ in range(size)] for _ in range(size)]
    S  = size / 64.0
    MX = size / 2.0
    MY = size / 2.0

    # ── helpers ──────────────────────────────────────────────────────────────

    def _set(ix, iy, r, g, b, a=255):
        if 0 <= ix < size and 0 <= iy < size:
            img[iy][ix] = [r, g, b, a]

    def _blend(ix, iy, r, g, b, alpha):
        if 0 <= ix < size and 0 <= iy < size:
            s = img[iy][ix]
            a = alpha / 255.0
            img[iy][ix] = [
                int(s[0]*(1-a) + r*a),
                int(s[1]*(1-a) + g*a),
                int(s[2]*(1-a) + b*a),
                max(s[3], alpha),
            ]

    def disk(cx, cy, rad, r, g, b, a=255):
        ri = int(rad) + 2
        for dy in range(-ri, ri + 1):
            for dx in range(-ri, ri + 1):
                d = math.sqrt(dx*dx + dy*dy)
                if d > rad + 1:
                    continue
                ix, iy = int(cx) + dx, int(cy) + dy
                if d <= rad - 0.5:
                    _set(ix, iy, r, g, b, a)
                else:
                    af = max(0.0, min(1.0, rad - d + 0.5))
                    _blend(ix, iy, r, g, b, int(a * af))

    def ellipse(cx, cy, rx, ry, r, g, b, a=255):
        for dy in range(-int(ry) - 2, int(ry) + 3):
            for dx in range(-int(rx) - 2, int(rx) + 3):
                nx = dx / max(rx, 0.01)
                ny = dy / max(ry, 0.01)
                d = math.sqrt(nx*nx + ny*ny)
                if d > 1 + 1/max(rx, ry):
                    continue
                ix, iy = int(cx) + dx, int(cy) + dy
                if d <= 1 - 0.5/max(rx, ry):
                    _set(ix, iy, r, g, b, a)
                else:
                    af = max(0.0, min(1.0, (1 - d) * max(rx, ry) + 0.5))
                    _blend(ix, iy, r, g, b, int(a * af))

    # ── 1. Blue gradient background circle ───────────────────────────────────
    bg_r = size / 2 - 0.5
    for y in range(size):
        for x in range(size):
            if (x - MX)**2 + (y - MY)**2 <= bg_r**2:
                t  = (x + y) / (size * 2.0)
                rr = int(22  + t * 18)
                gg = int(100 + t * 22)
                bb = int(215 + t * 22)
                img[y][x] = [rr, gg, bb, 255]

    # ── Penguin geometry (64px master grid) ──────────────────────────────────
    HC_X, HC_Y  = MX,          MY - 16*S    # head centre
    BC_X, BC_Y  = MX,          MY +  8*S    # body centre
    WL_X, WL_Y  = MX - 16*S,   MY +  5*S   # left wing
    WR_X, WR_Y  = MX + 16*S,   MY +  5*S   # right wing
    FL_X, FL_Y  = MX -  6*S,   BC_Y + 16*S # left foot
    FR_X, FR_Y  = MX +  6*S,   BC_Y + 16*S # right foot

    # ── 2. Wings (drawn behind body) ─────────────────────────────────────────
    ellipse(WL_X, WL_Y, 5*S, 10*S, 28, 28, 35)
    ellipse(WR_X, WR_Y, 5*S, 10*S, 28, 28, 35)

    # ── 3. Black body ────────────────────────────────────────────────────────
    ellipse(BC_X, BC_Y, 13*S, 17*S, 28, 28, 35)

    # ── 4. White belly ───────────────────────────────────────────────────────
    ellipse(BC_X, BC_Y + 1*S, 8*S, 12*S, 238, 238, 232)

    # ── 5. Black head ────────────────────────────────────────────────────────
    disk(HC_X, HC_Y, 10*S, 28, 28, 35)

    # ── 6. White face patch ──────────────────────────────────────────────────
    ellipse(HC_X, HC_Y + 2*S, 7*S, 6.5*S, 238, 238, 232)

    # ── 7. Eyes: white → black pupil → shine ─────────────────────────────────
    EYE_Y  = HC_Y - 2*S
    EYE_OX = 3.5*S
    disk(HC_X - EYE_OX, EYE_Y, 2.5*S, 255, 255, 255)
    disk(HC_X + EYE_OX, EYE_Y, 2.5*S, 255, 255, 255)
    disk(HC_X - EYE_OX, EYE_Y, 1.3*S, 20,  20,  25)
    disk(HC_X + EYE_OX, EYE_Y, 1.3*S, 20,  20,  25)
    if size >= 32:
        disk(HC_X - EYE_OX + 0.9*S, EYE_Y - 0.9*S, max(0.6, 0.7*S), 255, 255, 255)
        disk(HC_X + EYE_OX + 0.9*S, EYE_Y - 0.9*S, max(0.6, 0.7*S), 255, 255, 255)

    # ── 8. Orange beak ───────────────────────────────────────────────────────
    ellipse(HC_X, HC_Y + 4*S, 3.2*S, 2.2*S, 255, 145, 0)

    # ── 9. Orange feet (32px+) ───────────────────────────────────────────────
    if size >= 32:
        ellipse(FL_X, FL_Y, 5*S, 2.5*S, 255, 145, 0)
        ellipse(FR_X, FR_Y, 5*S, 2.5*S, 255, 145, 0)

    # ── 10. Gold sparkle top-right (48px+) ───────────────────────────────────
    if size >= 48:
        scx = MX + 17*S
        scy = MY - 19*S
        sr  = 4.5*S
        for ai in range(8):
            ang    = math.radians(ai * 45)
            length = sr if ai % 2 == 0 else sr * 0.45
            ri_f   = 0.5
            while ri_f <= length:
                _set(int(scx + ri_f*math.cos(ang)), int(scy + ri_f*math.sin(ang)), 255, 220, 60)
                ri_f += 0.5
        disk(scx, scy, max(1.5, 1.4*S), 255, 240, 100)

    # ── 11. Clip to circle ────────────────────────────────────────────────────
    for y in range(size):
        for x in range(size):
            if (x - MX)**2 + (y - MY)**2 > (size/2)**2:
                img[y][x] = [0, 0, 0, 0]

    # ── 12. Encode as PNG (RGBA 8-bit) ───────────────────────────────────────
    def png_chunk(name, data):
        body = name + data
        return (struct.pack('>I', len(data)) + body +
                struct.pack('>I', zlib.crc32(body) & 0xffffffff))

    raw = b''.join(
        b'\x00' + bytes(c for pixel in row for c in pixel)
        for row in img
    )
    return (b'\x89PNG\r\n\x1a\n'
            + png_chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + png_chunk(b'IDAT', zlib.compress(raw, 9))
            + png_chunk(b'IEND', b''))


# ── Package metadata ──────────────────────────────────────────────────────────
PACKAGE = "tuxgenie"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def _read_version_from_source():
    """Read __version__ from tuxgenie.py so local builds stay in sync."""
    import re
    try:
        with open(os.path.join(SCRIPT_DIR, "tuxgenie.py")) as f:
            m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
        return m.group(1) if m else "0.0.0"
    except FileNotFoundError:
        return "0.0.0"

VERSION = os.environ.get("TUXGENIE_VERSION") or _read_version_from_source()
ARCH    = "all"
DEB_OUT = f"{PACKAGE}_{VERSION}_{ARCH}.deb"

# ── Read the main Python script ───────────────────────────────────────────────
src = os.path.join(SCRIPT_DIR, "tuxgenie.py")
if not os.path.exists(src):
    sys.exit(f"ERROR: {src} not found - run from the ai-terminal directory.")

with open(src, "rb") as fh:
    TUXGENIE_PY = fh.read()

# Unified Shell (flagship desktop: WebKit/GTK control deck + live VTE).
# Ships as /usr/bin/tuxgenie-app and /usr/lib/tuxgenie/tuxgenie_shell.py.
_shell_src = os.path.join(SCRIPT_DIR, "tuxgenie_shell.py")
if not os.path.exists(_shell_src):
    sys.exit(f"ERROR: {_shell_src} not found — Unified Shell is required for packaging.")
with open(_shell_src, "rb") as fh:
    TUXGENIE_SHELL = fh.read()
# Executable copy for PATH (same source; shebang already present).
TUXGENIE_APP = TUXGENIE_SHELL

# ── Read the community fixes JSON (ships with every release) ─────────────────
_community_path = os.path.join(SCRIPT_DIR, "community_fixes.json")
if os.path.exists(_community_path):
    with open(_community_path, "rb") as fh:
        COMMUNITY_FIXES = fh.read()
else:
    COMMUNITY_FIXES = b'{"version": 1, "entries": []}\n'

# ── Icons at standard hicolor sizes ──────────────────────────────────────────
# Prefer the polished designed icon (assets/tuxgenie-<size>.png, rendered from
# assets/tuxgenie.svg — the single brand source used app-wide and on the site).
# Fall back to the procedural generator only if those assets are missing, so the
# build never breaks.
print("  Loading icons ", end="", flush=True)
ICONS = {}
_ASSETS = os.path.join(SCRIPT_DIR, "assets")
for _sz in (16, 32, 48, 64, 128, 256):
    _png = os.path.join(_ASSETS, f"tuxgenie-{_sz}.png")
    if os.path.exists(_png):
        with open(_png, "rb") as _fh:
            ICONS[_sz] = _fh.read()
    else:
        ICONS[_sz] = _generate_tuxgenie_icon(_sz)
    print(".", end="", flush=True)
print(f" done ({sum(len(v) for v in ICONS.values())//1024} KB total)")

INSTALLED_KB = max(1, (len(TUXGENIE_PY) + len(TUXGENIE_SHELL) + sum(len(v) for v in ICONS.values()) + len(COMMUNITY_FIXES) + 1023) // 1024 + 8)

# ── File contents (all in-memory) ─────────────────────────────────────────────

LAUNCHER = b"""\
#!/bin/bash
# Run TuxGenie; if Python crashes at startup, offer emergency recovery
python3 /usr/lib/tuxgenie/tuxgenie.py "$@"
_rc=$?
if [ $_rc -ne 0 ] && [ $# -eq 0 ] && [ -t 0 ] && [ -t 1 ]; then
    echo ""
    echo "  TuxGenie failed to start (exit $_rc)."
    echo "  Run: tuxgenie-update   to download the latest version and fix it."
fi
exit $_rc
"""

EMERGENCY_UPDATE = b"""\
#!/bin/bash
# tuxgenie-update: emergency recovery - replaces the installed script
# from GitHub without needing TuxGenie itself to be working.
set -e
DEST=/usr/lib/tuxgenie/tuxgenie.py
RAW_URL="https://raw.githubusercontent.com/ramchandragada/tuxgenie/main/tuxgenie.py"

if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    echo "Error: need curl or wget. Install with: sudo apt install curl" >&2; exit 1
fi

echo "Downloading latest TuxGenie..."
TMP=$(mktemp /tmp/tuxgenie_update_XXXXXX.py)
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$RAW_URL" -o "$TMP"
else
    wget -qO "$TMP" "$RAW_URL"
fi

if ! python3 -m py_compile "$TMP" 2>/dev/null; then
    echo "Downloaded file has syntax errors - aborting to avoid making things worse." >&2
    rm -f "$TMP"; exit 1
fi

sudo cp "$TMP" "$DEST"
sudo chmod 644 "$DEST"
rm -f "$TMP"
echo "Done! TuxGenie updated. Run: tuxgenie"
"""

CONTROL = f"""\
Package: {PACKAGE}
Version: {VERSION}
Section: utils
Priority: optional
Architecture: {ARCH}
Installed-Size: {INSTALLED_KB}
Depends: python3 (>= 3.8)
Recommends: python3-pip, python3-gi, gir1.2-gtk-3.0, gir1.2-vte-2.91, gir1.2-webkit2-4.1 | gir1.2-webkit2-4.0, python3-tk, xterm | gnome-terminal | konsole | xfce4-terminal | mate-terminal | lxterminal | ptyxis
Conflicts: ai-terminal, tuxgenie (<< {VERSION})
Replaces: ai-terminal, tuxgenie (<< {VERSION})
Provides: ai-terminal
Maintainer: TuxGenie Project <ramchandragada@users.noreply.github.com>
Homepage: https://github.com/ramchandragada/tuxgenie
Description: AI-powered Linux assistant (plain-English troubleshooting)
 TuxGenie fixes Linux problems described in plain English. Features include: a
 system health dashboard, network diagnostics, security audit, disk management,
 service control, log analysis, update management, script generation, cron
 scheduling, permission fixer, boot repair, Docker management, config backup,
 hardware info, SSH diagnostics, process manager, and session rollback.
 .
 Desktop: Unified Shell (tuxgenie-app) — modern control deck + live terminal in
 one window. Falls back to tuxgenie --gui (Tk) or a plain terminal if needed.
 .
 Free to run: choose a free AI provider on first launch (Google Gemini or Groq,
 no credit card), local Ollama, or Anthropic Claude for best quality. Common
 terminal commands run with no key at all.
""".encode()

POSTINST = b"""\
#!/bin/bash
set -e
case "$1" in
  configure)
    # Remove old ai-terminal package leftovers
    rm -f  /usr/bin/aifix 2>/dev/null || true
    rm -rf /usr/lib/ai-terminal 2>/dev/null || true
    rm -f  /usr/share/applications/ai-terminal.desktop 2>/dev/null || true

    # NOTE: no dependency installation happens here.
    # Debian policy forbids network access from maintainer scripts, and the free
    # providers (Google Gemini, Groq) need no extra packages at all - TuxGenie
    # talks to them over the standard-library urllib. The 'anthropic' SDK is only
    # needed if the user explicitly connects Claude, and in that case the app
    # installs it lazily, in user space, on first use (see _bootstrap_anthropic_sdk
    # in tuxgenie.py). So there is nothing to fetch as root at install time.

    # Always (re)write tuxgenie-gui launcher to keep the terminal-detection
    # logic in sync with create_deb.py. This is the same script that ships
    # in /usr/bin/tuxgenie-gui via data.tar.gz; we re-create it on every
    # install/upgrade so older systems get the latest fixes.
    cat > /usr/bin/tuxgenie-gui << 'GUISCRIPT'
#!/bin/bash
# TuxGenie GUI launcher - opens tuxgenie as an app-like, single-instance window.
# Avoid x-terminal-emulator (can resolve to Warp on 26.04+).

# Unified Shell first (WebKit/GTK control deck + live VTE). Exit 3 = GTK/VTE
# unavailable or spawn failed -> fall through.
if command -v tuxgenie-app >/dev/null 2>&1; then
    tuxgenie-app
    rc=$?
    [ "$rc" != "3" ] && exit "$rc"
fi

# Phase D: beginner Tk window (exit 2 = no python3-tk).
if command -v tuxgenie >/dev/null 2>&1; then
    tuxgenie --gui
    rc=$?
    [ "$rc" != "2" ] && exit "$rc"
fi

LOCK="${XDG_RUNTIME_DIR:-/tmp}/tuxgenie-$(id -u).lock"

# Single instance: if a TuxGenie session is already open, don't stack a new
# window. Best-effort raise the existing one (X11 only; GNOME/Wayland blocks
# cross-app activation); otherwise just notify and exit.
if command -v flock >/dev/null 2>&1 && ! flock -n "$LOCK" -c true 2>/dev/null; then
    if [ "${XDG_SESSION_TYPE:-}" != "wayland" ]; then
        command -v wmctrl >/dev/null 2>&1 && wmctrl -a "TuxGenie" 2>/dev/null && exit 0
        command -v xdotool >/dev/null 2>&1 && xdotool search --name "^TuxGenie$" windowactivate >/dev/null 2>&1 && exit 0
    fi
    command -v notify-send >/dev/null 2>&1 && notify-send "TuxGenie" "TuxGenie is already open in another window." --icon=tuxgenie
    exit 0
fi

# Inside the terminal: set an app-like window title, then hold the single-instance
# lock for the whole session so repeat clicks are detected above.
CMD='printf "\\033]0;TuxGenie\\007"; exec 9>"'"$LOCK"'" 2>/dev/null; flock -n 9 2>/dev/null || { echo "TuxGenie is already open in another window."; sleep 2; exit 0; }; tuxgenie; echo; read -rp "Press Enter to close..." _'
try_term() {
    case "$1" in
        ptyxis)          exec ptyxis -- bash -c "$CMD" ;;
        gnome-terminal)  exec gnome-terminal -- bash -c "$CMD" ;;
        konsole)         exec konsole --hold -e bash -c "$CMD" ;;
        xfce4-terminal)  exec xfce4-terminal --hold --command="bash -c '$CMD'" ;;
        mate-terminal)   exec mate-terminal -- bash -c "$CMD" ;;
        lxterminal)      exec lxterminal -e bash -c "$CMD" ;;
        tilix)           exec tilix -e bash -c "$CMD" ;;
        terminator)      exec terminator -e "bash -c '$CMD'" ;;
        alacritty)       exec alacritty --class TuxGenie -e bash -c "$CMD" ;;
        kitty)           exec kitty --class TuxGenie bash -c "$CMD" ;;
        wezterm)         exec wezterm start --class TuxGenie --always-new-process bash -c "$CMD" ;;
        foot)            exec foot --app-id=TuxGenie bash -c "$CMD" ;;
        st)              exec st -c TuxGenie -e bash -c "$CMD" ;;
        urxvt)           exec urxvt -name TuxGenie -e bash -c "$CMD" ;;
        xterm)           exec xterm -class TuxGenie -e bash -c "$CMD" ;;
    esac
}
for T in ptyxis gnome-terminal konsole xfce4-terminal mate-terminal lxterminal tilix terminator alacritty kitty wezterm foot st urxvt xterm; do
    command -v "$T" >/dev/null 2>&1 && try_term "$T"
done
command -v xdg-terminal-exec >/dev/null 2>&1 && exec xdg-terminal-exec bash -c "$CMD"
command -v notify-send >/dev/null 2>&1 && notify-send "TuxGenie" "No supported terminal found. Install one with: sudo apt install xterm" --icon=tuxgenie
exit 1
GUISCRIPT
    chmod +x /usr/bin/tuxgenie-gui

    # Make sure the .desktop file exists and points at our robust launcher.
    # It is named after the app-id (com.tuxgenie.TuxGenie) so GNOME links the
    # running window to it and shows the TuxGenie icon instead of a generic gear.
    # Remove the old tuxgenie.desktop from pre-6.27 installs to avoid a duplicate.
    rm -f /usr/share/applications/tuxgenie.desktop 2>/dev/null || true
    cat > /usr/share/applications/com.tuxgenie.TuxGenie.desktop << 'DESKTOPENTRY'
[Desktop Entry]
Version=1.0
Type=Application
Name=TuxGenie
GenericName=AI Linux Assistant
Comment=AI-powered Linux assistant - fix any Linux problem in plain English
Icon=tuxgenie
TryExec=tuxgenie
Exec=/usr/bin/tuxgenie-gui
Terminal=false
Categories=System;Administration;Utility;
Keywords=ai;linux;troubleshoot;claude;terminal;fix;tuxgenie;gui;shell;beginner;
StartupNotify=false
StartupWMClass=com.tuxgenie.TuxGenie
SingleMainWindow=true
DESKTOPENTRY
    chmod 644 /usr/share/applications/com.tuxgenie.TuxGenie.desktop

    # If no real terminal is installed, install xterm so the icon click works
    if ! command -v ptyxis >/dev/null 2>&1 \
       && ! command -v gnome-terminal >/dev/null 2>&1 \
       && ! command -v konsole >/dev/null 2>&1 \
       && ! command -v xfce4-terminal >/dev/null 2>&1 \
       && ! command -v mate-terminal >/dev/null 2>&1 \
       && ! command -v lxterminal >/dev/null 2>&1 \
       && ! command -v xterm >/dev/null 2>&1 \
       && command -v apt-get >/dev/null 2>&1; then
        echo "  Installing xterm so the TuxGenie app icon works..." >&2
        apt-get install -y xterm >/dev/null 2>&1 || true
    fi

    # Register icons with the desktop environment
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
    fi
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database /usr/share/applications 2>/dev/null || true
    fi

    VER=$(dpkg -s tuxgenie 2>/dev/null | awk '/^Version:/{print $2}')
    echo ""
    printf "  \\033[32m\\033[1m TuxGenie v%s installed!\\033[0m  Run: tuxgenie\\n" "$VER"
    echo ""
    echo "  Pick your AI on first run - no credit card needed:"
    echo "    Google Gemini  https://aistudio.google.com/apikey"
    echo "    Groq           https://console.groq.com/keys"
    echo "    Claude         https://console.anthropic.com  (optional, paid)"
    echo "  Common terminal commands work with no key at all."
    echo ""
    ;;
esac
exit 0
"""

PRERM = b"""\
#!/bin/bash
set -e
exit 0
"""

POSTRM = b"""\
#!/bin/bash
set -e
case "$1" in
  remove|purge)
    rm -rf /usr/lib/tuxgenie/__pycache__ 2>/dev/null || true
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
    fi
    ;;
esac
exit 0
"""

# App window: Unified Shell (tuxgenie_shell.py) — modern control deck + live VTE.
# Loaded from disk above as TUXGENIE_APP / TUXGENIE_SHELL. Exit 3 if GTK/VTE
# unavailable so the launcher can fall back to Tk --gui or a plain terminal.

# GUI launcher: Unified Shell first, then Tk --gui, then plain terminal.
LAUNCHER_GUI = b"""\
#!/bin/bash
# TuxGenie GUI launcher - opens tuxgenie as an app-like, single-instance window.
# Note: we intentionally avoid x-terminal-emulator because on Ubuntu 26.04+
# it can resolve to Warp Terminal, which doesn't accept the standard -e flag.

# Unified Shell first (WebKit/GTK + live VTE). Exit 3 = GTK/VTE unavailable
# or spawn failed -> fall through to Tk / plain terminal.
if command -v tuxgenie-app >/dev/null 2>&1; then
    tuxgenie-app
    rc=$?
    [ "$rc" != "3" ] && exit "$rc"
fi

# Phase D: beginner Tk window when python3-tk is installed.
# Exit 2 = Tkinter unavailable -> fall through to plain terminal below.
if command -v tuxgenie >/dev/null 2>&1; then
    tuxgenie --gui
    rc=$?
    [ "$rc" != "2" ] && exit "$rc"
fi

LOCK="${XDG_RUNTIME_DIR:-/tmp}/tuxgenie-$(id -u).lock"

# Single instance: if a TuxGenie session is already open, don't stack a new
# window. Best-effort raise the existing one (X11 only; GNOME/Wayland blocks
# cross-app window activation); otherwise notify and exit.
if command -v flock >/dev/null 2>&1 && ! flock -n "$LOCK" -c true 2>/dev/null; then
    if [ "${XDG_SESSION_TYPE:-}" != "wayland" ]; then
        command -v wmctrl >/dev/null 2>&1 && wmctrl -a "TuxGenie" 2>/dev/null && exit 0
        command -v xdotool >/dev/null 2>&1 && xdotool search --name "^TuxGenie$" windowactivate >/dev/null 2>&1 && exit 0
    fi
    command -v notify-send >/dev/null 2>&1 && notify-send "TuxGenie" "TuxGenie is already open in another window." --icon=tuxgenie
    exit 0
fi

# Inside the terminal: set an app-like window title, then hold the single-instance
# lock for the whole session so repeat clicks are detected above.
CMD='printf "\\033]0;TuxGenie\\007"; exec 9>"'"$LOCK"'" 2>/dev/null; flock -n 9 2>/dev/null || { echo "TuxGenie is already open in another window."; sleep 2; exit 0; }; tuxgenie; echo; read -rp "Press Enter to close..." _'

# Try each known-good terminal in order. Each branch uses the correct CLI
# syntax for that terminal (some need --, others -e, others nothing). Terminals
# that support a custom class/app-id get "TuxGenie" so the window groups under
# the TuxGenie icon; all get a "TuxGenie" title via the escape sequence in CMD.
try_term() {
    case "$1" in
        ptyxis)          exec ptyxis -- bash -c "$CMD" ;;
        gnome-terminal)  exec gnome-terminal -- bash -c "$CMD" ;;
        konsole)         exec konsole --hold -e bash -c "$CMD" ;;
        xfce4-terminal)  exec xfce4-terminal --hold --command="bash -c '$CMD'" ;;
        mate-terminal)   exec mate-terminal -- bash -c "$CMD" ;;
        lxterminal)      exec lxterminal -e bash -c "$CMD" ;;
        tilix)           exec tilix -e bash -c "$CMD" ;;
        terminator)      exec terminator -e "bash -c '$CMD'" ;;
        alacritty)       exec alacritty --class TuxGenie -e bash -c "$CMD" ;;
        kitty)           exec kitty --class TuxGenie bash -c "$CMD" ;;
        wezterm)         exec wezterm start --class TuxGenie --always-new-process bash -c "$CMD" ;;
        foot)            exec foot --app-id=TuxGenie bash -c "$CMD" ;;
        st)              exec st -c TuxGenie -e bash -c "$CMD" ;;
        urxvt)           exec urxvt -name TuxGenie -e bash -c "$CMD" ;;
        xterm)           exec xterm -class TuxGenie -e bash -c "$CMD" ;;
    esac
}

# Try terminals in this order (real, well-known ones first; xterm last as universal fallback)
for T in ptyxis gnome-terminal konsole xfce4-terminal mate-terminal lxterminal tilix terminator alacritty kitty wezterm foot st urxvt xterm; do
    if command -v "$T" >/dev/null 2>&1; then
        try_term "$T"
    fi
done

# Try xdg-terminal-exec last (Ubuntu 24.04+ standard but unreliable on some
# systems where it points to Warp or a misconfigured terminal).
if command -v xdg-terminal-exec >/dev/null 2>&1; then
    exec xdg-terminal-exec bash -c "$CMD"
fi

# Nothing worked. Tell the user via desktop notification.
if command -v notify-send >/dev/null 2>&1; then
    notify-send "TuxGenie" "No supported terminal found. Install one with: sudo apt install xterm  -- then click TuxGenie again." --icon=tuxgenie
fi
exit 1
"""

DESKTOP_ENTRY = b"""\
[Desktop Entry]
Version=1.0
Type=Application
Name=TuxGenie
GenericName=AI Linux Assistant
Comment=AI-powered Linux assistant - fix any Linux problem in plain English
Icon=tuxgenie
TryExec=tuxgenie
Exec=/usr/bin/tuxgenie-gui
Terminal=false
Categories=System;Administration;Utility;
Keywords=ai;linux;troubleshoot;claude;terminal;fix;tuxgenie;gui;shell;beginner;
StartupNotify=false
StartupWMClass=com.tuxgenie.TuxGenie
SingleMainWindow=true
"""

COPYRIGHT = b"""\
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: tuxgenie

Files: *
Copyright: 2025 TuxGenie Project
License: MIT
 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:
 .
 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_tar_gz(entries):
    """
    Build an in-memory .tar.gz.

    entries: list of dicts
      type='dir'  -> directory entry (data=None)
      type='file' -> regular file   (data=bytes)
      keys: path, type, mode (octal int), data
    All entries stamped uid=0 gid=0 root:root mtime=0.
    """
    raw_tar = io.BytesIO()
    with tarfile.open(fileobj=raw_tar, mode="w") as tar:
        for e in entries:
            info          = tarfile.TarInfo(name=e["path"])
            info.uid      = 0
            info.gid      = 0
            info.uname    = "root"
            info.gname    = "root"
            info.mtime    = 0
            info.mode     = e["mode"]
            if e["type"] == "dir":
                info.type = tarfile.DIRTYPE
                info.size = 0
                tar.addfile(info)
            else:
                info.size = len(e["data"])
                tar.addfile(info, io.BytesIO(e["data"]))
    raw_tar.seek(0)

    # Gzip with mtime=0 for reproducibility
    gz_buf = io.BytesIO()
    with gzip.GzipFile(fileobj=gz_buf, mode="wb", mtime=0) as gz:
        gz.write(raw_tar.read())
    return gz_buf.getvalue()


def ar_member(name: str, data: bytes) -> bytes:
    """
    Format one member of an ar archive.
    ar header layout (each field is ASCII, space-padded):
      name   16 bytes
      mtime  12 bytes  (decimal seconds)
      uid     6 bytes  (decimal)
      gid     6 bytes  (decimal)
      mode    8 bytes  (octal)
      size   10 bytes  (decimal)
      magic   2 bytes  0x60 0x0A
    Data follows, padded to even length with 0x0A.
    """
    hdr = (
        name.encode().ljust(16)[:16]        # identifier
        + b"0           "[:12]             # mtime = 0
        + b"0     "                        # uid   = 0
        + b"0     "                        # gid   = 0
        + b"100644  "                      # mode  = 100644 octal
        + str(len(data)).encode().ljust(10)[:10]  # size
        + b"\x60\x0a"                      # magic
    )
    body = data + (b"\n" if len(data) % 2 else b"")
    return hdr + body


def build_deb(control_tgz: bytes, data_tgz: bytes) -> bytes:
    """Assemble the three ar members into a .deb file."""
    out = io.BytesIO()
    out.write(b"!<arch>\n")                            # ar global header
    out.write(ar_member("debian-binary", b"2.0\n"))
    out.write(ar_member("control.tar.gz", control_tgz))
    out.write(ar_member("data.tar.gz",    data_tgz))
    return out.getvalue()


def md5sums_content(file_entries) -> bytes:
    """Generate the DEBIAN/md5sums file from data_entries."""
    lines = []
    for e in file_entries:
        if e["type"] == "file":
            path   = e["path"].lstrip("./")
            digest = hashlib.md5(e["data"]).hexdigest()
            lines.append(f"{digest}  {path}")
    lines.sort()
    return ("\n".join(lines) + "\n").encode()


# ── Define the installed files (data.tar.gz contents) ────────────────────────

data_entries = [
    # directories first
    {"path": "./",                                       "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/",                                   "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/bin/",                               "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/lib/",                               "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/lib/tuxgenie/",                      "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/",                             "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/doc/",                         "type": "dir",  "data": None,          "mode": 0o755},
    {"path": f"./usr/share/doc/{PACKAGE}/",              "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/applications/",                "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/tuxgenie/",                    "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/",                       "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/",               "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/16x16/",         "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/16x16/apps/",    "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/32x32/",         "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/32x32/apps/",    "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/48x48/",         "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/48x48/apps/",    "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/64x64/",         "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/64x64/apps/",    "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/128x128/",       "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/128x128/apps/",  "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/256x256/",       "type": "dir",  "data": None,          "mode": 0o755},
    {"path": "./usr/share/icons/hicolor/256x256/apps/",  "type": "dir",  "data": None,          "mode": 0o755},
    # files
    {"path": "./usr/bin/tuxgenie",
     "type": "file", "data": LAUNCHER,                                   "mode": 0o755},
    {"path": "./usr/bin/tuxgenie-gui",
     "type": "file", "data": LAUNCHER_GUI,                               "mode": 0o755},
    {"path": "./usr/bin/tuxgenie-app",
     "type": "file", "data": TUXGENIE_APP,                               "mode": 0o755},
    {"path": "./usr/bin/tuxgenie-update",
     "type": "file", "data": EMERGENCY_UPDATE,                           "mode": 0o755},
    {"path": "./usr/lib/tuxgenie/tuxgenie.py",
     "type": "file", "data": TUXGENIE_PY,                                "mode": 0o644},
    {"path": "./usr/lib/tuxgenie/tuxgenie_shell.py",
     "type": "file", "data": TUXGENIE_SHELL,                             "mode": 0o644},
    {"path": f"./usr/share/doc/{PACKAGE}/copyright",
     "type": "file", "data": COPYRIGHT,                                  "mode": 0o644},
    # Desktop file named after the app-id so GNOME links the running window
    # (app-id com.tuxgenie.TuxGenie) to it and shows the TuxGenie icon, not a
    # generic gear.
    {"path": "./usr/share/applications/com.tuxgenie.TuxGenie.desktop",
     "type": "file", "data": DESKTOP_ENTRY,                              "mode": 0o644},
    {"path": "./usr/share/tuxgenie/community_fixes.json",
     "type": "file", "data": COMMUNITY_FIXES,                            "mode": 0o644},
    # Icons - hicolor theme, 6 sizes. Installed under BOTH the classic name
    # (tuxgenie, used by notify-send and Icon=) and the app-id name
    # (com.tuxgenie.TuxGenie) so GNOME resolves the window icon either way.
    {"path": "./usr/share/icons/hicolor/16x16/apps/tuxgenie.png",
     "type": "file", "data": ICONS[16],                                  "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/32x32/apps/tuxgenie.png",
     "type": "file", "data": ICONS[32],                                  "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/48x48/apps/tuxgenie.png",
     "type": "file", "data": ICONS[48],                                  "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/64x64/apps/tuxgenie.png",
     "type": "file", "data": ICONS[64],                                  "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/128x128/apps/tuxgenie.png",
     "type": "file", "data": ICONS[128],                                 "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/256x256/apps/tuxgenie.png",
     "type": "file", "data": ICONS[256],                                 "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/16x16/apps/com.tuxgenie.TuxGenie.png",
     "type": "file", "data": ICONS[16],                                  "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/32x32/apps/com.tuxgenie.TuxGenie.png",
     "type": "file", "data": ICONS[32],                                  "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/48x48/apps/com.tuxgenie.TuxGenie.png",
     "type": "file", "data": ICONS[48],                                  "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/64x64/apps/com.tuxgenie.TuxGenie.png",
     "type": "file", "data": ICONS[64],                                  "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/128x128/apps/com.tuxgenie.TuxGenie.png",
     "type": "file", "data": ICONS[128],                                 "mode": 0o644},
    {"path": "./usr/share/icons/hicolor/256x256/apps/com.tuxgenie.TuxGenie.png",
     "type": "file", "data": ICONS[256],                                 "mode": 0o644},
]

# ── Define DEBIAN/ control files ──────────────────────────────────────────────

sums = md5sums_content(data_entries)

control_entries = [
    {"path": "./",           "type": "dir",  "data": None,     "mode": 0o755},
    {"path": "./control",    "type": "file", "data": CONTROL,  "mode": 0o644},
    {"path": "./postinst",   "type": "file", "data": POSTINST, "mode": 0o755},
    {"path": "./prerm",      "type": "file", "data": PRERM,    "mode": 0o755},
    {"path": "./postrm",     "type": "file", "data": POSTRM,   "mode": 0o755},
    {"path": "./md5sums",    "type": "file", "data": sums,     "mode": 0o644},
]

# ── Build ─────────────────────────────────────────────────────────────────────

print(f"  Building {DEB_OUT} ...")

control_tgz = make_tar_gz(control_entries)
data_tgz    = make_tar_gz(data_entries)
deb_bytes   = build_deb(control_tgz, data_tgz)

out_path = os.path.join(SCRIPT_DIR, DEB_OUT)
with open(out_path, "wb") as fh:
    fh.write(deb_bytes)

size_kb = len(deb_bytes) / 1024
print(f"  Done!  {out_path}  ({size_kb:.1f} KB)")

# ── Generate install.sh next to the .deb ──────────────────────────────────────
install_sh_path = os.path.join(SCRIPT_DIR, "install.sh")
install_sh = f"""\
#!/bin/bash
# TuxGenie Installer — double-click this file in your file manager to install.
# Works on Ubuntu, Debian, Linux Mint, and all Debian-based systems.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Auto-detect the .deb file next to this script (works for any version)
DEB=$(ls "$SCRIPT_DIR"/tuxgenie_*_all.deb 2>/dev/null | sort -V | tail -1)
VERSION=$(echo "$DEB" | grep -oP '(?<=tuxgenie_)[\\d.]+(?=_all\\.deb)' 2>/dev/null || echo "{VERSION}")

install_tuxgenie() {{
    echo ""
    echo "  TuxGenie Installer"
    echo "  ─────────────────────────────────────────────"

    if [ -z "$DEB" ] || [ ! -f "$DEB" ]; then
        echo "  ERROR: Cannot find a tuxgenie_*_all.deb file in this folder."
        echo "  Make sure install.sh is in the same folder as the .deb file."
        echo ""
        read -p "  Press Enter to close..."
        exit 1
    fi

    # Check if already installed — show upgrade vs fresh install message
    OLD_VER=$(dpkg -l tuxgenie 2>/dev/null | awk '/^ii/ {{print $3}}')
    if [ -n "$OLD_VER" ]; then
        echo "  Found existing version: $OLD_VER"
        echo "  Upgrading to v$VERSION — your API key and settings will be kept."
    else
        echo "  Fresh install — installing TuxGenie v$VERSION."
    fi
    echo ""
    echo "  You may be asked for your password (this is normal for installing software)."
    echo ""

    if sudo dpkg -i "$DEB"; then
        echo ""
        if [ -n "$OLD_VER" ]; then
            echo "  Upgraded from v$OLD_VER to v$VERSION successfully!"
        else
            echo "  TuxGenie v$VERSION installed successfully!"
        fi
        echo ""
        echo "  How to use:"
        echo "    • Open a Terminal and type:  tuxgenie"
        echo "    • Or find TuxGenie in your app menu / Unified Shell"
        echo ""
    else
        echo ""
        echo "  Installation failed. Trying to fix dependencies..."
        sudo apt-get install -f -y
        echo ""
        read -p "  Press Enter to close..."
        exit 1
    fi

    read -p "  Press Enter to close..."
}}

# Try to open a terminal window for the install - works by double-click.
# Note: we deliberately avoid x-terminal-emulator because on Ubuntu 26.04+
# it can resolve to Warp Terminal which doesn't accept the standard -e flag.
if [ -t 1 ]; then
    # Already running in a terminal
    install_tuxgenie
else
    # Launched from file manager - open a terminal window with the right syntax per terminal
    SELF="$(realpath "$0")"
    for term in ptyxis gnome-terminal konsole xfce4-terminal mate-terminal lxterminal tilix alacritty kitty foot xterm; do
        if command -v "$term" >/dev/null 2>&1; then
            case "$term" in
                ptyxis|gnome-terminal|mate-terminal) "$term" -- bash "$SELF" --in-terminal ;;
                konsole)                              konsole --hold -e bash "$SELF" --in-terminal ;;
                xfce4-terminal)                       xfce4-terminal --hold --command="bash '$SELF' --in-terminal" ;;
                kitty)                                kitty bash "$SELF" --in-terminal ;;
                foot|alacritty|tilix|lxterminal|xterm) "$term" -e bash "$SELF" --in-terminal ;;
            esac
            exit 0
        fi
    done
    # Fallback: no terminal found, try running directly with pkexec for GUI password prompt
    sudo dpkg -i "$DEB" && zenity --info --text="TuxGenie v$VERSION installed!\\nOpen a terminal and type: tuxgenie" 2>/dev/null
fi
"""

with open(install_sh_path, "w") as fh:
    fh.write(install_sh)
os.chmod(install_sh_path, 0o755)
print(f"  Done!  {install_sh_path}")
print()
print("  -- Share these two files together --")
print(f"  {DEB_OUT}")
print(f"  install.sh")
print()
print("  Users can double-click install.sh to install TuxGenie.")
print()
print("  -- Or install via terminal --")
print(f"  sudo dpkg -i {DEB_OUT}")
print()
print("  -- Run --")
print(f"  tuxgenie")
print()
print("  -- Remove --")
print(f"  sudo dpkg -r {PACKAGE}")
print()
