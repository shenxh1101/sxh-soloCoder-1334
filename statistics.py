from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QPushButton, QFileDialog, QComboBox,
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
matplotlib.rcParams["axes.unicode_minus"] = False


TASK_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#34495e", "#16a085", "#d35400",
]


class StatisticsPanel(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()
        try:
            self.refresh()
        except Exception:
            pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        header = QHBoxLayout()
        title = QLabel("📊 统计面板")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title)
        header.addStretch()
        export_btn = QPushButton("📤 导出数据")
        export_btn.setStyleSheet(self._btn_style())
        export_btn.clicked.connect(self._export_data)
        header.addWidget(export_btn)
        layout.addLayout(header)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ddd; border-radius: 8px; background: white; }
            QTabBar::tab { padding: 8px 20px; font-size: 14px; }
            QTabBar::tab:selected { background: white; border-bottom: 2px solid #e74c3c; }
        """)
        self.daily_tab = self._create_daily_tab()
        self.weekly_tab = self._create_weekly_tab()
        self.monthly_tab = self._create_monthly_tab()
        self.tasks_tab = self._create_tasks_tab()
        self.tabs.addTab(self.daily_tab, "今日")
        self.tabs.addTab(self.weekly_tab, "本周")
        self.tabs.addTab(self.monthly_tab, "本月")
        self.tabs.addTab(self.tasks_tab, "任务排行")
        layout.addWidget(self.tabs, stretch=1)
        trend_group_title = QLabel("📈 近 14 天专注效率趋势")
        trend_group_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(trend_group_title)
        self.trend_summary = QLabel()
        self.trend_summary.setStyleSheet("font-size: 13px; color: #555; padding: 6px;")
        layout.addWidget(self.trend_summary)
        self.trend_figure = Figure(figsize=(8.5, 2.8), dpi=100)
        self.trend_canvas = FigureCanvas(self.trend_figure)
        layout.addWidget(self.trend_canvas)
        refresh_btn = QPushButton("🔄 刷新统计")
        refresh_btn.setStyleSheet(self._btn_style())
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _btn_style(self):
        return """
            QPushButton {
                background: #3498db; color: white; border: none;
                padding: 8px 20px; border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background: #2980b9; }
        """

    def _create_daily_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.daily_summary = QLabel()
        self.daily_summary.setStyleSheet("font-size: 14px; color: #555; padding: 10px;")
        layout.addWidget(self.daily_summary)
        self.daily_figure = Figure(figsize=(8, 3), dpi=100)
        self.daily_canvas = FigureCanvas(self.daily_figure)
        layout.addWidget(self.daily_canvas, stretch=1)
        return widget

    def _create_weekly_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.weekly_summary = QLabel()
        self.weekly_summary.setStyleSheet("font-size: 14px; color: #555; padding: 10px;")
        layout.addWidget(self.weekly_summary)
        self.weekly_figure = Figure(figsize=(8, 3), dpi=100)
        self.weekly_canvas = FigureCanvas(self.weekly_figure)
        layout.addWidget(self.weekly_canvas, stretch=1)
        return widget

    def _create_monthly_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        month_header = QHBoxLayout()
        month_header.addWidget(QLabel("选择月份:"))
        self.month_combo = QComboBox()
        now = datetime.now()
        for i in range(6):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            self.month_combo.addItem(f"{y}年{m}月", (y, m))
        self.month_combo.currentIndexChanged.connect(self._refresh_monthly_safe)
        month_header.addWidget(self.month_combo)
        month_header.addStretch()
        layout.addLayout(month_header)
        self.monthly_summary = QLabel()
        self.monthly_summary.setStyleSheet("font-size: 14px; color: #555; padding: 10px;")
        layout.addWidget(self.monthly_summary)
        self.monthly_figure = Figure(figsize=(8, 3), dpi=100)
        self.monthly_canvas = FigureCanvas(self.monthly_figure)
        layout.addWidget(self.monthly_canvas, stretch=1)
        return widget

    def _create_tasks_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("时间范围:"))
        self.task_period_combo = QComboBox()
        self.task_period_combo.addItem("今日", "today")
        self.task_period_combo.addItem("本周", "week")
        self.task_period_combo.addItem("本月", "month")
        self.task_period_combo.addItem("全部", "all")
        self.task_period_combo.setCurrentIndex(1)
        self.task_period_combo.currentIndexChanged.connect(self._refresh_tasks_safe)
        period_layout.addWidget(self.task_period_combo)
        period_layout.addStretch()
        layout.addLayout(period_layout)
        self.tasks_summary = QLabel()
        self.tasks_summary.setStyleSheet("font-size: 13px; color: #555; padding: 10px;")
        layout.addWidget(self.tasks_summary)
        self.tasks_figure = Figure(figsize=(8, 3.5), dpi=100)
        self.tasks_canvas = FigureCanvas(self.tasks_figure)
        layout.addWidget(self.tasks_canvas, stretch=1)
        return widget

    def refresh(self):
        try:
            self._refresh_daily()
        except Exception:
            pass
        try:
            self._refresh_weekly()
        except Exception:
            pass
        try:
            self._refresh_monthly_safe()
        except Exception:
            pass
        try:
            self._refresh_tasks_safe()
        except Exception:
            pass
        try:
            self._refresh_trend()
        except Exception:
            pass

    def _refresh_daily(self):
        stats = self.db.get_daily_stats()
        self.daily_summary.setText(
            f"🍅 专注番茄数: {stats['pomodoro_count']}   "
            f"⏱ 专注时长: {stats['total_minutes']} 分钟   "
            f"✅ 完成任务: {stats['tasks_completed']}"
        )
        self.daily_figure.clear()
        ax = self.daily_figure.add_subplot(111)
        try:
            if stats["pomodoro_count"] > 0:
                records = self.db.get_records(
                    f"{stats['date']}T00:00:00",
                    f"{stats['date']}T23:59:59",
                    "work",
                )
                hours = {}
                for r in records:
                    try:
                        h = int(r["started_at"][11:13])
                        hours[h] = hours.get(h, 0) + r["duration_minutes"]
                    except (ValueError, KeyError):
                        continue
                sorted_hours = sorted(hours.items())
                if sorted_hours:
                    x_vals = [f"{h}:00" for h, _ in sorted_hours]
                    y_vals = [v for _, v in sorted_hours]
                    colors = ["#e74c3c" if v >= 25 else "#f39c12" for v in y_vals]
                    ax.bar(x_vals, y_vals, color=colors, edgecolor="white", linewidth=0.5)
                    ax.set_ylabel("专注时长(分钟)")
                    ax.set_title("今日专注时段分布")
                else:
                    ax.text(0.5, 0.5, "今日暂无专注记录", ha="center", va="center", fontsize=14, color="#999")
                    ax.set_xticks([])
                    ax.set_yticks([])
            else:
                ax.text(0.5, 0.5, "今日暂无专注记录", ha="center", va="center", fontsize=14, color="#999")
                ax.set_xticks([])
                ax.set_yticks([])
        except Exception:
            ax.text(0.5, 0.5, "数据加载失败", ha="center", va="center", fontsize=14, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
        self.daily_figure.tight_layout()
        self.daily_canvas.draw()

    def _refresh_weekly(self):
        stats = self.db.get_weekly_stats()
        self.weekly_summary.setText(
            f"🍅 总番茄数: {stats['total_pomodoros']}   "
            f"⏱ 总专注时长: {stats['total_minutes']} 分钟   "
            f"✅ 完成任务: {stats['total_tasks']}"
        )
        self.weekly_figure.clear()
        ax = self.weekly_figure.add_subplot(111)
        try:
            days = stats["days"]
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            x_labels = []
            y_vals = []
            task_counts = []
            for d in days:
                date_obj = datetime.strptime(d["date"], "%Y-%m-%d")
                wd = date_obj.weekday()
                x_labels.append(weekdays[wd] + "\n" + d["date"][5:])
                y_vals.append(d["total_minutes"])
                task_counts.append(d["tasks_completed"])
            colors = ["#e74c3c" if v > 0 else "#ecf0f1" for v in y_vals]
            bars = ax.bar(x_labels, y_vals, color=colors, edgecolor="white", linewidth=0.5, label="专注时长(分钟)")
            max_y = max(y_vals) if y_vals and max(y_vals) > 0 else 1
            for i, (bar, tc) in enumerate(zip(bars, task_counts)):
                height = bar.get_height()
                if tc > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height + max_y * 0.02,
                        f"{tc} 任务",
                        ha="center", va="bottom", fontsize=9, color="#27ae60", fontweight="bold",
                    )
            ax.set_ylabel("专注时长(分钟)")
            ax.set_title("本周每日专注时长与完成任务数")
            ax.legend(loc="upper left", fontsize=9)
            ax.set_ylim(0, max_y * 1.15)
        except Exception:
            ax.text(0.5, 0.5, "数据加载失败", ha="center", va="center", fontsize=14, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
        self.weekly_figure.tight_layout()
        self.weekly_canvas.draw()

    def _refresh_monthly_safe(self):
        try:
            self._refresh_monthly()
        except Exception:
            pass

    def _refresh_monthly(self):
        data = self.month_combo.currentData()
        if data is None:
            self.monthly_figure.clear()
            ax = self.monthly_figure.add_subplot(111)
            ax.text(0.5, 0.5, "请选择月份", ha="center", va="center", fontsize=14, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
            self.monthly_figure.tight_layout()
            self.monthly_canvas.draw()
            return
        year, month = data
        stats = self.db.get_monthly_stats(year, month)
        self.monthly_summary.setText(
            f"🍅 总番茄数: {stats['pomodoro_count']}   "
            f"⏱ 总专注时长: {stats['total_minutes']} 分钟   "
            f"✅ 完成任务: {stats['tasks_completed']}"
        )
        self.monthly_figure.clear()
        ax = self.monthly_figure.add_subplot(111)
        try:
            daily = stats["daily"]
            x_vals = [int(d["date"][-2:]) for d in daily]
            y_vals = [d["minutes"] for d in daily]
            if x_vals and sum(y_vals) > 0:
                ax.fill_between(x_vals, y_vals, alpha=0.3, color="#e74c3c")
                ax.plot(x_vals, y_vals, color="#e74c3c", linewidth=2, marker="o", markersize=3)
                avg_val = sum(y_vals) / len([y for y in y_vals if y > 0]) if any(y > 0 for y in y_vals) else 0
                if avg_val > 0:
                    ax.axhline(y=avg_val, color="#3498db", linestyle="--", linewidth=1, alpha=0.7, label=f"平均 {avg_val:.0f} 分钟/天")
                    ax.legend(loc="upper left", fontsize=9)
                ax.set_xlabel("日期")
                ax.set_ylabel("专注时长(分钟)")
                ax.set_title(f"{year}年{month}月专注趋势")
                ax.set_xlim(1, max(x_vals) if x_vals else 31)
            else:
                ax.text(0.5, 0.5, "本月暂无专注记录", ha="center", va="center", fontsize=14, color="#999")
                ax.set_xticks([])
                ax.set_yticks([])
        except Exception:
            ax.text(0.5, 0.5, "数据加载失败", ha="center", va="center", fontsize=14, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
        self.monthly_figure.tight_layout()
        self.monthly_canvas.draw()

    def _refresh_tasks_safe(self):
        try:
            self._refresh_tasks()
        except Exception:
            pass

    def _get_task_period_range(self):
        period = self.task_period_combo.currentData()
        today = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now()
        if period == "today":
            return f"{today}T00:00:00", f"{today}T23:59:59"
        elif period == "week":
            start = now - timedelta(days=6)
            return start.strftime("%Y-%m-%d") + "T00:00:00", now.strftime("%Y-%m-%d") + "T23:59:59"
        elif period == "month":
            start = datetime(now.year, now.month, 1)
            return start.strftime("%Y-%m-%d") + "T00:00:00", now.strftime("%Y-%m-%d") + "T23:59:59"
        else:
            return None, None

    def _refresh_tasks(self):
        start, end = self._get_task_period_range()
        ranking = self.db.get_task_time_ranking(start, end, limit=10)
        total_minutes = sum(r["total_minutes"] for r in ranking if r["total_minutes"])
        total_pomos = sum(r["pomodoro_count"] for r in ranking if r["pomodoro_count"])
        self.tasks_summary.setText(
            f"📋 共 {len(ranking)} 个任务 · "
            f"⏱ 总投入 {total_minutes} 分钟 · "
            f"🍅 总番茄 {total_pomos} 个"
        )
        self.tasks_figure.clear()
        ax = self.tasks_figure.add_subplot(111)
        try:
            if ranking and total_minutes > 0:
                names = []
                minutes = []
                pomos = []
                for r in ranking:
                    name = r["task_name"]
                    if len(name) > 15:
                        name = name[:13] + "..."
                    names.append(name)
                    minutes.append(r["total_minutes"] if r["total_minutes"] else 0)
                    pomos.append(r["pomodoro_count"] if r["pomodoro_count"] else 0)
                names = list(reversed(names))
                minutes = list(reversed(minutes))
                pomos = list(reversed(pomos))
                colors = [TASK_COLORS[i % len(TASK_COLORS)] for i in range(len(names))]
                bars = ax.barh(names, minutes, color=colors, edgecolor="white", height=0.6)
                for bar, pomo, minute in zip(bars, pomos, minutes):
                    width = bar.get_width()
                    ax.text(
                        width + max(minutes) * 0.01,
                        bar.get_y() + bar.get_height() / 2,
                        f"{minute} 分钟 ({pomo} 个)",
                        va="center", fontsize=9, color="#555",
                    )
                ax.set_xlabel("专注时长(分钟)")
                ax.set_title("任务投入时间排行")
                ax.set_xlim(0, max(minutes) * 1.25 if minutes else 1)
            else:
                ax.text(0.5, 0.5, "暂无任务数据", ha="center", va="center", fontsize=14, color="#999")
                ax.set_xticks([])
                ax.set_yticks([])
        except Exception:
            ax.text(0.5, 0.5, "数据加载失败", ha="center", va="center", fontsize=14, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
        self.tasks_figure.tight_layout()
        self.tasks_canvas.draw()

    def _refresh_trend(self):
        try:
            trend = self.db.get_efficiency_trend(14)
        except Exception:
            trend = []
        total_min = sum(t["minutes"] for t in trend)
        total_pomo = sum(t["pomodoros"] for t in trend)
        total_tasks = sum(t["tasks"] for t in trend)
        active_days = len([t for t in trend if t["minutes"] > 0])
        avg_eff = 0
        eff_vals = [t["efficiency"] for t in trend if t["minutes"] > 0]
        if eff_vals:
            avg_eff = sum(eff_vals) / len(eff_vals)
        self.trend_summary.setText(
            f"📊 14 天汇总: 总时长 {total_min} 分钟 · "
            f"总番茄 {total_pomo} 个 · "
            f"完成任务 {total_tasks} 个 · "
            f"活跃 {active_days} 天 · "
            f"平均效率 {avg_eff:.2f} 任务/小时"
        )
        self.trend_figure.clear()
        ax1 = self.trend_figure.add_subplot(111)
        try:
            x_vals = [t["date"] for t in trend]
            minutes = [t["minutes"] for t in trend]
            efficiencies = [t["efficiency"] for t in trend]
            ax2 = ax1.twinx()
            if sum(minutes) > 0:
                ax1.bar(x_vals, minutes, color="#e74c3c", alpha=0.4, edgecolor="white", label="专注时长(分钟)")
                ax2.plot(x_vals, efficiencies, color="#3498db", marker="o", linewidth=2, markersize=5, label="效率(任务/小时)")
                ax1.set_ylabel("专注时长(分钟)", color="#e74c3c")
                ax2.set_ylabel("效率 (任务/小时)", color="#3498db")
                ax1.tick_params(axis="y", labelcolor="#e74c3c")
                ax2.tick_params(axis="y", labelcolor="#3498db")
                ax1.set_title("近 14 天专注时长与效率趋势")
                ax1.tick_params(axis="x", rotation=45, labelsize=8)
                lines1, labels1 = ax1.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)
            else:
                ax1.text(0.5, 0.5, "暂无专注数据，开始你的第一个番茄钟吧！", ha="center", va="center", fontsize=14, color="#999")
                ax1.set_xticks([])
                ax1.set_yticks([])
                ax2.set_yticks([])
        except Exception:
            ax1.text(0.5, 0.5, "数据加载失败", ha="center", va="center", fontsize=14, color="#999")
            ax1.set_xticks([])
            ax1.set_yticks([])
        self.trend_figure.tight_layout()
        self.trend_canvas.draw()

    def _export_data(self):
        folder = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if folder:
            try:
                task_path, record_path = self.db.export_data(folder)
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"数据已导出:\n任务: {task_path}\n记录: {record_path}",
                )
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "导出失败", f"导出数据时出错: {e}")
