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
        "طبيب مشروع يكتشف ما سيكسر الـ EXE ويصلحه بنقرة",
        "تشخيص أعطال البناء والتشغيل",
        "استوديو أيقونات .ico بكل الأحجام",
        "بيئة بناء معزولة + مختبر الحجم + تقرير البناء",
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

    # ── 1.3: project doctor and diagnostics ──
    TAB_DOCTOR = "🩺 طبيب المشروع"
    DOCTOR_SCORE_FMT = "درجة الجاهزية: {score}/100"
    DOCTOR_SCORE_NONE = "درجة الجاهزية: —"
    DOCTOR_SUMMARY_FMT = "{errors} خطأ · {warnings} تحذير · {infos} ملاحظة"
    DOCTOR_BUILD_SUMMARY_FMT = "مشاكل من آخر بناء/تشغيل: {count}"
    DOCTOR_HINT = (
        "يفحص الطبيب كودك دون تشغيله بحثاً عمّا يعمل في بايثون وينكسر بعد "
        "التحويل، ويقرأ أخطاء آخر بناء وتشغيل. حدّد الإصلاحات ثم طبّقها بنقرة."
    )
    DOCTOR_NO_SOURCE = "اختر ملف المصدر في التبويب الرئيسي ليبدأ الفحص."
    DOCTOR_ALL_CLEAR = "✅ لا مشاكل معروفة — مشروعك جاهز للبناء"
    BTN_DOCTOR_EXAMINE = "🔍 افحص الآن"
    BTN_DOCTOR_APPLY = "✅ طبّق الإصلاحات المحددة"
    BTN_DOCTOR_APPLY_REBUILD = "🔁 طبّق وأعد البناء"
    BTN_DOCTOR_DIAGNOSE = "🧪 تشغيل تشخيصي"
    BTN_DOCTOR_DIAGNOSE_TIP = (
        "التطبيق بلا Console يُخفي رسالة الخطأ عند انهياره. هذا الزر يبني نسخة "
        "تشخيصية مع Console في مجلد جانبي، يشغّلها، ويقرأ الخطأ الحقيقي."
    )
    BTN_DOCTOR_COPY = "📋 نسخ الكود"
    BTN_DOCTOR_COPY_PIP = "📋 نسخ أمر التثبيت"
    DOCTOR_COPIED = "📋 تم النسخ إلى الحافظة"
    DOCTOR_FIXES_HEADER = "الإصلاح التلقائي:"
    DOCTOR_MANUAL_HEADER = "يتطلب تعديلاً منك — انسخ الكود التالي:"
    DOCTOR_PIP_HEADER = "ثبّت المكتبة في بايثون الذي يبني التطبيق:"
    DOCTOR_NOTE_HEADER = "ملاحظة:"
    DOCTOR_NOTHING_SELECTED = "لم تحدد أي إصلاح قابل للتطبيق"
    DOCTOR_READINESS_BTN_FMT = "🩺 {score}/100"
    DOCTOR_READINESS_TIP = "درجة جاهزية المشروع للتحويل — اضغط لعرض التفاصيل"
    LOG_DOCTOR_FIX_APPLIED = "🩺 تم تطبيق: {fix}"
    LOG_DOCTOR_PREBUILD = (
        "🩺 الطبيب وجد {errors} خطأ قد يكسر الـ EXE — راجع تبويب «طبيب المشروع»"
    )
    LOG_DOCTOR_BUILD_FINDINGS = (
        "🩺 تم تشخيص {count} سبب محتمل مع حلول مقترحة — راجع تبويب «طبيب المشروع»"
    )
    MSG_DOCTOR_FAILED_HINT = "\n\n🩺 الطبيب وجد {count} سبب محتمل مع حلول جاهزة في تبويب «طبيب المشروع»."
    LOG_SMOKE_WINDOWED_HINT = (
        "ℹ️ تطبيق بلا Console: إن ظهر خطأ فلن يراه الاختبار. استخدم «🧪 تشغيل تشخيصي» "
        "في تبويب الطبيب لقراءة الخطأ الحقيقي."
    )
    LOG_DIAG_START = "🧪 بناء نسخة تشخيصية (مع Console) في: {path}"
    LOG_DIAG_RUN = "🧪 تشغيل النسخة التشخيصية..."
    LOG_DIAG_DONE_FMT = "🧪 انتهى التشغيل التشخيصي: {count} مشكلة"
    LOG_DIAG_CLEAN = "🧪 النسخة التشخيصية عملت دون أخطاء ظاهرة خلال مهلة الاختبار"
    LOG_DIAG_BUILD_FAILED = "🧪 فشل بناء النسخة التشخيصية — راجع السجل"
    MSG_DIAG_BUSY = "هناك عملية بناء قيد التنفيذ. انتظر حتى تنتهي."

    ORIGIN_DOCTOR = "فحص مسبق"
    ORIGIN_BUILD = "سجل البناء"
    ORIGIN_WARN = "تحذيرات PyInstaller"
    ORIGIN_RUNTIME = "تشغيل الـ EXE"

    FIX_LABEL_HIDDEN_IMPORT = "إضافة Hidden Import: {value}"
    FIX_LABEL_ADD_DATA = "تضمين مع الـ EXE: {value}"
    FIX_LABEL_FLAG = "إضافة الخيار: {value}"
    FIX_LABEL_CONSOLE = "إعادة تفعيل نافذة Console"
    FIX_LABEL_SET_SOURCE = "البناء من الملف: {value}"

    FINDING_SOURCE_UNREADABLE_TITLE = "تعذّرت قراءة ملف المصدر"
    FINDING_SOURCE_UNREADABLE_DETAIL = "الخطأ: {error}. تأكد أن الملف موجود ومحفوظ بترميز UTF-8."
    FINDING_SYNTAX_ERROR_TITLE = "خطأ صياغة في السطر {line}"
    FINDING_SYNTAX_ERROR_DETAIL = "بايثون لا يستطيع قراءة الملف: {error}. أصلحه قبل البناء."
    FINDING_MISSING_PACKAGE_TITLE = "المكتبة «{module}» غير مثبتة في بيئة البناء"
    FINDING_MISSING_PACKAGE_DETAIL = (
        "PyInstaller يضمّن فقط ما يجده في بايثون الذي يبني التطبيق. بدونها سيُغلق "
        "الـ EXE فوراً بخطأ ModuleNotFoundError."
    )
    FINDING_PACKAGE_NEEDS_COLLECT_TITLE = "«{package}» تحتاج ملفات لا يراها PyInstaller وحده"
    FINDING_PACKAGE_NEEDS_COLLECT_DETAIL = (
        "هذه المكتبة تحمّل وحدات أو ملفات بيانات بطريقة ديناميكية. الإصلاح يضيف "
        "خيارات التجميع المناسبة لها."
    )
    FINDING_PACKAGE_DATA_DIR_TITLE = "مجلد «{folder}» الذي تحتاجه {package} غير مضمّن"
    FINDING_PACKAGE_DATA_DIR_DETAIL = (
        "{package} تبحث عن هذا المجلد بجوار البرنامج وقت التشغيل، ولن يكون موجوداً "
        "داخل الـ EXE ما لم يُضمَّن."
    )
    FINDING_PACKAGE_CONSOLE_STREAMS_TITLE = "«{package}» تنهار في تطبيق بلا Console"
    FINDING_PACKAGE_CONSOLE_STREAMS_DETAIL = (
        "هذه المكتبة تكتب مباشرة إلى sys.stdout أو sys.stderr، وهما None في تطبيق "
        "بلا Console. إما أن تُعيد الـ Console، أو تضيف الكود التالي أول البرنامج."
    )
    FINDING_LARGE_PACKAGE_TITLE = "«{package}» ستزيد حجم الـ EXE كثيراً"
    FINDING_LARGE_PACKAGE_DETAIL = "ليست مشكلة، لكن توقّع حجماً كبيراً ووقت إقلاع أطول في وضع الملف الواحد."
    FINDING_MULTIPLE_QT_BINDINGS_TITLE = "الكود يستورد أكثر من مكتبة Qt: {bindings}"
    FINDING_MULTIPLE_QT_BINDINGS_DETAIL = (
        "PyInstaller يرفض تضمين أكثر من مكتبة Qt في تطبيق واحد. اختر واحدة فقط في الكود."
    )
    FINDING_OTHER_QT_BINDINGS_INSTALLED_TITLE = "مكتبات Qt أخرى مثبتة بجانب {binding}"
    FINDING_OTHER_QT_BINDINGS_INSTALLED_DETAIL = (
        "إن جرّتها مكتبة أخرى (مثل matplotlib) يتوقف البناء بخطأ «multiple Qt bindings». "
        "استبعادها احتياط آمن ويقلل الحجم."
    )
    FINDING_DATA_NOT_BUNDLED_TITLE = "الملف «{path}» يستخدمه الكود لكنه غير مضمّن"
    FINDING_DATA_NOT_BUNDLED_DETAIL = (
        "الكود يشير إلى «{literal}» وهو موجود بجوار السكربت، لكنه لن يكون داخل الـ EXE "
        "فيظهر FileNotFoundError عند التشغيل."
    )
    FINDING_RELATIVE_PATHS_TITLE = "مسارات نسبية ستنكسر بعد التحويل"
    FINDING_RELATIVE_PATHS_DETAIL = (
        "مسار مثل «{example}» يُحسب من مجلد التشغيل الحالي، لا من مكان الملفات المضمّنة "
        "داخل الـ EXE. استخدم الدالة resource_path التالية لكل ملف بيانات."
    )
    FINDING_MISSING_FREEZE_SUPPORT_TITLE = "multiprocessing بدون freeze_support()"
    FINDING_MISSING_FREEZE_SUPPORT_DETAIL = (
        "بدونها يفتح الـ EXE على Windows نسخاً متتالية من نفسه بدل تشغيل العمليات "
        "الفرعية. أضف السطر أول كتلة if __name__ == \"__main__\"."
    )
    FINDING_INPUT_IN_WINDOWED_TITLE = "input() في تطبيق بلا Console"
    FINDING_INPUT_IN_WINDOWED_DETAIL = (
        "لا توجد لوحة أوامر يُكتب فيها الإدخال، فينهار البرنامج بخطأ "
        "«input(): lost sys.stdin». أعد تفعيل الـ Console أو استبدل input بنافذة إدخال."
    )
    FINDING_STREAM_IN_WINDOWED_TITLE = "{stream} يُستخدم مباشرة في تطبيق بلا Console"
    FINDING_STREAM_IN_WINDOWED_DETAIL = (
        "{stream} يساوي None في تطبيق بلا Console، فأي استدعاء عليه ينهار. print() "
        "آمنة، لكن الاستخدام المباشر ليس كذلك."
    )
    FINDING_NO_ENTRY_POINT_TITLE = "الملف لا يشغّل شيئاً — ربما اخترت الملف الخطأ"
    FINDING_NO_ENTRY_POINT_DETAIL = (
        "الملف يعرّف دوالاً وأصنافاً فقط، فسيُغلق الـ EXE دون أن يفعل شيئاً. يبدو أن "
        "«{candidate}» هو نقطة الدخول الحقيقية."
    )
    FINDING_NO_ENTRY_POINT_ALONE_TITLE = "الملف لا يشغّل شيئاً"
    FINDING_NO_ENTRY_POINT_ALONE_DETAIL = (
        "الملف يعرّف دوالاً وأصنافاً فقط ولا يستدعي أياً منها، فسيُغلق الـ EXE فوراً. "
        "أضف نقطة دخول."
    )
    FINDING_ICON_NOT_ICO_TITLE = "«{icon}» ليس ملف .ico حقيقياً"
    FINDING_ICON_NOT_ICO_DETAIL = (
        "يبدو أنه صورة أُعيدت تسميتها إلى .ico. أنشئ أيقونة صحيحة بأحجام متعددة من "
        "«🎨 استوديو الأيقونات» في التبويب الرئيسي."
    )
    FINDING_ICON_SINGLE_SIZE_TITLE = "«{icon}» يحوي حجماً واحداً فقط ({size}px)"
    FINDING_ICON_SINGLE_SIZE_DETAIL = (
        "سيقوم Windows بتكبيرها أو تصغيرها فتظهر مشوّشة في شريط المهام وسطح المكتب. "
        "«🎨 استوديو الأيقونات» يولّد كل الأحجام."
    )
    FINDING_PYINSTALLER_MISSING_TITLE = "PyInstaller غير مثبت في بيئة البناء"
    FINDING_PYINSTALLER_MISSING_DETAIL = "ثبّته بالأمر: pip install pyinstaller ثم أعد البناء."
    FINDING_RUNTIME_MISSING_MODULE_TITLE = "الـ EXE لم يجد الوحدة «{module}»"
    FINDING_RUNTIME_MISSING_MODULE_DETAIL = (
        "المكتبة مثبتة لكن PyInstaller لم يكتشف استيرادها (استيراد ديناميكي غالباً). "
        "الإصلاح يضيفها صراحةً."
    )
    FINDING_MISSING_METADATA_TITLE = "بيانات الحزمة «{package}» الوصفية غير مضمّنة"
    FINDING_MISSING_METADATA_DETAIL = (
        "الكود (أو مكتبة يستخدمها) يقرأ إصدار الحزمة وقت التشغيل عبر importlib.metadata. "
        "الإصلاح ينسخ بياناتها الوصفية إلى الـ EXE."
    )
    FINDING_MISSING_DATA_FILE_TITLE = "الـ EXE لم يجد الملف «{path}»"
    FINDING_MISSING_DATA_FILE_DETAIL = (
        "الملف إما غير مضمّن، أو مضمّن لكن الكود يبحث عنه بمسار نسبي. ضمّنه، واستخدم "
        "resource_path للوصول إليه."
    )
    FINDING_TEMPLATE_NOT_FOUND_TITLE = "القالب «{template}» غير موجود داخل الـ EXE"
    FINDING_TEMPLATE_NOT_FOUND_DETAIL = "مجلد templates لم يُضمَّن مع التطبيق. الإصلاح يضمّنه."
    FINDING_STREAMS_NONE_TITLE = "انهيار بسبب غياب الـ Console (.{attr})"
    FINDING_STREAMS_NONE_DETAIL = (
        "كود ما استدعى sys.stdout أو sys.stderr وهما None في تطبيق بلا Console. أعد "
        "تفعيل الـ Console أو أضف الكود التالي أول البرنامج."
    )
    FINDING_DLL_LOAD_FAILED_TITLE = "فشل تحميل DLL أثناء استيراد «{module}»"
    FINDING_DLL_LOAD_FAILED_DETAIL = (
        "ملف مكتبة ثنائي تحتاجه «{package}» لم يُضمَّن. الإصلاح يجمع ملفاتها الثنائية؛ "
        "وإن استمر الخطأ فقد يلزم تثبيت Visual C++ Redistributable على الجهاز المستهدف."
    )
    FINDING_MULTIPLE_QT_BINDINGS_BUILD_TITLE = "البناء توقف: أكثر من مكتبة Qt ({bindings})"
    FINDING_MULTIPLE_QT_BINDINGS_BUILD_DETAIL = (
        "PyInstaller لا يدعم أكثر من مكتبة Qt في تطبيق واحد. الإصلاح يستبعد {drop}."
    )
    FINDING_ADD_DATA_MISSING_TITLE = "ملف إضافي غير موجود: {path}"
    FINDING_ADD_DATA_MISSING_DETAIL = (
        "أحد خيارات --add-data يشير إلى مسار غير موجود. صحّحه في «أوامر PyInstaller "
        "إضافية» أو احذفه."
    )
    FINDING_ICON_WRONG_FORMAT_TITLE = "صيغة الأيقونة «{icon}» غير مدعومة"
    FINDING_ICON_WRONG_FORMAT_DETAIL = (
        "Windows يقبل .ico فقط. حوّل الصورة إلى أيقونة من «🎨 استوديو الأيقونات» في "
        "التبويب الرئيسي."
    )
    FINDING_FILE_LOCKED_TITLE = "الملف «{path}» مقفل"
    FINDING_FILE_LOCKED_DETAIL = (
        "غالباً النسخة السابقة من البرنامج ما زالت تعمل، أو مكافح الفيروسات يفحصها. "
        "أغلق البرنامج وأعد المحاولة."
    )
    FINDING_RUNTIME_UNHANDLED_TITLE = "الـ EXE انهار بخطأ غير معروف"
    FINDING_RUNTIME_UNHANDLED_DETAIL = (
        "آخر خطأ: {error}\nهذا الخطأ ليس من الأنماط المعروفة للتحويل — قد يكون خطأً في "
        "الكود نفسه. جرّب تشغيل السكربت بـ python للمقارنة."
    )
    FINDING_WARN_MISSING_MODULE_TITLE = "PyInstaller لم يجد «{module}» الذي يستورده كودك"
    FINDING_WARN_MISSING_MODULE_DETAIL = (
        "ورد في ملف تحذيرات PyInstaller. إن كانت مكتبة خارجية فثبّتها في بيئة البناء."
    )

    # ── 1.3: icon studio ──
    BTN_ICON_STUDIO = "🎨"
    ICON_STUDIO_TITLE = "🎨 استوديو الأيقونات"
    ICON_STUDIO_HINT = (
        "أنشئ ملف .ico حقيقياً بكل الأحجام التي يطلبها Windows "
        "(16 إلى 256) من صورة، أو من حروف اسم برنامجك."
    )
    ICON_STUDIO_FROM_IMAGE = "من صورة"
    ICON_STUDIO_FROM_TEXT = "من حروف"
    ICON_STUDIO_CHOOSE_IMAGE = "📂 اختر صورة"
    ICON_STUDIO_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp);;All Files (*.*)"
    ICON_STUDIO_TEXT_LABEL = "النص (حرف أو حرفان):"
    ICON_STUDIO_COLOR = "🎨 لون الخلفية"
    ICON_STUDIO_SHAPE_LABEL = "الشكل:"
    ICON_STUDIO_SHAPE_ROUNDED = "مربع بزوايا دائرية"
    ICON_STUDIO_SHAPE_CIRCLE = "دائرة"
    ICON_STUDIO_SHAPE_SQUARE = "مربع"
    ICON_STUDIO_PREVIEW = "معاينة:"
    ICON_STUDIO_SAVE = "💾 حفظ واستخدام الأيقونة"
    ICON_STUDIO_SAVE_DIALOG = "حفظ الأيقونة"
    ICON_STUDIO_ICO_FILTER = "Icon Files (*.ico)"
    ICON_STUDIO_NOTHING = "اختر صورة أو اكتب نصاً أولاً"
    ICON_STUDIO_BAD_IMAGE = "تعذّر فتح الصورة"
    ICON_STUDIO_SAVE_FAIL = "تعذّر حفظ الأيقونة: {error}"
    LOG_ICON_STUDIO_SAVED = "🎨 تم إنشاء الأيقونة ({sizes}): {path}"

    # ── 1.4: build environment, size lab, build report, sandbox ──
    TAB_SIZE = "⚖️ الحجم والبيئة"
    GROUP_BUILD_ENV = "🧪 بيئة البناء"
    ENV_HINT = (
        "PyInstaller يضمّن كل ما يجده مثبتاً، فالبناء من بايثون مليء بالمكتبات "
        "يضخّم الـ EXE. البيئة المعزولة تحوي فقط ما يستورده مشروعك."
    )
    ENV_MODE_CURRENT_FMT = "بايثون الحالي ({version})"
    ENV_MODE_ISOLATED = "بيئة معزولة لهذا المشروع (موصى بها: EXE أصغر وبناء قابل للتكرار)"
    ENV_BASE_PYTHON_LABEL = "بايثون لإنشاء البيئة:"
    ENV_BASE_PYTHON_PLACEHOLDER = "اتركه فارغاً لاستخدام بايثون الحالي"
    DIALOG_CHOOSE_PYTHON = "اختر مفسّر بايثون"
    DIALOG_FILTER_PYTHON = "Python (python.exe python python3*);;All Files (*)"
    ENV_STATUS_NONE = "البيئة: لم تُنشأ بعد"
    ENV_STATUS_FMT = "البيئة: Python {version} · {size}\n{path}"
    ENV_STATUS_NO_SOURCE = "اختر ملف المصدر أولاً"
    ENV_REQUIREMENTS_FMT = "ستُثبَّت: {items}"
    ENV_REQ_FROM_LOCK = "ملف القفل {file} (إصدارات مثبتة بدقة)"
    ENV_REQ_FROM_FILE = "ملف {file}"
    ENV_REQ_NONE = "لا مكتبات خارجية — PyInstaller فقط"
    ENV_UV_NOTE = "⚡ سيُستخدم uv لتسريع إنشاء البيئة"
    BTN_ENV_CREATE = "🔧 إنشاء / تحديث البيئة"
    BTN_ENV_RECREATE = "♻️ إعادة الإنشاء من الصفر"
    BTN_ENV_LOCK = "🔒 حفظ ملف القفل"
    BTN_ENV_LOCK_TIP = (
        "يحفظ الإصدارات الدقيقة للمكتبات في p2e-build.lock بجوار مشروعك، فتُعاد "
        "البيئة نفسها تماماً على أي جهاز."
    )
    BTN_ENV_DELETE = "🗑️ حذف البيئة"
    MSG_ENV_CONFIRM = (
        "سيتم تنفيذ الأوامر التالية (تحتاج اتصالاً بالإنترنت لتنزيل الحزم):\n\n"
        "{commands}\n\nمتابعة؟"
    )
    MSG_ENV_DELETE_CONFIRM = "حذف البيئة المعزولة لهذا المشروع ({size})؟"
    MSG_ENV_NEEDED = (
        "اخترت البناء في بيئة معزولة، لكنها لم تُنشأ بعد.\n"
        "إنشاؤها الآن ثم البناء؟"
    )
    LOG_ENV_START = "🧪 إنشاء بيئة البناء: {path}"
    LOG_ENV_STEP = "▶ {cmd}"
    LOG_ENV_RETRY_SINGLE = "⚠️ فشل التثبيت المجمّع — إعادة المحاولة لكل حزمة على حدة"
    LOG_ENV_PACKAGE_FAILED = "❌ تعذّر تثبيت: {name}"
    LOG_ENV_DONE = "✅ بيئة البناء جاهزة"
    LOG_ENV_DONE_PARTIAL = (
        "⚠️ البيئة جاهزة لكن تعذّر تثبيت: {names} — أضفها إلى requirements.txt "
        "بأسمائها الصحيحة على PyPI"
    )
    LOG_ENV_FAILED = "❌ فشل إنشاء البيئة: {error}"
    LOG_ENV_DELETED = "🗑️ حُذفت بيئة البناء"
    LOG_ENV_LOCK_SAVED = "🔒 حُفظ ملف القفل: {path}"
    LOG_ENV_LOCK_FAILED = "❌ تعذّر حفظ ملف القفل: {error}"
    LOG_ENV_PYTHON = "🐍 البناء باستخدام: {python}"
    ERR_ENV_PYTHON_MISSING = "مفسّر بايثون غير موجود: {path}"

    GROUP_SIZE = "📏 مختبر الحجم — آخر بناء"
    SIZE_NONE = "ابنِ مشروعك ليظهر هنا ما بداخل الـ EXE وحجم كل مكتبة."
    SIZE_SUMMARY_FMT = "الحجم على القرص: {disk} · المحتوى قبل الضغط: {content}"
    SIZE_COMPARE_FMT = "مقارنة بالبناء السابق ({previous}): {change}"
    SIZE_COL_PACKAGE = "المكتبة"
    SIZE_COL_SIZE = "الحجم"
    SIZE_COL_SHARE = "النسبة"
    SIZE_GROUP_RUNTIME = "مفسّر بايثون ومكوّناته"
    SIZE_GROUP_STDLIB = "مكتبة بايثون القياسية"
    SIZE_GROUP_SCRIPT = "كودك"
    SIZE_INDIRECT_FMT = (
        "💡 {size} من مكتبات لا يستوردها كودك مباشرة ({names}). كثير منها تبعيات "
        "حقيقية، لكن البناء في بيئة معزولة يتخلص مما جاء لمجرد أنه مثبت."
    )
    SIZE_ONEFILE_SLOW_FMT = (
        "🐢 ملف واحد بحجم {size} يفك نفسه عند كل تشغيل فيبطؤ إقلاعه. وضع المجلد مع "
        "مثبّت يقلع فوراً."
    )
    GROUP_SIZE_SUGGESTIONS = "✂️ مقترحات التنحيف"
    SIZE_SUGGESTIONS_NONE = "لا مقترحات — لا توجد في الـ EXE مكتبات معروفة يمكن استبعادها."
    SIZE_SUGGESTIONS_HINT = (
        "مكتبات داخل الـ EXE لا يستوردها كودك. استبعادها آمن غالباً، وأي خطأ بعد "
        "إعادة البناء سيلتقطه طبيب المشروع."
    )
    BTN_SIZE_APPLY = "✅ استبعد المحدد"
    BTN_SIZE_APPLY_REBUILD = "🔁 استبعد وأعد البناء"
    BTN_SIZE_REFRESH = "🔄 حلّل آخر بناء"
    LOG_SIZE_SUMMARY = "📏 الحجم: {disk} — التفاصيل في تبويب «الحجم والبيئة»"

    GROUP_REPORT = "📄 تقرير البناء"
    REPORT_AUTO = "إنشاء تقرير HTML بعد كل بناء ناجح"
    BTN_REPORT_OPEN = "📄 فتح آخر تقرير"
    LOG_REPORT_SAVED = "📄 تقرير البناء: {path}"
    LOG_REPORT_FAILED = "❌ تعذّر كتابة التقرير: {error}"
    REPORT_TITLE = "تقرير البناء"
    REPORT_DETAILS = "التفاصيل"
    REPORT_RESULT = "النتيجة"
    REPORT_SUCCESS = "نجح"
    REPORT_FAILED = "فشل"
    REPORT_SIZE_ON_DISK = "الحجم على القرص"
    REPORT_CONTENTS = "المحتوى قبل الضغط"
    REPORT_DURATION = "مدة البناء"
    REPORT_PREVIOUS = "مقارنة بالبناء السابق"
    REPORT_APP = "التطبيق"
    REPORT_DATE = "التاريخ"
    REPORT_SOURCE = "ملف المصدر"
    REPORT_OUTPUT = "الناتج"
    REPORT_MODE = "النمط"
    REPORT_ONEFILE = "ملف واحد"
    REPORT_ONEDIR = "مجلد"
    REPORT_ENVIRONMENT = "بيئة البناء"
    REPORT_ENV_ISOLATED = "بيئة معزولة"
    REPORT_ENV_CURRENT = "بايثون الحالي"
    REPORT_PYTHON = "Python"
    REPORT_PYINSTALLER = "PyInstaller"
    REPORT_PLATFORM = "النظام"
    REPORT_BREAKDOWN = "ما بداخل الـ EXE"
    REPORT_PACKAGE = "المكتبة"
    REPORT_SIZE = "الحجم"
    REPORT_SHARE = "النسبة"
    REPORT_LARGEST_FILES = "أكبر الملفات"
    REPORT_FINDINGS = "ملاحظات طبيب المشروع"
    REPORT_OPTIONS = "خيارات PyInstaller"
    REPORT_NONE = "لا شيء"
    REPORT_GENERATOR_FMT = "أُنشئ بواسطة {app} {version}"

    BTN_SANDBOX = "🧊 اختبار في Windows Sandbox"
    BTN_SANDBOX_TIP = (
        "يشغّل الـ EXE على نسخة Windows نظيفة تماماً (بلا بايثون ولا مكتباتك) "
        "لكشف مشاكل «يعمل عندي فقط»."
    )
    SANDBOX_UNAVAILABLE = (
        "Windows Sandbox غير متاح على هذا الجهاز (يتطلب Windows 10/11 Pro أو "
        "Enterprise مع تفعيل الميزة).\n\nللاختبار على جهاز نظيف: انسخ\n{path}\n"
        "إلى جهاز أو آلة افتراضية بلا بايثون وشغّله."
    )
    MSG_SANDBOX_NO_BUILD = "ابنِ المشروع أولاً."
    LOG_SANDBOX_WRITTEN = "🧊 ملف Windows Sandbox: {path}"

    FINDING_SIZE_EXCLUDE_CANDIDATE_TITLE = "استبعاد «{package}» يوفّر {size}"
    FINDING_SIZE_EXCLUDE_CANDIDATE_DETAIL = (
        "كودك لا يستورد {package}، لكن مكتبة أخرى جرّتها إلى الـ EXE. إن كانت تلك "
        "المكتبة تحتاجها فعلاً فسيظهر الخطأ في التشخيص بعد إعادة البناء."
    )
    FINDING_ENV_NOT_CREATED_TITLE = "البيئة المعزولة لم تُنشأ بعد"
    FINDING_ENV_NOT_CREATED_DETAIL = (
        "سيُطلب منك إنشاؤها عند البناء، أو أنشئها الآن من تبويب «الحجم والبيئة». "
        "حتى ذلك الحين لا يمكن التحقق من المكتبات المثبتة فيها."
    )


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
        "Project doctor that finds what will break the EXE and fixes it in one click",
        "Build and runtime failure diagnostics",
        "Icon Studio for multi-size .ico files",
        "Isolated build environment, size lab and build report",
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

    # ── 1.3: project doctor and diagnostics ──
    TAB_DOCTOR = "🩺 Project Doctor"
    DOCTOR_SCORE_FMT = "Readiness: {score}/100"
    DOCTOR_SCORE_NONE = "Readiness: —"
    DOCTOR_SUMMARY_FMT = "{errors} error(s) · {warnings} warning(s) · {infos} note(s)"
    DOCTOR_BUILD_SUMMARY_FMT = "Issues from the last build/run: {count}"
    DOCTOR_HINT = (
        "The doctor reads your code without running it, looking for things that "
        "work in Python but break once frozen, and reads the errors from the last "
        "build and run. Tick the fixes you want and apply them in one click."
    )
    DOCTOR_NO_SOURCE = "Choose a source file on the Main tab to start the checkup."
    DOCTOR_ALL_CLEAR = "✅ No known problems — your project is ready to build"
    BTN_DOCTOR_EXAMINE = "🔍 Check now"
    BTN_DOCTOR_APPLY = "✅ Apply selected fixes"
    BTN_DOCTOR_APPLY_REBUILD = "🔁 Apply and rebuild"
    BTN_DOCTOR_DIAGNOSE = "🧪 Diagnostic run"
    BTN_DOCTOR_DIAGNOSE_TIP = (
        "A windowed app hides its error message when it crashes. This builds a "
        "diagnostic copy with a console into a side folder, runs it, and reads "
        "the real error."
    )
    BTN_DOCTOR_COPY = "📋 Copy code"
    BTN_DOCTOR_COPY_PIP = "📋 Copy install command"
    DOCTOR_COPIED = "📋 Copied to clipboard"
    DOCTOR_FIXES_HEADER = "Automatic fix:"
    DOCTOR_MANUAL_HEADER = "Needs a change from you — copy this code:"
    DOCTOR_PIP_HEADER = "Install it into the Python that builds the app:"
    DOCTOR_NOTE_HEADER = "Note:"
    DOCTOR_NOTHING_SELECTED = "No applicable fix is selected"
    DOCTOR_READINESS_BTN_FMT = "🩺 {score}/100"
    DOCTOR_READINESS_TIP = "How ready the project is to build — click for details"
    LOG_DOCTOR_FIX_APPLIED = "🩺 Applied: {fix}"
    LOG_DOCTOR_PREBUILD = (
        "🩺 The doctor found {errors} error(s) that may break the EXE — see the "
        "Project Doctor tab"
    )
    LOG_DOCTOR_BUILD_FINDINGS = (
        "🩺 Diagnosed {count} likely cause(s) with suggested fixes — see the "
        "Project Doctor tab"
    )
    MSG_DOCTOR_FAILED_HINT = (
        "\n\n🩺 The doctor found {count} likely cause(s) with ready fixes on the "
        "Project Doctor tab."
    )
    LOG_SMOKE_WINDOWED_HINT = (
        "ℹ️ Windowed app: if it shows an error, the smoke test cannot see it. Use "
        "“🧪 Diagnostic run” on the Doctor tab to read the real error."
    )
    LOG_DIAG_START = "🧪 Building a diagnostic copy (with console) in: {path}"
    LOG_DIAG_RUN = "🧪 Running the diagnostic copy..."
    LOG_DIAG_DONE_FMT = "🧪 Diagnostic run finished: {count} issue(s)"
    LOG_DIAG_CLEAN = "🧪 The diagnostic copy ran without visible errors within the timeout"
    LOG_DIAG_BUILD_FAILED = "🧪 The diagnostic build failed — see the log"
    MSG_DIAG_BUSY = "A build is already running. Wait for it to finish."

    ORIGIN_DOCTOR = "Pre-build check"
    ORIGIN_BUILD = "Build log"
    ORIGIN_WARN = "PyInstaller warnings"
    ORIGIN_RUNTIME = "Running the EXE"

    FIX_LABEL_HIDDEN_IMPORT = "Add hidden import: {value}"
    FIX_LABEL_ADD_DATA = "Bundle with the EXE: {value}"
    FIX_LABEL_FLAG = "Add option: {value}"
    FIX_LABEL_CONSOLE = "Turn the console back on"
    FIX_LABEL_SET_SOURCE = "Build from: {value}"

    FINDING_SOURCE_UNREADABLE_TITLE = "The source file could not be read"
    FINDING_SOURCE_UNREADABLE_DETAIL = "Error: {error}. Make sure the file exists and is saved as UTF-8."
    FINDING_SYNTAX_ERROR_TITLE = "Syntax error on line {line}"
    FINDING_SYNTAX_ERROR_DETAIL = "Python cannot read the file: {error}. Fix it before building."
    FINDING_MISSING_PACKAGE_TITLE = "“{module}” is not installed in the build environment"
    FINDING_MISSING_PACKAGE_DETAIL = (
        "PyInstaller bundles only what the Python running the build can import. "
        "Without it the EXE closes immediately with ModuleNotFoundError."
    )
    FINDING_PACKAGE_NEEDS_COLLECT_TITLE = "“{package}” needs files PyInstaller can't see alone"
    FINDING_PACKAGE_NEEDS_COLLECT_DETAIL = (
        "This library loads modules or data files dynamically. The fix adds the "
        "collection options it needs."
    )
    FINDING_PACKAGE_DATA_DIR_TITLE = "The “{folder}” folder {package} needs is not bundled"
    FINDING_PACKAGE_DATA_DIR_DETAIL = (
        "{package} looks for this folder next to the program at runtime, and it "
        "won't exist inside the EXE unless it is bundled."
    )
    FINDING_PACKAGE_CONSOLE_STREAMS_TITLE = "“{package}” crashes in a windowed app"
    FINDING_PACKAGE_CONSOLE_STREAMS_DETAIL = (
        "This library writes straight to sys.stdout or sys.stderr, which are None "
        "in a windowed app. Either turn the console back on, or add this code at "
        "the top of your program."
    )
    FINDING_LARGE_PACKAGE_TITLE = "“{package}” will make the EXE much larger"
    FINDING_LARGE_PACKAGE_DETAIL = "Not a problem, but expect a large file and a slower start in one-file mode."
    FINDING_MULTIPLE_QT_BINDINGS_TITLE = "The code imports more than one Qt binding: {bindings}"
    FINDING_MULTIPLE_QT_BINDINGS_DETAIL = (
        "PyInstaller refuses to bundle more than one Qt binding in an app. Pick one "
        "in your code."
    )
    FINDING_OTHER_QT_BINDINGS_INSTALLED_TITLE = "Other Qt bindings are installed besides {binding}"
    FINDING_OTHER_QT_BINDINGS_INSTALLED_DETAIL = (
        "If another library (matplotlib, for example) pulls one in, the build stops "
        "with “multiple Qt bindings”. Excluding them is a safe precaution and "
        "reduces size."
    )
    FINDING_DATA_NOT_BUNDLED_TITLE = "“{path}” is used by the code but not bundled"
    FINDING_DATA_NOT_BUNDLED_DETAIL = (
        "The code refers to “{literal}”, which exists next to the script, but it "
        "won't be inside the EXE, so it fails with FileNotFoundError at runtime."
    )
    FINDING_RELATIVE_PATHS_TITLE = "Relative paths that will break once frozen"
    FINDING_RELATIVE_PATHS_DETAIL = (
        "A path such as “{example}” is resolved from the current working folder, "
        "not from where the bundled files live inside the EXE. Use this "
        "resource_path function for every data file."
    )
    FINDING_MISSING_FREEZE_SUPPORT_TITLE = "multiprocessing without freeze_support()"
    FINDING_MISSING_FREEZE_SUPPORT_DETAIL = (
        "Without it a Windows EXE keeps launching copies of itself instead of "
        "running worker processes. Add the call as the first line of the "
        "if __name__ == \"__main__\" block."
    )
    FINDING_INPUT_IN_WINDOWED_TITLE = "input() in a windowed app"
    FINDING_INPUT_IN_WINDOWED_DETAIL = (
        "There is no console to type into, so the program crashes with "
        "“input(): lost sys.stdin”. Turn the console back on or replace input() "
        "with a dialog."
    )
    FINDING_STREAM_IN_WINDOWED_TITLE = "{stream} is used directly in a windowed app"
    FINDING_STREAM_IN_WINDOWED_DETAIL = (
        "{stream} is None in a windowed app, so any call on it crashes. print() "
        "is safe; direct use is not."
    )
    FINDING_NO_ENTRY_POINT_TITLE = "This file doesn't run anything — wrong file?"
    FINDING_NO_ENTRY_POINT_DETAIL = (
        "The file only defines functions and classes, so the EXE would exit "
        "without doing anything. “{candidate}” looks like the real entry point."
    )
    FINDING_NO_ENTRY_POINT_ALONE_TITLE = "This file doesn't run anything"
    FINDING_NO_ENTRY_POINT_ALONE_DETAIL = (
        "The file only defines functions and classes and never calls them, so the "
        "EXE would exit immediately. Add an entry point."
    )
    FINDING_ICON_NOT_ICO_TITLE = "“{icon}” is not a real .ico file"
    FINDING_ICON_NOT_ICO_DETAIL = (
        "It looks like an image renamed to .ico. Create a proper multi-size icon "
        "with “🎨 Icon Studio” on the Main tab."
    )
    FINDING_ICON_SINGLE_SIZE_TITLE = "“{icon}” contains only one size ({size}px)"
    FINDING_ICON_SINGLE_SIZE_DETAIL = (
        "Windows will scale it and it will look blurry in the taskbar and on the "
        "desktop. “🎨 Icon Studio” generates every size."
    )
    FINDING_PYINSTALLER_MISSING_TITLE = "PyInstaller is not installed in the build environment"
    FINDING_PYINSTALLER_MISSING_DETAIL = "Install it with: pip install pyinstaller, then build again."
    FINDING_RUNTIME_MISSING_MODULE_TITLE = "The EXE could not find the module “{module}”"
    FINDING_RUNTIME_MISSING_MODULE_DETAIL = (
        "The library is installed, but PyInstaller did not detect the import "
        "(usually a dynamic import). The fix adds it explicitly."
    )
    FINDING_MISSING_METADATA_TITLE = "Package metadata for “{package}” is not bundled"
    FINDING_MISSING_METADATA_DETAIL = (
        "Your code (or a library it uses) reads the package version at runtime "
        "through importlib.metadata. The fix copies its metadata into the EXE."
    )
    FINDING_MISSING_DATA_FILE_TITLE = "The EXE could not find “{path}”"
    FINDING_MISSING_DATA_FILE_DETAIL = (
        "The file is either not bundled, or bundled but looked up with a relative "
        "path. Bundle it, and use resource_path to reach it."
    )
    FINDING_TEMPLATE_NOT_FOUND_TITLE = "Template “{template}” is missing from the EXE"
    FINDING_TEMPLATE_NOT_FOUND_DETAIL = "The templates folder was not bundled. The fix bundles it."
    FINDING_STREAMS_NONE_TITLE = "Crash caused by the missing console (.{attr})"
    FINDING_STREAMS_NONE_DETAIL = (
        "Some code called sys.stdout or sys.stderr, which are None in a windowed "
        "app. Turn the console back on, or add this code at the top of your program."
    )
    FINDING_DLL_LOAD_FAILED_TITLE = "A DLL failed to load while importing “{module}”"
    FINDING_DLL_LOAD_FAILED_DETAIL = (
        "A binary file that “{package}” needs was not bundled. The fix collects its "
        "binaries; if the error persists, the target machine may need the Visual "
        "C++ Redistributable."
    )
    FINDING_MULTIPLE_QT_BINDINGS_BUILD_TITLE = "Build stopped: more than one Qt binding ({bindings})"
    FINDING_MULTIPLE_QT_BINDINGS_BUILD_DETAIL = (
        "PyInstaller does not support more than one Qt binding in an app. The fix "
        "excludes {drop}."
    )
    FINDING_ADD_DATA_MISSING_TITLE = "Extra file not found: {path}"
    FINDING_ADD_DATA_MISSING_DETAIL = (
        "An --add-data option points to a path that doesn't exist. Correct or "
        "remove it under “Extra PyInstaller arguments”."
    )
    FINDING_ICON_WRONG_FORMAT_TITLE = "Icon format of “{icon}” is not supported"
    FINDING_ICON_WRONG_FORMAT_DETAIL = (
        "Windows accepts .ico only. Convert the image with “🎨 Icon Studio” on the "
        "Main tab."
    )
    FINDING_FILE_LOCKED_TITLE = "“{path}” is locked"
    FINDING_FILE_LOCKED_DETAIL = (
        "Usually the previous build of the program is still running, or an "
        "antivirus is scanning it. Close the program and try again."
    )
    FINDING_RUNTIME_UNHANDLED_TITLE = "The EXE crashed with an unrecognised error"
    FINDING_RUNTIME_UNHANDLED_DETAIL = (
        "Last error: {error}\nThis isn't one of the known freezing problems — it "
        "may be a bug in the code itself. Try running the script with python to "
        "compare."
    )
    FINDING_WARN_MISSING_MODULE_TITLE = "PyInstaller could not find “{module}”, which your code imports"
    FINDING_WARN_MISSING_MODULE_DETAIL = (
        "Listed in PyInstaller's warnings file. If it is a third-party library, "
        "install it into the build environment."
    )

    # ── 1.3: icon studio ──
    BTN_ICON_STUDIO = "🎨"
    ICON_STUDIO_TITLE = "🎨 Icon Studio"
    ICON_STUDIO_HINT = (
        "Create a real .ico with every size Windows asks for (16 to 256) from an "
        "image, or from your program's initials."
    )
    ICON_STUDIO_FROM_IMAGE = "From image"
    ICON_STUDIO_FROM_TEXT = "From letters"
    ICON_STUDIO_CHOOSE_IMAGE = "📂 Choose image"
    ICON_STUDIO_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.svg *.webp);;All Files (*.*)"
    ICON_STUDIO_TEXT_LABEL = "Text (one or two letters):"
    ICON_STUDIO_COLOR = "🎨 Background colour"
    ICON_STUDIO_SHAPE_LABEL = "Shape:"
    ICON_STUDIO_SHAPE_ROUNDED = "Rounded square"
    ICON_STUDIO_SHAPE_CIRCLE = "Circle"
    ICON_STUDIO_SHAPE_SQUARE = "Square"
    ICON_STUDIO_PREVIEW = "Preview:"
    ICON_STUDIO_SAVE = "💾 Save and use icon"
    ICON_STUDIO_SAVE_DIALOG = "Save icon"
    ICON_STUDIO_ICO_FILTER = "Icon Files (*.ico)"
    ICON_STUDIO_NOTHING = "Choose an image or type some text first"
    ICON_STUDIO_BAD_IMAGE = "The image could not be opened"
    ICON_STUDIO_SAVE_FAIL = "Could not save the icon: {error}"
    LOG_ICON_STUDIO_SAVED = "🎨 Icon created ({sizes}): {path}"

    # ── 1.4: build environment, size lab, build report, sandbox ──
    # "&&": a single "&" in a tab title is a keyboard-mnemonic marker.
    TAB_SIZE = "⚖️ Size && Environment"
    GROUP_BUILD_ENV = "🧪 Build environment"
    ENV_HINT = (
        "PyInstaller bundles whatever it finds installed, so building from a "
        "Python full of libraries bloats the EXE. An isolated environment holds "
        "only what your project imports."
    )
    ENV_MODE_CURRENT_FMT = "Current Python ({version})"
    ENV_MODE_ISOLATED = "Isolated environment for this project (recommended: smaller EXE, reproducible builds)"
    ENV_BASE_PYTHON_LABEL = "Python to create it from:"
    ENV_BASE_PYTHON_PLACEHOLDER = "Leave empty to use the current Python"
    DIALOG_CHOOSE_PYTHON = "Choose a Python interpreter"
    DIALOG_FILTER_PYTHON = "Python (python.exe python python3*);;All Files (*)"
    ENV_STATUS_NONE = "Environment: not created yet"
    ENV_STATUS_FMT = "Environment: Python {version} · {size}\n{path}"
    ENV_STATUS_NO_SOURCE = "Choose a source file first"
    ENV_REQUIREMENTS_FMT = "Will install: {items}"
    ENV_REQ_FROM_LOCK = "lock file {file} (exact versions)"
    ENV_REQ_FROM_FILE = "{file}"
    ENV_REQ_NONE = "no third-party packages — PyInstaller only"
    ENV_UV_NOTE = "⚡ uv will be used to create the environment faster"
    BTN_ENV_CREATE = "🔧 Create / update environment"
    BTN_ENV_RECREATE = "♻️ Recreate from scratch"
    BTN_ENV_LOCK = "🔒 Save lock file"
    BTN_ENV_LOCK_TIP = (
        "Saves the exact package versions to p2e-build.lock next to your project, "
        "so the very same environment can be rebuilt on any machine."
    )
    BTN_ENV_DELETE = "🗑️ Delete environment"
    MSG_ENV_CONFIRM = (
        "These commands will run (packages are downloaded, so this needs an "
        "internet connection):\n\n{commands}\n\nContinue?"
    )
    MSG_ENV_DELETE_CONFIRM = "Delete this project's isolated environment ({size})?"
    MSG_ENV_NEEDED = (
        "You chose to build in an isolated environment, but it has not been "
        "created yet.\nCreate it now and then build?"
    )
    LOG_ENV_START = "🧪 Creating the build environment: {path}"
    LOG_ENV_STEP = "▶ {cmd}"
    LOG_ENV_RETRY_SINGLE = "⚠️ The combined install failed — retrying one package at a time"
    LOG_ENV_PACKAGE_FAILED = "❌ Could not install: {name}"
    LOG_ENV_DONE = "✅ Build environment ready"
    LOG_ENV_DONE_PARTIAL = (
        "⚠️ Environment ready, but these could not be installed: {names} — add "
        "them to requirements.txt under their real PyPI names"
    )
    LOG_ENV_FAILED = "❌ Creating the environment failed: {error}"
    LOG_ENV_DELETED = "🗑️ Build environment deleted"
    LOG_ENV_LOCK_SAVED = "🔒 Lock file saved: {path}"
    LOG_ENV_LOCK_FAILED = "❌ Could not save the lock file: {error}"
    LOG_ENV_PYTHON = "🐍 Building with: {python}"
    ERR_ENV_PYTHON_MISSING = "Python interpreter not found: {path}"

    GROUP_SIZE = "📏 Size lab — last build"
    SIZE_NONE = "Build your project to see what is inside the EXE and how big each library is."
    SIZE_SUMMARY_FMT = "On disk: {disk} · contents before compression: {content}"
    SIZE_COMPARE_FMT = "Compared with the previous build ({previous}): {change}"
    SIZE_COL_PACKAGE = "Library"
    SIZE_COL_SIZE = "Size"
    SIZE_COL_SHARE = "Share"
    SIZE_GROUP_RUNTIME = "Python interpreter and runtime"
    SIZE_GROUP_STDLIB = "Python standard library"
    SIZE_GROUP_SCRIPT = "Your code"
    SIZE_INDIRECT_FMT = (
        "💡 {size} comes from libraries your code doesn't import directly ({names}). "
        "Many are real dependencies, but building in an isolated environment sheds "
        "the ones pulled in only because they were installed."
    )
    SIZE_ONEFILE_SLOW_FMT = (
        "🐢 A {size} one-file EXE unpacks itself on every launch, so it starts "
        "slowly. Folder mode with an installer starts instantly."
    )
    GROUP_SIZE_SUGGESTIONS = "✂️ Slimming suggestions"
    SIZE_SUGGESTIONS_NONE = "No suggestions — no known removable libraries are in the EXE."
    SIZE_SUGGESTIONS_HINT = (
        "Libraries inside the EXE that your code doesn't import. Excluding them is "
        "usually safe, and the Project Doctor catches any error after the rebuild."
    )
    BTN_SIZE_APPLY = "✅ Exclude selected"
    BTN_SIZE_APPLY_REBUILD = "🔁 Exclude and rebuild"
    BTN_SIZE_REFRESH = "🔄 Analyze last build"
    LOG_SIZE_SUMMARY = "📏 Size: {disk} — details on the Size & Environment tab"

    GROUP_REPORT = "📄 Build report"
    REPORT_AUTO = "Write an HTML report after every successful build"
    BTN_REPORT_OPEN = "📄 Open last report"
    LOG_REPORT_SAVED = "📄 Build report: {path}"
    LOG_REPORT_FAILED = "❌ Could not write the report: {error}"
    REPORT_TITLE = "Build report"
    REPORT_DETAILS = "Details"
    REPORT_RESULT = "Result"
    REPORT_SUCCESS = "Succeeded"
    REPORT_FAILED = "Failed"
    REPORT_SIZE_ON_DISK = "Size on disk"
    REPORT_CONTENTS = "Contents before compression"
    REPORT_DURATION = "Build time"
    REPORT_PREVIOUS = "Versus previous build"
    REPORT_APP = "Application"
    REPORT_DATE = "Date"
    REPORT_SOURCE = "Source file"
    REPORT_OUTPUT = "Output"
    REPORT_MODE = "Mode"
    REPORT_ONEFILE = "One file"
    REPORT_ONEDIR = "Folder"
    REPORT_ENVIRONMENT = "Build environment"
    REPORT_ENV_ISOLATED = "Isolated environment"
    REPORT_ENV_CURRENT = "Current Python"
    REPORT_PYTHON = "Python"
    REPORT_PYINSTALLER = "PyInstaller"
    REPORT_PLATFORM = "Platform"
    REPORT_BREAKDOWN = "What's inside"
    REPORT_PACKAGE = "Library"
    REPORT_SIZE = "Size"
    REPORT_SHARE = "Share"
    REPORT_LARGEST_FILES = "Largest files"
    REPORT_FINDINGS = "Project Doctor notes"
    REPORT_OPTIONS = "PyInstaller options"
    REPORT_NONE = "None"
    REPORT_GENERATOR_FMT = "Generated by {app} {version}"

    BTN_SANDBOX = "🧊 Test in Windows Sandbox"
    BTN_SANDBOX_TIP = (
        "Runs the EXE on a completely clean Windows (no Python, none of your "
        "libraries) to catch “works on my machine” problems."
    )
    SANDBOX_UNAVAILABLE = (
        "Windows Sandbox is not available on this machine (it needs Windows 10/11 "
        "Pro or Enterprise with the feature enabled).\n\nTo test on a clean system: "
        "copy\n{path}\nto a machine or VM without Python and run it there."
    )
    MSG_SANDBOX_NO_BUILD = "Build the project first."
    LOG_SANDBOX_WRITTEN = "🧊 Windows Sandbox file: {path}"

    FINDING_SIZE_EXCLUDE_CANDIDATE_TITLE = "Excluding “{package}” saves {size}"
    FINDING_SIZE_EXCLUDE_CANDIDATE_DETAIL = (
        "Your code doesn't import {package}, but another library pulled it into the "
        "EXE. If that library really needs it, the diagnostics will show the error "
        "after the rebuild."
    )
    FINDING_ENV_NOT_CREATED_TITLE = "The isolated environment has not been created yet"
    FINDING_ENV_NOT_CREATED_DETAIL = (
        "You'll be asked to create it when you build, or create it now on the Size "
        "& Environment tab. Until then, which packages it holds can't be checked."
    )


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
