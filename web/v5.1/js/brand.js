/**
 * ClawsJoy v5.1 品牌视觉系统
 * 3D科幻风格 + 角色主题体系
 */

const Brand = {
    version: "5.1.0",
    
    // 品牌标识
    logo: {
        primary: "🐾 ClawsJoy",
        short: "🦞",
        tech: "⚡ClawsJoy",
        full: "ClawsJoy 智能体AI操作系统",
        slogan: "未来已来，智能随行"
    },
    
    // 色彩体系 (3D科幻风格)
    colors: {
        brand: {
            primary: "#00f3ff",    // 赛博青
            secondary: "#7b2ff7",  // 幻影紫
            accent: "#ff00ff",     // 霓虹粉
            dark: "#0a0a1a",       // 深邃黑
            glass: "rgba(26,26,46,0.7)"
        },
        roles: {
            guest: { primary: "#00f3ff", glow: "#00f3ff80" },
            user: { primary: "#44ff44", glow: "#44ff4480" },
            developer: { primary: "#ffaa44", glow: "#ffaa4480" },
            admin: { primary: "#ff4444", glow: "#ff444480" }
        }
    },
    
    // 3D配置
    three3d: {
        particleCount: 3000,
        ringCount: 3,
        glowIntensity: 0.8,
        cameraDistance: 35
    }
};

// 主题切换函数
function applyRoleTheme(role) {
    const colors = Brand.colors.roles[role] || Brand.colors.roles.guest;
    document.documentElement.style.setProperty('--theme-primary', colors.primary);
    document.documentElement.style.setProperty('--theme-glow', colors.glow);
}

// 导出
window.Brand = Brand;
window.applyRoleTheme = applyRoleTheme;
