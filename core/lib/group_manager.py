"""群组管理 — 用户自建群、加成员、群发通知"""
import json
from pathlib import Path
from datetime import datetime
import secrets


class GroupManager:
    def __init__(self):
        self.groups_dir = Path("data/groups")
        self.groups_dir.mkdir(parents=True, exist_ok=True)

    def create(self, group_name: str, creator_id: str) -> dict:
        """创建群组，返回群ID和邀请码"""
        group_id = f"group_{secrets.token_hex(4)}"
        invite_code = secrets.token_hex(3)
        
        data = {
            "group_id": group_id,
            "name": group_name,
            "invite_code": invite_code,
            "created_by": creator_id,
            "created_at": datetime.now().isoformat(),
            "members": {
                creator_id: {"role": "admin", "joined_at": datetime.now().isoformat()}
            }
        }
        
        (self.groups_dir / f"{group_id}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2)
        )
        return {"group_id": group_id, "invite_code": invite_code}

    def join(self, invite_code: str, user_id: str) -> dict:
        """通过邀请码加入群"""
        for f in self.groups_dir.glob("*.json"):
            data = json.loads(f.read_text())
            if data.get("invite_code") == invite_code:
                data["members"][user_id] = {
                    "role": "member",
                    "joined_at": datetime.now().isoformat()
                }
                f.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                return {"success": True, "group_name": data["name"]}
        return {"success": False, "error": "邀请码无效"}

    def get_members(self, group_id: str) -> list:
        """获取群成员列表"""
        f = self.groups_dir / f"{group_id}.json"
        if f.exists():
            return list(json.loads(f.read_text())["members"].keys())
        return []

    def notify(self, group_id: str, message: str) -> list:
        """群发通知，返回所有成员ID"""
        return self.get_members(group_id)


group_manager = GroupManager()
