#!/usr/bin/env bash
# TuxGenie Installer — https://tuxgenie.com
set -euo pipefail

REPO="ramchandragada/tuxgenie"
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BOLD='\033[1m'; R='\033[0m'

echo -e "\n${CYAN}${BOLD}🐧 TuxGenie Installer${R}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${R}\n"

# Check for curl, install if missing
if ! command -v curl &>/dev/null; then
    echo -e "${YELLOW}⚠ curl not found. Installing...${R}"
    sudo apt-get install -y curl 2>/dev/null || sudo dnf install -y curl 2>/dev/null || sudo pacman -Sy --noconfirm curl 2>/dev/null || true
fi

# Fetch latest release
echo -e "${CYAN}→ Fetching latest version...${R}"
RELEASE=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null)
VERSION=$(echo "$RELEASE" | grep '"tag_name"' | head -1 | cut -d'"' -f4)
DEB_URL=$(echo "$RELEASE" | grep 'browser_download_url.*\.deb' | head -1 | cut -d'"' -f4)

if [ -z "$VERSION" ]; then
    echo -e "${RED}✘ Could not reach GitHub. Check your internet connection.${R}\n"; exit 1
fi
echo -e "${GREEN}✔ Latest: ${BOLD}$VERSION${R}\n"

# Debian/Ubuntu: use .deb
if command -v dpkg &>/dev/null && [ -n "$DEB_URL" ]; then
    echo -e "${CYAN}→ Downloading .deb package...${R}"
    TMP=$(mktemp /tmp/tuxgenie_XXXXXX.deb)
    curl -fsSL "$DEB_URL" -o "$TMP"
    echo -e "${CYAN}→ Installing (needs sudo)...${R}"
    sudo dpkg -i "$TMP" || { echo -e "${YELLOW}→ Fixing dependencies...${R}"; sudo apt-get install -f -y; }
    rm -f "$TMP"
    echo -e "\n${GREEN}${BOLD}✔ TuxGenie $VERSION installed!${R}"
    echo -e "\n  Run with: ${CYAN}${BOLD}tuxgenie${R}\n"
    exit 0
fi

# Fallback: pip
echo -e "${YELLOW}→ No dpkg found — installing via pip...${R}"
if command -v pip3 &>/dev/null; then
    pip3 install tuxgenie --break-system-packages 2>/dev/null || pip3 install tuxgenie
elif command -v pip &>/dev/null; then
    pip install tuxgenie --break-system-packages 2>/dev/null || pip install tuxgenie
else
    echo -e "${RED}✘ pip not found. Install Python pip first:${R}"
    echo -e "  sudo apt-get install python3-pip\n"; exit 1
fi

echo -e "\n${GREEN}${BOLD}✔ TuxGenie $VERSION installed!${R}"
echo -e "\n  Run with: ${CYAN}${BOLD}tuxgenie${R}\n"
