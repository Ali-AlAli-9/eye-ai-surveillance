import threading

_lock = threading.Lock()
_engine = None
_booting = False


def get_engine():
    with _lock:
        return _engine


def set_engine(engine):
    global _engine
    with _lock:
        _engine = engine


def clear_engine():
    global _engine
    with _lock:
        _engine = None


def set_booting(value):
    global _booting
    with _lock:
        _booting = value


def is_booting():
    with _lock:
        return _booting
