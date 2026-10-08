# Nuitka fixtures

Everything in this folder was produced by **Nuitka 4.2.2** on Python 3.12.3
(Ubuntu 24.04, gcc 13) while the Nuitka engine was being written. Nothing was
typed by hand; long paths are left exactly as Nuitka printed them.

| File | How it was produced |
|---|---|
| `help-4.2.2.txt`, `help-plugins-4.2.2.txt`, `plugin-list-4.2.2.txt`, `version-4.2.2.txt` | `python -m nuitka --help` / `--help-plugins` / `--plugin-list` / `--version` |
| `onefile_success.log`, `onefile_keep_intermediates.log`, `onefile_report.xml` | `--mode=onefile` builds of a small script with a data folder |
| `standalone_yaml.log`, `standalone_yaml_report.xml`, `standalone_yaml_listing.txt` | `--mode=standalone` build of a script importing PyYAML; the listing is `find -printf "%s %P"` of `yamlapp.dist` |
| `patchelf_missing.log` | first build, before `patchelf` was installed |
| `readelf_missing.log`, `compiler_missing.log`, `compiler_cc_invalid.log` | builds with a PATH lacking binutils / any C compiler, and with `CC` pointing nowhere |
| `standalone_report_dir_missing.log` | `--report` into a folder that did not exist |
| `download_declined.log` | `--linux-create-installer` without `appimagetool`, stdin closed (`</dev/null`) |
| `plugin_tk_inter.log`, `plugin_pyqt5.log` | scripts importing `tkinter` / `PyQt5` without the plugin |
| `syntax_error.log`, `missing_import_build.log` | a script with a syntax error / an import of a module that is not installed |
| `onefile_runtime_missing_data.log` | running a one-file build whose data folder was not bundled |
| `nuitka_not_installed.log` | `python -m nuitka --version` on an interpreter without Nuitka |
| `python_experimental.log` | the first lines of a build on Python 3.15.0b4 |
