import multiprocessing

import multiprocessing_utils


class ExclusiveSharedLockContext(object):
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        self.lock.acquire(exclusive=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()


class BaseSharedLock(object):
    def __init__(self):
        self._semaphore = multiprocessing.Semaphore(0)
        self._num_processes = multiprocessing.Value('I', 0)
        self._state = multiprocessing_utils.local()

    def acquire(self, exclusive=False):
        if not hasattr(self._state, 'exclusive'):
            self._state.exclusive = None

        if self._state.exclusive is not None and exclusive and not self._state.exclusive:
            raise ValueError(
                "Cannot upgrade a shared lock to an exclusive lock",
            )

        if self._pre_acquire():
            if self._state.exclusive is None:
                self._state.exclusive = exclusive

            with self._num_processes.get_lock():
                self._num_processes.value += 1
                self._semaphore.release()
            if self._state.exclusive:
                self._num_processes.get_lock().acquire()
                for _ in range(self._num_processes.value):
                    self._semaphore.acquire()
            else:
                self._semaphore.acquire()

    def _pre_acquire(self):
        raise NotImplementedError()  # pragma: no cover

    def _pre_release(self):
        raise NotImplementedError()  # pragma: no cover

    def release(self):
        if not hasattr(self._state, 'exclusive'):
            self._state.exclusive = None

        if self._state.exclusive is None:
            raise ValueError("lock released too many times")

        if self._pre_release():
            if self._state.exclusive:
                for _ in range(self._num_processes.value):
                    self._semaphore.release()
                self._num_processes.get_lock().release()
            else:
                self._semaphore.release()
            self._state.exclusive = None

            with self._num_processes.get_lock():
                self._semaphore.acquire()
                self._num_processes.value -= 1

    def exclusive(self):
        return ExclusiveSharedLockContext(self)

    def shared(self):
        return self  # pragma: no cover

    def __enter__(self):
        self.acquire(exclusive=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class SharedLock(BaseSharedLock):
    def _pre_acquire(self):
        if self._state.exclusive is not None:
            raise ValueError("Lock not re-entrant")
        return True

    def _pre_release(self):
        return True


class SharedRLock(BaseSharedLock):
    def _pre_acquire(self):
        if not hasattr(self._state, 'reference_count'):
            self._state.reference_count = 0
        self._state.reference_count += 1
        return self._state.reference_count == 1

    def _pre_release(self):
        self._state.reference_count -= 1
        return self._state.reference_count <= 0
