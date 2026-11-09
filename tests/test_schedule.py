from __future__ import annotations

import datetime as dt
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("para_kb_schedule", ROOT / "scripts" / "para_kb_schedule.py")
sched = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sched)


def make_vault(tmp: Path, schedules: list[dict]) -> Path:
    (tmp / ".para-kb").mkdir()
    config = json.loads((ROOT / "templates" / "para-kb.config.json").read_text(encoding="utf-8"))
    config["schedules"] = schedules
    (tmp / ".para-kb" / "config.json").write_text(json.dumps(config), encoding="utf-8")
    return tmp


def run(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = sched.main(argv)
    return rc, buf.getvalue()


class SlotMathTest(unittest.TestCase):
    def s(self, **kw):
        return sched.schedules({"schedules": [dict(id="x", **kw)]})[0]

    def test_weekly_slot_is_most_recent_weekday_time(self) -> None:
        s = self.s(cadence="weekly", weekday="sun", time="20:30")
        mon = dt.datetime(2026, 11, 9, 9, 0)  # Monday
        self.assertEqual(sched.last_slot(s, mon), dt.datetime(2026, 11, 8, 20, 30))
        sun_before = dt.datetime(2026, 11, 8, 20, 0)
        self.assertEqual(sched.last_slot(s, sun_before), dt.datetime(2026, 11, 1, 20, 30))

    def test_daily_and_monthly(self) -> None:
        d = self.s(cadence="daily", time="06:30")
        self.assertEqual(sched.last_slot(d, dt.datetime(2026, 11, 9, 6, 0)), dt.datetime(2026, 11, 8, 6, 30))
        m = self.s(cadence="monthly", day=1, time="09:00")
        self.assertEqual(sched.last_slot(m, dt.datetime(2026, 11, 1, 8, 0)), dt.datetime(2026, 10, 1, 9, 0))

    def test_bad_time_and_cadence_rejected(self) -> None:
        with self.assertRaises(sched.ScheduleError):
            self.s(time="25:00")
        with self.assertRaises(sched.ScheduleError):
            self.s(cadence="hourly")

    def test_due_respects_last_run_grace_and_disabled(self) -> None:
        s = self.s(cadence="weekly", weekday="sun", time="20:30")
        now = dt.datetime(2026, 11, 8, 21, 0)  # 30 minutes after the slot
        self.assertTrue(sched.is_due(s, {}, now, with_grace=False)[0])
        self.assertFalse(sched.is_due(s, {}, now, with_grace=True)[0])  # timer may still be running
        self.assertFalse(sched.is_due(s, {"last_run": "2026-11-08T20:31:00"}, now, with_grace=False)[0])
        off = self.s(cadence="weekly", weekday="sun", time="20:30", enabled=False)
        self.assertFalse(sched.is_due(off, {}, now, with_grace=False)[0])


class CliTest(unittest.TestCase):
    def test_hook_is_silent_without_config_or_when_not_due(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = run(["--vault", tmp, "due", "--hook"])
            self.assertEqual((rc, out), (0, ""))
            make_vault(Path(tmp), [])
            rc, out = run(["--vault", tmp, "due", "--hook"])
            self.assertEqual((rc, out), (0, ""))

    def test_hook_reports_overdue_once_and_mark_clears_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_vault(Path(tmp), [{"id": "dream", "task": "kb-dream", "cadence": "daily",
                                           "time": "00:00", "grace_minutes": 0}])
            # a brand-new schedule is not born overdue
            self.assertEqual(run(["--vault", tmp, "due", "--hook"])[1], "")
            state_p = root / ".para-kb/state/schedules.json"
            st = json.loads(state_p.read_text())
            st["dream"]["first_seen"] = "2026-01-01T00:00:00+00:00"
            state_p.write_text(json.dumps(st))
            rc, out = run(["--vault", tmp, "due", "--hook"])
            self.assertEqual(rc, 0)
            payload = json.loads(out)
            self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")
            self.assertIn("kb-dream", payload["hookSpecificOutput"]["additionalContext"])
            self.assertEqual(run(["--vault", tmp, "due", "--hook"])[1], "")  # reminded once per slot
            (root / "r.md").write_text("report", encoding="utf-8")
            rc, _ = run(["--vault", tmp, "mark", "dream", "--status", "ok", "--report", str(root / "r.md")])
            self.assertEqual(rc, 0)
            state = json.loads(state_p.read_text())
            self.assertEqual(state["dream"]["last_status"], "ok")
            self.assertEqual(state["dream"]["last_report"], "r.md")
            self.assertEqual(run(["--vault", tmp, "due", "--json"])[1].strip(), "[]")

    def test_hook_never_fails_on_bad_config_or_state(self) -> None:
        bad_configs = [[{"id": "dream", "day": "x"}], [{"id": "../x"}], ["notadict"], "notalist",
                       [{"id": "dream", "grace_minutes": None}]]
        for sch in bad_configs:
            with self.subTest(sch=sch), tempfile.TemporaryDirectory() as tmp:
                make_vault(Path(tmp), sch)
                self.assertEqual(run(["--vault", tmp, "due", "--hook"]), (0, ""))
        with tempfile.TemporaryDirectory() as tmp:
            root = make_vault(Path(tmp), [{"id": "dream"}])
            (root / ".para-kb/state").mkdir(parents=True)
            (root / ".para-kb/state/schedules.json").write_text("[]")
            self.assertEqual(run(["--vault", tmp, "due", "--hook"])[0], 0)
            (root / ".para-kb/config.json").write_text("{not json")
            self.assertEqual(run(["--vault", tmp, "due", "--hook"]), (0, ""))

    def test_failed_run_stays_due_after_retry_window(self) -> None:
        s = sched.schedules({"schedules": [{"id": "x", "cadence": "weekly", "weekday": "sun", "time": "20:30"}]})[0]
        now = dt.datetime(2026, 11, 9, 9, 0)
        recent = {"last_run": "2026-11-09T08:00:00", "last_status": "failed"}
        old = {"last_run": "2026-11-08T21:00:00", "last_status": "failed"}
        self.assertFalse(sched.is_due(s, recent, now, with_grace=False)[0])
        self.assertTrue(sched.is_due(s, old, now, with_grace=False)[0])
        self.assertTrue(sched.is_due(s, {"last_run": "2026-11-08T21:00:00Z", "last_status": "unverified"}, now, False)[0])

    def test_prompt_points_at_skill_and_mark(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_vault(Path(tmp), [{"id": "dream"}])
            rc, out = run(["--vault", tmp, "prompt", "dream"])
            self.assertEqual(rc, 0)
            self.assertIn("skills/kb-dream/SKILL.md", out)
            self.assertIn("mark dream --status ok", out)

    def test_runner_argv_for_each_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pf = root / "p.txt"
            pf.write_text("hello", encoding="utf-8")
            base = {"id": "d", "runner_path": "/usr/bin/true"}
            c = sched.runner_argv(root, sched.schedules({"schedules": [dict(base, model="sonnet")]})[0], pf)
            self.assertIn("-p", c)
            self.assertIn("acceptEdits", c)
            self.assertEqual(c[c.index("--model") + 1], "sonnet")
            x = sched.runner_argv(root, sched.schedules({"schedules": [dict(base, runner="codex")]})[0], pf)
            self.assertIn("exec", x)
            self.assertEqual(x[-1], "hello")
            cmd = sched.runner_argv(root, sched.schedules({"schedules": [dict(
                base, runner="command", command="mywrap {prompt_file} {id}")]})[0], pf)
            self.assertEqual(cmd, ["mywrap", str(pf), "d"])

    def test_install_print_renders_all_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            make_vault(Path(tmp), [{"id": "dream", "cadence": "weekly", "weekday": "sun", "time": "20:30"}])
            rc, out = run(["--vault", tmp, "install", "dream", "--target", "print"])
            self.assertEqual(rc, 0)
            self.assertIn("<key>Weekday</key><integer>0</integer>", out)  # launchd Sunday = 0
            self.assertIn("30 20 * * 0 PATH=", out)  # cron
            self.assertIn("/SC WEEKLY /D SUN /ST 20:30", out)
            self.assertNotIn("&", out.split("# Task Scheduler")[1])


if __name__ == "__main__":
    unittest.main()
