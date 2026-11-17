# Changelog

## 7.27.0

Light panel polish on ≤8 GB PCs (Mint XFCE):

- Short quiet banner under the brand (no wall of WebKit instructions).
- Usage meters sit right under the title.
- Tile icons try several Mint-friendly theme names, then a visible glyph fallback so icons do not vanish on XFCE.

## 7.26.0

Light control panel (≤8 GB RAM) restores what 7.25.0 dropped:

- Live **This PC** strip — CPU, Memory, Disk, and PC cards that refresh and open health/disk/hardware.
- Themed **icons** on every quick-action tile (Wi-Fi, Sound, Apps, …).
- Shorter low-RAM note. App Store remains in the terminal (`apps`); set `TUXGENIE_FORCE_WEBKIT=1` for the full WebKit panel.

## 7.25.0

tuxgenie-app memory on small PCs (≤8 GB RAM, e.g. Mint XFCE):

- Skip WebKitGTK on machines under 8 GB RAM and use the light GTK control panel instead. WebKit was measured at ~3.5 GB RSS alone on a 5.7 GB PC. Set `TUXGENIE_FORCE_WEBKIT=1` to force the modern panel.
- Cap VTE scrollback at 5000 lines (was unlimited).
- App Store icons use `file://` paths (not base64 data URIs), prefer Flathub 64×64, and refuse icons larger than 48 KB.
- Home pulse slows down; the mem widget reports TuxGenie's own RSS when it is large.

## 7.24.0

API key paste and terminal copy/paste:

- Pasting a Gemini (or other) API key shows stars as characters arrive, so clipboard paste is visibly working. Press Enter to save.
- Bracketed-paste markers from VTE/gnome-terminal are stripped so keys are no longer rejected as “doesn’t look like a Gemini key”.
- In `tuxgenie-app`, select text then Ctrl+C (or Ctrl+Shift+C) to copy; Ctrl+V / Ctrl+Shift+V or right-click to paste. The live-terminal header reminds you.

## 7.23.0

Linux Mint, including Mint XFCE on small PCs (6 GB thin clients such as the HP t640):

- Mint keeps Firefox and Thunderbird as debs. TuxGenie no longer installs the Ubuntu snap for those apps on Linux Mint.
- Every Mint edition (Cinnamon, MATE, and XFCE) gets Update Manager (`mintupdate`). XFCE and MATE also open their appearance settings. This follows the distro, not one PC.
- Codecs on Mint use `mint-meta-codecs` from the flavour, not Ubuntu's `ubuntu-restricted-extras`.
- Held updates on Mint point at Update Manager before offering `apt full-upgrade`.
- PCs under 8 GB of RAM with swap already in use get zram, not a swappiness of 10 (that freezes small desktops). Larger PCs still get swappiness 10.
- AMD graphics already on `amdgpu` are reported as the right driver. An AnyDesk apt line that is still `http://` can be switched to `https://`.

## 7.22.1

Follow-ups left open after the 7.22.0 Ubuntu release:

- **BUG-16:** Plain-English installs and playbook phrases (`install vlc`, `wifi not working`, `no sound`) route to the catalog / built-in fix flows first. The AI is only used when nothing matches.
- **BUG-17:** Memory hints / recall match only the saved problem text (never command steps) and need a real overlap, so unrelated past sessions are not offered as “you had this before”.
- **BUG-18:** `q` exits cleanly from Undo; typos like `updtes` suggest the closest menu keyword; empty catalog searches stay empty with a hint; pulse labels say “% used”; Smart routing is marked N/A for Gemini and other single-model providers; org/account IDs are scrubbed from error text; ~20 KB pastes are clamped; sudo passwords must pass `sudo -v` before any privileged step.

## 7.22.0

Ubuntu and Ubuntu-based desktops (Ubuntu 24.04 noble, Zorin OS, Linux Mint, Pop!_OS), from the 7.21.0 recheck:

- State-changing commands need an explicit yes, including ones the user types. `sysctl k=v`, `git -c core.sshCommand`, `pip config set`, `nmcli connection reload`, `apt-cache clean`, and `find -fls` are no longer treated as read-only.
- Destructive forms are blocked: `eval`, `base64|sh`, Python/Perl `rmtree` of `/`, `xargs rm -rf`, `rm -rf /home/<user>`, moving `/etc`, overwriting fstab, sysrq, `grub-install`, `crontab -r`, and purging the kernel, sudo, or python3.
- API keys are read with `getpass` (not echoed). Session logs are redacted and saved mode 0600, including UUID-style keys.
- Apt lock retries wait at least 5 seconds when the holder isn't visible. `/proc/locks` matches device and inode. Phased and held updates are named before install.
- Docker on Ubuntu-family uses `docker.io` or Docker's Ubuntu repo (`UBUNTU_CODENAME`). It does not write a Debian trixie repo, and it leaves an existing `docker-ce` install alone.
- Firefox, Chromium, and Thunderbird install as the Ubuntu snap (one copy). Lazygit, Fastfetch, Ulauncher, and VeraCrypt no longer depend on apt names noble doesn't ship. virt-manager uses `qemu-system-x86` on Ubuntu-family. JetBrains Toolbox drops the 404 `&type=download` query. Rambox is flagged abandoned and installs Ferdium.
- Bluetooth, webcam, and sound playbooks check that the hardware exists (rfkill, lsusb, v4l2, `/proc/asound`, pactl/wpctl) before restarting a service.
- A provider chosen in Settings is the one used on the next start. Failover continues past HTTP 401 and 413 to the next free provider and still never switches to paid Claude without a yes. A non-rating typed at the rating prompt is run as the next request.
- `tuxgenie-app` swaps a blank or stalled WebKit deck for the button panel and says to run `tuxgenie` in a terminal if that panel can't be shown.
- Interpreter one-liners that hide a destructive shell command are blocked (`perl -e 'system("rm -rf /")'`, and the same for Python, Ruby, and Node `system`/`exec`/`subprocess`/backticks).
- If Firefox's snap or Docker (`docker.io` / `docker-ce`) is already installed, the catalog says so without asking for a sudo password.
- The main prompt is printed once. A typed command you decline is not stored as if it ran. The compact menu wraps between items, and `tuxgenie-app` from a checkout runs the sibling `tuxgenie.py`.
