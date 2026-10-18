from app.core.security import (
    hash_password,
    normalize_username,
    verify_password,
)


def test_username_normalization() -> None:
    assert normalize_username("  Admin.User  ") == "Admin.User"


def test_argon2_password_hash_roundtrip() -> None:
    password = "ExamplePass123!"
    password_hash = hash_password(password)

    assert password_hash.startswith("$argon2id$")
    assert verify_password(password_hash, password) is True
    assert verify_password(password_hash, "wrong-password") is False
