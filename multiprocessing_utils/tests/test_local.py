import threading
from unittest import TestCase

import multiprocessing

import multiprocessing_utils


class LocalTestCaseMixin(object):
    def test_local(self):
        local = multiprocessing_utils.local()
        self.assertFalse(hasattr(local, 'value'))
        self.assertRaises(AttributeError, getattr, local, 'value')
        local.value = 1
        self.assertTrue(hasattr(local, 'value'))

        def local_test_target():
            self.assertFalse(hasattr(local, 'value'))
            self.assertRaises(AttributeError, getattr, local, 'value')
            local.value = 2
            self.assertTrue(hasattr(local, 'value'))
            self.assertEqual(local.value, 2)
        worker = self.get_concurrency_class()(target=local_test_target)
        worker.start()
        worker.join()
        self.assertEqual(local.value, 1)

    def get_concurrency_class(self):
        raise NotImplementedError()  # pragma: no cover


class TestLocalThreading(LocalTestCaseMixin, TestCase):
    def get_concurrency_class(self):
        return threading.Thread


class TestLocalMultiprocessing(LocalTestCaseMixin, TestCase):
    def get_concurrency_class(self):
        return multiprocessing.Process
