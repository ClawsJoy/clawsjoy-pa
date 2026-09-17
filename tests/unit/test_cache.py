"""缓存系统单元测试"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest

from core.lib.chat_engine import PersistentMemory


class TestCache(unittest.TestCase):
    def setUp(self):
        self.memory = PersistentMemory("data/test_memories")

    def tearDown(self):
        import shutil

        try:
            shutil.rmtree("data/test_memories")
        except Exception:
            pass

    def test_save_and_load(self):
        """测试保存和加载"""
        self.memory.save("test_user", {"name": "测试用户"})
        data = self.memory.load("test_user")
        self.assertEqual(data.get("name"), "测试用户")

    def test_save_conversation(self):
        """测试保存对话"""
        self.memory.save_conversation("test_user", "你好", "你好！")
        data = self.memory.load("test_user")
        self.assertEqual(len(data.get("conversations", [])), 1)
        self.assertEqual(data["conversations"][0]["user"], "你好")


if __name__ == "__main__":
    unittest.main()
