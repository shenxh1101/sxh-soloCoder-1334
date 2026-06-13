import sqlite3
import os
import json
from datetime import datetime, timedelta


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
                completed_at TEXT
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

    def add_task(self, name, pomodoros_target=1):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (name, created_at, pomodoros_target) VALUES (?, ?, ?)",
            (name, datetime.now().isoformat(), pomodoros_target),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_tasks(self, include_completed=True):
        cursor = self.conn.cursor()
        if include_completed:
            cursor.execute("SELECT * FROM tasks ORDER BY completed, created_at DESC")
        else:
            cursor.execute("SELECT * FROM tasks WHERE completed=0 ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def complete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET completed=1, completed_at=? WHERE id=?",
            (datetime.now().isoformat(), task_id),
        )
        self.conn.commit()

    def update_task_pomodoro(self, task_id, increment=1):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET pomodoros_completed=pomodoros_completed+? WHERE id=?",
            (increment, task_id),
        )
        self.conn.commit()

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
