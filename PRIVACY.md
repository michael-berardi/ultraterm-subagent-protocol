# Privacy

USAP is a skill: text that your agent reads. It has no account, service, or telemetry, and the skill text never asks the agent to make a network request.

## Network requests

- **Install.** The install line downloads the installer, `usap.tar.gz` (or `usap.zip`) and `SHA256SUMS` from the GitHub release. A clean git checkout is fast-forwarded from the remote you configured. Nothing is uploaded.
- **Update check.** The optional `update.py` sends one GET to `https://api.github.com/repos/michael-berardi/ultraterm-subagent-protocol/releases/latest` with the fixed user agent `usap-update-check`. It sends no identifier, installed version, usage data, or machine data. It runs only when you or a hook you set up run `update.py`; `--notice` asks at most once every 24 hours.
- **Update install.** `update.py` (or `--auto on`) downloads `usap.tar.gz` and `SHA256SUMS` for the new release from GitHub, the same files the install line uses.
- **Your agent.** Using the skill sends your prompts and worker output to the model provider your agent is set up to use. That provider's terms apply; USAP adds nothing.

GitHub sees the request like any other download: your IP address and the user agent.

## Local files

`update.py` writes one small file, `usap/update.json`, in your cache folder (`~/Library/Caches` on macOS, `$XDG_CACHE_HOME` or `~/.cache` on Linux, `%LOCALAPPDATA%` on Windows). It holds the time of the last check, the latest version or the cause of a failed check, the skipped version, the last notice shown, and your automatic-update and notice choices. With automatic updates on, `usap/update.log` records each install attempt and stays under 256 KB. An update keeps the previous copy as `.ultraterm-subagent-protocol.previous` next to the skill folder until the next `update.py` run.

## Turning it off and removing it

- `USAP_NO_UPDATE_CHECK=1`, `CI`, a non-interactive session, or `update.py --notify off` keeps `--notice` silent and offline.
- `update.py --auto off` turns off automatic updates and deletes `update.json` and `update.log` (it keeps only a `--notify off` choice).
- To uninstall, run `update.py --auto off`, then delete the skill folder.
