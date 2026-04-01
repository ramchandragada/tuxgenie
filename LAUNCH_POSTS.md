# TuxGenie Launch Posts

---

## Hacker News — Show HN

**Title:**
```
Show HN: TuxGenie – AI-powered Linux assistant that fixes your system in plain English
```

**Body:**
```
I built TuxGenie, an open-source CLI tool that lets you describe any Linux
problem in plain English and fixes it using Claude.

You type something like "my nginx won't start after I edited the config" and it:
1. Collects your system context silently (OS, kernel, running services, logs)
2. Sends it to Claude with the problem description
3. Gets back a structured fix plan with step-by-step commands
4. Shows each command with a risk level (SAFE / MODERATE / DANGEROUS) before running it
5. Feeds the output back to Claude and iterates until resolved

It never runs a command without your approval. Dangerous patterns (rm -rf /, dd if=,
mkfs, fork bombs) are flagged regardless of what the AI says.

Beyond just fixing problems, it has 16 built-in features: system health dashboard,
network diagnostics, security audit, disk management, log analysis, script generator,
cron scheduler, permission fixer, boot repair, Docker manager, SSH diagnostics, and more.

Install:
  pip install tuxgenie
  # or grab the .deb from the releases page (Debian/Ubuntu/Mint)

Requires a free Anthropic API key: https://console.anthropic.com

GitHub: https://github.com/ramchandragada/tuxgenie
```

---

## Reddit — r/linux

**Title:**
```
I built TuxGenie – open-source AI Linux assistant that fixes your system problems in plain English (free, MIT license)
```

**Body:**
```
Hey r/linux,

I've been working on TuxGenie for a while and wanted to share it with you.

**What it is:** A CLI tool that lets you describe any Linux problem in plain English
and fixes it using Claude AI.

**How it works:**
- You type: `tuxgenie "my docker containers can't reach the internet"`
- It silently collects your system context (OS, kernel, network config, logs, etc.)
- Claude analyzes everything and gives back a structured fix plan
- Each command shows a SAFE / MODERATE / DANGEROUS risk badge before running
- You approve or skip each step — it never runs anything without asking
- Output goes back to Claude, it iterates until the problem is resolved

**Features beyond just fixing problems:**
- System health dashboard
- Network diagnostics
- Security audit (open ports, failed logins, weak permissions)
- Log analyser (explains errors in plain English)
- Update advisor (flags packages likely to break your system)
- Script generator
- Docker manager
- Boot repair
- And more...

**Install:**
```
pip install tuxgenie
```
Or grab the .deb from the GitHub releases page.

**It's completely free and open source (MIT).** The only cost is your Anthropic API key,
which has a generous free tier.

GitHub: https://github.com/ramchandragada/tuxgenie

Would love feedback from this community — you're exactly the users I built this for.
```

---

## Reddit — r/commandline

**Title:**
```
TuxGenie: describe your Linux problem in plain English, AI fixes it step by step with your approval
```

**Body:**
```
Built a CLI tool for Linux troubleshooting powered by Claude AI.

The core idea: instead of googling error messages and copying random commands,
you just describe what's broken. TuxGenie collects your system context and
figures out the fix.

Every command is shown with a risk level before it runs. You approve each step.
Nothing executes without your say-so.

pip install tuxgenie

https://github.com/ramchandragada/tuxgenie

MIT licensed. Feedback welcome.
```

---

## Reddit — r/Ubuntu / r/debian

**Title:**
```
TuxGenie v3.9 – AI Linux assistant available as .deb (Ubuntu/Debian/Mint)
```

**Body:**
```
Just released TuxGenie v3.9 — an AI-powered Linux assistant that fixes system
problems in plain English.

Download the .deb directly from the releases page:
https://github.com/ramchandragada/tuxgenie/releases/latest

sudo dpkg -i tuxgenie_3.9.0_all.deb

Then just run: tuxgenie

It installs the anthropic Python package automatically. You need an Anthropic API
key (free tier available at console.anthropic.com).

Has 16 built-in features including system health, network diagnostics, security audit,
log analysis, and a self-update command (type `u` inside the app to update).

MIT licensed. Source: https://github.com/ramchandragada/tuxgenie
```

---

## dev.to article headline ideas

- "Meet TuxGenie: The AI Linux Assistant That Actually Fixes Things"
- "I built an AI co-pilot for Linux sysadmins — here's what I learned"
- "Stop Googling Linux errors. Let Claude fix them for you."
