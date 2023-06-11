from typing import TypeVar
import pytest
from account.models import User

T = TypeVar('T', bound=User)


@pytest.mark.django_db
def test_create_base_user():
    user: T = User.objects.create_base_user(
        email='test@example.com',
    )
    user.refresh_from_db()
    assert user.email == 'test@example.com'
    assert user.active is True
    assert user.staff is False
    assert user.admin is False
    assert user.has_usable_password() is False


@pytest.mark.django_db
def test_create_user():
    user: T = User.objects.create_user(
        email='test@example.com',
        password='randopass',
    )
    user.refresh_from_db()
    assert user.email == 'test@example.com'
    assert user.active is True
    assert user.staff is False
    assert user.admin is False
    assert user.has_usable_password() is True


@pytest.mark.django_db
def test_create_user_password_required():
    with pytest.raises(ValueError, match='provide a password'):
        User.objects.create_user(
            email='test@example.com'
        )


@pytest.mark.django_db
def test_create_staff():
    user: T = User.objects.create_staff(
        email='test@example.com',
        password='randopass',
    )
    user.refresh_from_db()
    assert user.email == 'test@example.com'
    assert user.active is True
    assert user.staff is True
    assert user.admin is False
    assert user.has_usable_password() is True


@pytest.mark.django_db
def test_create_superuser():
    user: T = User.objects.create_superuser(
        email='test@example.com',
        password='randopass',
    )
    user.refresh_from_db()
    assert user.email == 'test@example.com'
    assert user.active is True
    assert user.staff is True
    assert user.admin is True
    assert user.has_usable_password() is True


@pytest.mark.django_db
def test_get_staffs(basic_user, admin_user):
    staffs = User.objects.get_staffs()
    assert staffs.count() == 1


@pytest.mark.django_db
def test_get_admins(basic_user, admin_user):
    staffs = User.objects.get_admins()
    assert staffs.count() == 1
