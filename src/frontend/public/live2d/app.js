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

    // 表情插值（线性逼近）
    for (const p of EXPR_PARAMS) {
      exprCurrent[p] += (exprTarget[p] - exprCurrent[p]) * 0.12;
      core.setParameterValueById(p, exprCurrent[p]);
    }
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
let playSeq = 0;               // 播放序列号，防止快速连续调用导致竞态
let audioCtx = null;           // 惰性创建的 AudioContext
let sourceNodeCreated = false; // 防止对同一 media element 重复 createMediaElementSource
let analyser = null;
let analyserData = null;       // Uint8Array，时域数据

// 辅助：通知父页面播放状态
function notifySpeakState(playing) {
  window.parent.postMessage({ type: 'live2d-speak-state', playing }, window.location.origin);
}

// 停止当前口型循环并归零口型
function stopLipSync() {
  if (lipSyncId) {
    cancelAnimationFrame(lipSyncId);
    lipSyncId = null;
  }
  if (live2dModel) {
    live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', 0);
  }
}

function playAudio(path) {
  if (!path) return;

  const seq = ++playSeq;
  // 新播放前：先通知上一段结束，并清理
  notifySpeakState(false);
  stopLipSync();

  audioPlayer.src = path;

  // 惰性初始化 Web Audio 分析管线（只做一次）
  let useAnalyser = false;
  if (!audioCtx) {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      if (ctx.state === 'suspended') ctx.resume();
      audioCtx = ctx;
    } catch (err) {
      // AudioContext 不可用，走回退
    }
  }
  if (audioCtx && !sourceNodeCreated) {
    try {
      const src = audioCtx.createMediaElementSource(audioPlayer);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      src.connect(analyser);
      analyser.connect(audioCtx.destination);
      analyserData = new Uint8Array(analyser.fftSize);
      sourceNodeCreated = true;
      useAnalyser = true;
    } catch (err) {
      // 重复创建或其他异常，走回退
    }
  } else if (audioCtx && sourceNodeCreated) {
    useAnalyser = true;
  }

  // 确保 AudioContext 不处于 suspended
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {});
  }

  // 播放（catch 防止 unhandled rejection）
  audioPlayer.play().then(() => {
    if (seq !== playSeq) return;
    // 播放开始时通知父页面
    notifySpeakState(true);
  }).catch(() => {
    if (seq !== playSeq) return;
    notifySpeakState(false);
  });

  // 判断走哪条口型路径：analyser 可用 → 真实振幅；否则 → 正弦波回退
  if (useAnalyser && analyser && analyserData) {
    // Web Audio 真实振幅口型
    const GAIN = 6; // RMS 增益，让正常说话幅度可见
    let prevMouth = 0;
    function animateLipAnalyser() {
      if (audioPlayer.paused || audioPlayer.ended) {
        if (seq !== playSeq) return;
        stopLipSync();
        notifySpeakState(false);
        return;
      }
      if (live2dModel) {
        analyser.getByteTimeDomainData(analyserData);
        let sumSq = 0;
        for (let i = 0; i < analyserData.length; i++) {
          const v = (analyserData[i] - 128) / 128;
          sumSq += v * v;
        }
        const rms = Math.sqrt(sumSq / analyserData.length);
        let target = rms * GAIN;
        if (target > 1) target = 1;
        if (target < 0) target = 0;
        // 平滑：避免口型跳动
        const smooth = prevMouth + (target - prevMouth) * 0.35;
        prevMouth = smooth;
        live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', smooth);
      }
      lipSyncId = requestAnimationFrame(animateLipAnalyser);
    }
    animateLipAnalyser();
  } else {
    // 正弦波回退口型（保持原有逻辑）
    const startTime = performance.now();
    function animateLipFallback() {
      if (audioPlayer.paused || audioPlayer.ended) {
        if (seq !== playSeq) return;
        stopLipSync();
        notifySpeakState(false);
        return;
      }
      if (live2dModel) {
        const t = (performance.now() - startTime) / 1000;
        const v = Math.abs(0.3 * Math.sin(t * 8.5) + 0.2 * Math.sin(t * 12.3) + 0.15 * Math.sin(t * 5.7));
        live2dModel.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', Math.min(v, 1));
      }
      lipSyncId = requestAnimationFrame(animateLipFallback);
    }
    animateLipFallback();
  }

  // 播放结束
  audioPlayer.onended = () => {
    if (seq !== playSeq) return;
    stopLipSync();
    notifySpeakState(false);
  };

  // 播放出错
  audioPlayer.onerror = () => {
    if (seq !== playSeq) return;
    stopLipSync();
    notifySpeakState(false);
  };
}

// === 表情引擎 ===
// 可用的表情参数（不与自动眨眼/idle 冲突）
const EXPR_PARAMS = [
  'ParamEyeLSmile', 'ParamEyeRSmile', 'ParamMouthForm', 'ParamCheek',
  'ParamBrowLY', 'ParamBrowRY', 'ParamBrowLAngle', 'ParamBrowRAngle',
  'ParamBrowLForm', 'ParamBrowRForm'
];

// 表情映射表（未列出的参数视为 0）
const EXPR_MAP = {
  happy:     { EyeLSmile: 1, EyeRSmile: 1, MouthForm: 1,  Cheek: 0.6, BrowLY: 0.3,  BrowRY: 0.3 },
  excited:   { EyeLSmile: 1, EyeRSmile: 1, MouthForm: 1,  Cheek: 1,   BrowLY: 0.6,  BrowRY: 0.6 },
  sad:       { MouthForm: -0.8, BrowLY: -0.4, BrowRY: -0.4, BrowLAngle: -0.5, BrowRAngle: -0.5, BrowLForm: -0.6, BrowRForm: -0.6 },
  angry:     { MouthForm: -1, BrowLY: -0.6, BrowRY: -0.6, BrowLAngle: 0.5, BrowRAngle: 0.5, BrowLForm: -0.8, BrowRForm: -0.8, Cheek: 0.3 },
  surprised: { BrowLY: 0.9, BrowRY: 0.9, MouthForm: 0.2 },
  shy:       { Cheek: 1, MouthForm: 0.3, EyeLSmile: 0.5, EyeRSmile: 0.5, BrowLY: -0.2, BrowRY: -0.2 },
};

// 当前和目标表情值
const exprCurrent = {};
const exprTarget = {};
// 初始化全为 0
for (const p of EXPR_PARAMS) {
  exprCurrent[p] = 0;
  exprTarget[p] = 0;
}

// 设置目标表情
function applyExpression(emotion) {
  const map = (emotion && EXPR_MAP[emotion]) ? EXPR_MAP[emotion] : {};
  for (const p of EXPR_PARAMS) {
    exprTarget[p] = map[p] || 0;
  }
}

// === 锁定控制（来自父页面 postMessage）===
let interactionLocked = false

window.addEventListener('message', (e) => {
  if (!e.data || typeof e.data !== 'object') return;
  if (e.data.type === 'set-lock') {
    interactionLocked = e.data.locked;
  } else if (e.data.type === 'speak') {
    // 播放音频并驱动口型，可选表情
    if (e.data.emotion) applyExpression(e.data.emotion);
    playAudio(e.data.url);
  } else if (e.data.type === 'expression') {
    applyExpression(e.data.emotion);
  }
});

// === 拖拽 + 缩放 ===
function setupInteraction() {
  const canvas = document.getElementById('live2d-canvas');
  let dragging = false, lastX = 0, lastY = 0;
  canvas.addEventListener('mousedown', e => { if (interactionLocked) return; dragging = true; lastX = e.clientX; lastY = e.clientY; });
  canvas.addEventListener('mousemove', e => {
    if (!dragging) return;
    moveModel(e.clientX - lastX, e.clientY - lastY);
    lastX = e.clientX; lastY = e.clientY;
  });
  canvas.addEventListener('mouseup', () => { dragging = false; });
  canvas.addEventListener('mouseleave', () => { dragging = false; });
  canvas.addEventListener('wheel', e => {
    if (interactionLocked) return;
    e.preventDefault();
    currentScale = Math.max(0.3, Math.min(3, currentScale - e.deltaY * 0.001));
    setModelScale(currentScale);
  }, { passive: false });
}

// === 启动 ===
initLive2D().then(() => { setupInteraction(); restoreModelState(); }).catch(e => console.error('Live2D init failed:', e));
