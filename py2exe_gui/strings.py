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


# Default locale alias - swap this to switch languages in Phase 3.
S = Ar
