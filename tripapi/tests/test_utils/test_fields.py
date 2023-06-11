import pytest
from django.db import models
from model_bakery import baker
from utils.base.fields import TrackingCodeField, ModelBakeryGenerator
from django.core.checks import Error
from tests.models import ModelTrackingCode


class TestModelBakeryGenerator:
    def test_register(self):
        ModelBakeryGenerator.register(baker)

    def test_baker_gen_func(self):
        with pytest.raises(NotImplementedError):
            ModelBakeryGenerator.baker_gen_func()


@pytest.mark.django_db
class TestTrackingCodeField:

    Field = TrackingCodeField

    def test_baker_gen_func(self):
        value = self.Field.baker_gen_func()
        assert value.startswith(self.Field.default_prefix)

    def test_baker_generate(self):
        obj = baker.make(ModelTrackingCode)
        assert obj.code.startswith("TEST")

    @pytest.mark.parametrize(
        'prefix, error_text, error_code',
        [
            ("xxxxxxxxxxx", f"'prefix' length must not be greater than \
{Field.prefix_max_length}.", "E002"),
            (1, "'prefix' must be a string.", "E001"),
        ]
    )
    def test_tracking_code(self, prefix, error_text, error_code):

        class Model(models.Model):
            field = self.Field(prefix=prefix)

        tracking_code = Model._meta.get_field("field")
        errors = tracking_code.check()
        expected_errors = [
            Error(
                error_text,
                obj=tracking_code,
                id='tripapi.' + error_code,
            )
        ]
        assert expected_errors == errors

    def test_tracking_code_no_error(self):

        class Model(models.Model):
            field = self.Field(prefix="xxx")

        tracking_code = Model._meta.get_field("field")
        errors = tracking_code.check()
        expected_errors = []
        assert expected_errors == errors

    def test_tracking_code_deconstruct(self):

        field = self.Field(prefix="xxx")

        _, path, args, kwargs = field.deconstruct()
        assert path == 'utils.base.fields.TrackingCodeField'
        assert args == []
        assert kwargs.get('prefix') == 'xxx'

    def test_tracking_code_pre_save(self):

        class Model(models.Model):
            field = self.Field(prefix="xxx")

        obj = Model()
        field = obj._meta.get_field("field")
        computed = field.pre_save(obj, True)
        assert len(computed) > 0
