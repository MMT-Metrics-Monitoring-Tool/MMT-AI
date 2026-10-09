import datetime

import jwt
import pytest

from auth import Authenticator, AuthError


SECRET = "test-secret-key-that-is-at-least-32-bytes"


def make_token(**claims):
    payload = {"sub": "22", "project_ids": [1, 5], "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)}
    payload.update(claims)
    return jwt.encode({k: v for k, v in payload.items() if v is not None}, SECRET, algorithm="HS256")


def test_valid_token_gives_user_and_projects():
    principal = Authenticator(SECRET, "HS256").verify(make_token(name="Maija"))
    assert principal.user_id == "22"
    assert principal.name == "Maija"
    assert principal.can_access(5) and not principal.can_access(2)


def test_bearer_prefix_is_accepted():
    assert Authenticator(SECRET, "HS256").verify("Bearer " + make_token()).user_id == "22"


def test_expired_token_is_flagged():
    token = make_token(exp=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1))
    with pytest.raises(AuthError) as error:
        Authenticator(SECRET, "HS256").verify(token)
    assert error.value.expired


@pytest.mark.parametrize("token", [
    None,
    "not-a-jwt",
    jwt.encode({"sub": "22", "project_ids": [1], "exp": 9999999999}, "another-secret-of-at-least-32-bytes!", algorithm="HS256"),
    jwt.encode({"project_ids": [1], "exp": 9999999999}, SECRET, algorithm="HS256"),
    jwt.encode({"sub": "22", "project_ids": [1]}, SECRET, algorithm="HS256"),
    jwt.encode({"sub": "22", "project_ids": ["x"], "exp": 9999999999}, SECRET, algorithm="HS256"),
])
def test_invalid_tokens_are_rejected(token):
    with pytest.raises(AuthError):
        Authenticator(SECRET, "HS256").verify(token)


def test_dev_tokens_only_in_dev_mode():
    with pytest.raises(AuthError):
        Authenticator(SECRET, "HS256").issue_dev_token()
    dev = Authenticator(SECRET, "HS256", dev_mode=True, dev_project_ids=frozenset({3}))
    assert dev.verify(dev.issue_dev_token()).project_ids == {3}
