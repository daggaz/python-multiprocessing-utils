from time import sleep
from unittest import TestCase

import six

from multiprocessing_utils import SharedRLock
from multiprocessing_utils.tests.test_shared_lock import (
    SharedLockTestCaseMixin,
)

from multiprocessing_utils.tests.helpers import (
    ThreadingMixin,
    MultiprocessingMixin,
)


class SharedRLockMixin(object):
    def get_shared_lock(self):
        return SharedRLock()

    def test_lock_upgrade_fails_with_reentry(self):
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertFalse(hasattr(lock._state, 'exclusive'))
        self.assertFalse(hasattr(lock._state, 'reference_count'))
        with lock:
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, False)
            self.assertEqual(lock._state.reference_count, 1)
            assert_raises = six.assertRaisesRegex(
                self,
                ValueError,
                "Cannot upgrade a shared lock to an exclusive lock",
            )
            with assert_raises:
                with lock.exclusive():
                    pass  # pragma: no cover
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, False)
            self.assertEqual(lock._state.reference_count, 1)
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertEqual(lock._state.exclusive, None)
        self.assertEqual(lock._state.reference_count, 0)

    def test_reentry_shared(self):
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertFalse(hasattr(lock._state, 'exclusive'))
        self.assertFalse(hasattr(lock._state, 'reference_count'))
        with lock:
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, False)
            self.assertEqual(lock._state.reference_count, 1)
            with lock.shared():
                self.assertEqual(lock._num_processes.value, 1)
                self.assertEqual(lock._semaphore.get_value(), 0)
                self.assertEqual(lock._state.exclusive, False)
                self.assertEqual(lock._state.reference_count, 2)
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, False)
            self.assertEqual(lock._state.reference_count, 1)
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertEqual(lock._state.exclusive, None)
        self.assertEqual(lock._state.reference_count, 0)

    def test_reentry_exclusive(self):
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertFalse(hasattr(lock._state, 'exclusive'))
        self.assertFalse(hasattr(lock._state, 'reference_count'))
        with lock.exclusive():
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, True)
            self.assertEqual(lock._state.reference_count, 1)
            with lock.shared():
                self.assertEqual(lock._num_processes.value, 1)
                self.assertEqual(lock._semaphore.get_value(), 0)
                self.assertEqual(lock._state.exclusive, True)
                self.assertEqual(lock._state.reference_count, 2)
                with lock.exclusive():
                    self.assertEqual(lock._num_processes.value, 1)
                    self.assertEqual(lock._semaphore.get_value(), 0)
                    self.assertEqual(lock._state.exclusive, True)
                    self.assertEqual(lock._state.reference_count, 3)
                    with lock:
                        self.assertEqual(lock._num_processes.value, 1)
                        self.assertEqual(lock._semaphore.get_value(), 0)
                        self.assertEqual(lock._state.exclusive, True)
                        self.assertEqual(lock._state.reference_count, 4)
                    self.assertEqual(lock._num_processes.value, 1)
                    self.assertEqual(lock._semaphore.get_value(), 0)
                    self.assertEqual(lock._state.exclusive, True)
                    self.assertEqual(lock._state.reference_count, 3)
                self.assertEqual(lock._num_processes.value, 1)
                self.assertEqual(lock._semaphore.get_value(), 0)
                self.assertEqual(lock._state.exclusive, True)
                self.assertEqual(lock._state.reference_count, 2)
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, True)
            self.assertEqual(lock._state.reference_count, 1)
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertEqual(lock._state.exclusive, None)
        self.assertEqual(lock._state.reference_count, 0)

    def test_the_lot_with_reentry(self):
        """
        Test exclusive access to lock is indeed exclusive (thread safe) even
        when shared accesses are currently executing
        (i.e. exclusive lock is requested during shared lock sections, but
        doesn't acquire until all shared locks are released AND shared lock
        is requested during an the same exclusive lock section, but doesn't
        acquire until the exclusive lock is released)
        """
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        errors = self.get_shared_list()
        worker_lock = self.get_lock_class()()
        N = 5
        locking = [self.get_event_class()() for _ in range(N)]
        locked = [self.get_event_class()() for _ in range(N)]
        some_value = self.get_shared_list()
        some_value.append(0)

        def shared_lock_target(i):
            try:
                locking[i].set()
                with lock:
                    with lock:
                        locked[i].set()
                        sleep(0.1)
                        with worker_lock:
                            some_value[0] += 1
            except Exception as e:  # pragma: no cover
                errors.append(e)

        # start some shared locking workers
        workers = []
        for n in range(N):
            worker = self.get_concurrency_class()(
                target=shared_lock_target,
                args=(n,),
            )
            workers.append(worker)

        for worker in workers:
            worker.start()

        # wait for all shared locks to acquire
        for event in locked:
            event.wait()
            event.clear()

        # at this point, all shared lock workers should be sleeping, so
        # won't have updated some_value
        self.assertEqual(some_value[0], 0)

        # attempt to exclusively lock
        # should block here till all shared locks are released
        with lock.exclusive():
            with lock.shared():
                with lock.exclusive():
                    with lock:
                        # shared workers should have all updated some_value
                        self.assertEqual(some_value[0], N)

                        # start another set of shared locking workers
                        inner_workers = []
                        for n in range(N):
                            worker = self.get_concurrency_class()(
                                target=shared_lock_target,
                                args=(n,),
                            )
                            inner_workers.append(worker)
                            workers.append(worker)

                        for worker in inner_workers:
                            worker.start()

                        # wait for all shared locks to block(ish)
                        for event in locking:
                            event.wait()
                            event.clear()
                        sleep(0.1)

                        # check that the shared lock workers didn't
                        # update some_value
                        self.assertEqual(some_value[0], N)

        # wait for all shared lock workers to complete
        for worker in workers:
            worker.join()

        # shared workers should have all updated some_value again
        self.assertEqual(some_value[0], N*2)
        self.assertListEqual(list(errors), [])


class TestSharedRLockThreading(SharedRLockMixin, ThreadingMixin,
                               SharedLockTestCaseMixin, TestCase):
    pass


class TestSharedRLockMultiprocessing(SharedRLockMixin, MultiprocessingMixin,
                                     SharedLockTestCaseMixin, TestCase):
    pass
