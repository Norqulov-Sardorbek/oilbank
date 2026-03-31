import threading
from contextlib import contextmanager

_local = threading.local()

def signals_enabled():
    return not getattr(_local, "disable_signals", False)

@contextmanager
def disable_signals():
    _local.disable_signals = True
    try:
        yield
    finally:
        _local.disable_signals = False
