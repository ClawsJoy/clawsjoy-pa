# -*- coding: utf-8 -*-
"""#11 回归: 会话消息并发锁(clear 竞态防护)"""
import sys
sys.path.insert(0, '.')
import pytest

def test_consecutive_lock_used():
    """sandbox_write/write_file 的 clear 用 _get_consecutive_lock 保护"""
    sw = open('core/gateway/sandbox_write.py', encoding='utf-8').read()
    wf = open('core/tools/write_file.py', encoding='utf-8').read()
    assert sw.count('_get_consecutive_lock') >= 2, 'sandbox_write 缺锁保护(2处)'
    assert wf.count('_get_consecutive_lock') >= 1, 'write_file 缺锁保护'
    assert 'with _get_consecutive_lock():' in sw and 'with _get_consecutive_lock():' in wf

def test_consecutive_lock_exists():
    """shared_state 有 _get_consecutive_lock"""
    ss = open('core/gateway/shared_state.py', encoding='utf-8').read()
    assert 'def _get_consecutive_lock' in ss, '缺锁函数'
    assert '_consecutive_lock = _th_cf.Lock()' in ss, '缺锁实例'
