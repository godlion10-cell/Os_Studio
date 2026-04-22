// popup.js - AI Flow 4321 Controller (v2 - Scripting Injection)
const DASHBOARD_URL = 'http://127.0.0.1:5000';

// --- Tab 전환 ---
document.querySelectorAll('.tabs button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// --- 프롬프트 줄 수 카운터 ---
['image', 'video', 'audio'].forEach(type => {
  const ta = document.getElementById('prompt-' + type);
  const counter = document.getElementById('count-' + type);
  if (ta && counter) {
    ta.addEventListener('input', () => {
      counter.textContent = ta.value.split('\n').filter(l => l.trim()).length;
    });
  }
});

// --- 로그 ---
function addLog(msg, type = 'info') {
  const log = document.getElementById('log-area');
  const ts = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  log.innerHTML += `<div class="${type}">[${ts}] ${msg}</div>`;
  log.scrollTop = log.scrollHeight;
}

function setDot(id, on) {
  const dot = document.getElementById(id);
  if (dot) dot.className = 'status-dot ' + (on ? 'on' : 'off');
}

function getPrompts(type) {
  const ta = document.getElementById('prompt-' + type);
  return ta ? ta.value.split('\n').filter(l => l.trim()) : [];
}

// --- 대시보드에서 발주서 가져오기 ---
document.getElementById('btn-fetch').addEventListener('click', async () => {
  addLog('대시보드 연결 시도...', 'info');
  try {
    const histRes = await fetch(DASHBOARD_URL + '/api/history');
    const files = await histRes.json();
    if (!files.length) { addLog('저장된 기록 없음', 'err'); return; }

    const latestRes = await fetch(DASHBOARD_URL + '/api/history/' + files[0].fn);
    const data = await latestRes.json();

    let imgPrompts = [];
    ['hacker', 'healer'].forEach(mode => {
      const md = data[mode];
      if (!md) return;
      const pp = md.prompt_pack || [];
      imgPrompts = imgPrompts.concat(pp);
    });

    if (imgPrompts.length) {
      document.getElementById('prompt-image').value = imgPrompts.join('\n');
      document.getElementById('count-image').textContent = imgPrompts.length;
      addLog(`이미지 발주서 ${imgPrompts.length}건 로드`, 'ok');
      setDot('dot-dashboard', true);
    } else {
      addLog('프롬프트 없음. 대시보드에서 먼저 생성하세요.', 'err');
    }
  } catch (e) {
    addLog('대시보드 연결 실패: ' + e.message, 'err');
  }
});

// --- 현재 탭 공장 가동 (chrome.scripting 방식) ---
document.getElementById('btn-start').addEventListener('click', () => {
  const activeTab = document.querySelector('.tabs button.active').dataset.tab;
  const prompts = getPrompts(activeTab);
  if (!prompts.length) { addLog('프롬프트 비어있음', 'err'); return; }

  const nameMap = { image: 'Labs FX', video: 'Runway', audio: 'Suno' };
  addLog(`${nameMap[activeTab]} 공장 가동: ${prompts.length}건`, 'ok');

  chrome.runtime.sendMessage({
    type: 'START_FACTORY',
    platform: activeTab,
    prompts: prompts
  }, (res) => {
    if (res && res.tabId) {
      addLog(`탭 열림 (ID: ${res.tabId}), 주입 대기 중...`, 'info');
      const dotMap = { image: 'dot-imagen', video: 'dot-runway', audio: 'dot-suno' };
      setDot(dotMap[activeTab], true);
    }
  });
});

// --- 전 공장 동시 가동 ---
document.getElementById('btn-start-all').addEventListener('click', () => {
  const imagePrompts = getPrompts('image');
  const videoPrompts = getPrompts('video');
  const audioPrompts = getPrompts('audio');
  const total = imagePrompts.length + videoPrompts.length + audioPrompts.length;

  if (!total) { addLog('모든 발주서 비어있음', 'err'); return; }
  addLog(`🚀 전 공장 가동: 총 ${total}건`, 'ok');

  chrome.runtime.sendMessage({
    type: 'START_ALL_FACTORIES',
    imagePrompts, videoPrompts, audioPrompts
  }, (res) => {
    if (imagePrompts.length) { addLog(`Imagen: ${imagePrompts.length}장`, 'info'); setDot('dot-imagen', true); }
    if (videoPrompts.length) { addLog(`Runway: ${videoPrompts.length}편`, 'info'); setDot('dot-runway', true); }
    if (audioPrompts.length) { addLog(`Suno: ${audioPrompts.length}곡`, 'info'); setDot('dot-suno', true); }
  });
});

// --- 초기화 ---
(async () => {
  try {
    const r = await fetch(DASHBOARD_URL + '/api/history', { signal: AbortSignal.timeout(3000) });
    if (r.ok) { setDot('dot-dashboard', true); addLog('대시보드 연결 OK', 'ok'); }
  } catch (e) {
    addLog('대시보드 미연결', 'err');
  }
})();
