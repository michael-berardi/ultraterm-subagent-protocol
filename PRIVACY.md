# Privacy

This document explains what the portable UltraTerm Subagent Protocol (USAP) skill does with data and local storage. It covers the installed text and the two one-line installers. It does not claim to control your agent host or model provider.

The short answer: the installed skill is plain text. It makes no network calls, needs no account, sends no telemetry or usage data, and writes no USAP logs, prompt history, transcripts, caches, or credential files. Only a user-invoked installer writes the temporary and installed files listed below.

## The protocol itself

USAP is a set of instructions in `SKILL.md`, not a service, daemon, or runtime dependency. Loading it does not execute code, open a socket, read a configuration file, or contact GitHub. It has no analytics SDK, exporter, beacon, remote image, font, script, or third-party asset.

The protocol describes routing, ownership, bounded delegation, worktrees, board citations, checkpoints, transcript forking, and failover. Those are host features described in optional references; installing USAP does not implement or start them, create their files, or change a host's checkpoint or telemetry schema. A host may keep its own session history or diagnostics under its own policy, and a model provider receives the prompts and worker output your agent sends it. USAP adds no account, service, or retention policy of its own.

## Network access

- **Install or update:** the one-line command fetches `install.sh` or `install.ps1` from GitHub before running it. The installer then downloads `usap.tar.gz` or `usap.zip` and `SHA256SUMS` from the latest public release, or from the pinned release when `USAP_VERSION` is set. It checks the archive's SHA-256 against the published sums before installing. A clean git checkout is fast-forwarded from the remote configured in that checkout. Nothing is uploaded.
- **Normal use:** no network access. The skill never checks for updates and never prompts you to update. To opt out of an update, simply do not run the install command again.
- **Documentation links:** clicking a link opens GitHub or the project site in your browser; the docs load no external assets on their own.

The checksum verifies the published archive against the published sums; it does not independently authenticate the publisher or the downloaded installer script. Inspect the installer first if your trust policy requires it.

## Local-write table

Every write made by this repository has either automatic cleanup or an explicit retention bound. There are no USAP-managed logs, history files, caches, transcripts, or credential stores.

| Local write | Contents | Lifetime | Cleanup | Deletion |
|---|---|---|---|---|
| Installed skill folder: `~/.config/agents/skills/ultraterm-subagent-protocol` (Windows: `%USERPROFILE%\.config\agents\skills\ultraterm-subagent-protocol`) | The release text: `SKILL.md`, `README.md`, `PRIVACY.md`, references, and other shipped docs; release archives omit `tests/` and `scripts/`. | Until you run the installer again or remove it. | A plain copy is replaced by rename through a hidden staging folder and a hidden backup; a git checkout is fast-forwarded in place rather than replaced; links and unsafe copies are refused. | There is no uninstall command. Delete the folder yourself; deleting a git checkout also deletes its `.git` history. |
| Installer download folder: `${TMPDIR:-/tmp}/usap-install.XXXXXX` on macOS/Linux, `%TEMP%\usap-install-<guid>` on Windows | Downloaded archive and `SHA256SUMS` only. | One installer invocation, including failure and interrupt paths. | Shell installer uses an `EXIT` cleanup trap; PowerShell installer uses `finally`. | Automatic when the installer exits. |
| Installer staging folder: `.ultraterm-subagent-protocol.new.<pid or guid>` in the skills folder | Unpacked release before it moves into place. | Only until the folder swap. | Moved to the installed path on success; otherwise removed by the cleanup trap/`finally`. | Automatic. |
| Installer backup folder: `.ultraterm-subagent-protocol.old.<pid or guid>` in the skills folder | The previous plain installed copy during a swap. | Only while the replacement takes place. | Restored to the installed path if the swap fails. | Deleted immediately after a successful swap. |
| Git checkout at the installed path | Tracked skill files plus git's own objects, refs, and reflog after `git pull --ff-only`. | Until you manage or delete the checkout. | No staging or backup copy is made; dirty, pinned, and unsafe checkouts are refused before writes. A failed fast-forward leaves tracked files and HEAD unchanged, though git may keep its own fetch metadata. | User-controlled through git or by deleting the checkout folder. |
| Release build output: `dist/release/` by default | `usap.tar.gz`, `usap.zip`, installers, and `SHA256SUMS` for maintainers. | Retained until the next `scripts/build-release.sh` run overwrites it or you delete it. | Each build removes the old output before creating new files. | Manual, or automatically on the next build. |
| Installer-test temporary folders | Test homes, a local release fixture, and captured test output outside the real home directory. | One test invocation. | Shell test uses an `EXIT` trap; PowerShell test uses `try`/`finally`. | Automatic when the test ends. |
| Python-test temporary folders | Small throwaway fixture files used by documentation tests. | One test case. | `tempfile.TemporaryDirectory` removes them at exit. | Automatic. |

Installer variables do not create persistent preferences: `USAP_SKILLS_DIR` selects a target folder, `USAP_VERSION` pins a release, and `USAP_RELEASE_BASE` overrides the download URL for tests. The installers need no sudo, Node, or Python; they do not edit your shell profile, PATH, or system settings, and they store no credentials. Installer assets start at v1.5.0; older releases use the manual clone route.

## Removal

Delete `~/.config/agents/skills/ultraterm-subagent-protocol`, or `%USERPROFILE%\.config\agents\skills\ultraterm-subagent-protocol` on Windows. A symbolic link at that path is never followed or replaced by the installer; remove the link yourself if you no longer want it. Your agent host and model provider may have separate data that USAP cannot delete.
