#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         Python to EXE Converter                               ║
║                    تحويل تطبيقات بايثون إلى ملفات تنفيذية                      ║
║──────────────────────────────────────────────────────────────────────────────║
║  تطوير: عبدالكريم العبود | abo.saleh.g@gmail.com                              ║
║  © 2025 [Python to EXE] - All Rights Reserved                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QFileDialog,
    QComboBox, QCheckBox, QGroupBox, QTabWidget, QListWidget,
    QListWidgetItem, QProgressBar, QMessageBox, QFrame,
    QSplitter, QToolButton, QMenu, QAction, QStatusBar,
    QGridLayout, QSpinBox, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette, QPixmap


# ═══════════════════════════════════════════════════════════════════════════════
# المتغيرات الثابتة
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME = "Python to EXE Converter"
APP_VERSION = "1.0.0"
DEVELOPER = "عبدالكريم العبود"
EMAIL = "abo.saleh.g@gmail.com"
COPYRIGHT = "© 2025 [Python to EXE] - All Rights Reserved"

SETTINGS_FILE = "py2exe_settings.json"

# القوالب الجاهزة
TEMPLATES = {
    "تطبيق GUI (PyQt5/Tkinter)": {
        "windowed": True,
        "onefile": True,
        "hidden_imports": ["PyQt5", "PyQt5.QtWidgets", "PyQt5.QtCore", "PyQt5.QtGui"],
        "description": "مناسب لتطبيقات الواجهة الرسومية"
    },
    "تطبيق Console": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": [],
        "description": "مناسب لتطبيقات سطر الأوامر"
    },
    "تطبيق ويب (Flask/Django)": {
        "windowed": False,
        "onefile": False,
        "hidden_imports": ["flask", "jinja2", "werkzeug"],
        "description": "مناسب لتطبيقات الويب"
    },
    "تطبيق بيانات (Pandas/NumPy)": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": ["pandas", "numpy", "openpyxl"],
        "description": "مناسب لتطبيقات معالجة البيانات"
    },
    "لعبة (Pygame)": {
        "windowed": True,
        "onefile": False,
        "hidden_imports": ["pygame"],
        "description": "مناسب للألعاب"
    },
    "إعدادات مخصصة": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": [],
        "description": "تخصيص جميع الإعدادات يدوياً"
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# خيط التحويل
# ═══════════════════════════════════════════════════════════════════════════════

class ConversionThread(QThread):
    """خيط منفصل لعملية التحويل"""
    
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, command, output_dir):
        super().__init__()
        self.command = command
        self.output_dir = output_dir
        self.process = None
        self.is_cancelled = False
    
    def run(self):
        try:
            self.log_signal.emit("═" * 60)
            self.log_signal.emit(f"⏱️ بدء التحويل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_signal.emit("═" * 60)
            self.log_signal.emit(f"\n📋 الأمر المنفذ:\n{' '.join(self.command)}\n")
            self.log_signal.emit("─" * 60)
            
            self.progress_signal.emit(10)
            
            # تنفيذ PyInstaller
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=self.output_dir
            )
            
            self.progress_signal.emit(20)
            
            # قراءة المخرجات
            progress = 20
            for line in self.process.stdout:
                if self.is_cancelled:
                    self.process.terminate()
                    self.finished_signal.emit(False, "تم إلغاء العملية")
                    return
                
                self.log_signal.emit(line.strip())
                
                # تحديث التقدم بناءً على المخرجات
                if "Analyzing" in line:
                    progress = min(progress + 5, 50)
                elif "Processing" in line:
                    progress = min(progress + 2, 70)
                elif "Building" in line:
                    progress = min(progress + 5, 85)
                elif "Copying" in line:
                    progress = min(progress + 2, 95)
                
                self.progress_signal.emit(progress)
            
            self.process.wait()
            
            if self.process.returncode == 0:
                self.progress_signal.emit(100)
                self.log_signal.emit("\n" + "═" * 60)
                self.log_signal.emit("✅ تم التحويل بنجاح!")
                self.log_signal.emit("═" * 60)
                self.finished_signal.emit(True, "تم التحويل بنجاح!")
            else:
                self.log_signal.emit("\n" + "═" * 60)
                self.log_signal.emit("❌ فشل التحويل!")
                self.log_signal.emit("═" * 60)
                self.finished_signal.emit(False, "فشل التحويل - راجع السجل للتفاصيل")
                
        except Exception as e:
            self.log_signal.emit(f"\n❌ خطأ: {str(e)}")
            self.finished_signal.emit(False, str(e))
    
    def cancel(self):
        self.is_cancelled = True
        if self.process:
            self.process.terminate()


# ═══════════════════════════════════════════════════════════════════════════════
# نافذة إضافة Hidden Import
# ═══════════════════════════════════════════════════════════════════════════════

class AddImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة مكتبة مخفية")
        self.setFixedSize(400, 150)
        self.setLayoutDirection(Qt.RightToLeft)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("اسم المكتبة (Hidden Import):")
        self.input = QLineEdit()
        self.input.setPlaceholderText("مثال: PIL, requests, numpy...")
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(label)
        layout.addWidget(self.input)
        layout.addWidget(buttons)
    
    def get_value(self):
        return self.input.text().strip()


# ═══════════════════════════════════════════════════════════════════════════════
# النافذة الرئيسية
# ═══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.conversion_thread = None
        self.settings = {}
        self.load_settings()
        self.init_ui()
        self.check_dependencies()
    
    def init_ui(self):
        """تهيئة واجهة المستخدم"""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1080, 800)
        self.setLayoutDirection(Qt.RightToLeft)
        
        # الستايل
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QWidget {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                color: #cdd6f4;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 2px solid #45475a;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #313244;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 10px;
                color: #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                padding: 5px 12px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 16px;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:pressed {
                background-color: #74c7ec;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
            QPushButton#dangerBtn {
                background-color: #f38ba8;
            }
            QPushButton#dangerBtn:hover {
                background-color: #eba0ac;
            }
            QPushButton#successBtn {
                background-color: #a6e3a1;
            }
            QPushButton#successBtn:hover {
                background-color: #94e2d5;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #45475a;
                border: 2px solid #585b70;
                border-radius: 6px;
                padding: 8px;
                color: #cdd6f4;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #89b4fa;
            }
            QTextEdit {
                background-color: #181825;
                border: 2px solid #45475a;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                color: #a6e3a1;
            }
            QListWidget {
                background-color: #45475a;
                border: 2px solid #585b70;
                border-radius: 6px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #585b70;
                background-color: #45475a;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QProgressBar {
                border: 2px solid #45475a;
                border-radius: 6px;
                text-align: center;
                background-color: #313244;
                color: #cdd6f4;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 2px solid #45475a;
                border-radius: 8px;
                background-color: #313244;
            }
            QTabBar::tab {
                background-color: #45475a;
                padding: 10px 20px;
                margin: 2px;
                border-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QStatusBar {
                background-color: #181825;
                color: #6c7086;
            }
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: bold;
                color: #89b4fa;
            }
            QLabel#subtitleLabel {
                font-size: 12px;
                color: #6c7086;
            }
        """)
        
        # الويدجت الرئيسي
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # العنوان
        header = self.create_header()
        main_layout.addWidget(header)
        
        # التبويبات
        tabs = QTabWidget()
        tabs.addTab(self.create_main_tab(), "⚙️ الإعدادات الرئيسية")
        tabs.addTab(self.create_advanced_tab(), "🔧 إعدادات متقدمة")
        tabs.addTab(self.create_templates_tab(), "📋 القوالب")
        tabs.addTab(self.create_about_tab(), "ℹ️ حول البرنامج")
        main_layout.addWidget(tabs)
        
        # شريط التقدم
        progress_group = QGroupBox("حالة التحويل")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - جاهز للتحويل")
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_group)
        
        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        
        self.convert_btn = QPushButton("🚀 بدء التحويل")
        self.convert_btn.setObjectName("successBtn")
        self.convert_btn.setMinimumHeight(50)
        self.convert_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.convert_btn.clicked.connect(self.start_conversion)
        
        self.cancel_btn = QPushButton("❌ إلغاء")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setMinimumHeight(50)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        
        self.open_folder_btn = QPushButton("📂 فتح مجلد الإخراج")
        self.open_folder_btn.setMinimumHeight(50)
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        
        buttons_layout.addWidget(self.convert_btn)
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addWidget(self.open_folder_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # شريط الحالة
        self.statusBar().showMessage(f"{COPYRIGHT} | {DEVELOPER}")
    
    def create_header(self):
        """إنشاء العنوان"""
        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("🐍 Python to EXE Converter")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("تحويل تطبيقات بايثون إلى ملفات تنفيذية بسهولة")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        return header
    
    def create_main_tab(self):
        """تبويب الإعدادات الرئيسية"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ═══ ملف المصدر ═══
        source_group = QGroupBox("📄 ملف المصدر")
        source_layout = QHBoxLayout(source_group)
        
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("اختر ملف .py للتحويل...")
        self.source_input.textChanged.connect(self.on_source_changed)
        
        source_btn = QPushButton("📂")
        source_btn.clicked.connect(self.browse_source)
        
        source_layout.addWidget(self.source_input, stretch=4)
        source_layout.addWidget(source_btn, stretch=1)
        
        layout.addWidget(source_group)
        
        # ═══ إعدادات الإخراج ═══
        output_group = QGroupBox("📤 إعدادات الإخراج")
        output_layout = QGridLayout(output_group)
        
        # اسم الملف
        output_layout.addWidget(QLabel("اسم الملف الناتج:"), 0, 0)
        self.output_name = QLineEdit()
        self.output_name.setPlaceholderText("اسم الملف بدون .exe")
        output_layout.addWidget(self.output_name, 0, 1)
        
        # مجلد الإخراج
        output_layout.addWidget(QLabel("مجلد الإخراج:"), 1, 0)
        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("اختر مجلد الإخراج...")
        output_dir_btn = QPushButton("📂")
        output_dir_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_dir, 1, 1)
        output_layout.addWidget(output_dir_btn, 1, 2)
        
        # الأيقونة
        output_layout.addWidget(QLabel("أيقونة البرنامج:"), 2, 0)
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("اختياري - ملف .ico")
        icon_btn = QPushButton("📂")
        icon_btn.clicked.connect(self.browse_icon)
        output_layout.addWidget(self.icon_input, 2, 1)
        output_layout.addWidget(icon_btn, 2, 2)
        
        layout.addWidget(output_group)
        
        # ═══ خيارات التحويل ═══
        options_group = QGroupBox("⚙️ خيارات التحويل")
        options_layout = QVBoxLayout(options_group)
        
        # الصف الأول
        row1 = QHBoxLayout()
        self.onefile_check = QCheckBox("ملف واحد (--onefile)")
        self.onefile_check.setChecked(True)
        self.onefile_check.setToolTip("دمج كل الملفات في ملف EXE واحد")
        
        self.windowed_check = QCheckBox("بدون Console (--windowed)")
        self.windowed_check.setToolTip("إخفاء نافذة سطر الأوامر")
        
        self.clean_check = QCheckBox("تنظيف قبل البناء (--clean)")
        self.clean_check.setChecked(True)
        self.clean_check.setToolTip("حذف ملفات البناء السابقة")
        
        row1.addWidget(self.onefile_check)
        row1.addWidget(self.windowed_check)
        row1.addWidget(self.clean_check)
        
        # الصف الثاني
        row2 = QHBoxLayout()
        self.noconsole_check = QCheckBox("--noconsole")
        self.noconsole_check.setToolTip("مرادف لـ --windowed")
        
        self.noconfirm_check = QCheckBox("--noconfirm")
        self.noconfirm_check.setChecked(True)
        self.noconfirm_check.setToolTip("الكتابة فوق الملفات بدون تأكيد")
        
        self.strip_check = QCheckBox("--strip")
        self.strip_check.setToolTip("إزالة معلومات التنقيح (أصغر حجماً)")
        
        row2.addWidget(self.noconsole_check)
        row2.addWidget(self.noconfirm_check)
        row2.addWidget(self.strip_check)
        
        options_layout.addLayout(row1)
        options_layout.addLayout(row2)
        
        layout.addWidget(options_group)
        
        # ═══ السجل ═══
        log_group = QGroupBox("📋 سجل العملية")
        log_layout = QVBoxLayout(log_group)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)
        
        clear_log_btn = QPushButton("🗑️ مسح السجل")
        clear_log_btn.clicked.connect(lambda: self.log_output.clear())
        
        log_layout.addWidget(self.log_output)
        log_layout.addWidget(clear_log_btn)
        
        layout.addWidget(log_group)
        
        return tab
    
    def create_advanced_tab(self):
        """تبويب الإعدادات المتقدمة"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ═══ الملفات الإضافية ═══
        files_group = QGroupBox("📁 الملفات الإضافية (--add-data)")
        files_layout = QVBoxLayout(files_group)
        
        self.extra_files_list = QListWidget()
        self.extra_files_list.setMinimumHeight(100)
        
        files_btn_layout = QHBoxLayout()
        add_file_btn = QPushButton("➕ إضافة ملف")
        add_file_btn.clicked.connect(self.add_extra_file)
        add_folder_btn = QPushButton("📂 إضافة مجلد")
        add_folder_btn.clicked.connect(self.add_extra_folder)
        remove_file_btn = QPushButton("🗑️ حذف المحدد")
        remove_file_btn.clicked.connect(self.remove_extra_file)
        
        files_btn_layout.addWidget(add_file_btn)
        files_btn_layout.addWidget(add_folder_btn)
        files_btn_layout.addWidget(remove_file_btn)
        
        files_layout.addWidget(self.extra_files_list)
        files_layout.addLayout(files_btn_layout)
        
        layout.addWidget(files_group)
        
        # ═══ Hidden Imports ═══
        imports_group = QGroupBox("📦 المكتبات المخفية (--hidden-import)")
        imports_layout = QVBoxLayout(imports_group)
        
        self.hidden_imports_list = QListWidget()
        self.hidden_imports_list.setMinimumHeight(80)
        
        imports_btn_layout = QHBoxLayout()
        add_import_btn = QPushButton("➕ إضافة مكتبة")
        add_import_btn.clicked.connect(self.add_hidden_import)
        remove_import_btn = QPushButton("🗑️ حذف المحدد")
        remove_import_btn.clicked.connect(self.remove_hidden_import)
        detect_imports_btn = QPushButton("🔍 كشف تلقائي")
        detect_imports_btn.clicked.connect(self.detect_imports)
        
        imports_btn_layout.addWidget(add_import_btn)
        imports_btn_layout.addWidget(remove_import_btn)
        imports_btn_layout.addWidget(detect_imports_btn)
        
        imports_layout.addWidget(self.hidden_imports_list)
        imports_layout.addLayout(imports_btn_layout)
        
        layout.addWidget(imports_group)
        
        # ═══ خيارات إضافية ═══
        extra_group = QGroupBox("🔧 خيارات إضافية")
        extra_layout = QGridLayout(extra_group)
        
        extra_layout.addWidget(QLabel("مستوى التحسين:"), 0, 0)
        self.optimize_combo = QComboBox()
        self.optimize_combo.addItems(["0 - بدون تحسين", "1 - تحسين أساسي", "2 - تحسين كامل"])
        extra_layout.addWidget(self.optimize_combo, 0, 1)
        
        extra_layout.addWidget(QLabel("مستوى الضغط (UPX):"), 1, 0)
        self.upx_level = QSpinBox()
        self.upx_level.setRange(0, 9)
        self.upx_level.setValue(0)
        self.upx_level.setToolTip("0 = بدون ضغط، 9 = أقصى ضغط")
        extra_layout.addWidget(self.upx_level, 1, 1)
        
        self.upx_check = QCheckBox("استخدام UPX للضغط")
        self.upx_check.setToolTip("يتطلب تثبيت UPX")
        extra_layout.addWidget(self.upx_check, 2, 0, 1, 2)
        
        layout.addWidget(extra_group)
        
        # ═══ أوامر إضافية ═══
        cmd_group = QGroupBox("💻 أوامر PyInstaller إضافية")
        cmd_layout = QVBoxLayout(cmd_group)
        
        self.extra_args = QLineEdit()
        self.extra_args.setPlaceholderText("أضف أي أوامر إضافية هنا...")
        cmd_layout.addWidget(self.extra_args)
        
        layout.addWidget(cmd_group)
        
        layout.addStretch()
        
        return tab
    
    def create_templates_tab(self):
        """تبويب القوالب"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        templates_group = QGroupBox("📋 القوالب الجاهزة")
        templates_layout = QVBoxLayout(templates_group)
        
        templates_layout.addWidget(QLabel("اختر قالباً لتطبيق الإعدادات المناسبة تلقائياً:"))
        
        self.templates_combo = QComboBox()
        for name, data in TEMPLATES.items():
            self.templates_combo.addItem(f"{name} - {data['description']}", name)
        
        self.templates_combo.currentIndexChanged.connect(self.apply_template)
        templates_layout.addWidget(self.templates_combo)
        
        # وصف القالب
        self.template_desc = QTextEdit()
        self.template_desc.setReadOnly(True)
        self.template_desc.setMaximumHeight(100)
        templates_layout.addWidget(self.template_desc)
        
        apply_btn = QPushButton("✅ تطبيق القالب")
        apply_btn.clicked.connect(self.apply_selected_template)
        templates_layout.addWidget(apply_btn)
        
        layout.addWidget(templates_group)
        
        # ═══ حفظ/تحميل الإعدادات ═══
        save_group = QGroupBox("💾 حفظ وتحميل الإعدادات")
        save_layout = QVBoxLayout(save_group)
        
        save_layout.addWidget(QLabel("يمكنك حفظ إعداداتك الحالية لاستخدامها لاحقاً:"))
        
        save_btn_layout = QHBoxLayout()
        save_settings_btn = QPushButton("💾 حفظ الإعدادات")
        save_settings_btn.clicked.connect(self.save_current_settings)
        load_settings_btn = QPushButton("📂 تحميل إعدادات")
        load_settings_btn.clicked.connect(self.load_saved_settings)
        
        save_btn_layout.addWidget(save_settings_btn)
        save_btn_layout.addWidget(load_settings_btn)
        save_layout.addLayout(save_btn_layout)
        
        layout.addWidget(save_group)
        
        layout.addStretch()
        
        return tab
    
    def create_about_tab(self):
        """تبويب حول البرنامج"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignCenter)
        
        about_text = f"""
        <div style='text-align: center; direction: rtl;'>
            <h1 style='color: #89b4fa;'>🐍 {APP_NAME}</h1>
            <h3 style='color: #a6e3a1;'>الإصدار {APP_VERSION}</h3>
            
            <hr style='border: 1px solid #45475a; margin: 20px 0;'>
            
            <p style='font-size: 14px; color: #cdd6f4;'>
                أداة احترافية لتحويل تطبيقات بايثون إلى ملفات تنفيذية EXE<br>
                باستخدام PyInstaller مع واجهة رسومية سهلة الاستخدام
            </p>
            
            <hr style='border: 1px solid #45475a; margin: 20px 0;'>
            
            <h3 style='color: #f9e2af;'>👨‍💻 المطور</h3>
            <p style='font-size: 16px; color: #cdd6f4; font-weight: bold;'>
                {DEVELOPER}
            </p>
            <p style='color: #89b4fa;'>
                📧 {EMAIL}
            </p>
            
            <hr style='border: 1px solid #45475a; margin: 20px 0;'>
            
            <p style='color: #6c7086; font-size: 12px;'>
                {COPYRIGHT}
            </p>
            
            <hr style='border: 1px solid #45475a; margin: 20px 0;'>
            
            <h4 style='color: #cba6f7;'>✨ الميزات</h4>
            <ul style='text-align: right; color: #cdd6f4;'>
                <li>تحويل أي ملف بايثون إلى EXE</li>
                <li>إضافة أيقونة مخصصة</li>
                <li>إضافة ملفات وموارد إضافية</li>
                <li>قوالب جاهزة لأنواع التطبيقات</li>
                <li>كشف تلقائي للمكتبات</li>
                <li>حفظ وتحميل الإعدادات</li>
                <li>سجل تفصيلي للعملية</li>
            </ul>
        </div>
        """
        
        about_label = QLabel(about_text)
        about_label.setWordWrap(True)
        about_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(about_label)
        
        return tab
    
    # ═══════════════════════════════════════════════════════════════════════════
    # الوظائف
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_dependencies(self):
        """التحقق من المتطلبات"""
        self.log_output.append("🔍 جاري التحقق من المتطلبات...")
        
        # التحقق من Python
        try:
            result = subprocess.run(
                [sys.executable, "--version"],
                capture_output=True, text=True
            )
            self.log_output.append(f"✅ Python: {result.stdout.strip()}")
        except:
            self.log_output.append("❌ Python غير موجود!")
        
        # التحقق من PyInstaller
        try:
            result = subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--version"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                self.log_output.append(f"✅ PyInstaller: {result.stdout.strip()}")
            else:
                self.log_output.append("⚠️ PyInstaller غير مثبت - سيتم تثبيته عند التحويل")
        except:
            self.log_output.append("⚠️ PyInstaller غير مثبت - سيتم تثبيته عند التحويل")
        
        self.log_output.append("─" * 50)
        self.log_output.append("✅ جاهز للاستخدام!\n")
    
    def browse_source(self):
        """اختيار ملف المصدر"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف بايثون",
            self.settings.get("last_source_dir", ""),
            "Python Files (*.py *.pyw);;All Files (*.*)"
        )
        if file_path:
            self.source_input.setText(file_path)
            self.settings["last_source_dir"] = os.path.dirname(file_path)
    
    def on_source_changed(self, text):
        """عند تغيير ملف المصدر"""
        if text and os.path.isfile(text):
            # تعيين اسم الملف الناتج تلقائياً
            base_name = os.path.splitext(os.path.basename(text))[0]
            if not self.output_name.text():
                self.output_name.setText(base_name)
            
            # تعيين مجلد الإخراج تلقائياً
            if not self.output_dir.text():
                self.output_dir.setText(os.path.dirname(text))
    
    def browse_output_dir(self):
        """اختيار مجلد الإخراج"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "اختر مجلد الإخراج",
            self.settings.get("last_output_dir", "")
        )
        if dir_path:
            self.output_dir.setText(dir_path)
            self.settings["last_output_dir"] = dir_path
    
    def browse_icon(self):
        """اختيار الأيقونة"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر أيقونة",
            "",
            "Icon Files (*.ico);;All Files (*.*)"
        )
        if file_path:
            self.icon_input.setText(file_path)
    
    def add_extra_file(self):
        """إضافة ملف إضافي"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف إضافي", "", "All Files (*.*)"
        )
        if file_path:
            self.extra_files_list.addItem(file_path)
    
    def add_extra_folder(self):
        """إضافة مجلد إضافي"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "اختر مجلد إضافي", ""
        )
        if dir_path:
            self.extra_files_list.addItem(dir_path)
    
    def remove_extra_file(self):
        """حذف ملف إضافي"""
        current = self.extra_files_list.currentRow()
        if current >= 0:
            self.extra_files_list.takeItem(current)
    
    def add_hidden_import(self):
        """إضافة مكتبة مخفية"""
        dialog = AddImportDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            value = dialog.get_value()
            if value:
                self.hidden_imports_list.addItem(value)
    
    def remove_hidden_import(self):
        """حذف مكتبة مخفية"""
        current = self.hidden_imports_list.currentRow()
        if current >= 0:
            self.hidden_imports_list.takeItem(current)
    
    def detect_imports(self):
        """كشف المكتبات تلقائياً"""
        source = self.source_input.text()
        if not source or not os.path.isfile(source):
            QMessageBox.warning(self, "تنبيه", "اختر ملف المصدر أولاً!")
            return
        
        self.log_output.append("🔍 جاري كشف المكتبات المستخدمة...")
        
        try:
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # كشف الاستيرادات
            imports = set()
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import '):
                    parts = line[7:].split(',')
                    for part in parts:
                        module = part.strip().split(' as ')[0].split('.')[0]
                        if module:
                            imports.add(module)
                elif line.startswith('from '):
                    module = line[5:].split(' import')[0].strip().split('.')[0]
                    if module:
                        imports.add(module)
            
            # إضافة المكتبات غير الموجودة
            added = 0
            existing = [self.hidden_imports_list.item(i).text() 
                       for i in range(self.hidden_imports_list.count())]
            
            for imp in imports:
                if imp not in existing and imp not in ['sys', 'os', 'json', 'datetime', 
                    'pathlib', 'threading', 'subprocess', 're', 'math', 'random', 'time']:
                    self.hidden_imports_list.addItem(imp)
                    added += 1
            
            self.log_output.append(f"✅ تم كشف {len(imports)} مكتبة، تمت إضافة {added} مكتبة جديدة")
            
        except Exception as e:
            self.log_output.append(f"❌ خطأ في كشف المكتبات: {str(e)}")
    
    def apply_template(self, index):
        """عرض وصف القالب"""
        template_name = self.templates_combo.currentData()
        if template_name and template_name in TEMPLATES:
            template = TEMPLATES[template_name]
            desc = f"""
            <b>القالب:</b> {template_name}<br>
            <b>الوصف:</b> {template['description']}<br>
            <b>نافذة:</b> {'نعم' if template['windowed'] else 'لا'}<br>
            <b>ملف واحد:</b> {'نعم' if template['onefile'] else 'لا'}<br>
            <b>مكتبات مخفية:</b> {', '.join(template['hidden_imports']) if template['hidden_imports'] else 'لا يوجد'}
            """
            self.template_desc.setHtml(desc)
    
    def apply_selected_template(self):
        """تطبيق القالب المحدد"""
        template_name = self.templates_combo.currentData()
        if template_name and template_name in TEMPLATES:
            template = TEMPLATES[template_name]
            
            self.windowed_check.setChecked(template['windowed'])
            self.onefile_check.setChecked(template['onefile'])
            
            # إضافة المكتبات المخفية
            for imp in template['hidden_imports']:
                existing = [self.hidden_imports_list.item(i).text() 
                           for i in range(self.hidden_imports_list.count())]
                if imp not in existing:
                    self.hidden_imports_list.addItem(imp)
            
            self.log_output.append(f"✅ تم تطبيق قالب: {template_name}")
            QMessageBox.information(self, "نجاح", f"تم تطبيق قالب: {template_name}")
    
    def save_current_settings(self):
        """حفظ الإعدادات الحالية"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "حفظ الإعدادات",
            "py2exe_config.json",
            "JSON Files (*.json)"
        )
        if file_path:
            settings = {
                "source": self.source_input.text(),
                "output_name": self.output_name.text(),
                "output_dir": self.output_dir.text(),
                "icon": self.icon_input.text(),
                "onefile": self.onefile_check.isChecked(),
                "windowed": self.windowed_check.isChecked(),
                "clean": self.clean_check.isChecked(),
                "noconsole": self.noconsole_check.isChecked(),
                "noconfirm": self.noconfirm_check.isChecked(),
                "strip": self.strip_check.isChecked(),
                "extra_files": [self.extra_files_list.item(i).text() 
                               for i in range(self.extra_files_list.count())],
                "hidden_imports": [self.hidden_imports_list.item(i).text() 
                                  for i in range(self.hidden_imports_list.count())],
                "optimize": self.optimize_combo.currentIndex(),
                "upx": self.upx_check.isChecked(),
                "upx_level": self.upx_level.value(),
                "extra_args": self.extra_args.text()
            }
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                self.log_output.append(f"✅ تم حفظ الإعدادات: {file_path}")
                QMessageBox.information(self, "نجاح", "تم حفظ الإعدادات بنجاح!")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل حفظ الإعدادات:\n{str(e)}")
    
    def load_saved_settings(self):
        """تحميل إعدادات محفوظة"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "تحميل إعدادات",
            "",
            "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.source_input.setText(settings.get("source", ""))
                self.output_name.setText(settings.get("output_name", ""))
                self.output_dir.setText(settings.get("output_dir", ""))
                self.icon_input.setText(settings.get("icon", ""))
                self.onefile_check.setChecked(settings.get("onefile", True))
                self.windowed_check.setChecked(settings.get("windowed", False))
                self.clean_check.setChecked(settings.get("clean", True))
                self.noconsole_check.setChecked(settings.get("noconsole", False))
                self.noconfirm_check.setChecked(settings.get("noconfirm", True))
                self.strip_check.setChecked(settings.get("strip", False))
                
                self.extra_files_list.clear()
                for f in settings.get("extra_files", []):
                    self.extra_files_list.addItem(f)
                
                self.hidden_imports_list.clear()
                for imp in settings.get("hidden_imports", []):
                    self.hidden_imports_list.addItem(imp)
                
                self.optimize_combo.setCurrentIndex(settings.get("optimize", 0))
                self.upx_check.setChecked(settings.get("upx", False))
                self.upx_level.setValue(settings.get("upx_level", 0))
                self.extra_args.setText(settings.get("extra_args", ""))
                
                self.log_output.append(f"✅ تم تحميل الإعدادات: {file_path}")
                QMessageBox.information(self, "نجاح", "تم تحميل الإعدادات بنجاح!")
                
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل تحميل الإعدادات:\n{str(e)}")
    
    def load_settings(self):
        """تحميل الإعدادات المحفوظة"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except:
                self.settings = {}
    
    def save_settings(self):
        """حفظ الإعدادات"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def build_command(self):
        """بناء أمر PyInstaller"""
        source = self.source_input.text()
        
        if not source or not os.path.isfile(source):
            return None, "اختر ملف المصدر أولاً!"
        
        cmd = [sys.executable, "-m", "PyInstaller"]
        
        # الخيارات الأساسية
        if self.onefile_check.isChecked():
            cmd.append("--onefile")
        
        if self.windowed_check.isChecked():
            cmd.append("--windowed")
        
        if self.noconsole_check.isChecked():
            cmd.append("--noconsole")
        
        if self.clean_check.isChecked():
            cmd.append("--clean")
        
        if self.noconfirm_check.isChecked():
            cmd.append("--noconfirm")
        
        if self.strip_check.isChecked():
            cmd.append("--strip")
        
        # اسم الملف
        if self.output_name.text():
            cmd.extend(["--name", self.output_name.text()])
        
        # الأيقونة
        if self.icon_input.text() and os.path.isfile(self.icon_input.text()):
            cmd.extend(["--icon", self.icon_input.text()])
        
        # مجلد الإخراج
        if self.output_dir.text():
            cmd.extend(["--distpath", os.path.join(self.output_dir.text(), "dist")])
            cmd.extend(["--workpath", os.path.join(self.output_dir.text(), "build")])
            cmd.extend(["--specpath", self.output_dir.text()])
        
        # الملفات الإضافية
        sep = ";" if sys.platform == "win32" else ":"
        for i in range(self.extra_files_list.count()):
            path = self.extra_files_list.item(i).text()
            if os.path.exists(path):
                dest = os.path.basename(path)
                cmd.extend(["--add-data", f"{path}{sep}{dest}"])
        
        # المكتبات المخفية
        for i in range(self.hidden_imports_list.count()):
            imp = self.hidden_imports_list.item(i).text()
            cmd.extend(["--hidden-import", imp])
        
        # مستوى التحسين
        opt_level = self.optimize_combo.currentIndex()
        if opt_level > 0:
            cmd.append(f"-O{opt_level}")
        
        # UPX
        if self.upx_check.isChecked():
            cmd.append("--upx-dir=upx")
            if self.upx_level.value() > 0:
                cmd.append(f"--upx-level={self.upx_level.value()}")
        else:
            cmd.append("--noupx")
        
        # أوامر إضافية
        if self.extra_args.text():
            cmd.extend(self.extra_args.text().split())
        
        # ملف المصدر
        cmd.append(source)
        
        return cmd, None
    
    def start_conversion(self):
        """بدء عملية التحويل"""
        cmd, error = self.build_command()
        
        if error:
            QMessageBox.warning(self, "تنبيه", error)
            return
        
        # تحقق من تثبيت PyInstaller
        try:
            subprocess.run(
                [sys.executable, "-m", "PyInstaller", "--version"],
                capture_output=True, check=True
            )
        except:
            self.log_output.append("📦 جاري تثبيت PyInstaller...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "pyinstaller"],
                    capture_output=True, check=True
                )
                self.log_output.append("✅ تم تثبيت PyInstaller بنجاح!")
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"فشل تثبيت PyInstaller:\n{str(e)}")
                return
        
        # تحديد مجلد العمل
        work_dir = self.output_dir.text() or os.path.dirname(self.source_input.text())
        
        # بدء التحويل
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - جاري التحويل...")
        
        self.conversion_thread = ConversionThread(cmd, work_dir)
        self.conversion_thread.log_signal.connect(self.log_output.append)
        self.conversion_thread.progress_signal.connect(self.progress_bar.setValue)
        self.conversion_thread.finished_signal.connect(self.on_conversion_finished)
        self.conversion_thread.start()
    
    def cancel_conversion(self):
        """إلغاء عملية التحويل"""
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.cancel()
            self.log_output.append("⚠️ جاري إلغاء العملية...")
    
    def on_conversion_finished(self, success, message):
        """عند انتهاء التحويل"""
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success:
            self.progress_bar.setFormat("✅ تم التحويل بنجاح!")
            QMessageBox.information(self, "نجاح", message)
        else:
            self.progress_bar.setFormat("❌ فشل التحويل")
            if "إلغاء" not in message:
                QMessageBox.critical(self, "خطأ", message)
    
    def open_output_folder(self):
        """فتح مجلد الإخراج"""
        output_dir = self.output_dir.text() or os.path.dirname(self.source_input.text())
        dist_dir = os.path.join(output_dir, "dist")
        
        if os.path.isdir(dist_dir):
            target = dist_dir
        elif os.path.isdir(output_dir):
            target = output_dir
        else:
            QMessageBox.warning(self, "تنبيه", "مجلد الإخراج غير موجود!")
            return
        
        if sys.platform == "win32":
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.run(["open", target])
        else:
            subprocess.run(["xdg-open", target])
    
    def closeEvent(self, event):
        """عند إغلاق النافذة"""
        self.save_settings()
        if self.conversion_thread and self.conversion_thread.isRunning():
            reply = QMessageBox.question(
                self, "تأكيد",
                "هناك عملية تحويل جارية. هل تريد الإلغاء والخروج؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.conversion_thread.cancel()
                self.conversion_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ═══════════════════════════════════════════════════════════════════════════════
# نقطة البداية
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # ═══ دعم الشاشات عالية الدقة ═══
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    
    # تعيين الخط
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
