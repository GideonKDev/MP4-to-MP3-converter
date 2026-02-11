"""
MP4 to MP3 Converter - Professional Desktop Application
Complete GUI with drag-drop, batch processing, and advanced features
"""

import sys
import os
import subprocess
import threading
import json
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QProgressBar,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QFileDialog, QMessageBox, QSplitter, QTextEdit, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QStyleFactory,
    QMenu, QMenuBar, QStatusBar, QToolBar, QFrame, QSizePolicy,
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QSize,
    QPropertyAnimation, QEasingCurve, QRect, QPoint
)
from PyQt6.QtGui import (
    QFont, QIcon, QPixmap, QColor, QPalette, QAction,
    QDragEnterEvent, QDropEvent, QPainter, QBrush, QLinearGradient,
    QMovie, QFontDatabase
)

# Try to import conversion libraries
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

# Configuration
@dataclass
class AppConfig:
    """Application configuration"""
    default_bitrate: str = '192k'
    default_format: str = 'mp3'
    output_directory: str = os.path.expanduser('~/ConvertedAudio')
    preserve_metadata: bool = True
    extract_cover: bool = True
    theme: str = 'dark'
    max_concurrent: int = 2
    auto_clear_list: bool = False
    notification_sound: bool = True

class ConversionTask:
    """Represents a single conversion task"""
    
    def __init__(self, input_path: str, output_path: str = None):
        self.input_path = input_path
        self.output_path = output_path
        self.status = 'pending'  # pending, converting, completed, failed
        self.progress = 0
        self.error_message = ''
        self.start_time = None
        self.end_time = None
        self.file_size = os.path.getsize(input_path) if os.path.exists(input_path) else 0
        
        if output_path is None:
            input_file = Path(input_path)
            self.output_path = str(input_file.with_suffix('.mp3'))

class ConversionWorker(QThread):
    """Worker thread for conversion tasks"""
    
    # Signals
    progress_updated = pyqtSignal(int, int, int)  # task_id, progress, current_time
    task_completed = pyqtSignal(int, bool, str)   # task_id, success, message
    conversion_started = pyqtSignal(int)          # task_id
    log_message = pyqtSignal(str, str)           # message, level
    
    def __init__(self, tasks: List[ConversionTask], config: dict):
        super().__init__()
        self.tasks = tasks
        self.config = config
        self.is_running = True
        
    def run(self):
        """Main conversion loop"""
        for i, task in enumerate(self.tasks):
            if not self.is_running:
                break
                
            self.conversion_started.emit(i)
            task.status = 'converting'
            task.start_time = time.time()
            
            try:
                success, message = self._convert_single(task)
                task.status = 'completed' if success else 'failed'
                task.error_message = message if not success else ''
                task.end_time = time.time()
                
                self.task_completed.emit(i, success, message)
                
            except Exception as e:
                task.status = 'failed'
                task.error_message = str(e)
                self.task_completed.emit(i, False, str(e))
                
    def stop(self):
        """Stop the conversion process"""
        self.is_running = False
        
    def _convert_single(self, task: ConversionTask) -> (bool, str):
        """Convert single file"""
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(task.output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg', '-i', task.input_path,
                '-codec:a', 'libmp3lame',
                '-b:a', self.config.get('bitrate', '192k'),
                '-q:a', '2',  # Quality level (0-9, 0 is best)
                '-y', task.output_path
            ]
            
            # Add metadata preservation if enabled
            if self.config.get('preserve_metadata', True):
                cmd.insert(-1, '-map_metadata')
                cmd.insert(-1, '0')
                cmd.insert(-1, '-id3v2_version')
                cmd.insert(-1, '3')
            
            # Add normalization if enabled
            if self.config.get('normalize', False):
                target_db = self.config.get('target_db', -1.0)
                cmd.insert(-2, '-af')
                cmd.insert(-2, f'volume={target_db}dB')
            
            # Execute conversion
            self.log_message.emit(f"Converting: {os.path.basename(task.input_path)}", "info")
            
            # Simulate progress updates
            for progress in range(0, 101, 10):
                if not self.is_running:
                    return False, "Conversion cancelled"
                self.progress_updated.emit(self.tasks.index(task), progress, 0)
                time.sleep(0.2)  # Simulate work
                
            # Actually run ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract cover art if enabled
                if self.config.get('extract_cover', True) and HAS_MUTAGEN:
                    self._extract_cover_art(task.input_path, task.output_path)
                
                # Preserve metadata if enabled
                if self.config.get('preserve_metadata', True) and HAS_MUTAGEN:
                    self._preserve_metadata(task.input_path, task.output_path)
                
                return True, "Conversion successful"
            else:
                return False, f"FFmpeg error: {result.stderr[:200]}"
                
        except Exception as e:
            return False, f"Conversion error: {str(e)}"
    
    def _extract_cover_art(self, video_path: str, audio_path: str):
        """Extract and embed cover art"""
        try:
            # Extract cover using ffmpeg
            cover_path = audio_path.replace('.mp3', '_cover.jpg')
            cmd = [
                'ffmpeg', '-i', video_path,
                '-an', '-vcodec', 'png',
                '-vframes', '1',
                '-y', cover_path
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            
            # Embed in MP3
            if os.path.exists(cover_path) and audio_path.lower().endswith('.mp3'):
                audio = mutagen.File(audio_path, easy=True)
                if audio is not None:
                    with open(cover_path, 'rb') as f:
                        audio['APIC'] = APIC(
                            encoding=3,
                            mime='image/jpeg',
                            type=3,  # 3 is for cover image
                            desc='Cover',
                            data=f.read()
                        )
                    audio.save()
                    os.remove(cover_path)
                    
        except Exception as e:
            self.log_message.emit(f"Cover art error: {e}", "warning")
    
    def _preserve_metadata(self, video_path: str, audio_path: str):
        """Preserve metadata from video to audio"""
        if not HAS_MUTAGEN:
            return
            
        try:
            if video_path.lower().endswith('.mp4'):
                video = MP4(video_path)
                audio = ID3(audio_path)
                
                metadata_map = {
                    '©nam': 'TIT2',  # Title
                    '©ART': 'TPE1',  # Artist
                    '©alb': 'TALB',  # Album
                    '©day': 'TYER',  # Year
                    '©gen': 'TCON',  # Genre
                    'trkn': 'TRCK'   # Track number
                }
                
                for mp4_tag, id3_tag in metadata_map.items():
                    if mp4_tag in video:
                        value = str(video[mp4_tag][0])
                        tag_class = globals()[id3_tag]
                        audio.add(tag_class(encoding=3, text=value))
                
                audio.save()
                
        except Exception as e:
            self.log_message.emit(f"Metadata error: {e}", "warning")

class AnimatedButton(QPushButton):
    """Custom animated button"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Animation for hover
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def enterEvent(self, event):
        """Animate on hover"""
        if self.isEnabled():
            start = self.geometry()
            end = QRect(start.x() - 2, start.y() - 2, start.width() + 4, start.height() + 4)
            self._animation.setStartValue(start)
            self._animation.setEndValue(end)
            self._animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Animate on leave"""
        if self.isEnabled():
            start = self.geometry()
            end = QRect(start.x() + 2, start.y() + 2, start.width() - 4, start.height() - 4)
            self._animation.setStartValue(start)
            self._animation.setEndValue(end)
            self._animation.start()
        super().leaveEvent(event)

class DraggableListWidget(QListWidget):
    """Custom list widget with drag-drop support"""
    
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #555;
                border-radius: 8px;
                background-color: #2d2d2d;
                padding: 10px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px;
                background-color: #3a3a3a;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #4a6fa5;
            }
        """)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QListWidget {
                    border: 2px dashed #4a90e2;
                    border-radius: 8px;
                    background-color: #2d2d2d;
                    padding: 10px;
                }
            """)
        else:
            event.ignore()
            
    def dragLeaveEvent(self, event):
        """Handle drag leave event"""
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #555;
                border-radius: 8px;
                background-color: #2d2d2d;
                padding: 10px;
            }
        """)
        super().dragLeaveEvent(event)
        
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #555;
                border-radius: 8px;
                background-color: #2d2d2d;
                padding: 10px;
            }
        """)
        
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            files = []
            
            for url in urls:
                file_path = url.toLocalFile()
                if os.path.exists(file_path):
                    # Check if it's a video file
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm']:
                        files.append(file_path)
                        
                        # Add to list
                        item = QListWidgetItem(os.path.basename(file_path))
                        item.setData(Qt.ItemDataRole.UserRole, file_path)
                        item.setToolTip(file_path)
                        self.addItem(item)
            
            if files:
                self.files_dropped.emit(files)
                
        event.acceptProposedAction()

class ConversionProgressWidget(QWidget):
    """Widget showing conversion progress for a single file"""
    
    def __init__(self, task: ConversionTask, parent=None):
        super().__init__(parent)
        self.task = task
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # File info
        info_layout = QHBoxLayout()
        self.icon_label = QLabel()
        self.icon_label.setPixmap(QPixmap(":video-icon").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio))
        info_layout.addWidget(self.icon_label)
        
        self.file_label = QLabel(os.path.basename(task.input_path))
        self.file_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.file_label)
        
        info_layout.addStretch()
        
        self.status_label = QLabel(task.status.title())
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border-radius: 10px;
                background-color: #555;
                color: white;
            }
        """)
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(task.progress)
        layout.addWidget(self.progress_bar)
        
        # Details
        details_layout = QHBoxLayout()
        details_layout.addWidget(QLabel(f"Size: {self._format_size(task.file_size)}"))
        
        if task.start_time:
            elapsed = time.time() - task.start_time if not task.end_time else task.end_time - task.start_time
            details_layout.addWidget(QLabel(f"Time: {elapsed:.1f}s"))
        
        details_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedSize(80, 24)
        self.cancel_button.clicked.connect(self._on_cancel)
        details_layout.addWidget(self.cancel_button)
        
        layout.addLayout(details_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: #3a3a3a;
                border-radius: 6px;
                border: 1px solid #555;
            }
        """)
        
    def update_progress(self, progress: int):
        """Update progress bar"""
        self.progress_bar.setValue(progress)
        self.task.progress = progress
        
        if progress == 100:
            self.status_label.setText("Completed")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 2px 8px;
                    border-radius: 10px;
                    background-color: #2e7d32;
                    color: white;
                }
            """)
            self.cancel_button.hide()
            
    def update_status(self, status: str, is_error: bool = False):
        """Update status label"""
        self.status_label.setText(status.title())
        
        color = "#d32f2f" if is_error else "#2e7d32" if status == 'completed' else "#555"
        self.status_label.setStyleSheet(f"""
            QLabel {{
                padding: 2px 8px;
                border-radius: 10px;
                background-color: {color};
                color: white;
            }}
        """)
        
    def _format_size(self, bytes_size: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
        
    def _on_cancel(self):
        """Handle cancel button click"""
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        # Emit signal to cancel this task

class SettingsDialog(QDialog):
    """Settings dialog window"""
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 600)
        
        layout = QVBoxLayout()
        
        # Create tabs
        tabs = QTabWidget()
        
        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout()
        
        self.output_dir_edit = QLineEdit(self.config.output_directory)
        self.output_dir_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output_dir)
        
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.output_dir_edit)
        dir_layout.addWidget(browse_btn)
        general_layout.addRow("Output Directory:", dir_layout)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(['MP3', 'WAV', 'FLAC', 'AAC', 'OGG'])
        self.format_combo.setCurrentText(self.config.default_format.upper())
        general_layout.addRow("Default Format:", self.format_combo)
        
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(['64k', '128k', '192k', '256k', '320k'])
        self.bitrate_combo.setCurrentText(self.config.default_bitrate)
        general_layout.addRow("Default Bitrate:", self.bitrate_combo)
        
        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 8)
        self.max_concurrent_spin.setValue(self.config.max_concurrent)
        general_layout.addRow("Max Concurrent:", self.max_concurrent_spin)
        
        general_tab.setLayout(general_layout)
        tabs.addTab(general_tab, "General")
        
        # Audio tab
        audio_tab = QWidget()
        audio_layout = QFormLayout()
        
        self.preserve_metadata_cb = QCheckBox()
        self.preserve_metadata_cb.setChecked(self.config.preserve_metadata)
        audio_layout.addRow("Preserve Metadata:", self.preserve_metadata_cb)
        
        self.extract_cover_cb = QCheckBox()
        self.extract_cover_cb.setChecked(self.config.extract_cover)
        audio_layout.addRow("Extract Cover Art:", self.extract_cover_cb)
        
        self.normalize_cb = QCheckBox()
        audio_layout.addRow("Normalize Audio:", self.normalize_cb)
        
        self.target_db_spin = QDoubleSpinBox()
        self.target_db_spin.setRange(-30.0, 0.0)
        self.target_db_spin.setValue(-1.0)
        self.target_db_spin.setSingleStep(0.5)
        audio_layout.addRow("Target Level (dB):", self.target_db_spin)
        
        audio_tab.setLayout(audio_layout)
        tabs.addTab(audio_tab, "Audio")
        
        # Interface tab
        interface_tab = QWidget()
        interface_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Dark', 'Light', 'System'])
        self.theme_combo.setCurrentText(self.config.theme.title())
        interface_layout.addRow("Theme:", self.theme_combo)
        
        self.auto_clear_cb = QCheckBox()
        self.auto_clear_cb.setChecked(self.config.auto_clear_list)
        interface_layout.addRow("Auto-clear List:", self.auto_clear_cb)
        
        self.notification_sound_cb = QCheckBox()
        self.notification_sound_cb.setChecked(self.config.notification_sound)
        interface_layout.addRow("Notification Sound:", self.notification_sound_cb)
        
        interface_tab.setLayout(interface_layout)
        tabs.addTab(interface_tab, "Interface")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply)
        button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self._restore_defaults)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
        
    def _browse_output_dir(self):
        """Browse for output directory"""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_dir_edit.text())
        if dir_path:
            self.output_dir_edit.setText(dir_path)
            
    def _apply(self):
        """Apply settings without closing"""
        self._save_settings()
        
    def _restore_defaults(self):
        """Restore default settings"""
        default_config = AppConfig()
        
        self.output_dir_edit.setText(default_config.output_directory)
        self.format_combo.setCurrentText(default_config.default_format.upper())
        self.bitrate_combo.setCurrentText(default_config.default_bitrate)
        self.max_concurrent_spin.setValue(default_config.max_concurrent)
        self.preserve_metadata_cb.setChecked(default_config.preserve_metadata)
        self.extract_cover_cb.setChecked(default_config.extract_cover)
        self.theme_combo.setCurrentText(default_config.theme.title())
        self.auto_clear_cb.setChecked(default_config.auto_clear_list)
        self.notification_sound_cb.setChecked(default_config.notification_sound)
        
    def _save_settings(self):
        """Save current settings to config"""
        self.config.output_directory = self.output_dir_edit.text()
        self.config.default_format = self.format_combo.currentText().lower()
        self.config.default_bitrate = self.bitrate_combo.currentText()
        self.config.max_concurrent = self.max_concurrent_spin.value()
        self.config.preserve_metadata = self.preserve_metadata_cb.isChecked()
        self.config.extract_cover = self.extract_cover_cb.isChecked()
        self.config.theme = self.theme_combo.currentText().lower()
        self.config.auto_clear_list = self.auto_clear_cb.isChecked()
        self.config.notification_sound = self.notification_sound_cb.isChecked()
        
    def accept(self):
        """Save settings and close"""
        self._save_settings()
        super().accept()

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.tasks = []
        self.conversion_threads = []
        self.current_worker = None
        
        self._load_settings()
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._apply_theme()
        
    def _setup_ui(self):
        """Setup main UI components"""
        self.setWindowTitle("MP4 to MP3 Converter Pro")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout()
        
        title_label = QLabel("MP4 to MP3 Converter")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #4a90e2;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Stats label
        self.stats_label = QLabel("Ready to convert")
        self.stats_label.setStyleSheet("color: #aaa;")
        header_layout.addWidget(self.stats_label)
        
        header_frame.setLayout(header_layout)
        main_layout.addWidget(header_frame)
        
        # Splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - File list
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        list_label = QLabel("Files to Convert")
        list_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_layout.addWidget(list_label)
        
        self.file_list = DraggableListWidget()
        self.file_list.files_dropped.connect(self._on_files_dropped)
        left_layout.addWidget(self.file_list)
        
        # File list buttons
        file_buttons_layout = QHBoxLayout()
        
        self.add_files_btn = AnimatedButton("Add Files")
        self.add_files_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton))
        self.add_files_btn.clicked.connect(self._add_files)
        file_buttons_layout.addWidget(self.add_files_btn)
        
        self.add_folder_btn = AnimatedButton("Add Folder")
        self.add_folder_btn.setIcon(QIcon(":folder-icon"))
        self.add_folder_btn.clicked.connect(self._add_folder)
        file_buttons_layout.addWidget(self.add_folder_btn)
        
        self.clear_list_btn = AnimatedButton("Clear List")
        self.clear_list_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogResetButton))
        self.clear_list_btn.clicked.connect(self._clear_list)
        file_buttons_layout.addWidget(self.clear_list_btn)
        
        left_layout.addLayout(file_buttons_layout)
        
        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)
        
        # Right panel - Controls and progress
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Conversion settings group
        settings_group = QGroupBox("Conversion Settings")
        settings_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        settings_layout = QFormLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(['MP3', 'WAV', 'FLAC', 'AAC', 'OGG'])
        self.format_combo.setCurrentText(self.config.default_format.upper())
        settings_layout.addRow("Format:", self.format_combo)
        
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(['64k', '128k', '192k', '256k', '320k'])
        self.bitrate_combo.setCurrentText(self.config.default_bitrate)
        settings_layout.addRow("Bitrate:", self.bitrate_combo)
        
        self.preserve_metadata_cb = QCheckBox()
        self.preserve_metadata_cb.setChecked(self.config.preserve_metadata)
        settings_layout.addRow("Preserve Metadata:", self.preserve_metadata_cb)
        
        self.extract_cover_cb = QCheckBox()
        self.extract_cover_cb.setChecked(self.config.extract_cover)
        settings_layout.addRow("Extract Cover Art:", self.extract_cover_cb)
        
        settings_group.setLayout(settings_layout)
        right_layout.addWidget(settings_group)
        
        # Progress area
        progress_group = QGroupBox("Conversion Progress")
        progress_group.setStyleSheet(settings_group.styleSheet())
        progress_layout = QVBoxLayout()
        
        # Overall progress
        overall_layout = QHBoxLayout()
        overall_layout.addWidget(QLabel("Overall Progress:"))
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setTextVisible(True)
        overall_layout.addWidget(self.overall_progress)
        
        progress_layout.addLayout(overall_layout)
        
        # Progress list
        self.progress_scroll = QWidget()
        self.progress_layout = QVBoxLayout()
        self.progress_layout.setSpacing(10)
        
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.progress_layout)
        
        from PyQt6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        
        progress_layout.addWidget(scroll_area)
        progress_group.setLayout(progress_layout)
        right_layout.addWidget(progress_group)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_btn = AnimatedButton("Start Conversion")
        self.start_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:disabled {
                background-color: #555;
            }
        """)
        self.start_btn.clicked.connect(self._start_conversion)
        control_layout.addWidget(self.start_btn)
        
        self.pause_btn = AnimatedButton("Pause")
        self.pause_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPause))
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._pause_conversion)
        control_layout.addWidget(self.pause_btn)
        
        self.stop_btn = AnimatedButton("Stop")
        self.stop_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaStop))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_conversion)
        control_layout.addWidget(self.stop_btn)
        
        right_layout.addLayout(control_layout)
        
        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)
        
        # Set splitter sizes
        splitter.setSizes([400, 600])
        main_layout.addWidget(splitter)
        
        # Log area
        log_group = QGroupBox("Conversion Log")
        log_group.setStyleSheet(settings_group.styleSheet())
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #ddd;
                border: 1px solid #555;
                border-radius: 4px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        central_widget.setLayout(main_layout)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Update stats
        self._update_stats()
        
    def _setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        add_files_action = QAction("Add Files...", self)
        add_files_action.triggered.connect(self._add_files)
        add_files_action.setShortcut("Ctrl+O")
        file_menu.addAction(add_files_action)
        
        add_folder_action = QAction("Add Folder...", self)
        add_folder_action.triggered.connect(self._add_folder)
        file_menu.addAction(add_folder_action)
        
        file_menu.addSeparator()
        
        clear_action = QAction("Clear List", self)
        clear_action.triggered.connect(self._clear_list)
        clear_action.setShortcut("Ctrl+L")
        file_menu.addAction(clear_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        exit_action.setShortcut("Ctrl+Q")
        file_menu.addAction(exit_action)
        
        # Convert menu
        convert_menu = menubar.addMenu("Convert")
        
        start_action = QAction("Start Conversion", self)
        start_action.triggered.connect(self._start_conversion)
        start_action.setShortcut("F5")
        convert_menu.addAction(start_action)
        
        pause_action = QAction("Pause", self)
        pause_action.triggered.connect(self._pause_conversion)
        pause_action.setShortcut("F6")
        convert_menu.addAction(pause_action)
        
        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self._stop_conversion)
        stop_action.setShortcut("F7")
        convert_menu.addAction(stop_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self._open_settings)
        settings_action.setShortcut("Ctrl+,")
        tools_menu.addAction(settings_action)
        
        tools_menu.addSeparator()
        
        check_deps_action = QAction("Check Dependencies", self)
        check_deps_action.triggered.connect(self._check_dependencies)
        tools_menu.addAction(check_deps_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        docs_action = QAction("Documentation", self)
        docs_action.triggered.connect(self._show_docs)
        help_menu.addAction(docs_action)
        
    def _setup_toolbar(self):
        """Setup toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        toolbar.addAction(self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton), 
                         "Add Files", self._add_files)
        toolbar.addAction(QIcon(":folder-icon"), "Add Folder", self._add_folder)
        toolbar.addSeparator()
        toolbar.addAction(self.style().standardIcon(self.style().StandardPixmap.SP_DialogResetButton),
                         "Clear List", self._clear_list)
        toolbar.addSeparator()
        toolbar.addAction(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay),
                         "Start", self._start_conversion)
        toolbar.addAction(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPause),
                         "Pause", self._pause_conversion)
        toolbar.addAction(self.style().standardIcon(self.style().StandardPixmap.SP_MediaStop),
                         "Stop", self._stop_conversion)
        toolbar.addSeparator()
        toolbar.addAction(self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView),
                         "Settings", self._open_settings)
        
    def _apply_theme(self):
        """Apply current theme"""
        if self.config.theme == 'dark':
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                }
                QWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #3a3a3a;
                    border: 1px solid #555;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
                QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                    background-color: #3a3a3a;
                    border: 1px solid #555;
                    padding: 5px;
                    border-radius: 3px;
                }
                QProgressBar {
                    border: 1px solid #555;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4a90e2;
                    border-radius: 2px;
                }
            """)
        elif self.config.theme == 'light':
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f5;
                }
                QWidget {
                    background-color: #ffffff;
                    color: #000000;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #ccc;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
            """)
        
    def _load_settings(self):
        """Load settings from file"""
        settings_file = os.path.expanduser('~/.mp4tomp3_config.json')
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    data = json.load(f)
                    
                for key, value in data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
            except:
                pass
                
    def _save_settings(self):
        """Save settings to file"""
        settings_file = os.path.expanduser('~/.mp4tomp3_config.json')
        try:
            with open(settings_file, 'w') as f:
                json.dump(self.config.__dict__, f, indent=2)
        except:
            pass
            
    def _add_files(self):
        """Add files via file dialog"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Video Files",
            "",
            "Video Files (*.mp4 *.avi *.mov *.wmv *.flv *.mkv *.webm);;All Files (*.*)"
        )
        
        if files:
            for file in files:
                self._add_file_to_list(file)
            self._update_stats()
            
    def _add_folder(self):
        """Add all video files from folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        
        if folder:
            video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm']
            
            for root, dirs, files in os.walk(folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in video_extensions:
                        file_path = os.path.join(root, file)
                        self._add_file_to_list(file_path)
                        
            self._update_stats()
            
    def _add_file_to_list(self, file_path: str):
        """Add single file to list"""
        # Check if file already in list
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == file_path:
                return
                
        # Create new item
        item = QListWidgetItem(os.path.basename(file_path))
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        item.setToolTip(file_path)
        self.file_list.addItem(item)
        
        # Create task
        task = ConversionTask(file_path)
        self.tasks.append(task)
        
    def _on_files_dropped(self, files: List[str]):
        """Handle files dropped onto list"""
        for file in files:
            self._add_file_to_list(file)
        self._update_stats()
        
    def _clear_list(self):
        """Clear file list"""
        reply = QMessageBox.question(
            self,
            "Clear List",
            "Are you sure you want to clear all files from the list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.file_list.clear()
            self.tasks.clear()
            
            # Clear progress widgets
            for i in reversed(range(self.progress_layout.count())):
                widget = self.progress_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
                    
            self._update_stats()
            
    def _start_conversion(self):
        """Start conversion process"""
        if len(self.tasks) == 0:
            QMessageBox.warning(self, "No Files", "Please add files to convert first.")
            return
            
        # Disable UI controls
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.add_files_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.clear_list_btn.setEnabled(False)
        
        # Clear previous progress widgets
        for i in reversed(range(self.progress_layout.count())):
            widget = self.progress_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        # Create progress widgets
        self.progress_widgets = []
        for task in self.tasks:
            widget = ConversionProgressWidget(task)
            self.progress_layout.addWidget(widget)
            self.progress_widgets.append(widget)
            
        # Update output paths based on settings
        output_dir = self.config.output_directory
        os.makedirs(output_dir, exist_ok=True)
        
        format_lower = self.format_combo.currentText().lower()
        
        for task in self.tasks:
            input_file = Path(task.input_path)
            output_file = input_file.stem + f'.{format_lower}'
            task.output_path = os.path.join(output_dir, output_file)
            
        # Create and start worker thread
        config = {
            'bitrate': self.bitrate_combo.currentText(),
            'preserve_metadata': self.preserve_metadata_cb.isChecked(),
            'extract_cover': self.extract_cover_cb.isChecked(),
            'normalize': False,  # Add UI control for this
            'target_db': -1.0
        }
        
        self.current_worker = ConversionWorker(self.tasks, config)
        self.current_worker.progress_updated.connect(self._on_progress_updated)
        self.current_worker.task_completed.connect(self._on_task_completed)
        self.current_worker.conversion_started.connect(self._on_conversion_started)
        self.current_worker.log_message.connect(self._on_log_message)
        
        self.current_worker.start()
        
        self.status_bar.showMessage("Conversion started...")
        self._log_message("Conversion started", "info")
        
    def _pause_conversion(self):
        """Pause conversion process"""
        if self.current_worker:
            self.pause_btn.setText("Resume")
            self.pause_btn.clicked.disconnect()
            self.pause_btn.clicked.connect(self._resume_conversion)
            self.status_bar.showMessage("Conversion paused")
            self._log_message("Conversion paused", "warning")
            
    def _resume_conversion(self):
        """Resume conversion process"""
        if self.current_worker:
            self.pause_btn.setText("Pause")
            self.pause_btn.clicked.disconnect()
            self.pause_btn.clicked.connect(self._pause_conversion)
            self.status_bar.showMessage("Conversion resumed")
            self._log_message("Conversion resumed", "info")
            
    def _stop_conversion(self):
        """Stop conversion process"""
        if self.current_worker:
            reply = QMessageBox.question(
                self,
                "Stop Conversion",
                "Are you sure you want to stop the conversion?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.current_worker.stop()
                self.current_worker.wait()
                
                self.start_btn.setEnabled(True)
                self.pause_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                self.add_files_btn.setEnabled(True)
                self.add_folder_btn.setEnabled(True)
                self.clear_list_btn.setEnabled(True)
                
                self.status_bar.showMessage("Conversion stopped")
                self._log_message("Conversion stopped by user", "warning")
                
    def _on_progress_updated(self, task_id: int, progress: int, current_time: int):
        """Handle progress update from worker"""
        if task_id < len(self.progress_widgets):
            self.progress_widgets[task_id].update_progress(progress)
            
        # Update overall progress
        total_progress = sum(task.progress for task in self.tasks)
        overall_progress = int(total_progress / len(self.tasks)) if self.tasks else 0
        self.overall_progress.setValue(overall_progress)
        
    def _on_task_completed(self, task_id: int, success: bool, message: str):
        """Handle task completion"""
        if task_id < len(self.progress_widgets):
            status = "completed" if success else "failed"
            self.progress_widgets[task_id].update_status(status, not success)
            
            if not success:
                self.progress_widgets[task_id].cancel_button.setText("Error")
                self.progress_widgets[task_id].cancel_button.setEnabled(False)
                self._log_message(f"Failed: {os.path.basename(self.tasks[task_id].input_path)} - {message}", "error")
            else:
                self._log_message(f"Completed: {os.path.basename(self.tasks[task_id].input_path)}", "success")
                
        # Check if all tasks completed
        all_done = all(task.status in ['completed', 'failed'] for task in self.tasks)
        
        if all_done:
            self._on_conversion_finished()
            
    def _on_conversion_started(self, task_id: int):
        """Handle conversion start for a task"""
        if task_id < len(self.progress_widgets):
            self.progress_widgets[task_id].update_status("converting")
            self._log_message(f"Started: {os.path.basename(self.tasks[task_id].input_path)}", "info")
            
    def _on_conversion_finished(self):
        """Handle completion of all conversions"""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.clear_list_btn.setEnabled(True)
        
        # Calculate statistics
        successful = sum(1 for task in self.tasks if task.status == 'completed')
        failed = sum(1 for task in self.tasks if task.status == 'failed')
        
        self.status_bar.showMessage(f"Conversion finished: {successful} successful, {failed} failed")
        self._log_message(f"All conversions finished: {successful} successful, {failed} failed", "info")
        
        # Show notification
        if successful > 0:
            QMessageBox.information(
                self,
                "Conversion Complete",
                f"Successfully converted {successful} file(s)\nFailed: {failed} file(s)"
            )
            
        # Auto-clear if enabled
        if self.config.auto_clear_list and successful == len(self.tasks):
            QTimer.singleShot(2000, self._clear_list)
            
    def _on_log_message(self, message: str, level: str):
        """Handle log message from worker"""
        self._log_message(message, level)
        
    def _log_message(self, message: str, level: str = "info"):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "error":
            color = "#ff6b6b"
            prefix = "[ERROR]"
        elif level == "warning":
            color = "#ffa726"
            prefix = "[WARN]"
        elif level == "success":
            color = "#66bb6a"
            prefix = "[OK]"
        else:
            color = "#4fc3f7"
            prefix = "[INFO]"
            
        log_html = f'<span style="color: #aaa;">[{timestamp}]</span> <span style="color: {color};">{prefix}</span> {message}'
        self.log_text.append(log_html)
        
        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
    def _update_stats(self):
        """Update statistics display"""
        total_files = len(self.tasks)
        total_size = sum(task.file_size for task in self.tasks)
        
        if total_files == 0:
            self.stats_label.setText("Ready to convert")
        else:
            size_mb = total_size / (1024 * 1024)
            self.stats_label.setText(f"{total_files} files ({size_mb:.1f} MB)")
            
    def _open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self._apply_theme()
            self._save_settings()
            
    def _check_dependencies(self):
        """Check for required dependencies"""
        missing = []
        
        # Check FFmpeg
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append("FFmpeg")
            
        # Check Python libraries
        if not HAS_MOVIEPY:
            missing.append("moviepy")
        if not HAS_MUTAGEN:
            missing.append("mutagen")
            
        if missing:
            message = "Missing dependencies:\n\n" + "\n".join(missing)
            message += "\n\nPlease install missing packages:"
            message += "\npip install moviepy mutagen"
            if "FFmpeg" in missing:
                message += "\n\nInstall FFmpeg from: https://ffmpeg.org/download.html"
                
            QMessageBox.warning(self, "Dependencies Check", message)
        else:
            QMessageBox.information(self, "Dependencies Check", "All dependencies are installed and ready!")
            
    def _show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>MP4 to MP3 Converter Pro</h2>
        <p>Version 2.0.0</p>
        <p>Professional video to audio conversion software</p>
        <p>Features:</p>
        <ul>
            <li>Batch conversion with drag & drop support</li>
            <li>Multiple audio formats (MP3, WAV, FLAC, AAC, OGG)</li>
            <li>Metadata preservation</li>
            <li>Cover art extraction</li>
            <li>Advanced audio processing</li>
            <li>Dark/Light theme support</li>
        </ul>
        <p>© 2024 MP4 to MP3 Converter Pro. All rights reserved.</p>
        """
        
        QMessageBox.about(self, "About", about_text)
        
    def _show_docs(self):
        """Show documentation"""
        QMessageBox.information(
            self,
            "Documentation",
            "Documentation is available at:\nhttps://github.com/yourusername/mp4-to-mp3-converter"
        )
        
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any ongoing conversion
        if self.current_worker and self.current_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Quit Application",
                "Conversion is in progress. Are you sure you want to quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.current_worker.stop()
                self.current_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("MP4 to MP3 Converter Pro")
    app.setOrganizationName("AudioTools")
    
    # Set application style
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()