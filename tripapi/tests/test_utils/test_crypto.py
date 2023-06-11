from utils.base.crypto import hash_digest
import pytest


@pytest.mark.parametrize(
    "value",
    [
        ({"a": '1'},),
        ([1],),
        ((1,),),
        (1,),
        ("1",),
        (1.4,),
    ]
)
def test_hash_digest(value):
    assert len(hash_digest(value)) > 1
