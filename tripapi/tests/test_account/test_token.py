import pytest
from account.api.base.tokens import account_confirm_token


@pytest.mark.django_db
def test_account_make_token(basic_user):
    token = account_confirm_token.make_token(basic_user)
    assert account_confirm_token.check_token(basic_user, token) is True


@pytest.mark.django_db
def test_account_check_token(admin_user, basic_user):
    token = account_confirm_token.make_token(basic_user)
    assert account_confirm_token.check_token(admin_user, token) is False
    assert account_confirm_token.check_token(basic_user, token) is True
