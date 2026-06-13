from datetime import datetime
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


class StatisticsPanel(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()

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
        self.tabs.addTab(self.daily_tab, "今日")
        self.tabs.addTab(self.weekly_tab, "本周")
        self.tabs.addTab(self.monthly_tab, "本月")
        layout.addWidget(self.tabs)
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
        layout.addWidget(self.daily_canvas)
        return widget

    def _create_weekly_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.weekly_summary = QLabel()
        self.weekly_summary.setStyleSheet("font-size: 14px; color: #555; padding: 10px;")
        layout.addWidget(self.weekly_summary)
        self.weekly_figure = Figure(figsize=(8, 3), dpi=100)
        self.weekly_canvas = FigureCanvas(self.weekly_figure)
        layout.addWidget(self.weekly_canvas)
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
        self.month_combo.currentIndexChanged.connect(self.refresh)
        month_header.addWidget(self.month_combo)
        month_header.addStretch()
        layout.addLayout(month_header)
        self.monthly_summary = QLabel()
        self.monthly_summary.setStyleSheet("font-size: 14px; color: #555; padding: 10px;")
        layout.addWidget(self.monthly_summary)
        self.monthly_figure = Figure(figsize=(8, 3), dpi=100)
        self.monthly_canvas = FigureCanvas(self.monthly_figure)
        layout.addWidget(self.monthly_canvas)
        return widget

    def refresh(self):
        self._refresh_daily()
        self._refresh_weekly()
        self._refresh_monthly()

    def _refresh_daily(self):
        stats = self.db.get_daily_stats()
        self.daily_summary.setText(
            f"🍅 专注番茄数: {stats['pomodoro_count']}   "
            f"⏱ 专注时长: {stats['total_minutes']}分钟   "
            f"✅ 完成任务: {stats['tasks_completed']}"
        )
        self.daily_figure.clear()
        ax = self.daily_figure.add_subplot(111)
        if stats["pomodoro_count"] > 0:
            records = self.db.get_records(
                f"{stats['date']}T00:00:00",
                f"{stats['date']}T23:59:59",
                "work",
            )
            hours = {}
            for r in records:
                h = int(r["started_at"][11:13])
                hours[h] = hours.get(h, 0) + r["duration_minutes"]
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
        self.daily_figure.tight_layout()
        self.daily_canvas.draw()

    def _refresh_weekly(self):
        stats = self.db.get_weekly_stats()
        self.weekly_summary.setText(
            f"🍅 总番茄数: {stats['total_pomodoros']}   "
            f"⏱ 总专注时长: {stats['total_minutes']}分钟   "
            f"✅ 完成任务: {stats['tasks_completed']}"
        )
        self.weekly_figure.clear()
        ax = self.weekly_figure.add_subplot(111)
        days = stats["days"]
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        from datetime import datetime as dt
        x_labels = []
        y_vals = []
        for d in days:
            date_obj = dt.strptime(d["date"], "%Y-%m-%d")
            wd = date_obj.weekday()
            x_labels.append(weekdays[wd] + "\n" + d["date"][5:])
            y_vals.append(d["total_minutes"])
        colors = ["#e74c3c" if v > 0 else "#ecf0f1" for v in y_vals]
        ax.bar(x_labels, y_vals, color=colors, edgecolor="white", linewidth=0.5)
        ax.set_ylabel("专注时长(分钟)")
        ax.set_title("本周每日专注时长")
        self.weekly_figure.tight_layout()
        self.weekly_canvas.draw()

    def _refresh_monthly(self):
        data = self.month_combo.currentData()
        if data is None:
            return
        year, month = data
        stats = self.db.get_monthly_stats(year, month)
        self.monthly_summary.setText(
            f"🍅 总番茄数: {stats['pomodoro_count']}   "
            f"⏱ 总专注时长: {stats['total_minutes']}分钟   "
            f"✅ 完成任务: {stats['tasks_completed']}"
        )
        self.monthly_figure.clear()
        ax = self.monthly_figure.add_subplot(111)
        daily = stats["daily"]
        x_vals = [int(d["date"][-2:]) for d in daily]
        y_vals = [d["minutes"] for d in daily]
        ax.fill_between(x_vals, y_vals, alpha=0.3, color="#e74c3c")
        ax.plot(x_vals, y_vals, color="#e74c3c", linewidth=2, marker="o", markersize=3)
        ax.set_xlabel("日期")
        ax.set_ylabel("专注时长(分钟)")
        ax.set_title(f"{year}年{month}月专注趋势")
        ax.set_xlim(1, max(x_vals) if x_vals else 31)
        self.monthly_figure.tight_layout()
        self.monthly_canvas.draw()

    def _export_data(self):
        folder = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if folder:
            task_path, record_path = self.db.export_data(folder)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "导出成功",
                f"数据已导出:\n任务: {task_path}\n记录: {record_path}",
            )
