# Changelog

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
