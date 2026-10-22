#!/usr/bin/env python3
"""锁住评审里会让 Claude 走错路或真点出去的契约。不启动浏览器。"""
import contextlib
import json
import io
import re
import sqlite3
import subprocess
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
import _lib  # noqa: E402
from _lib import (CookieReadError, config_gaps, cooldown_wait_sec, deadline_expired, editor_text,
                  history_text, parse_salary, profile_has_login, read_wt2_expiry,
                  rotate_existing, scan_jd_flags)  # noqa: E402


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



class SalaryRuleFlags(unittest.TestCase):
    def test_monthly_uses_same_daymax_cut_as_daily(self):
        # 4000/22=181.8 < 255，与 181 元/天同一条 below_floor；6000/22=272.7 贴线不进边界
        cands, boundary, _, _ = filter.screen_jobs(
            [mkjob(1, company="甲", salary="2000-4000元/月"),
             mkjob(2, company="法研堂", salary="5000-6000元/月"),
             mkjob(3, company="丙", salary="272元/天")],
            parttime_cfg())
        self.assertEqual(boundary[0]["boundaryReasons"], ["below_floor"])
        self.assertEqual(boundary[0]["dayMax"], round(4000 / 22, 1))
        by_id = {c["id"]: c for c in cands}
        self.assertIn("i2", by_id)
        self.assertTrue(by_id["i2"]["nearFloor"])
        self.assertEqual(by_id["i2"]["dayMax"], round(6000 / 22, 1))
        self.assertTrue(by_id["i3"]["nearFloor"])
        self.assertNotIn("boundaryReasons", by_id["i2"])

    def test_list_degree_and_experience_are_flags_not_drops(self):
        cfg = parttime_cfg(degreeFloor="本科", experienceYears=4)
        jobs = [
            mkjob(1, degree="硕士", experience="5-10年"),
            mkjob(2, company="乙", degree="学历不限", experience="经验不限"),
            mkjob(3, company="丙", degree="本科", experience="1年以内"),
        ]
        cands, boundary, dropped, _ = filter.screen_jobs(jobs, cfg)
        self.assertEqual(boundary, [])
        self.assertEqual(dropped, [])
        by_id = {c["id"]: c for c in cands}
        self.assertIn("degree_above", by_id["i1"]["ruleFlags"])
        self.assertIn("exp_short", by_id["i1"]["ruleFlags"])
        self.assertNotIn("ruleFlags", by_id["i2"])
        self.assertEqual(by_id["i3"]["ruleFlags"], ["exp_over"])

    def test_degree_flag_skipped_when_floor_unset(self):
        cands, _, _, _ = filter.screen_jobs(
            [mkjob(1, degree="硕士", experience="5-10年")], parttime_cfg())
        self.assertNotIn("ruleFlags", cands[0])

    def test_abandon_hides_low_daymax_from_review(self):
        _, boundary, _, _ = filter.screen_jobs([mkjob(1, salary="20-30元/时")], parttime_cfg())
        self.assertEqual(boundary[0]["dayMax"], 120)  # 30×4
        review, abandon = filter.grade_boundary(boundary, 150)
        self.assertEqual(review, [])
        self.assertEqual(abandon[0]["boundaryGrade"], "abandon")
        self.assertEqual(filter.render_table([], review).splitlines(), [filter.render_table([], []).splitlines()[0]])

    def test_work_cycle_dash_until_detail(self):
        cands, _, _, _ = filter.screen_jobs([mkjob(1)], parttime_cfg())
        self.assertIn("	-	", filter.render_table(cands, []))
        known = {"i1": {"deadline": "时间：2025-04-12", "expired": True,
                        "hrActivity": "半年前活跃", "workCycle": "5天及以上",
                        "jdFlags": ["school_211", "time_window"]}}
        _, boundary, _, _ = filter.screen_jobs(
            [mkjob(1, salary="20-30元/时")], parttime_cfg(), known_details=known)
        self.assertTrue(boundary[0]["deadlineExpired"])
        self.assertEqual(boundary[0]["workCycle"], "5天及以上")
        self.assertIn("dead_post", boundary[0]["ruleFlags"])
        self.assertIn("school_211", boundary[0]["ruleFlags"])
        table = filter.render_table([], boundary)
        self.assertIn("5天及以上", table)
        self.assertIn("dead_post", table)


class DetailHardFlags(unittest.TestCase):
    def test_scan_tongrui_and_bulin_patterns(self):
        flags = scan_jd_flags(
            "1、211/985 学校毕业\n3、每周能拿出 18 小时左右\n晚上 8:00-9:00 开会",
            {"工作时间": "不限", "每周工期": "无要求"})
        self.assertIn("school_211", flags)
        self.assertIn("weekly_hours", flags)
        self.assertNotIn("time_window", flags)
        self.assertNotIn("weekly_days", flags)
        flags = scan_jd_flags("工作时间【工作日10-20点】", {"工作时间": "10:00-20:00", "每周工期": "5天及以上"})
        self.assertIn("time_window", flags)
        self.assertIn("weekly_days", flags)

    def test_master_requires_requirement_context(self):
        self.assertEqual(scan_jd_flags("团队里有硕士同事", {}), [])
        self.assertIn("degree_master", scan_jd_flags("学历要求：硕士及以上", {}))

    def test_collect_links_accepts_ids_and_dedupes(self):
        links = detail.collect_links(None, "abc,https://www.zhipin.com/job_detail/abc.html", None)
        self.assertEqual(links, ["https://www.zhipin.com/job_detail/abc.html"])

    def test_build_payload_writes_jd_flags(self):
        payload = detail.build_payload(
            "https://www.zhipin.com/job_detail/abc.html",
            "本周活跃\n工作时间：10:00-20:00\n211/985 学校毕业",
            "211/985 学校毕业")
        self.assertEqual(payload["id"], "abc")
        self.assertIn("school_211", payload["jdFlags"])
        self.assertIn("time_window", payload["jdFlags"])

    def test_sidebar_recommendation_is_not_this_job(self):
        payload = detail.build_payload(
            "https://www.zhipin.com/job_detail/abc.html",
            "其他岗位（每周20小时）\n工作时间：不限",
            "负责前端开发")
        self.assertNotIn("weekly_hours", payload["jdFlags"])

    def test_old_detail_file_rescanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "detail-abc.json"
            path.write_text(
                '{"id":"abc","jdText":"211/985 学校毕业","rawText":"","hrActivity":"刚刚活跃",'
                '"terms":{"工作时间":"不限","每周工期":"无要求"}}',
                encoding="utf-8")
            marks = filter.load_detail_marks(Path(tmp))
            self.assertIn("school_211", marks["abc"]["jdFlags"])
            self.assertNotIn("time_window", marks["abc"]["jdFlags"])


class RoundAndPlan(unittest.TestCase):
    def test_merge_rounds_dedupes_by_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prior = root / "jobs-2026-10-21-0900.json"
            latest = root / "jobs-2026-10-21.json"
            prior.write_text('{"jobs":[{"id":"a","job":"旧"},{"id":"b","job":"只在旧"}]}', encoding="utf-8")
            latest.write_text('{"jobs":[{"id":"a","job":"新"},{"id":"c","job":"只在新"}]}', encoding="utf-8")
            jobs, meta = filter.merge_round_jobs(latest)
            by_id = {j["id"]: j["job"] for j in jobs}
            self.assertEqual(by_id["a"], "新")
            self.assertEqual(set(by_id), {"a", "b", "c"})
            self.assertEqual(meta["new_ids"], {"c"})
            self.assertEqual(meta["overlap"], 1)

    def test_plan_target_uses_measured_rate(self):
        plan = filter.plan_target(10, 3, 0)
        self.assertEqual(plan["fetched_needed"], 167)  # ceil(10/0.06)
        self.assertEqual(plan["pages_suggest"], 4)     # ceil(167/45)
        self.assertEqual(filter.plan_target(0, 3)["pages_suggest"], 0)

    def test_config_confirm_shows_formula_not_default_8h(self):
        text = filter.format_config_confirm({"hoursPerDay": 4, "salaryFloorDay": 300, "headed": False, "jobType": "1903"})
        self.assertIn("CONFIG_CONFIRM", text)
        self.assertIn("不得默认 8", text)
        self.assertIn("月薪 ÷ 22", text)
        self.assertIn("hoursPerDay=4", text)
        self.assertNotIn("21.75", text.split("不是 21.75")[0])


class SessionBudget(unittest.TestCase):
    def test_under_budget_does_not_wait(self):
        sessions = [{"kind": "detail", "at": "2026-10-21T09:00:00"} for _ in range(6)]
        now = time.mktime(time.strptime("2026-10-21T09:01:00", "%Y-%m-%dT%H:%M:%S"))
        self.assertEqual(cooldown_wait_sec(sessions, now=now), 0)

    def test_over_budget_waits_remainder_from_last_session(self):
        sessions = [{"kind": "detail", "at": "2026-10-21T09:00:00"} for _ in range(7)]
        sessions.append({"kind": "apply", "at": "2026-10-21T09:10:00"})
        now = time.mktime(time.strptime("2026-10-21T09:11:00", "%Y-%m-%dT%H:%M:%S"))
        self.assertEqual(cooldown_wait_sec(sessions, now=now), 120)
        later = time.mktime(time.strptime("2026-10-21T09:14:00", "%Y-%m-%dT%H:%M:%S"))
        self.assertEqual(cooldown_wait_sec(sessions, now=later), 0)

    def test_apply_sessions_do_not_trip_budget(self):
        sessions = [{"kind": "apply", "at": "2026-10-21T09:00:00"} for _ in range(9)]
        now = time.mktime(time.strptime("2026-10-21T09:00:30", "%Y-%m-%dT%H:%M:%S"))
        self.assertEqual(cooldown_wait_sec(sessions, now=now), 0)

    def test_record_session_is_one_line_per_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _lib.record_session("detail", root=root, at="2026-10-21T09:00:00")
            _lib.record_session("detail", root=root, at="2026-10-21T09:05:00")
            rows = _lib.read_sessions(root=root, day="2026-10-21")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["kind"], "detail")


class ReplyStatus(unittest.TestCase):
    def test_invalid_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "delivered.json"
            dest.write_text('{"delivered":{}}', encoding="utf-8")
            self.assertIn("REPLY_STATUS_INVALID", _lib.set_reply_status("abc", "maybe", dest))
            self.assertIn("REPLY_STATUS_MISSING", _lib.set_reply_status("abc", "read", dest))

    def test_remark_does_not_wipe_reply_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "delivered.json"
            orig = _lib.DELIVERED_PATH
            _lib.DELIVERED_PATH = dest
            try:
                _lib.mark_delivered({"link": "https://www.zhipin.com/job_detail/abc.html", "job": "前端", "company": "甲"})
                self.assertEqual(_lib.set_reply_status("abc", "read", dest), "")
                _lib.mark_delivered({"link": "https://www.zhipin.com/job_detail/abc.html", "job": "前端", "company": "甲"})
                data = json.loads(dest.read_text(encoding="utf-8"))
                self.assertEqual(data["delivered"]["abc"]["replyStatus"], "read")
            finally:
                _lib.DELIVERED_PATH = orig

    def test_note_verify_updates_existing_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "delivered.json"
            dest.write_text('{"delivered":{"abc":{"job":"前端"}}}', encoding="utf-8")
            _lib.note_verify("abc", "ok", "招呼语已在聊天记录", dest)
            _lib.note_verify("missing", "missing", "无", dest)
            data = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(data["delivered"]["abc"]["verifyStatus"], "ok")
            self.assertNotIn("missing", data["delivered"])


class ShowConfigCli(unittest.TestCase):
    def test_missing_fields_refuse_ack(self):
        script = Path(__file__).resolve().parent / "filter.py"
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.json"
            cfg.write_text('{"jobType":"1903","keywords":["前端"]}', encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(script), "--config-path", str(cfg), "--show-config", "--ack"],
                capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("CONFIG_MISSING", proc.stdout)
            self.assertIn("CONFIG_ACK_REFUSED", proc.stdout)
            self.assertNotIn("confirmedAt", cfg.read_text(encoding="utf-8"))


class WorkflowContracts(unittest.TestCase):
    def test_skill_requires_confirm_batch_detail_and_verify(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("--show-config", text)
        self.assertIn("--plan-target", text)
        self.assertIn("--links", text)
        self.assertIn("--merge-rounds", text)
        self.assertIn("--verify", text)
        self.assertIn("COOLDOWN_REQUIRED", text)
        self.assertNotIn("别当日常流程跑", text)
        self.assertIn("不得代确认", text)
        self.assertIn("弹窗位置要调整吗", text)
        self.assertIn("--set-window", text)
        self.assertIn("没回答之前不要", text)
        self.assertIn("pages[].bodyTextHead", text)
        lib_src = (Path(__file__).resolve().parent / "_lib.py").read_text(encoding="utf-8")
        self.assertNotIn("OFFSCREEN_POS", lib_src)
        self.assertNotIn('arg_list.append("--window-position=-32000', lib_src)
        search_src = (Path(__file__).resolve().parent / "search.py").read_text(encoding="utf-8")
        self.assertNotIn("屏幕外有头窗口", search_src)
        for rel in ("search.py", "detail.py", "apply.py"):
            src = (Path(__file__).resolve().parent / rel).read_text(encoding="utf-8")
            self.assertIn("record_session", src)
        apply_src = (Path(__file__).resolve().parent / "apply.py").read_text(encoding="utf-8")
        self.assertIn("COOLDOWN_REQUIRED", apply_src)
        self.assertIn("VERIFY_REQUIRED", apply_src)
        self.assertIn("note_verify", apply_src)
        self.assertNotIn("skip-cooldown", apply_src)
        self.assertNotIn("--skip-cooldown", apply_src)


class WindowPosition(unittest.TestCase):
    def test_unset_confirm_asks_before_run(self):
        text = filter.format_config_confirm({"headed": False})
        self.assertIn("windowPosition=<未设置", text)
        self.assertIn("弹窗位置", text)
        self.assertIn("--set-window", text)
        self.assertIn("含弹窗位置", text)

    def test_configured_position_shown(self):
        text = filter.format_config_confirm({
            "windowX": 1200, "windowY": 80, "windowWidth": 520, "windowHeight": 720})
        self.assertIn("windowPosition=1200,80 520x720", text)

    def test_far_negative_rejected(self):
        spec, err = _lib.parse_window_value("-32000,-32000")
        self.assertIsNone(spec)
        self.assertIn("WINDOW_POSITION_INVALID", err)

    def test_xy_and_size_on_injected_display(self):
        displays = [(0, 0, 1920, 1080)]
        spec, err = _lib.parse_window_value("1200,80 900x700", displays=displays)
        self.assertIsNone(err)
        self.assertEqual(spec, {"x": 1200, "y": 80, "width": 900, "height": 700})

    def test_preset_uses_injected_bounds(self):
        spec, err = _lib.parse_window_value("右下", bounds=(0, 0, 1920, 1080))
        self.assertIsNone(err)
        self.assertEqual(spec["x"], 1920 - 640 - 40)
        self.assertEqual(spec["y"], 1080 - 800 - 40)
        self.assertEqual(spec["width"], 640)

    def test_left_monitor_negative_ok(self):
        displays = [(-1920, 0, 1920, 1080), (0, 0, 1920, 1080)]
        spec, err = _lib.parse_window_value("-1800,80 520x720", displays=displays)
        self.assertIsNone(err)
        self.assertEqual(spec["x"], -1800)

    def test_off_screen_rejected_when_displays_known(self):
        spec, err = _lib.parse_window_value("9000,80", displays=[(0, 0, 1920, 1080)])
        self.assertIsNone(spec)
        self.assertIn("WINDOW_POSITION_INVALID", err)

    def test_incomplete_pair(self):
        spec, err = _lib.resolve_window({"windowX": 10})
        self.assertIsNone(spec)
        self.assertIn("windowY", err)

    def test_tiny_size_rejected(self):
        spec, err = _lib.parse_window_value("40,40 100x100", displays=[(0, 0, 1920, 1080)])
        self.assertIsNone(spec)
        self.assertIn("宽高至少", err)

    def test_write_placement_moves_origin_and_skips_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(_lib.write_window_placement(root, {"x": 10, "y": 20}))
            pref = root / "Default" / "Preferences"
            pref.parent.mkdir(parents=True)
            pref.write_text(json.dumps({"browser": {"window_placement": {
                "left": 0, "top": 30, "right": 1512, "bottom": 889, "maximized": True,
                "work_area_left": 0}}}), encoding="utf-8")
            self.assertTrue(_lib.write_window_placement(root, {"x": 100, "y": 40}))
            wp = json.loads(pref.read_text(encoding="utf-8"))["browser"]["window_placement"]
            self.assertEqual((wp["left"], wp["top"], wp["right"], wp["bottom"]), (100, 40, 1612, 899))
            self.assertFalse(wp["maximized"])
            self.assertEqual(wp["work_area_left"], 0)

    def test_apply_window_writes_and_clears_without_probing(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.json"
            cfg.write_text('{"headed": false}', encoding="utf-8")
            displays = [(0, 0, 1920, 1080)]
            msg = _lib.apply_window_config(cfg, "1200,80 520x720", displays=displays, probe=False)
            self.assertTrue(msg.startswith("WINDOW_SET"))
            data = json.loads(cfg.read_text(encoding="utf-8"))
            self.assertEqual(data["windowX"], 1200)
            self.assertEqual(data["windowHeight"], 720)
            cleared = _lib.apply_window_config(cfg, "clear", probe=False)
            self.assertIn("WINDOW_CLEARED", cleared)
            self.assertNotIn("windowX", json.loads(cfg.read_text(encoding="utf-8")))

    def test_set_window_cli_rejects_far_negative(self):
        script = Path(__file__).resolve().parent / "filter.py"
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "config.json"
            cfg.write_text('{"headed": false}', encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(script), "--config-path", str(cfg), "--set-window=-32000,-32000"],
                capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("WINDOW_POSITION_INVALID", proc.stdout)
            self.assertNotIn("windowX", cfg.read_text(encoding="utf-8"))

    def test_chromium_args_and_cdp_payload(self):
        self.assertEqual(_lib.window_chromium_args({"x": 1, "y": 2}), ["--window-position=1,2"])
        self.assertEqual(
            _lib.window_chromium_args({"x": 1, "y": 2, "width": 3, "height": 4}),
            ["--window-position=1,2", "--window-size=3,4"])
        payload = _lib.window_bounds_payload({"x": 1, "y": 2, "width": 3, "height": 4})
        self.assertEqual(payload["windowState"], "normal")
        self.assertEqual(payload["left"], 1)


if __name__ == "__main__":
    unittest.main()
