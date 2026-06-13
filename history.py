from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDateEdit, QComboBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QDate


TYPE_LABELS = {
    "work": ("🍅 专注", "#e74c3c"),
    "break": ("☕ 短休息", "#2ecc71"),
    "long_break": ("🛋 长休息", "#3498db"),
    "abandoned": ("❌ 放弃", "#95a5a6"),
    "skip_break": ("⏭ 跳过休息", "#95a5a6"),
}


class HistoryPanel(QWidget):
    def __init__(self, db, on_jump_to_task=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.on_jump_to_task = on_jump_to_task
        self._current_date = datetime.now().strftime("%Y-%m-%d")
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("📜 专注记录历史")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        header.addWidget(title)
        header.addStretch()
        date_label = QLabel("日期:")
        date_label.setStyleSheet("font-size: 13px;")
        header.addWidget(date_label)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self._on_date_changed)
        header.addWidget(self.date_edit)
        prev_btn = QPushButton("◀ 前一天")
        prev_btn.setStyleSheet("background: #95a5a6; color: white; padding: 6px 12px; font-size: 12px;")
        prev_btn.clicked.connect(self._prev_day)
        header.addWidget(prev_btn)
        next_btn = QPushButton("后一天 ▶")
        next_btn.setStyleSheet("background: #95a5a6; color: white; padding: 6px 12px; font-size: 12px;")
        next_btn.clicked.connect(self._next_day)
        header.addWidget(next_btn)
        layout.addLayout(header)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("类型筛选:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", None)
        self.type_combo.addItem("🍅 专注", "work")
        self.type_combo.addItem("☕ 短休息", "break")
        self.type_combo.addItem("🛋 长休息", "long_break")
        self.type_combo.addItem("❌ 放弃", "abandoned")
        self.type_combo.currentIndexChanged.connect(self._refresh)
        filter_layout.addWidget(self.type_combo)
        filter_layout.addStretch()
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 13px; color: #555; padding: 6px 10px; background: #f8f9fa; border-radius: 6px;")
        filter_layout.addWidget(self.summary_label)
        layout.addLayout(filter_layout)
        self.record_list = QListWidget()
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
        """)
        self.record_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.record_list, stretch=1)
        tip = QLabel("💡 双击记录可跳转到对应任务")
        tip.setStyleSheet("font-size: 12px; color: #95a5a6;")
        layout.addWidget(tip)

    def _on_date_changed(self, date):
        self._current_date = date.toString("yyyy-MM-dd")
        self._refresh()

    def _prev_day(self):
        current = datetime.strptime(self._current_date, "%Y-%m-%d")
        prev = current - timedelta(days=1)
        self._current_date = prev.strftime("%Y-%m-%d")
        self.date_edit.setDate(QDate(prev.year, prev.month, prev.day))

    def _next_day(self):
        current = datetime.strptime(self._current_date, "%Y-%m-%d")
        next_day = current + timedelta(days=1)
        if next_day > datetime.now():
            QMessageBox.information(self, "提示", "已经是最新的一天啦~")
            return
        self._current_date = next_day.strftime("%Y-%m-%d")
        self.date_edit.setDate(QDate(next_day.year, next_day.month, next_day.day))

    def _refresh(self):
        start = f"{self._current_date}T00:00:00"
        end = f"{self._current_date}T23:59:59"
        record_type = self.type_combo.currentData()
        records = self.db.get_records_with_task_names(start, end, record_type)
        self.record_list.clear()
        work_minutes = 0
        work_count = 0
        break_minutes = 0
        break_count = 0
        for r in records:
            rtype = r.get("type", "work")
            label_info = TYPE_LABELS.get(rtype, ("❓ 未知", "#7f8c8d"))
            label, color = label_info
            duration = r.get("duration_minutes", 0)
            start_time = r.get("started_at", "")
            try:
                st = datetime.fromisoformat(start_time)
                time_str = st.strftime("%H:%M")
            except (ValueError, TypeError):
                time_str = start_time
            task_name = r.get("task_name", "无")
            if not task_name:
                task_name = "无"
            item_text = f"  {time_str}  {label}  {duration}分钟  —  {task_name}"
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
            self.record_list.addItem(item)
        self.summary_label.setText(
            f"共 {len(records)} 条记录 · "
            f"🍅 专注 {work_count} 次 / {work_minutes} 分钟 · "
            f"☕ 休息 {break_count} 次 / {break_minutes} 分钟"
        )

    def _on_item_double_clicked(self, item):
        record = item.data(Qt.ItemDataRole.UserRole)
        if not record:
            return
        task_id = record.get("task_id")
        if task_id and self.on_jump_to_task:
            self.on_jump_to_task(task_id)
        elif not task_id:
            QMessageBox.information(self, "提示", "这条记录没有关联的任务。")
