<div align="center">

# 🐍 Python to EXE Converter

### أداة احترافية لتحويل تطبيقات بايثون إلى ملفات تنفيذية

![Version](https://img.shields.io/badge/الإصدار-1.0.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge&logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/PyQt5-GUI-orange?style=for-the-badge&logo=qt&logoColor=white)
![Tests](https://img.shields.io/badge/الاختبارات-160_passing-brightgreen?style=for-the-badge)
![Languages](https://img.shields.io/badge/اللغات-عربي_+_English-purple?style=for-the-badge)
![License](https://img.shields.io/badge/الرخصة-All%20Rights%20Reserved-red?style=for-the-badge)

<br>

**حوّل أي ملف Python إلى ملف EXE بضغطة زر — بواجهة عربية كاملة، 11 قالب جاهز، توقيع رقمي، ومحرر metadata.**

[الميزات](#-الميزات) •
[التثبيت](#-التثبيت) •
[الاستخدام](#-الاستخدام) •
[القوالب](#-القوالب-الجاهزة) •
[خارطة الطريق](#-خارطة-الطريق) •
[المساهمة](#-المساهمة)

> 🇬🇧 **English:** see [README_EN.md](README_EN.md)

</div>

---

## 📖 نظرة عامة

**Python to EXE Converter** هي أداة احترافية مفتوحة المصدر لتحويل ملفات بايثون (`.py`) إلى ملفات تنفيذية (`.exe`) بدون أوامر سطر الأوامر.

تجمع الأداة بين سهولة الاستخدام (واجهة عربية/إنجليزية ثنائية الاتجاه) والقوة الكاملة لـ PyInstaller، مع إضافات احترافية مثل التوقيع الرقمي، محرر metadata، سجل البناءات السابقة، ومحلل تبعيات ذكي يعتمد على AST.

---

## ✨ الميزات

<table>
<tr>
<td width="50%">

### 🎨 الواجهة والتجربة
- ✅ واجهة عربية (RTL) + إنجليزية (LTR)
- ✅ سمة داكنة + سمة نهارية
- ✅ السحب والإفلات (Drag & Drop)
- ✅ معاينة الأمر قبل التنفيذ (Dry-run)
- ✅ تلوين السجل + بحث + تصدير
- ✅ 10+ اختصارات لوحة مفاتيح

</td>
<td width="50%">

### 🔍 محلل التبعيات الذكي
- ✅ كشف بـ AST (داخل الدوال والشروط)
- ✅ يكشف `__import__` و `importlib`
- ✅ استيراد من `requirements.txt`
- ✅ تصفية تلقائية للمكتبات القياسية

</td>
</tr>
<tr>
<td width="50%">

### 📝 metadata الاحترافية
- ✅ محرر Version Info (8 حقول)
- ✅ تضمين CompanyName، Copyright، Product
- ✅ تظهر في خصائص EXE في Windows
- ✅ توليد `version.txt` تلقائي

</td>
<td width="50%">

### 🚀 ميزات النشر
- ✅ شاشة بداية (Splash screen)
- ✅ Windows Manifest (DPI، UAC، OS)
- ✅ توقيع رقمي (signtool.exe)
- ✅ اختبار ما بعد البناء

</td>
</tr>
<tr>
<td width="50%">

### 🕓 سجل البناءات
- ✅ آخر 20 عملية بناء محفوظة
- ✅ استعادة الإعدادات بنقرة واحدة
- ✅ مدة كل بناء + نجاح/فشل

</td>
<td width="50%">

### 📦 PyInstaller Options
- ✅ ملف واحد أو مجلد
- ✅ مع/بدون Console
- ✅ أيقونة (.ico) + ملفات إضافية
- ✅ Hidden Imports + UPX + Optimize

</td>
</tr>
</table>

---

## 📥 التثبيت

### الطريقة الأولى: استنساخ المستودع

```bash
git clone https://github.com/abosalehg-ui/python_to_exe.git
cd python_to_exe
pip install -r requirements.txt
python python_to_exe.py
```

### الطريقة الثانية: كحزمة Python

```bash
git clone https://github.com/abosalehg-ui/python_to_exe.git
cd python_to_exe
pip install -e .
py2exe-gui
```

---

## 📋 المتطلبات

| المتطلب | الإصدار | الوصف |
|---------|---------|-------|
| Python | 3.8+ | لغة البرمجة |
| PyQt5 | 5.15+ | الواجهة الرسومية |
| PyInstaller | 5.0+ | محرك التحويل (يُثبَّت تلقائياً) |

---

## 🚀 الاستخدام

### الخطوات الأساسية:

```
1️⃣  افتح التطبيق: python python_to_exe.py
2️⃣  اسحب ملف .py على النافذة (أو استخدم زر 📂)
3️⃣  اختر قالباً من تبويب "القوالب" (اختياري)
4️⃣  املأ Version Info إن أردت metadata احترافية
5️⃣  فعّل ميزات النشر إن لزم (توقيع رقمي، splash، manifest)
6️⃣  Ctrl+P لمعاينة الأمر، Ctrl+B لبدء البناء 🚀
```

### الملف الناتج يظهر في `<مجلد الإخراج>/dist/`.

---

## ⌨️ اختصارات لوحة المفاتيح

| الاختصار | الإجراء |
|----------|--------|
| `Ctrl+O` | فتح ملف المصدر |
| `Ctrl+B` | بدء البناء |
| `Ctrl+Shift+B` | إلغاء البناء |
| `Ctrl+P` | معاينة الأمر (Dry-run) |
| `Ctrl+L` | مسح السجل |
| `Ctrl+E` | تصدير السجل |
| `Ctrl+S` | حفظ الإعدادات |
| `Ctrl+T` | تبديل السمة (داكن/نهاري) |
| `Ctrl+F` | تركيز على بحث السجل |
| `F5` | كشف المكتبات تلقائياً |

---

## 📑 التبويبات

| التبويب | المحتوى |
|--------|---------|
| **⚙️ الإعدادات الرئيسية** | ملف المصدر، الإخراج، الأيقونة، الخيارات الأساسية |
| **🔧 إعدادات متقدمة** | ملفات إضافية، Hidden Imports، استيراد من requirements، UPX، أوامر مخصصة |
| **📝 معلومات الإصدار** | CompanyName، FileDescription، FileVersion، ProductVersion، Copyright، إلخ |
| **🚀 النشر** | Splash، Manifest (DPI/UAC/OS)، التوقيع الرقمي، Smoke Test |
| **📋 القوالب** | 11 قالب جاهز + حفظ/تحميل الإعدادات + محدد اللغة |
| **🕓 سجل البناءات** | آخر 20 عملية مع استعادة الإعدادات |
| **ℹ️ حول البرنامج** | معلومات المطوّر والميزات |

---

## 🎯 القوالب الجاهزة

| القالب | النوع | المكتبات |
|--------|-------|----------|
| 🖥️ **تطبيق GUI** | PyQt5 / Tkinter | PyQt5.QtWidgets, QtCore, QtGui |
| ⌨️ **تطبيق Console** | سطر أوامر | — |
| 🌐 **تطبيق ويب** | Flask / Django | flask, jinja2, werkzeug |
| 📊 **تطبيق بيانات** | Pandas / NumPy | pandas, numpy, openpyxl |
| 🎮 **لعبة** | Pygame | pygame |
| ⚡ **FastAPI** | REST API | fastapi, uvicorn, starlette, pydantic |
| 📈 **Streamlit** | لوحة بيانات | streamlit, altair, click, tornado |
| 📱 **Kivy** | متعدد المنصات | kivy |
| 🤖 **بوت Discord** | discord.py | discord, aiohttp |
| 🛠️ **CLI Click** | أداة سطر أوامر | click |
| ⚙️ **مخصص** | إعدادات يدوية | حسب اختيارك |

---

## 🔐 التوقيع الرقمي

في تبويب "🚀 النشر" يمكن توقيع الـ EXE الناتج تلقائياً بعد البناء:

- اختيار ملف الشهادة `.pfx`
- إدخال كلمة المرور (مخفية في الحقل، **لا تُكتب أبداً في السجل**)
- خادم Timestamp (افتراضي: `http://timestamp.digicert.com`)
- وصف اختياري للتوقيع

> 💡 يستخدم `signtool.exe` المدمج مع Windows SDK. تأكد من وجوده في الـ PATH.

---

## 📂 هيكل المشروع

```
python_to_exe/
├── python_to_exe.py            # نقطة الدخول الرفيعة (23 سطر)
├── pyproject.toml              # تعريف الحزمة
├── requirements.txt
├── requirements-dev.txt
├── README.md  /  README_EN.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── IDEAS.md                    # خارطة الطريق الشاملة
│
├── py2exe_gui/                 # الحزمة الرئيسية
│   ├── app.py                  # bootstrap
│   ├── constants.py
│   ├── strings.py              # كل النصوص (Ar + En) + locale proxy
│   ├── styles.py               # السمات الداكنة والنهارية
│   ├── templates.py            # 11 قالب
│   │
│   ├── core/                   # النواة (بلا PyQt5، قابلة للاختبار)
│   │   ├── builder.py
│   │   ├── config.py
│   │   ├── dependency_analyzer.py    # AST + requirements
│   │   ├── version_info.py           # toGetMetadata
│   │   ├── manifest_generator.py     # XML للويندوز
│   │   ├── code_signer.py            # signtool builder
│   │   ├── smoke_test.py             # post-build
│   │   ├── build_history.py
│   │   └── log_formatter.py
│   │
│   └── ui/                     # واجهة PyQt5
│       ├── main_window.py
│       ├── conversion_thread.py
│       └── dialogs.py
│
├── tests/                      # 160 اختبار وحدة
└── .github/
    ├── workflows/ci.yml        # pytest + ruff
    └── ISSUE_TEMPLATE/
```

---

## 🧪 الاختبارات والـ CI

```bash
pip install -r requirements-dev.txt
pytest tests/                              # 160 اختبار
ruff check py2exe_gui/ tests/             # فحص الكود
pytest --cov=py2exe_gui.core --cov-report=term
```

**GitHub Actions** يُشغّل الاختبارات على Python 3.9 – 3.12 + ruff عند كل push.

---

## 🌐 اللغات والسمات

- **اللغات:** العربية (RTL، افتراضي) + الإنجليزية (LTR). التبديل من تبويب القوالب → اللغة.
- **السمات:** داكنة (Catppuccin Mocha) + نهارية (Catppuccin Latte). التبديل بـ Ctrl+T.
- **الإضافة:** انظر [CONTRIBUTING.md](CONTRIBUTING.md) لإضافة لغة أو سمة جديدة.

---

## 🐛 حل المشاكل

<details>
<summary><b>❌ ModuleNotFoundError عند تشغيل EXE</b></summary>

اضغط **F5** أو زر "🔍 كشف تلقائي" في تبويب "إعدادات متقدمة". المحلل بـ AST يكشف الاستيرادات داخل الدوال وكتل try/except و `__import__` و `importlib.import_module`. للاستيرادات الديناميكية النادرة، أضفها يدوياً.

</details>

<details>
<summary><b>❌ الملف الناتج كبير جداً</b></summary>

- عطّل `--onefile` (استخدم وضع المجلد)
- فعّل `--strip` لإزالة معلومات التنقيح
- استخدم UPX للضغط (يتطلب UPX في PATH)
- استثناء الوحدات غير المستخدمة عبر "أوامر إضافية": `--exclude-module X`

</details>

<details>
<summary><b>❌ مكافحات الفيروسات تعتبر الـ EXE خبيثاً</b></summary>

مشكلة معروفة في PyInstaller. حلول:
- **وقّع الـ EXE رقمياً** (تبويب النشر) - يقلل false positives بشكل ملحوظ
- تجنّب `--upx` للبيئات الحساسة
- انشر عبر قنوات موثوقة (Microsoft Store، GitHub Releases)

</details>

<details>
<summary><b>❌ خطأ في الأيقونة</b></summary>

- استخدم ملف `.ico` متعدد الأحجام (وليس PNG معاد التسمية)
- لتحويل PNG: `convert in.png -define icon:auto-resize=256,128,64,48,32,16 out.ico`

</details>

<details>
<summary><b>❌ التطبيق لا يجد الملفات الإضافية</b></summary>

في الكود استخدم `sys._MEIPASS`:
```python
import sys, os
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(__file__)
```

</details>

---

## 📋 خارطة الطريق

اطّلع على [IDEAS.md](IDEAS.md) للخارطة الكاملة. الحالة:

- ✅ **المرحلة 1:** تقسيم الكود، اختبارات، CI، packaging
- ✅ **المرحلة 2:** تحسينات UX (drag/drop، dry-run، سمات، اختصارات)
- ✅ **المرحلة 3:** تعدد اللغات (عربي + إنجليزي)
- ✅ **المرحلة 4:** محلل تبعيات AST + Version Info + Build History
- ✅ **المرحلة 5:** Splash + Manifest + Code Signing + Smoke Test
- ✅ **المرحلة 6:** 5 قوالب جديدة + وثائق إنجليزية
- ⏳ **المرحلة 7 (مستقبلية):** التحديث الذاتي، Dashboard، PyQt6، VirusTotal

---

## 🤝 المساهمة

نرحّب بالمساهمات! انظر [CONTRIBUTING.md](CONTRIBUTING.md) للتفاصيل:

- إعداد بيئة التطوير
- قواعد بنية الكود (لا PyQt5 في `core/`)
- كيفية إضافة قالب أو لغة جديدة
- إرشادات commit و pull request

للإبلاغ عن مشكلة أو اقتراح ميزة، استخدم قوالب Issues على GitHub.

---

## 📚 وثائق إضافية

- 📖 [README_EN.md](README_EN.md) — English documentation
- 🤝 [CONTRIBUTING.md](CONTRIBUTING.md) — دليل المساهمة (Ar/En)
- 📋 [CHANGELOG.md](CHANGELOG.md) — تاريخ التغييرات لكل مرحلة
- 💡 [IDEAS.md](IDEAS.md) — خارطة الطريق الشاملة والأفكار المستقبلية

---

## 👨‍💻 المطور

<div align="center">

**عبدالكريم العبود**

[![Email](https://img.shields.io/badge/Email-abo.saleh.g%40gmail.com-red?style=for-the-badge&logo=gmail&logoColor=white)](mailto:abo.saleh.g@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-abosalehg--ui-black?style=for-the-badge&logo=github&logoColor=white)](https://github.com/abosalehg-ui)

</div>

---

## 📄 الرخصة

```
© 2025 [Python to EXE Converter] - All Rights Reserved

تطوير: عبدالكريم العبود
البريد: abo.saleh.g@gmail.com
```

---

<div align="center">

### ⭐ إذا أعجبك المشروع، لا تنسَ إعطاءه نجمة!

<br>

**صُنع بـ ❤️ في السعودية 🇸🇦**

</div>
