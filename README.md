# TuxGenie 🧞

> **Your wish is my command.** AI-powered Linux assistant — fix any problem in plain English.

[![PyPI version](https://img.shields.io/pypi/v/tuxgenie)](https://pypi.org/project/tuxgenie/)
[![Python](https://img.shields.io/pypi/pyversions/tuxgenie)](https://pypi.org/project/tuxgenie/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/ramchandragada/tuxgenie/actions/workflows/ci.yml/badge.svg)](https://github.com/ramchandragada/tuxgenie/actions)

---

```
 ████████╗██╗   ██╗██╗  ██╗ ██████╗ ███████╗███╗   ██╗██╗███████╗
    ██╔══╝██║   ██║╚██╗██╔╝██╔════╝ ██╔════╝████╗  ██║██║██╔════╝
    ██║   ██║   ██║ ╚███╔╝ ██║  ███╗█████╗  ██╔██╗ ██║██║█████╗
    ██║   ██║   ██║ ██╔██╗ ██║   ██║██╔══╝  ██║╚██╗██║██║██╔══╝
    ██║   ╚██████╔╝██╔╝ ██╗╚██████╔╝███████╗██║ ╚████║██║███████╗
    ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚══════╝

  TuxGenie v5.79 — Powered by Claude · Free forever · Open Source
```

---

## What is TuxGenie?

TuxGenie is your AI co-pilot for Linux. Describe any problem in plain English and TuxGenie will diagnose it, explain what's wrong, and fix it — step by step, with your approval at every stage.

No more Googling error messages. No more copying random commands from Stack Overflow. Just tell TuxGenie what's wrong.

```
$ tuxgenie
TuxGenie > my nginx won't start after I edited the config

  ✦ Step 1 [SAFE]  Check nginx config for syntax errors
    nginx -t
  Run this step? [y/n/skip/abort]: y

  nginx: [emerg] unexpected "}" in /etc/nginx/nginx.conf:42
  nginx: configuration file /etc/nginx/nginx.conf test failed

  ✦ Step 2 [SAFE]  Show the problem line in context
    sed -n '38,46p' /etc/nginx/nginx.conf
  Run this step? [y/n/skip/abort]: y

  ✦ Step 3 [MODERATE]  Fix the missing semicolon on line 41
    ...
```

---

## Install

### Debian / Ubuntu / Linux Mint
```bash
# Download the latest .deb from GitHub Releases, then:
sudo dpkg -i tuxgenie_5.79.0_all.deb
```
[Download latest .deb →](https://github.com/ramchandragada/tuxgenie/releases/latest)

### Any Linux distro (pip)
```bash
pip install tuxgenie
```

### From source
```bash
git clone https://github.com/ramchandragada/tuxgenie.git
cd tuxgenie
pip install .
```

---

## First run

```bash
# Set your Anthropic API key (add to ~/.bashrc to make permanent)
export ANTHROPIC_API_KEY="sk-ant-..."

# Launch
tuxgenie
```

Get a free API key at [console.anthropic.com](https://console.anthropic.com).

---

## Features

You never *have* to pick a number — just type what you need in plain English. But every capability also has a menu entry:

**🚀 Start here**

| # | Feature | What it does |
|---|---------|--------------|
| 1 | **Fix a Problem** | Describe any issue in plain English — TuxGenie diagnoses and fixes it |
| 2 | **Health Check** | Full dashboard: CPU, memory, disk, temps, failed services |

**🔧 Fix something**

| # | Feature | What it does |
|---|---------|--------------|
| 3 | **Internet / WiFi** | DNS, routing, firewall, connectivity — finds the real problem |
| 4 | **Sound / Audio** | No audio, mic not working, HDMI sound |
| 5 | **Display** | Wrong resolution, monitor not detected |
| 6 | **Bluetooth** | Pairing fails, device keeps disconnecting |
| 7 | **Printer Setup** | Install a printer or fix printing problems |
| 8 | **Webcam Fix** | Camera not detected or black screen in Zoom / Teams / Meet |
| 9 | **Missing Drivers** | Detect & install missing WiFi / GPU / printer drivers |
| 10 | **Permissions** | Diagnose & fix "permission denied" errors |

**📦 Install & update**

| # | Feature | What it does |
|---|---------|--------------|
| 11 | **Install Software** | Find & install software by description |
| 12 | **Check for Updates** | Safe upgrade analysis — flags packages likely to break things |
| 13 | **Upgrade OS Version** | Move to the latest Ubuntu / Fedora / Debian release |
| 14 | **Find Linux App** | Find Linux equivalents of Windows / macOS apps |

**🛡️ Protect & recover**

| # | Feature | What it does |
|---|---------|--------------|
| 15 | **Security Check** | Harden firewall, SSH, open ports; find weak permissions |
| 16 | **Backup Settings** | Snapshot all system configs to a `.tar.gz` before changes |
| 17 | **Undo Changes** | Roll back changes TuxGenie made in a previous session |

**⚡ Speed & maintenance**

| # | Feature | What it does |
|---|---------|--------------|
| 18 | **Performance Boost** | Full audit + apply all safe speed fixes |
| 19 | **Disk Cleanup** | Find space hogs & clean up safely |
| 20 | **Speed Up Boot** | Find why boot is slow & fix it |
| 21 | **Battery & Power** | Improve battery life, fix overheating |
| 22 | **Manage Services** | Optimise startup & debug systemd services |

**📊 Inspect**

| # | Feature | What it does |
|---|---------|--------------|
| 23 | **Hardware Info** | Full hardware report & health check |
| 24 | **Running Programs** | Tame CPU / memory hogs & zombie processes |
| 25 | **Explain Logs** | Decode cryptic errors & system logs in plain English |

**⚙️ For developers**

| # | Feature | What it does |
|---|---------|--------------|
| 26 | **Generate Script** | Describe a task → get a tested bash script |
| 27 | **Schedule Task** | Create & debug cron jobs in plain English |
| 28 | **Docker Help** | Container health, network issues, log analysis |
| 29 | **SSH Setup** | Set up & harden SSH securely |
| 30 | **Git Helper** | Understand diffs, fix conflicts, undo commits |

**🎁 One-tap catalogs**

| # | Feature | What it does |
|---|---------|--------------|
| 77 | **Install Apps** | One-tap catalog of 64 popular Linux apps — Brave, Signal, Obsidian, Blender, Zoho Mail … |
| 88 | **Cloud Sync** | Guided rclone wrapper — Google Drive, Dropbox, OneDrive, S3, WebDAV from a single menu |
| 99 | **AI Tools** | One-tap installer for Ollama, Claude Code, ChatGPT, Whisper and a local-AI starter pack |

**Letter shortcuts**

| Key | Feature | What it does |
|-----|---------|--------------|
| s | **Settings** | Configure API key and model |
| i | **Shell Integration** | Install the `tg!!` shortcut in your terminal |
| m | **Error Monitor** | Background daemon that notifies you on system errors |
| u | **Self-Update** | Check for and install the latest TuxGenie |
| h | **History** | Show recent tasks |
| f | **Feature Request** | Suggest a new feature |

---

## Safety first

TuxGenie **never runs a command without your explicit approval.**

Every step shows:
- **Risk level** — `SAFE`, `MODERATE`, or `DANGEROUS` (colour-coded)
- **[SUDO NEEDED]** badge when root is required
- A red warning banner for destructive commands
- Prompt: `[y / n / skip / abort]` — you are always in control

Commands matching dangerous patterns (`rm -rf /`, `dd if=`, `mkfs`, `fdisk`, `wipefs`, `shred`, `chmod 777 /`, fork bombs) are flagged **regardless** of what the AI says about them.

---

## Requirements

- Python 3.8+
- An Anthropic API key ([get one free](https://console.anthropic.com))
- Linux

The `anthropic` Python package is installed automatically on first run if missing.

---

## How it works

```
You describe the problem
        │
        ▼
  System context collected silently (OS, kernel, services, logs…)
        │
        ▼
  Claude API → structured fix plan with risk levels
        │
        ▼
  Each step shown with risk badge — you approve or skip
        │
        ▼
  Command output fed back to Claude
        │
        ▼
  Claude iterates (up to 25 rounds) until resolved
```

---

## One-shot mode

```bash
# Skip the menu — go straight to fixing
tuxgenie "docker containers can't reach the internet"
tuxgenie "my SSH connection keeps dropping"
tuxgenie "cron job not running"
```

---

## Dedicated to Linus Torvalds

TuxGenie is dedicated to Linus Torvalds — creator of the Linux kernel, the greatest gift ever given to computing. His work powers servers, supercomputers, smartphones, satellites, and the entire modern internet.

---

## License

MIT — free to use, modify, and share forever.

Built with love by [Aspera Technologies Pte Ltd](https://github.com/ramchandragada/tuxgenie).
