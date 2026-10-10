"""The Linux and macOS packagers: layouts, metadata, tool commands, consent.

Everything but the ``slow`` tests runs with a fake tool runner and a fake
download, on any host: the layouts are checked on disk, the commands are
checked as lists. The ``slow`` tests build a real PyInstaller binary and run
the real ``dpkg-deb`` and ``appimagetool`` (the latter only when it is
already present or downloads were allowed for the test run).
"""

import os
import plistlib
import shutil
import stat
import struct
import subprocess
import sys
import zlib

import pytest

from py2exe_gui.core.packagers import (
    STAGING_DIR,
    AppImagePackager,
    DebPackager,
    DmgPackager,
    PackageResult,
    PackageSpec,
    UnknownFormatError,
    formats_for,
    get_packager,
    packager_names,
    preflight,
    run_packaging,
    spec_from_project,
)
from py2exe_gui.core.packagers.appimage import (
    KNOWN_DIGESTS,
    appimage_arch,
    appimagetool_url,
    apprun_script,
    download_appimagetool,
    find_appimagetool,
    find_runtime,
    runtime_url,
)
from py2exe_gui.core.packagers.base import (
    desktop_categories,
    desktop_entry,
    file_stem,
    install_build,
    resolve_icon_png,
    slug,
)
from py2exe_gui.core.packagers.deb import control_text, deb_arch, deb_version
from py2exe_gui.core.packagers.dmg import bundle_identifier, info_plist
from py2exe_gui.core.packagers.icons import (
    PNG_SIGNATURE,
    encode_png,
    placeholder_png,
    png_from_ico,
    png_from_icon_file,
    png_size,
)
from py2exe_gui.core.project_file import ProjectConfig

LINUX = "linux"
DOWNLOADS_ALLOWED = os.environ.get("P2E_TEST_DOWNLOADS") == "1"


# ── Fixtures ──────────────────────────────────────────────────────────────


def make_png(width=8, height=8):
    rows = [bytes([10, 20, 30, 255] * width) for _ in range(height)]
    return encode_png(width, height, rows)


def make_ico_with_png(size=16):
    png = make_png(size, size)
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(png), 6 + 16)
    return header + entry + png


def make_ico_with_bmp(size=4):
    # BITMAPINFOHEADER with doubled height, BGRA bottom-up, then an AND mask.
    pixels = b""
    for y in range(size):
        for x in range(size):
            pixels += bytes((x, y, 100, 255))  # B G R A
    mask = b"\x00" * (size * 4)
    bmp = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, 0, 0, 0, 0, 0) + pixels + mask
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(bmp), 22)
    return header + entry + bmp


@pytest.fixture
def onefile(tmp_path):
    built = tmp_path / "dist" / "hello"
    built.parent.mkdir()
    built.write_text("#!/bin/sh\necho hello\n")
    built.chmod(0o755)
    return str(built)


@pytest.fixture
def onedir(tmp_path):
    folder = tmp_path / "dist_dir" / "hello"
    (folder / "_internal").mkdir(parents=True)
    (folder / "hello").write_text("#!/bin/sh\necho hello\n")
    (folder / "hello").chmod(0o755)
    (folder / "_internal" / "lib.so").write_bytes(b"\x7fELF")
    return str(folder)


def spec_for(built, tmp_path, **overrides):
    values = dict(name="Hello App", version="1.2.3", built=built, exe_name="hello",
                  description="A hello app\nMore about it.", maintainer="Me <me@example.com>",
                  homepage="https://example.com", categories="Utility;Development",
                  out_dir=str(tmp_path / "release" / "1.2.3"), arch="x86_64")
    values.update(overrides)
    return PackageSpec(**values)


class FakeRunner:
    """Pretends to be dpkg-deb/appimagetool/hdiutil: writes the output file."""

    def __init__(self, returncode=0, stderr="", create=True):
        self.calls = []
        self.returncode = returncode
        self.stderr = stderr
        self.create = create

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if self.create and self.returncode == 0:
            target = command[-1]
            with open(target, "wb") as f:
                f.write(b"package-bytes")
        return subprocess.CompletedProcess(command, self.returncode, "built\n", self.stderr)


# ── Names, versions, architectures ────────────────────────────────────────


@pytest.mark.parametrize("name,expected", [
    ("Hello App", "hello-app"), ("My_Tool 2", "my-tool-2"), ("  ", "app"), ("x", "app-x"),
    ("--Weird--", "weird"), ("Café Finder", "caf-finder"), ("a+b.c", "a+b.c"),
])
def test_slug_follows_debian_package_name_rules(name, expected):
    assert slug(name) == expected


def test_file_stem_keeps_case_and_dots():
    assert file_stem("Hello App") == "Hello-App"
    assert file_stem("v1.2 (beta)") == "v1.2-beta"
    assert file_stem("") == "app"


@pytest.mark.parametrize("version,expected", [
    ("1.2.3", "1.2.3"), ("1.0.0-beta.1", "1.0.0~beta.1"), ("", "0.0.0"),
    ("v1.2", "0.0.0+v1.2"), ("1.0 build 7", "1.0.build.7"),
])
def test_deb_version(version, expected):
    assert deb_version(version) == expected


def test_architecture_names():
    assert deb_arch("x86_64") == "amd64"
    assert deb_arch("aarch64") == "arm64"
    assert deb_arch("i686") == "i386"
    assert deb_arch("riscv64") == "riscv64"
    assert appimage_arch("x86_64") == "x86_64" and appimage_arch("amd64") == "x86_64"
    assert appimage_arch("arm64") == "aarch64"
    assert appimage_arch("armv7l") == "armhf"
    assert appimage_arch("") == "x86_64"


def test_desktop_categories_normalized():
    assert desktop_categories("Utility, Development") == "Utility;Development;"
    assert desktop_categories("Utility;") == "Utility;"
    assert desktop_categories("") == "Utility;"


def test_desktop_entry_fields(tmp_path, onefile):
    spec = spec_for(onefile, tmp_path, windowed=True)
    text = desktop_entry(spec, exec_line="hello-app", icon_name="hello-app")
    assert "[Desktop Entry]\nType=Application\nName=Hello App\n" in text
    assert "Comment=A hello app More about it.\n" in text
    assert "Exec=hello-app\nIcon=hello-app\nTerminal=false\nCategories=Utility;Development;\n" in text
    console = desktop_entry(spec_for(onefile, tmp_path), "x", "x")
    assert "Terminal=true" in console


# ── Icons ─────────────────────────────────────────────────────────────────


def test_png_passthrough_and_size(tmp_path):
    png = make_png(12, 7)
    path = tmp_path / "icon.png"
    path.write_bytes(png)
    assert png_from_icon_file(str(path)) == png
    assert png_size(png) == (12, 7)
    assert png_size(b"nope") is None


def test_ico_with_embedded_png_is_copied_out():
    ico = make_ico_with_png(16)
    out = png_from_ico(ico)
    assert out and out.startswith(PNG_SIGNATURE) and png_size(out) == (16, 16)


def test_ico_with_bmp_entry_is_converted():
    out = png_from_ico(make_ico_with_bmp(4))
    assert out and png_size(out) == (4, 4)
    # Decode the first pixel of the top row: stored bottom-up, so row y=3.
    idat = out[out.index(b"IDAT") + 4:out.index(b"IEND") - 4]
    raw = zlib.decompress(idat)
    assert raw[1:5] == bytes((100, 3, 0, 255))  # R=100, G=y=3 (top row), B=x=0


def test_unreadable_icons_give_none(tmp_path):
    assert png_from_ico(b"") is None
    assert png_from_ico(b"\x00\x00\x02\x00\x01\x00") is None  # a .cur, not an .ico
    assert png_from_icon_file(str(tmp_path / "missing.ico")) is None
    bad = tmp_path / "bad.ico"
    bad.write_bytes(b"not an icon at all")
    assert png_from_icon_file(str(bad)) is None


def test_placeholder_png_is_a_valid_image():
    png = placeholder_png(32)
    assert png_size(png) == (32, 32)


def test_resolve_icon_png_reports_the_placeholder(tmp_path, onefile):
    png, warning = resolve_icon_png(spec_for(onefile, tmp_path, icon=""))
    assert png_size(png) == (256, 256)
    assert warning.code == "package_icon_placeholder" and warning.params["icon"] == "—"
    real = tmp_path / "app.png"
    real.write_bytes(make_png())
    png, warning = resolve_icon_png(spec_for(onefile, tmp_path, icon=str(real)))
    assert warning is None and png == make_png()


# ── The registry ──────────────────────────────────────────────────────────


def test_registry():
    assert packager_names() == ["appimage", "deb", "dmg"]
    assert isinstance(get_packager("deb"), DebPackager)
    assert formats_for("linux") == ["appimage", "deb"]
    assert formats_for("darwin") == ["dmg"]
    assert formats_for("win32") == []
    with pytest.raises(UnknownFormatError):
        get_packager("rpm")


def test_spec_from_project_falls_back_to_other_tabs(tmp_path):
    project = ProjectConfig(name="My App", version="2.0.0")
    project.build.source = str(tmp_path / "app.py")
    project.build.output_name = "myapp"
    project.build.icon = str(tmp_path / "a.ico")
    project.build.windowed = True
    project.version_info.company_name = "Acme"
    project.version_info.file_description = "Does things"
    project.installer.publisher_url = "https://acme.example"
    project.release.repository = "acme-org/my-app"
    project.release.winget.license = "MIT"
    spec = spec_from_project(project, "/dist/myapp", "2.0.0", "/out", sign_identity="Dev ID")
    assert spec.name == "My App" and spec.exe_name == "myapp" and spec.version == "2.0.0"
    assert spec.maintainer == "Acme" and spec.description == "Does things"
    assert spec.homepage == "https://acme.example" and spec.license == "MIT"
    assert spec.identifier == "io.github.acme-org.my-app"
    assert spec.windowed and spec.sign_identity == "Dev ID" and spec.categories == "Utility"
    project.packaging.maintainer = "Me <me@x>"
    project.packaging.identifier = "com.acme.app"
    project.packaging.description = "Short"
    project.packaging.deb_depends = "libc6"
    spec = spec_from_project(project, "/dist/myapp", "2.0.0", "/out")
    assert spec.maintainer == "Me <me@x>" and spec.identifier == "com.acme.app"
    assert spec.description == "Short" and spec.depends == "libc6"


def test_packaging_settings_enabled_formats():
    project = ProjectConfig()
    assert project.packaging.enabled_formats() == []
    project.packaging.deb = True
    project.packaging.dmg = True
    assert project.packaging.enabled_formats() == ["deb", "dmg"]


# ── Preflight checks ──────────────────────────────────────────────────────


def test_check_wrong_platform(tmp_path, onefile):
    spec = spec_for(onefile, tmp_path)
    codes = [f.code for f in get_packager("dmg").check(spec, "linux")]
    assert codes == ["package_wrong_platform"]
    codes = [f.code for f in get_packager("deb").check(spec, "win32")]
    assert codes == ["package_wrong_platform"]


def test_check_missing_build_tool_and_version(tmp_path, monkeypatch):
    spec = spec_for(str(tmp_path / "nope"), tmp_path, version="", maintainer="")
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    codes = [f.code for f in DebPackager().check(spec, "linux")]
    assert codes == ["package_no_build", "package_tool_missing", "package_version_missing"]


def test_deb_warns_about_a_missing_maintainer(tmp_path, onefile, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/dpkg-deb")
    spec = spec_for(onefile, tmp_path, maintainer="")
    findings = DebPackager().check(spec, "linux")
    assert [f.code for f in findings] == ["package_maintainer_missing"]
    assert findings[0].severity == "warning"


def test_preflight_runs_every_format(tmp_path, onefile, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/tool")
    spec = spec_for(onefile, tmp_path)
    tool = AppImagePackager(tools_dir=str(tmp_path / "tools"))
    monkeypatch.setitem(sys.modules["py2exe_gui.core.packagers"]._PACKAGERS, "appimage", tool)
    result = preflight(spec, ["appimage", "deb", "dmg"], "linux", env={})
    assert [f.code for f in result["appimage"]] == ["appimagetool_missing"]
    assert result["deb"] == []
    assert [f.code for f in result["dmg"]] == ["package_wrong_platform"]


# ── AppImage ──────────────────────────────────────────────────────────────


def test_find_appimagetool_order(tmp_path, monkeypatch):
    tools = tmp_path / "tools"
    tools.mkdir()
    assert find_appimagetool({}, str(tools), "x86_64") == ""
    local = tools / "appimagetool-x86_64.AppImage"
    local.write_bytes(b"x")
    assert find_appimagetool({}, str(tools), "x86_64") == str(local)
    explicit = tmp_path / "mine"
    explicit.write_bytes(b"x")
    assert find_appimagetool({"APPIMAGETOOL": str(explicit)}, str(tools)) == str(explicit)
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/appimagetool"
                        if name == "appimagetool" else None)
    assert find_appimagetool({}, "") == "/usr/bin/appimagetool"
    assert find_runtime({}, str(tools)) == ""
    (tools / "runtime-x86_64").write_bytes(b"r")
    assert find_runtime({}, str(tools), "x86_64") == str(tools / "runtime-x86_64")
    assert find_runtime({"APPIMAGE_RUNTIME_FILE": str(explicit)}, "") == str(explicit)


def test_tool_path_needs_the_runtime_too(tmp_path):
    """Without the runtime file appimagetool would download it mid-build."""
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "appimagetool-x86_64.AppImage").write_bytes(b"x")
    packager = AppImagePackager(tools_dir=str(tools))
    assert packager.tool_path({}) == ""
    (tools / "runtime-x86_64").write_bytes(b"r")
    assert packager.tool_path({}).endswith("appimagetool-x86_64.AppImage")


def test_urls_and_known_digests():
    assert appimagetool_url("x86_64").endswith("/continuous/appimagetool-x86_64.AppImage")
    assert appimagetool_url("arm64").endswith("appimagetool-aarch64.AppImage")
    assert runtime_url("x86_64").endswith("/type2-runtime/releases/download/continuous/runtime-x86_64")
    assert len(KNOWN_DIGESTS["x86_64"]) == 64


class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self.data)
        chunk = self.data[self.pos:self.pos + size]
        self.pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_download_fetches_both_files_and_reports_the_digest(tmp_path):
    fetched = []

    def urlopen(url, timeout=0):
        fetched.append(url)
        return FakeResponse(b"tool-bytes" if "appimagetool" in url else b"runtime-bytes")

    lines = []
    tools = str(tmp_path / "tools")
    path, digest, matches = download_appimagetool(tools, lines.append, "x86_64", urlopen=urlopen)
    assert fetched == [appimagetool_url("x86_64"), runtime_url("x86_64")]
    assert path == os.path.join(tools, "appimagetool-x86_64.AppImage")
    assert os.path.isfile(path) and os.path.isfile(os.path.join(tools, "runtime-x86_64"))
    assert os.stat(path).st_mode & stat.S_IXUSR
    assert matches is False and digest in "".join(lines)  # a fake, so not the recorded one
    assert not [n for n in os.listdir(tools) if n.endswith(".part")]
    # A second call downloads nothing.
    fetched.clear()
    download_appimagetool(tools, lines.append, "x86_64", urlopen=urlopen)
    assert fetched == []


def test_cut_download_leaves_no_tool(tmp_path):
    def urlopen(url, timeout=0):
        raise OSError("connection reset")

    tools = str(tmp_path / "tools")
    with pytest.raises(OSError):
        download_appimagetool(tools, machine="x86_64", urlopen=urlopen)
    assert not os.path.exists(os.path.join(tools, "appimagetool-x86_64.AppImage"))


def test_appimage_layout_onefile(tmp_path, onefile):
    spec = spec_for(onefile, tmp_path)
    packager = AppImagePackager(tools_dir=str(tmp_path / "tools"))
    staging = packager.staging_dir(spec)
    assert staging == os.path.join(spec.out_dir, STAGING_DIR, "appimage")
    os.makedirs(staging)
    findings = packager.stage(spec, staging, lambda _m: None)
    appdir = os.path.join(staging, "Hello-App.AppDir")
    assert os.stat(os.path.join(appdir, "AppRun")).st_mode & stat.S_IXUSR
    assert 'exec "$HERE/usr/bin/hello-app" "$@"' in open(os.path.join(appdir, "AppRun")).read()
    assert os.stat(os.path.join(appdir, "usr", "bin", "hello-app")).st_mode & stat.S_IXOTH
    for rel in ("hello-app.desktop", "hello-app.png", ".DirIcon",
                "usr/share/applications/hello-app.desktop",
                "usr/share/icons/hicolor/256x256/apps/hello-app.png"):
        assert os.path.isfile(os.path.join(appdir, rel)), rel
    assert [f.code for f in findings] == ["package_icon_placeholder"]
    commands = packager.commands(spec, staging, "/t/appimagetool", env={})
    assert commands == [["/t/appimagetool", "--no-appstream", "--runtime-file",
                         os.path.join(str(tmp_path / "tools"), "runtime-x86_64"), appdir,
                         os.path.join(spec.out_dir, "Hello-App-1.2.3-x86_64.AppImage")]]
    env = packager.environment(spec)
    assert env == {"ARCH": "x86_64", "VERSION": "1.2.3", "APPIMAGE_EXTRACT_AND_RUN": "1"}


def test_appimage_layout_onedir(tmp_path, onedir):
    spec = spec_for(onedir, tmp_path)
    packager = AppImagePackager(tools_dir=str(tmp_path / "tools"))
    staging = packager.staging_dir(spec)
    os.makedirs(staging)
    packager.stage(spec, staging, lambda _m: None)
    appdir = os.path.join(staging, "Hello-App.AppDir")
    assert os.path.isfile(os.path.join(appdir, "usr", "lib", "hello-app", "_internal", "lib.so"))
    assert 'exec "$HERE/usr/lib/hello-app/hello" "$@"' in open(os.path.join(appdir, "AppRun")).read()


def test_apprun_script_shape():
    text = apprun_script("usr/bin/x")
    assert text.startswith("#!/bin/sh\n") and text.endswith('exec "$HERE/usr/bin/x" "$@"\n')


# ── .deb ──────────────────────────────────────────────────────────────────


def test_control_text(tmp_path, onefile):
    spec = spec_for(onefile, tmp_path, depends="libc6 (>= 2.31)")
    text = control_text(spec, installed_kb=1234)
    assert text == (
        "Package: hello-app\nVersion: 1.2.3\nSection: utils\nPriority: optional\n"
        "Architecture: amd64\nMaintainer: Me <me@example.com>\nInstalled-Size: 1234\n"
        "Depends: libc6 (>= 2.31)\nHomepage: https://example.com\n"
        "Description: A hello app\n More about it.\n"
    )
    bare = control_text(spec_for(onefile, tmp_path, maintainer="", homepage="", depends="",
                                 description="One\n\nThree"), 0)
    assert "Maintainer: Hello App <unknown@localhost>\n" in bare
    assert "Homepage" not in bare and "Depends" not in bare
    assert "Description: One\n .\n Three\n" in bare and "Installed-Size: 1\n" in bare


def test_deb_layout_onefile_and_onedir(tmp_path, onefile, onedir):
    packager = DebPackager()
    spec = spec_for(onefile, tmp_path)
    staging = packager.staging_dir(spec)
    os.makedirs(staging)
    packager.stage(spec, staging, lambda _m: None)
    root = os.path.join(staging, "hello-app_1.2.3_amd64")
    assert os.path.isfile(os.path.join(root, "DEBIAN", "control"))
    assert os.stat(os.path.join(root, "DEBIAN")).st_mode & 0o777 == 0o755
    assert os.stat(os.path.join(root, "usr", "bin", "hello-app")).st_mode & stat.S_IXOTH
    assert os.path.isfile(os.path.join(root, "usr", "share", "applications", "hello-app.desktop"))
    assert os.path.isfile(os.path.join(root, "usr", "share", "icons", "hicolor", "256x256",
                                       "apps", "hello-app.png"))
    assert packager.commands(spec, staging, "dpkg-deb") == [[
        "dpkg-deb", "--build", "--root-owner-group", root,
        os.path.join(spec.out_dir, "hello-app_1.2.3_amd64.deb")]]

    spec = spec_for(onedir, tmp_path / "two")
    staging = packager.staging_dir(spec)
    os.makedirs(staging)
    packager.stage(spec, staging, lambda _m: None)
    root = os.path.join(staging, "hello-app_1.2.3_amd64")
    link = os.path.join(root, "usr", "bin", "hello-app")
    assert os.path.islink(link) and os.readlink(link) == "/opt/hello-app/hello"
    assert os.path.isfile(os.path.join(root, "opt", "hello-app", "_internal", "lib.so"))


# ── .dmg ──────────────────────────────────────────────────────────────────


def test_info_plist_and_identifier(tmp_path, onefile):
    spec = spec_for(onefile, tmp_path, identifier="", homepage="")
    assert bundle_identifier(spec) == "local.hello-app"
    info = plistlib.loads(info_plist(spec, "Hello-App", "Hello-App.icns"))
    assert info["CFBundleExecutable"] == "Hello-App"
    assert info["CFBundleIdentifier"] == "local.hello-app"
    assert info["CFBundleShortVersionString"] == "1.2.3" and info["CFBundleVersion"] == "1.2.3"
    assert info["CFBundleIconFile"] == "Hello-App.icns" and info["CFBundlePackageType"] == "APPL"
    assert info["CFBundleName"] == "Hello App" and info["NSHighResolutionCapable"] is True
    spec = spec_for(onefile, tmp_path, identifier="com.acme.hello")
    info = plistlib.loads(info_plist(spec, "x"))
    assert info["CFBundleIdentifier"] == "com.acme.hello" and "CFBundleIconFile" not in info


def test_dmg_layout_and_commands(tmp_path, onefile):
    packager = DmgPackager()
    icns = tmp_path / "app.icns"
    icns.write_bytes(b"icns")
    spec = spec_for(onefile, tmp_path, icon=str(icns), sign_identity="Developer ID: Me")
    staging = packager.staging_dir(spec)
    os.makedirs(staging)
    findings = packager.stage(spec, staging, lambda _m: None)
    app = os.path.join(staging, "Hello-App.app")
    assert findings == []
    assert os.path.isfile(os.path.join(app, "Contents", "MacOS", "Hello-App"))
    assert os.path.isfile(os.path.join(app, "Contents", "Resources", "Hello-App.icns"))
    assert open(os.path.join(app, "Contents", "PkgInfo"), "rb").read() == b"APPL????"
    assert os.readlink(os.path.join(staging, "Applications")) == "/Applications"
    info = plistlib.load(open(os.path.join(app, "Contents", "Info.plist"), "rb"))
    assert info["CFBundleExecutable"] == "Hello-App"
    commands = packager.commands(spec, staging, "hdiutil")
    assert commands[0][:2] == ["codesign", "--force"] and commands[0][-1] == app
    assert "--options" in commands[0] and "runtime" in commands[0]
    assert commands[1] == ["hdiutil", "create", "-volname", "Hello App", "-srcfolder", staging,
                           "-ov", "-format", "UDZO",
                           os.path.join(spec.out_dir, "Hello-App-1.2.3.dmg")]


def test_dmg_without_icns_warns(tmp_path, onedir):
    packager = DmgPackager()
    spec = spec_for(onedir, tmp_path, icon="/x/app.ico")
    staging = packager.staging_dir(spec)
    os.makedirs(staging)
    findings = packager.stage(spec, staging, lambda _m: None)
    assert [f.code for f in findings] == ["package_icon_icns"]
    assert findings[0].params["icon"] == "app.ico"
    assert os.path.isfile(os.path.join(staging, "Hello-App.app", "Contents", "MacOS", "hello"))
    assert len(packager.commands(spec, staging, "hdiutil")) == 1  # unsigned: no codesign


# ── Building with the tool ────────────────────────────────────────────────


def test_build_runs_the_tool_and_reports_the_file(tmp_path, onefile, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/dpkg-deb")
    runner = FakeRunner()
    lines = []
    result = DebPackager().build(spec_for(onefile, tmp_path), lines.append, runner, env={})
    assert result.ok and result.path.endswith("hello-app_1.2.3_amd64.deb")
    assert result.size_bytes == len(b"package-bytes")
    assert result.commands[0][0] == "/usr/bin/dpkg-deb"
    assert runner.calls[0][1]["cwd"] == os.path.dirname(result.path)
    assert lines[0].startswith("$ /usr/bin/dpkg-deb --build") and "built" in lines
    # The staging copy is removed after a success, and left after a failure.
    assert not os.path.exists(os.path.join(os.path.dirname(result.path), STAGING_DIR))
    failed = DebPackager().build(spec_for(onefile, tmp_path), runner=FakeRunner(1), env={})
    assert not failed.ok and os.path.isdir(os.path.join(tmp_path, "release", "1.2.3", STAGING_DIR))


def test_build_reports_a_failing_tool(tmp_path, onefile, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/dpkg-deb")
    result = DebPackager().build(spec_for(onefile, tmp_path), runner=FakeRunner(2, "boom"))
    assert not result.ok and result.error_code == "package_failed" and result.error == "boom"
    result = DebPackager().build(spec_for(onefile, tmp_path), runner=FakeRunner(0, create=False))
    assert not result.ok and "no output" in result.error

    def raising(*_a, **_k):
        raise OSError("cannot run")

    result = DebPackager().build(spec_for(onefile, tmp_path), runner=raising)
    assert not result.ok and result.error == "cannot run"


def test_build_without_the_tool(tmp_path, onefile, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    result = DebPackager().build(spec_for(onefile, tmp_path))
    assert not result.ok and result.error_code == "package_tool_missing"


def test_build_stages_fresh_each_time(tmp_path, onefile, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/dpkg-deb")
    spec = spec_for(onefile, tmp_path)
    packager = DebPackager()
    stale = os.path.join(packager.staging_dir(spec), "stale.txt")
    os.makedirs(os.path.dirname(stale))
    open(stale, "w").close()
    packager.build(spec, runner=FakeRunner())
    assert not os.path.exists(stale)


def test_install_build_keeps_the_executable_bit(tmp_path, onefile):
    target = str(tmp_path / "x" / "hello")
    assert install_build(spec_for(onefile, tmp_path), target) == target
    assert os.stat(target).st_mode & stat.S_IXOTH


# ── run_packaging: platforms and consent ──────────────────────────────────


def test_run_packaging_blocks_without_consent(tmp_path, onefile, monkeypatch):
    tool = AppImagePackager(tools_dir=str(tmp_path / "tools"))
    monkeypatch.setitem(sys.modules["py2exe_gui.core.packagers"]._PACKAGERS, "appimage", tool)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    spec = spec_for(onefile, tmp_path)
    results = run_packaging(spec, ["appimage"], platform=LINUX, env={})
    assert results[0].error_code == "appimagetool_missing" and not results[0].ok
    asked = []
    results = run_packaging(spec, ["appimage"], platform=LINUX, env={},
                            download_consent=lambda url, folder: asked.append((url, folder)) or False)
    assert asked == [(appimagetool_url("x86_64"), str(tmp_path / "tools"))]
    assert results[0].error_code == "appimagetool_missing"


def test_run_packaging_downloads_after_consent(tmp_path, onefile, monkeypatch):
    tools = str(tmp_path / "tools")
    tool = AppImagePackager(tools_dir=tools)
    monkeypatch.setitem(sys.modules["py2exe_gui.core.packagers"]._PACKAGERS, "appimage", tool)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    spec = spec_for(onefile, tmp_path)
    runner = FakeRunner()

    def downloader(folder, log, machine, env=None):
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "appimagetool-x86_64.AppImage")
        open(path, "wb").write(b"t")
        open(os.path.join(folder, "runtime-x86_64"), "wb").write(b"r")
        return path, "deadbeef", False

    lines = []
    results = run_packaging(spec, ["appimage"], lines.append, runner, LINUX, env={},
                            download_consent=lambda *_: True, downloader=downloader)
    assert results[0].ok and results[0].path.endswith(".AppImage")
    assert runner.calls[0][0][0] == os.path.join(tools, "appimagetool-x86_64.AppImage")
    assert runner.calls[0][1]["env"]["APPIMAGE_EXTRACT_AND_RUN"] == "1"
    assert any("differs" in line for line in lines)
    assert [f.code for f in results[0].findings] == ["package_icon_placeholder"]


def test_run_packaging_reports_a_failed_download(tmp_path, onefile, monkeypatch):
    tool = AppImagePackager(tools_dir=str(tmp_path / "tools"))
    monkeypatch.setitem(sys.modules["py2exe_gui.core.packagers"]._PACKAGERS, "appimage", tool)
    monkeypatch.setattr(shutil, "which", lambda _name: None)

    def downloader(*_a, **_k):
        raise OSError("offline")

    results = run_packaging(spec_for(onefile, tmp_path), ["appimage"], platform=LINUX, env={},
                            download_consent=lambda *_: True, downloader=downloader)
    assert results[0].error_code == "appimagetool_download_failed" and "offline" in results[0].error


def test_run_packaging_wrong_platform_and_order(tmp_path, onefile, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/tool")
    results = run_packaging(spec_for(onefile, tmp_path), ["dmg", "deb"], runner=FakeRunner(),
                            platform=LINUX, env={})
    assert [(r.format, r.ok, r.error_code) for r in results] == [
        ("dmg", False, "package_wrong_platform"), ("deb", True, "")]
    assert isinstance(results[1], PackageResult)


# ── Real tools (slow) ─────────────────────────────────────────────────────


def _real_build(tmp_path):
    pytest.importorskip("PyInstaller", reason="PyInstaller not installed")
    script = tmp_path / "hello_app.py"
    script.write_text("import sys\nprint('hello from a packaged app', sys.argv[1:])\n")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--onefile", "--clean", "--noconfirm",
                    "--log-level", "WARN", "--distpath", str(tmp_path / "dist"),
                    "--workpath", str(tmp_path / "build"), "--specpath", str(tmp_path),
                    str(script)], check=True, cwd=str(tmp_path), timeout=600)
    built = tmp_path / "dist" / "hello_app"
    assert built.is_file()
    return str(built)


@pytest.mark.slow
@pytest.mark.skipif(not sys.platform.startswith("linux") or shutil.which("dpkg-deb") is None,
                    reason="needs Linux and dpkg-deb")
def test_real_deb_builds_and_runs(tmp_path):
    built = _real_build(tmp_path)
    spec = spec_for(built, tmp_path, exe_name="hello_app")
    results = run_packaging(spec, ["deb"], platform=LINUX)
    assert results[0].ok, results[0].error
    deb = results[0].path
    listing = subprocess.run(["dpkg-deb", "-c", deb], capture_output=True, text=True, check=True)
    assert "./usr/bin/hello-app" in listing.stdout
    assert "./usr/share/applications/hello-app.desktop" in listing.stdout
    info = subprocess.run(["dpkg-deb", "-I", deb], capture_output=True, text=True, check=True)
    assert "Package: hello-app" in info.stdout and "Version: 1.2.3" in info.stdout
    extracted = tmp_path / "x"
    subprocess.run(["dpkg-deb", "-x", deb, str(extracted)], check=True)
    run = subprocess.run([str(extracted / "usr" / "bin" / "hello-app"), "a"], capture_output=True,
                         text=True, timeout=60)
    assert run.returncode == 0 and "hello from a packaged app ['a']" in run.stdout


@pytest.mark.slow
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="needs Linux")
def test_real_appimage_builds_and_runs(tmp_path, monkeypatch):
    tools = os.environ.get("P2E_TEST_TOOLS_DIR", "")
    packager = AppImagePackager(tools_dir=tools or str(tmp_path / "tools"))
    monkeypatch.setitem(sys.modules["py2exe_gui.core.packagers"]._PACKAGERS, "appimage", packager)
    if not packager.tool_path() and not DOWNLOADS_ALLOWED:
        pytest.skip("appimagetool not present; set P2E_TEST_DOWNLOADS=1 to allow the download")
    built = _real_build(tmp_path)
    spec = spec_for(built, tmp_path, exe_name="hello_app")
    results = run_packaging(spec, ["appimage"], platform=LINUX,
                            download_consent=lambda *_: DOWNLOADS_ALLOWED)
    assert results[0].ok, results[0].error
    image = results[0].path
    assert os.stat(image).st_mode & stat.S_IXUSR
    env = dict(os.environ, APPIMAGE_EXTRACT_AND_RUN="1")
    run = subprocess.run([image, "b"], capture_output=True, text=True, timeout=120, env=env)
    assert run.returncode == 0 and "hello from a packaged app ['b']" in run.stdout
    extract = subprocess.run([image, "--appimage-extract"], capture_output=True, text=True,
                             timeout=120, env=env, cwd=str(tmp_path))
    assert extract.returncode == 0
    squash = tmp_path / "squashfs-root"
    assert (squash / "AppRun").is_file() and (squash / "hello-app.desktop").is_file()
    assert (squash / "usr" / "bin" / "hello-app").is_file()
