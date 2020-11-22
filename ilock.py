# -*- coding: utf-8 -*-
#
# Copyright (c) 2020~2999 - Cologler <skyoflw@gmail.com>
# ----------
#
# ----------

from typing import Optional
import errno
import os
import sys
from hashlib import sha256
from tempfile import gettempdir
from time import sleep
from time import monotonic as _time

import portalocker


class ILockException(Exception):
    pass

def _lock_file(f, blocking: bool, expired: Optional[float], *, check_interval: float) -> bool:

    if blocking and expired is None:
        portalocker.lock(f, portalocker.constants.LOCK_EX)
        return True

    else:
        try:
            portalocker.lock(f, portalocker.constants.LOCK_EX | portalocker.constants.LOCK_NB)
            return True
        except portalocker.exceptions.LockException:
            pass

        if expired is not None:
            while (wait_time := expired - _time()) > 0:
                sleep(min(wait_time, check_interval))

                try:
                    portalocker.lock(f, portalocker.constants.LOCK_NB | portalocker.constants.LOCK_EX)
                    return True
                except portalocker.exceptions.LockException:
                    pass

    return False

class ILock(object):
    def __init__(self, name, check_interval: float=0.1, reentrant=False, lock_directory=None):
        self._check_interval = check_interval
        self._reentrant = reentrant

        lock_directory = gettempdir() if lock_directory is None else lock_directory
        unique_token = sha256(name.encode()).hexdigest()
        self._lockpath = os.path.join(lock_directory, 'ilock2-' + unique_token + '.lock')

        self._enter_count = 0

    def acquire(self, blocking=True, timeout=None) -> bool:
        if timeout is not None and timeout < 0:
            timeout = None
        if not blocking and timeout is not None:
            raise ValueError("can't specify a timeout for a non-blocking call")
        expired = None if timeout is None else _time() + timeout

        if self._enter_count > 0:
            if self._reentrant:
                self._enter_count += 1
                return True
            raise ILockException('Trying re-enter a non-reentrant lock')

        assert not hasattr(self, '_lockfile')

        while True:
            self._lockfile = open(self._lockpath, 'w')
            locked = _lock_file(self._lockfile, blocking=blocking, expired=expired, check_interval=self._check_interval)
            if locked:
                # https://stackoverflow.com/questions/17708885/flock-removing-locked-file-without-race-condition
                ino0 = os.stat(self._lockpath).st_ino
                ino1 = os.fstat(self._lockfile.fileno()).st_ino
                if ino0 == ino1:
                    return True
            self._lockfile.close()
            if not locked:
                del self._lockfile
                return False

    def release(self) -> None:
        '''
        When invoked on an unlocked lock, a `RuntimeError` is raised.
        '''
        self._enter_count -= 1

        if self._enter_count > 0:
            return

        self._lockfile.close()
        del self._lockfile

        try:
            os.remove(self._lockpath)
        except WindowsError as e:
            if e.errno not in (errno.EACCES, errno.ENOENT):
                raise

    def locked(self) -> bool:
        '''
        Return true if the lock is acquired.
        '''
        return self._enter_count > 0

    def __enter__(self):
        self.acquire(blocking=True, timeout=None)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
