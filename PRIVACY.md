# TuxGenie — Privacy & Transparency

TuxGenie is free, open source (MIT), and **not a business**. We don't sell
anything, we don't run ads, and we make no money from you. Our only goal is to
make Linux easier for everyone. This page explains — in plain English — exactly
what TuxGenie does and does not do with your data. If anything here is ever
unclear or wrong, [open an issue](https://github.com/ramchandragada/tuxgenie/issues)
and we'll fix it.

## The short version

- **No telemetry by default. No analytics. No tracking. No accounts.** TuxGenie
  does not count you, watch you, or profile you. The *one* thing it can send us —
  an anonymous, secret-scrubbed **error report** — is **strictly opt-in**: it is
  OFF until you explicitly say yes, and it is described in full below. You can
  read the whole thing — it's one file, `tuxgenie.py`.
- **Apart from opt-in error reports (below), nothing about your machine is sent
  anywhere unless you run an AI task** — and then it goes *only* to the AI
  provider you chose (Claude, Gemini, Groq, or SambaNova), never to us.
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
| **Groq** | **Free tier, no credit card** | Very fast (open Llama models). Check [Groq's terms](https://groq.com/terms-of-use/) for how free-tier data is handled; as with any free tier, **prefer Claude for confidential machines.** |
| **SambaNova** | **Free tier, no credit card** | Fast (open Llama models). Check [SambaNova's terms](https://sambanova.ai/terms-and-conditions) for how free-tier data is handled; as with any free tier, **prefer Claude for confidential machines.** |

Provider terms can change — always the current source of truth:
[Anthropic Privacy](https://www.anthropic.com/legal/privacy) ·
[Google Gemini API terms](https://ai.google.dev/gemini-api/terms) ·
[Groq terms](https://groq.com/terms-of-use/) ·
[SambaNova terms](https://sambanova.ai/terms-and-conditions).

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

- **Crash reports (GitHub)** — opt-in after an unexpected error. The report is
  **sanitized first**: your home path is replaced with `~`, and any API key or
  sudo password that might appear is redacted. It contains the error, the
  feature name, the version, and your distro/kernel.
- **Feedback & feature requests** — only what you type.
- **Shared fixes** — if you choose to contribute a fix that worked for you, the
  problem/command/fix is shown to you in full before it opens GitHub.

## Anonymous error reporting (opt-in)

To fix bugs without every user having to file a report by hand, TuxGenie can
send an **anonymous, scrubbed** error report when something goes wrong (a crash,
or an AI provider error we couldn't recover from). This is **completely
optional**:

- **It is OFF until you turn it on.** The first time an error occurs, TuxGenie
  asks once, and offers a **"see exactly what's sent"** option that prints the
  literal report. Your choice is remembered. Change it anytime in
  **Settings → Toggle anonymous error reports**.
- **What is sent:** TuxGenie version · your distro name · Python version · the
  name of your AI provider (e.g. "gemini") · the error type and a
  **secret-scrubbed** error message/stack.
- **What is NEVER sent:** your prompts or commands, file contents, API keys,
  sudo password, email address, or **IP address**. Reports carry no account or
  device identifier — identical errors from different people are simply counted
  together.
- **Where it goes:** a self-hosted-style error collector (a private
  [Sentry](https://sentry.io) project in the EU region). We deliberately do
  **not** use Sentry's PII option — no IP addresses or request headers are
  attached. The scrubbing happens on your machine *before* anything is sent.
- **How to be sure:** the scrubbing rules and the exact payload are in
  `tuxgenie.py` (`_sanitize_tb` and `_build_error_event`) — it's one file, and
  nothing is hidden.

## Updates

The `u` command checks GitHub Releases for a newer version. The downloaded
`.deb` is verified against the release's published **SHA-256 digest** before
installation — a corrupted or tampered download is refused, never installed.

## Your controls, in one place

- **Settings → Switch AI provider** — Claude, Gemini, Groq, or SambaNova, anytime.
- **Settings → Toggle anonymous error reports** — on/off, off by default.
- **Settings → Toggle cross-session memory** — stop saving anything locally.
- **Settings → Clear stored memory** — wipe the action log and fingerprint.
- **Delete `~/.config/tuxgenie/`** — removes your key and all local state.
- **Read the source** — it's one file. Nothing is hidden.

---

*Questions or concerns? [Open an issue](https://github.com/ramchandragada/tuxgenie/issues).
TuxGenie is built to make Linux better for everyone — being honest with you is
part of that.*
