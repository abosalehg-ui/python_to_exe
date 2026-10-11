"""The runtime's licence verifier: round trip, tampering, wrong key, expiry,
malformed input, features. Signing comes from the converter side
(``core/update_signing.sign``); the runtime only ever verifies."""

import datetime
import json

import pytest

from p2e_runtime import config as rconfig
from p2e_runtime import license as lic
from py2exe_gui.core.update_signing import new_signing_key, sign

KEY = new_signing_key()
OTHER = new_signing_key()
TODAY = datetime.date(2026, 10, 10)


def issue(key=KEY, **fields):
    payload = {"name": "Sara", "email": "sara@example.com", "product": "MyApp",
               "expiry": "", "features": ["pro"]}
    payload.update(fields)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return lic.encode_key(data, sign(key.seed, data))


# ── Round trip and the text form ───────────────────────────────────────────


def test_round_trip_returns_the_payload():
    info = lic.verify(issue(), KEY.public_hex, "MyApp", today=TODAY)
    assert info == lic.LicenseInfo("Sara", "sara@example.com", "MyApp", "", ("pro",))
    assert info.has_feature("pro") and not info.has_feature("enterprise")
    assert not info.expires and info.days_left(TODAY) is None


def test_key_is_grouped_base32():
    key = issue()
    groups = key.split("-")
    assert all(len(g) == lic.GROUP_SIZE for g in groups[:-1])
    assert 1 <= len(groups[-1]) <= lic.GROUP_SIZE
    assert set("".join(groups)) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


@pytest.mark.parametrize("mangle", [
    str.lower,
    lambda k: k.replace("-", ""),
    lambda k: k.replace("-", " \n\t"),
    lambda k: "  " + k.replace("-", " - ") + "\r\n",
    lambda k: k.replace("O", "0").replace("I", "1").replace("B", "8"),
])
def test_case_whitespace_dashes_and_lookalikes_are_tolerated(mangle):
    key = issue()
    assert lic.verify(mangle(key), KEY.public_hex, "MyApp", today=TODAY) is not None


def test_unicode_names_survive():
    info = lic.verify(issue(name="سارة العبود", email="s@مثال.com"), KEY.public_hex, today=TODAY)
    assert info.name == "سارة العبود" and info.email == "s@مثال.com"


def test_public_key_as_bytes_or_hex_in_any_case():
    key = issue()
    assert lic.verify(key, bytes.fromhex(KEY.public_hex), today=TODAY)
    assert lic.verify(key, KEY.public_hex.upper(), today=TODAY)


# ── Bad signatures, wrong key, wrong product ───────────────────────────────


def test_tampered_payload_is_rejected():
    payload = json.dumps({"name": "Sara", "email": "", "product": "MyApp", "expiry": "",
                          "features": []}).encode()
    signature = sign(KEY.seed, payload)
    forged = payload.replace(b'"features": []', b'"features": ["pro"]')
    assert lic.verify(lic.encode_key(forged, signature), KEY.public_hex) is None
    assert lic.verify(lic.encode_key(payload, signature), KEY.public_hex) is not None


def test_a_flipped_letter_is_rejected():
    key = issue()
    # Change one letter in the payload region (the end of the key).
    letters = list(key.replace("-", ""))
    letters[-5] = "A" if letters[-5] != "A" else "B"
    assert lic.verify("".join(letters), KEY.public_hex) is None


def test_wrong_public_key_is_rejected():
    assert lic.verify(issue(), OTHER.public_hex, "MyApp") is None
    assert lic.inspect(issue(), OTHER.public_hex)[0] == lic.STATUS_INVALID


def test_wrong_product_is_rejected_but_readable():
    status, info = lic.inspect(issue(), KEY.public_hex, "OtherApp", today=TODAY)
    assert status == lic.STATUS_WRONG_PRODUCT and info.product == "MyApp"
    assert lic.verify(issue(), KEY.public_hex, "OtherApp", today=TODAY) is None


def test_product_is_only_checked_when_asked():
    assert lic.verify(issue(), KEY.public_hex, today=TODAY) is not None
    assert lic.verify(issue(), KEY.public_hex, "", today=TODAY) is not None


# ── Expiry ─────────────────────────────────────────────────────────────────


def test_expired_license_is_none_but_inspect_names_the_date():
    key = issue(expiry="2026-10-09")
    assert lic.verify(key, KEY.public_hex, today=TODAY) is None
    status, info = lic.inspect(key, KEY.public_hex, today=TODAY)
    assert status == lic.STATUS_EXPIRED and info.expiry == "2026-10-09"
    assert info.days_left(TODAY) == -1


def test_the_expiry_day_itself_is_still_valid():
    info = lic.verify(issue(expiry="2026-10-10"), KEY.public_hex, today=TODAY)
    assert info is not None and info.days_left(TODAY) == 0 and info.expires
    assert lic.verify(issue(expiry="2026-10-11"), KEY.public_hex, today=TODAY).days_left(TODAY) == 1


def test_expiry_defaults_to_today(monkeypatch):
    class FixedDate(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(2030, 1, 1)

    monkeypatch.setattr(lic.datetime, "date", FixedDate)
    assert lic.verify(issue(expiry="2029-12-31"), KEY.public_hex) is None
    assert lic.verify(issue(expiry="2030-01-01"), KEY.public_hex) is not None


@pytest.mark.parametrize("expiry", ["2026-13-01", "tomorrow", "2026/10/10", "20261010", 5])
def test_malformed_expiry_is_invalid(expiry):
    assert lic.inspect(issue(expiry=expiry), KEY.public_hex)[0] == lic.STATUS_INVALID


# ── Garbage in ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("garbage", [
    "", "   ", "-----", "ABCDE-FGHIJ", "not a key at all!!", "A" * 200, "\x00\xff",
    None, 42, b"bytes", ["list"], "A" * 20000,
])
def test_garbage_never_raises(garbage):
    assert lic.verify(garbage, KEY.public_hex) is None
    assert lic.inspect(garbage, KEY.public_hex) == (lic.STATUS_INVALID, None)


@pytest.mark.parametrize("public", ["", "zz" * 32, "ab" * 31, b"short", None, 7])
def test_bad_public_key_never_raises(public):
    assert lic.verify(issue(), public) is None


def test_unknown_format_version_is_rejected():
    import base64

    payload = b'{"name":"a","email":"","product":"p","features":[]}'
    raw = bytes([2]) + sign(KEY.seed, payload) + payload
    key = base64.b32encode(raw).decode().rstrip("=")
    assert lic.verify(key, KEY.public_hex) is None


@pytest.mark.parametrize("payload", [
    b"[]", b"null", b"\xff\xfe", b"{", b'{"name": 1, "product": "p"}',
    b'{"name": "a", "product": ""}', b'{"name": "a", "product": "p", "features": "pro"}',
    b'{"name": "a", "product": "p", "features": [1]}',
    b'{"name": "a", "product": "p", "features": ["bad feature!"]}',
    b'{"name": "a", "product": "p", "email": ["x"]}',
])
def test_signed_but_malformed_payload_is_invalid(payload):
    key = lic.encode_key(payload, sign(KEY.seed, payload))
    assert lic.inspect(key, KEY.public_hex) == (lic.STATUS_INVALID, None)


def test_missing_optional_fields_default():
    payload = b'{"name": "a", "product": "p"}'
    info = lic.verify(lic.encode_key(payload, sign(KEY.seed, payload)), KEY.public_hex)
    assert info == lic.LicenseInfo("a", "", "p", "", ())


def test_encode_rejects_a_short_signature():
    with pytest.raises(ValueError):
        lic.encode_key(b"{}", b"short")


# ── check(): the bundled configuration ─────────────────────────────────────


def test_check_uses_the_bundled_product_and_key():
    config = rconfig.parse_config({
        "format": 1, "app": {"name": "MyApp"},
        "services": {"licensing": {"product": "MyApp", "public_key": KEY.public_hex}},
    })
    assert config.licensing.product == "MyApp"
    assert "licensing" in config.enabled()
    assert lic.check(issue(), config, today=TODAY) is not None
    assert lic.check(issue(product="Other"), config, today=TODAY) is None
    assert lic.check(issue(key=OTHER), config, today=TODAY) is None


def test_check_without_a_licensing_section_is_none():
    config = rconfig.parse_config({"format": 1, "app": {"name": "MyApp"}, "services": {}})
    assert config.licensing is None
    assert lic.check(issue(), config) is None
    assert lic.check(issue(), None) is None  # no bundled file in the test process


def test_licensing_section_rejects_a_bad_key():
    with pytest.raises(ValueError):
        rconfig.parse_config({"format": 1, "services": {"licensing": {"public_key": "xyz"}}})
    with pytest.raises(ValueError):
        rconfig.parse_config({"format": 1, "services": {"licensing": {"product": 3}}})
