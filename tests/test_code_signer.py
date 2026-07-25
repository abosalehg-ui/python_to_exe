"""Tests for the signtool command builder."""

from py2exe_gui.core.code_signer import (
    SigningConfig,
    build_signtool_command,
    redact_password,
)


def test_returns_error_when_disabled():
    cmd, err = build_signtool_command("/tmp/x.exe", SigningConfig(enabled=False))
    assert cmd is None
    assert err == "Signing is disabled"


def test_returns_error_when_exe_path_missing():
    cmd, err = build_signtool_command("", SigningConfig(enabled=True, cert_path="/c.pfx"))
    assert cmd is None
    assert "Executable" in err


def test_returns_error_when_cert_path_missing():
    cmd, err = build_signtool_command("/tmp/x.exe", SigningConfig(enabled=True))
    assert cmd is None
    assert "Certificate" in err


def test_minimal_command_includes_sign_and_exe():
    cmd, err = build_signtool_command(
        "/tmp/x.exe",
        SigningConfig(enabled=True, cert_path="/c.pfx"),
    )
    assert err is None
    assert cmd[0] == "signtool"
    assert cmd[1] == "sign"
    assert cmd[-1] == "/tmp/x.exe"


def test_command_includes_certificate_path():
    cmd, _ = build_signtool_command(
        "/tmp/x.exe",
        SigningConfig(enabled=True, cert_path="/path/cert.pfx"),
    )
    assert "/f" in cmd
    assert cmd[cmd.index("/f") + 1] == "/path/cert.pfx"


def test_command_includes_password_when_set():
    cmd, _ = build_signtool_command(
        "/tmp/x.exe",
        SigningConfig(enabled=True, cert_path="/c.pfx", cert_password="hunter2"),
    )
    assert "/p" in cmd
    assert cmd[cmd.index("/p") + 1] == "hunter2"


def test_command_omits_password_flag_when_blank():
    cmd, _ = build_signtool_command(
        "/tmp/x.exe",
        SigningConfig(enabled=True, cert_path="/c.pfx", cert_password=""),
    )
    assert "/p" not in cmd


def test_command_includes_timestamp_flags():
    cmd, _ = build_signtool_command(
        "/tmp/x.exe",
        SigningConfig(
            enabled=True,
            cert_path="/c.pfx",
            timestamp_url="http://timestamp.example.com",
        ),
    )
    assert "/tr" in cmd
    assert cmd[cmd.index("/tr") + 1] == "http://timestamp.example.com"
    assert "/td" in cmd  # timestamp digest


def test_command_includes_file_digest():
    cmd, _ = build_signtool_command(
        "/tmp/x.exe",
        SigningConfig(enabled=True, cert_path="/c.pfx", digest_algorithm="sha384"),
    )
    fd_idx = cmd.index("/fd")
    assert cmd[fd_idx + 1] == "sha384"


def test_description_added_when_set():
    cmd, _ = build_signtool_command(
        "/tmp/x.exe",
        SigningConfig(enabled=True, cert_path="/c.pfx", description="My App"),
    )
    assert "/d" in cmd
    assert cmd[cmd.index("/d") + 1] == "My App"


def test_custom_signtool_path_used():
    cmd, _ = build_signtool_command(
        "/tmp/x.exe",
        SigningConfig(
            enabled=True,
            cert_path="/c.pfx",
            signtool_path="C:/SDK/signtool.exe",
        ),
    )
    assert cmd[0] == "C:/SDK/signtool.exe"


def test_redact_password_replaces_password_token():
    cmd = ["signtool", "sign", "/f", "/c.pfx", "/p", "secret", "/tr", "http://ts", "exe"]
    redacted = redact_password(cmd)
    assert "secret" not in redacted
    assert redacted[redacted.index("/p") + 1] == "***"
    # Other tokens preserved.
    assert "/f" in redacted
    assert "exe" in redacted


def test_redact_password_handles_no_password():
    cmd = ["signtool", "sign", "/f", "/c.pfx", "exe"]
    assert redact_password(cmd) == cmd


def test_redact_password_handles_empty_list():
    assert redact_password([]) == []


# ── Certificate-store mode (keeps the password off the command line) ───────


def test_store_mode_uses_subject_name():
    cmd, error = build_signtool_command(
        "app.exe",
        SigningConfig(enabled=True, use_cert_store=True, cert_subject="Acme Ltd"),
    )
    assert error is None
    assert "/n" in cmd
    assert cmd[cmd.index("/n") + 1] == "Acme Ltd"


def test_store_mode_never_passes_a_password():
    cmd, _ = build_signtool_command(
        "app.exe",
        SigningConfig(
            enabled=True,
            use_cert_store=True,
            cert_subject="Acme Ltd",
            cert_password="hunter2",  # set but must not be used
        ),
    )
    assert "/p" not in cmd
    assert "hunter2" not in cmd


def test_store_mode_requires_a_subject():
    cmd, error = build_signtool_command(
        "app.exe", SigningConfig(enabled=True, use_cert_store=True)
    )
    assert cmd is None
    assert "subject" in error.lower()


def test_store_mode_ignores_missing_cert_path():
    """cert_path is irrelevant in store mode and must not block signing."""
    cmd, error = build_signtool_command(
        "app.exe",
        SigningConfig(enabled=True, use_cert_store=True, cert_subject="Acme", cert_path=""),
    )
    assert error is None
    assert cmd is not None


def test_store_mode_still_timestamps():
    cmd, _ = build_signtool_command(
        "app.exe",
        SigningConfig(enabled=True, use_cert_store=True, cert_subject="Acme"),
    )
    assert "/tr" in cmd
    assert "/fd" in cmd


def test_pfx_mode_is_still_the_default():
    cmd, error = build_signtool_command(
        "app.exe", SigningConfig(enabled=True, cert_path="/c.pfx", cert_password="pw")
    )
    assert error is None
    assert "/f" in cmd
    assert "/n" not in cmd
