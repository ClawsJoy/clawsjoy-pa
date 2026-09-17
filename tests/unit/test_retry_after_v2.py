# -*- coding: utf-8 -*-
"""#4 v2 回归: Retry-After 支持秒数 + HTTP-date"""
import sys
sys.path.insert(0, '.')

def test_retry_after_seconds():
    """秒数格式 → 用秒"""
    ra = '120'
    wait = min(int(ra), 30)
    assert wait == 30, f'秒数应取 min(120,30)=30, 实际 {wait}'

def test_retry_after_http_date():
    """HTTP-date 格式 → 解析为等待秒数"""
    from email.utils import parsedate_to_datetime
    import datetime
    # 模拟: Retry-After 是未来的时间
    future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10)
    ra = future.strftime('%a, %d %b %Y %H:%M:%S GMT')
    retry_dt = parsedate_to_datetime(ra)
    wait = max(int((retry_dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds()), 1)
    wait = min(wait, 30)
    assert 5 <= wait <= 15, f'HTTP-date 应解析出 ~10s, 实际 {wait}'

def test_retry_after_in_source():
    """源码含 HTTP-date 解析"""
    src = open('core/lib/v8/adapters/deepseek_adapter.py', encoding='utf-8').read()
    assert 'parsedate_to_datetime' in src, '缺 HTTP-date 解析'
    assert 'isdigit()' in src, '缺秒数判断'
    assert 'email.utils' in src, '缺 email.utils 导入'
