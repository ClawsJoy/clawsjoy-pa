"""空间语义参数映射 - 2D/3D位置 + 渲染参数"""

import re
from typing import Dict, Tuple


class SpatialParamMapper:
    """空间语义参数映射器"""

    # 位置映射
    POSITION_MAP = {
        "往上": {"y": -0.1, "direction": "up"},
        "往上一点": {"y": -0.05, "direction": "up"},
        "往上很多": {"y": -0.2, "direction": "up"},
        "往下": {"y": 0.1, "direction": "down"},
        "往下一点": {"y": 0.05, "direction": "down"},
        "往下很多": {"y": 0.2, "direction": "down"},
        "往左": {"x": -0.1, "direction": "left"},
        "往左一点": {"x": -0.05, "direction": "left"},
        "往左很多": {"x": -0.2, "direction": "left"},
        "往右": {"x": 0.1, "direction": "right"},
        "往右一点": {"x": 0.05, "direction": "right"},
        "往右很多": {"x": 0.2, "direction": "right"},
        "向前": {"z": -0.1, "direction": "forward"},
        "向前一点": {"z": -0.05, "direction": "forward"},
        "向前很多": {"z": -0.2, "direction": "forward"},
        "向后": {"z": 0.1, "direction": "back"},
        "向后一点": {"z": 0.05, "direction": "back"},
        "拉近": {"scale": 0.1, "zoom": "in"},
        "拉远": {"scale": -0.1, "zoom": "out"},
        "放大": {"scale": 0.15, "zoom": "in"},
        "缩小": {"scale": -0.15, "zoom": "out"},
    }

    # 光影映射
    LIGHTING_MAP = {
        "亮一点": {"brightness": 0.1, "exposure": 0.1},
        "暗一点": {"brightness": -0.1, "exposure": -0.1},
        "更亮": {"brightness": 0.15, "exposure": 0.15},
        "更暗": {"brightness": -0.15, "exposure": -0.15},
        "暖一点": {"temperature": 0.1, "color_temp": "warm"},
        "冷一点": {"temperature": -0.1, "color_temp": "cool"},
        "加对比": {"contrast": 0.1},
        "减对比": {"contrast": -0.1},
        "更鲜艳": {"saturation": 0.1},
        "淡一点": {"saturation": -0.1},
        "加光影": {"shadow_intensity": 0.1, "highlight": 0.1},
        "柔和": {"shadow_intensity": -0.05, "softness": 0.1},
        "戏剧光": {"shadow_intensity": 0.2, "contrast": 0.15},
    }

    # 场景映射
    SCENE_MAP = {
        "室内": {"scene": "indoor", "environment": "room"},
        "室外": {"scene": "outdoor", "environment": "nature"},
        "白天": {"time": "day", "sunlight": 0.8},
        "夜晚": {"time": "night", "sunlight": 0.1, "moonlight": 0.5},
        "黄昏": {"time": "dusk", "sunlight": 0.3, "warmth": 0.6},
        "黎明": {"time": "dawn", "sunlight": 0.2, "coolness": 0.4},
        "城市": {"scene": "city", "urban": 1.0},
        "自然": {"scene": "nature", "organic": 1.0},
        "科幻": {"scene": "sci-fi", "neon": 0.8, "futuristic": 1.0},
        "奇幻": {"scene": "fantasy", "magical": 1.0},
    }

    # 人物状态映射
    CHARACTER_MAP = {
        "开心": {"emotion": "happy", "smile": 1.0},
        "悲伤": {"emotion": "sad", "frown": 0.8},
        "愤怒": {"emotion": "angry", "anger": 1.0},
        "惊讶": {"emotion": "surprised", "surprise": 1.0},
        "疲惫": {"emotion": "tired", "energy": 0.3},
        "专注": {"emotion": "focused", "attention": 1.0},
        "放松": {"emotion": "relaxed", "tension": 0.1},
        "紧张": {"emotion": "nervous", "tension": 0.8},
    }

    def parse(self, user_input: str) -> Dict:
        """解析自然语言，返回完整参数"""
        params = {
            "position": {"x": 0, "y": 0, "z": 0},
            "scale": 1.0,
            "rotation": {"x": 0, "y": 0, "z": 0},
            "lighting": {
                "brightness": 0,
                "contrast": 0,
                "saturation": 0,
                "temperature": 0,
                "shadow_intensity": 0,
            },
            "scene": {"type": "default", "time": "day"},
            "character": {"emotion": "neutral"},
            "camera": {"angle": "front", "distance": 1.0},
        }

        # 解析位置
        for kw, change in self.POSITION_MAP.items():
            if kw in user_input:
                if "x" in change:
                    params["position"]["x"] += change["x"]
                if "y" in change:
                    params["position"]["y"] += change["y"]
                if "z" in change:
                    params["position"]["z"] += change["z"]
                if "scale" in change:
                    params["scale"] += change["scale"]

        # 解析光影
        for kw, changes in self.LIGHTING_MAP.items():
            if kw in user_input:
                for k, v in changes.items():
                    if k in params["lighting"]:
                        params["lighting"][k] += v

        # 解析场景
        for kw, changes in self.SCENE_MAP.items():
            if kw in user_input:
                for k, v in changes.items():
                    if k in params["scene"]:
                        params["scene"][k] = v

        # 解析人物状态
        for kw, changes in self.CHARACTER_MAP.items():
            if kw in user_input:
                for k, v in changes.items():
                    if k in params["character"]:
                        params["character"][k] = v

        # 解析相机角度
        if "正面" in user_input:
            params["camera"]["angle"] = "front"
        elif "侧面" in user_input:
            params["camera"]["angle"] = "side"
        elif "背面" in user_input:
            params["camera"]["angle"] = "back"
        elif "俯视" in user_input:
            params["camera"]["angle"] = "top"
        elif "仰视" in user_input:
            params["camera"]["angle"] = "bottom"

        return params

    def to_prompt(self, params: Dict) -> str:
        """将参数转换为 SD 提示词"""
        prompt_parts = []

        # 位置
        pos = params["position"]
        if pos["x"] != 0 or pos["y"] != 0 or pos["z"] != 0:
            prompt_parts.append(
                f"position offset x:{pos['x']:.2f} y:{pos['y']:.2f} z:{pos['z']:.2f}"
            )

        # 缩放
        if params["scale"] != 1.0:
            prompt_parts.append(f"scale {params['scale']:.2f}")

        # 光影
        lit = params["lighting"]
        if lit["brightness"] != 0:
            prompt_parts.append(f"brightness {1 + lit['brightness']:.2f}")
        if lit["contrast"] != 0:
            prompt_parts.append(f"contrast {1 + lit['contrast']:.2f}")
        if lit["temperature"] > 0:
            prompt_parts.append("warm lighting")
        elif lit["temperature"] < 0:
            prompt_parts.append("cool lighting")

        # 场景
        scene = params["scene"]
        if scene["type"] != "default":
            prompt_parts.append(scene["type"])
        if scene.get("time") != "day":
            prompt_parts.append(scene["time"])

        # 人物
        char = params["character"]
        if char["emotion"] != "neutral":
            prompt_parts.append(char["emotion"])

        # 相机
        cam = params["camera"]
        if cam["angle"] != "front":
            prompt_parts.append(f"{cam['angle']} view")

        return ", ".join(prompt_parts) if prompt_parts else "default"


spatial_mapper = SpatialParamMapper()


if __name__ == "__main__":
    tests = [
        "往上一点，往右一点，亮一点，暖一点",
        "拉近，放大，戏剧光，科幻场景，人物开心",
        "往左很多，更暗，冷一点，俯视",
    ]

    for test in tests:
        params = spatial_mapper.parse(test)
        prompt = spatial_mapper.to_prompt(params)
        print(f"{test}")
        print(
            f"  → 位置: x={params['position']['x']:.2f}, y={params['position']['y']:.2f}"
        )
        print(f"  → 光影: {params['lighting']}")
        print(f"  → 场景: {params['scene']}")
        print(f"  → 提示词: {prompt}\n")

# 全景/3D 可视化映射
PANORAMA_MAP = {
    "360": {"panorama": True, "fov": 360},
    "全景": {"panorama": True, "fov": 360},
    "球面": {"projection": "spherical", "fov": 360},
    "立方体": {"projection": "cube", "fov": 90},
    "VR": {"vr_mode": True, "stereo": True},
    "3D": {"three_d": True, "depth": True},
    "环绕": {"surround": True, "fov": 270},
    "鱼眼": {"lens": "fisheye", "fov": 180},
    "广角": {"lens": "wide", "fov": 120},
}

# 可视化类型映射
VISUALIZATION_MAP = {
    "热力图": {"viz_type": "heatmap", "colormap": "hot"},
    "温度图": {"viz_type": "heatmap", "colormap": "temperature"},
    "深度图": {"viz_type": "depth", "colormap": "viridis"},
    "法线图": {"viz_type": "normal", "colormap": "rgb"},
    "线框图": {"viz_type": "wireframe", "style": "lines"},
    "点云": {"viz_type": "pointcloud", "point_size": 1},
    "网格": {"viz_type": "mesh", "wireframe": False},
    "体积": {"viz_type": "volume", "opacity": 0.5},
    "切片": {"viz_type": "slice", "axis": "z"},
}

# 渲染参数映射
RENDER_MAP = {
    "真实感": {"renderer": "raytracing", "quality": "high"},
    "卡通": {"renderer": "toon", "style": "cartoon"},
    "素描": {"renderer": "sketch", "style": "pencil"},
    "水彩": {"renderer": "watercolor", "style": "artistic"},
    "油画": {"renderer": "oil", "style": "artistic"},
    "像素": {"renderer": "pixel", "resolution": "low"},
}


class ExtendedSpatialMapper(SpatialParamMapper):
    """扩展空间语义映射器 - 支持全景和可视化"""

    def parse(self, user_input: str) -> Dict:
        params = super().parse(user_input)

        # 初始化扩展参数
        params["panorama"] = {"enabled": False, "fov": 90, "projection": "perspective"}
        params["visualization"] = {"type": "standard"}
        params["render"] = {"quality": "standard"}

        # 解析全景参数
        for kw, config in PANORAMA_MAP.items():
            if kw in user_input:
                params["panorama"]["enabled"] = True
                for k, v in config.items():
                    params["panorama"][k] = v

        # 解析可视化类型
        for kw, config in VISUALIZATION_MAP.items():
            if kw in user_input:
                for k, v in config.items():
                    params["visualization"][k] = v

        # 解析渲染风格
        for kw, config in RENDER_MAP.items():
            if kw in user_input:
                for k, v in config.items():
                    params["render"][k] = v

        return params

    def to_panorama_prompt(self, params: Dict) -> str:
        """生成全景提示词"""
        if not params["panorama"]["enabled"]:
            return ""

        pano = params["panorama"]
        prompts = ["panorama", "360 degree view"]

        if pano.get("projection") == "spherical":
            prompts.append("spherical panorama")
        elif pano.get("projection") == "cube":
            prompts.append("cubemap")

        if pano.get("vr_mode"):
            prompts.append("VR ready, stereoscopic")

        if pano.get("lens") == "fisheye":
            prompts.append("fisheye lens")

        return ", ".join(prompts)

    def to_viz_prompt(self, params: Dict) -> str:
        """生成可视化提示词"""
        viz = params["visualization"]

        if viz["type"] == "standard":
            return ""

        prompts = []
        if viz.get("viz_type") == "heatmap":
            prompts.append("heatmap visualization")
        elif viz.get("viz_type") == "depth":
            prompts.append("depth map, depth visualization")
        elif viz.get("viz_type") == "normal":
            prompts.append("normal map")
        elif viz.get("viz_type") == "wireframe":
            prompts.append("wireframe view")
        elif viz.get("viz_type") == "pointcloud":
            prompts.append("point cloud rendering")

        return ", ".join(prompts)


extended_mapper = ExtendedSpatialMapper()


if __name__ == "__main__":
    tests = [
        "往上一点，往右一点，亮一点，360度全景",
        "VR模式，热力图，真实感渲染",
        "全景，球面投影，卡通风格，3D可视化",
        "鱼眼镜头，深度图，点云",
    ]

    for test in tests:
        params = extended_mapper.parse(test)
        pano = extended_mapper.to_panorama_prompt(params)
        viz = extended_mapper.to_viz_prompt(params)
        print(f"{test}")
        print(f"  全景: {pano if pano else '否'}")
        print(f"  可视化: {viz if viz else '标准'}")
        print(
            f"  位置: x={params['position']['x']:.2f}, y={params['position']['y']:.2f}"
        )
        print()
