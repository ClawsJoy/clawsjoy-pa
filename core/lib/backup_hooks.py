from core.lib.config_helper import get_data_root, get_llm_endpoint, get_llm_model, get_embedding_model, get_gateway_port, get_timeout
from core.lib.unified_config import unified_config

from core.lib.unified_config import unified_config

"""备份钩子 - 用户数据安全备份"""

import json
import shutil
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

class BackupHooks:
    """备份钩子 - 让用户数据安全可恢复"""
    
    def __init__(self):
        self.backup_dir = Path(f"{get_data_root()}/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = 10
        self.backup_interval_hours = 24
    
    def auto_backup(self, context: Dict) -> Dict:
        """自动备份用户数据"""
        user_id = context.get('user_id', 'unknown')
        data = context.get('data', {})

        # 检查是否需要备份
        if self._need_backup(user_id):
            backup_file = self._create_backup(user_id, data)
            context['backup_created'] = str(backup_file)
            print(f"💾 已备份用户数据: {backup_file}")

        return context
    
    def _need_backup(self, user_id: str) -> bool:
        """检查是否需要备份"""
        user_backups = list(self.backup_dir.glob(f"{user_id}_*.backup.gz"))
        if not user_backups:
            return True

        # 检查最新备份时间
        latest = max(user_backups, key=lambda p: p.stat().st_mtime)
        age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)

        return age > timedelta(hours=self.backup_interval_hours)
    
    def _create_backup(self, user_id: str, data: Dict) -> Path:
        """创建备份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"{user_id}_{timestamp}.backup.gz"

        # 压缩备份
        with gzip.open(backup_file, 'wt', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        # 清理旧备份
        self._cleanup_old_backups(user_id)

        return backup_file
    
    def _cleanup_old_backups(self, user_id: str):
        """清理旧备份"""
        backups = sorted(self.backup_dir.glob(f"{user_id}_*.backup.gz"), 
                        key=lambda p: p.stat().st_mtime, reverse=True)

        for old_backup in backups[self.max_backups:]:
            old_backup.unlink()
            print(f"🗑️ 已删除旧备份: {old_backup.name}")
    
    def restore_backup(self, user_id: str, backup_file: str = None) -> Dict:
        """恢复备份"""
        if backup_file:
            backup_path = self.backup_dir / backup_file
        else:
            # 获取最新备份
            backups = sorted(self.backup_dir.glob(f"{user_id}_*.backup.gz"), 
                            key=lambda p: p.stat().st_mtime, reverse=True)
            if not backups:
                return {'success': False, 'error': '没有找到备份'}
            backup_path = backups[0]

        with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        return {'success': True, 'data': data, 'backup_file': str(backup_path)}


# 全局实例
backup_hooks = BackupHooks()

# 导出钩子函数
auto_backup = backup_hooks.auto_backup
restore_backup = backup_hooks.restore_backup
