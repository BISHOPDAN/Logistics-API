import re
from django.conf import settings

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from utils.base.general import invalid_str, convert_bytes_to_mb


def validate_special_char(value):
    if invalid_str(value):
        raise ValidationError(
            _('Must not contain special characters'),
            params={'value': value},
        )


def validate_phone(phone=''):
    pattern = r'[\+\d]?(\d{2,3}[-\.\s]??\d{2,3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})' # noqa
    s = re.match(pattern, phone)
    if s is None:
        raise ValidationError(_('Must provide a valid phone number'),)


def validate_file_size(max_file_size=settings.MAX_IMAGE_UPLOAD_SIZE):

    def func(file):
        if file.size > max_file_size:
            max = round(convert_bytes_to_mb(max_file_size), 2)
            size = round(convert_bytes_to_mb(file.size), 2)
            raise ValidationError(
                _(f"File uploaded to large. Size must be \
{max}mb, uploaded file is {size}mb."))

    return func


def validate_rating_level(val):
    if val >= 0 or val <= 5:
        return True
    raise ValidationError(_('Must be between 0 and 5'),)
