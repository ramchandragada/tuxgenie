#!/bin/bash
# TuxGenie Installer — double-click this file in your file manager to install.
# Works on Ubuntu, Debian, Linux Mint, and all Debian-based systems.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Auto-detect the .deb file next to this script (works for any version)
DEB=$(ls "$SCRIPT_DIR"/tuxgenie_*_all.deb 2>/dev/null | sort -V | tail -1)
VERSION=$(echo "$DEB" | grep -oP '(?<=tuxgenie_)[\d.]+(?=_all\.deb)' 2>/dev/null || echo "6.83.0")

install_tuxgenie() {
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
    OLD_VER=$(dpkg -l tuxgenie 2>/dev/null | awk '/^ii/ {print $3}')
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
}

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
    sudo dpkg -i "$DEB" && zenity --info --text="TuxGenie v$VERSION installed!\nOpen a terminal and type: tuxgenie" 2>/dev/null
fi
