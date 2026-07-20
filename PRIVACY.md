# TuxGenie — Privacy & Transparency

TuxGenie is free, open source (MIT), and **not a business**. We don't sell
anything, we don't run ads, and we make no money from you. Our only goal is to
make Linux easier for everyone. This page explains — in plain English — exactly
what TuxGenie does and does not do with your data. If anything here is ever
unclear or wrong, [open an issue](https://github.com/ramchandragada/tuxgenie/issues)
and we'll fix it.

## The short version

- **No telemetry. No analytics. No tracking. No accounts.** TuxGenie never
  "phones home." There is no server that counts you, watches you, or profiles
  you. You can read the whole thing — it's one file, `tuxgenie.py`.
- **Nothing about your machine is sent anywhere unless you run an AI task** —
  and then it goes *only* to the AI provider you chose (Anthropic's Claude or
  Google Gemini), never to us.
- **Your API key and sudo password stay on your machine.** The API key is saved
  with owner-only permissions (`chmod 600`); your sudo password is held in
  memory for the session only and is never written to disk or sent anywhere.
- **Everything that leaves your machine is opt-in and shown to you first** —
  crash reports, feedback, and shared fixes all open GitHub in your browser and
  send nothing until *you* click Submit.

## What gets sent to the AI, and when

TuxGenie only contacts an AI provider when you actually ask it to fix, explain,
or plan something. Simple commands (`apt install …`, `systemctl status …`, etc.)
run **locally with no AI call at all**.

When an AI task *does* run, TuxGenie collects read-only system context so the AI
can diagnose accurately, and sends it to your chosen provider. That context can
include:

- Your distro, kernel, architecture, desktop environment, and shell
- Your username and hostname (as reported by the system)
- Health/hardware details relevant to the task (CPU, RAM, disk, GPU, audio,
  network interfaces, failed services, recent error logs)
- A list of installed packages (top entries), for install/troubleshooting help
- The command output from each step, fed back so the AI can decide the next step

This is the information a human expert would need to help you — nothing more. It
is sent **directly to the AI provider over HTTPS**. TuxGenie has no server in the
middle and keeps no copy off your machine.

### Choosing a provider — a privacy note

| Provider | Cost | Data handling |
|----------|------|---------------|
| **Claude (Anthropic)** | Free trial credit, then ~$0.01/session | Per Anthropic's API terms, API inputs/outputs are **not used to train their models**. Best choice for sensitive systems. |
| **Google Gemini** | **Free tier, no credit card** | On the **free tier**, Google may use your prompts and the AI's responses **to improve their products**, and staff may review them. Great for everyday use; **prefer Claude (or a paid Gemini plan) for confidential machines.** |

Provider terms can change — always the current source of truth:
[Anthropic Privacy](https://www.anthropic.com/legal/privacy) ·
[Google Gemini API terms](https://ai.google.dev/gemini-api/terms).

## What stays on your machine

- **Config & API key** — `~/.config/tuxgenie/config.json`, owner-only (`chmod 600`).
- **Sudo password** — kept in memory for the current session only, passed to
  `sudo` via stdin, never saved to disk, and redacted from any error output.
- **Cross-session memory** (optional) — to give better help over time, TuxGenie
  can remember a local action log and a system "fingerprint" (hardware summary +
  installed apps). This lives only on your machine. Turn it off in
  **Settings → Toggle cross-session memory**, and wipe it anytime with
  **Settings → Clear stored memory**.
- **History** — recent tasks, stored locally, part of the same memory toggle.

## What only leaves your machine if you choose to send it

All of these open GitHub in your browser and send **nothing** until you review
the pre-filled content and click Submit:

- **Crash reports** — opt-in after an unexpected error. The report is
  **sanitized first**: your home path is replaced with `~`, and any API key or
  sudo password that might appear is redacted. It contains the error, the
  feature name, the version, and your distro/kernel.
- **Feedback & feature requests** — only what you type.
- **Shared fixes** — if you choose to contribute a fix that worked for you, the
  problem/command/fix is shown to you in full before it opens GitHub.

## Updates

The `u` command checks GitHub Releases for a newer version. The downloaded
`.deb` is verified against the release's published **SHA-256 digest** before
installation — a corrupted or tampered download is refused, never installed.

## Your controls, in one place

- **Settings → Switch AI provider** — Claude or Gemini, anytime.
- **Settings → Toggle cross-session memory** — stop saving anything locally.
- **Settings → Clear stored memory** — wipe the action log and fingerprint.
- **Delete `~/.config/tuxgenie/`** — removes your key and all local state.
- **Read the source** — it's one file. Nothing is hidden.

---

*Questions or concerns? [Open an issue](https://github.com/ramchandragada/tuxgenie/issues).
TuxGenie is built to make Linux better for everyone — being honest with you is
part of that.*
