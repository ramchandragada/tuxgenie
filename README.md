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

  TuxGenie — Claude or Gemini · Free forever · Open Source
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

### Which distros are supported?

TuxGenie is built for **every** Linux user. The AI assistant detects your
package manager (apt, dnf, pacman, zypper, apk, …) and adapts its commands, and
`u` self-update works on both `.deb` and pip installs — so the **core assistant
works on any Linux distro**.

| | Debian family (Ubuntu, Mint, Pop!_OS, Debian, Zorin, elementary, Kali…) | Other distros (Fedora, Arch, openSUSE, …) |
|---|:---:|:---:|
| AI fix / diagnose / install, system updates | ✅ | ✅ |
| `.deb` install + app-menu icon + windowed app | ✅ | — (install via `pip`, runs in your terminal) |
| App catalog | ✅ full | ✅ Flatpak entries (auto-adapted for your package manager) |

On non-Debian systems, install with `pip install tuxgenie` and run `tuxgenie`.

---

## First run

On first launch TuxGenie asks which AI you'd like to use (Gemini is the default —
just press Enter):

- **Google Gemini** — **free tier, no credit card** *(recommended)*.
  Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
- **Groq** — **also free, very fast** (Llama models).
  Get a free key at [console.groq.com/keys](https://console.groq.com/keys).
- **SambaNova** — **also free, no credit card** (Llama models).
  Get a free key at [cloud.sambanova.ai/apis](https://cloud.sambanova.ai/apis).
- **OpenRouter** — **also free, no credit card** (one key, many models).
  Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys).
- **Claude (Anthropic)** — best quality. Free trial credit, then ~$0.01/session.
  Get a key at [console.anthropic.com](https://console.anthropic.com).

You can also set a key via environment variable and skip the prompt:

```bash
export GEMINI_API_KEY="..."             # Google Gemini (free tier)
# or
export GROQ_API_KEY="gsk_..."           # Groq (free tier)
# or
export SAMBANOVA_API_KEY="..."          # SambaNova (free tier)
# or
export OPENROUTER_API_KEY="sk-or-..."   # OpenRouter (free tier)
# or
export ANTHROPIC_API_KEY="sk-ant-..."   # Claude

tuxgenie
```

Switch providers anytime from **Settings → Switch AI provider**. Terminal
commands (apt, systemctl, …) run without any key — always free.

**Auto-switch on limits:** if you add keys for more than one free provider
(Gemini, Groq, SambaNova, OpenRouter), TuxGenie automatically rotates between them when a
free tier hits its rate limit — so a task never stalls. It never auto-switches to
paid Claude (no surprise charges). Toggle it in
**Settings → Auto-switch on limits**.

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

**🧭 Guided setups** — get your PC ready for how you actually use it

> **Not sure which one?** Type **`suggest`** (or `39`) — answer one plain-English
> question and TuxGenie takes you straight into the right setup.

| # | Feature | What it does |
|---|---------|--------------|
| 31 | **Gaming Setup** | Steam + Proton, GPU drivers, GameMode/MangoHud, controllers — get game-ready |
| 32 | **New to Linux** | Just switched from Windows/Mac? Guided first-day setup: apps, media codecs, drivers, updates |
| 33 | **Developer Setup** | Pick a stack → toolchains, VS Code, git identity, SSH keys, Docker, shell |
| 34 | **Creator / Streaming** | OBS, video/audio editors, virtual camera, PipeWire audio routing, hardware encoding |
| 35 | **Privacy & Security** | Password manager, Signal, Tor, VPN, guided firewall, encrypted DNS, encryption check |
| 36 | **Student Setup** | Free study tools: notes (Obsidian/Xournal++), citations (Zotero), flashcards (Anki), office, optional LaTeX |
| 37 | **Homelab Setup** | Self-hosting stack: Docker + Portainer, Tailscale, Syncthing, Samba/NFS, monitoring, scheduled backups |
| 38 | **Accessibility** | Screen reader (Orca), magnifier, on-screen keyboard, high contrast, larger text — guided per desktop |
| 39 | **Suggest a Setup** | Not sure? Answer one plain-English question → TuxGenie opens the right setup for you |
| 40 | **Dev Environments** | Ready-to-run stacks — LAMP/LEMP, Node.js, Python/Django, Rails, databases, local WordPress — installed, secured & verified, on your PC or in containers. Or just *describe* what you need (e.g. "run Magento"). |

**🎁 One-tap catalogs**

| # | Feature | What it does |
|---|---------|--------------|
| 77 | **Install Apps** | One-tap catalog of **111 popular Linux apps** — browsers, messaging, office, media, graphics, dev tools, gaming, security … (Brave, Signal, Obsidian, Blender, Bitwarden, Steam, Zoho Mail …) |
| 88 | **Cloud Sync** | Guided rclone wrapper — Google Drive, Dropbox, OneDrive, S3, WebDAV from a single menu |
| 99 | **AI Tools** | One-tap installer for **22 AI tools** — Cursor, Windsurf, Zed, Ollama, Claude Code, GitHub Copilot CLI, Gemini CLI, GPT4All, Whisper, a local-AI starter pack … |

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

TuxGenie **never changes your system without your OK.**

- **Read-only steps run automatically.** Diagnostics that only *look* at your
  system (`systemctl status`, `journalctl`, `ls`, `df`, `ip addr`, …) run
  without interrupting you, so troubleshooting stays fast.
- **Anything that changes your system asks first.** Installs, service
  restarts, config edits, package removals — each is shown with its command
  and risk level, then prompts:
  `[y = yes · n = skip · a = abort · A = yes to all]`. You're always in control.
- Every step shows a **risk badge** (`SAFE` / `MODERATE` / `DANGEROUS`), a
  **[SUDO NEEDED]** badge when root is required, and a red banner for
  destructive commands.

**Dangerous commands are hard-blocked** regardless of what the AI says — and the
filter reasons about the *actual command*, not just text patterns, so
reorderings and disguises are caught too:

- `rm -rf /`, `rm -rf /*`, `rm -Rf /`, `rm --recursive --force /`, and recursive
  deletes of any system directory (`/etc`, `/usr`, `/boot`, `/var`, …)
- `dd` writing to a raw disk (`of=/dev/sda`), `mkfs`, `fdisk`, `wipefs`, `shred`
- `chmod`/`chown` on `/` or system dirs, `find / -delete`, `tee` to a device
- fork bombs, `sudo` shells, `--no-preserve-root`

Ordinary work under your home directory (`rm -rf ~/project/node_modules`, writing
a disk image to a file, `chmod -R` on your own app) is **not** blocked.

> **Power users:** prefer the old fully-autonomous flow? Turn on
> **Settings → Auto-approve** to run AI commands without the per-step prompt
> (genuinely dangerous commands are still blocked).

### Safe updates

When you update with `u`, the downloaded `.deb` is checked for completeness and
verified against the release's published **SHA-256 digest** before installation —
a corrupted or tampered download is refused, never installed.

---

## Requirements

- Python 3.8+
- Linux
- An AI key — a **free** one from **Google Gemini** ([get it](https://aistudio.google.com/apikey)),
  **Groq** ([get it](https://console.groq.com/keys)), **SambaNova** ([get it](https://cloud.sambanova.ai/apis))
  or **OpenRouter** ([get it](https://openrouter.ai/keys)),
  or **Anthropic Claude** ([get one](https://console.anthropic.com)) for best quality. Terminal commands
  (apt, systemctl, …) run with no key at all.

The `anthropic` Python package is installed automatically on first run if missing
(only needed for Claude; the Gemini backend uses the standard library).

## Privacy & transparency

TuxGenie has **no backend, no telemetry, no analytics, and no accounts** —
nothing is sent anywhere unless you run an AI task, and then only to the
provider you chose. Your API key is stored locally (`chmod 600`) and your sudo
password is never saved or sent. Full, plain-English details in
**[PRIVACY.md](PRIVACY.md)**.

---

## How it works

```
You describe the problem
        │
        ▼
  System context collected silently (OS, kernel, services, logs…)
        │
        ▼
  AI provider (Claude or Gemini) → structured fix plan with risk levels
        │
        ▼
  Each step shown with risk badge — you approve or skip
        │
        ▼
  Command output fed back to the AI
        │
        ▼
  The AI iterates (up to 25 rounds) until resolved
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
