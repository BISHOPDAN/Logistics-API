from utils.base.db import count_queries
import pytest
from tests.models import ModelText
from io import StringIO
import sys
import re


@pytest.mark.django_db
def test_count_queries():

    @count_queries()
    def create():
        ModelText.objects.bulk_create(
            [
                ModelText(name="test"),
                ModelText(name="test1"),
            ]
        )

    pattern = re.compile(r"Ran (\d )queries?")

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    create()
    sys.stdout = old_stdout
    computed = mystdout.getvalue().strip("\n")
    assert ModelText.objects.count() == 2
    assert pattern.search(computed)
