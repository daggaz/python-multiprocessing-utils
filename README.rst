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
if there is an exclusive lock.

This is a little like database locks, which can be acquired for shared reading,
or exclusive writing.

*****************************
multiprocess theading.local()
*****************************

A process and thread safe version of ``threading.local()``

A standard threading.local() instance created before forking (via
``os.fork()`` or ``multiprocessing.Process()``) will not behave as
expected.
