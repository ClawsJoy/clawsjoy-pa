/**
 * ClawsJoy v5.1 3D背景系统
 * Three.js 粒子星系 + 旋转光环 + 动态光效
 */

(function() {
    const container = document.getElementById('three-canvas');
    if (!container) return;
    
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050510);
    
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 35;
    
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x050510, 1);
    container.appendChild(renderer.domElement);
    
    // 粒子系统
    const particlesCount = 3000;
    const posArray = new Float32Array(particlesCount * 3);
    const colorArray = new Float32Array(particlesCount * 3);
    
    for (let i = 0; i < particlesCount; i++) {
        posArray[i*3] = (Math.random() - 0.5) * 120;
        posArray[i*3+1] = (Math.random() - 0.5) * 80;
        posArray[i*3+2] = (Math.random() - 0.5) * 60 - 20;
        
        const color = Math.random() > 0.7 ? 0x7b2ff7 : 0x00f3ff;
        colorArray[i*3] = ((color >> 16) & 255) / 255;
        colorArray[i*3+1] = ((color >> 8) & 255) / 255;
        colorArray[i*3+2] = (color & 255) / 255;
    }
    
    const particlesGeometry = new THREE.BufferGeometry();
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));
    
    const particlesMaterial = new THREE.PointsMaterial({
        size: 0.12,
        vertexColors: true,
        transparent: true,
        opacity: 0.7,
        blending: THREE.AdditiveBlending
    });
    
    const particlesMesh = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particlesMesh);
    
    // 光环系统
    const rings = [];
    const ringConfigs = [
        { radius: 8, color: 0x00f3ff, opacity: 0.4, speed: 0.002 },
        { radius: 11, color: 0x7b2ff7, opacity: 0.3, speed: -0.0015 },
        { radius: 14, color: 0xff00ff, opacity: 0.2, speed: 0.001 }
    ];
    
    ringConfigs.forEach(config => {
        const geometry = new THREE.TorusGeometry(config.radius, 0.06, 64, 300);
        const material = new THREE.MeshBasicMaterial({ color: config.color, transparent: true, opacity: config.opacity });
        const ring = new THREE.Mesh(geometry, material);
        scene.add(ring);
        rings.push({ mesh: ring, speed: config.speed, radius: config.radius });
    });
    
    // 中心光晕
    const glowGeometry = new THREE.SphereGeometry(1.2, 32, 32);
    const glowMaterial = new THREE.MeshBasicMaterial({ color: 0x00f3ff, transparent: true, opacity: 0.15 });
    const coreGlow = new THREE.Mesh(glowGeometry, glowMaterial);
    scene.add(coreGlow);
    
    // 漂浮粒子环
    const floatParticlesCount = 500;
    const floatPositions = new Float32Array(floatParticlesCount * 3);
    for (let i = 0; i < floatParticlesCount; i++) {
        const angle = (i / floatParticlesCount) * Math.PI * 2;
        const radius = 15;
        floatPositions[i*3] = Math.cos(angle) * radius;
        floatPositions[i*3+1] = Math.sin(angle) * radius * 0.5;
        floatPositions[i*3+2] = Math.sin(angle) * 5;
    }
    const floatGeometry = new THREE.BufferGeometry();
    floatGeometry.setAttribute('position', new THREE.BufferAttribute(floatPositions, 3));
    const floatMaterial = new THREE.PointsMaterial({ size: 0.08, color: 0x00f3ff, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending });
    const floatRing = new THREE.Points(floatGeometry, floatMaterial);
    scene.add(floatRing);
    
    let time = 0;
    
    function animate() {
        requestAnimationFrame(animate);
        time += 0.008;
        
        // 粒子系统旋转
        particlesMesh.rotation.y = time * 0.03;
        particlesMesh.rotation.x = Math.sin(time * 0.1) * 0.1;
        
        // 光环旋转
        rings.forEach(ring => {
            ring.mesh.rotation.x = Math.sin(time * 0.2) * 0.2;
            ring.mesh.rotation.y = time * ring.speed * 30;
            ring.mesh.rotation.z = Math.cos(time * 0.15) * 0.1;
        });
        
        // 漂浮粒子环
        floatRing.rotation.y = time * 0.1;
        floatRing.rotation.x = Math.sin(time * 0.2) * 0.1;
        
        // 中心光晕脉动
        const scale = 1 + Math.sin(time * 5) * 0.1;
        coreGlow.scale.set(scale, scale, scale);
        
        renderer.render(scene, camera);
    }
    
    animate();
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
})();
