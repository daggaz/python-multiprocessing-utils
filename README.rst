============================
python-multiprocessing-utils
============================

Multiprocessing utilities

************
Shared locks
************

"Shared" version of the standard ``Lock()`` and ``RLock()`` classes found in
the ``multiprocessing``/``threading`` modules.

Shared locks can be acquired in two modes, shared and exclusive.

Any number of processes/threads can acquire the lock in shared mode.

Only one process/thread can acquire the lock in exclusive mode.

A process/thread attempting to exclusively acquire the lock will block
until the lock has been released by all other threads/processes.

A process/thread attempting to shared acquire the lock will only block
while there is an exclusive lock.

This is a little like database locks, which can be acquired for shared reading,
or exclusive writing.

::

    lock = multiprocessing_utils.SharedLock()

    def exclusive_worker():
        with lock.exclusive():
            # this code will only run when no other
            # process/thread in a lock context

    def shared_worker():
        with lock:
            # this code will run so long as no
            # thread/process holds an exclusive lock

***************************************
multiprocess-safe ``threading.local()``
***************************************

A process (and thread) safe version of ``threading.local()``

::

    l = multiprocessing_utils.local()
    l.x = 1

    def f():
        try:
            print(l.x)
        except Attribute:
            print("x not set")
    f()                                        # prints "1"
    threading.Thread(target=f).start()         # prints "x not set"
    multiprocessing.Process(target=f).start()  # prints "x not set"

Difference to standard ``threading.local()``
--------------------------------------------

A standard ``threading.local()`` instance created before forking (via
``os.fork()`` or ``multiprocessing.Process()``) will be "local" as expected
and the new process will have access to any data set before the fork.

Using a standard ``threading.local()`` in the example above would yield:

::

    f()                                        # prints "1"
    threading.Thread(target=f).start()         # prints "x not set"
    multiprocessing.Process(target=f).start()  # prints "1" :(
