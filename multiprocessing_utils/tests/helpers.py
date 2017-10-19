import multiprocessing
import threading
from time import sleep


class ConcurrentAccessException(Exception):
    pass


class ThreadingMixin(object):
    def get_concurrency_class(self):
        return threading.Thread

    def get_event_class(self):
        return threading.Event

    def get_lock_class(self):
        return threading.Lock

    def get_shared_list(self):
        return []


class MultiprocessingMixin(object):
    manager = multiprocessing.Manager()

    def get_concurrency_class(self):
        return multiprocessing.Process

    def get_event_class(self):
        return multiprocessing.Event

    def get_lock_class(self):
        return multiprocessing.Lock

    def get_shared_list(self):
        return self.manager.list()


class NotThreadSafe(object):
    unguarded = multiprocessing.Value('i')

    @classmethod
    def up(cls):
        if cls.unguarded.value:
            raise ConcurrentAccessException("lol threads")  # pragma: no cover
        cls.unguarded.value += 1

    @classmethod
    def down(cls):
        if not cls.unguarded.value:
            raise ConcurrentAccessException("lol threads")  # pragma: no cover
        cls.unguarded.value -= 1

    @classmethod
    def bounce(cls):
        cls.up()
        sleep(0.1)
        cls.down()
