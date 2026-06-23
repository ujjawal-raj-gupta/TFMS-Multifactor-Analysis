(function initThreeBackground() {
  const canvas = document.getElementById("bg-canvas");
  if (!window.THREE || !canvas) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const { THREE } = window;

  const COLORS = {
    cyan: 0x00d4ff,
    purple: 0xa855f7,
    orange: 0xff8c42,
    green: 0x00ff88,
    pink: 0xff3366,
    gold: 0xffd166,
  };
  const palette = Object.values(COLORS);

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x080c18, 0.009);

  const camera = new THREE.PerspectiveCamera(52, 1, 0.1, 400);
  camera.position.set(0, 4, 62);

  const group = new THREE.Group();
  scene.add(group);

  function coloredMat(color, opacity = 0.25, wireframe = false) {
    return new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      wireframe,
    });
  }

  const globe = new THREE.Mesh(
    new THREE.IcosahedronGeometry(14, 2),
    coloredMat(COLORS.cyan, 0.22, true)
  );
  globe.position.set(-22, 2, -8);
  group.add(globe);

  const globe2 = new THREE.Mesh(
    new THREE.IcosahedronGeometry(9, 1),
    coloredMat(COLORS.purple, 0.2, true)
  );
  globe2.position.set(28, -4, -10);
  group.add(globe2);

  function buildBars(offsetX, offsetY, offsetZ, rotY, scale) {
    const barGroup = new THREE.Group();
    const barHeights = [3.5, 6, 4.2, 8, 5, 7.2, 3.8, 6.5];
    barHeights.forEach((h, i) => {
      const bar = new THREE.Mesh(
        new THREE.BoxGeometry(1.4, h, 1.4),
        coloredMat(palette[i % palette.length], 0.22 + (i % 3) * 0.06)
      );
      bar.position.set(-8 + i * 2.2, h / 2 - 4, -12 + (i % 2) * 3);
      barGroup.add(bar);
    });
    barGroup.position.set(offsetX, offsetY, offsetZ);
    barGroup.rotation.y = rotY;
    barGroup.scale.set(scale, scale, scale);
    return barGroup;
  }

  const barGroup = buildBars(18, 0, -6, -0.35, 1);
  group.add(barGroup);
  group.add(buildBars(-30, -2, 4, 0.5, 0.7));
  group.add(buildBars(32, 6, 2, -0.8, 0.55));

  const nodeCount = 32;
  const nodePositions = [];
  const nodeColors = [];
  for (let i = 0; i < nodeCount; i += 1) {
    nodePositions.push(
      (Math.random() - 0.5) * 95,
      (Math.random() - 0.5) * 45,
      (Math.random() - 0.5) * 55 - 10
    );
    const c = new THREE.Color(palette[i % palette.length]);
    nodeColors.push(c.r, c.g, c.b);
  }
  const nodeGeom = new THREE.BufferGeometry();
  nodeGeom.setAttribute("position", new THREE.Float32BufferAttribute(nodePositions, 3));
  nodeGeom.setAttribute("color", new THREE.Float32BufferAttribute(nodeColors, 3));
  const nodes = new THREE.Points(
    nodeGeom,
    new THREE.PointsMaterial({ size: 0.65, transparent: true, opacity: 0.75, vertexColors: true })
  );
  group.add(nodes);

  const linePositions = [];
  const lineColors = [];
  for (let i = 0; i < nodeCount; i += 1) {
    const j = (i + 3 + Math.floor(Math.random() * 5)) % nodeCount;
    linePositions.push(
      nodePositions[i * 3], nodePositions[i * 3 + 1], nodePositions[i * 3 + 2],
      nodePositions[j * 3], nodePositions[j * 3 + 1], nodePositions[j * 3 + 2]
    );
    const c = new THREE.Color(palette[i % palette.length]);
    lineColors.push(c.r, c.g, c.b, c.r, c.g, c.b);
  }
  const lines = new THREE.LineSegments(
    new THREE.BufferGeometry()
      .setAttribute("position", new THREE.Float32BufferAttribute(linePositions, 3))
      .setAttribute("color", new THREE.Float32BufferAttribute(lineColors, 3)),
    new THREE.LineBasicMaterial({ transparent: true, opacity: 0.2, vertexColors: true })
  );
  group.add(lines);

  const particleCount = 1600;
  const particlePositions = new Float32Array(particleCount * 3);
  const particleColors = new Float32Array(particleCount * 3);
  for (let i = 0; i < particleCount; i += 1) {
    particlePositions[i * 3] = (Math.random() - 0.5) * 150;
    particlePositions[i * 3 + 1] = (Math.random() - 0.5) * 90;
    particlePositions[i * 3 + 2] = (Math.random() - 0.5) * 80;
    const c = new THREE.Color(palette[i % palette.length]);
    particleColors[i * 3] = c.r;
    particleColors[i * 3 + 1] = c.g;
    particleColors[i * 3 + 2] = c.b;
  }
  const particles = new THREE.Points(
    new THREE.BufferGeometry()
      .setAttribute("position", new THREE.BufferAttribute(particlePositions, 3))
      .setAttribute("color", new THREE.BufferAttribute(particleColors, 3)),
    new THREE.PointsMaterial({ size: 0.28, transparent: true, opacity: 0.5, vertexColors: true })
  );
  scene.add(particles);

  [
    { color: COLORS.cyan, r: 22, x: 8, y: -6, z: -18 },
    { color: COLORS.purple, r: 16, x: -24, y: 8, z: -12 },
    { color: COLORS.orange, r: 12, x: 20, y: 10, z: -8 },
  ].forEach(({ color, r, x, y, z }) => {
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(r, 0.07, 8, 80),
      coloredMat(color, 0.28)
    );
    ring.rotation.x = Math.PI / 2.4;
    ring.position.set(x, y, z);
    group.add(ring);
  });

  function resize() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  resize();
  window.addEventListener("resize", resize);

  if (reducedMotion) {
    renderer.render(scene, camera);
    return;
  }

  let t = 0;
  function animate() {
    requestAnimationFrame(animate);
    t += 0.005;
    group.rotation.y = Math.sin(t * 0.35) * 0.1;
    globe.rotation.y += 0.003;
    globe.rotation.x += 0.0015;
    globe2.rotation.y -= 0.004;
    barGroup.rotation.y = -0.35 + Math.sin(t) * 0.06;
    particles.rotation.y += 0.0006;
    particles.rotation.x = Math.sin(t * 0.3) * 0.02;
    camera.position.x = Math.sin(t * 0.5) * 3;
    camera.position.y = 4 + Math.sin(t * 0.35) * 1.5;
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
  }
  animate();
})();
