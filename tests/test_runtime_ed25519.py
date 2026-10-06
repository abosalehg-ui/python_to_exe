"""Ed25519: the runtime's verifier and the converter's signer, on RFC 8032 §7.1.

The vectors are the RFC's own (tests/data/rfc8032_ed25519.json, extracted
verbatim from the RFC text). Both halves must reproduce every one of them:
the signer byte for byte (Ed25519 is deterministic), the verifier by
accepting the signature and refusing any change to it.
"""

import json
import os

import pytest

from p2e_runtime import _ed25519
from py2exe_gui.core.update_signing import public_key_from_seed, sign

DATA = os.path.join(os.path.dirname(__file__), "data", "rfc8032_ed25519.json")
with open(DATA, encoding="utf-8") as _f:
    VECTORS = json.load(_f)["vectors"]


def test_all_five_rfc_vectors_are_present():
    assert [v["name"] for v in VECTORS] == [
        "TEST 1", "TEST 2", "TEST 3", "TEST 1024", "TEST SHA(abc)",
    ]
    assert len(bytes.fromhex(VECTORS[3]["message"])) == 1023


@pytest.mark.parametrize("vector", VECTORS, ids=[v["name"] for v in VECTORS])
def test_verify_accepts_rfc_vector(vector):
    assert _ed25519.verify(
        bytes.fromhex(vector["public"]),
        bytes.fromhex(vector["message"]),
        bytes.fromhex(vector["signature"]),
    )


@pytest.mark.parametrize("vector", VECTORS, ids=[v["name"] for v in VECTORS])
def test_signer_reproduces_rfc_vector(vector):
    seed = bytes.fromhex(vector["secret"])
    assert public_key_from_seed(seed).hex() == vector["public"]
    assert sign(seed, bytes.fromhex(vector["message"])).hex() == vector["signature"]


@pytest.mark.parametrize("vector", VECTORS, ids=[v["name"] for v in VECTORS])
def test_any_flipped_bit_is_rejected(vector):
    public = bytes.fromhex(vector["public"])
    message = bytes.fromhex(vector["message"])
    signature = bytes.fromhex(vector["signature"])
    for position in (0, 31, 32, 63):  # R and S, both ends
        tampered = bytearray(signature)
        tampered[position] ^= 0x01
        assert not _ed25519.verify(public, message, bytes(tampered))
    assert not _ed25519.verify(public, message + b"x", signature)
    if message:
        assert not _ed25519.verify(public, message[:-1], signature)


def test_wrong_key_is_rejected():
    first, second = VECTORS[0], VECTORS[1]
    assert not _ed25519.verify(
        bytes.fromhex(second["public"]),
        bytes.fromhex(first["message"]),
        bytes.fromhex(first["signature"]),
    )


def test_malleable_s_is_rejected():
    """S + L verifies the same equation; RFC 8032 requires refusing S >= L."""
    v = VECTORS[1]
    signature = bytes.fromhex(v["signature"])
    s = int.from_bytes(signature[32:], "little") + _ed25519.L
    forged = signature[:32] + s.to_bytes(32, "little")
    assert not _ed25519.verify(bytes.fromhex(v["public"]), bytes.fromhex(v["message"]), forged)


def test_non_canonical_point_encoding_is_rejected():
    # y = p (not reduced) is not a canonical encoding of any point.
    non_canonical = _ed25519.P.to_bytes(32, "little")
    assert _ed25519.point_decompress(non_canonical) is None
    v = VECTORS[0]
    assert not _ed25519.verify(
        non_canonical, bytes.fromhex(v["message"]), bytes.fromhex(v["signature"])
    )


def test_point_not_on_curve_is_rejected():
    # y = 2 has no matching x on edwards25519.
    assert _ed25519.point_decompress((2).to_bytes(32, "little")) is None


@pytest.mark.parametrize("public,signature", [
    (b"", b"\x00" * 64),
    (b"\x00" * 31, b"\x00" * 64),
    (b"\x00" * 32, b"\x00" * 63),
    ("not bytes", b"\x00" * 64),
    (b"\x00" * 32, None),
])
def test_malformed_input_is_false_not_an_exception(public, signature):
    assert _ed25519.verify(public, b"m", signature) is False


def test_round_trip_with_a_fresh_key():
    seed = os.urandom(32)
    public = public_key_from_seed(seed)
    message = b'{"version": "2.0.0"}\n'
    signature = sign(seed, message)
    assert _ed25519.verify(public, message, signature)
    assert not _ed25519.verify(public, message.replace(b"2.0.0", b"9.0.0"), signature)


def test_signer_rejects_bad_seed_length():
    with pytest.raises(ValueError):
        sign(b"short", b"m")
