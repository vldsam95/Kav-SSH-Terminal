# Kav SSH Terminal

A personal, experimental desktop SSH/SFTP client with Hebrew and mixed RTL/LTR terminal rendering, built with Python and PySide6.

**Status:** early development. Terminal compatibility and real-server behavior are still being tested. This source release is not a security certification or a production support commitment.

## Features

- SSH sessions in tabs, with password, private-key, agent and keyboard-interactive authentication.
- Hebrew/English terminal text, logical-order copy/paste and ANSI colors.
- A pyte-backed screen buffer, alternate-screen handling and terminal input modes.
- SFTP browsing, transfers and remote text-file editing.
- Local connection profiles and optional password storage through the operating system keychain.
- Font, size and color-preset settings.

Terminal applications such as vim, nano and tmux may expose compatibility gaps. No live connection to a private server is required or performed by the automated tests.

## Run on Windows

Install Python 3.12 or newer from [python.org](https://www.python.org/downloads/).
Download this repository using **Code → Download ZIP** and extract it to a permanent folder, or clone it:

```powershell
git clone https://github.com/vldsam95/Kav-SSH-Terminal.git
cd Kav-SSH-Terminal
```

Double-click **Start Kav SSH Terminal.cmd**, or run:

```powershell
.\scripts\run.ps1
```

The launcher creates a local `.venv` and installs dependencies from PyPI on first run. It uses your installed Python interpreter. Do not copy another computer's `.venv`.

For a manual setup:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e "."
.\.venv\Scripts\python -m main
```

After installation, `kav-ssh` is also available from the activated environment.

## Run on Linux

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m main
```

A graphical desktop and platform-specific Qt libraries are required. Keychain password storage also needs a working OS keyring backend. Linux has not been manually validated for this initial publication.

## Existing local settings

The previous development name was BidiSSH. The internal config directory and keychain service keep that identifier so existing profiles and saved passwords remain accessible. The visible application name, package, launcher and build output use Kav SSH Terminal / KavSSH. No profiles or keychain contents are included in this repository.

## Security and privacy

Passwords are passed to SSH/SFTP in memory; optional saved passwords use the OS keychain. Profile JSON stores connection metadata, not passwords. Hostnames, usernames, private-key paths and notes in your own local profiles can still be sensitive.

Host-key checking uses the user's `~/.ssh/known_hosts`. Verify server fingerprints through a trusted channel and provision known hosts before connecting. A full first-connect trust interface is not implemented. Do not disable host-key validation to work around a connection error.

There is no application telemetry or analytics integration in the reviewed source. Dependency installation contacts PyPI; SSH/SFTP operations contact servers you select. Files opened for editing can create local temporary copies; avoid editing sensitive remote files until you have reviewed the temporary-file workflow.

See [SECURITY.md](SECURITY.md). Never upload private keys, passwords, `.env` files, personal connection profiles or session logs.

## Development and tests

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]" build
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m build
```

The existing suite covers terminal rendering/buffers/input, profile persistence, a test keyring adapter and SFTP path/model helpers. Automated checks do not prove real-server interoperability or a comprehensive security review.

`requirements-reviewed-windows.txt` records the Windows/Python 3.12 runtime
dependency versions used for the initial publication checks. It is a snapshot,
not a cross-platform lockfile; future installs and other systems may differ.

## Build scripts

Windows: `scripts/build_windows.ps1`. Linux: `scripts/build_linux.sh`.
The expected portable output is `dist/KavSSH/` (`KavSSH.exe` on Windows).

Build scripts are provided for development; **no executable release is included**. Before distributing a bundled executable, review every included dependency's licenses, preserve notices, satisfy applicable corresponding-source and library replacement/relinking requirements, and validate the actual bundle. See [PUBLICATION_REVIEW.he.md](PUBLICATION_REVIEW.he.md).

## License and credits

Original project code: [MIT License](LICENSE), Copyright (c) 2026 vldsam95. MIT allows commercial use by others and provides the software without warranty.

Dependencies and palettes retain their own licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [third_party_licenses/](third_party_licenses/) and the Hebrew [publication review](PUBLICATION_REVIEW.he.md). Included dependency notices are a version-specific snapshot, not a guarantee for future dependency updates.

Kav SSH Terminal is independent and is not affiliated with Qt, AsyncSSH, PuTTY, Microsoft, or the credited theme projects. Third-party names identify compatibility, dependencies or palette inspiration; no endorsement is claimed.
