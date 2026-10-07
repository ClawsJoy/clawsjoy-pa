"""
重新复制原始 agent_gateway_enhanced.py
"""
import os
import shutil

src = "/home/<user>/clawsjoy_v5/agent_gateway_enhanced.py"
dst = "clawsjoy_dev/agent_gateway_enhanced.py"

size = os.path.getsize(src)
print(f"Source size: {size} bytes")

shutil.copy2(src, dst)
print(f"Copied to {dst}")

# 验证
size2 = os.path.getsize(dst)
print(f"Dest size: {size2} bytes")
print(f"Match: {size == size2}")
