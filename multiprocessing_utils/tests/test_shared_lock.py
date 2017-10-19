from time import sleep
from unittest import TestCase

import six

from multiprocessing_utils import SharedLock
from multiprocessing_utils.tests.helpers import (
    ThreadingMixin,
    MultiprocessingMixin,
    NotThreadSafe,
    ConcurrentAccessException,
)


class SharedLockTestCaseMixin(object):
    maxDiff = None

    def test_basic_shared(self):
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertFalse(hasattr(lock._state, 'exclusive'))
        with lock:
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, False)
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertEqual(lock._state.exclusive, None)

    def test_basic_exclusive(self):
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertFalse(hasattr(lock._state, 'exclusive'))
        with lock.exclusive():
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, True)
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertEqual(lock._state.exclusive, None)

    def test_lock_upgrade_fails(self):
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertFalse(hasattr(lock._state, 'exclusive'))
        with lock:
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, False)
            assert_raises = six.assertRaisesRegex(
                self,
                ValueError,
                "Cannot upgrade a shared lock to an exclusive lock"
            )
            with assert_raises:
                with lock.exclusive():
                    pass  # pragma: no cover
            self.assertEqual(lock._num_processes.value, 1)
            self.assertEqual(lock._semaphore.get_value(), 0)
            self.assertEqual(lock._state.exclusive, False)
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        self.assertEqual(lock._state.exclusive, None)

    def test_release_before_acquire(self):
        lock = self.get_shared_lock()
        with six.assertRaisesRegex(self, ValueError, "lock released too many times"):
            lock.release()

    def test_release_too_many_times(self):
        lock = self.get_shared_lock()
        with lock:
            pass  # pragma: no cover
        with six.assertRaisesRegex(self, ValueError, "lock released too many times"):
            lock.release()

    def test_shared_acquire_during_shared_locking(self):
        """
        Test shared access to lock is indeed shared (not thread safe)
        (i.e. all shared locked sections are parallelized)
        """

        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)

        concurrent_accesses = self.get_shared_list()
        errors = self.get_shared_list()

        def something():
            try:
                with lock:
                    # will raise ConcurrentAccessException if
                    #  called in a non thread safe manner
                    NotThreadSafe.bounce()
            except ConcurrentAccessException as e:
                concurrent_accesses.append(e)
            except Exception as e:  # pragma: no cover
                errors.append(e)

        workers = []
        for _ in range(20):
            workers.append(self.get_concurrency_class()(target=something))
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        # We want some concurrent accesses to have occured
        self.assertNotEqual(len(concurrent_accesses), 0)
        self.assertListEqual(list(errors), [])

    def test_exclusive_acquire_during_exclusive_locking(self):
        """
        Test exclusive access to lock is indeed exclusive (thread safe)
        (i.e. all exclusive locked sections are serialized)
        """
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        concurrent_accesses = self.get_shared_list()
        errors = self.get_shared_list()

        def something():
            try:
                with lock.exclusive():
                    # will raise ConcurrentAccessException if
                    # called in a non thread safe manner
                    NotThreadSafe.bounce()
            except ConcurrentAccessException as e:  # pragma: no cover
                concurrent_accesses.append(e)
            except Exception as e:  # pragma: no cover
                errors.append(e)

        workers = []
        for _ in range(20):
            workers.append(self.get_concurrency_class()(target=something))
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        # We want no concurrent accesses to have occured
        self.assertListEqual(list(concurrent_accesses), [])
        self.assertListEqual(list(errors), [])

    def test_exclusive_acquire_during_shared_locking(self):
        """
        Test exclusive access to lock is indeed exclusive (thread safe) even
        when shared accesses are currently executing (started before exclusive
        lock taken)
        (i.e. exclusive lock is requested during existing shared lock
        sections, but doesn't acquire until all shared locks are released)
        """
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        errors = self.get_shared_list()
        worker_lock = self.get_lock_class()()
        N = 5
        locked = [self.get_event_class()() for _ in range(N)]
        some_value = self.get_shared_list()
        some_value.append(0)

        def shared_lock_target(i):
            try:
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

        # at this point, all shared lock workers should be
        # sleeping, so won't have updated some_value
        self.assertEqual(some_value[0], 0)

        # attempt to exclusively lock
        # should block here till all shared locks released
        with lock.exclusive():
            # shared workers should have all updated some_value
            self.assertEqual(some_value[0], N)

        # cleanup workers
        for worker in workers:
            worker.join()

        self.assertListEqual(list(errors), [])

    def test_shared_acquire_during_exclusive_locking(self):
        """
        Test exclusive access to lock is indeed exclusive (thread safe) even
        when shared accesses are currently executing (started after exclusive
        lock taken)
        (i.e. shared lock is requested during an exclusive lock section, but
        doesn't acquire until the exclusive lock is released)
        """
        lock = self.get_shared_lock()
        self.assertEqual(lock._num_processes.value, 0)
        self.assertEqual(lock._semaphore.get_value(), 0)
        errors = self.get_shared_list()
        N = 5
        locking = [self.get_event_class()() for _ in range(N)]
        some_value = self.get_shared_list()
        some_value.append('original')

        def shared_lock_target(i):
            try:
                locking[i].set()
                with lock:
                    self.assertEqual(some_value[0], 'slept')
            except Exception as e:  # pragma: no cover
                errors.append(e)

        # acquire exclusive lock
        with lock.exclusive():
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

            # wait for all shared locks to block(ish)
            for event in locking:
                event.wait()

            sleep(0.1)

            # update some_value
            # shared lock workers will check for this value once
            # exclusive lock is released
            some_value[0] = 'slept'

        # wait for all shared lock workers to complete
        for worker in workers:
            worker.join()

        self.assertListEqual(list(errors), [])

    def test_the_lot(self):
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

            # check that the shared lock workers didn't update some_value
            self.assertEqual(some_value[0], N)

        # wait for all shared lock workers to complete
        for worker in workers:
            worker.join()

        # shared workers should have all updated some_value again
        self.assertEqual(some_value[0], N*2)
        self.assertListEqual(list(errors), [])

    def get_shared_lock(self):
        raise NotImplementedError()  # pragma: no cover

    def get_shared_list(self):
        raise NotImplementedError()  # pragma: no cover

    def get_concurrency_class(self):
        raise NotImplementedError()  # pragma: no cover

    def get_event_class(self):
        raise NotImplementedError()  # pragma: no cover

    def get_lock_class(self):
        raise NotImplementedError()  # pragma: no cover


class SharedLockMixin(object):
    def get_shared_lock(self):
        return SharedLock()

    def test_shared_reentry_fails(self):
        lock = self.get_shared_lock()
        with lock:
            with six.assertRaisesRegex(self, ValueError, "Lock not re-entrant"):
                with lock:
                    pass  # pragma: no cover

    def test_exclusive_reentry_fails(self):
        lock = self.get_shared_lock()
        with lock.exclusive():
            with six.assertRaisesRegex(self, ValueError, "Lock not re-entrant"):
                with lock.exclusive():
                    pass  # pragma: no cover

            with six.assertRaisesRegex(self, ValueError, "Lock not re-entrant"):
                with lock:
                    pass  # pragma: no cover


class TestSharedLockThreading(SharedLockMixin, ThreadingMixin,
                              SharedLockTestCaseMixin, TestCase):
    pass


class TestSharedLockMultiprocessing(SharedLockMixin, MultiprocessingMixin,
                                    SharedLockTestCaseMixin, TestCase):
    pass
