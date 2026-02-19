const chatBox = document.getElementById('chat-box');
const mouth = document.getElementById('mouth');
const emotionInd = document.getElementById('emotion-indicator');
const audioPlayer = document.getElementById('audio-player');
let currentAiMsg = null;

const EMOTION_MAP = {
  happy: '😊', sad: '😢', angry: '😠', surprised: '😲',
  neutral: '😐', shy: '😳', excited: '🤩'
};

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

function playAudio(path) {
  if (!path) return;
  audioPlayer.src = path;
  audioPlayer.play();
  mouth.classList.add('speaking');
  audioPlayer.onended = () => mouth.classList.remove('speaking');
}

// 初始化
setEmotion('neutral');
