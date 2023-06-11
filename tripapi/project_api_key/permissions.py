from account.models import User
from django.conf import settings
from rest_framework import permissions
from rest_framework_simplejwt.models import TokenUser
from utils.base.logger import err_logger, logger  # noqa

from .models import ProjectApiKey


def check_user_set(request):
    # Check if the user is a Token user and set user to request
    if isinstance(request.user, TokenUser):
        try:
            # Get the real user object
            user = User.objects.get(id=request.user.id)
            request.user = user
        except User.DoesNotExist:
            return False


class HasStaffProjectAPIKey(permissions.BasePermission):
    """
    This is a permission class to validate api keys
    belongs to staffs and admins only
    """

    def has_permission(self, request, view):
        # logger.debug(request.META)
        key, api_obj = self.validate_apikey(request)

        if key:
            if check_user_set(request) is False:
                return False

            try:
                return api_obj.user.staff or api_obj.user.admin
            except Exception as e:
                err_logger.exception(e)

    def validate_apikey(self, request):
        custom_header = settings.API_KEY_HEADER
        custom_sec_header = settings.API_SEC_KEY_HEADER

        pub_key = self.get_from_header(request, custom_header)
        sec_key = self.get_from_header(request, custom_sec_header)

        # The the Project api key obj the pub_key belongs to
        try:
            api_obj = ProjectApiKey.objects.select_related(
                'user').get(pub_key=pub_key)
        except ProjectApiKey.DoesNotExist:
            return False, None

        return api_obj.check_password(sec_key), api_obj

    def get_from_header(self, request, name):
        return request.META.get(name) or None


class HasProjectAPIKey(HasStaffProjectAPIKey):
    """
    This is a permission class to validate api keys is valid
    """

    def has_permission(self, request, view):
        key, api_obj = self.validate_apikey(request)

        if key:
            if check_user_set(request) is False:
                return False
            try:
                return api_obj.user.active
            except Exception as e:
                err_logger.exception(e)


# Create instance to use on auth permissions and others
has_staff_key = HasStaffProjectAPIKey()
has_project_key = HasProjectAPIKey()
