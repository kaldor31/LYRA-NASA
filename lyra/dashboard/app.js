// LYRA — панель зеркала. Получает события по WebSocket от lyra/server.py.
const $ = (id) => document.getElementById(id);
const STATUS_ICON = { green: "✓", yellow: "↻", red: "!", retry: "?" };
const STATUS_WORD = { green: "норма", yellow: "повторить", red: "отклонение", retry: "переизмерить" };
const GROUPS = { face: "Лицо", body: "Осанка", palm: "Ладонь" };
const PHASE_SUB = { face: "Сканирование лица и осанки", palm: "Пульс, SpO₂, температура", grip: "Сила хвата" };

let state = null;
let phase = "idle";
let lastFrame = null;
let resultTimer = null;

// ---------- соединение ----------
function connect() {
  const ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
  ws.onmessage = (e) => handle(JSON.parse(e.data));
  ws.onclose = () => setTimeout(connect, 1500);
}

function handle(m) {
  switch (m.type) {
    case "state": return onState(m);
    case "phase": return onPhase(m);
    case "frame": lastFrame = m; setProgress(m.progress); return;
    case "palm": return onPalm(m);
    case "result": return onResult(m);
    case "calibrated": toast(m.text); return setIdle();
    case "error": toast(m.text); return setIdle();
  }
}

function onState(s) {
  state = s;
  $("day").textContent = s.day <= 0 ? "до полёта" : `День ${s.day} полёта`;
  const badges = [];
  if (s.camera === "sim") badges.push("камера: симуляция");
  if (s.palm === "sim") badges.push("ладонь: симуляция");
  if (s.calibrated) badges.push("откалибровано");
  $("modes").innerHTML = badges.map((b) => `<span class="badge">${b}</span>`).join("");
  if (!s.busy && phase !== "result") setIdle();
}

function onPhase(m) {
  phase = m.phase;
  clearTimeout(resultTimer);
  $("overall").classList.add("hidden");
  $("metrics").classList.add("hidden");
  $("trends").classList.add("hidden");
  $("phase").classList.remove("hidden");
  $("phase-text").textContent = m.text;
  $("phase-sub").textContent = PHASE_SUB[m.phase] || "";
  $("live").innerHTML = "";
  setProgress(0);
  if (m.phase !== "face") lastFrame = null;
}

function onPalm(m) {
  setProgress(m.progress);
  if (phase === "palm") {
    const parts = [];
    parts.push(m.finger ? "палец на датчике" : "положите палец на датчик");
    if (m.hr) parts.push(`пульс ${m.hr}`);
    if (m.temp != null) parts.push(`${Number(m.temp).toFixed(1)} °C`);
    $("live").textContent = parts.join(" · ");
  } else if (phase === "grip") {
    const peak = m.peak || 0;
    $("live").innerHTML = `${peak.toFixed(1).replace(".", ",")} кг<div class="grip-meter"><div style="width:${Math.min(100, peak / 60 * 100)}%"></div></div>`;
  }
}

function setIdle() {
  phase = "idle";
  lastFrame = null;
  $("phase").classList.remove("hidden");
  $("phase-text").textContent = "Подойдите к зеркалу";
  $("phase-sub").textContent = state && state.calibrated === false && state.camera === "real"
    ? "C — калибровка (первый запуск), пробел — проверка"
    : "Пробел — начать проверку";
  $("live").textContent = "";
  setProgress(0);
}

function setProgress(p) { $("bar-fill").style.width = `${Math.round((p || 0) * 100)}%`; }

// ---------- результат ----------
const fmt = (v, unit, d) => (v == null ? "—" : `${v.toFixed(d)}`.replace(".", ",")) + (unit ? `<small>${unit}</small>` : "");
const DECIMALS = { face_puffiness: 3, head_forward: 2, shoulder_tilt: 1, perclos: 1, skin_temp: 1, grip_strength: 1 };

function onResult(r) {
  phase = "result";
  lastFrame = null;
  $("phase").classList.add("hidden");
  const o = r.overall;
  $("ov-icon").className = `icon ${o.status}`;
  $("ov-icon").textContent = STATUS_ICON[o.status];
  $("ov-title").textContent = o.title;
  $("ov-summary").textContent = o.summary;
  $("ov-sim").textContent = r.simulated ? "История до этого дня смоделирована (демо-данные)." : "";
  $("overall").classList.remove("hidden");

  const box = $("metrics");
  box.innerHTML = "";
  for (const g of Object.keys(GROUPS)) {
    const items = r.metrics.filter((m) => m.group === g);
    if (!items.length) continue;
    box.insertAdjacentHTML("beforeend", `<div class="group-title">${GROUPS[g]}</div>`);
    for (const m of items) {
      const el = document.createElement("div");
      el.className = `metric ${m.status === "green" ? "ok" : ""}`;
      el.innerHTML = `
        <span class="dot ${m.status}" title="${STATUS_WORD[m.status]}">${STATUS_ICON[m.status]}</span>
        <span class="name">${m.name}</span>
        <span class="val">${fmt(m.value, m.unit, DECIMALS[m.key] ?? 0)}</span>
        <svg class="spark" viewBox="0 0 300 28" preserveAspectRatio="none" aria-label="тренд ${m.name}"></svg>
        <span class="text">${m.text}</span>`;
      box.appendChild(el);
      sparkline(el.querySelector(".spark"), m.series, m.status);
    }
  }
  box.classList.remove("hidden");
  resultTimer = setTimeout(() => { if (phase === "result") { box.classList.add("hidden"); $("overall").classList.add("hidden"); setIdle(); } }, 90000);
}

// Мини-тренд: одна серия, последняя точка — цвет статуса (статус также подписан значком).
function sparkline(svg, series, status) {
  if (!series || series.length < 2) return;
  const xs = series.map((p) => p[0]), ys = series.map((p) => p[1]);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  let [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  if (y1 - y0 < 1e-9) { y0 -= 1; y1 += 1; }
  const X = (x) => 4 + (x - x0) / (x1 - x0 || 1) * 284, Y = (y) => 24 - (y - y0) / (y1 - y0) * 20;
  const pts = series.map(([x, y]) => `${X(x).toFixed(1)},${Y(y).toFixed(1)}`).join(" ");
  const [lx, ly] = series[series.length - 1];
  const color = getComputedStyle(document.documentElement).getPropertyValue(
    { green: "--good", yellow: "--warn", red: "--crit", retry: "--retry" }[status]);
  svg.innerHTML = `<polyline points="${pts}" fill="none" stroke="var(--accent)" stroke-width="1.5" vector-effect="non-scaling-stroke" opacity="0.7"/>
    <circle cx="${X(lx)}" cy="${Y(ly)}" r="4" fill="${color}" stroke="#000" stroke-width="2" vector-effect="non-scaling-stroke"/>`;
}

// ---------- тренды ----------
const TREND_KEYS = ["face_puffiness", "grip_strength", "hr_palm", "perclos"];

async function showTrends() {
  const t = await (await fetch("/api/trends")).json();
  const grid = $("trend-grid");
  grid.innerHTML = "";
  $("trends").classList.remove("hidden"); // сначала показать — иначе ширина графиков = 0
  for (const k of TREND_KEYS) {
    const d = t[k];
    const card = document.createElement("div");
    card.className = "trend";
    const last = d.series.length ? d.series[d.series.length - 1][1] : null;
    const pct = d.preflight && last != null ? (100 * (last - d.preflight) / d.preflight) : null;
    card.innerHTML = `<h3>${d.name}${d.unit ? `, ${d.unit}` : ""}</h3>
      <div class="sub">${pct == null ? "" : `с начала полёта: ${pct > 0 ? "+" : "−"}${Math.abs(pct).toFixed(1).replace(".", ",")} %`}</div>
      <svg></svg>`;
    grid.appendChild(card);
    trendChart(card.querySelector("svg"), d);
  }
  $("trends").classList.remove("hidden");
}

function trendChart(svg, d) {
  const W = svg.clientWidth || 400, H = 180, L = 44, R = 10, T = 10, B = 24;
  const s = d.series;
  if (s.length < 2) { svg.innerHTML = ""; return; }
  const xs = s.map((p) => p[0]), ys = s.map((p) => p[1]).concat(d.preflight ?? []);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  let [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const pad = (y1 - y0) * 0.15 || 1; y0 -= pad; y1 += pad;
  const X = (x) => L + (x - x0) / (x1 - x0) * (W - L - R);
  const Y = (y) => T + (1 - (y - y0) / (y1 - y0)) * (H - T - B);
  const dec = Math.abs(y1 - y0) < 1 ? 2 : Math.abs(y1 - y0) < 10 ? 1 : 0;
  const ticks = [y0 + pad, (y0 + y1) / 2, y1 - pad];
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = `
    ${ticks.map((v) => `<line class="axis" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}" opacity="0.5"/>
      <text class="axis-label" x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v.toFixed(dec).replace(".", ",")}</text>`).join("")}
    ${x0 <= 0 ? `<line class="flight-start" x1="${X(0.5)}" x2="${X(0.5)}" y1="${T}" y2="${H - B}"/>
      <text class="axis-label" x="${X(0.5) + 4}" y="${T + 10}">старт</text>` : ""}
    ${d.preflight != null ? `<line class="preflight" x1="${L}" x2="${W - R}" y1="${Y(d.preflight)}" y2="${Y(d.preflight)}"/>` : ""}
    <polyline class="series" points="${s.map(([x, y]) => `${X(x)},${Y(y)}`).join(" ")}"/>
    <text class="axis-label" x="${L}" y="${H - 6}">день ${x0}</text>
    <text class="axis-label" x="${W - R}" y="${H - 6}" text-anchor="end">день ${x1}</text>
    <line class="cross hidden" y1="${T}" y2="${H - B}"/>
    <circle class="hover-dot hidden" r="5"/>
    <rect x="${L}" y="0" width="${W - L - R}" height="${H}" fill="transparent"/>`;
  const cross = svg.querySelector(".cross"), dot = svg.querySelector(".hover-dot"), tip = $("tip");
  svg.querySelector("rect").addEventListener("mousemove", (e) => {
    const r = svg.getBoundingClientRect();
    const day = x0 + ((e.clientX - r.left) * (W / r.width) - L) / (W - L - R) * (x1 - x0);
    const p = s.reduce((a, b) => (Math.abs(b[0] - day) < Math.abs(a[0] - day) ? b : a));
    cross.setAttribute("x1", X(p[0])); cross.setAttribute("x2", X(p[0]));
    dot.setAttribute("cx", X(p[0])); dot.setAttribute("cy", Y(p[1]));
    cross.classList.remove("hidden"); dot.classList.remove("hidden");
    tip.innerHTML = `${p[0] <= 0 ? `до полёта, день ${p[0]}` : `день ${p[0]}`}: <b>${p[1].toFixed(dec + 1).replace(".", ",")}</b>${d.unit ? " " + d.unit : ""}`;
    tip.style.left = `${e.clientX + 14}px`; tip.style.top = `${e.clientY - 10}px`;
    tip.classList.remove("hidden");
  });
  svg.querySelector("rect").addEventListener("mouseleave", () => {
    cross.classList.add("hidden"); dot.classList.add("hidden"); tip.classList.add("hidden");
  });
}

// ---------- сетка лица (зеркальная) ----------
const canvas = $("mesh"), ctx = canvas.getContext("2d");
function resize() { canvas.width = innerWidth * devicePixelRatio; canvas.height = innerHeight * devicePixelRatio; }
addEventListener("resize", resize); resize();

function drawMesh() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (lastFrame && phase === "face") {
    // Кадр камеры 16:9 → вписываем в экран. x зеркалим, чтобы совпало с отражением.
    const W = canvas.width, H = canvas.height;
    const fw = Math.min(W, H * 16 / 9), fh = fw * 9 / 16, ox = (W - fw) / 2, oy = (H - fh) / 2;
    const P = ([x, y]) => [ox + (1 - x) * fw, oy + y * fh];
    ctx.fillStyle = "rgba(143,199,255,0.85)";
    for (const pt of lastFrame.face || []) {
      const [x, y] = P(pt);
      ctx.beginPath(); ctx.arc(x, y, 1.6 * devicePixelRatio, 0, Math.PI * 2); ctx.fill();
    }
    if (lastFrame.shoulders) {
      const [a, b] = lastFrame.shoulders.map(P);
      ctx.strokeStyle = "rgba(143,199,255,0.6)"; ctx.lineWidth = 2 * devicePixelRatio;
      ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b); ctx.stroke();
      for (const p of [a, b]) { ctx.beginPath(); ctx.arc(...p, 5 * devicePixelRatio, 0, Math.PI * 2); ctx.stroke(); }
    }
  }
  requestAnimationFrame(drawMesh);
}
requestAnimationFrame(drawMesh);

// ---------- управление ----------
async function act(a) {
  if (a === "measure" || a === "calibrate") {
    const r = await fetch(`/api/measure${a === "calibrate" ? "?calibrate=true" : ""}`, { method: "POST" });
    if (!r.ok) toast((await r.json()).detail);
  } else if (a === "trends") {
    $("trends").classList.contains("hidden") ? showTrends() : $("trends").classList.add("hidden");
  } else if (a === "cancel") {
    fetch("/api/cancel", { method: "POST" });
  } else if (a.startsWith("day")) {
    const r = await fetch(`/api/scenario/${a}`, { method: "POST" });
    if (!r.ok) return toast((await r.json()).detail);
    $("overall").classList.add("hidden"); $("metrics").classList.add("hidden"); $("trends").classList.add("hidden");
    setIdle();
    toast(`Сценарий: ${a === "day1" ? "день 1" : a === "day20" ? "день 20" : "день 40 (с отклонением)"}`);
  }
}

const KEYS = { " ": "measure", Enter: "measure", c: "calibrate", "с": "calibrate", t: "trends", "е": "trends",
  "1": "day1", "2": "day20", "3": "day40", Escape: "cancel" };
addEventListener("keydown", (e) => { const a = KEYS[e.key] || KEYS[e.key.toLowerCase()]; if (a) { e.preventDefault(); act(a); } });
document.querySelectorAll("footer button").forEach((b) => b.addEventListener("click", () => act(b.dataset.act)));

let toastTimer;
function toast(text) {
  const t = $("toast"); t.textContent = text; t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 4000);
}

setInterval(() => { $("clock").textContent = new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }); }, 1000);
connect();
