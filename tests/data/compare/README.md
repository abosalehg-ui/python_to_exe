# Compare-mode fixtures

Each file is the unedited output of a real `py2exe-gui compare --json` run in
this repository's development environment (Linux x86_64, Python 3.12.3,
PyInstaller 6.22.3, Nuitka 4.2.2, gcc 13), on these sample programs:

| File | Program | Mode | Runs / timeout |
|---|---|---|---|
| `yaml_onefile.json` | reads a YAML file with PyYAML, prints, exits | one file | 5 / 10 s |
| `yaml_onedir.json` | the same | folder | 5 / 10 s |
| `kit_onefile.json` | imports `p2e_runtime`, sleeps 1.5 s, prints (Runtime Kit: log redirection) | one file | 5 / 10 s |
| `server_onefile.json` | prints "listening on :8000", then loops forever | one file | 3 / 3 s |
| `silent_onefile.json` | loops forever without printing | one file | 3 / 3 s |
