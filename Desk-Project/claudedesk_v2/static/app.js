const API_URL = 'http://localhost:3000/api';

// Navigation
function showSection(sectionId) {
    document.querySelectorAll('.content-section').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    document.getElementById(sectionId).classList.add('active');

    // Find nav item by onclick content (hacky but simple)
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        if (item.getAttribute('onclick').includes(sectionId)) {
            item.classList.add('active');
        }
    });

    if (sectionId === 'galaxy') fetchGalaxy();
    if (sectionId === 'audit') fetchLogs();
}

// Terminal
const commandInput = document.getElementById('commandInput');
const terminalOutput = document.getElementById('terminalOutput');

commandInput.addEventListener('keypress', async (e) => {
    if (e.key === 'Enter') {
        const cmd = commandInput.value;
        commandInput.value = '';

        appendLog(`> ${cmd}`, 'command');

        try {
            const res = await fetch(`${API_URL}/command`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            });
            const data = await res.json();

            // Format output (handle newlines)
            const lines = data.output.split('\n');
            lines.forEach(line => appendLog(line, 'response'));

            // Auto-refresh views if needed
            if (cmd.includes('explore') || cmd.includes('scan')) fetchGalaxy();
            if (cmd.includes('audit')) fetchLogs();

        } catch (err) {
            appendLog(`Error: ${err.message}`, 'error');
        }
    }
});

function appendLog(text, type) {
    const div = document.createElement('div');
    div.className = `line ${type}`;
    div.textContent = text;
    terminalOutput.appendChild(div);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

// Three.js Globals
let scene, camera, renderer, controls;
let galaxyData = { files: [], links: [] };

// Initialize 3D Scene
function initGalaxy3D() {
    const container = document.getElementById('galaxy-canvas');
    if (!container) return;

    // SCENE
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b001a); // Deep Cosmic Purple
    scene.fog = new THREE.FogExp2(0x0b001a, 0.002);

    // CAMERA
    camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 40, 100);

    // RENDERER
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // CONTROLS
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.5;

    // LIGHTS
    const ambientLight = new THREE.AmbientLight(0x4040a0, 2.0); // Blueish ambient
    scene.add(ambientLight);

    const sunLight = new THREE.PointLight(0xffaa00, 2, 200);
    sunLight.position.set(0, 0, 0);
    scene.add(sunLight);

    // 🌌 NEBULA CLOUDS (Colorful Background)
    const particleCount = 1500;
    const geometry = new THREE.BufferGeometry();
    const positions = [];
    const colors = [];

    const colorPalette = [
        new THREE.Color(0x8b5cf6), // Violet
        new THREE.Color(0xec4899), // Pink
        new THREE.Color(0x3b82f6), // Blue
        new THREE.Color(0x10b981)  // Emerald
    ];

    for (let i = 0; i < particleCount; i++) {
        // Random position in a large sphere
        const r = 400 + Math.random() * 400; // Distant background
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos((Math.random() * 2) - 1);

        const x = r * Math.sin(phi) * Math.cos(theta);
        const y = r * Math.sin(phi) * Math.sin(theta);
        const z = r * Math.cos(phi);

        positions.push(x, y, z);

        // Random color from palette
        const color = colorPalette[Math.floor(Math.random() * colorPalette.length)];
        colors.push(color.r, color.g, color.b);
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
        size: 4,
        vertexColors: true,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending
    });

    const starField = new THREE.Points(geometry, material);
    scene.add(starField);

    // GRID HELPER (Sci-Fi feel)
    const gridHelper = new THREE.PolarGridHelper(200, 16, 8, 32, 0x2d3748, 0x2d3748);
    gridHelper.position.y = -50;
    gridHelper.material.opacity = 0.2;
    gridHelper.material.transparent = true;
    scene.add(gridHelper);

    animate();
}

function animate() {
    requestAnimationFrame(animate);
    if (controls) controls.update();
    renderer.render(scene, camera);
}

// Render Galaxy Data
function renderGalaxy3D(data) {
    if (!scene) return;

    // Clear old meshes
    for (let i = scene.children.length - 1; i >= 0; i--) {
        const obj = scene.children[i];
        if (obj.userData.isDynamic) {
            scene.remove(obj);
        }
    }

    // DRAW FILES (STARS)
    data.files.forEach(file => {
        let radius = Math.max(1.5, file.size_radius); // Bigger stars
        const geometry = new THREE.SphereGeometry(radius, 32, 32);

        // Neon Colors
        let color = 0xffffff;
        switch (file.color) {
            case 'blue': color = 0x60a5fa; break;  // Neon Blue
            case 'red': color = 0xf87171; break;   // Neon Red
            case 'green': color = 0x4ade80; break; // Neon Green
            case 'yellow': color = 0xfacc15; break;// Neon Yellow
            case 'magenta': color = 0xe879f9; break;// Neon Magenta
        }

        const material = new THREE.MeshStandardMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 2.0, // HIGH GLOW
            roughness: 0.1,
            metalness: 0.9
        });

        const sphere = new THREE.Mesh(geometry, material);
        sphere.position.set(file.position.x, file.position.y, file.position.z);
        sphere.userData.isDynamic = true; // Mark for clearing
        scene.add(sphere);

        // Add a "Glow" sprite? Optional, keeping it simple for now with high emissive.
    });

    // DRAW LINKS (LASERS)
    const material = new THREE.LineBasicMaterial({
        color: 0x00ffff, // Cyan Lasers
        opacity: 0.8,
        transparent: true,
        linewidth: 2
    });

    data.links.forEach(link => {
        const f1 = data.files.find(f => f.path === link.file1);
        const f2 = data.files.find(f => f.path === link.file2);

        if (f1 && f2) {
            const points = [];
            points.push(new THREE.Vector3(f1.position.x, f1.position.y, f1.position.z));
            points.push(new THREE.Vector3(f2.position.x, f2.position.y, f2.position.z));
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const line = new THREE.Line(geometry, material);
            line.userData.isDynamic = true;
            scene.add(line);
        }
    });
}

// Modified Fetch Galaxy
async function fetchGalaxy() {
    try {
        const res = await fetch(`${API_URL}/galaxy/json`); // New JSON endpoint
        const data = await res.json();

        // Init 3D scene if not ready
        if (!scene) initGalaxy3D();

        renderGalaxy3D(data);
    } catch (err) {
        console.error(err);
    }
}

// Fetch Logs
async function fetchLogs() {
    try {
        const res = await fetch(`${API_URL}/logs`);
        const logs = await res.json();
        const tbody = document.getElementById('auditTableBody');
        tbody.innerHTML = '';

        logs.forEach(log => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${new Date(log.timestamp * 1000).toLocaleString()}</td>
                <td style="color: var(--primary)">${log.operation}</td>
                <td>${log.file_path}</td>
                <td>${log.user}</td>
                <td>${log.success ? '✅ Success' : '❌ Failed'}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error(err);
    }
}

// Poll for updates every 5 seconds
setInterval(() => {
    // Optional: Auto-refresh data
}, 5000);
