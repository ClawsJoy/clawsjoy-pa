"""租户隔离引擎"""

import json
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from engine.lib.logger import engine_logger


class TenantEngine:
    """租户隔离引擎"""

    def __init__(self):
        self.tenants = {}
        self._load_tenants()
        engine_logger.get().info("🏢 租户引擎已初始化")

    def _load_tenants(self):
        tenant_dirs = [Path("tenants"), Path("data/tenants")]
        for td in tenant_dirs:
            if td.exists():
                for d in td.iterdir():
                    if d.is_dir():
                        self.tenants[d.name] = {"name": d.name, "path": str(d)}
        engine_logger.get().info(f"   ✅ 加载 {len(self.tenants)} 个租户")

    def process(self, input_data: Any, **kwargs) -> Any:
        if isinstance(input_data, str):
            return self.get_tenant(input_data)
        return self.get_tenant(str(input_data))

    def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        return self.tenants.get(tenant_id)

    def list_tenants(self) -> List[str]:
        return list(self.tenants.keys())

    def get_stats(self) -> Dict:
        return {"total_tenants": len(self.tenants), "tenants": self.list_tenants()}

    def reload(self) -> Dict:
        self.tenants = {}
        self._load_tenants()
        return {"success": True, "message": f"Reloaded {len(self.tenants)} tenants"}

    def health_check(self) -> Dict:
        return {"name": "tenant_engine", "status": "healthy"}


tenant_engine = TenantEngine()
