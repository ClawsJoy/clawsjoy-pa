"""ClawsJoy 平台客户端 — OS 端连接云平台的桥梁"""

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

from core.lib.version import __version__


class PlatformClient:
    """OS 端平台连接器：密钥管理 + 注册 + 订阅 + 下载"""

    def __init__(self, platform_url: str = None, data_dir: str = None):
        self.platform_url = platform_url or os.getenv("CLAWSJOY_PLATFORM_URL", "")
        self.data_dir = Path(data_dir or os.getenv("CLAWSJOY_DATA_DIR", "data"))
        self.key_file = self.data_dir / ".clawsjoy_key.json"
        self.jwt = None
        # 主机名：POSIX 走 os.uname；无 uname（Windows）⇒ env（⛔ 崩于 import）
        _uname = getattr(os, "uname", None)
        self.hostname = (_uname().nodename if _uname else
                         (os.getenv("COMPUTERNAME") or os.getenv("HOSTNAME") or "unknown"))

    # ===== 密钥管理 =====

    def _load_or_create_key(self) -> Dict:
        """加载或创建 Ed25519 密钥对"""
        if self.key_file.exists():
            return json.loads(self.key_file.read_text(encoding="utf-8"))
        from cryptography.hazmat.primitives.asymmetric import ed25519
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        import base64
        key = {
            "private_key": base64.b64encode(
                private_key.private_bytes_raw()
            ).decode(),
            "public_key": base64.b64encode(
                public_key.public_bytes_raw()
            ).decode(),
        }
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file.write_text(json.dumps(key), encoding="utf-8")
        return key

    # ===== 平台通信 =====

    def login(self) -> bool:
        """用公钥登录平台，获取 JWT。未注册则自动注册后重试。"""
        if not self.platform_url:
            print("[PlatformClient] CLAWSJOY_PLATFORM_URL 未设置，无法连接平台")
            return False
        import requests
        key = self._load_or_create_key()
        try:
            # 先注册 OS 节点（幂等操作）
            requests.post(f"{self.platform_url}/api/os/register", json={
                "hostname": self.hostname,
                "version": __version__,
                "capabilities": ["agent_workspace"],
            }, timeout=5)
            # 尝试登录
            resp = requests.post(f"{self.platform_url}/api/users/login", json={
                "public_key": key["public_key"],
            }, timeout=10)
            # 公钥未注册 → 先注册用户再重试
            if resp.status_code == 401:
                requests.post(f"{self.platform_url}/api/users/register", json={
                    "public_key": key["public_key"],
                    "username": self.hostname,
                }, timeout=5)
                resp = requests.post(f"{self.platform_url}/api/users/login", json={
                    "public_key": key["public_key"],
                }, timeout=10)
            if resp.status_code == 200:
                self.jwt = resp.json().get("token")
                return True
        except Exception as e:
            print(f"[PlatformClient] 登录失败: {e}")
        return False

    def fetch_subscriptions(self) -> List[Dict]:
        """拉取已订阅的 Agent 列表"""
        if not self.jwt and not self.login():
            return []
        try:
            import requests
            resp = requests.get(f"{self.platform_url}/api/agents/subscribed", headers={
                "Authorization": f"Bearer {self.jwt}",
            }, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("agents", [])
        except Exception:
            pass
        return []

    def download_agent(self, agent_id: str, target_dir: Path = None) -> bool:
        """下载 Agent 代码到本地沙箱"""
        if not self.jwt and not self.login():
            return False
        target = target_dir or Path(f"data/agents/{agent_id}")
        target.mkdir(parents=True, exist_ok=True)
        try:
            import requests
            resp = requests.get(f"{self.platform_url}/api/agents/{agent_id}/download", headers={
                "Authorization": f"Bearer {self.jwt}",
            }, timeout=30)
            if resp.status_code == 200:
                import zipfile, io
                with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                    zf.extractall(target)
                return True
        except Exception:
            pass
        return False


# 全局实例
platform = PlatformClient()
