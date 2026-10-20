#!/usr/bin/env python3
"""锁住评审里会让 Claude 走错路或真点出去的契约。不启动浏览器。"""
import contextlib
import io
import re
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply  # noqa: E402
import detail  # noqa: E402
import filter  # noqa: E402
import login  # noqa: E402
from _lib import (CookieReadError, config_gaps, deadline_expired, editor_text,
                  history_text, parse_salary, profile_has_login, read_wt2_expiry,
                  rotate_existing)  # noqa: E402


def parttime_cfg(**over):
    cfg = {"jobType": "1903", "city": "100010000", "salaryFloorDay": 300, "hoursPerDay": 4,
           "blacklistCompanies": [], "blacklistKeywords": ["外包"],
           "includeTitleKeywords": filter.DEFAULT_INCLUDE,
           "excludeTitleKeywords": filter.DEFAULT_EXCLUDE}
    cfg.update(over)
    return cfg


def mkjob(i=1, title="前端开发", company="X公司", salary="40-70元/时", **over):
    j = {"id": f"i{i}", "job": title, "company": company, "salary": salary,
         "salaryParsed": parse_salary(salary), "jobValid": True, "deliveredBefore": False,
         "goldHunter": False, "jobType": 6, "area": "杭州·西湖", "daysPerWeek": "",
         "tags": [], "skills": [], "industry": "", "link": f"https://www.zhipin.com/job_detail/i{i}.html"}
    j.update(over)
    return j

SKILL = Path(__file__).resolve().parents[2] / "SKILL.md"
CHROME_EPOCH = 11644473600


def chrome_expiry(unix_ts: float) -> int:
    return int((unix_ts + CHROME_EPOCH) * 1_000_000)


def write_cookie_db(profile: Path, rows: list[tuple]) -> None:
    db = profile / "Default" / "Cookies"
    db.parent.mkdir(parents=True)
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE cookies (host_key TEXT, name TEXT, expires_utc INTEGER, is_persistent INTEGER)"
    )
    con.executemany(
        "INSERT INTO cookies (host_key, name, expires_utc, is_persistent) VALUES (?, ?, ?, ?)",
        rows,
    )
    con.commit()
    con.close()


class SkillContracts(unittest.TestCase):
    def test_greeting_refs_resolve_from_skill_dir(self):
        text = SKILL.read_text(encoding="utf-8")
        for rel in (
            "../gen-greeting/references/greeting-principles.md",
            "../gen-greeting/references/greeting-templates.md",
        ):
            self.assertIn(rel, text)
            self.assertTrue((SKILL.parent / rel).resolve().is_file(), rel)
        self.assertNotIn("references/greeting-principles.md", text.replace(
            "../gen-greeting/references/greeting-principles.md", ""))

    def test_skill_does_not_teach_dead_inactive_filter_or_wrong_timeout(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertNotIn("HR 活跃超", text)
        self.assertIn("10 分钟超时", text)
        self.assertNotIn("5 分钟超时", text)
        self.assertNotIn("playwright install chromium", text)
        search = Path(__file__).resolve().parent / "search.py"
        self.assertNotIn("无头模式", search.read_text(encoding="utf-8"))


class LoginCheck(unittest.TestCase):
    def test_valid_wt2_without_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp)
            write_cookie_db(profile, [(
                ".zhipin.com", "wt2", chrome_expiry(time.time() + 86400), 1,
            )])
            self.assertIsNotNone(read_wt2_expiry(profile))
            self.assertTrue(profile_has_login(profile))

    def test_expired_or_missing_is_not_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp)
            write_cookie_db(profile, [(
                ".zhipin.com", "wt2", chrome_expiry(time.time() - 10), 1,
            )])
            self.assertFalse(profile_has_login(profile))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(profile_has_login(Path(tmp)))

    def test_unreadable_db_is_not_reported_as_logged_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp)
            db = profile / "Default" / "Cookies"
            db.parent.mkdir(parents=True)
            db.write_text("not a sqlite database", encoding="utf-8")
            with self.assertRaises(CookieReadError):
                profile_has_login(profile)

    def test_check_only_does_not_call_launch(self):
        def boom(*_a, **_k):
            raise AssertionError("launched")

        orig_launch, orig_pw, orig_has = login.launch, login.sync_pw, login.profile_has_login
        login.launch = boom
        login.sync_pw = boom
        login.profile_has_login = lambda: True
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(login.check_only(), 0)
        finally:
            login.launch, login.sync_pw, login.profile_has_login = orig_launch, orig_pw, orig_has


class ParseSalary(unittest.TestCase):
    def test_monthly_k_unchanged(self):
        sp = parse_salary("25-50K·16薪")
        self.assertEqual((sp["unit"], sp["minK"], sp["maxK"], sp["months"]), ("K", 25, 50, 16))
        self.assertEqual(sp["annualMaxK"], 800)

    def test_parttime_units_no_longer_null(self):
        # 2026-10-20 事故：160/160 条兼职岗 parse 为 null，硬过滤形同虚设
        self.assertEqual(parse_salary("40-70元/时"), {"unit": "时", "min": 40, "max": 70})
        self.assertEqual(parse_salary("200-300元/天"), {"unit": "天", "min": 200, "max": 300})
        self.assertEqual(parse_salary("700-800元/周"), {"unit": "周", "min": 700, "max": 800})
        self.assertEqual(parse_salary("3000-5000元/月"), {"unit": "月", "min": 3000, "max": 5000})

    def test_single_value_and_unknown(self):
        self.assertEqual(parse_salary("200元/天"), {"unit": "天", "min": 200, "max": 200})
        self.assertIsNone(parse_salary("面议"))
        self.assertIsNone(parse_salary(""))


class ConfigGaps(unittest.TestCase):
    def test_missing_headed_is_listed_not_masked_by_defaults(self):
        missing, ignored = config_gaps({"jobType": "", "keywords": ["前端"]})
        self.assertEqual(missing, ["headed"])
        self.assertEqual(ignored, [])

    def test_parttime_requires_asked_fields(self):
        missing, _ = config_gaps({"headed": True, "jobType": "1903"})
        self.assertEqual(sorted(missing), ["hoursPerDay", "salaryFloorDay"])
        missing, _ = config_gaps({"headed": False, "jobType": "1903", "hoursPerDay": 4, "salaryFloorDay": 300})
        self.assertEqual(missing, [])

    def test_dead_skipinactive_is_ignored(self):
        missing, ignored = config_gaps({"headed": True, "jobType": "", "skipInactiveDays": 7})
        self.assertEqual((missing, ignored), ([], ["skipInactiveDays"]))


class ScreenJobs(unittest.TestCase):
    def test_hourly_floor_uses_configured_hours_per_day(self):
        # 300 元/天 ÷ 4h = 75 元/时，85% 硬切线 63.75：上限 60 不过线，上限 70 过线
        cands, boundary, dropped, stats = filter.screen_jobs(
            [mkjob(1, company="甲", salary="40-60元/时"), mkjob(2, company="乙", salary="40-70元/时")],
            parttime_cfg())
        self.assertEqual([b["id"] for b in boundary], ["i1"])
        self.assertEqual(boundary[0]["boundaryReasons"], ["below_floor"])
        self.assertTrue(boundary[0]["belowFloor"])
        self.assertEqual([c["id"] for c in cands], ["i2"])
        self.assertEqual(cands[0]["hourlyMax"], 70)
        self.assertEqual(cands[0]["dayMax"], 280)  # 时薪 × 4h

    def test_weekly_converts_via_default_days_per_week(self):
        _, boundary, _, _ = filter.screen_jobs([mkjob(1, salary="700-800元/周")], parttime_cfg())
        # 800/5 天/4h = 40 元/时 → 160 元/天 < 255 切线：与 2026-10-20 寰亚结论一致（进边界不硬丢）
        self.assertEqual(boundary[0]["boundaryReasons"], ["below_floor"])

    def test_wide_range_and_hourly_cap_go_to_boundary(self):
        _, boundary, _, _ = filter.screen_jobs(
            [mkjob(1, company="甲", salary="40-120元/时"), mkjob(2, company="乙", salary="150-300元/时")],
            parttime_cfg())
        self.assertEqual(boundary[0]["boundaryReasons"], ["wide_range"])
        self.assertEqual(boundary[1]["boundaryReasons"], ["hourly_too_high"])

    def test_gates_blacklist_title_duplicate(self):
        jobs = [
            mkjob(1, title="前端", company="外包科技"),
            mkjob(2, title="少儿编程老师", company="A教育"),
            mkjob(3, title="销售专员"),
            mkjob(4, title="Java后端"),
            mkjob(5, title="前端", company="B公司"),
            mkjob(6, title="前端", company="B公司"),
        ]
        cands, _, dropped, stats = filter.screen_jobs(jobs, parttime_cfg())
        self.assertEqual([c["id"] for c in cands], ["i5"])
        reasons = {d["id"]: d["reason"].split(":")[0] for d in dropped}
        self.assertEqual(reasons["i1"], "blacklist_keyword")
        self.assertEqual(reasons["i2"], "title_excluded")
        self.assertEqual(reasons["i3"], "title_excluded")
        self.assertEqual(reasons["i4"], "title_not_dev")
        self.assertEqual(reasons["i6"], "duplicate")

    def test_delivered_hunter_invalid_dropped_without_scoring(self):
        jobs = [mkjob(1, deliveredBefore=True), mkjob(2, goldHunter=True), mkjob(3, jobValid=False)]
        cands, boundary, dropped, _ = filter.screen_jobs(jobs, parttime_cfg())
        self.assertEqual((cands, boundary), ([], []))
        self.assertEqual([d["reason"] for d in dropped], ["delivered_7d", "hunter", "job_invalid"])

    def test_missing_config_refuses_instead_of_defaulting_8h(self):
        # hoursPerDay 必须问用户（用户反馈），脚本不得按 8 小时默认折算
        cfg = parttime_cfg()
        del cfg["hoursPerDay"]
        p = Path(__file__).resolve().parent / "filter.py"
        text = p.read_text(encoding="utf-8")
        self.assertIn("CONFIG_MISSING", text)
        self.assertIn("不得默认 8 小时", text)


class DetailExtract(unittest.TestCase):
    def test_terms_and_hr_activity_line_match(self):
        text = "前端开发\nHR·王女士\n本周活跃\n工作周期：每周3-4天\n结算方式：月结\n完善在线简历"
        self.assertEqual(detail.extract_hr_activity(text), "本周活跃")
        terms = detail.extract_terms(text)
        self.assertEqual(terms["工作周期"], "每周3-4天")
        self.assertEqual(terms["结算方式"], "月结")
        self.assertNotIn("招聘截止", terms)

    def test_online_resume_button_is_not_activity(self):
        # 「完善在线简历」含「在线」二字，不能被当成活跃时间（2026-10-19 教训）
        self.assertIsNone(detail.extract_hr_activity("完善在线简历\n工作周期：每周2天"))


class RotateExisting(unittest.TestCase):
    def test_same_name_file_is_rotated_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "screen-2026-10-20.json"
            p.write_text('{"old": true}', encoding="utf-8")
            rotated = rotate_existing(p)
            self.assertIsNotNone(rotated)
            self.assertTrue(re.search(r"-\d{4}\.json$", Path(rotated).name))
            assert rotated is not None
            self.assertEqual(Path(rotated).read_text(encoding="utf-8"), '{"old": true}')
            self.assertFalse(p.exists())

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(rotate_existing(Path(tmp) / "nope.json"))


class HistoryText(unittest.TestCase):
    class FakePage:
        def evaluate(self, script):
            if "contenteditable" in script:
                return "打了一半没发出去"
            return "历史消息\n打了一半没发出去"

    def test_editor_text_excluded_from_history(self):
        hist = history_text(self.FakePage())
        self.assertIn("历史消息", hist)
        self.assertNotIn("打了一半没发出去", hist)
        self.assertEqual(editor_text(self.FakePage()), "打了一半没发出去")

    def test_apply_validates_against_history_not_body(self):
        # 2026-10-20 事故专档 4.1：输入框残留文字不得被校验成已发送
        src = (Path(__file__).resolve().parent / "apply.py").read_text(encoding="utf-8")
        self.assertIn("history_text(chat_page)", src)
        self.assertNotIn("snippet in body_text", src)


class DeadlineRules(unittest.TestCase):
    def test_deadline_expired_parser(self):
        self.assertTrue(deadline_expired("时间：2026-12-18", today="2027-01-01"))
        self.assertFalse(deadline_expired("时间：2026-12-18", today="2026-10-20"))
        self.assertTrue(deadline_expired("2026年5月31日", today="2026-10-20"))
        self.assertIsNone(deadline_expired("长期有效"))

    def test_filter_tags_expired_deadline_from_known_details(self):
        known = {"i1": {"deadline": "时间：2026-08-25", "expired": True, "hrActivity": "2月内活跃"}}
        cands, _, _, _ = filter.screen_jobs([mkjob(1)], parttime_cfg(), known_details=known)
        self.assertEqual(cands[0]["deadline"], "时间：2026-08-25")
        self.assertTrue(cands[0]["deadlineExpired"])
        self.assertEqual(cands[0]["hrActivity"], "2月内活跃")

    def test_detail_prints_deadline_expired_line(self):
        src = (Path(__file__).resolve().parent / "detail.py").read_text(encoding="utf-8")
        self.assertIn("DEADLINE_EXPIRED", src)


class FilterTable(unittest.TestCase):
    def test_table_includes_area_and_hr_online(self):
        # 2026-10-20：临时投影漏 area 导致无法判断坐班/异地，补查多花一轮
        cands, _, _, _ = filter.screen_jobs([mkjob(1)], parttime_cfg())
        table = filter.render_table(cands, [])
        header = table.splitlines()[0]
        self.assertIn("area", header)
        self.assertIn("hrOnline", header)
        self.assertIn("杭州·西湖", table)
        self.assertIn("候选", table)

    def test_boundary_rows_marked_in_status_column(self):
        _, boundary, _, _ = filter.screen_jobs([mkjob(2, salary="40-60元/时")], parttime_cfg())
        table = filter.render_table([], boundary)
        self.assertIn("边界", table.splitlines()[1])


class SearchAndVerifyContracts(unittest.TestCase):
    def test_search_result_line_carries_stopped_and_fetched(self):
        src = (Path(__file__).resolve().parent / "search.py").read_text(encoding="utf-8")
        self.assertIn("stopped=", src)
        self.assertIn("fetched=", src)

    def test_apply_has_readonly_verify_mode(self):
        src = (Path(__file__).resolve().parent / "apply.py").read_text(encoding="utf-8")
        self.assertIn("--verify", src)
        self.assertIn("run_verify", src)


class ApplyPlan(unittest.TestCase):
    def test_missing_greeting_does_not_navigate(self):
        page = object()
        job = {"link": "https://www.zhipin.com/job_detail/x.html", "greeting": "   ", "resume": "/tmp/a.pdf"}
        out = apply.greet_one(object(), page, job, "   ", True)
        self.assertEqual(out["status"], "error")
        self.assertIn("greeting", out["note"])

    def test_missing_link_does_not_navigate(self):
        out = apply.greet_one(object(), object(), {"greeting": "你好"}, "你好", True)
        self.assertEqual(out["status"], "error")
        self.assertIn("link", out["note"])

    def test_present_greeting_reaches_navigation(self):
        with self.assertRaises(AttributeError):
            apply.greet_one(object(), object(), {"link": "https://www.zhipin.com/job_detail/x.html"}, "你好", False)


if __name__ == "__main__":
    unittest.main()
