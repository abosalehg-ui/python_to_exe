"""winget manifests, checked against the official 1.28.0 JSON schemas."""

import json
import os
import re

import pytest

from py2exe_gui.core.release import winget

SCHEMAS = os.path.join(os.path.dirname(__file__), "data", "winget")
SHA = "ab" * 32


def load_schema(kind):
    with open(os.path.join(SCHEMAS, f"manifest.{kind}.1.28.0.json"), encoding="utf-8") as f:
        return json.load(f)


def _resolve(schema, root):
    while "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        schema = root["definitions"][name]
    return schema


def schema_errors(value, schema, root, path="$"):
    """The subset of JSON Schema (draft-07) the winget schemas use."""
    schema = _resolve(schema, root)
    errors = []
    types = schema.get("type")
    if types:
        allowed = types if isinstance(types, list) else [types]
        kinds = {"string": str, "array": list, "object": dict, "integer": int,
                 "boolean": bool, "null": type(None)}
        if not any(isinstance(value, kinds[t]) for t in allowed if t in kinds):
            return [f"{path}: expected {allowed}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must be {schema['const']}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in enum")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match {schema['pattern']}")
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: too short")
        if len(value) > schema.get("maxLength", 10**9):
            errors.append(f"{path}: too long")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required {key}")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key not in props:
                errors.append(f"{path}: {key} is not a property of the schema")
                continue
            errors += schema_errors(item, props[key], root, f"{path}.{key}")
    if isinstance(value, list):
        if len(value) > schema.get("maxItems", 10**9):
            errors.append(f"{path}: too many items")
        if "items" in schema:
            for i, item in enumerate(value):
                errors += schema_errors(item, schema["items"], root, f"{path}[{i}]")
    return errors


def manifests(**overrides):
    args = dict(identifier="AbdulkarimAlaboud.PythonToExe", version="1.6.0",
                publisher="عبدالكريم العبود", name="Python to EXE", license_text="Proprietary",
                short_description="محوّل بايثون إلى EXE",
                installer_url="https://github.com/me/app/releases/download/v1.6.0/A-setup.exe",
                sha256=SHA, installer_type="inno", publisher_url="https://example.com")
    args.update(overrides)
    return winget.build_manifests(**args)


def assert_matches_official_schema(docs):
    for kind, doc in docs.items():
        schema = load_schema(kind)
        errors = schema_errors(doc, schema, schema)
        assert errors == [], f"{kind}: {errors}"


def test_schema_files_are_the_version_we_generate():
    for kind in ("version", "installer", "defaultLocale"):
        schema = load_schema(kind)
        assert schema["$id"] == winget.SCHEMA_URL.format(kind=kind.lower())
        assert tuple(schema["required"]) == winget.REQUIRED[kind]
    installer = load_schema("installer")
    assert tuple(installer["definitions"]["Installer"]["required"]) == winget.INSTALLER_REQUIRED
    assert tuple(installer["definitions"]["InstallerType"]["enum"]) == winget.INSTALLER_TYPES
    assert tuple(installer["definitions"]["Architecture"]["enum"]) == winget.ARCHITECTURES


@pytest.mark.parametrize("kind,extra", [
    ("inno", {}),
    ("portable", {"installer_url": "https://github.com/me/app/releases/download/v1/A.exe"}),
    ("zip", {"nested_path": "App/App.exe", "command_alias": "app",
             "installer_url": "https://github.com/me/app/releases/download/v1/A.zip"}),
])
def test_generated_manifests_satisfy_the_official_schema(kind, extra):
    docs = manifests(installer_type=kind, **extra)
    assert winget.validate_manifests(docs) == []
    assert_matches_official_schema(docs)
    assert docs["installer"]["Installers"][0]["InstallerSha256"] == SHA.upper()


@pytest.mark.parametrize("change,problem", [
    ({"identifier": "NoDot"}, "PackageIdentifier"),
    ({"identifier": ""}, "PackageIdentifier: required"),
    ({"license_text": ""}, "License: required"),
    ({"license_text": "AB"}, "License: length"),
    ({"short_description": ""}, "ShortDescription"),
    ({"publisher": "X"}, "Publisher: length"),
    ({"installer_url": "ftp://x/y"}, "InstallerUrl"),
    ({"sha256": "123"}, "InstallerSha256"),
    ({"locale": "english"}, "Locale"),
    ({"version": "1/2"}, "PackageVersion"),
    ({"architecture": "sparc"}, "Architecture"),
    ({"installer_type": "deb"}, "InstallerType"),
    ({"installer_type": "zip"}, "RelativeFilePath"),
    ({"publisher_url": "example.com"}, "PublisherUrl"),
])
def test_validation_catches_what_the_schema_rejects(change, problem):
    docs = manifests(**change)
    problems = winget.validate_manifests(docs)
    assert any(problem.split(":")[0] in p for p in problems), problems
    schema_found = []
    for kind, doc in docs.items():
        schema = load_schema(kind)
        schema_found += schema_errors(doc, schema, schema)
    # Our checker is never more lenient than the official schema.
    assert schema_found or problems


def test_missing_documents_and_bad_types():
    assert "version: missing" in winget.validate_manifests({})
    docs = manifests()
    docs["installer"]["Installers"] = "nope"
    docs["installer"]["NestedInstallerType"] = "deb"
    problems = winget.validate_manifests(docs)
    assert any("NestedInstallerType" in p for p in problems)
    docs = manifests()
    docs["version"]["ManifestType"] = "installer"
    docs["version"]["ManifestVersion"] = "1.0.0"
    assert len(winget.validate_manifests(docs)) == 2
    docs = manifests()
    del docs["installer"]["InstallerType"]
    assert any("InstallerType: required" in p for p in winget.validate_manifests(docs))


def test_yaml_files_are_written_with_schema_header(tmp_path):
    docs = manifests(installer_type="zip", nested_path="App/App.exe", command_alias="app")
    paths = winget.write_manifests(docs, str(tmp_path / "w"))
    names = sorted(os.path.basename(p) for p in paths)
    assert names == ["AbdulkarimAlaboud.PythonToExe.installer.yaml",
                     "AbdulkarimAlaboud.PythonToExe.locale.en-US.yaml",
                     "AbdulkarimAlaboud.PythonToExe.yaml"]
    text = open(paths[1], encoding="utf-8").read()
    assert text.startswith("# Created with Python to EXE Converter\n"
                           "# yaml-language-server: $schema=https://aka.ms/"
                           "winget-manifest.installer.1.28.0.schema.json\n")
    assert 'PackageVersion: "1.6.0"' in text
    assert "Installers:\n- Architecture: x64\n  InstallerUrl: " in text
    assert "NestedInstallerFiles:\n- RelativeFilePath: App/App.exe\n  PortableCommandAlias: app" \
        in text
    locale = open(paths[2], encoding="utf-8").read()
    assert '"عبدالكريم العبود"' in locale  # non-ASCII text kept readable, quoted
    assert "ManifestType: defaultLocale" in locale


def test_yaml_round_trips_through_a_real_parser(tmp_path):
    yaml = pytest.importorskip("yaml")
    docs = manifests(publisher='Quote "me": yes', short_description="true")
    for path in winget.write_manifests(docs, str(tmp_path)):
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
        kind = loaded["ManifestType"]
        assert loaded == json.loads(json.dumps(docs[kind]))


@pytest.mark.parametrize("value,expected", [
    ("plain text", "plain text"),
    ("1.6.0", '"1.6.0"'),
    ("yes", '"yes"'),
    ("a: b", '"a: b"'),
    ("x #y", '"x #y"'),
    ("https://x", '"https://x"'),
    ("", '""'),
    (True, "true"),
    (3, "3"),
    ("trailing ", '"trailing "'),
])
def test_yaml_scalars(value, expected):
    assert winget.yaml_scalar(value) == expected


def test_choose_installer_and_architecture():
    assert winget.choose_installer("S.exe", "A.exe", "Z.zip") == ("S.exe", "inno")
    assert winget.choose_installer("", "A.exe", "Z.zip") == ("A.exe", "portable")
    assert winget.choose_installer("", "linux-binary", "Z.zip") == ("Z.zip", "zip")
    assert winget.choose_installer() == (None, "")
    assert winget.architecture_for("x86") == "x86"
    assert winget.architecture_for("any") == "neutral"
    assert winget.architecture_for("") == "x64"
