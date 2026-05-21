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

نقطة الدخول - الكود الفعلي في حزمة py2exe_gui/
"""

import os
import sys


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from py2exe_gui.app import main

    sys.exit(main())
