Official winget manifest JSON schemas, version 1.28.0, copied unchanged from
https://github.com/microsoft/winget-cli/tree/master/schemas/JSON/manifests/v1.28.0
(MIT licence, Microsoft Corporation) on 2026-10-06.

`tests/test_release_winget.py` checks the generated manifests against the
`required`, `enum`, `pattern` and length constraints in these files, so the
generator is tested against the real schema rather than a copy from memory.
