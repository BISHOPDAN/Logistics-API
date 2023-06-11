from hashlib import md5
from typing import Any


def hash_digest(val: Any):
    """Convert python datatype to md5 hash"""
    return md5(str(val).encode()).hexdigest()
