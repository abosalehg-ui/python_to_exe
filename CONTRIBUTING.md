# Contributing Guide

شكراً لاهتمامك بالمساهمة في هذا المشروع! / Thanks for your interest in contributing!

This guide is bilingual: Arabic first, then English.

---

## بالعربية

### إعداد البيئة

```bash
git clone https://github.com/abosalehg-ui/python_to_exe.git
cd python_to_exe
pip install -r requirements-dev.txt
```

### تشغيل الاختبارات والـ Lint

```bash
pytest tests/                       # كل الاختبارات
ruff check py2exe_gui/ tests/       # فحص الكود
```

### إرشادات قبل فتح Pull Request

1. **اكتب اختباراً** لأي وظيفة نواة جديدة (في `py2exe_gui/core/`).
2. **حافظ على فصل النواة عن الواجهة**: لا تستورد `PyQt5` داخل `py2exe_gui/core/`.
3. **استعمل النصوص من `strings.py`** — لا تكتب نصوص عربية أو إنجليزية مباشرة في الكود.
4. **عند إضافة نص جديد**: أضفه في `class Ar` و `class En` معاً. الاختبارات ستفشل إن نقص أحدهما.
5. **شغّل `pytest` و `ruff`** قبل الـ commit. CI يفشل بدونهما.
6. **رسالة الـ commit**: قصيرة، تصف الـ "لماذا" لا الـ "ماذا".

### إضافة قالب جديد

1. أضف مدخلاً في `TEMPLATES` في `py2exe_gui/templates.py`
2. أضف مفاتيح في `_NAME_ATTR` و `_DESC_ATTR`
3. أضف الترجمات في `class Ar` و `class En` في `strings.py`
4. `pytest tests/test_templates.py` يجب أن يمرّ

### إضافة لغة جديدة

1. أنشئ `class Xx` في `strings.py` بكل المفاتيح الموجودة في `Ar`/`En`
2. سجّلها في `LOCALES = {"ar": Ar, "en": En, "xx": Xx}`
3. أضف `LOCALE_NATIVE_NAMES["xx"] = "اسمها الأصلي"`
4. حدّد `LOCALE_LAYOUT["xx"]` (`"rtl"` أو `"ltr"`)

### الإبلاغ عن مشكلة

استخدم قالب Issue المناسب على GitHub.

---

## English

### Development Setup

```bash
git clone https://github.com/abosalehg-ui/python_to_exe.git
cd python_to_exe
pip install -r requirements-dev.txt
```

### Running Tests and Linter

```bash
pytest tests/                       # all tests
ruff check py2exe_gui/ tests/       # lint check
```

### Guidelines Before Opening a PR

1. **Write a test** for any new core function (in `py2exe_gui/core/`).
2. **Keep UI and core separate** — never `import PyQt5` from `py2exe_gui/core/`.
3. **Use strings from `strings.py`** — no hard-coded Arabic or English in the code.
4. **When adding a new string**: add it to both `class Ar` and `class En`. Tests fail if either is missing.
5. **Run `pytest` and `ruff`** before committing. CI rejects either failure.
6. **Commit message**: short, describes "why" not "what".

### Adding a New Template

1. Add an entry to `TEMPLATES` in `py2exe_gui/templates.py`
2. Add keys to `_NAME_ATTR` and `_DESC_ATTR`
3. Add translations to both `class Ar` and `class En` in `strings.py`
4. `pytest tests/test_templates.py` must pass

### Adding a New Language

1. Create a `class Xx` in `strings.py` with all the keys from `Ar`/`En`
2. Register it in `LOCALES = {"ar": Ar, "en": En, "xx": Xx}`
3. Add `LOCALE_NATIVE_NAMES["xx"] = "Native name"`
4. Set `LOCALE_LAYOUT["xx"]` (`"rtl"` or `"ltr"`)

The `test_en_defines_every_public_attribute_of_ar` and its sibling tests
will catch any missing keys.

### Architecture Rules

- **No business logic in UI files.** UI calls into `py2exe_gui/core/`.
- **Core modules must be pure** — no Qt, no implicit global state.
  (Subprocess for `run_smoke_test` is the only exception.)
- **Tests live in `tests/` only** and must not touch the UI.

### Filing a Bug

Use the appropriate Issue template on GitHub. Please include:

- Your OS and Python version
- The PyInstaller version
- The exact command preview (Ctrl+P → Copy)
- Full log output (Export Log button)
