from project_api_key.permissions import has_staff_key
from rest_framework.permissions import BasePermission, IsAuthenticated
from utils.base.general import check_raise_exc
from utils.base.logger import err_logger, logger  # noqa


class IsAuthenticatedAdmin(BasePermission):
    def has_permission(self, request, view):
        # Get the user, if the user is staff or admin (open access)
        try:
            if request.user.is_authenticated:
                user = request.user
                if user.staff or user.admin:
                    return True
        except Exception as e:
            err_logger.exception(e)


is_auth_admin = IsAuthenticatedAdmin()
is_auth_normal = IsAuthenticated()


class SuperPerm(BasePermission):
    """
    Permission to check if user uses a staff project
    api key or is an authenticated admin
    """

    def has_permission(self, request, view):
        # Check if the user has staff project api key
        if has_staff_key.has_permission(request, view):
            return True

        # Check if the user is an authenticated admin
        if is_auth_admin.has_permission(request, view):
            return True


class BasicPerm(BasePermission):
    """
    Permissions to check if user has a project
    staff api key and is authenticated
    Or user is authenticated admin
    """

    def has_permission(self, request, view):
        # Check if the user has project api key
        if has_staff_key.has_permission(request, view):

            # Check if the user is authenticated
            if is_auth_normal.has_permission(request, view):
                return True

        # Check if the user is an authenticated admin
        if is_auth_admin.has_permission(request, view):
            return True


class AuthUserIsTransporter(BasicPerm):
    """
    This checks if the user has BasicPerm permission
    and is a transporter
    """

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            try:
                request.user.transporter
                return True
            except Exception as e:
                check_raise_exc(e)


class AuthUserIsLogistic(BasicPerm):
    """
    This checks if the user has BasicPerm permission
    and is a logistic
    """

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            try:
                request.user.logistic
                return True
            except Exception as e:
                check_raise_exc(e)


class AuthUserIsPartner(BasicPerm):
    """
    This checks if the user has BasicPerm permission
    and is a partner, transporter or logistics
    """

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            try:
                request.user.transporter
                return True
            except Exception as e:
                check_raise_exc(e)

            try:
                request.user.logistic
                return True
            except Exception as e:
                check_raise_exc(e)
