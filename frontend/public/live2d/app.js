const chatBox = document.getElementById('chat-box');
const audioPlayer = document.getElementById('audio-player');
let currentAiMsg = null;
let live2dModel = null;
let pixiApp = null;
let baseScale = 1;
let currentScale = 1;

// === Live2D 初始化 ===
async function initLive2D() {
  const canvas = document.getElementById('live2d-canvas');
  const w = canvas.clientWidth, h = canvas.clientHeight;
  pixiApp = new PIXI.Application({
    view: canvas, width: w, height: h,
    backgroundAlpha: 0, autoStart: true,
  });

  const model = await PIXI.live2d.Live2DModel.from(
    './model/delisha.model3.json'
  );
  live2dModel = model;
  fitModel();
  pixiApp.stage.addChild(model);

  // idle 动画
  let elapsed = 0;
  pixiApp.ticker.add((delta) => {
    if (!live2dModel) return;
    elapsed += delta;
    const t = elapsed / 60;
    const core = live2dModel.internalModel.coreModel;
    core.setParameterValueById('ParamBreath', 0.5 + 0.5 * Math.sin(t * 1.8));
    core.setParameterValueById('ParamAngleX', 5 * Math.sin(t * 1.05));
    core.setParameterValueById('ParamAngleY', 3 * Math.sin(t * 0.78));
    core.setParameterValueById('ParamAngleZ', 2 * Math.sin(t * 0.5));
    core.setParameterValueById('ParamBodyAngleX', 2.5 * Math.sin(t * 1.05 - 0.3));
    core.setParameterValueById('ParamBodyAngleZ', 1 * Math.sin(t * 0.5 - 0.2));
  });
}

function fitModel() {
  if (!live2dModel || !pixiApp) return;
  const w = pixiApp.renderer.width, h = pixiApp.renderer.height;
  baseScale = Math.min(w / live2dModel.width, h / live2dModel.height);
  live2dModel.scale.set(baseScale);
  live2dModel.x = (w - live2dModel.width * baseScale) / 2;
  live2dModel.y = (h - live2dModel.height * baseScale) / 2;
}

// === 控制函数（供 Python 端调用）===
function resizeCanvas(w, h) {
  if (!pixiApp) return;
  pixiApp.renderer.resize(w, h);
  fitModel();
}

function setModelScale(s) {
  if (!live2dModel || !pixiApp) return;
  const oldCx = live2dModel.x + live2dModel.width * live2dModel.scale.x / 2;
  const oldCy = live2dModel.y + live2dModel.height * live2dModel.scale.y / 2;
  live2dModel.scale.set(baseScale * s);
  live2dModel.x = oldCx - live2dModel.width * baseScale * s / 2;
  live2dModel.y = oldCy - live2dModel.height * baseScale * s / 2;
  saveModelState();
}

function resetModel() { fitModel(); }

function moveModel(dx, dy) {
  if (!live2dModel) return;
  live2dModel.x += dx;
  live2dModel.y += dy;
  saveModelState();
}

function saveModelState() {
  if (!live2dModel) return;
  localStorage.setItem('live2d_state', JSON.stringify({
    x: live2dModel.x, y: live2dModel.y, scale: currentScale
  }));
}

function restoreModelState() {
  const raw = localStorage.getItem('live2d_state');
  if (!raw || !live2dModel) return;
  try {
    const s = JSON.parse(raw);
    if (s.scale) { currentScale = s.scale; live2dModel.scale.set(baseScale * currentScale); }
    if (s.x != null) live2dModel.x = s.x;
    if (s.y != null) live2dModel.y = s.y;
  } catch(e) {}
}

function setBackground(color) {
  document.body.style.background = color || 'transparent';
}

// === 原有 API ===
function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = text;
  chatBox.appendChild(div);
  if (role === 'ai') currentAiMsg = div;
  chatBox.scrollTop = chatBox.scrollHeight;
}

function appendChunk(text) {
  if (!currentAiMsg) addMessage('ai', '');
  currentAiMsg.textContent += text;
  chatBox.scrollTop = chatBox.scrollHeight;
}

function endStream() { currentAiMsg = null; }

// === 音频播放 + 口型 ===
let lipSyncId = null;

function playAudio(path) {
  if (!path) return;
  audioPlayer.src = path;
  audioPlayer.play();
  if (lipSyncId) cancelAnimationFrame(lipSyncId);
  const startTime = performance.now();
  function animateLip() {
    if (audioPlayer.paused || audioPlayer.ended) {
      if (live2dModel) live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', 0);
      lipSyncId = null;
      return;
    }
    if (live2dModel) {
      const t = (performance.now() - startTime) / 1000;
      const v = Math.abs(0.3 * Math.sin(t * 8.5) + 0.2 * Math.sin(t * 12.3) + 0.15 * Math.sin(t * 5.7));
      live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', Math.min(v, 1));
    }
    lipSyncId = requestAnimationFrame(animateLip);
  }
  animateLip();
  audioPlayer.onended = () => {
    if (lipSyncId) { cancelAnimationFrame(lipSyncId); lipSyncId = null; }
    if (live2dModel) live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', 0);
  };
}

// === 拖拽 + 缩放 ===
function setupInteraction() {
  const canvas = document.getElementById('live2d-canvas');
  let dragging = false, lastX = 0, lastY = 0;
  canvas.addEventListener('mousedown', e => { dragging = true; lastX = e.clientX; lastY = e.clientY; });
  canvas.addEventListener('mousemove', e => {
    if (!dragging) return;
    moveModel(e.clientX - lastX, e.clientY - lastY);
    lastX = e.clientX; lastY = e.clientY;
  });
  canvas.addEventListener('mouseup', () => { dragging = false; });
  canvas.addEventListener('mouseleave', () => { dragging = false; });
  canvas.addEventListener('wheel', e => {
    e.preventDefault();
    currentScale = Math.max(0.3, Math.min(3, currentScale - e.deltaY * 0.001));
    setModelScale(currentScale);
  }, { passive: false });
}

// === 启动 ===
initLive2D().then(() => { setupInteraction(); restoreModelState(); }).catch(e => console.error('Live2D init failed:', e));
