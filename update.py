#!/usr/bin/env python3
"""USAP update helper. Python standard library only; no telemetry.

  python3 update.py                         install the latest release (asks first on a terminal)
  python3 update.py --check                 report only: exit 0 current, 10 available, 1 check failed
  python3 update.py --notice                daily check for a shell or session-start hook
  python3 update.py --skip                  hide the newest release's notice until a newer one
  python3 update.py --rollback              restore the copy the last update replaced
  python3 update.py --auto on|off|status    install updates automatically (off by default)
  python3 update.py --notify on|off|status  the daily check and notice (on by default)

The skill never runs this file itself. --notice stays silent and offline outside an
interactive terminal, in CI, with USAP_NO_UPDATE_CHECK=1, or after --notify off.
USAP_UPDATE_API and USAP_RELEASE_BASE point at a local release for tests.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

NAME = "ultraterm-subagent-protocol"
REPO = "michael-berardi/ultraterm-subagent-protocol"
API = "https://api.github.com/repos/" + REPO + "/releases/latest"
DOWNLOAD = "https://github.com/" + REPO + "/releases/download/v%s"
USER_AGENT = "usap-update-check"
DAY = 24 * 60 * 60
LOG_LIMIT = 256 * 1024
ROOT = Path(os.path.abspath(__file__)).parent  # the installed skill folder


class UpdateError(Exception):
    pass


# --- state: one small JSON file and, only for automatic installs, one bounded log ---

def cache_dir():
    if os.environ.get("XDG_CACHE_HOME"):
        base = Path(os.environ["XDG_CACHE_HOME"])
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path.home() / ".cache"
    return base / "usap"


def load():
    try:
        state = json.loads((cache_dir() / "update.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))  # created 0600
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def save(state):
    write_atomic(cache_dir() / "update.json", json.dumps(state, sort_keys=True).encode())


def log(message):
    path = cache_dir() / "update.log"
    try:
        old = path.read_bytes()
    except OSError:
        old = b""
    data = old + ("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), message)).encode()
    if len(data) > LOG_LIMIT:
        data = data[-LOG_LIMIT:]
        data = data[data.find(b"\n") + 1:]
    write_atomic(path, data)


def remove(path):
    try:
        path.unlink()
    except OSError:
        pass


def within_day(stamp):
    try:
        return 0 <= time.time() - float(stamp) < DAY
    except (TypeError, ValueError):
        return False


# --- versions and the release record ---

def installed_version(root=None):
    try:
        text = ((root or ROOT) / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r"(?m)^  version:\s*(\S+)\s*$", text)
    return match.group(1) if match else ""


def parse(version):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version or ""):
        return None
    return tuple(int(part) for part in version.split("."))


def is_newer(candidate, current):
    new, old = parse(candidate), parse(current)
    return bool(new and old and new > old)


def fetch_latest():
    """One anonymous GET of the public latest-release record: (version, notes)."""
    request = urllib.request.Request(
        os.environ.get("USAP_UPDATE_API") or API,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=4) as response:
        record = json.loads(response.read().decode("utf-8"))
    if not isinstance(record, dict) or record.get("draft") or record.get("prerelease"):
        return "", ""
    tag = str(record.get("tag_name") or "")
    return (tag[1:] if tag.startswith("v") else tag), str(record.get("body") or "")


def refresh(state):
    """Ask the release API now and record the result, or the failure and its cause."""
    state["checked_at"] = time.time()
    notes = ""
    try:
        state["latest"], notes = fetch_latest()
        state.pop("error", None)
    except urllib.error.HTTPError as exc:
        state["error"] = "the release API returned HTTP %s" % exc.code
    except Exception as exc:
        state["error"] = "cannot read the release API (%s)" % (getattr(exc, "reason", None) or exc)
    save(state)
    return notes


# --- commands shown to the user ---

def shown(path):
    text, home = str(path), str(Path.home())
    if " " in text:
        return '"%s"' % text
    return "~" + text[len(home):] if text.startswith(home + os.sep) else text


def helper():
    return ("python" if os.name == "nt" else "python3") + " " + shown(ROOT / "update.py")


def is_git():
    return (ROOT / ".git").exists()


def run_command(new):
    """The one step that updates this copy: the helper, or git for a git checkout."""
    if is_git():
        return "git -C {0} fetch --tags && git -C {0} checkout v{1}".format(shown(ROOT), new)
    return helper()


def notice(current, new):
    second = "skip: %s --skip" % helper()
    if not is_git():
        second = "turn on automatic updates: %s --auto on · %s" % (helper(), second)
    if not os.environ.get("NO_COLOR"):
        second = "\033[2m" + second + "\033[0m"
    return "USAP %s available (you have %s) · run: %s\n%s" % (new, current, run_command(new), second)


def tty():
    return all(stream is not None and stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr))


def quiet(state):
    """The automatic check is off here: no output, no request, no file written."""
    for name in ("USAP_NO_UPDATE_CHECK", "CI"):
        if os.environ.get(name, "").lower() not in ("", "0", "false"):
            return True
    return state.get("notify") is False or not tty()


def confirm(question, default):
    try:
        answer = input(question).strip().lower()
    except EOFError:
        return False
    return default if not answer else answer in ("y", "yes")


# --- verified install with one rollback copy ---

def backup_dir():
    return ROOT.parent / ("." + NAME + ".previous")


def prune():
    """This copy runs, so the rollback copy from the last update can go."""
    backup = backup_dir()
    if backup.is_dir() and not backup.is_symlink() and parse(installed_version()):
        shutil.rmtree(backup, ignore_errors=True)


def download(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    except Exception as exc:
        raise UpdateError("download failed: %s (%s)" % (path.name, exc)) from exc


def verify(archive, sums):
    want = ""
    for line in sums.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == archive.name:
            want = parts[0].lower()
    if not want:
        raise UpdateError("no checksum for %s in SHA256SUMS; nothing was installed" % archive.name)
    got = hashlib.sha256(archive.read_bytes()).hexdigest()
    if got != want:
        raise UpdateError(
            "checksum mismatch for %s (expected %s, got %s); nothing was installed" % (archive.name, want, got)
        )


def extract(archive, stage):
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if not (member.isfile() or member.isdir()) or member.name.startswith("/") or ".." in Path(member.name).parts:
                raise UpdateError("the release archive has an unsafe entry (%s); nothing was installed" % member.name)
        if hasattr(tarfile, "data_filter"):
            tar.extractall(stage, filter="data")
        else:
            tar.extractall(stage)


def install(new):
    """Download release <new>, verify it, then swap folders. Returns (ok, cause)."""
    if ROOT.is_symlink():
        return False, "%s is a symbolic link; it was not changed" % ROOT
    if is_git():
        return False, "%s is a git checkout; run: %s" % (ROOT, run_command(new))
    base = (os.environ.get("USAP_RELEASE_BASE") or DOWNLOAD % new).rstrip("/")
    temp = Path(tempfile.mkdtemp(prefix="usap-update."))
    stage = None
    try:
        archive, sums = temp / "usap.tar.gz", temp / "SHA256SUMS"
        download(base + "/usap.tar.gz", archive)
        download(base + "/SHA256SUMS", sums)
        verify(archive, sums)
        stage = Path(tempfile.mkdtemp(prefix="." + NAME + ".new.", dir=str(ROOT.parent)))
        extract(archive, stage)
        if installed_version(stage) != new:
            raise UpdateError("the download declares '%s', not %s; nothing was installed" % (installed_version(stage), new))
        backup = backup_dir()
        shutil.rmtree(backup, ignore_errors=True)  # never more than one rollback copy
        os.rename(ROOT, backup)
        try:
            os.rename(stage, ROOT)
        except BaseException:
            os.rename(backup, ROOT)
            raise
        stage = None
        return True, ""
    except Exception as exc:
        return False, str(exc) or exc.__class__.__name__
    finally:
        shutil.rmtree(temp, ignore_errors=True)
        if stage is not None:
            shutil.rmtree(stage, ignore_errors=True)


# --- command handlers ---

def cmd_update():
    state = load()
    notes = refresh(state)  # an explicit update always asks the API now
    if state.get("error"):
        print("USAP update check failed: %s" % state["error"], file=sys.stderr)
        return 1
    current, new = installed_version(), state.get("latest", "")
    if not is_newer(new, current):
        print("USAP %s is up to date." % current)
        return 0
    print("USAP %s → %s" % (current, new))
    for line in [line.strip() for line in notes.splitlines() if line.strip()][:3]:
        print("  " + (line if len(line) <= 120 else line[:119] + "…"))
    sys.stdout.flush()
    if is_git():
        print("This copy is a git checkout. Update it with: %s" % run_command(new), file=sys.stderr)
        return 1
    if tty() and not confirm("Install %s now? [Y/n] " % new, True):
        return 0
    ok, cause = install(new)
    if not ok:
        print("USAP update failed: %s" % cause, file=sys.stderr)
        return 1
    print("Updated USAP from %s to %s. New agent sessions load it." % (current, new))
    state = load()
    if tty() and state.get("auto") is not True and not state.get("asked"):
        state["auto"] = confirm("Install future updates automatically? [y/N] ", False)
        state["asked"] = True
        save(state)
    return 0


def cmd_check():
    state = load()
    if not within_day(state.get("checked_at")) or state.get("error"):
        refresh(state)
    if state.get("error"):
        print("USAP update check failed: %s" % state["error"], file=sys.stderr)
        return 1
    current, new = installed_version(), state.get("latest", "")
    if not is_newer(new, current):
        print("USAP %s is up to date." % current)
        return 0
    print("USAP %s available (you have %s) · run: %s" % (new, current, run_command(new)))
    if state.get("failed") == new:
        print("The automatic install of %s failed: %s" % (new, state.get("failure", "")), file=sys.stderr)
    return 10


def cmd_notice():
    state = load()
    if quiet(state):
        return 0
    current, new = installed_version(), state.get("latest", "")
    auto = state.get("auto") is True and not is_git()
    show = (
        is_newer(new, current)
        and state.get("skip") != new
        and not (auto and state.get("failed") != new)  # the background run installs it instead
        and not (state.get("shown") == new and within_day(state.get("shown_at")))
    )
    due = not within_day(state.get("checked_at"))
    if show:
        state.update(shown=new, shown_at=time.time())
    if due:
        state["checked_at"] = time.time()  # claim today's check before the background run starts
    if show or due:
        save(state)
    if show:
        print(notice(current, new), file=sys.stderr)
    if due:
        spawn()
    return 0


def spawn():
    """Run the check (and an opted-in install) detached, at low priority, off the startup path."""
    options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        options["creationflags"] = sum(
            getattr(subprocess, flag, 0)
            for flag in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP", "BELOW_NORMAL_PRIORITY_CLASS")
        )
    else:
        options["start_new_session"] = True
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "--background"], **options)


def cmd_background():
    if hasattr(os, "nice"):
        os.nice(10)
    state = load()
    refresh(state)
    current, new = installed_version(), state.get("latest", "")
    if state.get("auto") is not True or is_git() or not is_newer(new, current) or state.get("skip") == new:
        return 0
    ok, cause = install(new)
    log("automatic update to %s: %s" % (new, "installed" if ok else cause))
    if not ok:
        state = load()
        state.update(failed=new, failure=cause)  # the notice comes back for this version
        save(state)
    return 0


def cmd_skip():
    state = load()
    if not within_day(state.get("checked_at")) or state.get("error"):
        refresh(state)
    new = state.get("latest", "")
    if not is_newer(new, installed_version()):
        if state.get("error"):
            print("USAP update check failed: %s" % state["error"], file=sys.stderr)
            return 1
        print("No newer USAP release to skip.")
        return 0
    state["skip"] = new
    save(state)
    print("Skipped USAP %s. A newer release will be announced." % new)
    return 0


def cmd_rollback():
    backup = backup_dir()
    if backup.is_symlink() or not parse(installed_version(backup)):
        print("No rollback copy is available.", file=sys.stderr)
        return 1
    newer = installed_version()
    discard = ROOT.parent / ("." + NAME + ".discard")
    shutil.rmtree(discard, ignore_errors=True)
    os.rename(ROOT, discard)
    try:
        os.rename(backup, ROOT)
    except BaseException:
        os.rename(discard, ROOT)
        raise
    shutil.rmtree(discard, ignore_errors=True)
    if parse(newer):
        state = load()
        state["skip"] = newer  # so neither the notice nor an automatic update brings it back
        save(state)
    print("Rolled back USAP to %s; %s is skipped." % (installed_version(), newer))
    return 0


def cmd_auto(value):
    state = load()
    if value == "status":
        print("Automatic updates: %s" % ("on" if state.get("auto") is True else "off"))
        return 0
    if value == "on":
        state.update(auto=True, asked=True, checked_at=0)  # the next notice checks and installs
        state.pop("failed", None)
        save(state)
    else:
        remove(cache_dir() / "update.log")
        if state.get("notify") is False:
            save({"notify": False})
        else:
            remove(cache_dir() / "update.json")
            try:
                cache_dir().rmdir()
            except OSError:
                pass
    print("Automatic updates: %s" % value)
    return 0


def cmd_notify(value):
    state = load()
    if value != "status":
        state["notify"] = value == "on"
        save(state)
    print("Update notices: %s" % ("off" if state.get("notify") is False else "on"))
    return 0


def main(args):
    simple = {"--check": cmd_check, "--notice": cmd_notice, "--skip": cmd_skip,
              "--rollback": cmd_rollback, "--background": cmd_background}
    if args in (["-h"], ["--help"]):
        print(__doc__.strip())
        return 0
    if not args:
        handler = cmd_update
    elif len(args) == 1 and args[0] in simple:
        handler = simple[args[0]]
    elif len(args) == 2 and args[0] in ("--auto", "--notify") and args[1] in ("on", "off", "status"):
        value = args[1]
        handler = (lambda: cmd_auto(value)) if args[0] == "--auto" else (lambda: cmd_notify(value))
    else:
        print("usage: update.py [--check | --notice | --skip | --rollback | --auto on|off|status"
              " | --notify on|off|status]", file=sys.stderr)
        return 2
    automatic = handler in (cmd_notice, cmd_background)
    try:
        if handler not in (cmd_rollback, cmd_background):
            prune()
        return handler()
    except Exception as exc:
        if automatic:  # never noise from the automatic path
            if handler is cmd_background:
                try:
                    log("background check failed: %s" % exc)
                except Exception:
                    pass
            return 0
        print("USAP update failed: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
