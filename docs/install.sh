#!/usr/bin/env bash
# TuxGenie universal installer — https://tuxgenie.com
# Works on Ubuntu, Debian, Mint, Fedora, Arch, openSUSE, Alpine, and more.
# Usage:  curl -fsSL https://tuxgenie.com/install.sh | bash
set -euo pipefail

REPO="ramchandragada/tuxgenie"
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
BOLD='\033[1m'; DIM='\033[2m'; R='\033[0m'

echo -e "\n${CYAN}${BOLD}🐧 TuxGenie Installer${R}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${R}\n"

detect_pm() {
    for pm in apt-get dnf yum pacman zypper apk; do
        if command -v "$pm" >/dev/null 2>&1; then
            echo "$pm"
            return
        fi
    done
    echo "unknown"
}

PM="$(detect_pm)"
echo -e "${DIM}Detected package manager: ${BOLD}${PM}${R}\n"

ensure_pkg() {
    # ensure_pkg <pkg...>  — best-effort install via the distro package manager
    local pkgs=("$@")
    case "$PM" in
        apt-get) sudo apt-get update -q && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q "${pkgs[@]}" ;;
        dnf)     sudo dnf install -y "${pkgs[@]}" ;;
        yum)     sudo yum install -y "${pkgs[@]}" ;;
        pacman)  sudo pacman -Sy --noconfirm "${pkgs[@]}" ;;
        zypper)  sudo zypper --non-interactive install "${pkgs[@]}" ;;
        apk)     sudo apk add "${pkgs[@]}" ;;
        *)       return 1 ;;
    esac
}

# curl is required to talk to GitHub
if ! command -v curl >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ curl not found. Installing…${R}"
    ensure_pkg curl || {
        echo -e "${RED}✘ Could not install curl. Install it manually and re-run.${R}\n"
        exit 1
    }
fi

# Python 3 is required for pip installs (and the app itself)
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ python3 not found. Installing…${R}"
    case "$PM" in
        apt-get) ensure_pkg python3 python3-pip python3-venv ;;
        dnf|yum) ensure_pkg python3 python3-pip ;;
        pacman)  ensure_pkg python python-pip ;;
        zypper)  ensure_pkg python3 python3-pip ;;
        apk)     ensure_pkg python3 py3-pip ;;
        *)       echo -e "${RED}✘ Install Python 3.8+ and re-run.${R}\n"; exit 1 ;;
    esac
fi

echo -e "${CYAN}→ Fetching latest version…${R}"
RELEASE=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null || true)
VERSION=$(echo "$RELEASE" | grep -oE '"tag_name":\s*"v[^"]+"' | head -1 | cut -d'"' -f4)
DEB_URL=$(echo "$RELEASE" | grep -oE "https://[^\"]+_all\\.deb" | head -1 || true)
WHL_URL=$(echo "$RELEASE" | grep -oE "https://[^\"]+-py3-none-any\\.whl" | head -1 || true)

if [ -z "$VERSION" ]; then
    echo -e "${YELLOW}⚠ GitHub API unavailable — falling back to PyPI.${R}"
    VERSION="latest"
else
    echo -e "${GREEN}✔ Latest: ${BOLD}${VERSION}${R}\n"
fi

finish_ok() {
    echo -e "\n${GREEN}${BOLD}✔ TuxGenie ${VERSION} installed!${R}"
    echo -e "\n  Run with:  ${CYAN}${BOLD}tuxgenie${R}"
    echo -e "\n  On first run, pick a free AI key (no credit card):"
    echo -e "    Google Gemini  https://aistudio.google.com/apikey"
    echo -e "    Groq           https://console.groq.com/keys"
    echo -e "    Claude         https://console.anthropic.com  (optional)"
    echo -e "  Terminal commands work with no key at all.\n"
}

# ── Path 1: Debian-family → .deb ─────────────────────────────────────────────
if command -v dpkg >/dev/null 2>&1 && [ -n "${DEB_URL:-}" ]; then
    echo -e "${CYAN}→ Installing via .deb (Debian / Ubuntu / Mint)…${R}"
    TMP=$(mktemp /tmp/tuxgenie_XXXXXX.deb)
    if curl -fsSL "$DEB_URL" -o "$TMP"; then
        if sudo dpkg -i "$TMP"; then
            rm -f "$TMP"
            finish_ok
            exit 0
        fi
        echo -e "${YELLOW}→ Fixing dependencies…${R}"
        sudo apt-get install -f -y || true
        if dpkg -l tuxgenie 2>/dev/null | grep -q '^ii'; then
            rm -f "$TMP"
            finish_ok
            exit 0
        fi
    fi
    rm -f "$TMP"
    echo -e "${YELLOW}⚠ .deb install failed — trying pip…${R}"
fi

# ── Path 2: pip (wheel from GitHub release, then PyPI) ───────────────────────
echo -e "${CYAN}→ Installing via pip (works on every distro)…${R}"

# Ensure pip module
if ! python3 -m pip --version >/dev/null 2>&1; then
    echo -e "${YELLOW}→ Installing pip…${R}"
    case "$PM" in
        apt-get) ensure_pkg python3-pip || true ;;
        dnf|yum) ensure_pkg python3-pip || true ;;
        pacman)  ensure_pkg python-pip || true ;;
        zypper)  ensure_pkg python3-pip || true ;;
        apk)     ensure_pkg py3-pip || true ;;
    esac
    python3 -m ensurepip --upgrade 2>/dev/null || true
fi

PIP_FLAGS=(--upgrade)
# Prefer user install when not root; allow break-system-packages on PEP 668 distros.
if [ "$(id -u)" -ne 0 ]; then
    PIP_FLAGS+=(--user)
fi

install_with_pip() {
    local target="$1"
    python3 -m pip install "${PIP_FLAGS[@]}" "$target" 2>/dev/null \
        || python3 -m pip install "${PIP_FLAGS[@]}" --break-system-packages "$target" 2>/dev/null \
        || pip3 install --upgrade "$target" --break-system-packages 2>/dev/null \
        || pip3 install --upgrade "$target"
}

RC=1
if [ -n "${WHL_URL:-}" ]; then
    echo -e "${DIM}  Using release wheel…${R}"
    WHL=$(mktemp /tmp/tuxgenie_XXXXXX.whl)
    if curl -fsSL "$WHL_URL" -o "$WHL"; then
        if install_with_pip "$WHL"; then RC=0; fi
    fi
    rm -f "$WHL"
fi

if [ "$RC" -ne 0 ]; then
    echo -e "${DIM}  Using PyPI…${R}"
    if [ "$VERSION" != "latest" ]; then
        VER_NUM="${VERSION#v}"
        install_with_pip "tuxgenie==${VER_NUM}" && RC=0 || true
    fi
    if [ "$RC" -ne 0 ]; then
        install_with_pip "tuxgenie" && RC=0 || true
    fi
fi

if [ "$RC" -ne 0 ]; then
    echo -e "${RED}✘ Install failed.${R}"
    echo -e "  Try manually:"
    echo -e "    python3 -m pip install --user --upgrade tuxgenie"
    echo -e "  Or download a release: https://github.com/${REPO}/releases/latest\n"
    exit 1
fi

# Ensure ~/.local/bin is on PATH hint for --user installs
if [ "$(id -u)" -ne 0 ] && [ -x "${HOME}/.local/bin/tuxgenie" ]; then
    case ":$PATH:" in
        *":${HOME}/.local/bin:"*) ;;
        *)
            echo -e "${YELLOW}⚠ Add this to your shell profile so 'tuxgenie' is found:${R}"
            echo -e "    export PATH=\"\$HOME/.local/bin:\$PATH\""
            ;;
    esac
fi

finish_ok
exit 0
