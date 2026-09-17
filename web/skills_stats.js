// 技能统计模块
async function loadSkillsStats() {
    try {
        const resp = await fetch('/api/skills');
        const data = await resp.json();
        
        const categories = {
            'core': ['do_anything', 'calibrated_executor', 'quality_gate', 'closed_loop_executor'],
            'math': ['add', 'multiply', 'divide', 'math_enhanced'],
            'image': ['remove_bg', 'spider', 'image_slideshow', 'character_designer'],
            'video': ['manju_maker', 'video_uploader', 'add_subtitles', 'ffmpeg_video'],
            'self_heal': ['self_heal', 'self_healer', 'self_debug', 'error_analyzer'],
            'memory': ['memory', 'memory_enhanced', 'knowledge_ingest']
        };
        
        const skills = data.skills || [];
        const stats = {};
        
        for (const [cat, skillList] of Object.entries(categories)) {
            stats[cat] = skillList.filter(s => skills.includes(s)).length;
        }
        stats['total'] = skills.length;
        
        // 更新显示
        const container = document.getElementById('skills-stats');
        if (container) {
            container.innerHTML = `
                <div class="stats-grid">
                    ${Object.entries(stats).map(([cat, count]) => `
                        <div class="stat-item">
                            <span class="stat-cat">${cat}</span>
                            <span class="stat-count">${count}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    } catch(e) {
        console.error('加载技能统计失败:', e);
    }
}

// 页面加载时执行
if (typeof window !== 'undefined') {
    document.addEventListener('DOMContentLoaded', loadSkillsStats);
}
