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
    UPX_DIR_LABEL = "مجلد UPX:"
    UPX_DIR_PLACEHOLDER = "اختياري - مجلد يحتوي upx.exe (الافتراضي: البحث في PATH)"
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
    MSG_INFO_TITLE = "معلومة"
    ERR_NO_SOURCE = "اختر ملف المصدر أولاً!"
    ERR_INSTALL_PYINSTALLER_FAIL = "فشل تثبيت PyInstaller:\n{error}"
    ERR_OUTPUT_MISSING = "مجلد الإخراج غير موجود!"
    ERR_SAVE_FAIL = "فشل حفظ الإعدادات:\n{error}"
    ERR_LOAD_FAIL = "فشل تحميل الإعدادات:\n{error}"
    MSG_SAVED_OK = "تم حفظ الإعدادات بنجاح!"
    MSG_LOADED_OK = "تم تحميل الإعدادات بنجاح!"
    MSG_TEMPLATE_OK_FMT = "تم تطبيق قالب: {name}"
    MSG_CLOSE_CONFIRM = "هناك عملية تحويل جارية. هل تريد الإلغاء والخروج؟"

    # ── Phase 8: تأكيدات وأمان ──────────────────────────────────────────
    MSG_INSTALL_PYINSTALLER_CONFIRM = (
        "PyInstaller غير مثبّت. هل تسمح بتثبيته الآن من PyPI؟\n\n"
        "الأمر الذي سيُنفَّذ:\n{cmd}\n\n"
        "سيتم تنزيل حزم من الإنترنت."
    )
    LOG_INSTALL_PYINSTALLER_DECLINED = "⚠️ تم رفض تثبيت PyInstaller — أُلغي البناء"
    MSG_DANGEROUS_ARGS_CONFIRM = (
        "⚠️ ملف الإعدادات هذا يحتوي على أوامر تُشغِّل كوداً أثناء البناء:\n\n"
        "{flags}\n\n"
        "الأوامر الكاملة:\n{args}\n\n"
        "أمر مثل ‎--runtime-hook‎ يحقن كوداً داخل كل ملف EXE تنتجه. "
        "لا تقبل إلا إذا كنت تثق بمصدر هذا الملف.\n\n"
        "هل تريد المتابعة؟"
    )
    LOG_SETTINGS_REJECTED = "⚠️ تم رفض ملف الإعدادات: {path}"
    MSG_CLEAR_HISTORY_CONFIRM = (
        "سيتم حذف {count} عملية بناء من السجل نهائياً.\n"
        "لا يمكن التراجع عن هذا الإجراء.\n\nهل تريد المتابعة؟"
    )
    LOG_SETTINGS_SAVE_FAIL = "⚠️ فشل حفظ الإعدادات: {error}"
    LOG_HISTORY_SAVE_FAIL = "⚠️ فشل حفظ السجل: {error}"
    SIGNING_USE_STORE = "استخدام شهادة من مخزن شهادات Windows"
    SIGNING_USE_STORE_TIP = (
        "أكثر أماناً: لا تُمرَّر كلمة المرور في سطر الأوامر حيث يمكن "
        "لأي عملية أخرى قراءتها"
    )
    SIGNING_SUBJECT_LABEL = "اسم موضوع الشهادة:"
    SIGNING_SUBJECT_PLACEHOLDER = "مثال: Acme Ltd"


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
    ABOUT_DESC_PLAIN = (
        "أداة احترافية لتحويل تطبيقات بايثون إلى ملفات تنفيذية EXE "
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

    # ── Phase 7: مثبّت Inno Setup ──────────────────────────────────────
    TAB_INSTALLER = "📦 المثبِّت"
    GROUP_INSTALLER = "📦 إنشاء مثبّت (Inno Setup)"
    INSTALLER_HINT = (
        "أنشئ ملف Setup.exe احترافياً بعد البناء مباشرةً. "
        "يتطلب تثبيت Inno Setup 6 على الجهاز."
    )
    INSTALLER_ENABLE = "إنشاء المثبّت تلقائياً بعد نجاح البناء"

    GROUP_INSTALLER_IDENTITY = "🪪 هوية التطبيق"
    INST_APP_NAME_LABEL = "اسم التطبيق:"
    INST_APP_NAME_PLACEHOLDER = "الاسم الظاهر في قائمة ابدأ ولوحة التحكم"
    INST_VERSION_LABEL = "الإصدار:"
    INST_VERSION_PLACEHOLDER = "1.0.0"
    INST_PUBLISHER_LABEL = "الناشر:"
    INST_PUBLISHER_PLACEHOLDER = "اسم الشركة أو المطوّر"
    INST_URL_LABEL = "الموقع الإلكتروني:"
    INST_URL_PLACEHOLDER = "https://example.com"
    INST_APPID_LABEL = "AppId (GUID):"
    INST_APPID_PLACEHOLDER = "يُشتق تلقائياً من الاسم + الناشر"
    INST_APPID_TIP = (
        "معرّف ثابت يجعل الإصدارات الجديدة تُحدّث التثبيت السابق بدل تكراره"
    )

    GROUP_INSTALLER_OUTPUT = "📤 مخرجات المثبّت"
    INST_OUT_DIR_LABEL = "مجلد الإخراج:"
    INST_OUT_DIR_PLACEHOLDER = "الافتراضي: بجانب ملف EXE الناتج"
    INST_OUT_NAME_LABEL = "اسم ملف Setup:"
    INST_OUT_NAME_PLACEHOLDER = "الافتراضي: <الاسم>-<الإصدار>-setup"
    INST_LICENSE_LABEL = "ملف الترخيص:"
    INST_LICENSE_PLACEHOLDER = "اختياري - يظهر في معالج التثبيت (.txt/.rtf)"
    INST_README_LABEL = "ملف README:"
    INST_README_PLACEHOLDER = "اختياري - يظهر بعد انتهاء التثبيت"
    INST_SETUP_ICON_LABEL = "أيقونة المثبّت:"
    INST_SETUP_ICON_PLACEHOLDER = "اختياري - ملف .ico لواجهة Setup.exe"

    GROUP_INSTALLER_OPTIONS = "⚙️ خيارات التثبيت"
    INST_PRIVILEGES_LABEL = "صلاحيات التثبيت:"
    INST_PRIV_ADMIN = "لكل المستخدمين (يتطلب مدير)"
    INST_PRIV_LOWEST = "للمستخدم الحالي فقط (بدون مدير)"
    INST_ARCH_LABEL = "المعمارية:"
    INST_ARCH_X64 = "64-bit فقط"
    INST_ARCH_X86 = "32-bit"
    INST_ARCH_ANY = "أي معمارية"
    INST_COMPRESSION_LABEL = "الضغط:"
    INST_LANGUAGES_LABEL = "لغات المثبّت:"
    INST_ARABIC_ISL_LABEL = "ملف Arabic.isl:"
    INST_ARABIC_ISL_PLACEHOLDER = "مطلوب لدعم العربية (ترجمة غير رسمية)"
    INST_ARABIC_ISL_TIP = (
        "Inno Setup لا يتضمّن العربية افتراضياً — نزّل Arabic.isl "
        "من ترجمات المجتمع وحدّد مساره هنا"
    )
    INST_DESKTOP_ICON = "إنشاء اختصار على سطح المكتب"
    INST_LAUNCH_AFTER = "تشغيل التطبيق بعد التثبيت"
    INST_ALLOW_DIR_CHANGE = "السماح بتغيير مجلد التثبيت"
    INST_UNINSTALL_ICON = "إضافة اختصار لإلغاء التثبيت"
    INST_SIGN_INSTALLER = "توقيع ملف Setup.exe رقمياً"
    INST_SIGN_TIP = "يستخدم نفس إعدادات التوقيع في تبويب النشر"
    INST_ASSOC_LABEL = "ربط امتداد ملفات:"
    INST_ASSOC_PLACEHOLDER = "اختياري - مثال: .myapp"

    GROUP_INSTALLER_TOOLCHAIN = "🔧 مترجم Inno Setup"
    INST_ISCC_LABEL = "مسار ISCC.exe:"
    INST_ISCC_PLACEHOLDER = "الافتراضي: البحث التلقائي في PATH ومجلدات التثبيت"
    BTN_DETECT_ISCC = "🔍 كشف تلقائي"
    BTN_GENERATE_ISS = "📝 توليد ملف .iss فقط"
    BTN_BUILD_INSTALLER = "📦 بناء المثبّت الآن"

    # رسائل المثبّت
    LOG_ISCC_FOUND = "✅ تم العثور على Inno Setup: {path}"
    LOG_ISCC_MISSING = (
        "⚠️ لم يتم العثور على ISCC.exe — ثبّت Inno Setup 6 أو حدّد المسار يدوياً"
    )
    LOG_INSTALLER_START = "📦 جاري إنشاء المثبّت..."
    LOG_INSTALLER_OK = "✅ تم إنشاء المثبّت: {path}"
    LOG_INSTALLER_FAIL = "❌ فشل إنشاء المثبّت: {error}"
    LOG_INSTALLER_SKIPPED = "⏭️ تم تخطي إنشاء المثبّت: {reason}"
    LOG_ISS_WRITTEN = "✅ تم توليد ملف Inno Setup: {path}"
    LOG_ISS_FAIL = "❌ فشل توليد ملف .iss: {error}"
    LOG_INSTALLER_LANG_WARN = "⚠️ لغات غير مدعومة تم تجاهلها: {langs}"
    ERR_INSTALLER_NO_EXE = "لم يتم العثور على ملف EXE ناتج — نفّذ البناء أولاً"
    ERR_INSTALLER_NO_NAME = "أدخل اسم التطبيق في تبويب المثبّت أولاً"
    DIALOG_SAVE_ISS = "حفظ ملف Inno Setup"
    DIALOG_FILTER_ISS = "Inno Setup Scripts (*.iss);;All Files (*.*)"
    DIALOG_CHOOSE_ISCC = "اختر ISCC.exe"
    DIALOG_FILTER_EXE = "Executables (*.exe);;All Files (*.*)"
    DIALOG_CHOOSE_LICENSE = "اختر ملف الترخيص"
    DIALOG_FILTER_TEXT = "Text Files (*.txt *.rtf);;All Files (*.*)"
    DIALOG_CHOOSE_ISL = "اختر ملف Arabic.isl"
    DIALOG_FILTER_ISL = "Inno Setup Language Files (*.isl);;All Files (*.*)"
    MSG_INSTALLER_OK = "تم إنشاء المثبّت بنجاح:\n{path}"

    # ── Phase 9: simplified mode ──
    WELCOME_TITLE = "أهلاً بك 👋"
    WELCOME_BODY = (
        "يمكنك استخدام البرنامج بوضعين:\n\n"
        "• الوضع المبسّط: ثلاث خطوات فقط — اختر الملف، اختر النوع، ابنِ.\n"
        "• الوضع المتقدم: كل التبويبات (النشر، المثبّت، معلومات الإصدار...).\n\n"
        "يمكنك التبديل بينهما في أي وقت من زر الوضع أسفل النافذة."
    )
    WELCOME_CHOOSE_SIMPLE = "ابدأ بالوضع المبسّط"
    WELCOME_CHOOSE_ADVANCED = "ابدأ بالوضع المتقدم"
    BTN_MODE_TO_ADVANCED = "🔧 الوضع المتقدم"
    BTN_MODE_TO_SIMPLE = "🌱 الوضع المبسّط"
    MODE_SIMPLE_TIP = "إظهار التبويبات الأساسية فقط"
    MODE_ADVANCED_TIP = "إظهار كل التبويبات"
    LOG_MODE_SIMPLE = "🌱 تم التبديل إلى الوضع المبسّط"
    LOG_MODE_ADVANCED = "🔧 تم التبديل إلى الوضع المتقدم"

    # ── Phase 9: platform support ──
    # Arabic uses its own comma; kept as a string so joins stay locale-correct.
    LIST_SEPARATOR = "، "
    PLATFORM_WINDOWS_ONLY_FMT = (
        "⚠️ أنت تشغّل البرنامج على {platform}. الميزات التالية تعمل عند "
        "البناء على Windows فقط ولن يكون لها أثر هنا: {features}"
    )
    FEATURE_CODE_SIGNING = "التوقيع الرقمي"
    FEATURE_MANIFEST = "Windows Manifest"
    FEATURE_VERSION_INFO = "معلومات الإصدار"
    FEATURE_INSTALLER = "مثبّت Inno Setup"

    # ── Phase 9: themes ──
    THEME_SELECT_LABEL = "السمة:"
    THEME_LABEL_AUTO = "🖥️ تلقائي (حسب النظام)"
    THEME_LABEL_DARK = "🌙 داكنة"
    THEME_LABEL_LIGHT = "☀️ نهارية"
    THEME_LABEL_NORD = "❄️ Nord"
    THEME_LABEL_HIGH_CONTRAST = "🔲 تباين عالٍ"
    LOG_THEME_CHANGED = "🎨 تم تغيير السمة: {theme}"

    # ── Phase 9: font zoom ──
    LOG_ZOOM_FMT = "🔍 حجم الخط: {percent}%"
    ZOOM_IN_TIP = "تكبير الخط (Ctrl++)"
    ZOOM_OUT_TIP = "تصغير الخط (Ctrl+-)"
    ZOOM_RESET_TIP = "إعادة حجم الخط (Ctrl+0)"

    # ── Phase 9: system tray ──
    TRAY_TOOLTIP = "Python to EXE Converter"
    TRAY_SHOW = "إظهار النافذة"
    TRAY_CANCEL = "إلغاء البناء"
    TRAY_QUIT = "خروج"
    TRAY_BUILD_OK_TITLE = "اكتمل البناء ✅"
    TRAY_BUILD_OK_BODY = "تم إنشاء {name} بنجاح"
    TRAY_BUILD_FAIL_TITLE = "فشل البناء ❌"
    TRAY_BUILD_FAIL_BODY = "راجع السجل لمعرفة السبب"

    # ── Phase 9: real build stages ──
    STAGE_STARTING = "التحضير"
    STAGE_ANALYZING = "تحليل الاستيرادات"
    STAGE_HOOKS = "معالجة الـ hooks"
    STAGE_DEPENDENCIES = "جمع المكتبات"
    STAGE_PYZ = "بناء أرشيف PYZ"
    STAGE_PKG = "تجميع الحزمة"
    STAGE_EXE = "بناء الملف التنفيذي"
    STAGE_COLLECT = "نسخ الملفات"
    PROGRESS_STAGE_FMT = "{stage} — %p%"

    # ── Phase 9: icon preview ──
    ICON_PREVIEW_LABEL = "معاينة:"
    ICON_PREVIEW_NONE = "لا توجد أيقونة"
    ICON_PREVIEW_INVALID = "⚠️ تعذّرت قراءة الأيقونة — تأكد أنه ملف .ico صالح"

    # ── Phase 9: log filters ──
    LOG_FILTER_LABEL = "تصفية:"
    LOG_FILTER_ALL = "الكل"
    LOG_FILTER_ERRORS = "❌ أخطاء"
    LOG_FILTER_WARNINGS = "⚠️ تحذيرات"
    LOG_FILTER_SUCCESS = "✅ نجاح"
    LOG_FILTER_EMPTY = "لا توجد أسطر مطابقة لهذه التصفية."

    # ── Phase 10: batch conversion ──
    TAB_BATCH = "📚 تحويل دفعي"
    GROUP_BATCH_FILES = "📚 قائمة الملفات"
    BATCH_HINT = (
        "حوّل عدة ملفات بنفس الإعدادات. تُنفَّذ واحداً تلو الآخر — "
        "لأن PyInstaller يكتب في نفس مجلدي build/ و dist/."
    )
    BTN_BATCH_ADD = "➕ إضافة ملفات"
    BTN_BATCH_REMOVE = "🗑️ حذف المحدد"
    BTN_BATCH_CLEAR = "🧹 تفريغ القائمة"
    BTN_BATCH_START = "🚀 بدء التحويل الدفعي"
    BTN_BATCH_CANCEL = "⏹️ إلغاء"
    GROUP_BATCH_RESULT = "📊 النتيجة"
    BATCH_EMPTY = "القائمة فارغة — أضف ملفات .py للبدء."
    BATCH_SUMMARY_FMT = (
        "الإجمالي: {total} | ✅ نجح: {succeeded} | ❌ فشل: {failed} | "
        "⊘ ملغى: {cancelled} | المدة: {duration} ثانية"
    )
    BATCH_FAILURES_FMT = "الملفات الفاشلة: {names}"
    LOG_BATCH_START = "📚 بدء التحويل الدفعي لـ {count} ملف..."
    LOG_BATCH_JOB_START = "▶ ({index}/{total}) {name}"
    LOG_BATCH_JOB_OK = "✅ ({index}/{total}) {name} — تم في {duration} ثانية"
    LOG_BATCH_JOB_FAIL = "❌ ({index}/{total}) {name} — فشل"
    LOG_BATCH_DONE = "📚 انتهى التحويل الدفعي."
    LOG_BATCH_CANCELLED = "⚠️ تم إلغاء التحويل الدفعي."
    ERR_BATCH_NO_FILES = "أضف ملفاً واحداً على الأقل إلى قائمة التحويل الدفعي"
    ERR_BATCH_BUSY = "هناك عملية بناء قيد التنفيذ بالفعل"
    MSG_BATCH_CANCEL_CONFIRM = "إلغاء التحويل الدفعي؟ الملفات المتبقية لن تُبنى."
    DIALOG_CHOOSE_BATCH_FILES = "اختر ملفات .py للتحويل الدفعي"

    # ── Phase 10: update check ──
    BTN_CHECK_UPDATES = "🔄 التحقق من التحديثات"
    UPDATE_CHECK_ON_START = "التحقق من التحديثات عند بدء التشغيل"
    UPDATE_AVAILABLE_FMT = (
        "يتوفر إصدار جديد: {version} (الحالي {current}).\n\n"
        "لن يُنزَّل شيء تلقائياً — افتح صفحة الإصدارات للاطلاع والتنزيل يدوياً."
    )
    BTN_OPEN_RELEASES = "فتح صفحة الإصدارات"
    UPDATE_NONE = "أنت على أحدث إصدار ✅"
    LOG_UPDATE_CHECKING = "🔄 جاري التحقق من وجود تحديث..."
    LOG_UPDATE_AVAILABLE = "🎉 يتوفر إصدار جديد: {version} — {url}"
    LOG_UPDATE_NONE = "✅ لا يوجد تحديث — أنت على أحدث إصدار ({version})"
    LOG_UPDATE_FAILED = "⚠️ تعذّر التحقق من التحديثات (تحقق من الاتصال)"

    # ── Phase 10: presets ──
    GROUP_PRESETS = "⭐ الإعدادات المحفوظة (Presets)"
    PRESETS_HINT = (
        "احفظ الإعدادات الحالية باسم لاستعادتها لاحقاً بنقرة واحدة، "
        "بدل البحث عن ملف JSON في كل مرة."
    )
    PRESET_NONE = "— لا توجد إعدادات محفوظة —"
    BTN_PRESET_SAVE = "💾 حفظ باسم"
    BTN_PRESET_APPLY = "📥 تطبيق"
    BTN_PRESET_DELETE = "🗑️ حذف"
    BTN_PRESET_EXPORT = "📤 تصدير الكل"
    BTN_PRESET_IMPORT = "📥 استيراد"
    PRESET_NAME_PROMPT = "اسم الإعداد:"
    PRESET_SAVED_FMT = "⭐ تم حفظ الإعداد: {name}"
    PRESET_APPLIED_FMT = "📥 تم تطبيق الإعداد: {name}"
    PRESET_DELETED_FMT = "🗑️ تم حذف الإعداد: {name}"
    PRESET_OVERWRITE_CONFIRM = "يوجد إعداد بنفس الاسم «{name}». هل تريد استبداله؟"
    MSG_PRESET_DELETE_CONFIRM = "حذف الإعداد «{name}»؟ لا يمكن التراجع."
    ERR_PRESET_NAME = "أدخل اسماً صالحاً للإعداد"
    ERR_PRESET_SAVE_FAIL = "تعذّر حفظ الإعداد: {error}"
    LOG_PRESET_IMPORTED_FMT = "📥 تم استيراد {count} إعداد"
    LOG_PRESET_IMPORT_NONE = "لم يُستورد أي إعداد جديد (الأسماء موجودة مسبقاً)"
    DIALOG_EXPORT_PRESETS = "تصدير الإعدادات المحفوظة"
    DIALOG_IMPORT_PRESETS = "استيراد إعدادات محفوظة"


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
    UPX_DIR_LABEL = "UPX directory:"
    UPX_DIR_PLACEHOLDER = "Optional - folder containing upx.exe (default: search PATH)"
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
    MSG_INFO_TITLE = "Information"
    ERR_NO_SOURCE = "Choose a source file first!"
    ERR_INSTALL_PYINSTALLER_FAIL = "Failed to install PyInstaller:\n{error}"
    ERR_OUTPUT_MISSING = "Output folder does not exist!"
    ERR_SAVE_FAIL = "Failed to save settings:\n{error}"
    ERR_LOAD_FAIL = "Failed to load settings:\n{error}"
    MSG_SAVED_OK = "Settings saved successfully!"
    MSG_LOADED_OK = "Settings loaded successfully!"
    MSG_TEMPLATE_OK_FMT = "Template applied: {name}"
    MSG_CLOSE_CONFIRM = "A build is in progress. Cancel and exit?"

    # ── Phase 8: confirmations and security ────────────────────────────
    MSG_INSTALL_PYINSTALLER_CONFIRM = (
        "PyInstaller is not installed. Install it now from PyPI?\n\n"
        "Command to run:\n{cmd}\n\n"
        "This downloads packages from the internet."
    )
    LOG_INSTALL_PYINSTALLER_DECLINED = "⚠️ PyInstaller install declined — build cancelled"
    MSG_DANGEROUS_ARGS_CONFIRM = (
        "⚠️ This settings file contains arguments that execute code during the build:\n\n"
        "{flags}\n\n"
        "Full arguments:\n{args}\n\n"
        "A flag such as --runtime-hook injects code into every EXE you produce. "
        "Only accept this if you trust where the file came from.\n\n"
        "Continue?"
    )
    LOG_SETTINGS_REJECTED = "⚠️ Settings file rejected: {path}"
    MSG_CLEAR_HISTORY_CONFIRM = (
        "This permanently deletes {count} build(s) from the history.\n"
        "The action cannot be undone.\n\nContinue?"
    )
    LOG_SETTINGS_SAVE_FAIL = "⚠️ Failed to save settings: {error}"
    LOG_HISTORY_SAVE_FAIL = "⚠️ Failed to save history: {error}"
    SIGNING_USE_STORE = "Use a certificate from the Windows certificate store"
    SIGNING_USE_STORE_TIP = (
        "More secure: no password is placed on the command line, where any "
        "other process could read it"
    )
    SIGNING_SUBJECT_LABEL = "Certificate subject name:"
    SIGNING_SUBJECT_PLACEHOLDER = "e.g. Acme Ltd"


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
    ABOUT_DESC_PLAIN = (
        "A professional tool for converting Python applications into EXE files "
        "using PyInstaller, with an easy-to-use graphical interface"
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

    # ── Phase 7: Inno Setup installer ──────────────────────────────────
    TAB_INSTALLER = "📦 Installer"
    GROUP_INSTALLER = "📦 Build an installer (Inno Setup)"
    INSTALLER_HINT = (
        "Produce a professional Setup.exe right after the build. "
        "Requires Inno Setup 6 to be installed on this machine."
    )
    INSTALLER_ENABLE = "Build the installer automatically after a successful build"

    GROUP_INSTALLER_IDENTITY = "🪪 Application identity"
    INST_APP_NAME_LABEL = "Application name:"
    INST_APP_NAME_PLACEHOLDER = "Shown in the Start menu and Apps & features"
    INST_VERSION_LABEL = "Version:"
    INST_VERSION_PLACEHOLDER = "1.0.0"
    INST_PUBLISHER_LABEL = "Publisher:"
    INST_PUBLISHER_PLACEHOLDER = "Company or developer name"
    INST_URL_LABEL = "Website:"
    INST_URL_PLACEHOLDER = "https://example.com"
    INST_APPID_LABEL = "AppId (GUID):"
    INST_APPID_PLACEHOLDER = "Derived automatically from name + publisher"
    INST_APPID_TIP = (
        "A stable id makes a newer setup upgrade the existing install "
        "instead of installing side by side"
    )

    GROUP_INSTALLER_OUTPUT = "📤 Installer output"
    INST_OUT_DIR_LABEL = "Output directory:"
    INST_OUT_DIR_PLACEHOLDER = "Default: next to the produced EXE"
    INST_OUT_NAME_LABEL = "Setup file name:"
    INST_OUT_NAME_PLACEHOLDER = "Default: <name>-<version>-setup"
    INST_LICENSE_LABEL = "License file:"
    INST_LICENSE_PLACEHOLDER = "Optional - shown in the wizard (.txt/.rtf)"
    INST_README_LABEL = "README file:"
    INST_README_PLACEHOLDER = "Optional - shown after installation"
    INST_SETUP_ICON_LABEL = "Setup icon:"
    INST_SETUP_ICON_PLACEHOLDER = "Optional - .ico for Setup.exe itself"

    GROUP_INSTALLER_OPTIONS = "⚙️ Installation options"
    INST_PRIVILEGES_LABEL = "Install privileges:"
    INST_PRIV_ADMIN = "All users (requires admin)"
    INST_PRIV_LOWEST = "Current user only (no admin)"
    INST_ARCH_LABEL = "Architecture:"
    INST_ARCH_X64 = "64-bit only"
    INST_ARCH_X86 = "32-bit"
    INST_ARCH_ANY = "Any architecture"
    INST_COMPRESSION_LABEL = "Compression:"
    INST_LANGUAGES_LABEL = "Installer languages:"
    INST_ARABIC_ISL_LABEL = "Arabic.isl file:"
    INST_ARABIC_ISL_PLACEHOLDER = "Required for Arabic (unofficial translation)"
    INST_ARABIC_ISL_TIP = (
        "Inno Setup does not bundle Arabic — download Arabic.isl from the "
        "community translations and point to it here"
    )
    INST_DESKTOP_ICON = "Create a desktop shortcut"
    INST_LAUNCH_AFTER = "Launch the application after installing"
    INST_ALLOW_DIR_CHANGE = "Let the user change the install directory"
    INST_UNINSTALL_ICON = "Add an uninstall shortcut"
    INST_SIGN_INSTALLER = "Digitally sign Setup.exe"
    INST_SIGN_TIP = "Reuses the signing settings from the Deploy tab"
    INST_ASSOC_LABEL = "Associate file extension:"
    INST_ASSOC_PLACEHOLDER = "Optional - e.g. .myapp"

    GROUP_INSTALLER_TOOLCHAIN = "🔧 Inno Setup compiler"
    INST_ISCC_LABEL = "ISCC.exe path:"
    INST_ISCC_PLACEHOLDER = "Default: auto-detect on PATH and standard install dirs"
    BTN_DETECT_ISCC = "🔍 Auto-detect"
    BTN_GENERATE_ISS = "📝 Generate .iss only"
    BTN_BUILD_INSTALLER = "📦 Build installer now"

    # Installer messages
    LOG_ISCC_FOUND = "✅ Inno Setup found: {path}"
    LOG_ISCC_MISSING = (
        "⚠️ ISCC.exe not found — install Inno Setup 6 or set the path manually"
    )
    LOG_INSTALLER_START = "📦 Building the installer..."
    LOG_INSTALLER_OK = "✅ Installer created: {path}"
    LOG_INSTALLER_FAIL = "❌ Installer build failed: {error}"
    LOG_INSTALLER_SKIPPED = "⏭️ Installer step skipped: {reason}"
    LOG_ISS_WRITTEN = "✅ Inno Setup script generated: {path}"
    LOG_ISS_FAIL = "❌ Failed to generate the .iss file: {error}"
    LOG_INSTALLER_LANG_WARN = "⚠️ Unsupported languages ignored: {langs}"
    ERR_INSTALLER_NO_EXE = "No built EXE found — run the build first"
    ERR_INSTALLER_NO_NAME = "Enter the application name in the Installer tab first"
    DIALOG_SAVE_ISS = "Save Inno Setup script"
    DIALOG_FILTER_ISS = "Inno Setup Scripts (*.iss);;All Files (*.*)"
    DIALOG_CHOOSE_ISCC = "Choose ISCC.exe"
    DIALOG_FILTER_EXE = "Executables (*.exe);;All Files (*.*)"
    DIALOG_CHOOSE_LICENSE = "Choose the license file"
    DIALOG_FILTER_TEXT = "Text Files (*.txt *.rtf);;All Files (*.*)"
    DIALOG_CHOOSE_ISL = "Choose Arabic.isl"
    DIALOG_FILTER_ISL = "Inno Setup Language Files (*.isl);;All Files (*.*)"
    MSG_INSTALLER_OK = "Installer created successfully:\n{path}"

    # ── Phase 9: simplified mode ──
    WELCOME_TITLE = "Welcome 👋"
    WELCOME_BODY = (
        "There are two ways to use this app:\n\n"
        "• Simple mode: three steps — pick the file, pick the type, build.\n"
        "• Advanced mode: every tab (Deploy, Installer, Version Info...).\n\n"
        "You can switch between them at any time with the mode button."
    )
    WELCOME_CHOOSE_SIMPLE = "Start in simple mode"
    WELCOME_CHOOSE_ADVANCED = "Start in advanced mode"
    BTN_MODE_TO_ADVANCED = "🔧 Advanced mode"
    BTN_MODE_TO_SIMPLE = "🌱 Simple mode"
    MODE_SIMPLE_TIP = "Show only the essential tabs"
    MODE_ADVANCED_TIP = "Show every tab"
    LOG_MODE_SIMPLE = "🌱 Switched to simple mode"
    LOG_MODE_ADVANCED = "🔧 Switched to advanced mode"

    # ── Phase 9: platform support ──
    LIST_SEPARATOR = ", "
    PLATFORM_WINDOWS_ONLY_FMT = (
        "⚠️ You are running on {platform}. The following features only take "
        "effect when building on Windows and will do nothing here: {features}"
    )
    FEATURE_CODE_SIGNING = "code signing"
    FEATURE_MANIFEST = "Windows manifest"
    FEATURE_VERSION_INFO = "version info"
    FEATURE_INSTALLER = "Inno Setup installer"

    # ── Phase 9: themes ──
    THEME_SELECT_LABEL = "Theme:"
    THEME_LABEL_AUTO = "🖥️ Automatic (follow system)"
    THEME_LABEL_DARK = "🌙 Dark"
    THEME_LABEL_LIGHT = "☀️ Light"
    THEME_LABEL_NORD = "❄️ Nord"
    THEME_LABEL_HIGH_CONTRAST = "🔲 High contrast"
    LOG_THEME_CHANGED = "🎨 Theme changed: {theme}"

    # ── Phase 9: font zoom ──
    LOG_ZOOM_FMT = "🔍 Font size: {percent}%"
    ZOOM_IN_TIP = "Increase font size (Ctrl++)"
    ZOOM_OUT_TIP = "Decrease font size (Ctrl+-)"
    ZOOM_RESET_TIP = "Reset font size (Ctrl+0)"

    # ── Phase 9: system tray ──
    TRAY_TOOLTIP = "Python to EXE Converter"
    TRAY_SHOW = "Show window"
    TRAY_CANCEL = "Cancel build"
    TRAY_QUIT = "Quit"
    TRAY_BUILD_OK_TITLE = "Build finished ✅"
    TRAY_BUILD_OK_BODY = "{name} was created successfully"
    TRAY_BUILD_FAIL_TITLE = "Build failed ❌"
    TRAY_BUILD_FAIL_BODY = "Check the log for the reason"

    # ── Phase 9: real build stages ──
    STAGE_STARTING = "Starting"
    STAGE_ANALYZING = "Analyzing imports"
    STAGE_HOOKS = "Processing hooks"
    STAGE_DEPENDENCIES = "Collecting libraries"
    STAGE_PYZ = "Building PYZ archive"
    STAGE_PKG = "Assembling package"
    STAGE_EXE = "Building executable"
    STAGE_COLLECT = "Copying files"
    PROGRESS_STAGE_FMT = "{stage} — %p%"

    # ── Phase 9: icon preview ──
    ICON_PREVIEW_LABEL = "Preview:"
    ICON_PREVIEW_NONE = "No icon"
    ICON_PREVIEW_INVALID = "⚠️ Could not read the icon — make sure it is a valid .ico"

    # ── Phase 9: log filters ──
    LOG_FILTER_LABEL = "Filter:"
    LOG_FILTER_ALL = "All"
    LOG_FILTER_ERRORS = "❌ Errors"
    LOG_FILTER_WARNINGS = "⚠️ Warnings"
    LOG_FILTER_SUCCESS = "✅ Success"
    LOG_FILTER_EMPTY = "No lines match this filter."

    # ── Phase 10: batch conversion ──
    TAB_BATCH = "📚 Batch"
    GROUP_BATCH_FILES = "📚 File queue"
    BATCH_HINT = (
        "Convert several files with the same settings. They run one after "
        "another — PyInstaller writes into the same build/ and dist/ folders."
    )
    BTN_BATCH_ADD = "➕ Add files"
    BTN_BATCH_REMOVE = "🗑️ Remove selected"
    BTN_BATCH_CLEAR = "🧹 Clear queue"
    BTN_BATCH_START = "🚀 Start batch"
    BTN_BATCH_CANCEL = "⏹️ Cancel"
    GROUP_BATCH_RESULT = "📊 Result"
    BATCH_EMPTY = "The queue is empty — add .py files to begin."
    BATCH_SUMMARY_FMT = (
        "Total: {total} | ✅ ok: {succeeded} | ❌ failed: {failed} | "
        "⊘ cancelled: {cancelled} | duration: {duration}s"
    )
    BATCH_FAILURES_FMT = "Failed files: {names}"
    LOG_BATCH_START = "📚 Starting batch conversion of {count} file(s)..."
    LOG_BATCH_JOB_START = "▶ ({index}/{total}) {name}"
    LOG_BATCH_JOB_OK = "✅ ({index}/{total}) {name} — done in {duration}s"
    LOG_BATCH_JOB_FAIL = "❌ ({index}/{total}) {name} — failed"
    LOG_BATCH_DONE = "📚 Batch conversion finished."
    LOG_BATCH_CANCELLED = "⚠️ Batch conversion cancelled."
    ERR_BATCH_NO_FILES = "Add at least one file to the batch queue"
    ERR_BATCH_BUSY = "A build is already running"
    MSG_BATCH_CANCEL_CONFIRM = "Cancel the batch? The remaining files will not be built."
    DIALOG_CHOOSE_BATCH_FILES = "Choose .py files for batch conversion"

    # ── Phase 10: update check ──
    BTN_CHECK_UPDATES = "🔄 Check for updates"
    UPDATE_CHECK_ON_START = "Check for updates on startup"
    UPDATE_AVAILABLE_FMT = (
        "A new version is available: {version} (you have {current}).\n\n"
        "Nothing is downloaded automatically — open the releases page to "
        "review and download it yourself."
    )
    BTN_OPEN_RELEASES = "Open releases page"
    UPDATE_NONE = "You are on the latest version ✅"
    LOG_UPDATE_CHECKING = "🔄 Checking for updates..."
    LOG_UPDATE_AVAILABLE = "🎉 A new version is available: {version} — {url}"
    LOG_UPDATE_NONE = "✅ No update — you are on the latest version ({version})"
    LOG_UPDATE_FAILED = "⚠️ Could not check for updates (check your connection)"

    # ── Phase 10: presets ──
    GROUP_PRESETS = "⭐ Saved presets"
    PRESETS_HINT = (
        "Save the current settings under a name and restore them later with "
        "one click, instead of hunting for a JSON file each time."
    )
    PRESET_NONE = "— no saved presets —"
    BTN_PRESET_SAVE = "💾 Save as"
    BTN_PRESET_APPLY = "📥 Apply"
    BTN_PRESET_DELETE = "🗑️ Delete"
    BTN_PRESET_EXPORT = "📤 Export all"
    BTN_PRESET_IMPORT = "📥 Import"
    PRESET_NAME_PROMPT = "Preset name:"
    PRESET_SAVED_FMT = "⭐ Preset saved: {name}"
    PRESET_APPLIED_FMT = "📥 Preset applied: {name}"
    PRESET_DELETED_FMT = "🗑️ Preset deleted: {name}"
    PRESET_OVERWRITE_CONFIRM = "A preset named '{name}' already exists. Replace it?"
    MSG_PRESET_DELETE_CONFIRM = "Delete the preset '{name}'? This cannot be undone."
    ERR_PRESET_NAME = "Enter a valid preset name"
    ERR_PRESET_SAVE_FAIL = "Could not save the preset: {error}"
    LOG_PRESET_IMPORTED_FMT = "📥 Imported {count} preset(s)"
    LOG_PRESET_IMPORT_NONE = "No new presets imported (the names already exist)"
    DIALOG_EXPORT_PRESETS = "Export saved presets"
    DIALOG_IMPORT_PRESETS = "Import saved presets"


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
