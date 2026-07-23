# Security Policy

## Reporting a vulnerability

**Please do not open a public issue for security problems.** Report privately via
GitHub's **Security Advisories** on this repository
(*Security → Report a vulnerability*). We aim to acknowledge within a few days and
to ship a fix in a subsequent release, crediting reporters who wish to be named.

## What TuxGenie is (threat model in one paragraph)

TuxGenie is a local assistant that, at your request, proposes and — with your
consent — runs shell commands (often with `sudo`) to fix your Linux system. It is
**not** sandboxed, because its purpose is to change the host. The security model is
therefore about **consent, safety gates, and not leaking secrets**, not about
isolation.

## Safeguards

- **Layered command safety.** A hard-block denylist (regex + a shlex/argv analyzer
  that normalises paths and understands flag reordering and globs) refuses
  catastrophic commands regardless of approval. Ordinary state-changing commands
  are shown and confirmed **per step**.
- **High-risk gate.** Remote-pipe-to-shell (`curl … | bash`), writes to protected
  paths (`/etc`, `/boot`, `/usr`, `/lib`, `/sys`), and recursive `chmod`/`chown` on
  system directories are confirmed **even when auto-approve is on**.
- **`sudo` password handling.** Captured via the terminal, held only in process
  memory, passed to `sudo -S` over stdin — never in argv, never in environment,
  never written to disk, and scrubbed from any error output.
- **Updates require explicit consent.** TuxGenie never installs an update as root
  without an explicit "yes"; downloads are size- and SHA-256-checked before
  `dpkg`.
- **Telemetry is opt-in.** Error reporting is off by default, asked once on an
  interactive terminal, shows exactly what would be sent, and scrubs secrets
  (keys, tokens, Authorization headers, emails, IPs, home paths, sudo password) at
  a single trust boundary before anything leaves the machine.
- **No unsafe execution primitives.** No `eval`, `exec`, `pickle`, `marshal`, or
  `yaml.load`; all network calls use TLS-verified `urllib`.
- **File reads are credential-blocklisted** (`~/.ssh`, `~/.gnupg`, `*.pem/.key`,
  `/etc/shadow`, …) with symlink-resolving `realpath` checks.

## Known trust boundaries (by design)

- **Your chosen AI provider sees your prompts** and the command output TuxGenie
  shares with it. Pick Claude for confidential machines; free tiers may use
  free-tier data to improve their products (see `PRIVACY.md`).
- **Self-update trusts GitHub Releases over TLS.** Release artifacts are not yet
  independently signed; signature verification is planned. Until then, prefer
  installing from a channel you trust and review release diffs.
- **The AI can propose commands influenced by untrusted input** it reads (file
  contents, command output, logs). The safety gates above are the mitigation;
  keep per-step confirmation on for anything sensitive.

## Supported versions

Only the latest release is supported. Please update (`u` inside TuxGenie, or your
package manager) before reporting an issue.
