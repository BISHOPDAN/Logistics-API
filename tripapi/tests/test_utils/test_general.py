from django.test import TestCase

from utils.base.general import add_queryset, merge_querysets, capture_output

from tests.models import ModelText

from functools import partial


class TestGeneral(TestCase):
    def setUp(self) -> None:
        for i in range(3):
            ModelText.objects.create(name=i)

    def test_count(self):
        count = ModelText.objects.count()
        self.assertEqual(count, 3)

    def test_capture_output(self):
        func = (lambda: print("test"))
        with capture_output(func) as output:
            assert output.strip("\n") == "test"

    def test_capture_output_complex(self):
        def func(value):
            print(value)
        partial_func = partial(func, "test")
        with capture_output(partial_func) as output:
            assert output.strip("\n") == "test"

    def test_add_queryset(self):
        q1 = ModelText.objects.filter(name='1')
        q2 = ModelText.objects.filter(name='2')
        q3 = add_queryset(q1, q2)
        self.assertEqual(q3.count(), 2)
        self.assertTrue(q3.filter(name='1').exists())
        self.assertTrue(q3.filter(name='2').exists())

    def test_merge_querysets(self):
        q1 = ModelText.objects.filter(name='0')
        q2 = ModelText.objects.filter(name='1')
        q3 = ModelText.objects.filter(name='2')
        q4 = merge_querysets(q1, q2, q3)
        self.assertEqual(q4.count(), 3)
        self.assertTrue(q4.filter(name='1').exists())
        self.assertTrue(q4.filter(name='2').exists())
        self.assertTrue(q4.filter(name='0').exists())
