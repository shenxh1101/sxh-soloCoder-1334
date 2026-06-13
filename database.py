import sqlite3
import os
import json
from datetime import datetime, timedelta


DEFAULT_CATEGORIES = ["工作", "学习", "生活", "健康", "娱乐", "其他"]


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            app_data = os.path.join(os.path.expanduser("~"), ".pomodoro_focus")
            os.makedirs(app_data, exist_ok=True)
            db_path = os.path.join(app_data, "pomodoro.db")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._migrate_schema()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed INTEGER DEFAULT 0,
                pomodoros_completed INTEGER DEFAULT 0,
                pomodoros_target INTEGER DEFAULT 1,
                completed_at TEXT,
                category TEXT DEFAULT '工作',
                notes TEXT DEFAULT '',
                archived INTEGER DEFAULT 0,
                archived_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pomodoro_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                type TEXT NOT NULL DEFAULT 'work',
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocked_sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site TEXT NOT NULL UNIQUE
            )
        """)
        self.conn.commit()

    def _migrate_schema(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT '工作'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN notes TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN archived INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN archived_at TEXT")
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def get_config(self, key, default=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key=?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                return row["value"]
        return default

    def set_config(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
        self.conn.commit()

    def get_categories(self):
        stored = self.get_config("task_categories", None)
        if stored and isinstance(stored, list):
            return stored
        return DEFAULT_CATEGORIES[:]

    def set_categories(self, categories):
        self.set_config("task_categories", list(categories))

    def add_task(self, name, pomodoros_target=1, category="工作", notes=""):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (name, created_at, pomodoros_target, category, notes) VALUES (?, ?, ?, ?, ?)",
            (name, datetime.now().isoformat(), pomodoros_target, category, notes),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_tasks(self, include_completed=True, include_archived=False):
        cursor = self.conn.cursor()
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        if not include_completed:
            query += " AND completed=0"
        if not include_archived:
            query += " AND archived=0"
        query += " ORDER BY archived, completed, created_at DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def complete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET completed=1, completed_at=? WHERE id=?",
            (datetime.now().isoformat(), task_id),
        )
        self.conn.commit()

    def uncomplete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET completed=0, completed_at=NULL WHERE id=?",
            (task_id,),
        )
        self.conn.commit()

    def archive_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET archived=1, archived_at=? WHERE id=?",
            (datetime.now().isoformat(), task_id),
        )
        self.conn.commit()

    def unarchive_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET archived=0, archived_at=NULL WHERE id=?",
            (task_id,),
        )
        self.conn.commit()

    def align_task_completion_state(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT completed, pomodoros_completed, pomodoros_target FROM tasks WHERE id=?",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row:
            return
        completed = row["completed"]
        done = row["pomodoros_completed"]
        target = row["pomodoros_target"]
        should_be_complete = done >= target
        if should_be_complete and not completed:
            self.complete_task(task_id)
        elif not should_be_complete and completed:
            self.uncomplete_task(task_id)

    def update_task_name(self, task_id, new_name):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET name=? WHERE id=?",
            (new_name, task_id),
        )
        self.conn.commit()

    def update_task_category(self, task_id, new_category):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET category=? WHERE id=?",
            (new_category, task_id),
        )
        self.conn.commit()

    def update_task_notes(self, task_id, notes):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET notes=? WHERE id=?",
            (notes, task_id),
        )
        self.conn.commit()

    def update_task_target(self, task_id, new_target):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET pomodoros_target=? WHERE id=?",
            (max(1, new_target), task_id),
        )
        self.conn.commit()
        self.align_task_completion_state(task_id)

    def update_task_pomodoro(self, task_id, increment=1):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET pomodoros_completed=pomodoros_completed+? WHERE id=?",
            (increment, task_id),
        )
        self.conn.commit()
        self.align_task_completion_state(task_id)

    def delete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()

    def add_pomodoro_record(self, task_id, started_at, ended_at, duration_minutes, record_type="work"):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO pomodoro_records (task_id, started_at, ended_at, duration_minutes, type) VALUES (?, ?, ?, ?, ?)",
            (task_id, started_at, ended_at, duration_minutes, record_type),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_records(self, start_date=None, end_date=None, record_type=None):
        cursor = self.conn.cursor()
        query = "SELECT * FROM pomodoro_records WHERE 1=1"
        params = []
        if start_date:
            query += " AND started_at>=?"
            params.append(start_date)
        if end_date:
            query += " AND started_at<=?"
            params.append(end_date)
        if record_type:
            query += " AND type=?"
            params.append(record_type)
        query += " ORDER BY started_at DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_daily_stats(self, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        start = f"{date}T00:00:00"
        end = f"{date}T23:59:59"
        records = self.get_records(start, end, "work")
        total_minutes = sum(r["duration_minutes"] for r in records)
        pomodoro_count = len(records)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE completed=1 AND completed_at>=? AND completed_at<=?",
            (start, end),
        )
        row = cursor.fetchone()
        tasks_completed = row["cnt"] if row else 0
        return {
            "date": date,
            "total_minutes": total_minutes,
            "pomodoro_count": pomodoro_count,
            "tasks_completed": tasks_completed,
        }

    def get_weekly_stats(self, end_date=None):
        if end_date is None:
            end_date = datetime.now()
        start_date = end_date - timedelta(days=6)
        days = []
        current = start_date
        while current <= end_date:
            days.append(self.get_daily_stats(current.strftime("%Y-%m-%d")))
            current += timedelta(days=1)
        total_minutes = sum(d["total_minutes"] for d in days)
        total_pomodoros = sum(d["pomodoro_count"] for d in days)
        total_tasks = sum(d["tasks_completed"] for d in days)
        return {
            "days": days,
            "total_minutes": total_minutes,
            "total_pomodoros": total_pomodoros,
            "total_tasks": total_tasks,
        }

    def get_monthly_stats(self, year=None, month=None):
        if year is None or month is None:
            now = datetime.now()
            year = now.year
            month = now.month
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        start = datetime(year, month, 1).isoformat()
        end = (next_month - timedelta(seconds=1)).isoformat()
        records = self.get_records(start, end, "work")
        total_minutes = sum(r["duration_minutes"] for r in records)
        pomodoro_count = len(records)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM tasks WHERE completed=1 AND completed_at>=? AND completed_at<=?",
            (start, end),
        )
        row = cursor.fetchone()
        tasks_completed = row["cnt"] if row else 0
        days_in_month = (next_month - timedelta(days=1)).day
        daily = {}
        for r in records:
            day = r["started_at"][:10]
            daily[day] = daily.get(day, 0) + r["duration_minutes"]
        daily_list = []
        for d in range(1, days_in_month + 1):
            day_str = f"{year}-{month:02d}-{d:02d}"
            daily_list.append({"date": day_str, "minutes": daily.get(day_str, 0)})
        return {
            "year": year,
            "month": month,
            "total_minutes": total_minutes,
            "pomodoro_count": pomodoro_count,
            "tasks_completed": tasks_completed,
            "daily": daily_list,
        }

    def get_summary(self, start_date=None, end_date=None):
        cursor = self.conn.cursor()
        query = """
            SELECT type, COUNT(*) as cnt, SUM(duration_minutes) as total_min
            FROM pomodoro_records
            WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND started_at>=?"
            params.append(start_date)
        if end_date:
            query += " AND started_at<=?"
            params.append(end_date)
        query += " GROUP BY type"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = {
            "work_minutes": 0,
            "work_count": 0,
            "break_minutes": 0,
            "break_count": 0,
            "long_break_minutes": 0,
            "long_break_count": 0,
            "abandoned_minutes": 0,
            "abandoned_count": 0,
            "skip_break_minutes": 0,
            "skip_break_count": 0,
            "task_completed_count": 0,
        }
        for r in rows:
            t = r["type"]
            cnt = r["cnt"] or 0
            total = r["total_min"] or 0
            if t == "work":
                result["work_minutes"] = total
                result["work_count"] = cnt
            elif t == "break":
                result["break_minutes"] = total
                result["break_count"] = cnt
            elif t == "long_break":
                result["long_break_minutes"] = total
                result["long_break_count"] = cnt
            elif t == "abandoned":
                result["abandoned_minutes"] = total
                result["abandoned_count"] = cnt
            elif t == "skip_break":
                result["skip_break_minutes"] = total
                result["skip_break_count"] = cnt
        if start_date and end_date:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM tasks WHERE completed=1 AND completed_at>=? AND completed_at<=?",
                (start_date, end_date),
            )
            row = cursor.fetchone()
            result["task_completed_count"] = row["cnt"] if row else 0
        return result

    def get_daily_task_summary(self, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        start = f"{date}T00:00:00"
        end = f"{date}T23:59:59"
        cursor = self.conn.cursor()
        query = """
            SELECT pr.task_id, t.name as task_name, t.category as task_category,
                   COUNT(pr.id) as pomodoro_count,
                   SUM(pr.duration_minutes) as total_minutes
            FROM pomodoro_records pr
            LEFT JOIN tasks t ON pr.task_id = t.id
            WHERE pr.type='work' AND pr.started_at>=? AND pr.started_at<=?
            GROUP BY pr.task_id
            ORDER BY total_minutes DESC
        """
        cursor.execute(query, (start, end))
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            if d["task_name"] is None:
                d["task_name"] = "未指定任务"
            if d["task_category"] is None:
                d["task_category"] = "其他"
            results.append(d)
        return results

    def get_daily_category_summary(self, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        start = f"{date}T00:00:00"
        end = f"{date}T23:59:59"
        cursor = self.conn.cursor()
        query = """
            SELECT COALESCE(t.category, '其他') as category,
                   COUNT(DISTINCT pr.task_id) as task_count,
                   COUNT(pr.id) as pomodoro_count,
                   SUM(pr.duration_minutes) as total_minutes
            FROM pomodoro_records pr
            LEFT JOIN tasks t ON pr.task_id = t.id
            WHERE pr.type='work' AND pr.started_at>=? AND pr.started_at<=?
            GROUP BY COALESCE(t.category, '其他')
            ORDER BY total_minutes DESC
        """
        cursor.execute(query, (start, end))
        return [dict(row) for row in cursor.fetchall()]

    def generate_daily_report(self, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date_obj.weekday()]
        summary = self.get_summary(f"{date}T00:00:00", f"{date}T23:59:59")
        tasks = self.get_daily_task_summary(date)
        categories = self.get_daily_category_summary(date)
        work_min = summary["work_minutes"]
        work_count = summary["work_count"]
        break_min = summary["break_minutes"] + summary["long_break_minutes"]
        completed_count = summary["task_completed_count"]
        h_work, m_work = divmod(work_min, 60)
        h_break, m_break = divmod(break_min, 60)
        work_str = f"{h_work}小时{m_work}分钟" if h_work > 0 else f"{m_work}分钟"
        break_str = f"{h_break}小时{m_break}分钟" if h_break > 0 else f"{m_break}分钟"
        lines = []
        lines.append(f"📅 {date}（{weekday_cn}）工作日志")
        lines.append("=" * 40)
        lines.append("")
        lines.append("⏱ 今日概览")
        lines.append(f"  🍅 专注：{work_count} 次 · {work_str}")
        lines.append(f"  ☕ 休息：{break_str}")
        lines.append(f"  ✅ 完成任务：{completed_count} 个")
        lines.append("")
        if categories:
            lines.append("📂 分类投入")
            for i, c in enumerate(categories, 1):
                cat_min = c["total_minutes"]
                cat_h, cat_m = divmod(cat_min, 60)
                cat_str = f"{cat_h}小时{cat_m}分钟" if cat_h > 0 else f"{cat_m}分钟"
                lines.append(f"  {i}. {c['category']}：{cat_str} ({c['pomodoro_count']}🍅, {c['task_count']}个任务)")
            lines.append("")
        if tasks:
            lines.append("📝 任务明细")
            for i, t in enumerate(tasks, 1):
                t_min = t["total_minutes"]
                t_h, t_m = divmod(t_min, 60)
                t_str = f"{t_h}小时{t_m}分钟" if t_h > 0 else f"{t_m}分钟"
                cat_tag = f" [{t['task_category']}]" if t["task_category"] else ""
                lines.append(f"  {i}. {t['task_name']}{cat_tag}")
                lines.append(f"     投入：{t_str} · {t['pomodoro_count']} 个番茄")
            lines.append("")
        lines.append("— 番茄钟专注助手自动生成 —")
        return "\n".join(lines)

    def generate_weekly_report(self, end_date=None):
        if end_date is None:
            end_date = datetime.now()
        start_date = end_date - timedelta(days=end_date.weekday())
        end_date_dt = start_date + timedelta(days=6)
        start_str = start_date.strftime("%Y-%m-%d") + "T00:00:00"
        end_str = end_date_dt.strftime("%Y-%m-%d") + "T23:59:59"
        summary = self.get_summary(start_str, end_str)
        work_min = summary["work_minutes"]
        work_count = summary["work_count"]
        break_min = summary["break_minutes"] + summary["long_break_minutes"]
        completed_count = summary["task_completed_count"]
        h_work, m_work = divmod(work_min, 60)
        work_str = f"{h_work}小时{m_work}分钟" if h_work > 0 else f"{m_work}分钟"
        cursor = self.conn.cursor()
        query = """
            SELECT pr.task_id, t.name as task_name, t.category as task_category,
                   COUNT(pr.id) as pomodoro_count,
                   SUM(pr.duration_minutes) as total_minutes
            FROM pomodoro_records pr
            LEFT JOIN tasks t ON pr.task_id = t.id
            WHERE pr.type='work' AND pr.started_at>=? AND pr.started_at<=?
            GROUP BY pr.task_id
            ORDER BY total_minutes DESC
        """
        cursor.execute(query, (start_str, end_str))
        top_tasks = []
        for row in cursor.fetchall():
            d = dict(row)
            if d["task_name"] is None:
                d["task_name"] = "未指定任务"
            if d["task_category"] is None:
                d["task_category"] = "其他"
            top_tasks.append(d)
        cat_query = """
            SELECT COALESCE(t.category, '其他') as category,
                   COUNT(DISTINCT pr.task_id) as task_count,
                   COUNT(pr.id) as pomodoro_count,
                   SUM(pr.duration_minutes) as total_minutes
            FROM pomodoro_records pr
            LEFT JOIN tasks t ON pr.task_id = t.id
            WHERE pr.type='work' AND pr.started_at>=? AND pr.started_at<=?
            GROUP BY COALESCE(t.category, '其他')
            ORDER BY total_minutes DESC
        """
        cursor.execute(cat_query, (start_str, end_str))
        top_cats = [dict(row) for row in cursor.fetchall()]
        daily = []
        for i in range(7):
            d = start_date + timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            ds_str = ds + "T00:00:00"
            de_str = ds + "T23:59:59"
            day_sum = self.get_summary(ds_str, de_str)
            daily.append({
                "date": ds,
                "date_short": d.strftime("%m-%d"),
                "weekday": ["一", "二", "三", "四", "五", "六", "日"][d.weekday()],
                "minutes": day_sum["work_minutes"],
                "pomodoros": day_sum["work_count"],
            })
        lines = []
        lines.append(f"📆 本周工作复盘（{start_date.strftime('%m月%d日')} ~ {end_date_dt.strftime('%m月%d日')}）")
        lines.append("=" * 48)
        lines.append("")
        lines.append("📊 本周总览")
        lines.append(f"  🍅 专注：{work_count} 次 · {work_str}")
        lines.append(f"  ✅ 完成任务：{completed_count} 个")
        lines.append(f"  💪 日均专注：{work_min // 7} 分钟")
        lines.append("")
        if daily:
            lines.append("📅 每日投入")
            for d in daily:
                bar = "█" * (d["minutes"] // 15)
                lines.append(f"  周{d['weekday']} ({d['date_short']})  {d['minutes']:>4}分钟  {bar}")
            lines.append("")
        if top_cats:
            lines.append("📂 分类排行")
            for i, c in enumerate(top_cats[:5], 1):
                cat_h, cat_m = divmod(c["total_minutes"], 60)
                cat_str = f"{cat_h}小时{cat_m}分钟" if cat_h > 0 else f"{cat_m}分钟"
                lines.append(f"  {i}. {c['category']}：{cat_str} ({c['pomodoro_count']}🍅)")
            lines.append("")
        if top_tasks:
            lines.append("🏆 任务 Top 5")
            for i, t in enumerate(top_tasks[:5], 1):
                t_h, t_m = divmod(t["total_minutes"], 60)
                t_str = f"{t_h}小时{t_m}分钟" if t_h > 0 else f"{t_m}分钟"
                cat_tag = f" [{t['task_category']}]" if t["task_category"] else ""
                lines.append(f"  {i}. {t['task_name']}{cat_tag} — {t_str} ({t['pomodoro_count']}🍅)")
            lines.append("")
        lines.append("— 番茄钟专注助手自动生成 —")
        return "\n".join(lines)

    def add_blocked_site(self, site):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO blocked_sites (site) VALUES (?)", (site,))
        self.conn.commit()

    def remove_blocked_site(self, site):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM blocked_sites WHERE site=?", (site,))
        self.conn.commit()

    def get_blocked_sites(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT site FROM blocked_sites ORDER BY site")
        return [row["site"] for row in cursor.fetchall()]

    def get_records_with_task_names(self, start_date=None, end_date=None, record_type=None):
        cursor = self.conn.cursor()
        query = """
            SELECT pr.*, t.name as task_name, t.category as task_category
            FROM pomodoro_records pr
            LEFT JOIN tasks t ON pr.task_id = t.id
            WHERE 1=1
        """
        params = []
        if start_date:
            query += " AND pr.started_at>=?"
            params.append(start_date)
        if end_date:
            query += " AND pr.started_at<=?"
            params.append(end_date)
        if record_type:
            query += " AND pr.type=?"
            params.append(record_type)
        query += " ORDER BY pr.started_at DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_task_time_ranking(self, start_date=None, end_date=None, limit=10):
        cursor = self.conn.cursor()
        query = """
            SELECT t.id as task_id, t.name as task_name, t.category as task_category,
                   COUNT(pr.id) as pomodoro_count,
                   SUM(pr.duration_minutes) as total_minutes
            FROM pomodoro_records pr
            LEFT JOIN tasks t ON pr.task_id = t.id
            WHERE pr.type='work'
        """
        params = []
        if start_date:
            query += " AND pr.started_at>=?"
            params.append(start_date)
        if end_date:
            query += " AND pr.started_at<=?"
            params.append(end_date)
        query += " GROUP BY pr.task_id ORDER BY total_minutes DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        results = []
        for row in cursor.fetchall():
            d = dict(row)
            if d["task_name"] is None:
                d["task_name"] = "未指定任务"
            if d["task_category"] is None:
                d["task_category"] = "其他"
            results.append(d)
        return results

    def get_category_time_ranking(self, start_date=None, end_date=None, limit=10):
        cursor = self.conn.cursor()
        query = """
            SELECT COALESCE(t.category, '其他') as category,
                   COUNT(DISTINCT pr.task_id) as task_count,
                   COUNT(pr.id) as pomodoro_count,
                   SUM(pr.duration_minutes) as total_minutes
            FROM pomodoro_records pr
            LEFT JOIN tasks t ON pr.task_id = t.id
            WHERE pr.type='work'
        """
        params = []
        if start_date:
            query += " AND pr.started_at>=?"
            params.append(start_date)
        if end_date:
            query += " AND pr.started_at<=?"
            params.append(end_date)
        query += " GROUP BY COALESCE(t.category, '其他') ORDER BY total_minutes DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_daily_work_heatmap(self, days=60):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)
        start_str = start_date.strftime("%Y-%m-%d") + "T00:00:00"
        end_str = end_date.strftime("%Y-%m-%d") + "T23:59:59"
        records = self.get_records(start_str, end_str, "work")
        daily = {}
        hourly = {}
        for h in range(24):
            hourly[h] = 0
        for r in records:
            day = r["started_at"][:10]
            daily[day] = daily.get(day, 0) + r["duration_minutes"]
            try:
                h = int(r["started_at"][11:13])
                hourly[h] = hourly.get(h, 0) + r["duration_minutes"]
            except (ValueError, KeyError, IndexError):
                pass
        calendar = []
        cur = start_date
        while cur <= end_date:
            ds = cur.strftime("%Y-%m-%d")
            calendar.append({
                "date": ds,
                "date_short": cur.strftime("%m-%d"),
                "weekday": cur.weekday(),
                "minutes": daily.get(ds, 0),
            })
            cur += timedelta(days=1)
        return {
            "calendar": calendar,
            "hourly": [{"hour": h, "minutes": hourly[h]} for h in range(24)],
            "total_minutes": sum(daily.values()),
            "active_days": len([v for v in daily.values() if v > 0]),
        }

    def get_efficiency_trend(self, days=14):
        end_date = datetime.now()
        trend = []
        for i in range(days - 1, -1, -1):
            d = end_date - timedelta(days=i)
            stats = self.get_daily_stats(d.strftime("%Y-%m-%d"))
            work_hours = stats["total_minutes"] / 60.0
            tasks = stats["tasks_completed"]
            if work_hours > 0:
                efficiency = tasks / work_hours if work_hours > 0 else 0
            else:
                efficiency = 0
            trend.append({
                "date": d.strftime("%m-%d"),
                "date_full": d.strftime("%Y-%m-%d"),
                "minutes": stats["total_minutes"],
                "pomodoros": stats["pomodoro_count"],
                "tasks": tasks,
                "efficiency": round(efficiency, 2),
            })
        return trend

    def export_data(self, export_dir):
        os.makedirs(export_dir, exist_ok=True)
        tasks = self.get_tasks()
        records = self.get_records()
        import csv
        task_path = os.path.join(export_dir, "tasks.csv")
        with open(task_path, "w", newline="", encoding="utf-8") as f:
            if tasks:
                writer = csv.DictWriter(f, fieldnames=tasks[0].keys())
                writer.writeheader()
                writer.writerows(tasks)
        record_path = os.path.join(export_dir, "pomodoro_records.csv")
        with open(record_path, "w", newline="", encoding="utf-8") as f:
            if records:
                writer = csv.DictWriter(f, fieldnames=records[0].keys())
                writer.writeheader()
                writer.writerows(records)
        return task_path, record_path

    def close(self):
        self.conn.close()
