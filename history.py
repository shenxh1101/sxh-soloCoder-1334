from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDateEdit, QComboBox,
    QMessageBox, QFrame, QGroupBox,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
matplotlib.rcParams["axes.unicode_minus"] = False


TYPE_LABELS = {
    "work": ("🍅 专注", "#e74c3c"),
    "break": ("☕ 短休息", "#2ecc71"),
    "long_break": ("🛋 长休息", "#3498db"),
    "abandoned": ("❌ 放弃", "#95a5a6"),
    "skip_break": ("⏭ 跳过休息", "#95a5a6"),
}


WEEKDAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"]


def _minutes_to_color(minutes):
    if minutes <= 0:
        return "#f0f0f0"
    if minutes < 25:
        return "#fee5d9"
    if minutes < 50:
        return "#fcae91"
    if minutes < 100:
        return "#fb6a4a"
    if minutes < 200:
        return "#de2d26"
    return "#a50f15"


class HistoryPanel(QWidget):
    def __init__(self, db, on_jump_to_task=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.on_jump_to_task = on_jump_to_task
        self._current_date = datetime.now().strftime("%Y-%m-%d")
        self._setup_ui()
        try:
            self._refresh_all()
        except Exception:
            pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("📜 专注记录 · 工作日志")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title)
        header.addStretch()
        date_label = QLabel("当前日期:")
        date_label.setStyleSheet("font-size: 13px; color: #555;")
        header.addWidget(date_label)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self._on_date_changed)
        header.addWidget(self.date_edit)
        prev_btn = QPushButton("◀ 前一天")
        prev_btn.setStyleSheet(
            "background: #95a5a6; color: white; padding: 6px 12px; "
            "font-size: 12px; border-radius: 5px;"
        )
        prev_btn.clicked.connect(self._prev_day)
        header.addWidget(prev_btn)
        next_btn = QPushButton("后一天 ▶")
        next_btn.setStyleSheet(
            "background: #95a5a6; color: white; padding: 6px 12px; "
            "font-size: 12px; border-radius: 5px;"
        )
        next_btn.clicked.connect(self._next_day)
        header.addWidget(next_btn)
        today_btn = QPushButton("回到今天")
        today_btn.setStyleSheet(
            "background: #3498db; color: white; padding: 6px 12px; "
            "font-size: 12px; border-radius: 5px;"
        )
        today_btn.clicked.connect(self._go_today)
        header.addWidget(today_btn)
        layout.addLayout(header)
        heatmap_group = QGroupBox("📅 近 60 天专注热力图（点击日期可跳转）")
        heatmap_group.setStyleSheet(
            "QGroupBox { font-size: 13px; font-weight: bold; color: #2c3e50; "
            "border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }"
        )
        heatmap_layout = QVBoxLayout(heatmap_group)
        self.heatmap_figure = Figure(figsize=(9, 3.0), dpi=100)
        self.heatmap_canvas = FigureCanvas(self.heatmap_figure)
        try:
            self.heatmap_canvas.mpl_connect("button_press_event", self._on_heatmap_click)
        except Exception:
            pass
        heatmap_layout.addWidget(self.heatmap_canvas)
        layout.addWidget(heatmap_group)
        hourly_group = QGroupBox("⏰ 24 小时专注时段分布（近 60 天）")
        hourly_group.setStyleSheet(
            "QGroupBox { font-size: 13px; font-weight: bold; color: #2c3e50; "
            "border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; padding-top: 14px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }"
        )
        hourly_layout = QVBoxLayout(hourly_group)
        self.hourly_figure = Figure(figsize=(9, 1.8), dpi=100)
        self.hourly_canvas = FigureCanvas(self.hourly_figure)
        hourly_layout.addWidget(self.hourly_canvas)
        layout.addWidget(hourly_group)
        day_line = QFrame()
        day_line.setFrameShape(QFrame.Shape.HLine)
        day_line.setStyleSheet("color: #eee;")
        layout.addWidget(day_line)
        day_header = QHBoxLayout()
        self.day_title = QLabel()
        self.day_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #2c3e50;"
        )
        day_header.addWidget(self.day_title)
        day_header.addStretch()
        day_header.addWidget(QLabel("类型筛选:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", None)
        self.type_combo.addItem("🍅 专注", "work")
        self.type_combo.addItem("☕ 短休息", "break")
        self.type_combo.addItem("🛋 长休息", "long_break")
        self.type_combo.addItem("❌ 放弃", "abandoned")
        self.type_combo.currentIndexChanged.connect(self._refresh_daily_list)
        day_header.addWidget(self.type_combo)
        layout.addLayout(day_header)
        self.daily_summary = QLabel()
        self.daily_summary.setStyleSheet(
            "font-size: 13px; color: #555; padding: 6px 10px; "
            "background: #f8f9fa; border-radius: 6px;"
        )
        layout.addWidget(self.daily_summary)
        self.record_list = QListWidget()
        self.record_list.setMinimumHeight(160)
        self.record_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: #fafafa;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:hover {
                background: #f0f7ff;
            }
            QListWidget::item:selected {
                background: #dbeafe;
                color: #1e3a8a;
            }
        """)
        try:
            self.record_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        except Exception:
            pass
        layout.addWidget(self.record_list, stretch=1)
        tip = QLabel("💡 双击记录可跳转到对应任务 · 点击热力图中日期可切换")
        tip.setStyleSheet("font-size: 12px; color: #95a5a6;")
        layout.addWidget(tip)

    def _on_date_changed(self, date):
        self._current_date = date.toString("yyyy-MM-dd")
        try:
            self._refresh_daily_list()
        except Exception:
            pass

    def _prev_day(self):
        try:
            current = datetime.strptime(self._current_date, "%Y-%m-%d")
            prev = current - timedelta(days=1)
            self._current_date = prev.strftime("%Y-%m-%d")
            self.date_edit.blockSignals(True)
            self.date_edit.setDate(QDate(prev.year, prev.month, prev.day))
            self.date_edit.blockSignals(False)
            self._refresh_daily_list()
        except Exception:
            pass

    def _next_day(self):
        try:
            current = datetime.strptime(self._current_date, "%Y-%m-%d")
            next_day = current + timedelta(days=1)
            if next_day > datetime.now() + timedelta(days=1):
                QMessageBox.information(self, "提示", "无法跳转到未来~")
                return
            self._current_date = next_day.strftime("%Y-%m-%d")
            self.date_edit.blockSignals(True)
            self.date_edit.setDate(QDate(next_day.year, next_day.month, next_day.day))
            self.date_edit.blockSignals(False)
            self._refresh_daily_list()
        except Exception:
            pass

    def _go_today(self):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            self._current_date = today
            now = datetime.now()
            self.date_edit.blockSignals(True)
            self.date_edit.setDate(QDate(now.year, now.month, now.day))
            self.date_edit.blockSignals(False)
            self._refresh_daily_list()
        except Exception:
            pass

    def _refresh_all(self):
        try:
            self._refresh_heatmap()
        except Exception:
            pass
        try:
            self._refresh_hourly()
        except Exception:
            pass
        try:
            self._refresh_daily_list()
        except Exception:
            pass

    def _refresh_heatmap(self):
        try:
            data = self.db.get_daily_work_heatmap(60)
        except Exception:
            data = {"calendar": [], "total_minutes": 0, "active_days": 0, "hourly": []}
        self.heatmap_figure.clear()
        ax = self.heatmap_figure.add_subplot(111)
        calendar = data.get("calendar", [])
        if not calendar:
            ax.text(0.5, 0.5, "暂无专注数据", ha="center", va="center", fontsize=12, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
            self.heatmap_figure.suptitle("近 60 天专注时长（分钟/天）", fontsize=11, y=0.98)
            self.heatmap_figure.tight_layout(rect=(0, 0, 1, 0.95))
            self.heatmap_canvas.draw()
            return
        weeks = [[] for _ in range(7)]
        try:
            first_wd = calendar[0]["weekday"]
            for _ in range(first_wd):
                weeks[first_wd - 1 - _ if first_wd > 0 else 6 - _].append(None)
        except Exception:
            pass
        for i, item in enumerate(calendar):
            wd = item["weekday"]
            weeks[wd].append(item)
        max_weeks = max(len(w) for w in weeks) if weeks else 0
        rows = 7
        cols = max_weeks
        ax.set_xlim(0, cols)
        ax.set_ylim(0, rows)
        for r in range(rows):
            wd_items = weeks[r]
            for c in range(min(cols, len(wd_items))):
                item = wd_items[c]
                if item is None:
                    continue
                x = c
                y = rows - 1 - r
                m = item.get("minutes", 0)
                color = _minutes_to_color(m)
                rect = matplotlib.patches.Rectangle(
                    (x, y), 0.92, 0.92,
                    facecolor=color,
                    edgecolor="white",
                    linewidth=1,
                    zorder=2,
                )
                ax.add_patch(rect)
                date_str = item.get("date_short", "")
                ax.text(x + 0.46, y + 0.7, date_str,
                        ha="center", va="center", fontsize=7,
                        color="#333" if m < 50 else "white")
                if m > 0:
                    ax.text(x + 0.46, y + 0.25, f"{m}",
                            ha="center", va="center", fontsize=7,
                            color="#333" if m < 100 else "white",
                            fontweight="bold")
                item["_cell_x"] = x
                item["_cell_y"] = y
        self._calendar_cells = []
        for wd_items in weeks:
            for item in wd_items:
                if item is not None and "_cell_x" in item:
                    self._calendar_cells.append(item)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_frame_on(False)
        total = data.get("total_minutes", 0)
        active = data.get("active_days", 0)
        self.heatmap_figure.suptitle(
            f"近 60 天专注时长（分钟/天）  ·  总投入 {total} 分钟  ·  活跃 {active} 天",
            fontsize=11, y=0.98,
        )
        self.heatmap_figure.tight_layout(rect=(0, 0, 1, 0.95))
        self.heatmap_canvas.draw()

    def _on_heatmap_click(self, event):
        try:
            if event.inaxes is None:
                return
            x, y = event.xdata, event.ydata
            if x is None or y is None:
                return
            for item in getattr(self, "_calendar_cells", []):
                cx = item["_cell_x"]
                cy = item["_cell_y"]
                if cx <= x <= cx + 0.92 and cy <= y <= cy + 0.92:
                    self._current_date = item["date"]
                    dt = datetime.strptime(item["date"], "%Y-%m-%d")
                    self.date_edit.blockSignals(True)
                    self.date_edit.setDate(QDate(dt.year, dt.month, dt.day))
                    self.date_edit.blockSignals(False)
                    try:
                        self._refresh_daily_list()
                    except Exception:
                        pass
                    return
        except Exception:
            pass

    def _refresh_hourly(self):
        try:
            data = self.db.get_daily_work_heatmap(60)
            hourly = data.get("hourly", [])
        except Exception:
            hourly = [{"hour": h, "minutes": 0} for h in range(24)]
        self.hourly_figure.clear()
        ax = self.hourly_figure.add_subplot(111)
        hours = list(range(24))
        values = [0] * 24
        for h in hourly:
            if 0 <= h["hour"] < 24:
                values[h["hour"]] = h["minutes"]
        if sum(values) > 0:
            colors = []
            for v in values:
                if v == 0:
                    colors.append("#ecf0f1")
                elif v < max(values) * 0.3:
                    colors.append("#fcae91")
                elif v < max(values) * 0.7:
                    colors.append("#fb6a4a")
                else:
                    colors.append("#e74c3c")
            ax.bar(hours, values, color=colors, edgecolor="white", linewidth=0.5, width=0.85)
            ax.set_xticks(hours)
            ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=8)
            ax.set_ylabel("分钟")
            ax.set_ylim(0, max(values) * 1.25)
            ax.set_title("近 60 天每小时专注时长")
            for spine in ["top", "right"]:
                ax.spines[spine].set_visible(False)
        else:
            ax.text(0.5, 0.5, "暂无专注数据", ha="center", va="center", fontsize=12, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
        self.hourly_figure.tight_layout()
        self.hourly_canvas.draw()

    def _refresh_daily_list(self):
        start = f"{self._current_date}T00:00:00"
        end = f"{self._current_date}T23:59:59"
        record_type = self.type_combo.currentData()
        try:
            records = self.db.get_records_with_task_names(start, end, record_type)
        except Exception:
            records = []
        date_obj = None
        try:
            date_obj = datetime.strptime(self._current_date, "%Y-%m-%d")
        except Exception:
            date_obj = datetime.now()
        weekday = WEEKDAY_LABELS[date_obj.weekday()]
        self.day_title.setText(f"📌 {self._current_date}（周{weekday}）当日明细")
        self.record_list.clear()
        work_minutes = 0
        work_count = 0
        break_minutes = 0
        break_count = 0
        abandoned_count = 0
        if not records:
            no_data = QListWidgetItem("  —  当日暂无专注记录，开始一个番茄钟吧！")
            no_data.setForeground(QColor("#999"))
            self.record_list.addItem(no_data)
        for r in records:
            rtype = r.get("type", "work")
            label_info = TYPE_LABELS.get(rtype, ("❓ 未知", "#7f8c8d"))
            label, color = label_info
            duration = r.get("duration_minutes", 0)
            start_time = r.get("started_at", "")
            try:
                st = datetime.fromisoformat(start_time)
                end_time_str = r.get("ended_at", "")
                et = datetime.fromisoformat(end_time_str) if end_time_str else None
                time_range = f"{st.strftime('%H:%M')}-{et.strftime('%H:%M')}" if et else st.strftime("%H:%M")
            except (ValueError, TypeError):
                time_range = start_time
            task_name = r.get("task_name", "无")
            if not task_name:
                task_name = "无"
            cat = r.get("task_category") or ""
            cat_tag = f" [{cat}]" if cat else ""
            item_text = (
                f"  {time_range}  {label}  {duration}分钟"
                f"  —  {task_name}{cat_tag}"
            )
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, r)
            item.setForeground(QColor(color))
            font = item.font()
            font.setPointSize(10)
            item.setFont(font)
            if rtype == "work":
                work_minutes += duration
                work_count += 1
            elif rtype in ("break", "long_break"):
                break_minutes += duration
                break_count += 1
            elif rtype == "abandoned":
                abandoned_count += 1
            self.record_list.addItem(item)
        self.daily_summary.setText(
            f"共 {len(records)} 条记录 · "
            f"🍅 专注 {work_count} 次 / {work_minutes} 分钟 · "
            f"☕ 休息 {break_count} 次 / {break_minutes} 分钟"
            + (f" · ❌ 放弃 {abandoned_count} 次" if abandoned_count > 0 else "")
        )

    def _on_item_double_clicked(self, item):
        try:
            record = item.data(Qt.ItemDataRole.UserRole)
            if not record:
                return
            task_id = record.get("task_id")
            if task_id and self.on_jump_to_task:
                self.on_jump_to_task(task_id)
            elif not task_id:
                QMessageBox.information(self, "提示", "这条记录没有关联的任务。")
        except Exception:
            pass
