# -*- coding: utf-8 -*-
"""#16 锁粒度修复回归: 整个读-改-写在锁内, 锁内无耗时 LLM"""
import sys, re
sys.path.insert(0, '.')

def test_whole_read_modify_write_locked():
    src = open('core/gateway/message_assembler.py', encoding='utf-8').read()
    idx = src.find('def _layered_compress')
    end = src.find('def _summarize_text', idx)
    body = src[idx:end]
    lock_line = [i for i, l in enumerate(body.split('\n')) if 'with _get_layer_lock():' in l]
    assert lock_line, '缺锁'
    lock_idx = lock_line[0]
    lines = body.split('\n')
    in_lock_writes = 0
    for l in lines[lock_idx+1:]:
        stripped = l.lstrip()
        indent = len(l) - len(l.strip())
        if stripped.startswith(('store[', 'msgs[:]')):
            if indent >= 12:
                in_lock_writes += 1
    assert in_lock_writes >= 4, f'锁内应有多个 store 修改, 实际 {in_lock_writes}'

def test_lock_inside_no_llm_call():
    """锁内无实际 LLM 调用(去注释后)"""
    src = open('core/gateway/message_assembler.py', encoding='utf-8').read()
    idx = src.find('def _layered_compress')
    end = src.find('def _summarize_text', idx)
    body = src[idx:end]
    no_comments = re.sub(r'#.*', '', body)  # 去注释
    assert 'requests.post' not in no_comments, '锁内不应有 HTTP'
    assert 'llm_client' not in no_comments, '锁内不应有 LLM 客户端'
    assert 'deepseek' not in no_comments.lower(), '锁内不应有 DeepSeek 调用'
    # 摘要函数本身去注释后无 LLM
    sem = src[src.find('def _summarize_messages_semantic'):src.find('def _assemble_messages')]
    sem_no_c = re.sub(r'#.*', '', sem)
    assert 'llm' not in sem_no_c.lower(), '摘要函数不应调 LLM'
    assert 'requests' not in sem_no_c, '摘要函数不应有 HTTP'
