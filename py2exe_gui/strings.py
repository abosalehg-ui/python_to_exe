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

    # Phase 4: Version info editor
    TAB_VERSION_INFO = "📝 معلومات الإصدار"
    GROUP_VERSION_INFO = "📝 بيانات ملف EXE (Windows)"
    VERSION_INFO_HINT = "اترك الحقول فارغة لتجاهلها. تُضمَّن في خصائص الـ EXE الناتج."
    VI_COMPANY_NAME = "اسم الشركة:"
    VI_FILE_DESCRIPTION = "وصف الملف:"
    VI_FILE_VERSION = "إصدار الملف (1.0.0.0):"
    VI_INTERNAL_NAME = "الاسم الداخلي:"
    VI_LEGAL_COPYRIGHT = "حقوق النشر:"
    VI_ORIGINAL_FILENAME = "اسم الملف الأصلي:"
    VI_PRODUCT_NAME = "اسم المنتج:"
    VI_PRODUCT_VERSION = "إصدار المنتج (1.0.0.0):"
    VI_PLACEHOLDER_VERSION = "مثل: 1.0.0.0"

    # Phase 4: requirements.txt import
    BTN_IMPORT_REQUIREMENTS = "📥 استيراد من requirements.txt"
    DIALOG_CHOOSE_REQS = "اختر ملف requirements.txt"
    DIALOG_FILTER_REQS = "Requirements (*.txt);;All Files (*.*)"
    LOG_REQS_IMPORTED = "✅ تم استيراد {total} حزمة من requirements.txt، أُضيفت {added} جديدة"
    LOG_REQS_HINT = (
        "⚠️ تنبيه: أسماء الحزم قد تختلف عن أسماء الاستيراد "
        "(مثل Pillow → PIL). راجع القائمة."
    )
    LOG_REQS_ERROR = "❌ خطأ في قراءة requirements.txt: {error}"

    # Phase 4: Build history
    TAB_HISTORY = "🕓 سجل البناءات"
    GROUP_HISTORY = "🕓 آخر البناءات"
    HISTORY_EMPTY = "لا توجد بناءات سابقة."
    BTN_RESTORE_BUILD = "♻️ استعادة الإعدادات"
    BTN_CLEAR_HISTORY = "🗑️ مسح السجل"
    HISTORY_CLEARED = "✅ تم مسح سجل البناءات"
    LOG_RESTORED = "✅ تمت استعادة إعدادات البناء من {time}"

    # Phase 5: Deployment tab
    TAB_DEPLOY = "🚀 النشر"

    # Splash
    GROUP_SPLASH = "🖼️ شاشة البداية (Splash)"
    SPLASH_LABEL = "صورة شاشة البداية:"
    SPLASH_PLACEHOLDER = "اختياري - PNG / JPG"
    DIALOG_CHOOSE_SPLASH = "اختر صورة شاشة البداية"
    DIALOG_FILTER_IMAGE = "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"

    # Manifest
    GROUP_MANIFEST = "📜 Windows Manifest"
    MANIFEST_HINT = "يُولَّد ملف XML ويُمرَّر عبر --manifest عند البناء."
    MANIFEST_ENABLE = "تفعيل توليد Manifest"
    MANIFEST_DPI = "DPI Aware (PerMonitorV2)"
    MANIFEST_ADMIN = "يتطلب صلاحيات المدير (requireAdministrator)"
    MANIFEST_OS_LABEL = "أنظمة Windows المدعومة:"

    # Signing
    GROUP_SIGNING = "🔐 التوقيع الرقمي"
    SIGNING_HINT = "بعد إكمال البناء، يُوقَّع الـ EXE باستخدام signtool.exe (Windows)."
    SIGNING_ENABLE = "تفعيل التوقيع الرقمي"
    SIGNING_CERT_LABEL = "ملف الشهادة (.pfx):"
    SIGNING_CERT_PLACEHOLDER = "اختر ملف .pfx"
    SIGNING_PASSWORD_LABEL = "كلمة المرور:"
    SIGNING_PASSWORD_PLACEHOLDER = "كلمة مرور الشهادة"
    SIGNING_TIMESTAMP_LABEL = "خادم Timestamp:"
    SIGNING_DESC_LABEL = "وصف للتوقيع:"
    SIGNING_DESC_PLACEHOLDER = "اختياري - مثل اسم المنتج"
    DIALOG_CHOOSE_CERT = "اختر ملف الشهادة"
    DIALOG_FILTER_CERT = "Certificate Files (*.pfx *.p12);;All Files (*.*)"
    LOG_SIGNING_START = "🔐 جاري التوقيع الرقمي..."
    LOG_SIGNING_OK = "✅ تم التوقيع الرقمي بنجاح"
    LOG_SIGNING_FAIL = "❌ فشل التوقيع الرقمي: {error}"
    LOG_SIGNING_SKIPPED = "⏭️ تم تخطي التوقيع: {reason}"

    # Smoke test
    GROUP_SMOKE = "🧪 اختبار ما بعد البناء"
    SMOKE_ENABLE = "تشغيل الـ EXE الناتج تلقائياً للتحقق"
    SMOKE_TIMEOUT_LABEL = "مدة الانتظار (ثواني):"
    LOG_SMOKE_START = "🧪 جاري اختبار الـ EXE الناتج..."
    LOG_SMOKE_OK = "✅ نجاح الاختبار: EXE يعمل بشكل صحيح"
    LOG_SMOKE_FAIL = "❌ فشل الاختبار: {error}"
    LOG_SMOKE_NOT_FOUND = "⚠️ لم يُعثَر على الـ EXE الناتج للاختبار"

    # OS list labels (kept short - no version prefix needed)
    OS_VISTA = "Vista"
    OS_7 = "Windows 7"
    OS_8 = "Windows 8"
    OS_81 = "Windows 8.1"
    OS_10 = "Windows 10"
    OS_11 = "Windows 11"

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
    TPL_FASTAPI_NAME = "FastAPI (واجهة برمجية)"
    TPL_FASTAPI_DESC = "تطبيق REST API بـ FastAPI/Uvicorn"
    TPL_STREAMLIT_NAME = "Streamlit (لوحة بيانات)"
    TPL_STREAMLIT_DESC = "تطبيق Streamlit لتحليل البيانات التفاعلي"
    TPL_KIVY_NAME = "Kivy (تطبيق متعدد المنصات)"
    TPL_KIVY_DESC = "تطبيق Kivy للهاتف وسطح المكتب"
    TPL_DISCORD_NAME = "بوت Discord (discord.py)"
    TPL_DISCORD_DESC = "بوت Discord باستخدام discord.py"
    TPL_CLICK_NAME = "أداة CLI (Click)"
    TPL_CLICK_DESC = "أداة سطر أوامر باستخدام مكتبة Click"
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

    # Phase 4: Version info editor
    TAB_VERSION_INFO = "📝 Version Info"
    GROUP_VERSION_INFO = "📝 EXE Metadata (Windows)"
    VERSION_INFO_HINT = "Leave fields blank to skip. Embedded into the resulting EXE's properties."
    VI_COMPANY_NAME = "Company name:"
    VI_FILE_DESCRIPTION = "File description:"
    VI_FILE_VERSION = "File version (1.0.0.0):"
    VI_INTERNAL_NAME = "Internal name:"
    VI_LEGAL_COPYRIGHT = "Legal copyright:"
    VI_ORIGINAL_FILENAME = "Original filename:"
    VI_PRODUCT_NAME = "Product name:"
    VI_PRODUCT_VERSION = "Product version (1.0.0.0):"
    VI_PLACEHOLDER_VERSION = "e.g.: 1.0.0.0"

    # Phase 4: requirements.txt import
    BTN_IMPORT_REQUIREMENTS = "📥 Import from requirements.txt"
    DIALOG_CHOOSE_REQS = "Choose requirements.txt"
    DIALOG_FILTER_REQS = "Requirements (*.txt);;All Files (*.*)"
    LOG_REQS_IMPORTED = "✅ Imported {total} packages from requirements.txt, added {added} new"
    LOG_REQS_HINT = (
        "⚠️ Note: package names can differ from import names "
        "(e.g. Pillow → PIL). Review the list."
    )
    LOG_REQS_ERROR = "❌ Failed to read requirements.txt: {error}"

    # Phase 4: Build history
    TAB_HISTORY = "🕓 Build History"
    GROUP_HISTORY = "🕓 Recent Builds"
    HISTORY_EMPTY = "No previous builds yet."
    BTN_RESTORE_BUILD = "♻️ Restore Settings"
    BTN_CLEAR_HISTORY = "🗑️ Clear History"
    HISTORY_CLEARED = "✅ Build history cleared"
    LOG_RESTORED = "✅ Build settings restored from {time}"

    # Phase 5: Deployment tab
    TAB_DEPLOY = "🚀 Deploy"

    GROUP_SPLASH = "🖼️ Splash Screen"
    SPLASH_LABEL = "Splash image:"
    SPLASH_PLACEHOLDER = "Optional - PNG / JPG"
    DIALOG_CHOOSE_SPLASH = "Choose splash image"
    DIALOG_FILTER_IMAGE = "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"

    GROUP_MANIFEST = "📜 Windows Manifest"
    MANIFEST_HINT = "Generates an XML manifest passed via --manifest at build time."
    MANIFEST_ENABLE = "Generate manifest"
    MANIFEST_DPI = "DPI Aware (PerMonitorV2)"
    MANIFEST_ADMIN = "Require administrator (requireAdministrator)"
    MANIFEST_OS_LABEL = "Supported Windows versions:"

    GROUP_SIGNING = "🔐 Code Signing"
    SIGNING_HINT = "After build, signs the EXE using signtool.exe (Windows-only)."
    SIGNING_ENABLE = "Enable code signing"
    SIGNING_CERT_LABEL = "Certificate file (.pfx):"
    SIGNING_CERT_PLACEHOLDER = "Choose .pfx file"
    SIGNING_PASSWORD_LABEL = "Password:"
    SIGNING_PASSWORD_PLACEHOLDER = "Certificate password"
    SIGNING_TIMESTAMP_LABEL = "Timestamp URL:"
    SIGNING_DESC_LABEL = "Signature description:"
    SIGNING_DESC_PLACEHOLDER = "Optional - e.g. product name"
    DIALOG_CHOOSE_CERT = "Choose certificate"
    DIALOG_FILTER_CERT = "Certificate Files (*.pfx *.p12);;All Files (*.*)"
    LOG_SIGNING_START = "🔐 Signing executable..."
    LOG_SIGNING_OK = "✅ Code signing succeeded"
    LOG_SIGNING_FAIL = "❌ Code signing failed: {error}"
    LOG_SIGNING_SKIPPED = "⏭️ Signing skipped: {reason}"

    GROUP_SMOKE = "🧪 Post-build Smoke Test"
    SMOKE_ENABLE = "Run built EXE automatically to verify it starts"
    SMOKE_TIMEOUT_LABEL = "Timeout (seconds):"
    LOG_SMOKE_START = "🧪 Testing built executable..."
    LOG_SMOKE_OK = "✅ Smoke test passed: EXE runs"
    LOG_SMOKE_FAIL = "❌ Smoke test failed: {error}"
    LOG_SMOKE_NOT_FOUND = "⚠️ Built EXE not found for smoke test"

    OS_VISTA = "Vista"
    OS_7 = "Windows 7"
    OS_8 = "Windows 8"
    OS_81 = "Windows 8.1"
    OS_10 = "Windows 10"
    OS_11 = "Windows 11"

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
    TPL_FASTAPI_NAME = "FastAPI (REST API)"
    TPL_FASTAPI_DESC = "REST API service with FastAPI/Uvicorn"
    TPL_STREAMLIT_NAME = "Streamlit (Data App)"
    TPL_STREAMLIT_DESC = "Streamlit app for interactive data analysis"
    TPL_KIVY_NAME = "Kivy (Cross-platform)"
    TPL_KIVY_DESC = "Kivy app for mobile and desktop"
    TPL_DISCORD_NAME = "Discord Bot (discord.py)"
    TPL_DISCORD_DESC = "Discord bot using discord.py"
    TPL_CLICK_NAME = "CLI tool (Click)"
    TPL_CLICK_DESC = "Command-line tool built with the Click library"
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
