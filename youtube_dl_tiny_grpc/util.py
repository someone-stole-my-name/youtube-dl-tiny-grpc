import signal

from concurrent.futures import ProcessPoolExecutor as PoolExecutor


def port_is_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def guess_type(value):
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return bool(value)
    except ValueError:
        pass
    try:
        return str(value)
    except ValueError:
        pass
    return None


class ProcessPoolExecutor(PoolExecutor):
    """ A ProcessPoolExecutor that ignores SIGINT signals. """

    def __init__(self, *args, **kwargs):
        kwargs['initializer'] = ProcessPoolExecutor.initializer
        super().__init__(*args, **kwargs)

    @staticmethod
    def initializer():
        signal.signal(signal.SIGINT, signal.SIG_IGN)
