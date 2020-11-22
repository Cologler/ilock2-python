# -*- coding: utf-8 -*-
#
# Copyright (c) 2020~2999 - Cologler <skyoflw@gmail.com>
# ----------
#
# ----------

import os
from tempfile import TemporaryDirectory
import multiprocessing as mp
import ilock
import time
import pathlib
from ctypes import c_wchar_p

def f1(path: str):
    lock = ilock.ILock('196de887-cec7-4626-ba05-f514a9f35088')
    with lock:
        time.sleep(2)
        pathlib.Path(path).write_text('76c53da8-9af2-488c-82a5-8fce3ce944db')

def f2(path: str, rv):
    lock = ilock.ILock('196de887-cec7-4626-ba05-f514a9f35088')
    with lock:
        rv.value = pathlib.Path(path).read_text()

def test_processes_safely():
    manager = mp.Manager()

    with TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, '79986c95-2197-49bb-9d74-0db7705bce40.txt')
        p1 = mp.Process(target=f1, args=(path,))
        p1.start()
        time.sleep(1)
        rv2 = manager.Value(c_wchar_p, '')
        p2 = mp.Process(target=f2, args=(path, rv2))
        p2.start()
        p1.join()
        p2.join()
        assert rv2.value == '76c53da8-9af2-488c-82a5-8fce3ce944db'
