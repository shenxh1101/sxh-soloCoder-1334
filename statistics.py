from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QComboBox,
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial"]
matplotlib.rcParams["axes.unicode_minus"] = False


CATEGORY_COLORS = [
    "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c",
    "#e67e22", "#34495e", "#d35400", "#27ae60", "#2980b9", "#8e44ad",
]


def _minutes_to_hhmm(minutes):
    if minutes <= 0:
        return "0分钟"
    h, m = divmod(minutes, 60)
    if h > 0 and m > 0:
        return f"{h}小时{m}分钟"
    if h > 0:
        return f"{h}小时"
    return f"{m}分钟"


def _safe(d, key, default=0):
    val = d.get(key) if isinstance(d, dict) else None
    if val is None:
        return default
    return val


class StatisticsPanel(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._setup_ui()
        try:
            self._refresh_today()
        except Exception:
            pass
        try:
            self._refresh_week()
        except Exception:
            pass
        try:
            self._refresh_month()
        except Exception:
            pass
        try:
            self._refresh_task_ranking()
        except Exception:
            pass
        try:
            self._refresh_category_ranking()
        except Exception:
            pass
        try:
            self._refresh_efficiency_trend()
        except Exception:
            pass
        try:
            self.tabs.currentChanged.connect(self._on_tab_changed)
        except Exception:
            pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        title = QLabel("📊 数据统计面板")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
            }
            QTabBar::tab {
                background: #f5f5f5;
                padding: 8px 20px;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 13px;
                color: #555;
            }
            QTabBar::tab:selected {
                background: white;
                color: #2c3e50;
                font-weight: bold;
            }
        """)
        self._build_today_tab()
        self._build_week_tab()
        self._build_month_tab()
        self._build_task_rank_tab()
        self._build_category_rank_tab()
        layout.addWidget(self.tabs)
        eff_label = QLabel("📈 近 14 天效率趋势（柱状=专注分钟，折线=效率）")
        eff_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; margin-top: 6px;")
        layout.addWidget(eff_label)
        self.eff_figure = Figure(figsize=(9.2, 3.6), dpi=100)
        self.eff_canvas = FigureCanvas(self.eff_figure)
        layout.addWidget(self.eff_canvas)

    def _build_today_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        self.today_summary = QLabel()
        self.today_summary.setWordWrap(True)
        self.today_summary.setStyleSheet(
            "padding: 12px; background: linear-gradient(90deg, #f8f9fa, #e3f2fd);"
            "border-radius: 8px; font-size: 13px; line-height: 1.7;"
        )
        lay.addWidget(self.today_summary)
        self.today_figure = Figure(figsize=(8.6, 3.2), dpi=100)
        self.today_canvas = FigureCanvas(self.today_figure)
        lay.addWidget(self.today_canvas)
        self.tabs.addTab(widget, "今日")

    def _build_week_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        self.week_summary = QLabel()
        self.week_summary.setWordWrap(True)
        self.week_summary.setStyleSheet(
            "padding: 12px; background: linear-gradient(90deg, #f8f9fa, #e8f5e9);"
            "border-radius: 8px; font-size: 13px; line-height: 1.7;"
        )
        lay.addWidget(self.week_summary)
        self.week_figure = Figure(figsize=(8.6, 3.2), dpi=100)
        self.week_canvas = FigureCanvas(self.week_figure)
        lay.addWidget(self.week_canvas)
        self.tabs.addTab(widget, "本周")

    def _build_month_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        self.month_summary = QLabel()
        self.month_summary.setWordWrap(True)
        self.month_summary.setStyleSheet(
            "padding: 12px; background: linear-gradient(90deg, #f8f9fa, #fff3e0);"
            "border-radius: 8px; font-size: 13px; line-height: 1.7;"
        )
        lay.addWidget(self.month_summary)
        self.month_figure = Figure(figsize=(8.6, 3.2), dpi=100)
        self.month_canvas = FigureCanvas(self.month_figure)
        lay.addWidget(self.month_canvas)
        self.tabs.addTab(widget, "本月")

    def _build_task_rank_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        top = QHBoxLayout()
        top.addWidget(QLabel("统计周期:"))
        self.task_period_combo = QComboBox()
        self.task_period_combo.addItem("今日", "today")
        self.task_period_combo.addItem("本周", "week")
        self.task_period_combo.addItem("本月", "month")
        self.task_period_combo.addItem("全部", "all")
        self.task_period_combo.setCurrentIndex(1)
        try:
            self.task_period_combo.currentIndexChanged.connect(self._refresh_task_ranking)
        except Exception:
            pass
        top.addWidget(self.task_period_combo)
        top.addStretch()
        self.task_rank_summary = QLabel()
        self.task_rank_summary.setStyleSheet("font-size: 12px; color: #666;")
        top.addWidget(self.task_rank_summary)
        lay.addLayout(top)
        self.task_rank_figure = Figure(figsize=(8.6, 4.0), dpi=100)
        self.task_rank_canvas = FigureCanvas(self.task_rank_figure)
        lay.addWidget(self.task_rank_canvas)
        self.tabs.addTab(widget, "任务排行")

    def _build_category_rank_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        top = QHBoxLayout()
        top.addWidget(QLabel("统计周期:"))
        self.category_period_combo = QComboBox()
        self.category_period_combo.addItem("今日", "today")
        self.category_period_combo.addItem("本周", "week")
        self.category_period_combo.addItem("本月", "month")
        self.category_period_combo.addItem("全部", "all")
        self.category_period_combo.setCurrentIndex(1)
        try:
            self.category_period_combo.currentIndexChanged.connect(self._refresh_category_ranking)
        except Exception:
            pass
        top.addWidget(self.category_period_combo)
        top.addStretch()
        self.category_rank_summary = QLabel()
        self.category_rank_summary.setStyleSheet("font-size: 12px; color: #666;")
        top.addWidget(self.category_rank_summary)
        lay.addLayout(top)
        plot_row = QHBoxLayout()
        self.category_pie_figure = Figure(figsize=(3.6, 3.2), dpi=100)
        self.category_pie_canvas = FigureCanvas(self.category_pie_figure)
        plot_row.addWidget(self.category_pie_canvas, 3)
        self.category_bar_figure = Figure(figsize=(5.0, 3.2), dpi=100)
        self.category_bar_canvas = FigureCanvas(self.category_bar_figure)
        plot_row.addWidget(self.category_bar_canvas, 5)
        lay.addLayout(plot_row)
        self.tabs.addTab(widget, "分类排行")

    def _today_range(self):
        today = datetime.now()
        start = today.strftime("%Y-%m-%d") + "T00:00:00"
        end = today.strftime("%Y-%m-%d") + "T23:59:59"
        return start, end

    def _week_range(self):
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        next_mon = monday + timedelta(days=7)
        return (monday.strftime("%Y-%m-%d") + "T00:00:00",
                next_mon.strftime("%Y-%m-%d") + "T00:00:00")

    def _month_range(self):
        today = datetime.now()
        first = today.replace(day=1)
        if first.month == 12:
            next_first = first.replace(year=first.year + 1, month=1, day=1)
        else:
            next_first = first.replace(month=first.month + 1, day=1)
        return (first.strftime("%Y-%m-%d") + "T00:00:00",
                next_first.strftime("%Y-%m-%d") + "T00:00:00")

    def _period_range(self, combo):
        try:
            period = combo.currentData()
        except Exception:
            period = "week"
        if period == "today":
            return self._today_range()
        if period == "month":
            return self._month_range()
        if period == "all":
            return ("1970-01-01T00:00:00", "2999-12-31T23:59:59")
        return self._week_range()

    def _on_tab_changed(self, index):
        try:
            tab_name = self.tabs.tabText(index)
            if tab_name == "今日":
                self._refresh_today()
            elif tab_name == "本周":
                self._refresh_week()
            elif tab_name == "本月":
                self._refresh_month()
            elif tab_name == "任务排行":
                self._refresh_task_ranking()
            elif tab_name == "分类排行":
                self._refresh_category_ranking()
        except Exception:
            pass

    def _refresh_today(self):
        self.today_figure.clear()
        ax = self.today_figure.add_subplot(111)
        try:
            start, end = self._today_range()
            stats = self.db.get_summary(start, end)
        except Exception:
            stats = {}
        work = _safe(stats, "work_minutes")
        brk = _safe(stats, "break_minutes") + _safe(stats, "long_break_minutes")
        total = work + brk
        completed = _safe(stats, "task_completed_count")
        wc = _safe(stats, "work_count")
        bc = _safe(stats, "break_count") + _safe(stats, "long_break_count")
        today_label = datetime.now().strftime("%Y年%m月%d日")
        self.today_summary.setText(
            f"<b>📆 {today_label}（今天）</b><br>"
            f"🍅 专注 <b>{wc}</b> 次，共 <b>{_minutes_to_hhmm(work)}</b>　"
            f"☕ 休息 <b>{bc}</b> 次，共 <b>{_minutes_to_hhmm(brk)}</b><br>"
            f"✅ 完成任务 <b>{completed}</b> 个　"
            f"🕒 总计时 <b>{_minutes_to_hhmm(total)}</b>"
        )
        if total <= 0:
            ax.text(0.5, 0.5, "今日暂无记录，加油开始吧！",
                    ha="center", va="center", fontsize=12, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
            self.today_figure.tight_layout()
            self.today_canvas.draw()
            return
        work_short = _safe(stats, "break_minutes")
        long_brk = _safe(stats, "long_break_minutes")
        labels = ["专注", "短休息", "长休息"]
        values = [work, work_short, long_brk]
        colors = ["#e74c3c", "#2ecc71", "#3498db"]
        non_zero_count = sum(1 for v in values if v > 0)
        if non_zero_count <= 1:
            ax.bar(labels, values, color=colors, width=0.5, edgecolor="white", linewidth=1)
            for i, v in enumerate(values):
                if v > 0:
                    ax.text(i, v + max(values) * 0.02,
                            f"{v}分钟", ha="center", fontsize=9, fontweight="bold")
            ax.set_ylabel("分钟")
            ax.set_title(f"{today_label} 时长分布")
            for spine in ["top", "right"]:
                ax.spines[spine].set_visible(False)
        else:
            filtered = [(l, v, c) for l, v, c in zip(labels, values, colors) if v > 0]
            ls = [x[0] for x in filtered]
            vs = [x[1] for x in filtered]
            cs = [x[2] for x in filtered]
            explode = [0.03] * len(ls)
            wedges, texts, autotexts = ax.pie(
                vs, labels=ls, colors=cs, explode=explode,
                autopct="%1.1f%%", startangle=90, textprops={"fontsize": 10},
                pctdistance=0.75, wedgeprops={"edgecolor": "white", "linewidth": 1.5},
            )
            for at in autotexts:
                at.set_fontsize(9)
                at.set_fontweight("bold")
                at.set_color("white")
            ax.set_title(f"{today_label} 时长占比")
        self.today_figure.tight_layout()
        self.today_canvas.draw()

    def _refresh_week(self):
        self.week_figure.clear()
        ax = self.week_figure.add_subplot(111)
        try:
            start, end = self._week_range()
            stats = self.db.get_summary(start, end)
        except Exception:
            stats = {}
        work = _safe(stats, "work_minutes")
        brk = _safe(stats, "break_minutes") + _safe(stats, "long_break_minutes")
        total = work + brk
        completed = _safe(stats, "task_completed_count")
        wc = _safe(stats, "work_count")
        try:
            start_dt = datetime.strptime(start[:10], "%Y-%m-%d")
            end_dt = datetime.strptime(end[:10], "%Y-%m-%d")
            week_label = f"{start_dt.strftime('%m月%d日')} ~ {end_dt.strftime('%m月%d日')}"
        except Exception:
            week_label = "本周"
        self.week_summary.setText(
            f"<b>📆 本周（{week_label}）</b><br>"
            f"🍅 专注 <b>{wc}</b> 次，共 <b>{_minutes_to_hhmm(work)}</b>　"
            f"☕ 休息共 <b>{_minutes_to_hhmm(brk)}</b><br>"
            f"✅ 完成任务 <b>{completed}</b> 个　"
            f"🕒 总计时 <b>{_minutes_to_hhmm(total)}</b>"
        )
        days = []
        day_minutes = []
        today = datetime.now()
        try:
            for i in range(7):
                d = start_dt + timedelta(days=i)
                d_str = d.strftime("%m-%d")
                days.append(f"周{['一','二','三','四','五','六','日'][d.weekday()]}\n{d_str}")
                try:
                    s = d.strftime("%Y-%m-%d") + "T00:00:00"
                    e = d.strftime("%Y-%m-%d") + "T23:59:59"
                    ds = self.db.get_summary(s, e)
                    day_minutes.append(_safe(ds, "work_minutes"))
                except Exception:
                    day_minutes.append(0)
        except Exception:
            pass
        if not day_minutes or all(m == 0 for m in day_minutes):
            ax.text(0.5, 0.5, "本周暂无专注数据",
                    ha="center", va="center", fontsize=12, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
            self.week_figure.tight_layout()
            self.week_canvas.draw()
            return
        max_m = max(day_minutes) if day_minutes else 1
        colors = []
        for m in day_minutes:
            if m <= 0:
                colors.append("#ecf0f1")
            elif m < max_m * 0.3:
                colors.append("#fcae91")
            elif m < max_m * 0.7:
                colors.append("#fb6a4a")
            else:
                colors.append("#e74c3c")
        ax.bar(range(len(days)), day_minutes, color=colors,
               edgecolor="white", linewidth=1, width=0.6)
        ax.set_xticks(range(len(days)))
        ax.set_xticklabels(days, fontsize=9)
        for i, v in enumerate(day_minutes):
            if v > 0:
                ax.text(i, v + max_m * 0.03,
                        f"{v}", ha="center", fontsize=9, fontweight="bold", color="#c0392b")
        ax.set_ylabel("专注分钟")
        ax.set_title("本周每日专注时长")
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        self.week_figure.tight_layout()
        self.week_canvas.draw()

    def _refresh_month(self):
        self.month_figure.clear()
        ax = self.month_figure.add_subplot(111)
        try:
            start, end = self._month_range()
            stats = self.db.get_summary(start, end)
        except Exception:
            stats = {}
        work = _safe(stats, "work_minutes")
        brk = _safe(stats, "break_minutes") + _safe(stats, "long_break_minutes")
        total = work + brk
        completed = _safe(stats, "task_completed_count")
        wc = _safe(stats, "work_count")
        month_label = datetime.now().strftime("%Y年%m月")
        self.month_summary.setText(
            f"<b>📆 {month_label}（本月）</b><br>"
            f"🍅 专注 <b>{wc}</b> 次，共 <b>{_minutes_to_hhmm(work)}</b>　"
            f"☕ 休息共 <b>{_minutes_to_hhmm(brk)}</b><br>"
            f"✅ 完成任务 <b>{completed}</b> 个　"
            f"🕒 总计时 <b>{_minutes_to_hhmm(total)}</b>"
        )
        today = datetime.now()
        first = today.replace(day=1)
        day_labels = []
        minute_data = []
        for d in range(1, today.day + 1):
            current = first.replace(day=d)
            day_labels.append(f"{d}")
            try:
                s = current.strftime("%Y-%m-%d") + "T00:00:00"
                e = current.strftime("%Y-%m-%d") + "T23:59:59"
                ds = self.db.get_summary(s, e)
                minute_data.append(_safe(ds, "work_minutes"))
            except Exception:
                minute_data.append(0)
        if not minute_data or all(m == 0 for m in minute_data):
            ax.text(0.5, 0.5, "本月暂无专注数据",
                    ha="center", va="center", fontsize=12, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
            self.month_figure.tight_layout()
            self.month_canvas.draw()
            return
        ax.plot(range(len(day_labels)), minute_data, marker="o", markersize=4,
                linewidth=2, color="#e74c3c", markerfacecolor="#fcae91")
        ax.fill_between(range(len(day_labels)), minute_data, alpha=0.15, color="#e74c3c")
        ax.set_xticks(range(len(day_labels)))
        ax.set_xticklabels(day_labels, fontsize=9)
        for i, t in enumerate(ax.get_xticklabels()):
            if (i + 1) % 3 != 0 and i != len(day_labels) - 1:
                t.set_visible(False)
        max_m = max(minute_data) if minute_data else 1
        for i, v in enumerate(minute_data):
            if v > 0:
                ax.text(i, v + max_m * 0.02,
                        str(v), ha="center", fontsize=8, color="#c0392b")
        ax.set_ylabel("专注分钟")
        ax.set_title("本月每日专注时长走势")
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        self.month_figure.tight_layout()
        self.month_canvas.draw()

    def _refresh_task_ranking(self):
        self.task_rank_figure.clear()
        ax = self.task_rank_figure.add_subplot(111)
        try:
            start, end = self._period_range(self.task_period_combo)
            ranking = self.db.get_task_time_ranking(start, end, limit=12)
        except Exception:
            ranking = []
        total = sum(_safe(r, "total_minutes") for r in ranking)
        tasks_count = len(ranking)
        self.task_rank_summary.setText(f"共 {tasks_count} 个任务 · 总投入 {total} 分钟")
        if not ranking:
            ax.text(0.5, 0.5, "此周期暂无任务投入数据",
                    ha="center", va="center", fontsize=12, color="#999")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
            self.task_rank_figure.tight_layout()
            self.task_rank_canvas.draw()
            return
        names = []
        minutes = []
        pomodoros = []
        for r in ranking:
            cat = r.get("task_category") or ""
            n = r.get("task_name", "未知")
            names.append(f"[{cat}] {n}" if cat else n)
            minutes.append(_safe(r, "total_minutes"))
            pomodoros.append(_safe(r, "pomodoro_count"))
        names_rev = names[::-1]
        minutes_rev = minutes[::-1]
        pomodoros_rev = pomodoros[::-1]
        bar_colors = [CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i in range(len(names_rev))]
        ax.barh(names_rev, minutes_rev, color=bar_colors,
                edgecolor="white", linewidth=1.2, height=0.6)
        max_m = max(minutes_rev) if minutes_rev else 1
        for i, (m, p) in enumerate(zip(minutes_rev, pomodoros_rev)):
            label = f"{m}分钟 ({p}🍅)"
            ax.text(m + max_m * 0.015, i, label,
                    va="center", fontsize=9, fontweight="bold", color="#333")
        ax.set_xlabel("投入分钟")
        ax.set_title(f"任务投入排行 Top {len(names_rev)}")
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        self.task_rank_figure.tight_layout()
        self.task_rank_canvas.draw()

    def _refresh_category_ranking(self):
        self.category_pie_figure.clear()
        self.category_bar_figure.clear()
        pie_ax = self.category_pie_figure.add_subplot(111)
        bar_ax = self.category_bar_figure.add_subplot(111)
        try:
            start, end = self._period_range(self.category_period_combo)
            ranking = self.db.get_category_time_ranking(start, end, limit=10)
        except Exception:
            ranking = []
        total = sum(_safe(r, "total_minutes") for r in ranking)
        cats_count = len(ranking)
        self.category_rank_summary.setText(f"共 {cats_count} 类 · 总投入 {total} 分钟")
        if not ranking:
            for ax in [pie_ax, bar_ax]:
                ax.text(0.5, 0.5, "暂无分类数据",
                        ha="center", va="center", fontsize=12, color="#999")
                ax.set_xticks([])
                ax.set_yticks([])
                ax.set_frame_on(False)
            self.category_pie_figure.tight_layout()
            self.category_pie_canvas.draw()
            self.category_bar_figure.tight_layout()
            self.category_bar_canvas.draw()
            return
        cats = [r.get("category") or "未分类" for r in ranking]
        minutes = [_safe(r, "total_minutes") for r in ranking]
        pomodoros = [_safe(r, "pomodoro_count") for r in ranking]
        task_counts = [_safe(r, "task_count") for r in ranking]
        colors = [CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i in range(len(cats))]
        cats_rev = cats[::-1]
        minutes_rev = minutes[::-1]
        pomodoros_rev = pomodoros[::-1]
        task_counts_rev = task_counts[::-1]
        colors_rev = colors[::-1]
        max_m = max(minutes_rev) if minutes_rev else 1
        bar_ax.barh(cats_rev, minutes_rev, color=colors_rev,
                    edgecolor="white", linewidth=1.2, height=0.6)
        for i, (m, p, t) in enumerate(zip(minutes_rev, pomodoros_rev, task_counts_rev)):
            label = f"{m}分钟 ({p}🍅, {t}任务)"
            bar_ax.text(m + max_m * 0.015, i, label,
                        va="center", fontsize=9, fontweight="bold", color="#333")
        bar_ax.set_xlabel("投入分钟")
        bar_ax.set_title("分类投入排行")
        for spine in ["top", "right"]:
            bar_ax.spines[spine].set_visible(False)
        pie_data = [(c, m, col) for c, m, col in zip(cats, minutes, colors) if m > 0]
        if pie_data and len(pie_data) > 1:
            pie_cats = [x[0] for x in pie_data]
            pie_mins = [x[1] for x in pie_data]
            pie_cols = [x[2] for x in pie_data]
            explode = [0.03] * len(pie_cats)
            wedges, texts, autotexts = pie_ax.pie(
                pie_mins, labels=pie_cats, colors=pie_cols, explode=explode,
                autopct="%1.1f%%", startangle=90, textprops={"fontsize": 9},
                pctdistance=0.72, wedgeprops={"edgecolor": "white", "linewidth": 1.5},
            )
            for at in autotexts:
                at.set_fontsize(8)
                at.set_fontweight("bold")
                at.set_color("white")
            pie_ax.set_title("分类占比")
        else:
            if pie_data:
                pie_ax.text(0.5, 0.65, pie_data[0][0],
                            ha="center", va="center", fontsize=12, fontweight="bold", color="#333")
                pie_ax.text(0.5, 0.4, f"{pie_data[0][1]}分钟\n100%",
                            ha="center", va="center", fontsize=10, color="#555")
            pie_ax.set_xticks([])
            pie_ax.set_yticks([])
            pie_ax.set_frame_on(False)
            pie_ax.set_title("分类占比")
        self.category_pie_figure.tight_layout()
        self.category_pie_canvas.draw()
        self.category_bar_figure.tight_layout()
        self.category_bar_canvas.draw()

    def _refresh_efficiency_trend(self):
        self.eff_figure.clear()
        ax1 = self.eff_figure.add_subplot(111)
        ax2 = ax1.twinx()
        try:
            trend = self.db.get_efficiency_trend(days=14)
        except Exception:
            trend = []
        if not trend:
            ax1.text(0.5, 0.5, "暂无效率数据",
                     ha="center", va="center", fontsize=12, color="#999",
                     transform=ax1.transAxes)
            ax1.set_xticks([])
            ax1.set_yticks([])
            ax2.set_yticks([])
            for spine in ["top", "right", "left", "bottom"]:
                ax1.spines[spine].set_visible(False)
            self.eff_figure.tight_layout()
            self.eff_canvas.draw()
            return
        day_labels = [f"{x.get('date', x.get('date_short', ''))}\n周{['一','二','三','四','五','六','日'][datetime.strptime(x.get('date_full', x.get('date', '')), '%Y-%m-%d').weekday()]}" if x.get('date_full') else x.get('date', x.get('date_short', '')) for x in trend]
        minutes = [x.get("minutes", x.get("work_minutes", 0)) or 0 for x in trend]
        efficiencies = [x.get("efficiency", 0) or 0 for x in trend]
        tasks_list = [x.get("tasks", x.get("tasks_completed", 0)) or 0 for x in trend]
        xs = list(range(len(day_labels)))
        bar_colors = []
        max_min = max(minutes) if minutes else 1
        for m in minutes:
            if m <= 0:
                bar_colors.append("#ecf0f1")
            elif m < max_min * 0.3:
                bar_colors.append("#fcae91")
            elif m < max_min * 0.7:
                bar_colors.append("#fb6a4a")
            else:
                bar_colors.append("#e74c3c")
        ax1.bar(xs, minutes, color=bar_colors, alpha=0.85, width=0.6,
                edgecolor="white", linewidth=1, label="专注分钟")
        ax1.set_ylabel("专注分钟", color="#e74c3c", fontsize=10)
        ax1.tick_params(axis="y", labelcolor="#e74c3c", labelsize=9)
        ax1.set_xticks(xs)
        ax1.set_xticklabels(day_labels, fontsize=8)
        for i, v in enumerate(minutes):
            if v > 0:
                ax1.text(i, v + max_min * 0.02,
                         str(v), ha="center", fontsize=7.5,
                         color="#c0392b", fontweight="bold")
        line_color = "#2980b9"
        ax2.plot(xs, efficiencies, color=line_color, marker="D", markersize=5,
                 linewidth=2, label="效率(任务/h)", markerfacecolor="white", markeredgewidth=2)
        ax2.set_ylabel("效率 (任务/小时)", color=line_color, fontsize=10)
        ax2.tick_params(axis="y", labelcolor=line_color, labelsize=9)
        max_eff = max(efficiencies) if efficiencies else 1
        if max_eff > 0:
            for i, v in enumerate(efficiencies):
                if v > 0:
                    ax2.text(i, v + max_eff * 0.08,
                             f"{v:.1f}", ha="center", fontsize=7.5,
                             color=line_color, fontweight="bold")
        max_idx = minutes.index(max_min) if max_min > 0 else 0
        best_eff = max(efficiencies) if efficiencies else 0
        best_eff_idx = efficiencies.index(best_eff) if best_eff > 0 else 0
        for spine in ["top"]:
            ax1.spines[spine].set_visible(False)
            ax2.spines[spine].set_visible(False)
        title = f"近 14 天 专注时长 & 效率趋势  ·  最投入: {day_labels[max_idx].replace(chr(10), ' ')} ({max_min}分钟)  ·  最高效: {day_labels[best_eff_idx].replace(chr(10), ' ')} ({best_eff:.1f}任务/h)"
        self.eff_figure.suptitle(title, fontsize=10, y=0.97)
        self.eff_figure.tight_layout(rect=(0, 0, 1, 0.93))
        self.eff_canvas.draw()

    def refresh_all(self):
        for fn in [self._refresh_today, self._refresh_week, self._refresh_month,
                   self._refresh_task_ranking, self._refresh_category_ranking,
                   self._refresh_efficiency_trend]:
            try:
                fn()
            except Exception:
                pass
