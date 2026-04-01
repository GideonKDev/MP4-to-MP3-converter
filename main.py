"""
MP4 to MP3 Converter Pro — Redesigned UI
Industrial-dark aesthetic with proper SVG icons, refined typography, polished UX
"""

import sys
import os
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QProgressBar,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QFileDialog, QMessageBox, QSplitter, QTextEdit, QTabWidget,
    QHeaderView, QStyleFactory, QMenu, QMenuBar, QStatusBar,
    QToolBar, QFrame, QSizePolicy, QDialog, QLineEdit,
    QFormLayout, QDialogButtonBox, QScrollArea, QStackedWidget,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation,
    QEasingCurve, QRect, QPoint, QPointF
)
from PyQt6.QtGui import (
    QFont, QIcon, QPixmap, QColor, QPalette, QAction,
    QDragEnterEvent, QDropEvent, QPainter, QBrush, QLinearGradient,
    QPen, QFontDatabase, QRadialGradient, QPainterPath, QPolygonF,
    QConicalGradient
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtSvgWidgets import QSvgWidget

# ─────────────────────────────────────────────
#  Optional dependencies
# ─────────────────────────────────────────────
try:
    from moviepy.editor import VideoFileClip
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

try:
    import mutagen
    from mutagen.mp4 import MP4
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TYER, TCON, TRCK, APIC
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False


# ─────────────────────────────────────────────
#  Palette & Fonts
# ─────────────────────────────────────────────
PALETTE = {
    "bg_deep":     "#0D0F12",
    "bg_panel":    "#141720",
    "bg_card":     "#1C2030",
    "bg_hover":    "#242840",
    "border":      "#2A2E45",
    "border_lit":  "#3A4060",
    "accent":      "#4F8EF7",
    "accent_dim":  "#2A4880",
    "accent_glow": "#6AAEFF",
    "success":     "#3DD68C",
    "warning":     "#F5A623",
    "error":       "#F75A5A",
    "text_prim":   "#E8EAF2",
    "text_sec":    "#7B82A0",
    "text_dim":    "#454C6A",
    "waveform":    "#1E2540",
}


# ─────────────────────────────────────────────
#  SVG Icon Library  (inline SVGs → QIcon)
# ─────────────────────────────────────────────
class Icons:
    """All UI icons as inline SVG strings rendered to QIcon."""

    _cache: dict = {}

    # Raw SVG templates – all use currentColor via fill attr
    _SVG = {
        "add_file": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <polyline points="14 2 14 8 20 8" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="12" y1="18" x2="12" y2="12" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="9" y1="15" x2="15" y2="15" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        </svg>""",

        "add_folder": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="12" y1="11" x2="12" y2="17" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="9" y1="14" x2="15" y2="14" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        </svg>""",

        "clear": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <polyline points="3 6 5 6 21 6" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M10 11v6M14 11v6" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",

        "play": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="1.8"/>
          <polygon points="10,8 17,12 10,16" fill="{color}"/>
        </svg>""",

        "pause": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="1.8"/>
          <line x1="10" y1="8" x2="10" y2="16" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
          <line x1="14" y1="8" x2="14" y2="16" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        </svg>""",

        "stop": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="1.8"/>
          <rect x="9" y="9" width="6" height="6" rx="1" fill="{color}"/>
        </svg>""",

        "settings": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="3" stroke="{color}" stroke-width="1.8"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",

        "music": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M9 18V5l12-2v13" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="6" cy="18" r="3" stroke="{color}" stroke-width="1.8"/>
          <circle cx="18" cy="16" r="3" stroke="{color}" stroke-width="1.8"/>
        </svg>""",

        "video": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="2" y="5" width="15" height="14" rx="2" stroke="{color}" stroke-width="1.8"/>
          <path d="M17 9l5-3v12l-5-3V9z" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>
        </svg>""",

        "check": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="1.8"/>
          <polyline points="8,12 11,15 16,9" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",

        "error_icon": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="1.8"/>
          <line x1="15" y1="9" x2="9" y2="15" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
          <line x1="9" y1="9" x2="15" y2="15" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        </svg>""",

        "remove": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <line x1="18" y1="6" x2="6" y2="18" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
          <line x1="6" y1="6" x2="18" y2="18" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        </svg>""",

        "info": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="1.8"/>
          <line x1="12" y1="8" x2="12" y2="8" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="12" y1="12" x2="12" y2="16" stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        </svg>""",

        "waveform": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <line x1="2" y1="12" x2="4" y2="12" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="5" y1="9" x2="5" y2="15" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="7.5" y1="6" x2="7.5" y2="18" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="10" y1="4" x2="10" y2="20" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="12.5" y1="7" x2="12.5" y2="17" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="15" y1="9" x2="15" y2="15" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="17.5" y1="11" x2="17.5" y2="13" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="20" y1="12" x2="22" y2="12" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
        </svg>""",

        "log": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="8" y1="13" x2="16" y2="13" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="8" y1="17" x2="13" y2="17" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>
        </svg>""",

        "about": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" stroke="{color}" stroke-width="1.8"/>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="12" y1="17" x2="12.01" y2="17" stroke="{color}" stroke-width="2.5" stroke-linecap="round"/>
        </svg>""",

        "check_deps": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <polyline points="9,12 11,14 15,10" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",
    }

    @classmethod
    def get(cls, name: str, color: str = PALETTE["text_prim"], size: int = 20) -> QIcon:
        key = f"{name}_{color}_{size}"
        if key in cls._cache:
            return cls._cache[key]

        svg_str = cls._SVG.get(name, cls._SVG["info"])
        svg_colored = svg_str.replace("{color}", color)
        svg_bytes = svg_str.encode()

        renderer = QSvgRenderer(svg_colored.encode())
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        icon = QIcon(pixmap)
        cls._cache[key] = icon
        return icon

    @classmethod
    def pixmap(cls, name: str, color: str = PALETTE["text_prim"], size: int = 20) -> QPixmap:
        svg_str = cls._SVG.get(name, cls._SVG["info"])
        svg_colored = svg_str.replace("{color}", color)
        renderer = QSvgRenderer(svg_colored.encode())
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        renderer.render(p)
        p.end()
        return px


# ─────────────────────────────────────────────
#  Data
# ─────────────────────────────────────────────
@dataclass
class AppConfig:
    default_bitrate: str = "192k"
    default_format: str = "mp3"
    output_directory: str = os.path.expanduser("~/ConvertedAudio")
    preserve_metadata: bool = True
    extract_cover: bool = True
    theme: str = "dark"
    max_concurrent: int = 2
    auto_clear_list: bool = False
    notification_sound: bool = True


class ConversionTask:
    def __init__(self, input_path: str, output_path: str = None):
        self.input_path = input_path
        self.output_path = output_path
        self.status = "pending"
        self.progress = 0
        self.error_message = ""
        self.start_time = None
        self.end_time = None
        self.file_size = os.path.getsize(input_path) if os.path.exists(input_path) else 0
        if output_path is None:
            self.output_path = str(Path(input_path).with_suffix(".mp3"))


# ─────────────────────────────────────────────
#  Worker Thread
# ─────────────────────────────────────────────
class ConversionWorker(QThread):
    progress_updated = pyqtSignal(int, int, int)
    task_completed  = pyqtSignal(int, bool, str)
    conversion_started = pyqtSignal(int)
    log_message     = pyqtSignal(str, str)

    def __init__(self, tasks: List[ConversionTask], config: dict):
        super().__init__()
        self.tasks = tasks
        self.config = config
        self.is_running = True

    def run(self):
        for i, task in enumerate(self.tasks):
            if not self.is_running:
                break
            self.conversion_started.emit(i)
            task.status = "converting"
            task.start_time = time.time()
            try:
                success, message = self._convert_single(task, i)
                task.status = "completed" if success else "failed"
                task.error_message = "" if success else message
                task.end_time = time.time()
                self.task_completed.emit(i, success, message)
            except Exception as e:
                task.status = "failed"
                task.error_message = str(e)
                self.task_completed.emit(i, False, str(e))

    def stop(self):
        self.is_running = False

    def _convert_single(self, task: ConversionTask, idx: int):
        try:
            os.makedirs(os.path.dirname(task.output_path), exist_ok=True)
            cmd = [
                "ffmpeg", "-i", task.input_path,
                "-codec:a", "libmp3lame",
                "-b:a", self.config.get("bitrate", "192k"),
                "-q:a", "2", "-y", task.output_path,
            ]
            if self.config.get("preserve_metadata", True):
                cmd[-2:-2] = ["-map_metadata", "0", "-id3v2_version", "3"]
            if self.config.get("normalize", False):
                cmd[-2:-2] = ["-af", f'volume={self.config.get("target_db", -1.0)}dB']

            self.log_message.emit(f"Converting: {os.path.basename(task.input_path)}", "info")
            for p in range(0, 101, 5):
                if not self.is_running:
                    return False, "Cancelled"
                self.progress_updated.emit(idx, p, 0)
                time.sleep(0.12)

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                if self.config.get("extract_cover") and HAS_MUTAGEN:
                    self._extract_cover_art(task.input_path, task.output_path)
                if self.config.get("preserve_metadata") and HAS_MUTAGEN:
                    self._preserve_metadata(task.input_path, task.output_path)
                return True, "Conversion successful"
            else:
                return False, f"FFmpeg error: {result.stderr[:200]}"
        except Exception as e:
            return False, f"Error: {e}"

    def _extract_cover_art(self, video_path, audio_path):
        try:
            cover = audio_path.replace(".mp3", "_cover.jpg")
            subprocess.run(["ffmpeg", "-i", video_path, "-an", "-vcodec", "png", "-vframes", "1", "-y", cover],
                           capture_output=True, check=True)
            if os.path.exists(cover) and audio_path.lower().endswith(".mp3"):
                audio = mutagen.File(audio_path, easy=True)
                if audio:
                    with open(cover, "rb") as f:
                        audio["APIC"] = APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=f.read())
                    audio.save()
                    os.remove(cover)
        except Exception as e:
            self.log_message.emit(f"Cover art: {e}", "warning")

    def _preserve_metadata(self, video_path, audio_path):
        try:
            if video_path.lower().endswith(".mp4"):
                video = MP4(video_path)
                audio = ID3(audio_path)
                m = {"©nam": TIT2, "©ART": TPE1, "©alb": TALB, "©day": TYER, "©gen": TCON, "trkn": TRCK}
                for k, cls_ in m.items():
                    if k in video:
                        audio.add(cls_(encoding=3, text=str(video[k][0])))
                audio.save()
        except Exception as e:
            self.log_message.emit(f"Metadata: {e}", "warning")


# ─────────────────────────────────────────────
#  Custom Widgets
# ─────────────────────────────────────────────
class IconButton(QPushButton):
    """Sleek icon+text button with hover glow."""

    def __init__(self, icon_name: str, label: str = "", color: str = PALETTE["text_prim"],
                 accent: bool = False, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._label = label
        self._color = color
        self._accent = accent
        self._hovered = False

        if label:
            self.setText(f"  {label}")
        self.setIcon(Icons.get(icon_name, color, 18))
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self._apply_style(False)

    def _apply_style(self, hovered: bool):
        if self._accent:
            bg   = PALETTE["accent"] if not hovered else PALETTE["accent_glow"]
            text = "#FFFFFF"
            border = PALETTE["accent"]
        else:
            bg   = PALETTE["bg_card"] if not hovered else PALETTE["bg_hover"]
            text = PALETTE["text_prim"]
            border = PALETTE["border_lit"] if hovered else PALETTE["border"]

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 0 14px;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                font-size: 12px;
                font-weight: 500;
                letter-spacing: 0.4px;
            }}
            QPushButton:disabled {{
                background-color: {PALETTE['bg_panel']};
                color: {PALETTE['text_dim']};
                border-color: {PALETTE['border']};
            }}
        """)

    def enterEvent(self, e):
        self._hovered = True
        self._apply_style(True)
        self.setIcon(Icons.get(self._icon_name,
                               PALETTE["accent_glow"] if not self._accent else "#FFFFFF", 18))
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._apply_style(False)
        self.setIcon(Icons.get(self._icon_name, self._color, 18))
        super().leaveEvent(e)


class WaveformWidget(QWidget):
    """Animated waveform bar decoration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._bars = [0.3, 0.7, 1.0, 0.6, 0.9, 0.4, 0.8, 0.5, 0.7, 0.3, 0.6, 0.9, 0.4]
        self._phase = 0.0
        self._active = False
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

    def set_active(self, v: bool):
        self._active = v
        if v:
            self._timer.start(80)
        else:
            self._timer.stop()
            self.update()

    def _tick(self):
        import math
        self._phase += 0.25
        self._bars = [abs(math.sin(self._phase + i * 0.6)) * 0.85 + 0.15
                      for i in range(len(self._bars))]
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self._bars)
        bar_w = max(2, (w - n * 2) // n)
        total = n * (bar_w + 2)
        x = (w - total) // 2

        for i, val in enumerate(self._bars):
            bar_h = int(val * (h - 4)) + 4
            y = (h - bar_h) // 2
            color = QColor(PALETTE["accent"] if self._active else PALETTE["text_dim"])
            color.setAlphaF(0.6 + val * 0.4)
            p.setBrush(QBrush(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x + i * (bar_w + 2), y, bar_w, bar_h, 1, 1)
        p.end()


class DropZone(QListWidget):
    """File list with styled drop zone."""

    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setSpacing(2)
        self._normal_style()

    def _normal_style(self):
        self.setStyleSheet(f"""
            QListWidget {{
                border: 2px dashed {PALETTE['border_lit']};
                border-radius: 10px;
                background-color: {PALETTE['bg_card']};
                padding: 8px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                margin: 1px 0;
                background-color: {PALETTE['bg_panel']};
                border: 1px solid {PALETTE['border']};
                border-radius: 6px;
                color: {PALETTE['text_prim']};
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
            }}
            QListWidget::item:selected {{
                background-color: {PALETTE['accent_dim']};
                border-color: {PALETTE['accent']};
            }}
            QListWidget::item:hover {{
                background-color: {PALETTE['bg_hover']};
                border-color: {PALETTE['border_lit']};
            }}
            QScrollBar:vertical {{
                background: {PALETTE['bg_panel']};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {PALETTE['border_lit']};
                border-radius: 3px;
            }}
        """)

    def _active_style(self):
        self.setStyleSheet(f"""
            QListWidget {{
                border: 2px dashed {PALETTE['accent']};
                border-radius: 10px;
                background-color: {PALETTE['bg_hover']};
                padding: 8px;
            }}
            QListWidget::item {{
                padding: 10px 12px; margin: 1px 0;
                background-color: {PALETTE['bg_panel']};
                border: 1px solid {PALETTE['border']};
                border-radius: 6px;
                color: {PALETTE['text_prim']};
                font-size: 12px;
            }}
        """)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._active_style()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._normal_style()
        super().dragLeaveEvent(e)

    def dropEvent(self, e: QDropEvent):
        self._normal_style()
        if e.mimeData().hasUrls():
            EXTS = {".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"}
            files = []
            for url in e.mimeData().urls():
                fp = url.toLocalFile()
                if os.path.exists(fp) and Path(fp).suffix.lower() in EXTS:
                    files.append(fp)
                    item = QListWidgetItem(Icons.get("video", PALETTE["accent"], 16),
                                          f"  {os.path.basename(fp)}")
                    item.setData(Qt.ItemDataRole.UserRole, fp)
                    item.setToolTip(fp)
                    self.addItem(item)
            if files:
                self.files_dropped.emit(files)
        e.acceptProposedAction()


class SlimProgressBar(QProgressBar):
    """Thin, accent-colored progress bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self.setTextVisible(False)
        self.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background-color: {PALETTE['bg_panel']};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PALETTE['accent_dim']}, stop:1 {PALETTE['accent_glow']});
                border-radius: 3px;
            }}
        """)


class TaskRow(QWidget):
    """Single file conversion task row."""

    def __init__(self, task: ConversionTask, parent=None):
        super().__init__(parent)
        self.task = task
        self.setFixedHeight(72)
        self.setObjectName("TaskRow")
        self.setStyleSheet(f"""
            #TaskRow {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 8px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(5)

        top = QHBoxLayout()
        top.setSpacing(8)

        self._icon = QLabel()
        self._icon.setPixmap(Icons.pixmap("video", PALETTE["text_sec"], 16))
        top.addWidget(self._icon)

        self._name = QLabel(os.path.basename(task.input_path))
        self._name.setStyleSheet(f"color:{PALETTE['text_prim']}; font-size:12px; font-weight:500;")
        top.addWidget(self._name, 1)

        size_mb = task.file_size / (1024 * 1024)
        self._size = QLabel(f"{size_mb:.1f} MB")
        self._size.setStyleSheet(f"color:{PALETTE['text_dim']}; font-size:11px;")
        top.addWidget(self._size)

        self._badge = QLabel("PENDING")
        self._badge.setFixedWidth(72)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_badge("pending")
        top.addWidget(self._badge)

        root.addLayout(top)

        bot = QHBoxLayout()
        self._bar = SlimProgressBar()
        self._bar.setValue(0)
        bot.addWidget(self._bar, 1)

        self._pct = QLabel("0%")
        self._pct.setFixedWidth(34)
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._pct.setStyleSheet(f"color:{PALETTE['text_sec']}; font-size:11px;")
        bot.addWidget(self._pct)

        root.addLayout(bot)

    def _set_badge(self, status: str):
        colors = {
            "pending":    (PALETTE["text_dim"],    PALETTE["bg_panel"],  PALETTE["border"]),
            "converting": (PALETTE["accent"],       PALETTE["accent_dim"], PALETTE["accent"]),
            "completed":  (PALETTE["success"],      "#1A3328",             PALETTE["success"]),
            "failed":     (PALETTE["error"],        "#33141A",             PALETTE["error"]),
        }
        fg, bg, border = colors.get(status, colors["pending"])
        label = status.upper()
        self._badge.setText(label)
        self._badge.setStyleSheet(f"""
            QLabel {{
                color: {fg};
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
                font-family: monospace;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 2px 4px;
            }}
        """)

    def update_progress(self, val: int):
        self._bar.setValue(val)
        self._pct.setText(f"{val}%")
        self.task.progress = val

    def update_status(self, status: str):
        self._set_badge(status)
        ico = {
            "converting": ("video", PALETTE["accent"]),
            "completed":  ("check", PALETTE["success"]),
            "failed":     ("error_icon", PALETTE["error"]),
        }.get(status, ("video", PALETTE["text_sec"]))
        self._icon.setPixmap(Icons.pixmap(ico[0], ico[1], 16))


class SectionHeader(QWidget):
    """Labelled section header with icon."""

    def __init__(self, icon_name: str, title: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        ico = QLabel()
        ico.setPixmap(Icons.pixmap(icon_name, PALETTE["accent"], 16))
        lay.addWidget(ico)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"""
            color: {PALETTE['text_prim']};
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.5px;
        """)
        lay.addWidget(lbl)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {PALETTE['border']}; border: none; height: 1px;")
        lay.addWidget(line, 1)


class Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {PALETTE['border']}; border: none;")


# ─────────────────────────────────────────────
#  Settings Dialog
# ─────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setFixedSize(480, 520)
        self.setStyleSheet(f"""
            QDialog {{ background: {PALETTE['bg_deep']}; color: {PALETTE['text_prim']}; }}
            QTabWidget::pane {{ border: 1px solid {PALETTE['border']}; border-radius: 6px;
                                background: {PALETTE['bg_panel']}; }}
            QTabBar::tab {{ background: {PALETTE['bg_card']}; color: {PALETTE['text_sec']};
                            padding: 8px 18px; border: 1px solid {PALETTE['border']};
                            border-radius: 4px; margin-right: 2px; font-size: 12px; }}
            QTabBar::tab:selected {{ background: {PALETTE['bg_hover']};
                                     color: {PALETTE['accent']}; border-color: {PALETTE['accent']}; }}
            QLabel {{ color: {PALETTE['text_prim']}; font-size: 12px; }}
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
                background: {PALETTE['bg_card']}; color: {PALETTE['text_prim']};
                border: 1px solid {PALETTE['border']}; border-radius: 5px;
                padding: 6px 10px; font-size: 12px;
            }}
            QCheckBox {{ color: {PALETTE['text_prim']}; font-size: 12px; spacing: 8px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px;
                                    border: 1px solid {PALETTE['border_lit']}; border-radius: 3px;
                                    background: {PALETTE['bg_card']}; }}
            QCheckBox::indicator:checked {{ background: {PALETTE['accent']};
                                            border-color: {PALETTE['accent']}; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        tabs = QTabWidget()

        # General
        gen = QWidget()
        gl = QFormLayout(gen)
        gl.setSpacing(12)
        self.out_dir = QLineEdit(config.output_directory)
        self.out_dir.setReadOnly(True)
        browse = QPushButton("Browse…")
        browse.setStyleSheet(f"background:{PALETTE['bg_hover']}; color:{PALETTE['text_prim']}; border:1px solid {PALETTE['border']}; border-radius:5px; padding:6px 12px;")
        browse.clicked.connect(lambda: self._browse())
        row = QHBoxLayout()
        row.addWidget(self.out_dir)
        row.addWidget(browse)
        gl.addRow("Output Dir:", row)
        self.fmt = QComboBox()
        self.fmt.addItems(["MP3", "WAV", "FLAC", "AAC", "OGG"])
        self.fmt.setCurrentText(config.default_format.upper())
        gl.addRow("Format:", self.fmt)
        self.br = QComboBox()
        self.br.addItems(["64k", "128k", "192k", "256k", "320k"])
        self.br.setCurrentText(config.default_bitrate)
        gl.addRow("Bitrate:", self.br)
        self.conc = QSpinBox()
        self.conc.setRange(1, 8)
        self.conc.setValue(config.max_concurrent)
        gl.addRow("Max Concurrent:", self.conc)
        tabs.addTab(gen, Icons.get("settings", PALETTE["text_sec"], 16), "General")

        # Audio
        aud = QWidget()
        al = QFormLayout(aud)
        al.setSpacing(12)
        self.meta_cb = QCheckBox()
        self.meta_cb.setChecked(config.preserve_metadata)
        al.addRow("Preserve Metadata:", self.meta_cb)
        self.cover_cb = QCheckBox()
        self.cover_cb.setChecked(config.extract_cover)
        al.addRow("Extract Cover Art:", self.cover_cb)
        self.norm_cb = QCheckBox()
        al.addRow("Normalize Audio:", self.norm_cb)
        self.db_spin = QDoubleSpinBox()
        self.db_spin.setRange(-30, 0)
        self.db_spin.setValue(-1.0)
        self.db_spin.setSingleStep(0.5)
        al.addRow("Target Level (dB):", self.db_spin)
        tabs.addTab(aud, Icons.get("waveform", PALETTE["text_sec"], 16), "Audio")

        # Interface
        iface = QWidget()
        il = QFormLayout(iface)
        il.setSpacing(12)
        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Light", "System"])
        self.theme.setCurrentText(config.theme.title())
        il.addRow("Theme:", self.theme)
        self.clear_cb = QCheckBox()
        self.clear_cb.setChecked(config.auto_clear_list)
        il.addRow("Auto-clear List:", self.clear_cb)
        self.notif_cb = QCheckBox()
        self.notif_cb.setChecked(config.notification_sound)
        il.addRow("Notification Sound:", self.notif_cb)
        tabs.addTab(iface, Icons.get("info", PALETTE["text_sec"], 16), "Interface")

        lay.addWidget(tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.setStyleSheet(f"""
            QPushButton {{ background:{PALETTE['bg_card']}; color:{PALETTE['text_prim']};
                           border:1px solid {PALETTE['border']}; border-radius:5px;
                           padding:8px 20px; font-size:12px; }}
            QPushButton:default {{ background:{PALETTE['accent']}; border-color:{PALETTE['accent']}; color:#fff; }}
        """)
        btns.accepted.connect(self._ok)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Output Directory", self.out_dir.text())
        if d:
            self.out_dir.setText(d)

    def _ok(self):
        self.config.output_directory = self.out_dir.text()
        self.config.default_format   = self.fmt.currentText().lower()
        self.config.default_bitrate  = self.br.currentText()
        self.config.max_concurrent   = self.conc.value()
        self.config.preserve_metadata = self.meta_cb.isChecked()
        self.config.extract_cover    = self.cover_cb.isChecked()
        self.config.theme            = self.theme.currentText().lower()
        self.config.auto_clear_list  = self.clear_cb.isChecked()
        self.config.notification_sound = self.notif_cb.isChecked()
        self.accept()


# ─────────────────────────────────────────────
#  Main Window
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.tasks: List[ConversionTask] = []
        self.task_rows: List[TaskRow] = []
        self.current_worker: Optional[ConversionWorker] = None
        self._load_settings()
        self._build_ui()
        self._build_menus()
        self._build_toolbar()

    # ── Build UI ────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("MP4 → MP3  ·  Converter Pro")
        self.setWindowIcon(Icons.get("music", PALETTE["accent"], 32))
        self.setGeometry(80, 80, 1100, 760)
        self.setMinimumSize(860, 600)

        # Global stylesheet
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {PALETTE['bg_deep']};
                color: {PALETTE['text_prim']};
                font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
            }}
            QGroupBox {{
                border: 1px solid {PALETTE['border']};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                color: {PALETTE['text_sec']};
            }}
            QComboBox, QSpinBox, QDoubleSpinBox {{
                background: {PALETTE['bg_card']};
                color: {PALETTE['text_prim']};
                border: 1px solid {PALETTE['border']};
                border-radius: 5px;
                padding: 6px 10px;
                font-size: 12px;
                min-height: 28px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QCheckBox {{ spacing: 8px; font-size: 12px; color: {PALETTE['text_prim']}; }}
            QCheckBox::indicator {{ width:16px; height:16px;
                                    border:1px solid {PALETTE['border_lit']}; border-radius:3px;
                                    background:{PALETTE['bg_card']}; }}
            QCheckBox::indicator:checked {{ background:{PALETTE['accent']};
                                            border-color:{PALETTE['accent']}; }}
            QScrollArea {{ border: none; }}
            QScrollBar:vertical {{ background:{PALETTE['bg_panel']}; width:6px; border-radius:3px; }}
            QScrollBar::handle:vertical {{ background:{PALETTE['border_lit']}; border-radius:3px; min-height:30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QStatusBar {{ background:{PALETTE['bg_panel']}; color:{PALETTE['text_sec']};
                           border-top:1px solid {PALETTE['border']}; font-size:11px; }}
            QToolBar {{ background:{PALETTE['bg_panel']}; border-bottom:1px solid {PALETTE['border']};
                        spacing:4px; padding:4px 8px; }}
            QMenuBar {{ background:{PALETTE['bg_panel']}; color:{PALETTE['text_prim']}; font-size:12px; }}
            QMenuBar::item:selected {{ background:{PALETTE['bg_hover']}; }}
            QMenu {{ background:{PALETTE['bg_card']}; color:{PALETTE['text_prim']};
                     border:1px solid {PALETTE['border']}; font-size:12px; }}
            QMenu::item:selected {{ background:{PALETTE['accent_dim']}; }}
            QMenu::separator {{ background:{PALETTE['border']}; height:1px; margin:3px 0; }}
        """)

        # ── Central layout
        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Left sidebar ────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet(f"background:{PALETTE['bg_panel']}; border-right:1px solid {PALETTE['border']};")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(16, 20, 16, 16)
        sb_lay.setSpacing(16)

        # Logo
        logo_row = QHBoxLayout()
        logo_ico = QLabel()
        logo_ico.setPixmap(Icons.pixmap("music", PALETTE["accent"], 28))
        logo_row.addWidget(logo_ico)
        logo_txt = QLabel("Converter Pro")
        logo_txt.setStyleSheet(f"""
            color: {PALETTE['text_prim']};
            font-size: 17px;
            font-weight: 700;
            letter-spacing: -0.5px;
        """)
        logo_row.addWidget(logo_txt)
        logo_row.addStretch()
        sb_lay.addLayout(logo_row)

        sb_lay.addWidget(Divider())

        # Waveform animation
        self._wave = WaveformWidget()
        sb_lay.addWidget(self._wave)

        sb_lay.addWidget(Divider())

        # Settings group
        sb_lay.addWidget(SectionHeader("settings", "Output Settings"))

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        lbl_style = f"color:{PALETTE['text_sec']}; font-size:11px;"

        fmt_lbl = QLabel("Format")
        fmt_lbl.setStyleSheet(lbl_style)
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["MP3", "WAV", "FLAC", "AAC", "OGG"])
        self.fmt_combo.setCurrentText(self.config.default_format.upper())
        form.addRow(fmt_lbl, self.fmt_combo)

        br_lbl = QLabel("Bitrate")
        br_lbl.setStyleSheet(lbl_style)
        self.br_combo = QComboBox()
        self.br_combo.addItems(["64k", "128k", "192k", "256k", "320k"])
        self.br_combo.setCurrentText(self.config.default_bitrate)
        form.addRow(br_lbl, self.br_combo)

        sb_lay.addLayout(form)

        meta_row = QHBoxLayout()
        meta_lbl = QLabel("Metadata")
        meta_lbl.setStyleSheet(lbl_style)
        self.meta_cb = QCheckBox()
        self.meta_cb.setChecked(self.config.preserve_metadata)
        meta_row.addWidget(meta_lbl)
        meta_row.addStretch()
        meta_row.addWidget(self.meta_cb)
        sb_lay.addLayout(meta_row)

        cover_row = QHBoxLayout()
        cover_lbl = QLabel("Cover Art")
        cover_lbl.setStyleSheet(lbl_style)
        self.cover_cb = QCheckBox()
        self.cover_cb.setChecked(self.config.extract_cover)
        cover_row.addWidget(cover_lbl)
        cover_row.addStretch()
        cover_row.addWidget(self.cover_cb)
        sb_lay.addLayout(cover_row)

        sb_lay.addStretch()
        sb_lay.addWidget(Divider())

        # Stats footer
        self._stats = QLabel("No files loaded")
        self._stats.setStyleSheet(f"color:{PALETTE['text_dim']}; font-size:11px;")
        self._stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb_lay.addWidget(self._stats)

        main.addWidget(sidebar)

        # ── Right content area ───────────────────
        content = QWidget()
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(20, 20, 20, 16)
        c_lay.setSpacing(16)

        # Top row: file controls
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self._btn_add   = IconButton("add_file",   "Add Files",  PALETTE["text_prim"])
        self._btn_folder= IconButton("add_folder", "Add Folder", PALETTE["text_prim"])
        self._btn_clear = IconButton("clear",      "Clear",      PALETTE["error"])
        ctrl_row.addWidget(self._btn_add)
        ctrl_row.addWidget(self._btn_folder)
        ctrl_row.addWidget(self._btn_clear)
        ctrl_row.addStretch()

        self._btn_start = IconButton("play",  "Convert", PALETTE["text_prim"], accent=True)
        self._btn_pause = IconButton("pause", "Pause",   PALETTE["text_prim"])
        self._btn_stop  = IconButton("stop",  "Stop",    PALETTE["error"])
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)

        ctrl_row.addWidget(self._btn_start)
        ctrl_row.addWidget(self._btn_pause)
        ctrl_row.addWidget(self._btn_stop)

        self._btn_add.clicked.connect(self._add_files)
        self._btn_folder.clicked.connect(self._add_folder)
        self._btn_clear.clicked.connect(self._clear_list)
        self._btn_start.clicked.connect(self._start_conversion)
        self._btn_pause.clicked.connect(self._pause_conversion)
        self._btn_stop.clicked.connect(self._stop_conversion)

        c_lay.addLayout(ctrl_row)

        # Splitter: file list | progress
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{ background: {PALETTE['border']}; border-radius: 2px; }}
        """)

        # File drop zone
        file_card = QWidget()
        file_card.setStyleSheet(f"background:{PALETTE['bg_panel']}; border-radius:10px;")
        fc_lay = QVBoxLayout(file_card)
        fc_lay.setContentsMargins(12, 12, 12, 12)
        fc_lay.setSpacing(8)
        fc_lay.addWidget(SectionHeader("video", "Files to Convert"))

        self._drop = DropZone()
        self._drop.files_dropped.connect(self._on_dropped)

        # Empty-state placeholder
        self._empty = QLabel("Drop video files here  ·  or use Add Files above")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet(f"""
            color: {PALETTE['text_dim']};
            font-size: 13px;
            padding: 40px;
            border: 2px dashed {PALETTE['border']};
            border-radius: 10px;
        """)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._empty)   # 0
        self._stack.addWidget(self._drop)    # 1
        fc_lay.addWidget(self._stack, 1)

        splitter.addWidget(file_card)

        # Progress area
        prog_card = QWidget()
        prog_card.setStyleSheet(f"background:{PALETTE['bg_panel']}; border-radius:10px;")
        pc_lay = QVBoxLayout(prog_card)
        pc_lay.setContentsMargins(12, 12, 12, 12)
        pc_lay.setSpacing(10)
        pc_lay.addWidget(SectionHeader("waveform", "Conversion Progress"))

        # Overall bar
        ov_row = QHBoxLayout()
        ov_lbl = QLabel("Overall")
        ov_lbl.setStyleSheet(f"color:{PALETTE['text_sec']}; font-size:11px;")
        ov_row.addWidget(ov_lbl)
        self._ov_bar = QProgressBar()
        self._ov_bar.setFixedHeight(8)
        self._ov_bar.setTextVisible(False)
        self._ov_bar.setStyleSheet(f"""
            QProgressBar {{ border:none; border-radius:4px; background:{PALETTE['bg_panel']}; }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {PALETTE['accent_dim']}, stop:1 {PALETTE['accent_glow']});
                border-radius:4px;
            }}
        """)
        ov_row.addWidget(self._ov_bar, 1)
        self._ov_pct = QLabel("0%")
        self._ov_pct.setFixedWidth(36)
        self._ov_pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._ov_pct.setStyleSheet(f"color:{PALETTE['text_sec']}; font-size:11px;")
        ov_row.addWidget(self._ov_pct)
        pc_lay.addLayout(ov_row)

        # Task scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background:transparent; border:none;")
        self._task_container = QWidget()
        self._task_container.setStyleSheet("background:transparent;")
        self._tasks_lay = QVBoxLayout(self._task_container)
        self._tasks_lay.setContentsMargins(0, 0, 0, 0)
        self._tasks_lay.setSpacing(6)
        self._tasks_lay.addStretch()
        scroll.setWidget(self._task_container)
        pc_lay.addWidget(scroll, 1)

        splitter.addWidget(prog_card)
        splitter.setSizes([340, 280])
        c_lay.addWidget(splitter, 1)

        # Log panel
        log_card = QWidget()
        log_card.setStyleSheet(f"background:{PALETTE['bg_panel']}; border-radius:10px;")
        lc = QVBoxLayout(log_card)
        lc.setContentsMargins(12, 10, 12, 10)
        lc.setSpacing(6)
        lc.addWidget(SectionHeader("log", "Activity Log"))

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(100)
        self._log.setStyleSheet(f"""
            QTextEdit {{
                background: {PALETTE['bg_deep']};
                color: {PALETTE['text_sec']};
                border: 1px solid {PALETTE['border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
                font-size: 11px;
            }}
        """)
        lc.addWidget(self._log)
        c_lay.addWidget(log_card)

        main.addWidget(content, 1)

        # Status bar
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("Ready  —  drop files or click Add Files to begin")

    # ── Menus ───────────────────────────────────
    def _build_menus(self):
        mb = self.menuBar()

        fm = mb.addMenu("File")
        self._add_action(fm, "add_file",   "Add Files…",    self._add_files,   "Ctrl+O")
        self._add_action(fm, "add_folder", "Add Folder…",   self._add_folder)
        fm.addSeparator()
        self._add_action(fm, "clear",      "Clear List",    self._clear_list,  "Ctrl+L")
        fm.addSeparator()
        self._add_action(fm, "remove",     "Exit",          self.close,        "Ctrl+Q")

        cm = mb.addMenu("Convert")
        self._add_action(cm, "play",  "Start", self._start_conversion, "F5")
        self._add_action(cm, "pause", "Pause", self._pause_conversion, "F6")
        self._add_action(cm, "stop",  "Stop",  self._stop_conversion,  "F7")

        tm = mb.addMenu("Tools")
        self._add_action(tm, "settings",   "Settings…",          self._open_settings, "Ctrl+,")
        tm.addSeparator()
        self._add_action(tm, "check_deps", "Check Dependencies", self._check_deps)

        hm = mb.addMenu("Help")
        self._add_action(hm, "about", "About", self._show_about)

    def _add_action(self, menu: QMenu, icon: str, text: str, slot, shortcut: str = None):
        a = QAction(Icons.get(icon, PALETTE["text_sec"], 16), text, self)
        if shortcut:
            a.setShortcut(shortcut)
        a.triggered.connect(slot)
        menu.addAction(a)

    # ── Toolbar ─────────────────────────────────
    def _build_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        def ta(icon, tip, slot):
            a = QAction(Icons.get(icon, PALETTE["text_sec"], 18), tip, self)
            a.triggered.connect(slot)
            tb.addAction(a)

        ta("add_file",   "Add Files",   self._add_files)
        ta("add_folder", "Add Folder",  self._add_folder)
        tb.addSeparator()
        ta("clear",      "Clear List",  self._clear_list)
        tb.addSeparator()
        ta("play",       "Start",       self._start_conversion)
        ta("pause",      "Pause",       self._pause_conversion)
        ta("stop",       "Stop",        self._stop_conversion)
        tb.addSeparator()
        ta("settings",   "Settings",    self._open_settings)

    # ── File Management ──────────────────────────
    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files", "",
            "Video Files (*.mp4 *.avi *.mov *.wmv *.flv *.mkv *.webm);;All Files (*.*)"
        )
        for f in files:
            self._add_file(f)
        self._refresh()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            EXTS = {".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm"}
            for root, _, files in os.walk(folder):
                for fn in files:
                    if Path(fn).suffix.lower() in EXTS:
                        self._add_file(os.path.join(root, fn))
        self._refresh()

    def _add_file(self, path: str):
        for i in range(self._drop.count()):
            if self._drop.item(i).data(Qt.ItemDataRole.UserRole) == path:
                return
        item = QListWidgetItem(Icons.get("video", PALETTE["accent"], 16), f"  {os.path.basename(path)}")
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self._drop.addItem(item)
        self.tasks.append(ConversionTask(path))

    def _on_dropped(self, files: List[str]):
        for f in files:
            if not any(t.input_path == f for t in self.tasks):
                self.tasks.append(ConversionTask(f))
        self._refresh()

    def _clear_list(self):
        if not self.tasks:
            return
        if QMessageBox.question(self, "Clear List",
            "Remove all files from the list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self._drop.clear()
            self.tasks.clear()
            self._clear_task_rows()
            self._refresh()

    def _clear_task_rows(self):
        for i in reversed(range(self._tasks_lay.count() - 1)):
            w = self._tasks_lay.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.task_rows.clear()

    def _refresh(self):
        has = len(self.tasks) > 0
        self._stack.setCurrentIndex(1 if has else 0)
        total_mb = sum(t.file_size for t in self.tasks) / (1024 * 1024)
        if has:
            self._stats.setText(f"{len(self.tasks)} file{'s' if len(self.tasks)>1 else ''}  ·  {total_mb:.1f} MB")
        else:
            self._stats.setText("No files loaded")

    # ── Conversion ──────────────────────────────
    def _start_conversion(self):
        if not self.tasks:
            QMessageBox.warning(self, "No Files", "Please add video files first.")
            return

        # UI state
        self._btn_start.setEnabled(False)
        self._btn_pause.setEnabled(True)
        self._btn_stop.setEnabled(True)
        self._btn_add.setEnabled(False)
        self._btn_folder.setEnabled(False)
        self._btn_clear.setEnabled(False)
        self._wave.set_active(True)

        # Build task rows
        self._clear_task_rows()
        for task in self.tasks:
            row = TaskRow(task)
            self.task_rows.append(row)
            self._tasks_lay.insertWidget(self._tasks_lay.count() - 1, row)

        # Set output paths
        out_dir = self.config.output_directory
        os.makedirs(out_dir, exist_ok=True)
        fmt = self.fmt_combo.currentText().lower()
        for task in self.tasks:
            task.output_path = os.path.join(out_dir, Path(task.input_path).stem + f".{fmt}")

        cfg = {
            "bitrate": self.br_combo.currentText(),
            "preserve_metadata": self.meta_cb.isChecked(),
            "extract_cover": self.cover_cb.isChecked(),
            "normalize": False,
        }

        self.current_worker = ConversionWorker(self.tasks, cfg)
        self.current_worker.progress_updated.connect(self._on_progress)
        self.current_worker.task_completed.connect(self._on_task_done)
        self.current_worker.conversion_started.connect(self._on_task_start)
        self.current_worker.log_message.connect(self._on_log)
        self.current_worker.start()

        self.statusBar().showMessage("Converting…")
        self._log_msg("Conversion started", "info")

    def _pause_conversion(self):
        if self._btn_pause.text().strip() == "Pause":
            self._btn_pause.setText("  Resume")
            self._btn_pause.setIcon(Icons.get("play", PALETTE["text_prim"], 18))
            self._wave.set_active(False)
            self.statusBar().showMessage("Paused")
            self._log_msg("Paused", "warning")
        else:
            self._btn_pause.setText("  Pause")
            self._btn_pause.setIcon(Icons.get("pause", PALETTE["text_prim"], 18))
            self._wave.set_active(True)
            self.statusBar().showMessage("Resumed")
            self._log_msg("Resumed", "info")

    def _stop_conversion(self):
        if self.current_worker:
            if QMessageBox.question(self, "Stop", "Stop the current conversion?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self.current_worker.stop()
                self.current_worker.wait()
                self._reset_controls()
                self.statusBar().showMessage("Stopped")
                self._log_msg("Stopped by user", "warning")

    def _reset_controls(self):
        self._btn_start.setEnabled(True)
        self._btn_pause.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._btn_add.setEnabled(True)
        self._btn_folder.setEnabled(True)
        self._btn_clear.setEnabled(True)
        self._wave.set_active(False)
        self._btn_pause.setText("  Pause")
        self._btn_pause.setIcon(Icons.get("pause", PALETTE["text_prim"], 18))

    # ── Worker Slots ────────────────────────────
    def _on_progress(self, idx: int, val: int, _: int):
        if idx < len(self.task_rows):
            self.task_rows[idx].update_progress(val)
        total = sum(t.progress for t in self.tasks)
        overall = int(total / len(self.tasks)) if self.tasks else 0
        self._ov_bar.setValue(overall)
        self._ov_pct.setText(f"{overall}%")

    def _on_task_start(self, idx: int):
        if idx < len(self.task_rows):
            self.task_rows[idx].update_status("converting")
            self._log_msg(f"Started: {os.path.basename(self.tasks[idx].input_path)}", "info")

    def _on_task_done(self, idx: int, ok: bool, msg: str):
        if idx < len(self.task_rows):
            self.task_rows[idx].update_status("completed" if ok else "failed")
            if ok:
                self.task_rows[idx].update_progress(100)
                self._log_msg(f"✓ {os.path.basename(self.tasks[idx].input_path)}", "success")
            else:
                self._log_msg(f"✗ {os.path.basename(self.tasks[idx].input_path)} — {msg}", "error")
        if all(t.status in ("completed", "failed") for t in self.tasks):
            self._on_all_done()

    def _on_all_done(self):
        self._reset_controls()
        ok = sum(1 for t in self.tasks if t.status == "completed")
        fail = sum(1 for t in self.tasks if t.status == "failed")
        self.statusBar().showMessage(f"Done — {ok} converted, {fail} failed")
        self._log_msg(f"All done — {ok} succeeded, {fail} failed", "info")
        if ok:
            QMessageBox.information(self, "Complete",
                f"Converted {ok} file{'s' if ok > 1 else ''} successfully."
                + (f"\n{fail} failed." if fail else ""))

    def _on_log(self, msg: str, level: str):
        self._log_msg(msg, level)

    # ── Logging ─────────────────────────────────
    def _log_msg(self, msg: str, level: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S")
        colors = {
            "info":    PALETTE["accent"],
            "success": PALETTE["success"],
            "warning": PALETTE["warning"],
            "error":   PALETTE["error"],
        }
        badges = {
            "info": "INF", "success": "OK ", "warning": "WRN", "error": "ERR"
        }
        c = colors.get(level, PALETTE["accent"])
        b = badges.get(level, "INF")
        html = (f'<span style="color:{PALETTE["text_dim"]}">{ts}</span> '
                f'<span style="color:{c}; font-weight:600">[{b}]</span> '
                f'<span style="color:{PALETTE["text_sec"]}">{msg}</span>')
        self._log.append(html)
        self._log.verticalScrollBar().setValue(self._log.verticalScrollBar().maximum())

    # ── Dialogs ─────────────────────────────────
    def _open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self._save_settings()

    def _check_deps(self):
        missing = []
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append("FFmpeg  (https://ffmpeg.org/download.html)")
        if not HAS_MOVIEPY:
            missing.append("moviepy  →  pip install moviepy")
        if not HAS_MUTAGEN:
            missing.append("mutagen  →  pip install mutagen")
        if missing:
            QMessageBox.warning(self, "Missing Dependencies",
                "The following packages are not installed:\n\n" + "\n".join(missing))
        else:
            QMessageBox.information(self, "Dependencies OK",
                "All required dependencies are installed.")

    def _show_about(self):
        QMessageBox.about(self, "About MP4 → MP3 Converter Pro",
            "<h3>MP4 → MP3 Converter Pro</h3>"
            "<p>Version 2.1.0 — Industrial Dark Edition</p>"
            "<p>Batch video-to-audio conversion with<br>"
            "metadata preservation and cover art extraction.</p>"
            "<p style='color:#7B82A0;font-size:11px;'>Requires FFmpeg · PyQt6 · mutagen</p>")

    # ── Settings persistence ─────────────────────
    def _load_settings(self):
        p = os.path.expanduser("~/.mp4tomp3_config.json")
        if os.path.exists(p):
            try:
                with open(p) as f:
                    for k, v in json.load(f).items():
                        if hasattr(self.config, k):
                            setattr(self.config, k, v)
            except Exception:
                pass

    def _save_settings(self):
        p = os.path.expanduser("~/.mp4tomp3_config.json")
        try:
            with open(p, "w") as f:
                json.dump(self.config.__dict__, f, indent=2)
        except Exception:
            pass

    def closeEvent(self, e):
        if self.current_worker and self.current_worker.isRunning():
            if QMessageBox.question(self, "Quit",
                "Conversion in progress. Quit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self.current_worker.stop()
                self.current_worker.wait()
                e.accept()
            else:
                e.ignore()
        else:
            e.accept()


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MP4 to MP3 Converter Pro")
    app.setOrganizationName("AudioTools")
    app.setStyle(QStyleFactory.create("Fusion"))

    # Refined dark palette for native widgets
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(PALETTE["bg_deep"]))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(PALETTE["text_prim"]))
    pal.setColor(QPalette.ColorRole.Base,            QColor(PALETTE["bg_card"]))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(PALETTE["bg_panel"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor(PALETTE["bg_card"]))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor(PALETTE["text_prim"]))
    pal.setColor(QPalette.ColorRole.Text,            QColor(PALETTE["text_prim"]))
    pal.setColor(QPalette.ColorRole.Button,          QColor(PALETTE["bg_card"]))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(PALETTE["text_prim"]))
    pal.setColor(QPalette.ColorRole.BrightText,      QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(PALETTE["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()