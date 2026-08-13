from src.application.use_cases.manage_auth import _password_hash, _password_valid, _token_hash


def test_password_hash_is_salted_and_verifiable() -> None:
    first = _password_hash("correct horse battery staple")
    second = _password_hash("correct horse battery staple")

    assert first != second
    assert "correct horse" not in first
    assert _password_valid("correct horse battery staple", first)
    assert not _password_valid("wrong password", first)


def test_session_token_hash_is_stable_without_exposing_token() -> None:
    token = "private-session-token"
    digest = _token_hash(token)

    assert digest == _token_hash(token)
    assert token not in digest
