"""Issuing licence keys (``core/licensing.py``) and embedding the public key.

The one test that matters most: ``test_private_key_never_reaches_a_build_or_the_project_file``
writes a complete Runtime Kit and a ``p2e.toml`` and looks for the private
key in every byte of both.
"""

import datetime
import json
import os
import stat
import sys

import pytest

from p2e_runtime import config as rconfig
from p2e_runtime import license as rlic
from py2exe_gui.core import licensing as lic
from py2exe_gui.core import runtime_kit as rk
from py2exe_gui.core.config import BuildConfig, RuntimeKitConfig
from py2exe_gui.core.fixes import FINDING_CODES
from py2exe_gui.core.project_file import ProjectConfig, load_project, save_project
from py2exe_gui.core.update_signing import KEY_FORMAT, new_signing_key, read_key_file
from py2exe_gui.paths import license_key_path, signing_key_path

TODAY = datetime.date(2026, 10, 10)


def request(**fields):
    base = dict(name="Sara", email="sara@example.com", product="MyApp", expiry="",
                features=("pro",))
    base.update(fields)
    return lic.LicenseRequest(**base)


# ── Requests ───────────────────────────────────────────────────────────────


def test_parse_features_splits_dedupes_and_keeps_order():
    assert lic.parse_features("pro, export cloud;pro\nbeta") == ("pro", "export", "cloud", "beta")
    assert lic.parse_features("") == () and lic.parse_features("  ,, ") == ()


def test_validate_accepts_a_complete_request():
    assert lic.validate_request(request(), TODAY) == []
    assert lic.validate_request(request(email="", features=(), expiry="2026-10-10"), TODAY) == []


@pytest.mark.parametrize("fields, code, value", [
    (dict(name="  "), lic.ERR_NAME_MISSING, ""),
    (dict(product=""), lic.ERR_PRODUCT_MISSING, ""),
    (dict(email="not-an-email"), lic.ERR_EMAIL_INVALID, "not-an-email"),
    (dict(email="a@b"), lic.ERR_EMAIL_INVALID, "a@b"),
    (dict(expiry="10/10/2026"), lic.ERR_EXPIRY_INVALID, "10/10/2026"),
    (dict(expiry="2026-13-40"), lic.ERR_EXPIRY_INVALID, "2026-13-40"),
    (dict(expiry="2026-10-09"), lic.ERR_EXPIRY_PAST, "2026-10-09"),
    (dict(features=("ok", "bad feature")), lic.ERR_FEATURE_INVALID, "bad feature"),
])
def test_validate_names_each_problem(fields, code, value):
    assert (code, value) in lic.validate_request(request(**fields), TODAY)


def test_issue_refuses_an_invalid_request():
    with pytest.raises(ValueError, match="name_missing"):
        lic.issue(request(name=""), new_signing_key(), TODAY)


# ── Issuing ────────────────────────────────────────────────────────────────


def test_issued_key_verifies_with_the_runtime():
    key = new_signing_key()
    text = lic.issue(request(expiry="2027-01-01", features=("pro", "export")), key, TODAY)
    assert text == rlic.format_key(text)  # already in the grouped form
    info = rlic.verify(text, key.public_hex, "MyApp", TODAY)
    assert info.name == "Sara" and info.email == "sara@example.com"
    assert info.expiry == "2027-01-01" and info.features == ("pro", "export")
    assert rlic.verify(text, new_signing_key().public_hex, "MyApp", TODAY) is None


def test_payload_is_compact_json_with_stripped_fields():
    data = json.loads(lic.payload_bytes(request(name="  Sara ", product=" MyApp ")))
    assert data == {"name": "Sara", "email": "sara@example.com", "product": "MyApp",
                    "expiry": "", "features": ["pro"]}
    assert b" " not in lic.payload_bytes(request(name="Sara"))


def test_key_length_is_reasonable():
    text = lic.issue(request(), new_signing_key(), TODAY)
    # Version byte + 64-byte signature + ~80 bytes of JSON, in base32.
    assert 200 <= len(text.replace("-", "")) <= 320


def test_verify_with_key_reports_a_status(tmp_path):
    path = str(tmp_path / "k.json")
    key, _ = lic.load_or_create_key(path)
    text = lic.issue(request(), key, TODAY)
    assert lic.verify_with_key(text, path, "MyApp")[0] == rlic.STATUS_VALID
    assert lic.verify_with_key(text, path, "Other")[0] == rlic.STATUS_WRONG_PRODUCT
    assert lic.verify_with_key("garbage", path)[0] == rlic.STATUS_INVALID
    assert lic.verify_with_key(text, str(tmp_path / "none.json"))[0] == rlic.STATUS_INVALID


# ── The key pair: stored exactly like the update key ───────────────────────


def test_license_key_lives_beside_the_update_key_in_its_own_file():
    assert os.path.dirname(license_key_path()) == os.path.dirname(signing_key_path())
    assert os.path.basename(license_key_path()) == lic.KEY_FILE_NAME
    assert license_key_path() != signing_key_path()
    assert "signing" in license_key_path()


def test_load_or_create_writes_the_1_5_key_format_owner_only(tmp_path):
    path = tmp_path / "signing" / "license_signing_key.json"
    key, created = lic.load_or_create_key(str(path))
    assert created and path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format"] == KEY_FORMAT and data["public_key"] == key.public_hex
    assert "PRIVATE KEY" in data["warning"]
    if sys.platform != "win32":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    again, created = lic.load_or_create_key(str(path))
    assert not created and again == key
    assert read_key_file(str(path)) == key  # the update-signing reader accepts it


def test_broken_key_file_is_not_replaced_silently(tmp_path):
    path = tmp_path / "k.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        lic.load_or_create_key(str(path))
    assert path.read_text(encoding="utf-8") == "{not json"


def test_replace_key_keeps_the_old_one(tmp_path):
    path = str(tmp_path / "k.json")
    old, _ = lic.load_or_create_key(path)
    new, backup = lic.replace_key(path)
    assert new != old and backup.startswith(path + ".replaced-")
    assert read_key_file(backup) == old and read_key_file(path) == new
    assert lic.public_key_at(path) == new.public_hex
    assert lic.public_key_at(str(tmp_path / "missing.json")) == ""


# ── Embedding: the public key goes in, the private key never does ──────────


def kit_config(tmp_path, public_hex, product=""):
    source = tmp_path / "proj" / "app.py"
    source.parent.mkdir(exist_ok=True)
    source.write_text("print('hi')\n")
    return BuildConfig(
        source=str(source), output_name="MyApp", output_dir=str(tmp_path / "out"),
        runtime_kit=RuntimeKitConfig(licensing=True, license_public_key=public_hex,
                                     license_product=product),
    )


def test_private_key_never_reaches_a_build_or_the_project_file(tmp_path):
    key_path = str(tmp_path / "config" / "signing" / "license_signing_key.json")
    key, _ = lic.load_or_create_key(key_path)
    private_hex = key.seed.hex()
    config = kit_config(tmp_path, key.public_hex)

    options, errors = rk.write_kit(config)
    assert errors == [] and options
    files = rk.kit_files(config)
    written = []
    for folder, _dirs, names in os.walk(files.kit_dir):
        for name in names:
            written.append(os.path.join(folder, name))
    assert files.config_path in written and files.hook_path in written
    for path in written:
        with open(path, "rb") as f:
            blob = f.read()
        assert private_hex.encode() not in blob, path
        assert private_hex.upper().encode() not in blob, path
        assert key.seed not in blob, path
        assert b"private_key" not in blob, path
    with open(files.config_path, encoding="utf-8") as f:
        embedded = json.load(f)
    assert embedded["services"]["licensing"] == {"product": "MyApp", "public_key": key.public_hex}

    project = ProjectConfig(name="MyApp", build=config)
    toml_path = save_project(project, str(tmp_path / "proj" / "p2e.toml"))
    with open(toml_path, "rb") as f:
        toml = f.read()
    assert key.public_hex.encode() in toml
    assert private_hex.encode() not in toml and b"private_key" not in toml
    loaded = load_project(toml_path).project
    assert loaded.build.runtime_kit.licensing is True
    assert loaded.build.runtime_kit.license_public_key == key.public_hex
    # The key file itself stayed where it was, alone.
    assert os.path.isfile(key_path)
    assert not any("signing" in p for p in written)


def test_runtime_reads_the_embedded_section(tmp_path):
    key = new_signing_key()
    config = kit_config(tmp_path, key.public_hex.upper(), product="My Product")
    _options, errors = rk.write_kit(config)
    assert errors == []
    runtime = rconfig.load_config(rk.kit_files(config).config_path)
    assert runtime.licensing.product == "My Product"
    assert runtime.licensing.public_key == key.public_hex  # normalised to lower case
    text = lic.issue(request(product="My Product"), key, TODAY)
    assert rlic.check(text, runtime, TODAY).name == "Sara"
    assert rlic.check(lic.issue(request(), key, TODAY), runtime, TODAY) is None  # "MyApp"


def test_product_defaults_to_the_app_name():
    kit = RuntimeKitConfig(licensing=True, license_public_key="ab" * 32)
    assert rk.runtime_config_dict(kit, "Tool")["services"]["licensing"]["product"] == "Tool"


def test_hidden_import_for_the_license_module(tmp_path):
    config = kit_config(tmp_path, "ab" * 32)
    options = rk.preview_options(config)
    assert "p2e_runtime.license" in options
    assert "p2e_runtime.updates" not in options  # the updater is off


# ── Validation findings ────────────────────────────────────────────────────


def codes(kit):
    return [f.code for f in rk.validate(kit)]


def test_licensing_findings_are_registered():
    for code in ("kit_license_key_missing", "kit_license_key_invalid", "kit_license_client_side"):
        assert code in FINDING_CODES


def test_licensing_without_a_key_blocks_the_build(tmp_path):
    assert codes(RuntimeKitConfig(licensing=True)) == [
        "kit_license_key_missing", "kit_license_client_side",
    ]
    assert codes(RuntimeKitConfig(licensing=True, license_public_key="xyz")) == [
        "kit_license_key_invalid", "kit_license_client_side",
    ]
    _options, errors = rk.write_kit(kit_config(tmp_path, ""))
    assert [e.code for e in errors] == ["kit_license_key_missing"]


def test_honesty_note_is_info_and_always_present():
    findings = rk.validate(RuntimeKitConfig(licensing=True, license_public_key="ab" * 32))
    assert [(f.code, f.severity) for f in findings] == [("kit_license_client_side", "info")]
    assert rk.blocking(findings) == []
    assert codes(RuntimeKitConfig()) == []
