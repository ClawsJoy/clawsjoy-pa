# -*- coding: utf-8 -*-
"""#16 审核修复回归: _assemble_messages 读+构造全在锁内"""
import sys, re
sys.path.insert(0, '.')

def test_assemble_whole_locked():
    """result 构造(读 store)在锁内"""
    src = open('core/gateway/message_assembler.py', encoding='utf-8').read()
    idx = src.find('def _assemble_messages')
    end = src.find('def _safe_compress_messages', idx)
    body = src[idx:end]
    lock_line = [i for i, l in enumerate(body.split('\n')) if 'with _get_layer_lock():' in l]
    assert lock_line, '缺锁'
    lines = body.split('\n')
    lock_idx = lock_line[0]
    # 锁内缩进 8(with 在 4, 函数体在 4, 锁内 8)
    in_lock_ops = [l.strip()[:45] for l in lines[lock_idx+1:] if l.strip() and (len(l) - len(l.lstrip())) >= 8]
    assert any('result = list(store' in o for o in in_lock_ops), f'result 构造应在锁内: {in_lock_ops}'
    assert any('result.extend(store' in o for o in in_lock_ops), 'result.extend 应在锁内'

def test_no_store_read_outside_lock():
    """锁外无 store 读取(result 构造前)"""
    src = open('core/gateway/message_assembler.py', encoding='utf-8').read()
    idx = src.find('def _assemble_messages')
    end = src.find('def _safe_compress_messages', idx)
    body = src[idx:end]
    lines = body.split('\n')
    in_lock = False
    for l in lines:
        stripped = l.strip()
        indent = len(l) - len(l.lstrip())
        if 'with _get_layer_lock():' in l:
            in_lock = True
            continue
        if in_lock and indent < 8 and stripped and not stripped.startswith(('#', 'return', '"""')):
            assert 'store[' not in stripped, f'锁外仍读 store: {stripped[:50]}'
