"""Pre-configured build templates for common project types."""

TEMPLATES = {
    "تطبيق GUI (PyQt5/Tkinter)": {
        "windowed": True,
        "onefile": True,
        "hidden_imports": ["PyQt5", "PyQt5.QtWidgets", "PyQt5.QtCore", "PyQt5.QtGui"],
        "description": "مناسب لتطبيقات الواجهة الرسومية",
    },
    "تطبيق Console": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": [],
        "description": "مناسب لتطبيقات سطر الأوامر",
    },
    "تطبيق ويب (Flask/Django)": {
        "windowed": False,
        "onefile": False,
        "hidden_imports": ["flask", "jinja2", "werkzeug"],
        "description": "مناسب لتطبيقات الويب",
    },
    "تطبيق بيانات (Pandas/NumPy)": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": ["pandas", "numpy", "openpyxl"],
        "description": "مناسب لتطبيقات معالجة البيانات",
    },
    "لعبة (Pygame)": {
        "windowed": True,
        "onefile": False,
        "hidden_imports": ["pygame"],
        "description": "مناسب للألعاب",
    },
    "إعدادات مخصصة": {
        "windowed": False,
        "onefile": True,
        "hidden_imports": [],
        "description": "تخصيص جميع الإعدادات يدوياً",
    },
}
