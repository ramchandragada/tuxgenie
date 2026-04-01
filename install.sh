#!/bin/bash
# TuxGenie Installer — double-click this file in your file manager to install.
# Works on Ubuntu, Debian, Linux Mint, and all Debian-based systems.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEB="$SCRIPT_DIR/tuxgenie_3.8.0_all.deb"

install_tuxgenie() {
    echo ""
    echo "  🧞 TuxGenie Installer"
    echo "  ─────────────────────────────────────────────"

    if [ ! -f "$DEB" ]; then
        echo "  ✗ ERROR: Cannot find $DEB"
        echo "  Make sure install.sh is in the same folder as the .deb file."
        echo ""
        read -p "  Press Enter to close..."
        exit 1
    fi

    # Check if already installed — show upgrade vs fresh install message
    OLD_VER=$(dpkg -l tuxgenie 2>/dev/null | awk '/^ii/ {print $3}')
    if [ -n "$OLD_VER" ]; then
        echo "  Found existing version: $OLD_VER"
        echo "  Upgrading to v3.8.0 — your API key and settings will be kept."
    else
        echo "  Fresh install — installing TuxGenie v3.8.0."
    fi
    echo ""
    echo "  You may be asked for your password (this is normal for installing software)."
    echo ""

    if sudo dpkg -i "$DEB"; then
        echo ""
        if [ -n "$OLD_VER" ]; then
            echo "  ✓ Upgraded from v$OLD_VER  →  v3.8.0 successfully!"
        else
            echo "  ✓ TuxGenie v3.8.0 installed successfully!"
        fi
        echo ""
        echo "  How to use:"
        echo "    • Open a Terminal and type:  tuxgenie"
        echo "    • Or find TuxGenie in your app menu"
        echo ""
    else
        echo ""
        echo "  ✗ Installation failed. Trying to fix dependencies..."
        sudo apt-get install -f -y
        echo ""
        read -p "  Press Enter to close..."
        exit 1
    fi

    read -p "  Press Enter to close..."
}

# Try to open a terminal window for the install — works by double-click
if [ -t 1 ]; then
    # Already running in a terminal
    install_tuxgenie
else
    # Launched from file manager — open a terminal window
    SELF="$(realpath "$0")"
    for term in gnome-terminal x-terminal-emulator xterm konsole xfce4-terminal mate-terminal lxterminal; do
        if command -v "$term" &>/dev/null; then
            case "$term" in
                gnome-terminal) gnome-terminal -- bash "$SELF" --in-terminal ;;
                *)              "$term" -e "bash '$SELF' --in-terminal" ;;
            esac
            exit 0
        fi
    done
    # Fallback: no terminal found, try running directly with pkexec for GUI password prompt
    sudo dpkg -i "$DEB" && zenity --info --text="TuxGenie v3.8.0 installed!\nOpen a terminal and type: tuxgenie" 2>/dev/null
fi
