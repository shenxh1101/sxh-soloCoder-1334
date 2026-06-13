import os
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont


HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
MARKER_START = "# POMODORO_FOCUS_BLOCK_START"
MARKER_END = "# POMODORO_FOCUS_BLOCK_END"


class ScreenOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._visible = False
        self._border_width = 18
        self._color = QColor(220, 50, 50, 60)
        self._label_text = ""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def show_overlay(self, remaining_text=""):
        self._visible = True
        self._label_text = remaining_text
        screen = self.screen()
        if screen:
            geo = screen.geometry()
            self.setGeometry(geo)
        self.show()
        self.update()

    def hide_overlay(self):
        self._visible = False
        self.hide()

    def set_remaining_text(self, text):
        self._label_text = text
        if self._visible:
            self.update()

    def paintEvent(self, event):
        if not self._visible:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        bw = self._border_width
        top_rect = QRect(0, 0, w, bw)
        bottom_rect = QRect(0, h - bw, w, bw)
        left_rect = QRect(0, bw, bw, h - 2 * bw)
        right_rect = QRect(w - bw, bw, bw, h - 2 * bw)
        painter.fillRect(top_rect, self._color)
        painter.fillRect(bottom_rect, self._color)
        painter.fillRect(left_rect, self._color)
        painter.fillRect(right_rect, self._color)
        inner_color = QColor(0, 0, 0, 20)
        inner_rect = QRect(bw, bw, w - 2 * bw, h - 2 * bw)
        painter.fillRect(inner_rect, inner_color)
        if self._label_text:
            painter.setPen(QPen(QColor(255, 255, 255, 180)))
            font = QFont("Microsoft YaHei", 14, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QRect(w - 280, 40, 260, 40), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._label_text)
        painter.end()


class WebsiteBlocker:
    def __init__(self):
        self._blocked = False
        self._sites = []

    def block_sites(self, sites):
        if not sites:
            return
        self._sites = list(sites)
        try:
            self._write_hosts(sites)
            self._blocked = True
        except PermissionError:
            self._blocked = False

    def unblock_sites(self):
        if not self._blocked:
            return
        try:
            self._remove_hosts_entries()
        except PermissionError:
            pass
        self._blocked = False

    def _read_hosts(self):
        try:
            with open(HOSTS_PATH, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def _write_hosts(self, sites):
        content = self._read_hosts()
        self._remove_hosts_entries_from_content(content)
        content = self._read_hosts()
        lines = [MARKER_START]
        for site in sites:
            lines.append(f"127.0.0.1 {site}")
            lines.append(f"127.0.0.1 www.{site}")
        lines.append(MARKER_END)
        with open(HOSTS_PATH, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(lines) + "\n")

    def _remove_hosts_entries(self):
        content = self._read_hosts()
        new_content = self._remove_hosts_entries_from_content(content)
        if new_content != content:
            with open(HOSTS_PATH, "w", encoding="utf-8") as f:
                f.write(new_content)

    def _remove_hosts_entries_from_content(self, content):
        lines = content.split("\n")
        new_lines = []
        skip = False
        for line in lines:
            if line.strip() == MARKER_START:
                skip = True
                continue
            if line.strip() == MARKER_END:
                skip = False
                continue
            if not skip:
                new_lines.append(line)
        return "\n".join(new_lines)

    def is_blocked(self):
        return self._blocked
