"""p2e_runtime: log redirection, crash reporter, single-instance guard."""

import os
import sys
import threading

import pytest

from p2e_runtime import _native, crash, logs, single_instance

# ── Log redirection ────────────────────────────────────────────────────────


@pytest.fixture
def no_streams(monkeypatch):
    """A windowed EXE: every standard stream is None.

    Returned as a function to call inside the test: pytest re-installs its
    own capture streams between fixture setup and the test body.
    """
    monkeypatch.setattr(logs, "_stream", None)

    def clear():
        for name in ("stdout", "stderr", "__stdout__", "__stderr__"):
            monkeypatch.setattr(sys, name, None)

    yield clear
    if logs._stream is not None:
        logs._stream.close()


def test_missing_streams_go_to_the_log(no_streams, tmp_path):
    no_streams()
    path = logs.redirect("My App", "1.0", base_dir=str(tmp_path))
    assert path == os.path.join(str(tmp_path), "logs", "My App.log")
    print("from print")
    sys.stdout.write("from write\n")
    sys.stderr.write("from stderr\n")
    sys.stdout.buffer.write("bytes ✓\n".encode())
    sys.stdout.flush()
    content = open(path, encoding="utf-8").read()
    assert "My App 1.0 started" in content
    for line in ("from print", "from write", "from stderr", "bytes ✓"):
        assert line in content
    # PyInstaller's bootloader flushes sys.__stdout__ at exit: it must exist.
    assert sys.__stdout__ is sys.stdout and sys.__stderr__ is sys.stderr


def test_existing_console_is_left_alone(monkeypatch, tmp_path):
    monkeypatch.setattr(logs, "_stream", None)
    out, err = sys.stdout, sys.stderr
    assert logs.redirect("App", base_dir=str(tmp_path)) is None
    assert sys.stdout is out and sys.stderr is err
    assert not os.path.exists(tmp_path / "logs")


def test_only_the_missing_stream_is_replaced(monkeypatch, tmp_path):
    monkeypatch.setattr(logs, "_stream", None)
    monkeypatch.setattr(sys, "stderr", None)
    out = sys.stdout
    assert logs.redirect("App", base_dir=str(tmp_path))
    assert sys.stdout is out
    assert isinstance(sys.stderr, logs.RotatingLogStream)
    logs._stream.close()


def test_stream_behaves_like_a_text_file(tmp_path):
    stream = logs.RotatingLogStream(str(tmp_path / "a.log"))
    assert stream.writable() and not stream.isatty()
    assert stream.encoding == "utf-8" and stream.errors == "replace"
    assert stream.write(123) == 3
    stream.close()
    assert open(tmp_path / "a.log").read() == "123"


def test_rotation_keeps_the_configured_backups(tmp_path):
    path = str(tmp_path / "app.log")
    stream = logs.RotatingLogStream(path, max_bytes=1024, backups=2)
    for index in range(10):
        stream.write(f"{index}" * 600 + "\n")
    stream.close()
    files = sorted(os.listdir(tmp_path))
    assert files == ["app.log", "app.log.1", "app.log.2"]
    assert all(os.path.getsize(tmp_path / f) <= 1024 for f in files)
    # Newest in app.log, the one before it in .1.
    assert open(path).read().startswith("9")
    assert open(path + ".1").read().startswith("8")


def test_rotation_without_backups_starts_over(tmp_path):
    path = str(tmp_path / "app.log")
    stream = logs.RotatingLogStream(path, max_bytes=1024, backups=0)
    stream.write("a" * 1000)
    stream.write("b" * 100)
    stream.close()
    assert os.listdir(tmp_path) == ["app.log"]
    assert open(path).read() == "b" * 100


def test_unwritable_log_never_raises(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    stream = logs.RotatingLogStream(str(blocker / "sub" / "app.log"))
    assert stream.write("lost") == 4  # swallowed, not raised


def test_writes_from_threads_do_not_interleave_lines(tmp_path):
    path = str(tmp_path / "t.log")
    stream = logs.RotatingLogStream(path, max_bytes=10 * 1024 * 1024)

    def worker(tag):
        for _ in range(200):
            stream.write(f"{tag * 40}\n")

    threads = [threading.Thread(target=worker, args=(c,)) for c in "abcd"]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    stream.close()
    lines = open(path).read().splitlines()
    assert len(lines) == 800
    assert all(len(set(line)) == 1 for line in lines)


# ── Crash reporter ─────────────────────────────────────────────────────────


def _exc_info(message="boom"):
    try:
        raise ValueError(message)
    except ValueError:
        return sys.exc_info()


def test_report_content(monkeypatch):
    monkeypatch.setenv("SECRET_TOKEN", "do-not-leak-1234")
    text = crash.format_report(*_exc_info(), app_name="Tool", app_version="2.1.0",
                               thread_name="Worker", now=0)
    assert text.startswith("Crash report: Tool 2.1.0\n")
    assert "Time (UTC): 1970-01-01T00:00:00Z" in text
    assert "OS: " in text and "Python: " in text and "Frozen: no" in text
    assert "Thread: Worker" in text
    assert "ValueError: boom" in text and "Traceback (most recent call last)" in text
    # No environment, no user or machine name, no executable path.
    assert "do-not-leak-1234" not in text
    assert os.path.expanduser("~") not in text.split("Traceback")[0]
    assert sys.executable not in text


def test_reports_never_overwrite_each_other(tmp_path):
    first = crash.write_report("one", str(tmp_path), now=0)
    second = crash.write_report("two", str(tmp_path), now=0)
    assert first != second
    assert open(first).read() == "one" and open(second).read() == "two"


@pytest.fixture
def reporter_factory(monkeypatch, tmp_path):
    made = []

    def make(**options):
        shown, opened = [], []
        answer = options.pop("_answer", True)

        def show(text, title, kind, yes_no, rtl):
            shown.append((text, title, kind, yes_no, rtl))
            return answer

        reporter = crash.CrashReporter(
            "Tool", "1.0", directory=str(tmp_path / "crashes"), show=show,
            open_url=opened.append, **options,
        )
        reporter.shown, reporter.opened = shown, opened
        made.append(reporter)
        return reporter

    hook, thread_hook = sys.excepthook, threading.excepthook
    yield make
    sys.excepthook, threading.excepthook = hook, thread_hook


def test_excepthook_saves_a_report_and_tells_the_user(reporter_factory, capsys):
    reporter = reporter_factory()
    reporter.install()
    assert sys.excepthook == reporter.excepthook
    sys.excepthook(*_exc_info("main thread"))
    assert "ValueError: main thread" in capsys.readouterr().err  # default hook still ran
    assert os.path.isfile(reporter.last_report)
    assert "main thread" in open(reporter.last_report).read()
    text, title, kind, yes_no, _rtl = reporter.shown[0]
    assert reporter.last_report in text and "Tool" in title
    assert kind == "error" and yes_no is False
    reporter.uninstall()


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_thread_exceptions_are_reported(reporter_factory):
    reporter = reporter_factory(dialog=False)
    reporter.install()
    worker = threading.Thread(target=lambda: 1 / 0, name="Downloader")
    worker.start()
    worker.join()
    assert reporter.last_report
    content = open(reporter.last_report).read()
    assert "Thread: Downloader" in content and "ZeroDivisionError" in content
    assert reporter.shown == []
    reporter.uninstall()


def test_keyboard_interrupt_and_system_exit_are_not_crashes(reporter_factory):
    reporter = reporter_factory()
    reporter._previous_hook = lambda *a: None
    try:
        raise KeyboardInterrupt
    except KeyboardInterrupt:
        reporter.excepthook(*sys.exc_info())
    assert reporter.last_report == ""

    class Args:
        exc_type, exc_value, exc_traceback, thread = SystemExit, SystemExit(), None, None

    reporter._previous_thread_hook = lambda args: None
    reporter.thread_excepthook(Args)
    assert reporter.last_report == ""


def test_support_url_opens_only_when_the_user_says_yes(reporter_factory):
    yes = reporter_factory(support_url="https://help.example/report", _answer=True)
    yes.report(*_exc_info())
    assert yes.shown[0][3] is True  # a Yes/No question
    assert yes.opened == ["https://help.example/report"]

    no = reporter_factory(support_url="https://help.example/report", _answer=False)
    no.report(*_exc_info())
    assert no.opened == []


def test_unsafe_support_url_is_dropped(reporter_factory):
    reporter = reporter_factory(support_url="file:///etc/passwd")
    assert reporter.support_url == ""
    assert crash.is_safe_support_url("mailto:help@example.com")
    assert not crash.is_safe_support_url("javascript:alert(1)")


def test_without_a_native_dialog_stderr_gets_the_path_but_no_link_opens(
        reporter_factory, capsys):
    reporter = reporter_factory(support_url="https://help.example")
    reporter._show = lambda *a: None  # Linux/macOS: no native dialog
    path = reporter.report(*_exc_info())
    err = capsys.readouterr().err
    assert path in err and "https://help.example" in err
    assert reporter.opened == []


def test_unwritable_crash_folder_still_tells_the_user(reporter_factory, tmp_path, capsys):
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    reporter = reporter_factory()
    reporter.directory = str(blocker / "crashes")
    assert reporter.report(*_exc_info()) == ""
    assert "could not save the crash report" in capsys.readouterr().err
    assert reporter.shown  # the dialog still appears


def test_custom_texts_are_filled(reporter_factory):
    reporter = reporter_factory(title="{app}!", message="Saved: {path}", rtl=True)
    path = reporter.report(*_exc_info())
    text, title, _kind, _yes_no, rtl = reporter.shown[0]
    assert title == "Tool!" and text == f"Saved: {path}" and rtl is True


def test_module_install_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(crash, "_reporter", None)
    hook, thread_hook = sys.excepthook, threading.excepthook
    try:
        first = crash.install("Tool", directory=str(tmp_path), dialog=False)
        assert crash.install("Other") is first
    finally:
        sys.excepthook, threading.excepthook = hook, thread_hook


# ── Native dialogs ─────────────────────────────────────────────────────────


def test_native_dialog_flags_and_answers(monkeypatch):
    calls = []

    def fake(text, title, flags):
        calls.append(flags)
        return _native.IDYES

    monkeypatch.setattr(_native, "windows_message_box", fake)
    assert _native.show("t", "x", _native.KIND_QUESTION, yes_no=True, rtl=True,
                        platform="win32") is True
    flags = calls[-1]
    assert flags & _native.MB_YESNO and flags & _native.MB_ICONQUESTION
    assert flags & _native.MB_RTLREADING and flags & _native.MB_RIGHT
    assert _native.show("t", "x", platform="win32") is True
    assert not calls[-1] & _native.MB_YESNO

    monkeypatch.setattr(_native, "windows_message_box", lambda *a: 7)  # IDNO
    assert _native.show("t", "x", yes_no=True, platform="win32") is False
    assert _native.show("t", "x", platform="linux") is None

    def broken(*_a):
        raise OSError("no user32")

    monkeypatch.setattr(_native, "windows_message_box", broken)
    assert _native.show("t", "x", platform="win32") is None


def test_to_stderr_without_stderr(monkeypatch):
    monkeypatch.setattr(sys, "stderr", None)
    assert _native.to_stderr("x") is False


# ── Single instance ────────────────────────────────────────────────────────


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX lock file")
def test_posix_lock_admits_one_holder(tmp_path):
    first = single_instance.acquire("Tool", lock_dir=str(tmp_path))
    assert first is not None and first.kind == "file"
    assert open(first.path).read() == str(os.getpid())
    # A second open file description conflicts, exactly as another process would.
    assert single_instance.acquire("Tool", lock_dir=str(tmp_path)) is None
    first.release()
    again = single_instance.acquire("Tool", lock_dir=str(tmp_path))
    assert again is not None
    again.release()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX lock file")
def test_posix_lock_is_released_when_the_holder_dies(tmp_path):
    import subprocess

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    holder = subprocess.Popen(
        [sys.executable, "-c",
         "import sys, time; from p2e_runtime import single_instance as s; "
         f"lock = s.acquire('Tool', lock_dir={str(tmp_path)!r}); "
         "print('held' if lock else 'busy', flush=True); time.sleep(30)"],
        cwd=root, stdout=subprocess.PIPE, text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "held"
        assert single_instance.acquire("Tool", lock_dir=str(tmp_path)) is None
    finally:
        holder.kill()
        holder.wait()
    lock = single_instance.acquire("Tool", lock_dir=str(tmp_path))
    assert lock is not None
    lock.release()


class FakeKernel32:
    """Stands in for CreateMutexW/GetLastError/CloseHandle."""

    def __init__(self):
        self.names, self.closed, self._handle = {}, [], 100

    def create_mutex(self, name):
        self._handle += 1
        existed = name in self.names
        self.names.setdefault(name, self._handle)
        return self._handle, single_instance.ERROR_ALREADY_EXISTS if existed else 0

    def close(self, handle):
        self.closed.append(handle)


def test_windows_mutex_branch():
    api = FakeKernel32()
    first = single_instance.acquire("My App", platform="win32", api=api)
    assert first.kind == "mutex"
    assert list(api.names) == ["Local\\p2e-My App"]
    second = single_instance.acquire("My App", platform="win32", api=api)
    assert second is None
    assert api.closed == [102]  # the duplicate handle is closed at once
    first.release()
    assert api.closed == [102, 101]


def test_windows_mutex_failure_raises():
    class Failing(FakeKernel32):
        def create_mutex(self, name):
            return 0, 5  # NULL handle, ERROR_ACCESS_DENIED

    with pytest.raises(OSError):
        single_instance.acquire("x", platform="win32", api=Failing())


def test_second_copy_shows_the_message_and_exits(monkeypatch):
    monkeypatch.setattr(single_instance, "_lock", None)
    api = FakeKernel32()
    shown = []
    monkeypatch.setattr(_native, "windows_message_box",
                        lambda text, title, flags: shown.append((text, title)) or 1)
    single_instance.ensure_single_instance("Tool", "Tool", platform="win32", api=api)
    monkeypatch.setattr(single_instance, "_lock", None)
    with pytest.raises(SystemExit) as exited:
        single_instance.ensure_single_instance(
            "Tool", "Tool", message="{app} is busy", exit_code=4, platform="win32", api=api
        )
    assert exited.value.code == 4
    assert shown == [("Tool is busy", "Tool")]


def test_second_copy_message_goes_to_stderr_without_a_dialog(monkeypatch, tmp_path, capsys):
    if sys.platform == "win32":
        pytest.skip("POSIX lock file")
    monkeypatch.setattr(single_instance, "_lock", None)
    held = single_instance.acquire("Tool", lock_dir=str(tmp_path))
    try:
        with pytest.raises(SystemExit) as exited:
            single_instance.ensure_single_instance("Tool", "Tool", lock_dir=str(tmp_path))
        assert exited.value.code == 0
        assert "Tool is already running." in capsys.readouterr().err
    finally:
        held.release()


def test_ensure_returns_the_held_lock_when_called_twice(monkeypatch):
    monkeypatch.setattr(single_instance, "_lock", None)
    api = FakeKernel32()
    first = single_instance.ensure_single_instance("A", platform="win32", api=api)
    assert single_instance.ensure_single_instance("A", platform="win32", api=api) is first


def test_unattended_runs_get_no_dialog(monkeypatch):
    """The converter's smoke test sets this, so a crash dialog never hangs it."""
    monkeypatch.setattr(_native, "windows_message_box",
                        lambda *a: pytest.fail("a dialog was shown"))
    monkeypatch.setenv(_native.NO_DIALOGS_ENV, "1")
    assert _native.show("t", "x", platform="win32") is None
    monkeypatch.setenv(_native.NO_DIALOGS_ENV, "0")
    monkeypatch.setattr(_native, "windows_message_box", lambda *a: 1)
    assert _native.show("t", "x", platform="win32") is True
