<!-- update-contract: v1 -->
# Updates

USAP is text, so nothing checks for updates unless you ask. The skill folder ships `update.py`, which needs Python 3 and nothing else. Run it from anywhere; the examples assume the default install path.

```sh
U=~/.config/agents/skills/ultraterm-subagent-protocol/update.py
python3 $U                         # show the new version and notes, ask, verify, install
python3 $U --check                 # report only: exit 0 up to date, 10 available, 1 check failed
python3 $U --notice                # daily check for a shell or session-start hook
python3 $U --skip                  # no notice for this version; a newer one is announced
python3 $U --rollback              # restore the copy the last update replaced
python3 $U --auto on|off|status    # install updates automatically (off by default)
python3 $U --notify on|off|status  # the daily check and notice (on by default)
```

Re-running the install line also updates the skill and needs no Python.

## Notice

Put `python3 ~/.config/agents/skills/ultraterm-subagent-protocol/update.py --notice` in your shell profile or your agent host's session-start hook to hear about new releases. It prints at most once a day per version, on stderr:

```text
USAP 1.9.0 available (you have 1.8.0) · run: python3 ~/.config/agents/skills/ultraterm-subagent-protocol/update.py
turn on automatic updates: python3 ~/.config/agents/skills/ultraterm-subagent-protocol/update.py --auto on · skip: python3 ~/.config/agents/skills/ultraterm-subagent-protocol/update.py --skip
```

`--notice` never waits on the network: it shows what the last check found and, once a day, starts the next check in a detached low-priority process with a 4-second timeout. It is silent and makes no request outside an interactive terminal, when `CI` or `USAP_NO_UPDATE_CHECK=1` is set, or after `--notify off`. A failed check records its cause for `--check` and is not retried until the next day. Only stable `x.y.z` releases newer than the installed one count; drafts and prereleases are ignored.

## Install

`update.py` asks `Install <new> now? [Y/n]` on a terminal and installs without asking otherwise (the command is the consent). It downloads `usap.tar.gz` and `SHA256SUMS` for that release into a temporary folder, refuses a checksum mismatch, unpacks next to the skill, and swaps folders by rename. The previous copy stays as `.ultraterm-subagent-protocol.previous` until the next `update.py` run, so `--rollback` can restore it; a rolled-back version is skipped. Temporary files are removed whether the install succeeds or fails.

After the first successful install it asks once, `Install future updates automatically? [y/N]`, and remembers the answer. With automatic updates on, the daily check installs a new release in the background and logs to `update.log` (under 256 KB); agents load it in their next session. A failed automatic install keeps the current copy and brings the notice back.

A git checkout is never replaced: the notice and `update.py` print `git -C <folder> fetch --tags && git -C <folder> checkout v<new>` instead. A symbolic link is left alone.

## Files and removal

All state is one small file, `usap/update.json`, in the platform cache folder; see [PRIVACY.md](../PRIVACY.md). `--auto off` deletes it and the log. To uninstall, run `update.py --auto off`, then delete the skill folder.

Tests point `USAP_UPDATE_API` and `USAP_RELEASE_BASE` at local files and never use the network.
