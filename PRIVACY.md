# Privacy

This document explains what the portable UltraTerm Subagent Protocol (USAP) skill does with data and local storage. It covers the installed text, the two one-line installers, and the optional `update.py` helper. It does not claim to control your agent host or model provider.

The short answer: the skill itself is plain text. It makes no network calls, needs no account, sends no telemetry or usage data, and writes no USAP logs, prompt history, transcripts, or credential files. Only commands you run (an installer, or `update.py`) make network requests or write the files listed below.

## The protocol itself

USAP is a set of instructions in `SKILL.md`, not a service, daemon, or runtime dependency. Loading it does not execute code, open a socket, read a configuration file, or contact GitHub, and the skill text never tells the agent to run `update.py`. It has no analytics SDK, exporter, beacon, remote image, font, script, or third-party asset.

The protocol describes routing, ownership, bounded delegation, worktrees, board citations, checkpoints, transcript forking, and failover. Those are host features described in optional references; installing USAP does not implement or start them, create their files, or change a host's checkpoint or telemetry schema. A host may keep its own session history or diagnostics under its own policy, and a model provider receives the prompts and worker output your agent sends it. USAP adds no account, service, or retention policy of its own.

## Network access

- **Install:** the one-line command fetches `install.sh` or `install.ps1` from GitHub before running it. The installer then downloads `usap.tar.gz` or `usap.zip` and `SHA256SUMS` from the latest public release, or from the pinned release when `USAP_VERSION` is set. It checks the archive's SHA-256 against the published sums before installing. A clean git checkout is fast-forwarded from the remote configured in that checkout. Nothing is uploaded.
- **Update check:** the optional `update.py` sends one anonymous GET to `https://api.github.com/repos/michael-berardi/ultraterm-subagent-protocol/releases/latest` with the fixed user agent `usap-update-check`. It sends no identifier, installed version, usage data, or machine data. It runs only when you, or a shell or session-start hook you set up, run `update.py`; `update.py --notice` checks at most once every 24 hours, in a detached background process with a 4-second timeout.
- **Update install:** `update.py` (or `update.py --auto on`, off by default) downloads `usap.tar.gz` and `SHA256SUMS` for the new release from GitHub, the same files the install line uses, and refuses a checksum mismatch.
- **Opting out:** `update.py --notice` is silent and makes no request outside an interactive terminal, when `CI` or `USAP_NO_UPDATE_CHECK=1` is set, or after `update.py --notify off`. Not running `update.py` at all also means no check.
- **Your agent:** using the skill sends your prompts and worker output to the model provider your agent is set up to use. That provider's terms and retention apply; USAP adds nothing.
- **Documentation links:** clicking a link opens GitHub or the project site in your browser; the docs load no external assets on their own.

GitHub sees each request like any other download: your IP address and the user agent. The checksum verifies the published archive against the published sums; it does not independently authenticate the publisher or the downloaded installer script. Inspect the installer first if your trust policy requires it.

## Local-write table

Every write made by this repository has either automatic cleanup or an explicit retention bound. There are no USAP-managed prompt histories, transcripts, or credential stores.

| Local write | Contents | Lifetime | Cleanup | Deletion |
|---|---|---|---|---|
| Installed skill folder: `~/.config/agents/skills/ultraterm-subagent-protocol` (Windows: `%USERPROFILE%\.config\agents\skills\ultraterm-subagent-protocol`) | The release text: `SKILL.md`, `README.md`, `PRIVACY.md`, `update.py`, references, and other shipped docs; release archives omit `tests/` and `scripts/`. | Until you install again, update, or remove it. | A plain copy is replaced by rename through a hidden staging folder and a hidden backup; a git checkout is fast-forwarded in place rather than replaced; links and unsafe copies are refused. | There is no uninstall command. Delete the folder yourself; deleting a git checkout also deletes its `.git` history. |
| Installer download folder: `${TMPDIR:-/tmp}/usap-install.XXXXXX` on macOS/Linux, `%TEMP%\usap-install-<guid>` on Windows | Downloaded archive and `SHA256SUMS` only. | One installer invocation, including failure and interrupt paths. | Shell installer uses an `EXIT` cleanup trap; PowerShell installer uses `finally`. | Automatic when the installer exits. |
| Installer staging folder: `.ultraterm-subagent-protocol.new.<pid or guid>` in the skills folder | Unpacked release before it moves into place. | Only until the folder swap. | Moved to the installed path on success; otherwise removed by the cleanup trap/`finally`. | Automatic. |
| Installer backup folder: `.ultraterm-subagent-protocol.old.<pid or guid>` in the skills folder | The previous plain installed copy during a swap. | Only while the replacement takes place. | Restored to the installed path if the swap fails. | Deleted immediately after a successful swap. |
| Git checkout at the installed path | Tracked skill files plus git's own objects, refs, and reflog after `git pull --ff-only`. | Until you manage or delete the checkout. | No staging or backup copy is made; dirty, pinned, and unsafe checkouts are refused before writes. A failed fast-forward leaves tracked files and HEAD unchanged, though git may keep its own fetch metadata. | User-controlled through git or by deleting the checkout folder. |
| Update state: `usap/update.json` in your cache folder (`~/Library/Caches` on macOS, `$XDG_CACHE_HOME` or `~/.cache` on Linux, `%LOCALAPPDATA%` on Windows) | Time of the last check, the latest version or the cause of a failed check, the skipped version, the last notice shown, and your automatic-update and notice choices. A few hundred bytes. | Until `update.py --auto off`. | Rewritten in place (atomic rename) on each check; never grows. | `update.py --auto off` deletes it (keeping only a `--notify off` choice), or delete the `usap` cache folder. |
| Update log: `usap/update.log` in the same cache folder | One line per automatic install attempt or failed background check. | Kept under 256 KB; the oldest lines are dropped first. | Trimmed on every write. | `update.py --auto off` deletes it. |
| Update download folder: `usap-update.XXXXXX` in the system temporary folder | Downloaded `usap.tar.gz` and `SHA256SUMS`. | One `update.py` install. | Removed in a `finally` block whether the install succeeds or fails. | Automatic. |
| Update staging folder: `.ultraterm-subagent-protocol.new.XXXXXX` in the skills folder | Unpacked, verified release before the swap. | Only until the folder swap. | Renamed into place on success; removed on failure. | Automatic. |
| Rollback copy: `.ultraterm-subagent-protocol.previous` in the skills folder | The copy the last `update.py` install replaced (at most one). | Until the next `update.py` run. | Deleted by the next `update.py` run; `update.py --rollback` restores it instead (via a short-lived `.ultraterm-subagent-protocol.discard` folder). | Automatic, or delete it yourself. |
| Release build output: `dist/release/` by default | `usap.tar.gz`, `usap.zip`, installers, and `SHA256SUMS` for maintainers. | Retained until the next `scripts/build-release.sh` run overwrites it or you delete it. | Each build removes the old output before creating new files. | Manual, or automatically on the next build. |
| Installer-test temporary folders | Test homes, a local release fixture, and captured test output outside the real home directory. | One test invocation. | Shell test uses an `EXIT` trap; PowerShell test uses `try`/`finally`. | Automatic when the test ends. |
| Python-test temporary folders | Small throwaway fixture files and a fake cache folder used by the tests. | One test case. | `tempfile.TemporaryDirectory` removes them at exit. | Automatic. |

Installer variables do not create persistent preferences: `USAP_SKILLS_DIR` selects a target folder, `USAP_VERSION` pins a release, and `USAP_RELEASE_BASE` overrides the download URL for tests. `USAP_UPDATE_API` points `update.py` at a local release record for tests. The installers need no sudo, Node, or Python; they do not edit your shell profile, PATH, or system settings, and they store no credentials. Installer assets start at v1.5.0; older releases use the manual clone route.

## Removal

Run `update.py --auto off` if you used `update.py`, then delete `~/.config/agents/skills/ultraterm-subagent-protocol`, or `%USERPROFILE%\.config\agents\skills\ultraterm-subagent-protocol` on Windows, and any `.ultraterm-subagent-protocol.previous` folder next to it. A symbolic link at that path is never followed or replaced by the installer or `update.py`; remove the link yourself if you no longer want it. Your agent host and model provider may have separate data that USAP cannot delete.
