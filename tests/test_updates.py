"""Offline checks for update.py. Releases are local files; no test uses the network."""

import hashlib
import importlib.util
import io
import json
import os
import stat
import tarfile
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("usap_update", ROOT / "update.py")
update = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update)

CURRENT = "1.8.0"


def skill_text(version):
    return "---\nname: ultraterm-subagent-protocol\nmetadata:\n  version: %s\n---\n" % version


class UpdateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.skill = self.base / "skills" / update.NAME
        self.skill.mkdir(parents=True)
        (self.skill / "SKILL.md").write_text(skill_text(CURRENT), encoding="utf-8")
        self.tmp = self.base / "tmp"
        self.tmp.mkdir()
        for patch in (
            mock.patch.object(update, "ROOT", self.skill),
            mock.patch.object(tempfile, "tempdir", str(self.tmp)),
            mock.patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.base / "cache"), "NO_COLOR": "1"}),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        for name in ("USAP_UPDATE_API", "USAP_RELEASE_BASE", "USAP_NO_UPDATE_CHECK", "CI"):
            os.environ.pop(name, None)
        self.spawned = mock.patch.object(update, "spawn").start()
        self.addCleanup(mock.patch.stopall)

    # helpers

    def api(self, version, notes="", **flags):
        path = self.base / "release.json"
        record = {"tag_name": "v" + version, "draft": False, "prerelease": False, "body": notes}
        record.update(flags)
        path.write_text(json.dumps(record), encoding="utf-8")
        os.environ["USAP_UPDATE_API"] = path.as_uri()

    def release(self, version, corrupt=False):
        folder = self.base / ("release-" + version)
        folder.mkdir()
        (folder / "SKILL.md").write_text(skill_text(version), encoding="utf-8")
        archive = folder / "usap.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(folder / "SKILL.md", arcname="SKILL.md")
        digest = "0" * 64 if corrupt else hashlib.sha256(archive.read_bytes()).hexdigest()
        (folder / "SHA256SUMS").write_text(digest + "  usap.tar.gz\n", encoding="utf-8")
        os.environ["USAP_RELEASE_BASE"] = folder.as_uri()

    def run_cli(self, *args, tty=True, answers=()):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(update, "tty", return_value=tty), mock.patch(
            "builtins.input", side_effect=list(answers)
        ) as prompt, redirect_stdout(out), redirect_stderr(err):
            code = update.main(list(args))
        self.prompts = [call.args[0] for call in prompt.call_args_list]
        return code, out.getvalue(), err.getvalue()

    def state_file(self):
        return self.base / "cache" / "usap" / "update.json"

    def backup(self):
        return self.skill.parent / ("." + update.NAME + ".previous")

    def skills_entries(self):
        return sorted(path.name for path in self.skill.parent.iterdir())

    # version comparison

    def test_only_strictly_newer_stable_versions_count(self):
        for candidate, current, newer in (
            ("1.8.1", CURRENT, True),
            ("1.10.0", "1.9.9", True),
            ("2.0.0", CURRENT, True),
            (CURRENT, CURRENT, False),
            ("1.7.9", CURRENT, False),
            ("1.9.0-rc.1", CURRENT, False),
            ("v1.9.0", CURRENT, False),
            ("garbage", CURRENT, False),
            ("", CURRENT, False),
            ("1.9.0", "dev", False),
        ):
            self.assertEqual(update.is_newer(candidate, current), newer, (candidate, current))

    def test_prerelease_and_draft_records_are_ignored(self):
        self.api("1.9.0", prerelease=True)
        self.assertEqual(update.fetch_latest(), ("", ""))
        self.api("1.9.0", draft=True)
        self.assertEqual(update.fetch_latest(), ("", ""))
        self.api("1.9.0", "notes")
        self.assertEqual(update.fetch_latest(), ("1.9.0", "notes"))

    def test_request_is_anonymous_with_the_fixed_user_agent(self):
        seen = []

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_urlopen(request, timeout):
            seen.append((request, timeout))
            return Response(b'{"tag_name": "v1.9.0"}')

        with mock.patch.object(update.urllib.request, "urlopen", fake_urlopen):
            self.assertEqual(update.fetch_latest()[0], "1.9.0")
        request, timeout = seen[0]
        self.assertEqual(request.full_url, update.API)
        self.assertTrue(update.API.endswith("/repos/michael-berardi/ultraterm-subagent-protocol/releases/latest"))
        self.assertEqual(request.get_method(), "GET")
        self.assertIsNone(request.data)
        self.assertEqual({k.lower() for k in request.headers}, {"user-agent", "accept"})
        self.assertEqual(request.get_header("User-agent"), "usap-update-check")
        self.assertLessEqual(timeout, 4)

    # cache, frequency and failures

    def test_notice_checks_in_the_background_at_most_daily(self):
        self.api("1.9.0")
        self.assertEqual(self.run_cli("--notice"), (0, "", ""))  # nothing known yet; check starts detached
        self.assertEqual(self.spawned.call_count, 1)
        self.assertEqual(self.run_cli("--notice")[2], "")
        self.assertEqual(self.spawned.call_count, 1, "a second notice within 24 h must not check again")
        self.assertEqual(self.run_cli("--background")[0], 0)
        self.assertEqual(json.loads(self.state_file().read_text())["latest"], "1.9.0")
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(self.state_file().stat().st_mode), 0o600)
        state = update.load()
        state["checked_at"] = time.time() - update.DAY - 1
        update.save(state)
        self.run_cli("--notice")
        self.assertEqual(self.spawned.call_count, 2)

    def test_failure_is_recorded_with_its_cause_and_never_printed_by_the_notice(self):
        os.environ["USAP_UPDATE_API"] = (self.base / "missing.json").as_uri()
        self.assertEqual(self.run_cli("--background")[0], 0)
        self.assertIn("cannot read the release API", update.load()["error"])
        self.assertEqual(self.run_cli("--notice"), (0, "", ""))
        code, out, err = self.run_cli("--check")
        self.assertEqual(code, 1)
        self.assertIn("USAP update check failed: cannot read the release API", err)
        self.api("1.9.0")
        self.assertEqual(self.run_cli("--check")[0], 10, "an explicit check retries a recorded failure once")

    def test_check_exit_codes_and_report(self):
        self.api(CURRENT)
        self.assertEqual(self.run_cli("--check")[:2], (0, "USAP 1.8.0 is up to date.\n"))
        update.save({})
        self.api("1.9.0")
        code, out, err = self.run_cli("--check")
        self.assertEqual(code, 10)
        self.assertTrue(out.startswith("USAP 1.9.0 available (you have 1.8.0) · run: python"))
        self.assertTrue(out.rstrip().endswith("update.py"))

    # notice text, placement, skip and frequency

    def test_notice_is_two_lines_on_stderr_once_per_day_per_version(self):
        update.save({"checked_at": time.time(), "latest": "1.9.0"})
        code, out, err = self.run_cli("--notice")
        self.assertEqual((code, out), (0, ""), "the notice never goes to stdout")
        first, second = err.splitlines()
        helper = update.helper()
        self.assertEqual(first, "USAP 1.9.0 available (you have 1.8.0) · run: " + helper)
        self.assertEqual(second, "turn on automatic updates: %s --auto on · skip: %s --skip" % (helper, helper))
        self.assertEqual(self.run_cli("--notice")[2], "")
        state = update.load()
        state["shown_at"] = time.time() - update.DAY - 1
        update.save(state)
        self.assertIn("USAP 1.9.0 available", self.run_cli("--notice")[2])
        self.spawned.assert_not_called()

    def test_skipped_version_is_silent_and_a_newer_one_notifies(self):
        self.api("1.9.0")
        self.assertEqual(self.run_cli("--skip")[0], 0)
        self.assertEqual(update.load()["skip"], "1.9.0")
        self.assertEqual(self.run_cli("--notice")[2], "")
        update.save(dict(update.load(), latest="1.10.0"))
        self.assertIn("USAP 1.10.0 available", self.run_cli("--notice")[2])

    def test_silent_and_offline_in_ci_opt_out_config_off_and_non_tty(self):
        self.api("1.9.0")
        cases = ({"CI": "true"}, {"USAP_NO_UPDATE_CHECK": "1"})
        for env in cases:
            with mock.patch.dict(os.environ, env):
                self.assertEqual(self.run_cli("--notice"), (0, "", ""), env)
        self.assertEqual(self.run_cli("--notice", tty=False), (0, "", ""))
        self.spawned.assert_not_called()
        self.assertFalse(self.state_file().exists(), "a silent run writes nothing")
        self.assertEqual(self.run_cli("--notify", "off")[1], "Update notices: off\n")
        update.save(dict(update.load(), latest="1.9.0"))
        self.assertEqual(self.run_cli("--notice"), (0, "", ""))
        self.spawned.assert_not_called()
        self.assertEqual(self.run_cli("--notify", "on")[1], "Update notices: on\n")
        self.assertIn("1.9.0 available", self.run_cli("--notice")[2])

    # auto-update

    def test_auto_is_off_by_default_and_persists(self):
        self.assertEqual(self.run_cli("--auto", "status")[1], "Automatic updates: off\n")
        self.run_cli("--auto", "on")
        self.assertEqual(self.run_cli("--auto", "status")[1], "Automatic updates: on\n")
        self.assertIs(update.load()["auto"], True)
        self.run_cli("--auto", "off")
        self.assertEqual(self.run_cli("--auto", "status")[1], "Automatic updates: off\n")

    def test_auto_install_runs_in_the_background_and_a_failure_falls_back_to_the_notice(self):
        self.api("1.9.0")
        self.release("1.9.0", corrupt=True)
        update.save({"checked_at": time.time(), "latest": "1.9.0"})
        self.run_cli("--auto", "on")
        self.assertEqual(self.run_cli("--notice"), (0, "", ""), "with auto on the notice waits for the install")
        self.assertEqual(self.spawned.call_count, 1, "--auto on makes the next notice check")
        self.assertEqual(self.run_cli("--background")[0], 0)
        self.assertEqual(update.installed_version(self.skill), CURRENT, "a failed install keeps the current copy")
        state = update.load()
        self.assertEqual(state["failed"], "1.9.0")
        self.assertIn("checksum mismatch", state["failure"])
        self.assertIn("checksum mismatch", (self.base / "cache" / "usap" / "update.log").read_text())
        self.assertIn("USAP 1.9.0 available", self.run_cli("--notice")[2])

        os.environ.pop("USAP_RELEASE_BASE")
        self.base.joinpath("release-1.9.0").rename(self.base / "corrupt")
        self.release("1.9.0")
        update.save(dict(update.load(), checked_at=0))
        self.assertEqual(self.run_cli("--background")[0], 0)
        self.assertEqual(update.installed_version(self.skill), "1.9.0")
        self.assertIn("automatic update to 1.9.0: installed", (self.base / "cache" / "usap" / "update.log").read_text())

    def test_interactive_update_asks_once_and_remembers_no(self):
        self.api("1.9.0", "First note\nSecond note")
        self.release("1.9.0")
        code, out, err = self.run_cli(answers=["", "n"])
        self.assertEqual(code, 0, err)
        self.assertEqual(self.prompts, ["Install 1.9.0 now? [Y/n] ", "Install future updates automatically? [y/N] "])
        self.assertIn("USAP 1.8.0 → 1.9.0\n  First note\n  Second note\n", out)
        self.assertIn("Updated USAP from 1.8.0 to 1.9.0.", out)
        self.assertIs(update.load()["auto"], False)
        os.environ.pop("USAP_RELEASE_BASE")
        self.release("1.10.0")
        self.api("1.10.0")
        self.assertEqual(self.run_cli(answers=["y"])[0], 0)
        self.assertEqual(self.prompts, ["Install 1.10.0 now? [Y/n] "], "never asked again after no")

    def test_non_tty_update_installs_without_questions_even_when_checks_are_off(self):
        self.api("1.9.0")
        self.release("1.9.0")
        with mock.patch.dict(os.environ, {"CI": "1", "USAP_NO_UPDATE_CHECK": "1"}):
            code, out, err = self.run_cli(tty=False)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.prompts, [])
        self.assertEqual(update.installed_version(self.skill), "1.9.0")

    def test_declined_update_changes_nothing(self):
        self.api("1.9.0")
        self.release("1.9.0")
        self.assertEqual(self.run_cli(answers=["n"])[0], 0)
        self.assertEqual(update.installed_version(self.skill), CURRENT)

    # install safety and debris

    def test_checksum_mismatch_refuses_and_leaves_no_temp_files(self):
        self.api("1.9.0")
        self.release("1.9.0", corrupt=True)
        code, out, err = self.run_cli(tty=False)
        self.assertEqual(code, 1)
        self.assertIn("checksum mismatch for usap.tar.gz", err)
        self.assertEqual(update.installed_version(self.skill), CURRENT)
        self.assertEqual(self.skills_entries(), [update.NAME])
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_unsafe_archive_entries_are_refused(self):
        folder = self.base / "evil"
        folder.mkdir()
        archive = folder / "usap.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            info = tarfile.TarInfo("../escape")
            info.size = 0
            tar.addfile(info, io.BytesIO(b""))
        (folder / "SHA256SUMS").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  usap.tar.gz\n")
        os.environ["USAP_RELEASE_BASE"] = folder.as_uri()
        ok, cause = update.install("1.9.0")
        self.assertFalse(ok)
        self.assertIn("unsafe entry", cause)
        self.assertFalse((self.skill.parent.parent / "escape").exists())
        self.assertEqual(self.skills_entries(), [update.NAME])

    def test_one_rollback_copy_pruned_after_the_next_run_and_rollback_restores(self):
        self.release("1.9.0")
        self.assertEqual(update.install("1.9.0"), (True, ""))
        self.assertEqual(update.installed_version(self.backup()), CURRENT)
        os.environ.pop("USAP_RELEASE_BASE")
        self.release("1.10.0")
        self.assertEqual(update.install("1.10.0"), (True, ""))
        self.assertEqual(self.skills_entries(), ["." + update.NAME + ".previous", update.NAME])
        self.assertEqual(update.installed_version(self.backup()), "1.9.0", "never more than one rollback copy")
        self.assertEqual(list(self.tmp.iterdir()), [])

        code, out, err = self.run_cli("--rollback")
        self.assertEqual(code, 0, err)
        self.assertEqual(update.installed_version(self.skill), "1.9.0")
        self.assertEqual(update.load()["skip"], "1.10.0", "a rolled-back version is not offered again")
        self.assertEqual(self.skills_entries(), [update.NAME])
        self.assertEqual(self.run_cli("--rollback")[0], 1)

        os.environ.pop("USAP_RELEASE_BASE")
        self.release("1.11.0")
        self.assertTrue(update.install("1.11.0")[0])
        self.api("1.11.0")
        self.assertEqual(self.run_cli("--check")[0], 0)
        self.assertEqual(self.skills_entries(), [update.NAME], "the next run removes the rollback copy")

    def test_git_checkout_is_never_swapped_and_gets_the_git_command(self):
        (self.skill / ".git").mkdir()
        self.api("1.9.0")
        self.release("1.9.0")
        code, out, err = self.run_cli(tty=False)
        self.assertEqual(code, 1)
        self.assertIn("git checkout", err)
        self.assertIn("fetch --tags && git -C", err)
        self.assertEqual(update.installed_version(self.skill), CURRENT)
        update.save({"checked_at": time.time(), "latest": "1.9.0", "auto": True})
        notice = self.run_cli("--notice")[2]
        self.assertIn("checkout v1.9.0", notice.splitlines()[0])
        self.assertNotIn("--auto on", notice)

    def test_log_is_bounded(self):
        log = self.base / "cache" / "usap" / "update.log"
        log.parent.mkdir(parents=True)
        log.write_bytes(b"old line\n" * (update.LOG_LIMIT // 4))
        update.log("newest")
        data = log.read_bytes()
        self.assertLessEqual(len(data), update.LOG_LIMIT)
        self.assertTrue(data.startswith(b"old line\n"), "the log is cut at a line boundary")
        self.assertTrue(data.rstrip().endswith(b"newest"))

    def test_auto_off_removes_the_cache_and_log(self):
        self.run_cli("--auto", "on")
        update.log("entry")
        self.run_cli("--auto", "off")
        self.assertFalse((self.base / "cache" / "usap").exists())
        self.run_cli("--notify", "off")
        self.run_cli("--auto", "off")
        self.assertEqual(update.load(), {"notify": False}, "the notice opt-out survives --auto off")


if __name__ == "__main__":
    unittest.main()
