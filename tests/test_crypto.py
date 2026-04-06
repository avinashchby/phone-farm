"""Tests for encryption/decryption of credentials."""

from phone_farm.crypto import derive_key, encrypt, decrypt


def test_round_trip_encryption() -> None:
    key = derive_key("master-password", salt=b"fixed-salt-for-test")
    plaintext = "super-secret-app-password"
    ciphertext = encrypt(plaintext, key)
    assert ciphertext != plaintext
    assert decrypt(ciphertext, key) == plaintext


def test_wrong_key_fails_to_decrypt() -> None:
    import pytest
    key1 = derive_key("password-one", salt=b"fixed-salt-for-test")
    key2 = derive_key("password-two", salt=b"fixed-salt-for-test")
    ciphertext = encrypt("secret", key1)
    with pytest.raises(Exception):
        decrypt(ciphertext, key2)


def test_derive_key_deterministic() -> None:
    salt = b"same-salt"
    k1 = derive_key("pw", salt=salt)
    k2 = derive_key("pw", salt=salt)
    assert k1 == k2


def test_derive_key_different_salts_differ() -> None:
    k1 = derive_key("pw", salt=b"salt-a")
    k2 = derive_key("pw", salt=b"salt-b")
    assert k1 != k2
