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

  TuxGenie v3.9 — Powered by Claude · Free forever · Open Source
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
sudo dpkg -i tuxgenie_3.9.0_all.deb
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

| # | Feature | What it does |
|---|---------|--------------|
| 1 | **Fix my problem** | Describe any issue in plain English — TuxGenie diagnoses and fixes it |
| 2 | **System Health** | Full health dashboard: CPU, memory, disk, temps, failed services |
| 3 | **Network Diagnostics** | DNS, routing, firewall, connectivity — finds the real problem |
| 4 | **Security Audit** | Checks open ports, failed logins, weak permissions, exposed configs |
| 5 | **Disk Management** | Finds space hogs, cleans safely, analyses usage |
| 6 | **Service Control** | Manage and debug systemd services with AI explanations |
| 7 | **Log Analyser** | Parses journals and log files, explains errors in plain English |
| 8 | **Update Advisor** | Safe upgrade analysis — flags packages likely to break things |
| 9 | **Script Generator** | Describe what you want, get a tested bash script |
| 10 | **Cron Scheduler** | Create and debug cron jobs with natural language |
| 11 | **Permission Fixer** | Diagnoses and fixes broken file permissions |
| 12 | **Boot Repair** | Diagnoses boot failures, GRUB issues, kernel panics |
| 13 | **Docker Manager** | Container health, network issues, log analysis |
| 14 | **SSH Diagnostics** | Key auth, config issues, connectivity debugging |
| 15 | **Process Manager** | Find CPU/memory hogs, diagnose runaway processes |
| 16 | **Config Backup** | Safe backup of system configs before changes |
| u | **Self-Update** | Type `u` to check for and install the latest TuxGenie |

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
  Claude iterates (up to 6 rounds) until resolved
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
