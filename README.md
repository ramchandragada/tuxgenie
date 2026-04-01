# AI Terminal

An intelligent Linux troubleshooter that accepts natural language problem descriptions and fixes them automatically using the Anthropic Claude API.

## What it does

Describe your Linux problem in plain English. AI Terminal will:

1. Collect system context (OS, kernel, user, desktop, uptime) silently at startup
2. Send the issue + system info to Claude via the Anthropic API
3. Receive a structured fix plan with step-by-step commands
4. Show each step with its risk level before running it
5. Ask for confirmation before executing anything
6. Feed command outputs back to Claude and iterate until resolved (up to 6 rounds)

## Quick Start

**1. Install**

```bash
git clone <repo>
cd ai-terminal
bash install.sh
```

**2. Set your API key**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Get your key at [console.anthropic.com](https://console.anthropic.com).

**3. Run**

```bash
aifix
```

Or without installing:

```bash
ANTHROPIC_API_KEY=sk-ant-... python3 ai_terminal.py
```

## Example issues you can describe

- `nginx won't start after I changed the config`
- `my disk is almost full, help me find what's taking space`
- `SSH connections keep timing out`
- `a process is eating 100% CPU, I don't know which one`
- `my cron job isn't running`
- `docker containers can't reach the internet`
- `I accidentally changed file permissions, nothing works`

## Safety

AI Terminal never runs a command without your explicit approval. For each step you see:

- **Risk level** — `SAFE`, `MODERATE`, or `DANGEROUS` (colour-coded)
- **[SUDO NEEDED]** badge when root is required
- A red warning banner for destructive commands
- A prompt: `[y/n/skip/abort]` — you decide what runs

Commands matching dangerous patterns (`rm -rf /`, `dd if=`, `mkfs`, `fdisk`, `wipefs`, `shred`, `chmod 777 /`, fork bombs) are flagged regardless of what Claude labels them.

## How it works

```
User describes issue
       │
       ▼
  System context collected (OS, kernel, user, uptime…)
       │
       ▼
  Claude API → structured JSON fix plan
       │
       ▼
  Display steps with risk badges
       │
       ▼
  User approves/skips each command
       │
       ▼
  Command output captured and sent back to Claude
       │
       ▼
  Claude iterates (max 6 rounds) until resolved
```

## File listing

```
ai-terminal/
├── ai_terminal.py      # Main script — run this directly
├── install.sh          # Installer (creates ~/.local/bin/aifix)
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Requirements

- Python 3.8+
- `anthropic` Python package (auto-installed by the script)
- An Anthropic API key
- Linux (the tool is designed for Linux environments)
