"""pytest 配置和共享 fixtures"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

import pytest


@pytest.fixture
def test_user_id():
    """测试用户ID"""
    return "test_user"


@pytest.fixture
def sample_code():
    """示例代码"""
    return """
def hello():
    print("hello world")

def add(a, b):
    return a + b
"""


@pytest.fixture
def sample_code_with_issues():
    """有问题的示例代码"""
    return """
def unsafe():
    eval(input())
    for i in range(10):
        for j in range(10):
            print(i*j)
    try:
        result = 1/0
    except Exception:
        pass
"""
