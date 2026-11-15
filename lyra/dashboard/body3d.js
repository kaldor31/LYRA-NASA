// LYRA: 3D point cloud of the astronaut body (ToF for the body, structured light for the face).
// API: createBody(container) -> { setParams, setView, scan, setLabels, setSkeleton, resize, dispose }
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const STATUS_COLORS = { green: "#5BC98A", yellow: "#E8B04B", red: "#F0686A" };
const NEUTRAL = new THREE.Color("#A3A9AF");
const ACCENT = new THREE.Color("#8FB2E8");
const ZONES = ["face", "legs", "body", "hands", "posture"];
// Body parts (id) -> zone
const P = { HEAD: 0, EYE: 1, NOSE: 2, NECK: 3, TORSO: 4, PELVIS: 5, THIGH: 6, SHIN: 7, FOOT: 8, UARM: 9, FARM: 10, HAND: 11, DELT: 12 };
const PART_ZONE = [0, 0, 0, 4, 2, 2, 1, 1, 1, 2, 3, 3, 2];
const FACE_PARTS = new Set([P.HEAD, P.EYE, P.NOSE]);
const UPPER_PARTS = new Set([P.HEAD, P.EYE, P.NOSE, P.NECK, P.UARM, P.FARM, P.HAND, P.DELT]);
const ARM_PARTS = new Set([P.UARM, P.FARM, P.HAND, P.DELT]);
const SPINE_LO = 0.98, SPINE_HI = 1.45, NECK_BASE = 1.47;
const FOV = 35;
const REDUCED = () => !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Deterministic PRNG so the cloud is identical on every load
function rng(seed) {
  return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const rand = rng(1717);
const gauss = () => (rand() + rand() + rand() - 1.5) * 0.8;

// ---------- Procedural body model ----------
function buildBodyPoints() {
  const pts = []; // {x,y,z, nx,ny,nz, cx,cy,cz, part, size}
  const add = (x, y, z, nx, ny, nz, cx, cy, cz, part, noise) => {
    pts.push({ x: x + gauss() * noise, y: y + gauss() * noise, z: z + gauss() * noise, nx, ny, nz, cx, cy, cz, part });
  };
  const BODY_D = 7200, FACE_D = 24000; // points per m2 (ToF / structured light)

  // Capsule (truncated cone) between a and b; caps: [start, end] close with a hemisphere
  function limb(a, b, r1, r2, part, bulge = 0, caps = [false, false]) {
    const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b);
    const axis = B.clone().sub(A), L = axis.length(); axis.normalize();
    const u = new THREE.Vector3(1, 0, 0); if (Math.abs(axis.x) > 0.9) u.set(0, 0, 1);
    u.cross(axis).normalize(); const v = axis.clone().cross(u).normalize();
    const rAt = (t) => r1 + (r2 - r1) * t + bulge * Math.sin(Math.PI * t);
    const n = Math.round(BODY_D * 2 * Math.PI * ((r1 + r2) / 2 + bulge * 0.6) * L);
    for (let i = 0; i < n; i++) {
      const t = rand(), ang = rand() * Math.PI * 2, r = rAt(t);
      const d = u.clone().multiplyScalar(Math.cos(ang)).addScaledVector(v, Math.sin(ang));
      const c = A.clone().addScaledVector(axis, t * L);
      add(c.x + d.x * r, c.y + d.y * r, c.z + d.z * r, d.x, d.y, d.z, c.x, c.y, c.z, part, 0.003);
    }
    [[A, r1, -1, caps[0]], [B, r2, 1, caps[1]]].forEach(([C, r, sgn, on]) => {
      if (!on) return;
      const m = Math.round(BODY_D * 2 * Math.PI * r * r);
      for (let i = 0; i < m; i++) {
        const d = new THREE.Vector3(gauss(), gauss(), gauss()).normalize();
        if (d.dot(axis) * sgn < 0) d.addScaledVector(axis, -2 * d.dot(axis));
        add(C.x + d.x * r, C.y + d.y * r, C.z + d.z * r, d.x, d.y, d.z, C.x, C.y, C.z, part, 0.003);
      }
    });
  }
  // Ellipsoid; shape(x,y,z) may adjust a point (for example narrow the chin)
  function blob(c, r, part, density, noise, shape) {
    const area = 4 * Math.PI * Math.pow((Math.pow(r[0] * r[1], 1.6) + Math.pow(r[0] * r[2], 1.6) + Math.pow(r[1] * r[2], 1.6)) / 3, 1 / 1.6);
    const n = Math.round(density * area);
    for (let i = 0; i < n; i++) {
      const d = new THREE.Vector3(gauss(), gauss(), gauss()).normalize();
      let x = d.x * r[0], y = d.y * r[1], z = d.z * r[2];
      if (shape) [x, y, z] = shape(x, y, z);
      const nn = new THREE.Vector3(x / (r[0] * r[0]), y / (r[1] * r[1]), z / (r[2] * r[2])).normalize();
      add(c[0] + x, c[1] + y, c[2] + z, nn.x, nn.y, nn.z, c[0], c[1], c[2], part, noise);
    }
  }

  // Head: ellipsoid narrowing toward the chin
  const HC = [0, 1.655, 0.01], HR = [0.076, 0.108, 0.095];
  const chin = (x, y, z) => { if (y < 0) { const k = 1 - 0.32 * (-y / HR[1]); x *= k; z = z * (0.85 + 0.15 * k) + (z > 0 ? 0 : 0.01 * (1 - k)); } return [x, y, z]; };
  blob(HC, HR, P.HEAD, FACE_D, 0.0012, chin);
  // Dense patches around the eyes (periorbital puffiness)
  for (const sx of [-1, 1]) {
    for (let i = 0; i < 200; i++) {
      const dx = sx * 0.032 + gauss() * 0.02, dy = 0.008 + gauss() * 0.012;
      // project onto the front of the ellipsoid
      const zz = HR[2] * Math.sqrt(Math.max(0.02, 1 - (dx / HR[0]) ** 2 - (dy / HR[1]) ** 2));
      const nn = new THREE.Vector3(dx / HR[0] ** 2, dy / HR[1] ** 2, zz / HR[2] ** 2).normalize();
      add(HC[0] + dx, HC[1] + dy, HC[2] + zz - 0.004, nn.x, nn.y, nn.z, HC[0], HC[1], HC[2], P.EYE, 0.001);
    }
  }
  limb([0, 1.66, 0.098], [0, 1.625, 0.118], 0.011, 0.014, P.NOSE, 0, [true, true]);       // nose
  for (const sx of [-1, 1]) blob([sx * 0.078, 1.655, 0.0], [0.012, 0.03, 0.02], P.HEAD, FACE_D * 0.6, 0.001); // ears
  limb([0, 1.45, -0.005], [0, 1.575, 0.005], 0.055, 0.05, P.NECK);                          // neck

  // Torso: stacked ellipses along a profile (narrow waist, wider chest and shoulders)
  const prof = [[0.84, 0.15, 0.1], [0.92, 0.163, 0.106], [1.0, 0.148, 0.098], [1.07, 0.134, 0.094], [1.16, 0.143, 0.1], [1.28, 0.166, 0.113], [1.37, 0.174, 0.106], [1.44, 0.135, 0.082]];
  const at = (y) => { for (let i = 1; i < prof.length; i++) if (y <= prof[i][0]) {
    const t = (y - prof[i - 1][0]) / (prof[i][0] - prof[i - 1][0]);
    return [prof[i - 1][1] + (prof[i][1] - prof[i - 1][1]) * t, prof[i - 1][2] + (prof[i][2] - prof[i - 1][2]) * t]; }
    return [prof[prof.length - 1][1], prof[prof.length - 1][2]]; };
  const torsoN = Math.round(BODY_D * 2 * Math.PI * 0.135 * 0.6);
  for (let i = 0; i < torsoN; i++) {
    const y = 0.84 + rand() * 0.6, [rx, rz] = at(y), a = rand() * Math.PI * 2;
    const cz = 0.008 * Math.sin(((y - 0.84) / 0.6) * Math.PI); // chest slightly forward
    const nn = new THREE.Vector3(Math.cos(a) / rx, 0, Math.sin(a) / rz).normalize();
    add(Math.cos(a) * rx, y, cz + Math.sin(a) * rz, nn.x, 0.1, nn.z, 0, y, cz, P.TORSO, 0.003);
  }
  // Top of the torso: slope from shoulders to neck
  for (let i = 0; i < 900; i++) {
    const s = Math.sqrt(rand()), a = rand() * Math.PI * 2;
    const k = 0.36 + 0.64 * s, rx = 0.135 * k, rz = 0.082 * k, y = 1.44 + 0.04 * (1 - s);
    add(Math.cos(a) * rx, y, Math.sin(a) * rz, Math.cos(a) * 0.5, 0.85, Math.sin(a) * 0.5, 0, y, 0, P.TORSO, 0.003);
  }
  blob([0, 0.84, -0.005], [0.15, 0.07, 0.1], P.PELVIS, BODY_D * 0.5, 0.003, (x, y, z) => [x, -Math.abs(y), z]); // bottom of the pelvis

  for (const sx of [-1, 1]) {
    // Legs
    limb([sx * 0.095, 0.89, 0], [sx * 0.098, 0.49, 0.012], 0.085, 0.054, P.THIGH, 0.006);
    limb([sx * 0.098, 0.49, 0.012], [sx * 0.1, 0.085, -0.005], 0.05, 0.034, P.SHIN, 0.012);
    blob([sx * 0.103, 0.045, 0.05], [0.042, 0.035, 0.11], P.FOOT, BODY_D, 0.003, (x, y, z) => [x, Math.max(y, -0.035 + 0.0), z]);
    // Arms: shoulder -> elbow (slightly out) -> hand forward to the grip
    blob([sx * 0.188, 1.41, 0], [0.058, 0.06, 0.06], P.DELT, BODY_D, 0.003);
    limb([sx * 0.2, 1.4, 0], [sx * 0.265, 1.13, -0.03], 0.046, 0.037, P.UARM, 0.004);
    limb([sx * 0.265, 1.13, -0.03], [sx * 0.3, 1.045, 0.22], 0.037, 0.027, P.FARM, 0.005, [true, false]);
    blob([sx * 0.305, 1.035, 0.27], [0.03, 0.045, 0.05], P.HAND, BODY_D * 1.3, 0.002);      // fist on the grip
  }
  return pts;
}

// ---------- Label styles (once) ----------
function injectStyles() {
  if (document.getElementById("body3d-styles")) return;
  const st = document.createElement("style"); st.id = "body3d-styles";
  st.textContent = `
.body3d-overlay{position:absolute;inset:0;pointer-events:none;overflow:hidden}
.body3d-label{position:absolute;left:0;top:0;padding:4px 8px;font:500 13px/1.25 "IBM Plex Sans",system-ui,sans-serif;font-variant-numeric:tabular-nums;color:#E7ECF0;
 background:rgba(13,17,20,.88);border-left:2px solid #B9C7D6;border-radius:2px;white-space:nowrap;will-change:transform}
.body3d-label.status-green{border-left-color:#5BC98A}.body3d-label.status-yellow{border-left-color:#E8B04B}.body3d-label.status-red{border-left-color:#F0686A}
.body3d-dot{position:absolute;left:0;top:0;width:7px;height:7px;margin:-3.5px 0 0 -3.5px;border-radius:50%;background:#B9C7D6;border:1.5px solid #0D1114}
.body3d-line{position:absolute;left:0;top:0;height:1px;transform-origin:0 0;background:#B9C7D6;opacity:.6}
.body3d-fallback{display:flex;align-items:center;justify-content:center;width:100%;height:100%;min-height:120px;color:#7F8B96;font-size:14px}`;
  document.head.appendChild(st);
}

function webglAvailable() {
  try { const c = document.createElement("canvas"); return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl"))); }
  catch { return false; }
}

function stubApi(container) {
  injectStyles();
  const d = document.createElement("div"); d.className = "body3d-fallback"; d.textContent = "3D view is not available in this browser";
  container.appendChild(d);
  const noop = () => {};
  return { setParams: noop, setView: noop, scan: noop, setLabels: noop, setSkeleton: noop, resize: noop, dispose: () => d.remove() };
}

// ---------- Main function ----------
export function createBody(container) {
  if (!webglAvailable()) return stubApi(container);
  let renderer;
  try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); }
  catch { return stubApi(container); }
  injectStyles();
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  if (getComputedStyle(container).position === "static") container.style.position = "relative";
  const canvas = renderer.domElement;
  canvas.style.cssText = "display:block;width:100%;height:100%;position:absolute;inset:0";
  container.appendChild(canvas);
  const overlay = document.createElement("div"); overlay.className = "body3d-overlay"; container.appendChild(overlay);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.05, 50);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true; controls.enablePan = false; controls.autoRotateSpeed = 0.8;
  controls.minDistance = 1.2; controls.maxDistance = 9;

  // --- Point cloud ---
  const src = buildBodyPoints(), N = src.length;
  const base = new Float32Array(N * 3), cen = new Float32Array(N * 3), part = new Uint8Array(N), zone = new Uint8Array(N);
  const pos = new Float32Array(N * 3), nrm = new Float32Array(N * 3), col = new Float32Array(N * 3), colT = new Float32Array(N * 3);
  const size = new Float32Array(N), pulse = new Float32Array(N), bright = new Float32Array(N);
  src.forEach((p, i) => {
    base.set([p.x, p.y, p.z], i * 3); cen.set([p.cx, p.cy, p.cz], i * 3);
    const nl = Math.hypot(p.nx, p.ny, p.nz) || 1; nrm.set([p.nx / nl, p.ny / nl, p.nz / nl], i * 3);
    part[i] = p.part; zone[i] = PART_ZONE[p.part];
    // Posture zone also includes a strip along the spine
    if (p.part === P.TORSO && Math.abs(p.x) < 0.035 && p.z < -0.05 && p.y > 1.0) zone[i] = 4;
    const face = FACE_PARTS.has(p.part);
    size[i] = face ? 0.0042 : 0.0068;
    bright[i] = 0.82 + rand() * 0.3;
  });
  pos.set(base);
  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geom.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
  geom.setAttribute("aColor", new THREE.BufferAttribute(col, 3));
  geom.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
  geom.setAttribute("aPulse", new THREE.BufferAttribute(pulse, 1));
  const uniforms = { uTime: { value: 0 }, uScale: { value: 500 }, uScanOn: { value: 0 }, uScanY: { value: 1 }, uScanDown: { value: 1 }, uFade: { value: 1 } };
  const mat = new THREE.ShaderMaterial({
    uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `
      attribute vec3 aColor; attribute float aSize; attribute float aPulse;
      uniform float uTime, uScale, uScanOn, uScanY, uScanDown;
      varying vec3 vColor; varying float vAlpha;
      void main(){
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        vec3 n = normalize(normalMatrix * normal);
        float rim = 1.0 - abs(n.z);
        float pul = aPulse * (0.5 + 0.5 * sin(uTime * 2.5 + position.y * 5.0));
        float b = 0.45 + 0.8 * rim * rim + 0.5 * pul;
        float a = 1.0, glow = 0.0;
        if (uScanOn > 0.5) { float d = position.y - uScanY; glow = exp(-d * d / 0.0006);
          if (uScanDown > 0.5 && d < 0.0) a = 0.05; }
        vColor = aColor * b + vec3(0.56, 0.70, 0.91) * glow;
        vAlpha = a;
        gl_PointSize = max(1.5, aSize * (1.0 + 0.45 * pul + glow) * uScale / -mv.z);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      uniform float uFade; varying vec3 vColor; varying float vAlpha;
      void main(){ vec2 c = gl_PointCoord - 0.5; float d = dot(c, c); if (d > 0.25) discard;
        gl_FragColor = vec4(vColor, vAlpha * uFade * smoothstep(0.25, 0.02, d) * 0.8); }`,
  });
  const cloud = new THREE.Points(geom, mat); cloud.frustumCulled = false; scene.add(cloud);

  // --- LYRA station: work area, posts, grips ---
  const station = new THREE.Group(); scene.add(station);
  const lineMat = (o) => new THREE.LineBasicMaterial({ color: 0x8fa3b8, transparent: true, opacity: o, depthWrite: false });
  const seg = (arr, o) => { const g = new THREE.BufferGeometry().setFromPoints(arr.map((a) => new THREE.Vector3(...a))); station.add(new THREE.LineSegments(g, lineMat(o))); };
  const grid = []; for (let k = -0.6; k <= 0.601; k += 0.2) grid.push([k, 0, -0.6], [k, 0, 0.6], [-0.6, 0, k], [0.6, 0, k]);
  seg(grid, 0.08);
  seg([[-0.6, 0, -0.6], [0.6, 0, -0.6], [0.6, 0, -0.6], [0.6, 0, 0.6], [0.6, 0, 0.6], [-0.6, 0, 0.6], [-0.6, 0, 0.6], [-0.6, 0, -0.6]], 0.35);
  const ring = []; for (let i = 0; i < 64; i++) { const a = (i / 64) * Math.PI * 2, b = ((i + 1) / 64) * Math.PI * 2;
    ring.push([Math.cos(a) * 0.45, 0.001, Math.sin(a) * 0.45], [Math.cos(b) * 0.45, 0.001, Math.sin(b) * 0.45]); }
  seg(ring, 0.25);
  const posts = [[-0.55, 0.45], [0.55, 0.45], [0, -0.6]], ticks = [];
  posts.forEach(([x, z]) => { ticks.push([x, 0, z], [x, 2.0, z]);
    for (const h of [0.5, 1.0, 1.5, 1.95]) ticks.push([x - 0.025, h, z], [x + 0.025, h, z]); }); // ToF sensors
  seg(ticks, 0.4);
  // Grips on the front posts at elbow height
  for (const sx of [-1, 1]) seg([[sx * 0.55, 1.04, 0.45], [sx * 0.305, 1.035, 0.29], [sx * 0.305, 0.97, 0.28], [sx * 0.305, 1.1, 0.28]], 0.55);

  // --- Scan plane ---
  const scanGroup = new THREE.Group(); scanGroup.visible = false; scene.add(scanGroup);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(0.62, 48), new THREE.MeshBasicMaterial({ color: 0x8fb2e8, transparent: true, opacity: 0.06, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }));
  disc.rotation.x = -Math.PI / 2; scanGroup.add(disc);
  const sring = []; for (let i = 0; i <= 64; i++) { const a = (i / 64) * Math.PI * 2; sring.push(new THREE.Vector3(Math.cos(a) * 0.62, 0, Math.sin(a) * 0.62)); }
  scanGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(sring), new THREE.LineBasicMaterial({ color: 0x8fb2e8, transparent: true, opacity: 0.7 })));

  // --- Parameters and deformation ---
  const KEYS = ["face_pct", "periorbital_mm", "legs_pct", "body_pct", "height_pct", "head_forward_deg", "shoulder_asym_deg"];
  const cur = Object.fromEntries(KEYS.map((k) => [k, 0])), tgt = { ...cur };
  let geomDirty = true, colorDirty = true, zones = {};
  const tmp = [0, 0, 0];

  // Deform one point by current parameters (visual gain: face x2.2, legs x3, height x3)
  function deform(x, y, z, pt, cx, cy, cz, nx, ny, nz, out) {
    const fk = cur.face_pct * 0.022, lk = cur.legs_pct * 0.03, bk = cur.body_pct * 0.02;
    let s = 1, sy = 1;
    if (FACE_PARTS.has(pt)) { s = 1 + fk * (0.7 + 0.5 * Math.min(1, Math.max(0, (1.68 - y) / 0.12))); sy = 1 + fk * 0.25; }
    else if (pt === P.NECK) s = 1 + fk * 0.5;
    else if (pt === P.THIGH) s = 1 + lk * 0.75;
    else if (pt === P.SHIN) s = 1 + lk;
    else if (pt === P.FOOT) s = 1 + lk * 0.25;
    else if (pt === P.TORSO || pt === P.PELVIS) s = 1 + bk;
    s = Math.max(0.55, s);
    x = cx + (x - cx) * s; z = cz + (z - cz) * s; if (sy !== 1) y = cy + (y - cy) * sy;
    if (pt === P.EYE) { const e = cur.periorbital_mm * 0.003; x += nx * e; y += ny * e; z += nz * e; }
    // Shoulder asymmetry: tilt of the shoulder line
    const sa = Math.tan((cur.shoulder_asym_deg * 2 * Math.PI) / 180);
    const w = ARM_PARTS.has(pt) ? 1 : pt === P.TORSO ? Math.min(1, Math.max(0, (y - 1.2) / 0.25)) : 0;
    y += x * sa * w;
    // Height: spinal elongation
    const stretch = cur.height_pct * 0.03 * (SPINE_HI - SPINE_LO);
    if (pt === P.TORSO) y += Math.min(1, Math.max(0, (y - SPINE_LO) / (SPINE_HI - SPINE_LO))) * stretch;
    else if (UPPER_PARTS.has(pt)) y += stretch;
    // Head forward tilt around the base of the neck
    if (FACE_PARTS.has(pt) || pt === P.NECK) {
      const py = NECK_BASE + stretch;
      let th = (cur.head_forward_deg * 1.3 * Math.PI) / 180;
      if (pt === P.NECK) th *= Math.min(1, Math.max(0, (y - py) / 0.12));
      const dy = y - py, c = Math.cos(th), sn = Math.sin(th);
      y = py + dy * c - z * sn; z = z * c + dy * sn;
    }
    out[0] = x; out[1] = y; out[2] = z; return out;
  }
  function rebuildPositions() {
    for (let i = 0; i < N; i++) {
      const j = i * 3;
      deform(base[j], base[j + 1], base[j + 2], part[i], cen[j], cen[j + 1], cen[j + 2], nrm[j], nrm[j + 1], nrm[j + 2], tmp);
      pos[j] = tmp[0]; pos[j + 1] = tmp[1]; pos[j + 2] = tmp[2];
    }
    geom.attributes.position.needsUpdate = true;
  }
  function changing(zn) {
    if (zn === "face") return Math.abs(tgt.face_pct) >= 1 || Math.abs(tgt.periorbital_mm) >= 0.5;
    if (zn === "legs") return Math.abs(tgt.legs_pct) >= 1;
    if (zn === "body") return Math.abs(tgt.body_pct) >= 1 || Math.abs(tgt.height_pct) >= 1;
    if (zn === "posture") return Math.abs(tgt.head_forward_deg) >= 3 || Math.abs(tgt.shoulder_asym_deg) >= 1;
    return false;
  }
  function rebuildColorTargets() {
    // Status colour only for Recheck/Deviation; a normal but changing zone gets the accent; the rest stays neutral.
    const zc = ZONES.map((zn) => (zones[zn] && zones[zn] !== "green" && STATUS_COLORS[zones[zn]] ? new THREE.Color(STATUS_COLORS[zones[zn]])
      : changing(zn) ? ACCENT : NEUTRAL));
    const zp = ZONES.map((zn) => (changing(zn) ? 1 : 0));
    for (let i = 0; i < N; i++) {
      const c = zc[zone[i]], b = c === NEUTRAL ? bright[i] : 0.9 + (bright[i] - 0.82) * 0.5;
      colT[i * 3] = c.r * b; colT[i * 3 + 1] = c.g * b; colT[i * 3 + 2] = c.b * b; pulse[i] = zp[zone[i]];
    }
    geom.attributes.aPulse.needsUpdate = true; colorDirty = true;
  }
  rebuildColorTargets();

  // --- Skeletal keypoint model (front, side and back views are fused into these joints) ---
  const KP = [ // [x, y, z, part, cx, cy, cz]
    [0, 1.66, 0.01, P.HEAD, 0, 1.655, 0.01], [0, 1.47, 0, P.NECK, 0, 1.5, 0],
    [-0.19, 1.41, 0, P.DELT, -0.188, 1.41, 0], [0.19, 1.41, 0, P.DELT, 0.188, 1.41, 0],
    [-0.265, 1.13, -0.03, P.UARM, -0.265, 1.13, -0.03], [0.265, 1.13, -0.03, P.UARM, 0.265, 1.13, -0.03],
    [-0.3, 1.045, 0.22, P.FARM, -0.3, 1.045, 0.22], [0.3, 1.045, 0.22, P.FARM, 0.3, 1.045, 0.22],
    [0, 0.92, 0, P.PELVIS, 0, 0.92, 0], [-0.095, 0.89, 0, P.THIGH, -0.095, 0.89, 0], [0.095, 0.89, 0, P.THIGH, 0.095, 0.89, 0],
    [-0.098, 0.49, 0.012, P.SHIN, -0.098, 0.49, 0.012], [0.098, 0.49, 0.012, P.SHIN, 0.098, 0.49, 0.012],
    [-0.1, 0.07, 0.02, P.FOOT, -0.1, 0.07, 0.02], [0.1, 0.07, 0.02, P.FOOT, 0.1, 0.07, 0.02]];
  const BONES = [[0, 1], [1, 2], [1, 3], [2, 4], [3, 5], [4, 6], [5, 7], [1, 8], [8, 9], [8, 10], [9, 11], [10, 12], [11, 13], [12, 14], [2, 3], [9, 10]];
  const kpPos = new Float32Array(KP.length * 3), bonePos = new Float32Array(BONES.length * 6);
  const kpGeom = new THREE.BufferGeometry(); kpGeom.setAttribute("position", new THREE.BufferAttribute(kpPos, 3));
  const boneGeom = new THREE.BufferGeometry(); boneGeom.setAttribute("position", new THREE.BufferAttribute(bonePos, 3));
  const skeleton = new THREE.Group(); skeleton.visible = false; skeleton.renderOrder = 5; scene.add(skeleton);
  skeleton.add(new THREE.LineSegments(boneGeom, new THREE.LineBasicMaterial({ color: 0x8fb2e8, transparent: true, opacity: 0.95, depthTest: false })));
  const dotTex = (() => { const cv = document.createElement("canvas"); cv.width = cv.height = 32; const g = cv.getContext("2d");
    g.fillStyle = "#fff"; g.beginPath(); g.arc(16, 16, 12, 0, Math.PI * 2); g.fill(); g.strokeStyle = "#0D1114"; g.lineWidth = 4; g.stroke(); return new THREE.CanvasTexture(cv); })();
  const kpPts = new THREE.Points(kpGeom, new THREE.PointsMaterial({ color: 0xe7ecf0, size: 8, map: dotTex, alphaTest: 0.4, transparent: true, sizeAttenuation: false, depthTest: false }));
  kpPts.renderOrder = 6; skeleton.add(kpPts);
  function rebuildSkeleton() {
    KP.forEach((k, i) => { deform(k[0], k[1], k[2], k[3], k[4], k[5], k[6], 0, 0, 1, tmp); kpPos.set(tmp, i * 3); });
    BONES.forEach(([a, b], i) => { bonePos.set(kpPos.subarray(a * 3, a * 3 + 3), i * 6); bonePos.set(kpPos.subarray(b * 3, b * 3 + 3), i * 6 + 3); });
    kpGeom.attributes.position.needsUpdate = true; boneGeom.attributes.position.needsUpdate = true;
  }
  rebuildSkeleton();
  function setSkeleton(on) { skeleton.visible = !!on; uniforms.uFade.value = on ? 0.4 : 1; }

  // --- Camera and views ---
  const VIEWS = { front: { theta: 0, phi: Math.PI / 2 - 0.06, ty: 0.98 }, side: { theta: Math.PI / 2, phi: Math.PI / 2 - 0.06, ty: 0.98 },
    back: { theta: Math.PI, phi: Math.PI / 2 - 0.06, ty: 0.98 }, top: { theta: 0, phi: 0.02, ty: 0.9 }, orbit: { theta: Math.PI / 5, phi: Math.PI / 2 - 0.22, ty: 0.98 } };
  let view = "front", tween = null, W = 0, H = 0;
  const half = Math.tan(((FOV / 2) * Math.PI) / 180);
  function fitDistance(name) {
    const aspect = W && H ? W / H : 1;
    if (name === "top") return Math.max(0.72 / half, 0.72 / (half * aspect)) + 1.0;
    return Math.max(1.06 / half, 0.72 / (half * aspect)) + 0.55;
  }
  function placeCamera(theta, phi, r, ty) {
    const sp = new THREE.Spherical(r, phi, theta);
    camera.position.setFromSpherical(sp).add(new THREE.Vector3(0, ty, 0));
    controls.target.set(0, ty, 0); camera.lookAt(controls.target);
  }
  function setView(name) {
    if (!VIEWS[name]) return;
    view = name; controls.autoRotate = name === "orbit" && !REDUCED();
    const off = camera.position.clone().sub(controls.target), from = new THREE.Spherical().setFromVector3(off);
    const v = VIEWS[name];
    let dth = v.theta - from.theta; dth = Math.atan2(Math.sin(dth), Math.cos(dth)); // shortest path
    tween = { t: 0, from: { th: from.theta, ph: from.phi, r: from.radius, ty: controls.target.y }, to: { th: from.theta + dth, ph: v.phi, r: fitDistance(name), ty: v.ty } };
  }
  placeCamera(VIEWS.front.theta, VIEWS.front.phi, fitDistance("front"), VIEWS.front.ty);

  // --- Labels ---
  const ANCHORS = { face: [[0.075, 1.67, 0.04], P.HEAD, [0, 1.655, 0.01], 1], legs: [[-0.15, 0.3, 0.01], P.SHIN, [-0.1, 0.3, 0.005], -1],
    body: [[-0.15, 1.12, 0.03], P.TORSO, [0, 1.12, 0], -1], hands: [[0.32, 1.035, 0.3], P.HAND, [0.305, 1.035, 0.27], 1],
    posture: [[0, 1.5, -0.06], P.NECK, [0, 1.5, 0], -1] };
  const SIDE_X = { face: 1, legs: -1, body: -1, hands: 1, posture: 1 };
  let labels = [];
  function setLabels(list) {
    labels.forEach((l) => { l.box.remove(); l.dot.remove(); l.line.remove(); }); labels = [];
    (list || []).forEach((it) => {
      if (!ANCHORS[it.zone]) return;
      const color = STATUS_COLORS[it.status] || "#B9C7D6";
      const box = document.createElement("div"); box.className = `body3d-label status-${it.status || "none"}`; box.textContent = it.text || "";
      const dot = document.createElement("div"); dot.className = "body3d-dot"; dot.style.background = color;
      const line = document.createElement("div"); line.className = "body3d-line"; line.style.background = color;
      overlay.append(line, dot, box); labels.push({ zone: it.zone, box, dot, line });
    });
  }
  const pv = new THREE.Vector3();
  function updateLabels() {
    for (const l of labels) {
      const [p, pt, c] = ANCHORS[l.zone];
      deform(p[0], p[1], p[2], pt, c[0], c[1], c[2], 0, 0, 1, tmp);
      pv.set(tmp[0], tmp[1], tmp[2]).project(camera);
      const vis = pv.z < 1 && pv.z > -1;
      const ax = (pv.x * 0.5 + 0.5) * W, ay = (-pv.y * 0.5 + 0.5) * H;
      const side = Math.abs(ax - W / 2) < 24 ? SIDE_X[l.zone] : Math.sign(ax - W / 2), bw = l.box.offsetWidth, bh = l.box.offsetHeight;
      let bx = ax + side * Math.min(90, W * 0.12) - (side < 0 ? bw : 0), by = ay - bh / 2 - 12;
      bx = Math.max(4, Math.min(W - bw - 4, bx)); by = Math.max(4, Math.min(H - bh - 4, by));
      const ex = side > 0 ? bx : bx + bw, ey = by + bh / 2, len = Math.hypot(ex - ax, ey - ay);
      [l.box, l.dot, l.line].forEach((e) => (e.style.display = vis ? "" : "none"));
      l.dot.style.transform = `translate(${ax}px,${ay}px)`;
      l.box.style.transform = `translate(${bx}px,${by}px)`;
      l.line.style.width = `${len}px`;
      l.line.style.transform = `translate(${ax}px,${ay}px) rotate(${Math.atan2(ey - ay, ex - ax)}rad)`;
    }
  }

  // --- Sizing ---
  function resize() {
    W = container.clientWidth; H = container.clientHeight;
    if (!W || !H) return;
    renderer.setSize(W, H, false);
    camera.aspect = W / H; camera.updateProjectionMatrix();
    uniforms.uScale.value = canvas.height / (2 * half);
    if (!tween) { // keep direction, refit distance to the new aspect ratio
      const off = camera.position.clone().sub(controls.target).setLength(fitDistance(view));
      camera.position.copy(controls.target).add(off);
    }
  }
  const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => resize()) : null;
  if (ro) ro.observe(container); else window.addEventListener("resize", resize);
  resize();

  // --- Animation loop ---
  let raf = 0, last = performance.now(), scanning = false, scanT = 0, disposed = false;
  function frame(now) {
    raf = requestAnimationFrame(frame);
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    if (!W || !H) { resize(); if (!W || !H) return; }
    if (!REDUCED()) uniforms.uTime.value += dt;
    // Smooth parameter transition (about 0.5 s)
    const k = 1 - Math.exp(-dt / 0.15);
    for (const key of KEYS) { const d = tgt[key] - cur[key]; if (Math.abs(d) > 1e-4) { cur[key] += d * k; geomDirty = true; } else cur[key] = tgt[key]; }
    if (geomDirty) { rebuildPositions(); rebuildSkeleton(); geomDirty = false; }
    if (colorDirty) {
      let maxd = 0;
      for (let i = 0; i < col.length; i++) { const d = colT[i] - col[i]; col[i] += d * k; if (Math.abs(d) > maxd) maxd = Math.abs(d); }
      geom.attributes.aColor.needsUpdate = true; if (maxd < 0.002) colorDirty = false;
    }
    // Scan sweep: down 2.4 s, up 1.6 s
    if (scanning) {
      scanT = (scanT + dt) % 4.0;
      const down = scanT < 2.4, y = down ? 1.85 - (scanT / 2.4) * 1.85 : ((scanT - 2.4) / 1.6) * 1.85;
      uniforms.uScanY.value = y; uniforms.uScanDown.value = down ? 1 : 0; scanGroup.position.y = y;
    }
    // Camera
    if (tween) {
      tween.t = Math.min(1, tween.t + dt / 0.9);
      const e = tween.t < 0.5 ? 2 * tween.t * tween.t : 1 - Math.pow(-2 * tween.t + 2, 2) / 2, f = tween.from, t = tween.to;
      placeCamera(f.th + (t.th - f.th) * e, f.ph + (t.ph - f.ph) * e, f.r + (t.r - f.r) * e, f.ty + (t.ty - f.ty) * e);
      if (tween.t >= 1) tween = null;
    } else controls.update();
    renderer.render(scene, camera);
    updateLabels();
  }
  raf = requestAnimationFrame(frame);

  return {
    setParams(p = {}) {
      for (const key of KEYS) if (p[key] != null && isFinite(+p[key])) tgt[key] = +p[key];
      if (p.zones) zones = { ...p.zones };
      rebuildColorTargets();
    },
    setView,
    scan(on) { scanning = !!on; scanGroup.visible = scanning; uniforms.uScanOn.value = scanning ? 1 : 0; if (scanning) scanT = 0; },
    setLabels,
    setSkeleton,
    resize,
    dispose() {
      if (disposed) return; disposed = true;
      cancelAnimationFrame(raf); if (ro) ro.disconnect(); else window.removeEventListener("resize", resize);
      controls.dispose();
      scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
      renderer.dispose(); canvas.remove(); overlay.remove();
    },
  };
}
