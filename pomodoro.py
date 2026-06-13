from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QListWidget, QListWidgetItem, QLineEdit,
    QSpinBox, QSlider, QDialog, QFormLayout, QGroupBox,
    QCheckBox, QStackedWidget, QSizePolicy, QMessageBox,
    QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPoint, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient, QAction, QIcon, QPixmap
from database import Database
from audio import AudioPlayer, SOUND_TYPES, ensure_sound_files
from overlay import ScreenOverlay, WebsiteBlocker
from statistics import StatisticsPanel


class CircularProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0.0
        self._time_text = "25:00"
        self._status_text = "准备就绪"
        self._color = QColor(231, 76, 60)
        self._bg_color = QColor(236, 240, 241)
        self.setMinimumSize(280, 280)
        self.setMaximumSize(320, 320)

    def set_progress(self, value):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    def set_time_text(self, text):
        self._time_text = text
        self.update()

    def set_status_text(self, text):
        self._status_text = text
        self.update()

    def set_color(self, color):
        self._color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 320.0, side / 320.0)
        pen_width = 14
        radius = 130
        bg_pen = QPen(QBrush(self._bg_color), pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(int(-radius), int(-radius), int(2 * radius), int(2 * radius), 0, 360 * 16)
        if self._progress > 0:
            gradient = QRadialGradient(0, 0, radius)
            gradient.setColorAt(0, self._color.lighter(110))
            gradient.setColorAt(1, self._color)
            fg_pen = QPen(QBrush(gradient), pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(fg_pen)
            span = int(-self._progress * 360 * 16)
            painter.drawArc(int(-radius), int(-radius), int(2 * radius), int(2 * radius), 90 * 16, span)
        painter.setPen(Qt.PenStyle.NoPen)
        inner_radius = radius - pen_width / 2 - 20
        inner_gradient = QRadialGradient(0, 0, inner_radius)
        inner_gradient.setColorAt(0, QColor(255, 255, 255, 250))
        inner_gradient.setColorAt(1, QColor(245, 245, 245, 250))
        painter.setBrush(QBrush(inner_gradient))
        painter.drawEllipse(QPointF(0, 0), inner_radius, inner_radius)
        painter.setPen(QPen(QColor(44, 62, 80)))
        time_font = QFont("Consolas", 42, QFont.Weight.Bold)
        painter.setFont(time_font)
        painter.drawText(QRectF(-100, -40, 200, 60), Qt.AlignmentFlag.AlignCenter, self._time_text)
        status_font = QFont("Microsoft YaHei", 12)
        painter.setFont(status_font)
        painter.setPen(QPen(QColor(149, 165, 166)))
        painter.drawText(QRectF(-100, 20, 200, 30), Qt.AlignmentFlag.AlignCenter, self._status_text)
        painter.end()


class SettingsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("设置")
        self.setMinimumWidth(450)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        timer_group = QGroupBox("⏱ 番茄钟时长")
        timer_layout = QFormLayout()
        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setSuffix(" 分钟")
        timer_layout.addRow("工作时长:", self.work_spin)
        self.break_spin = QSpinBox()
        self.break_spin.setRange(1, 60)
        self.break_spin.setSuffix(" 分钟")
        timer_layout.addRow("短休息时长:", self.break_spin)
        self.long_break_spin = QSpinBox()
        self.long_break_spin.setRange(5, 60)
        self.long_break_spin.setSuffix(" 分钟")
        timer_layout.addRow("长休息时长:", self.long_break_spin)
        self.long_break_interval_spin = QSpinBox()
        self.long_break_interval_spin.setRange(2, 10)
        self.long_break_interval_spin.setSuffix(" 个番茄钟")
        timer_layout.addRow("长休息间隔:", self.long_break_interval_spin)
        timer_group.setLayout(timer_layout)
        layout.addWidget(timer_group)
        site_group = QGroupBox("🚫 干扰网站")
        site_layout = QVBoxLayout()
        self.site_list = QListWidget()
        site_layout.addWidget(self.site_list)
        site_input_layout = QHBoxLayout()
        self.site_input = QLineEdit()
        self.site_input.setPlaceholderText("输入网站域名，如: youtube.com")
        site_input_layout.addWidget(self.site_input)
        add_site_btn = QPushButton("添加")
        add_site_btn.clicked.connect(self._add_site)
        site_input_layout.addWidget(add_site_btn)
        remove_site_btn = QPushButton("移除选中")
        remove_site_btn.clicked.connect(self._remove_site)
        site_input_layout.addWidget(remove_site_btn)
        site_layout.addLayout(site_input_layout)
        site_group.setLayout(site_layout)
        layout.addWidget(site_group)
        misc_group = QGroupBox("⚙ 其他设置")
        misc_layout = QFormLayout()
        self.auto_start_check = QCheckBox("休息结束后自动开始下一个番茄钟")
        misc_layout.addRow(self.auto_start_check)
        self.overlay_check = QCheckBox("工作时显示屏幕边缘遮罩")
        self.overlay_check.setChecked(True)
        misc_layout.addRow(self.overlay_check)
        self.block_check = QCheckBox("工作时屏蔽干扰网站 (需要管理员权限)")
        misc_layout.addRow(self.block_check)
        misc_group.setLayout(misc_layout)
        layout.addWidget(misc_group)
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("background: #27ae60; color: white; padding: 8px 30px; border-radius: 6px; font-size: 14px;")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("padding: 8px 30px; border-radius: 6px; font-size: 14px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _load_settings(self):
        self.work_spin.setValue(self.db.get_config("work_duration", 25))
        self.break_spin.setValue(self.db.get_config("break_duration", 5))
        self.long_break_spin.setValue(self.db.get_config("long_break_duration", 15))
        self.long_break_interval_spin.setValue(self.db.get_config("long_break_interval", 4))
        self.auto_start_check.setChecked(self.db.get_config("auto_start", False))
        self.overlay_check.setChecked(self.db.get_config("show_overlay", True))
        self.block_check.setChecked(self.db.get_config("block_sites", False))
        self.site_list.clear()
        for site in self.db.get_blocked_sites():
            self.site_list.addItem(site)

    def _add_site(self):
        site = self.site_input.text().strip()
        if site:
            self.db.add_blocked_site(site)
            self.site_list.addItem(site)
            self.site_input.clear()

    def _remove_site(self):
        current = self.site_list.currentItem()
        if current:
            self.db.remove_blocked_site(current.text())
            self.site_list.takeItem(self.site_list.row(current))

    def _save(self):
        self.db.set_config("work_duration", self.work_spin.value())
        self.db.set_config("break_duration", self.break_spin.value())
        self.db.set_config("long_break_duration", self.long_break_spin.value())
        self.db.set_config("long_break_interval", self.long_break_interval_spin.value())
        self.db.set_config("auto_start", self.auto_start_check.isChecked())
        self.db.set_config("show_overlay", self.overlay_check.isChecked())
        self.db.set_config("block_sites", self.block_check.isChecked())
        self.accept()


class PomodoroWindow(QWidget):
    STATE_IDLE = "idle"
    STATE_WORK = "work"
    STATE_BREAK = "break"
    STATE_LONG_BREAK = "long_break"

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.audio_player = AudioPlayer()
        self.overlay = ScreenOverlay()
        self.website_blocker = WebsiteBlocker()
        self.state = self.STATE_IDLE
        self.total_seconds = 0
        self.remaining_seconds = 0
        self.current_task_id = None
        self.pomodoro_count = 0
        self.session_started_at = None
        self._init_configs()
        self._setup_ui()
        self._setup_timer()
        self._setup_tray()
        self._refresh_tasks()

    def _init_configs(self):
        self.work_duration = self.db.get_config("work_duration", 25)
        self.break_duration = self.db.get_config("break_duration", 5)
        self.long_break_duration = self.db.get_config("long_break_duration", 15)
        self.long_break_interval = self.db.get_config("long_break_interval", 4)
        self.auto_start = self.db.get_config("auto_start", False)
        self.show_overlay = self.db.get_config("show_overlay", True)
        self.block_sites = self.db.get_config("block_sites", False)

    def _setup_ui(self):
        self.setWindowTitle("🍅 番茄钟与专注助手")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        self.setStyleSheet("""
            QWidget { font-family: "Microsoft YaHei", "SimHei", sans-serif; }
            QPushButton {
                border: none; padding: 10px 24px; border-radius: 8px;
                font-size: 14px; font-weight: bold;
            }
            QListWidget {
                border: 1px solid #ddd; border-radius: 8px;
                padding: 4px; background: #fafafa;
            }
            QListWidget::item { padding: 8px; border-radius: 4px; }
            QListWidget::item:selected { background: #e74c3c; color: white; }
            QComboBox {
                padding: 6px 12px; border: 1px solid #ddd;
                border-radius: 6px; background: white;
            }
            QLineEdit {
                padding: 8px 12px; border: 1px solid #ddd;
                border-radius: 6px; background: white;
            }
            QSpinBox {
                padding: 6px; border: 1px solid #ddd;
                border-radius: 6px; background: white;
            }
            QSlider::groove:horizontal {
                height: 6px; background: #ddd; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px; height: 16px; margin: -5px 0;
                background: #e74c3c; border-radius: 8px;
            }
        """)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        task_label = QLabel("📋 任务清单")
        task_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        left_layout.addWidget(task_label)
        task_input_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("添加新任务...")
        self.task_input.returnPressed.connect(self._add_task)
        task_input_layout.addWidget(self.task_input)
        add_task_btn = QPushButton("+")
        add_task_btn.setFixedSize(36, 36)
        add_task_btn.setStyleSheet("background: #27ae60; color: white; border-radius: 18px; font-size: 18px; padding: 0;")
        add_task_btn.clicked.connect(self._add_task)
        task_input_layout.addWidget(add_task_btn)
        left_layout.addLayout(task_input_layout)
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("番茄数:"))
        self.pomodoro_target_spin = QSpinBox()
        self.pomodoro_target_spin.setRange(1, 20)
        self.pomodoro_target_spin.setValue(1)
        target_layout.addWidget(self.pomodoro_target_spin)
        target_layout.addStretch()
        left_layout.addLayout(target_layout)
        self.task_list = QListWidget()
        self.task_list.setMaximumHeight(200)
        left_layout.addWidget(self.task_list)
        task_btn_layout = QHBoxLayout()
        select_btn = QPushButton("选中为当前任务")
        select_btn.setStyleSheet("background: #3498db; color: white;")
        select_btn.clicked.connect(self._select_task)
        task_btn_layout.addWidget(select_btn)
        complete_btn = QPushButton("完成任务")
        complete_btn.setStyleSheet("background: #27ae60; color: white;")
        complete_btn.clicked.connect(self._complete_task)
        task_btn_layout.addWidget(complete_btn)
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("background: #e74c3c; color: white;")
        delete_btn.clicked.connect(self._delete_task)
        task_btn_layout.addWidget(delete_btn)
        left_layout.addLayout(task_btn_layout)
        self.current_task_label = QLabel("当前任务: 无")
        self.current_task_label.setStyleSheet("font-size: 13px; color: #7f8c8d; padding: 6px; background: #f8f9fa; border-radius: 6px;")
        left_layout.addWidget(self.current_task_label)
        pomodoro_counter = QLabel("🍅 连续番茄计数")
        pomodoro_counter.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; margin-top: 10px;")
        left_layout.addWidget(pomodoro_counter)
        self.pomodoro_counter_label = QLabel("0 / 4")
        self.pomodoro_counter_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #e74c3c;")
        left_layout.addWidget(self.pomodoro_counter_label)
        left_layout.addStretch()
        left_panel.setMaximumWidth(320)
        left_panel.setMinimumWidth(260)
        main_layout.addWidget(left_panel)
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(16)
        center_layout.addStretch()
        self.progress_bar = CircularProgressBar()
        center_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.start_btn = QPushButton("▶ 开始专注")
        self.start_btn.setStyleSheet("background: #e74c3c; color: white; font-size: 16px; padding: 12px 36px;")
        self.start_btn.clicked.connect(self._toggle_timer)
        btn_layout.addWidget(self.start_btn)
        self.skip_btn = QPushButton("⏭ 跳过")
        self.skip_btn.setStyleSheet("background: #95a5a6; color: white;")
        self.skip_btn.clicked.connect(self._skip)
        self.skip_btn.setEnabled(False)
        btn_layout.addWidget(self.skip_btn)
        self.reset_btn = QPushButton("↺ 重置")
        self.reset_btn.setStyleSheet("background: #7f8c8d; color: white;")
        self.reset_btn.clicked.connect(self._reset)
        btn_layout.addWidget(self.reset_btn)
        center_layout.addLayout(btn_layout)
        center_layout.addStretch()
        main_layout.addWidget(center_panel, stretch=1)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        sound_label = QLabel("🎵 白噪音")
        sound_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        right_layout.addWidget(sound_label)
        self.sound_combo = QComboBox()
        for key, name in SOUND_TYPES.items():
            self.sound_combo.addItem(name, key)
        self.sound_combo.addItem("关闭", "off")
        self.sound_combo.currentIndexChanged.connect(self._on_sound_changed)
        right_layout.addWidget(self.sound_combo)
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("🔊"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_layout.addWidget(self.volume_slider)
        self.volume_label = QLabel("50%")
        self.volume_label.setMinimumWidth(35)
        volume_layout.addWidget(self.volume_label)
        right_layout.addLayout(volume_layout)
        right_layout.addStretch()
        right_btn_layout = QVBoxLayout()
        right_btn_layout.setSpacing(8)
        stats_btn = QPushButton("📊 统计面板")
        stats_btn.setStyleSheet("background: #9b59b6; color: white;")
        stats_btn.clicked.connect(self._show_statistics)
        right_btn_layout.addWidget(stats_btn)
        settings_btn = QPushButton("⚙ 设置")
        settings_btn.setStyleSheet("background: #34495e; color: white;")
        settings_btn.clicked.connect(self._show_settings)
        right_btn_layout.addWidget(settings_btn)
        right_layout.addLayout(right_btn_layout)
        right_panel.setMaximumWidth(200)
        right_panel.setMinimumWidth(160)
        main_layout.addWidget(right_panel)

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

    def _setup_tray(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(231, 76, 60))
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont("Arial", 18, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "🍅")
        painter.end()
        icon = QIcon(pixmap)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("番茄钟与专注助手")
        tray_menu = QMenu()
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def _update_display(self):
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        time_text = f"{mins:02d}:{secs:02d}"
        self.progress_bar.set_time_text(time_text)
        if self.total_seconds > 0:
            progress = 1.0 - (self.remaining_seconds / self.total_seconds)
        else:
            progress = 0.0
        self.progress_bar.set_progress(progress)
        state_texts = {
            self.STATE_IDLE: "准备就绪",
            self.STATE_WORK: f"专注中 · 任务 {self.pomodoro_count + 1}",
            self.STATE_BREAK: "短休息",
            self.STATE_LONG_BREAK: "长休息",
        }
        self.progress_bar.set_status_text(state_texts.get(self.state, ""))
        colors = {
            self.STATE_IDLE: QColor(231, 76, 60),
            self.STATE_WORK: QColor(231, 76, 60),
            self.STATE_BREAK: QColor(46, 204, 113),
            self.STATE_LONG_BREAK: QColor(52, 152, 219),
        }
        self.progress_bar.set_color(colors.get(self.state, QColor(231, 76, 60)))
        self.pomodoro_counter_label.setText(f"{self.pomodoro_count} / {self.long_break_interval}")
        if self.state == self.STATE_WORK:
            remaining_text = f"🍅 专注中 {time_text}"
            if self.show_overlay:
                self.overlay.set_remaining_text(remaining_text)
        elif self.state in (self.STATE_BREAK, self.STATE_LONG_BREAK):
            remaining_text = f"☕ 休息中 {time_text}"
            if self.show_overlay:
                self.overlay.set_remaining_text(remaining_text)

    def _toggle_timer(self):
        if self.state == self.STATE_IDLE:
            self._start_work()
        elif self.state in (self.STATE_WORK, self.STATE_BREAK, self.STATE_LONG_BREAK):
            self._pause()

    def _start_work(self):
        self.state = self.STATE_WORK
        self.work_duration = self.db.get_config("work_duration", 25)
        self.total_seconds = self.work_duration * 60
        self.remaining_seconds = self.total_seconds
        self.session_started_at = datetime.now().isoformat()
        self.start_btn.setText("⏸ 暂停")
        self.skip_btn.setEnabled(True)
        self.timer.start()
        if self.show_overlay:
            self.overlay.show_overlay()
        if self.block_sites:
            sites = self.db.get_blocked_sites()
            if sites:
                self.website_blocker.block_sites(sites)
        if self.audio_player.current_sound():
            self.audio_player.play(self.audio_player.current_sound())
        self._update_display()

    def _start_break(self):
        if self.pomodoro_count >= self.long_break_interval:
            self.state = self.STATE_LONG_BREAK
            self.long_break_duration = self.db.get_config("long_break_duration", 15)
            self.total_seconds = self.long_break_duration * 60
        else:
            self.state = self.STATE_BREAK
            self.break_duration = self.db.get_config("break_duration", 5)
            self.total_seconds = self.break_duration * 60
        self.remaining_seconds = self.total_seconds
        self.start_btn.setText("⏸ 暂停")
        self.timer.start()
        self.website_blocker.unblock_sites()
        if self.show_overlay:
            self.overlay.show_overlay()
        self._update_display()

    def _pause(self):
        self.timer.stop()
        self.start_btn.setText("▶ 继续")
        self.overlay.hide_overlay()

    def _resume(self):
        self.timer.start()
        self.start_btn.setText("⏸ 暂停")
        if self.show_overlay:
            self.overlay.show_overlay()

    def _reset(self):
        self.timer.stop()
        self.state = self.STATE_IDLE
        self.total_seconds = 0
        self.remaining_seconds = 0
        self.session_started_at = None
        self.start_btn.setText("▶ 开始专注")
        self.skip_btn.setEnabled(False)
        self.overlay.hide_overlay()
        self.website_blocker.unblock_sites()
        self.audio_player.stop()
        self.sound_combo.setCurrentIndex(self.sound_combo.count() - 1)
        self._update_display()

    def _skip(self):
        self._complete_session()

    def _tick(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_display()
        else:
            self._complete_session()

    def _complete_session(self):
        self.timer.stop()
        now = datetime.now().isoformat()
        if self.state == self.STATE_WORK:
            self.db.add_pomodoro_record(
                self.current_task_id,
                self.session_started_at or now,
                now,
                self.work_duration,
                "work",
            )
            self.pomodoro_count += 1
            if self.current_task_id:
                self.db.update_task_pomodoro(self.current_task_id)
                task = self._get_task_by_id(self.current_task_id)
                if task and task["pomodoros_completed"] >= task["pomodoros_target"]:
                    self.db.complete_task(self.current_task_id)
                    self.current_task_label.setText("当前任务: 无 (上一个任务已完成! ✅)")
                    self.current_task_id = None
                    self._refresh_tasks()
            self._refresh_tasks()
            if self.pomodoro_count >= self.long_break_interval:
                QMessageBox.information(
                    self,
                    "🍅 长休息提醒",
                    f"你已完成 {self.long_break_interval} 个番茄钟！\n请享受一个长休息吧！",
                )
                self.pomodoro_count = 0
                self._start_break()
            else:
                self.auto_start = self.db.get_config("auto_start", False)
                if self.auto_start:
                    self._start_break()
                else:
                    self.state = self.STATE_IDLE
                    self.start_btn.setText("☕ 开始休息")
                    self.start_btn.clicked.disconnect()
                    self.start_btn.clicked.connect(self._start_break_from_btn)
                    self.overlay.hide_overlay()
                    self.website_blocker.unblock_sites()
                    self._update_display()
        elif self.state in (self.STATE_BREAK, self.STATE_LONG_BREAK):
            self.db.add_pomodoro_record(
                None,
                self.session_started_at or now,
                now,
                self.total_seconds // 60,
                self.state,
            )
            self.overlay.hide_overlay()
            self.auto_start = self.db.get_config("auto_start", False)
            if self.auto_start:
                self._start_work()
            else:
                self.state = self.STATE_IDLE
                self.start_btn.setText("▶ 开始专注")
                self.start_btn.clicked.disconnect()
                self.start_btn.clicked.connect(self._toggle_timer)
                self._update_display()

    def _start_break_from_btn(self):
        self.start_btn.clicked.disconnect()
        self.start_btn.clicked.connect(self._toggle_timer)
        self._start_break()

    def _add_task(self):
        name = self.task_input.text().strip()
        if name:
            target = self.pomodoro_target_spin.value()
            self.db.add_task(name, target)
            self.task_input.clear()
            self._refresh_tasks()

    def _select_task(self):
        current = self.task_list.currentItem()
        if current:
            task_id = current.data(Qt.ItemDataRole.UserRole)
            task = self._get_task_by_id(task_id)
            if task:
                self.current_task_id = task_id
                self.current_task_label.setText(f"当前任务: {task['name']}")
                self.pomodoro_target_spin.setValue(task.get("pomodoros_target", 1))

    def _complete_task(self):
        current = self.task_list.currentItem()
        if current:
            task_id = current.data(Qt.ItemDataRole.UserRole)
            self.db.complete_task(task_id)
            if self.current_task_id == task_id:
                self.current_task_id = None
                self.current_task_label.setText("当前任务: 无")
            self._refresh_tasks()

    def _delete_task(self):
        current = self.task_list.currentItem()
        if current:
            task_id = current.data(Qt.ItemDataRole.UserRole)
            self.db.delete_task(task_id)
            if self.current_task_id == task_id:
                self.current_task_id = None
                self.current_task_label.setText("当前任务: 无")
            self._refresh_tasks()

    def _get_task_by_id(self, task_id):
        for t in self.db.get_tasks():
            if t["id"] == task_id:
                return t
        return None

    def _refresh_tasks(self):
        self.task_list.clear()
        for task in self.db.get_tasks():
            status = "✅" if task["completed"] else "⬜"
            item_text = f"{status} {task['name']} ({task['pomodoros_completed']}/{task['pomodoros_target']})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, task["id"])
            if task["completed"]:
                item.setForeground(QColor(149, 165, 166))
            self.task_list.addItem(item)
        if self.current_task_id:
            task = self._get_task_by_id(self.current_task_id)
            if task:
                if task["completed"]:
                    self.current_task_label.setText("当前任务: 无 (任务已完成)")
                    self.current_task_id = None
                else:
                    self.current_task_label.setText(f"当前任务: {task['name']}")

    def _on_sound_changed(self, index):
        data = self.sound_combo.currentData()
        if data == "off":
            self.audio_player.stop()
        else:
            self.audio_player.play(data)

    def _on_volume_changed(self, value):
        self.volume_label.setText(f"{value}%")
        self.audio_player.set_volume(value / 100.0)

    def _show_statistics(self):
        self.stats_window = QWidget()
        self.stats_window.setWindowTitle("📊 统计面板")
        self.stats_window.setMinimumSize(850, 550)
        layout = QVBoxLayout(self.stats_window)
        panel = StatisticsPanel(self.db)
        layout.addWidget(panel)
        panel.refresh()
        self.stats_window.show()

    def _show_settings(self):
        dialog = SettingsDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._init_configs()

    def _quit_app(self):
        self.overlay.hide_overlay()
        self.website_blocker.unblock_sites()
        self.audio_player.stop()
        self.db.close()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "番茄钟",
            "程序已最小化到系统托盘，双击图标可恢复",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def showEvent(self, event):
        super().showEvent(event)
        if not self.tray_icon.isVisible():
            self.tray_icon.show()
