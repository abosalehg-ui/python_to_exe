"""User-facing strings, centralized to enable future i18n.

All UI text lives here so Phase 3 (multi-language support) can replace this
module with a QTranslator-based system without touching the UI code.
"""


class Ar:
    """Arabic strings (default locale)."""

    # Window & tabs
    WINDOW_TITLE_FMT = "{name} v{version}"
    TAB_MAIN = "⚙️ الإعدادات الرئيسية"
    TAB_ADVANCED = "🔧 إعدادات متقدمة"
    TAB_TEMPLATES = "📋 القوالب"
    TAB_ABOUT = "ℹ️ حول البرنامج"

    # Header
    HEADER_TITLE = "🐍 Python to EXE Converter"
    HEADER_SUBTITLE = "تحويل تطبيقات بايثون إلى ملفات تنفيذية بسهولة"

    # Main tab
    GROUP_SOURCE = "📄 ملف المصدر"
    SOURCE_PLACEHOLDER = "اختر ملف .py للتحويل..."
    GROUP_OUTPUT = "📤 إعدادات الإخراج"
    OUTPUT_NAME_LABEL = "اسم الملف الناتج:"
    OUTPUT_NAME_PLACEHOLDER = "اسم الملف بدون .exe"
    OUTPUT_DIR_LABEL = "مجلد الإخراج:"
    OUTPUT_DIR_PLACEHOLDER = "اختر مجلد الإخراج..."
    ICON_LABEL = "أيقونة البرنامج:"
    ICON_PLACEHOLDER = "اختياري - ملف .ico"

    GROUP_OPTIONS = "⚙️ خيارات التحويل"
    OPT_ONEFILE = "ملف واحد (--onefile)"
    OPT_ONEFILE_TIP = "دمج كل الملفات في ملف EXE واحد"
    OPT_WINDOWED = "بدون Console (--windowed)"
    OPT_WINDOWED_TIP = "إخفاء نافذة سطر الأوامر"
    OPT_CLEAN = "تنظيف قبل البناء (--clean)"
    OPT_CLEAN_TIP = "حذف ملفات البناء السابقة"
    OPT_NOCONSOLE = "--noconsole"
    OPT_NOCONSOLE_TIP = "مرادف لـ --windowed"
    OPT_NOCONFIRM = "--noconfirm"
    OPT_NOCONFIRM_TIP = "الكتابة فوق الملفات بدون تأكيد"
    OPT_STRIP = "--strip"
    OPT_STRIP_TIP = "إزالة معلومات التنقيح (أصغر حجماً)"

    # Logs
    GROUP_LOG = "📋 سجل العملية"
    CLEAR_LOG = "🗑️ مسح السجل"
    LOG_CHECKING_DEPS = "🔍 جاري التحقق من المتطلبات..."
    LOG_PYTHON_FOUND = "✅ Python: {version}"
    LOG_PYTHON_MISSING = "❌ Python غير موجود!"
    LOG_PYINSTALLER_FOUND = "✅ PyInstaller: {version}"
    LOG_PYINSTALLER_MISSING = "⚠️ PyInstaller غير مثبت - سيتم تثبيته عند التحويل"
    LOG_READY = "✅ جاهز للاستخدام!\n"
    LOG_DETECTING_IMPORTS = "🔍 جاري كشف المكتبات المستخدمة..."
    LOG_DETECT_RESULT = "✅ تم كشف {total} مكتبة، تمت إضافة {added} مكتبة جديدة"
    LOG_DETECT_ERROR = "❌ خطأ في كشف المكتبات: {error}"
    LOG_INSTALL_PYINSTALLER = "📦 جاري تثبيت PyInstaller..."
    LOG_INSTALL_PYINSTALLER_OK = "✅ تم تثبيت PyInstaller بنجاح!"
    LOG_TEMPLATE_APPLIED = "✅ تم تطبيق قالب: {name}"
    LOG_SETTINGS_SAVED = "✅ تم حفظ الإعدادات: {path}"
    LOG_SETTINGS_LOADED = "✅ تم تحميل الإعدادات: {path}"
    LOG_CANCELLING = "⚠️ جاري إلغاء العملية..."

    # Conversion thread
    CONV_START = "⏱️ بدء التحويل: {time}"
    CONV_COMMAND = "\n📋 الأمر المنفذ:\n{cmd}\n"
    CONV_SUCCESS = "✅ تم التحويل بنجاح!"
    CONV_FAILED = "❌ فشل التحويل!"
    CONV_ERROR = "\n❌ خطأ: {error}"
    CONV_CANCELLED = "تم إلغاء العملية"
    CONV_FAILED_MSG = "فشل التحويل - راجع السجل للتفاصيل"

    # Advanced tab
    GROUP_EXTRA_FILES = "📁 الملفات الإضافية (--add-data)"
    BTN_ADD_FILE = "➕ إضافة ملف"
    BTN_ADD_FOLDER = "📂 إضافة مجلد"
    BTN_REMOVE_SELECTED = "🗑️ حذف المحدد"
    GROUP_HIDDEN_IMPORTS = "📦 المكتبات المخفية (--hidden-import)"
    BTN_ADD_IMPORT = "➕ إضافة مكتبة"
    BTN_AUTO_DETECT = "🔍 كشف تلقائي"
    GROUP_EXTRA_OPTS = "🔧 خيارات إضافية"
    OPT_LEVEL_LABEL = "مستوى التحسين:"
    OPT_LEVELS = ["0 - بدون تحسين", "1 - تحسين أساسي", "2 - تحسين كامل"]
    UPX_LEVEL_LABEL = "مستوى الضغط (UPX):"
    UPX_LEVEL_TIP = "0 = بدون ضغط، 9 = أقصى ضغط"
    UPX_USE = "استخدام UPX للضغط"
    UPX_USE_TIP = "يتطلب تثبيت UPX"
    GROUP_EXTRA_ARGS = "💻 أوامر PyInstaller إضافية"
    EXTRA_ARGS_PLACEHOLDER = "أضف أي أوامر إضافية هنا..."

    # Templates tab
    GROUP_TEMPLATES = "📋 القوالب الجاهزة"
    TEMPLATES_HINT = "اختر قالباً لتطبيق الإعدادات المناسبة تلقائياً:"
    BTN_APPLY_TEMPLATE = "✅ تطبيق القالب"
    GROUP_SAVE_LOAD = "💾 حفظ وتحميل الإعدادات"
    SAVE_LOAD_HINT = "يمكنك حفظ إعداداتك الحالية لاستخدامها لاحقاً:"
    BTN_SAVE_SETTINGS = "💾 حفظ الإعدادات"
    BTN_LOAD_SETTINGS = "📂 تحميل إعدادات"

    # Dialog
    DIALOG_ADD_IMPORT_TITLE = "إضافة مكتبة مخفية"
    DIALOG_ADD_IMPORT_LABEL = "اسم المكتبة (Hidden Import):"
    DIALOG_ADD_IMPORT_PLACEHOLDER = "مثال: PIL, requests, numpy..."

    # File dialogs
    DIALOG_CHOOSE_PY = "اختر ملف بايثون"
    DIALOG_FILTER_PY = "Python Files (*.py *.pyw);;All Files (*.*)"
    DIALOG_CHOOSE_OUT_DIR = "اختر مجلد الإخراج"
    DIALOG_CHOOSE_ICON = "اختر أيقونة"
    DIALOG_FILTER_ICON = "Icon Files (*.ico);;All Files (*.*)"
    DIALOG_CHOOSE_EXTRA_FILE = "اختر ملف إضافي"
    DIALOG_FILTER_ALL = "All Files (*.*)"
    DIALOG_CHOOSE_EXTRA_FOLDER = "اختر مجلد إضافي"
    DIALOG_SAVE_SETTINGS = "حفظ الإعدادات"
    DIALOG_LOAD_SETTINGS = "تحميل إعدادات"
    DIALOG_FILTER_JSON = "JSON Files (*.json)"

    # Log enhancements (Phase 2)
    LOG_SEARCH_PLACEHOLDER = "🔍 ابحث في السجل..."
    BTN_EXPORT_LOG = "💾 تصدير السجل"
    DIALOG_EXPORT_LOG = "تصدير السجل"
    DIALOG_FILTER_LOG = "Log Files (*.log *.txt);;All Files (*.*)"
    LOG_EXPORT_OK = "✅ تم تصدير السجل: {path}"
    LOG_EXPORT_FAIL = "فشل تصدير السجل:\n{error}"
    LOG_DROPPED_SOURCE = "📁 تم سحب الملف: {path}"
    LOG_DROPPED_ICON = "🎨 تم سحب الأيقونة: {path}"
    LOG_DROPPED_EXTRA = "➕ تم سحب ملف إضافي: {path}"

    # Dry-run preview (Phase 2)
    BTN_PREVIEW_CMD = "👁️ معاينة الأمر"
    DIALOG_PREVIEW_TITLE = "معاينة أمر PyInstaller"
    DIALOG_PREVIEW_HINT = "هذا هو الأمر الذي سيُنفَّذ عند الضغط على \"بدء التحويل\":"
    BTN_COPY_CMD = "📋 نسخ"
    BTN_CLOSE = "إغلاق"
    MSG_COPIED = "تم نسخ الأمر إلى الحافظة"

    # Theme toggle (Phase 2)
    BTN_TOGGLE_THEME = "🌓 تبديل السمة"
    THEME_DARK = "dark"
    THEME_LIGHT = "light"

    # Status / Progress
    PROGRESS_READY = "%p% - جاهز للتحويل"
    PROGRESS_CONVERTING = "%p% - جاري التحويل..."
    PROGRESS_DONE = "✅ تم التحويل بنجاح!"
    PROGRESS_FAILED = "❌ فشل التحويل"
    PROGRESS_GROUP = "حالة التحويل"

    # Buttons
    BTN_CONVERT = "🚀 بدء التحويل"
    BTN_CANCEL = "❌ إلغاء"
    BTN_OPEN_FOLDER = "📂 فتح مجلد الإخراج"

    # Messages
    MSG_WARNING = "تنبيه"
    MSG_ERROR = "خطأ"
    MSG_SUCCESS = "نجاح"
    MSG_CONFIRM = "تأكيد"
    ERR_NO_SOURCE = "اختر ملف المصدر أولاً!"
    ERR_INSTALL_PYINSTALLER_FAIL = "فشل تثبيت PyInstaller:\n{error}"
    ERR_OUTPUT_MISSING = "مجلد الإخراج غير موجود!"
    ERR_SAVE_FAIL = "فشل حفظ الإعدادات:\n{error}"
    ERR_LOAD_FAIL = "فشل تحميل الإعدادات:\n{error}"
    MSG_SAVED_OK = "تم حفظ الإعدادات بنجاح!"
    MSG_LOADED_OK = "تم تحميل الإعدادات بنجاح!"
    MSG_TEMPLATE_OK_FMT = "تم تطبيق قالب: {name}"
    MSG_CLOSE_CONFIRM = "هناك عملية تحويل جارية. هل تريد الإلغاء والخروج؟"

    # Template description
    TEMPLATE_DESC_FMT = (
        "<b>القالب:</b> {name}<br>"
        "<b>الوصف:</b> {desc}<br>"
        "<b>نافذة:</b> {windowed}<br>"
        "<b>ملف واحد:</b> {onefile}<br>"
        "<b>مكتبات مخفية:</b> {imports}"
    )
    YES = "نعم"
    NO = "لا"
    NONE = "لا يوجد"

    # About tab
    ABOUT_VERSION_FMT = "الإصدار {version}"
    ABOUT_DESC = (
        "أداة احترافية لتحويل تطبيقات بايثون إلى ملفات تنفيذية EXE<br>"
        "باستخدام PyInstaller مع واجهة رسومية سهلة الاستخدام"
    )
    ABOUT_DEVELOPER_LABEL = "👨‍💻 المطور"
    ABOUT_FEATURES_LABEL = "✨ الميزات"
    ABOUT_FEATURES = [
        "تحويل أي ملف بايثون إلى EXE",
        "إضافة أيقونة مخصصة",
        "إضافة ملفات وموارد إضافية",
        "قوالب جاهزة لأنواع التطبيقات",
        "كشف تلقائي للمكتبات",
        "حفظ وتحميل الإعدادات",
        "سجل تفصيلي للعملية",
    ]

    # Language selector (Phase 3)
    LANGUAGE_LABEL = "🌐 اللغة:"
    LANGUAGE_NATIVE = "العربية"
    MSG_RESTART_REQUIRED = "يجب إعادة تشغيل التطبيق لتطبيق اللغة الجديدة."

    # Template names & descriptions (Phase 3 — accessed via templates helpers)
    TPL_GUI_NAME = "تطبيق GUI (PyQt5/Tkinter)"
    TPL_GUI_DESC = "مناسب لتطبيقات الواجهة الرسومية"
    TPL_CONSOLE_NAME = "تطبيق Console"
    TPL_CONSOLE_DESC = "مناسب لتطبيقات سطر الأوامر"
    TPL_WEB_NAME = "تطبيق ويب (Flask/Django)"
    TPL_WEB_DESC = "مناسب لتطبيقات الويب"
    TPL_DATA_NAME = "تطبيق بيانات (Pandas/NumPy)"
    TPL_DATA_DESC = "مناسب لتطبيقات معالجة البيانات"
    TPL_GAME_NAME = "لعبة (Pygame)"
    TPL_GAME_DESC = "مناسب للألعاب"
    TPL_CUSTOM_NAME = "إعدادات مخصصة"
    TPL_CUSTOM_DESC = "تخصيص جميع الإعدادات يدوياً"


class En:
    """English strings."""

    # Window & tabs
    WINDOW_TITLE_FMT = "{name} v{version}"
    TAB_MAIN = "⚙️ Main Settings"
    TAB_ADVANCED = "🔧 Advanced"
    TAB_TEMPLATES = "📋 Templates"
    TAB_ABOUT = "ℹ️ About"

    # Header
    HEADER_TITLE = "🐍 Python to EXE Converter"
    HEADER_SUBTITLE = "Convert Python apps to executables with ease"

    # Main tab
    GROUP_SOURCE = "📄 Source File"
    SOURCE_PLACEHOLDER = "Choose a .py file to convert..."
    GROUP_OUTPUT = "📤 Output Settings"
    OUTPUT_NAME_LABEL = "Output file name:"
    OUTPUT_NAME_PLACEHOLDER = "File name without .exe"
    OUTPUT_DIR_LABEL = "Output directory:"
    OUTPUT_DIR_PLACEHOLDER = "Choose output directory..."
    ICON_LABEL = "Program icon:"
    ICON_PLACEHOLDER = "Optional - .ico file"

    GROUP_OPTIONS = "⚙️ Build Options"
    OPT_ONEFILE = "Single file (--onefile)"
    OPT_ONEFILE_TIP = "Bundle everything into one EXE"
    OPT_WINDOWED = "No console (--windowed)"
    OPT_WINDOWED_TIP = "Hide the console window"
    OPT_CLEAN = "Clean before build (--clean)"
    OPT_CLEAN_TIP = "Delete previous build files"
    OPT_NOCONSOLE = "--noconsole"
    OPT_NOCONSOLE_TIP = "Alias for --windowed"
    OPT_NOCONFIRM = "--noconfirm"
    OPT_NOCONFIRM_TIP = "Overwrite files without confirmation"
    OPT_STRIP = "--strip"
    OPT_STRIP_TIP = "Strip debug info (smaller output)"

    # Logs
    GROUP_LOG = "📋 Build Log"
    CLEAR_LOG = "🗑️ Clear Log"
    LOG_CHECKING_DEPS = "🔍 Checking dependencies..."
    LOG_PYTHON_FOUND = "✅ Python: {version}"
    LOG_PYTHON_MISSING = "❌ Python not found!"
    LOG_PYINSTALLER_FOUND = "✅ PyInstaller: {version}"
    LOG_PYINSTALLER_MISSING = "⚠️ PyInstaller is not installed - will be installed on convert"
    LOG_READY = "✅ Ready!\n"
    LOG_DETECTING_IMPORTS = "🔍 Detecting imports..."
    LOG_DETECT_RESULT = "✅ Detected {total} modules, added {added} new ones"
    LOG_DETECT_ERROR = "❌ Failed to detect imports: {error}"
    LOG_INSTALL_PYINSTALLER = "📦 Installing PyInstaller..."
    LOG_INSTALL_PYINSTALLER_OK = "✅ PyInstaller installed successfully!"
    LOG_TEMPLATE_APPLIED = "✅ Template applied: {name}"
    LOG_SETTINGS_SAVED = "✅ Settings saved: {path}"
    LOG_SETTINGS_LOADED = "✅ Settings loaded: {path}"
    LOG_CANCELLING = "⚠️ Cancelling operation..."

    # Conversion thread
    CONV_START = "⏱️ Starting build: {time}"
    CONV_COMMAND = "\n📋 Running command:\n{cmd}\n"
    CONV_SUCCESS = "✅ Build succeeded!"
    CONV_FAILED = "❌ Build failed!"
    CONV_ERROR = "\n❌ Error: {error}"
    CONV_CANCELLED = "Operation cancelled"
    CONV_FAILED_MSG = "Build failed - see log for details"

    # Advanced tab
    GROUP_EXTRA_FILES = "📁 Extra files (--add-data)"
    BTN_ADD_FILE = "➕ Add file"
    BTN_ADD_FOLDER = "📂 Add folder"
    BTN_REMOVE_SELECTED = "🗑️ Remove selected"
    GROUP_HIDDEN_IMPORTS = "📦 Hidden imports (--hidden-import)"
    BTN_ADD_IMPORT = "➕ Add module"
    BTN_AUTO_DETECT = "🔍 Auto-detect"
    GROUP_EXTRA_OPTS = "🔧 Extra options"
    OPT_LEVEL_LABEL = "Optimization level:"
    OPT_LEVELS = ["0 - None", "1 - Basic", "2 - Full"]
    UPX_LEVEL_LABEL = "UPX compression level:"
    UPX_LEVEL_TIP = "0 = no compression, 9 = maximum"
    UPX_USE = "Use UPX compression"
    UPX_USE_TIP = "Requires UPX installed"
    GROUP_EXTRA_ARGS = "💻 Extra PyInstaller arguments"
    EXTRA_ARGS_PLACEHOLDER = "Add any additional arguments here..."

    # Templates tab
    GROUP_TEMPLATES = "📋 Available Templates"
    TEMPLATES_HINT = "Choose a template to auto-apply suitable settings:"
    BTN_APPLY_TEMPLATE = "✅ Apply Template"
    GROUP_SAVE_LOAD = "💾 Save & Load Settings"
    SAVE_LOAD_HINT = "Save your current settings for later use:"
    BTN_SAVE_SETTINGS = "💾 Save Settings"
    BTN_LOAD_SETTINGS = "📂 Load Settings"

    # Dialog
    DIALOG_ADD_IMPORT_TITLE = "Add Hidden Import"
    DIALOG_ADD_IMPORT_LABEL = "Module name (Hidden Import):"
    DIALOG_ADD_IMPORT_PLACEHOLDER = "e.g.: PIL, requests, numpy..."

    # File dialogs
    DIALOG_CHOOSE_PY = "Choose Python file"
    DIALOG_FILTER_PY = "Python Files (*.py *.pyw);;All Files (*.*)"
    DIALOG_CHOOSE_OUT_DIR = "Choose output directory"
    DIALOG_CHOOSE_ICON = "Choose icon"
    DIALOG_FILTER_ICON = "Icon Files (*.ico);;All Files (*.*)"
    DIALOG_CHOOSE_EXTRA_FILE = "Choose extra file"
    DIALOG_FILTER_ALL = "All Files (*.*)"
    DIALOG_CHOOSE_EXTRA_FOLDER = "Choose extra folder"
    DIALOG_SAVE_SETTINGS = "Save Settings"
    DIALOG_LOAD_SETTINGS = "Load Settings"
    DIALOG_FILTER_JSON = "JSON Files (*.json)"

    # Log enhancements
    LOG_SEARCH_PLACEHOLDER = "🔍 Search log..."
    BTN_EXPORT_LOG = "💾 Export Log"
    DIALOG_EXPORT_LOG = "Export Log"
    DIALOG_FILTER_LOG = "Log Files (*.log *.txt);;All Files (*.*)"
    LOG_EXPORT_OK = "✅ Log exported: {path}"
    LOG_EXPORT_FAIL = "Failed to export log:\n{error}"
    LOG_DROPPED_SOURCE = "📁 Dropped source: {path}"
    LOG_DROPPED_ICON = "🎨 Dropped icon: {path}"
    LOG_DROPPED_EXTRA = "➕ Dropped extra: {path}"

    # Dry-run preview
    BTN_PREVIEW_CMD = "👁️ Preview Command"
    DIALOG_PREVIEW_TITLE = "PyInstaller Command Preview"
    DIALOG_PREVIEW_HINT = 'This is the command that will run when you click "Start build":'
    BTN_COPY_CMD = "📋 Copy"
    BTN_CLOSE = "Close"
    MSG_COPIED = "Command copied to clipboard"

    # Theme toggle
    BTN_TOGGLE_THEME = "🌓 Toggle Theme"
    THEME_DARK = "dark"
    THEME_LIGHT = "light"

    # Status / Progress
    PROGRESS_READY = "%p% - Ready to build"
    PROGRESS_CONVERTING = "%p% - Building..."
    PROGRESS_DONE = "✅ Build succeeded!"
    PROGRESS_FAILED = "❌ Build failed"
    PROGRESS_GROUP = "Build Status"

    # Buttons
    BTN_CONVERT = "🚀 Start Build"
    BTN_CANCEL = "❌ Cancel"
    BTN_OPEN_FOLDER = "📂 Open Output Folder"

    # Messages
    MSG_WARNING = "Warning"
    MSG_ERROR = "Error"
    MSG_SUCCESS = "Success"
    MSG_CONFIRM = "Confirm"
    ERR_NO_SOURCE = "Choose a source file first!"
    ERR_INSTALL_PYINSTALLER_FAIL = "Failed to install PyInstaller:\n{error}"
    ERR_OUTPUT_MISSING = "Output folder does not exist!"
    ERR_SAVE_FAIL = "Failed to save settings:\n{error}"
    ERR_LOAD_FAIL = "Failed to load settings:\n{error}"
    MSG_SAVED_OK = "Settings saved successfully!"
    MSG_LOADED_OK = "Settings loaded successfully!"
    MSG_TEMPLATE_OK_FMT = "Template applied: {name}"
    MSG_CLOSE_CONFIRM = "A build is in progress. Cancel and exit?"

    # Template description
    TEMPLATE_DESC_FMT = (
        "<b>Template:</b> {name}<br>"
        "<b>Description:</b> {desc}<br>"
        "<b>Windowed:</b> {windowed}<br>"
        "<b>Single file:</b> {onefile}<br>"
        "<b>Hidden imports:</b> {imports}"
    )
    YES = "Yes"
    NO = "No"
    NONE = "None"

    # About tab
    ABOUT_VERSION_FMT = "Version {version}"
    ABOUT_DESC = (
        "Professional tool for converting Python apps to .exe<br>"
        "using PyInstaller with an easy graphical interface"
    )
    ABOUT_DEVELOPER_LABEL = "👨‍💻 Developer"
    ABOUT_FEATURES_LABEL = "✨ Features"
    ABOUT_FEATURES = [
        "Convert any Python file to EXE",
        "Add a custom icon",
        "Bundle extra files and resources",
        "Templates for common app types",
        "Automatic dependency detection",
        "Save and load settings",
        "Detailed build log",
    ]

    # Language selector
    LANGUAGE_LABEL = "🌐 Language:"
    LANGUAGE_NATIVE = "English"
    MSG_RESTART_REQUIRED = "Please restart the app to apply the new language."

    # Template names & descriptions
    TPL_GUI_NAME = "GUI app (PyQt5/Tkinter)"
    TPL_GUI_DESC = "Suitable for graphical applications"
    TPL_CONSOLE_NAME = "Console app"
    TPL_CONSOLE_DESC = "Suitable for command-line tools"
    TPL_WEB_NAME = "Web app (Flask/Django)"
    TPL_WEB_DESC = "Suitable for web applications"
    TPL_DATA_NAME = "Data app (Pandas/NumPy)"
    TPL_DATA_DESC = "Suitable for data-processing apps"
    TPL_GAME_NAME = "Game (Pygame)"
    TPL_GAME_DESC = "Suitable for games"
    TPL_CUSTOM_NAME = "Custom settings"
    TPL_CUSTOM_DESC = "Fully manual configuration"


# ──────────────────────────────────────────────────────────────────────────
# Locale registry and proxy
# ──────────────────────────────────────────────────────────────────────────

LOCALES = {"ar": Ar, "en": En}

# Native language names for UI display.
LOCALE_NATIVE_NAMES = {"ar": "العربية", "en": "English"}

# Layout direction per locale ("rtl" or "ltr").
LOCALE_LAYOUT = {"ar": "rtl", "en": "ltr"}

DEFAULT_LOCALE = "ar"


class _LocaleProxy:
    """Live proxy that forwards attribute access to the active locale class."""

    def __init__(self, klass):
        object.__setattr__(self, "_current", klass)

    def __getattr__(self, name):
        return getattr(self._current, name)


S = _LocaleProxy(LOCALES[DEFAULT_LOCALE])


def set_locale(name: str) -> bool:
    """Switch the active locale. Returns True if applied, False if unknown."""
    if name not in LOCALES:
        return False
    object.__setattr__(S, "_current", LOCALES[name])
    return True


def current_locale() -> str:
    """Return the name of the currently active locale."""
    for name, klass in LOCALES.items():
        if S._current is klass:
            return name
    return DEFAULT_LOCALE


def available_locales() -> dict:
    """Mapping of locale code → native name for UI selectors."""
    return dict(LOCALE_NATIVE_NAMES)
