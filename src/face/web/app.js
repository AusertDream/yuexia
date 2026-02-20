const chatBox = document.getElementById('chat-box');
const emotionInd = document.getElementById('emotion-indicator');
const audioPlayer = document.getElementById('audio-player');
let currentAiMsg = null;
let live2dModel = null;
let pixiApp = null;
let baseScale = 1;

const EMOTION_MAP = {
  happy: '😊', sad: '😢', angry: '😠', surprised: '😲',
  neutral: '😐', shy: '😳', excited: '🤩'
};

// === Live2D 初始化 ===
async function initLive2D() {
  const canvas = document.getElementById('live2d-canvas');
  const w = canvas.clientWidth, h = canvas.clientHeight;
  pixiApp = new PIXI.Application({
    view: canvas, width: w, height: h,
    backgroundAlpha: 0, autoStart: true,
  });

  const model = await PIXI.live2d.Live2DModel.from(
    '../../../assets/live2d/yuexia/delisha.model3.json'
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
  const w = pixiApp.renderer.width, h = pixiApp.renderer.height;
  live2dModel.scale.set(baseScale * s);
  live2dModel.x = (w - live2dModel.width * baseScale * s) / 2;
  live2dModel.y = (h - live2dModel.height * baseScale * s) / 2;
}

function resetModel() { fitModel(); }

function moveModel(dx, dy) {
  if (!live2dModel) return;
  live2dModel.x += dx;
  live2dModel.y += dy;
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

function setEmotion(emotion) {
  emotionInd.textContent = EMOTION_MAP[emotion] || EMOTION_MAP.neutral;
}

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

// === 启动 ===
setEmotion('neutral');
initLive2D().catch(e => console.error('Live2D init failed:', e));
