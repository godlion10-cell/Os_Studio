// popup.js - AI Flow 4321 (v3 - Tab Discovery + Direct Injection)
const DASHBOARD_URL = 'http://127.0.0.1:5000';

// --- 타겟 사이트 좌표 맵 ---
const factoryMap = {
  "labs.google": {
    name: "Imagen 3", promptId: "prompt-image",
    url: "https://labs.google/fx/tools/image-fx",
    inputCSS: ["textarea[placeholder*='Describe']","textarea[aria-label*='prompt']","textarea"],
    btnCSS: ["button[aria-label*='Generate']","button[aria-label*='Create']","button[data-testid*='generate']","button[type='submit']"]
  },
  "lumalabs.ai": {
    name: "Luma Video", promptId: "prompt-video",
    url: "https://lumalabs.ai/dream-machine",
    inputCSS: ["textarea[placeholder*='Type a prompt']","textarea[placeholder*='Describe']","textarea","[contenteditable='true']"],
    btnCSS: ["button[aria-label='Generate']","button[aria-label*='Create']","button[type='submit']"]
  },
  "suno.com": {
    name: "Suno Music", promptId: "prompt-audio",
    url: "https://suno.com/create",
    inputCSS: ["textarea[name='prompt']","textarea[placeholder*='song']","textarea[placeholder*='describe']","textarea"],
    btnCSS: ["button.create-btn","button[aria-label*='Create']","button[aria-label*='Generate']","button[type='submit']"]
  },
  "elevenlabs.io": {
    name: "ElevenLabs Voice", promptId: "prompt-tts",
    url: "https://elevenlabs.io",
    inputCSS: ["textarea[name='text']","textarea[placeholder*='Enter']","textarea","[contenteditable='true']"],
    btnCSS: ["button[type='submit']","button[aria-label*='Generate']","button[aria-label*='Convert']"]
  },
  "타겟사이트주소.com": { 
    name: "영상 공장", 
    promptId: "vid-prompt", 
    // 사장님이 방금 훔쳐온 '입력창 좌표'를 여기에 넣습니다!
    inputCSS: ["textarea[placeholder*='Describe what you want']"], 
    // ⚠️ 이제 이 '버튼 좌표' 하나만 더 찾으시면 끝납니다!
    btnCSS: ["여기에_버튼_좌표를_넣으세요"]
  }
};

// --- Tab 전환 ---
document.querySelectorAll('.tabs button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// --- 카운터 ---
['image','video','audio','tts'].forEach(type => {
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

function clearTab(id) {
  const ta = document.getElementById(id);
  if (ta) { ta.value = ''; ta.dispatchEvent(new Event('input')); }
  addLog('발주서 초기화 완료', 'info');
}

function setDot(id, on) {
  const dot = document.getElementById(id);
  if (dot) dot.className = 'status-dot ' + (on ? 'on' : 'off');
}

// --- 대시보드에서 발주서 가져오기 ---
document.getElementById('btn-fetch').addEventListener('click', async () => {
  addLog('대시보드 연결...', 'info');
  try {
    const histRes = await fetch(DASHBOARD_URL + '/api/history');
    const files = await histRes.json();
    if (!files.length) { addLog('기록 없음', 'err'); return; }
    const latestRes = await fetch(DASHBOARD_URL + '/api/history/' + files[0].fn);
    const data = await latestRes.json();
    let prompts = [];
    ['hacker', 'healer'].forEach(mode => {
      const md = data[mode];
      if (md) prompts = prompts.concat(md.prompt_pack || []);
    });
    if (prompts.length) {
      document.getElementById('prompt-image').value = prompts.join('\n');
      document.getElementById('count-image').textContent = prompts.length;
      addLog(`발주서 ${prompts.length}건 로드`, 'ok');
      setDot('dot-dashboard', true);
    } else { addLog('프롬프트 없음', 'err'); }
  } catch (e) { addLog('연결 실패: ' + e.message, 'err'); }
});

// --- 단일 공장 가동 (현재 탭) ---
document.getElementById('btn-start').addEventListener('click', async () => {
  const activeTab = document.querySelector('.tabs button.active').dataset.tab;
  const domainMap = { image: 'labs.google', video: 'lumalabs.ai', audio: 'suno.com', tts: 'elevenlabs.io' };
  const domain = domainMap[activeTab];
  const config = factoryMap[domain];
  const ta = document.getElementById(config.promptId);
  const lines = ta.value.split('\n').filter(l => l.trim());
  if (!lines.length) { addLog('발주서 비어있음', 'err'); return; }

  addLog(`${config.name} 가동: ${lines.length}건`, 'ok');
  await executeOnSite(domain, config, lines);
});

// --- 전 공장 동시 가동 (메가 팩토리) ---
document.getElementById('btn-start-all').addEventListener('click', async () => {
  addLog('⚠️ 전 공장 동시 가동 시작...', 'ok');
  const allTabs = await chrome.tabs.query({});
  let totalJobs = 0;

  for (const domain in factoryMap) {
    const config = factoryMap[domain];
    const ta = document.getElementById(config.promptId);
    const text = ta ? ta.value.trim() : '';
    if (!text) continue;

    const lines = text.split('\n').filter(l => l.trim());
    totalJobs += lines.length;

    // 이미 열린 탭 찾기
    const targetTab = allTabs.find(t => t.url && t.url.includes(domain));

    if (targetTab) {
      addLog(`🎯 [${config.name}] 탭 발견 (ID:${targetTab.id}), 침투 시작`, 'ok');
      await injectToTab(targetTab.id, lines[0], config);
      // 나머지는 큐로 순차 처리
      if (lines.length > 1) {
        chrome.runtime.sendMessage({
          type: 'QUEUE_REMAINING', tabId: targetTab.id,
          prompts: lines.slice(1), config, domain
        });
      }
    } else {
      addLog(`[${config.name}] 탭 없음 → 새 탭 열기`, 'info');
      chrome.tabs.create({ url: config.url }, (tab) => {
        const dotMap = { 'labs.google': 'dot-imagen', 'lumalabs.ai': 'dot-luma', 'suno.com': 'dot-suno', 'elevenlabs.io': 'dot-eleven' };
        setDot(dotMap[domain], true);
        chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
          if (tabId === tab.id && info.status === 'complete') {
            chrome.tabs.onUpdated.removeListener(listener);
            setTimeout(() => {
              injectToTab(tab.id, lines[0], config);
              if (lines.length > 1) {
                chrome.runtime.sendMessage({
                  type: 'QUEUE_REMAINING', tabId: tab.id,
                  prompts: lines.slice(1), config, domain
                });
              }
            }, 3000);
          }
        });
      });
    }
  }

  if (!totalJobs) addLog('❌ 모든 발주서 비어있음', 'err');
  else addLog(`🏁 총 ${totalJobs}건 지시 하달 완료`, 'ok');
});

// --- 스크립트 주입 ---
async function injectToTab(tabId, promptText, config) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      args: [promptText, { inputCSS: config.inputCSS, btnCSS: config.btnCSS, name: config.name }],
      func: (text, cfg) => {
        // 입력창 찾기 (폴백 체인)
        let inputEl = null;
        for (const sel of cfg.inputCSS) {
          inputEl = document.querySelector(sel);
          if (inputEl) break;
        }
        if (!inputEl) {
          console.error(`[Os Studio RPA] ${cfg.name}: 입력창 없음`);
          return;
        }

        // React/Vue 호환 네이티브 값 설정
        inputEl.focus();
        if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
          const proto = inputEl.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
          const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
          if (nativeSetter) nativeSetter.call(inputEl, text);
          else inputEl.value = text;
          inputEl.dispatchEvent(new Event('input', { bubbles: true }));
          inputEl.dispatchEvent(new Event('change', { bubbles: true }));
        } else {
          inputEl.textContent = text;
          inputEl.dispatchEvent(new InputEvent('input', { bubbles: true, data: text }));
        }

        // 1.5초 뒤 생성 버튼 클릭
        setTimeout(() => {
          let btnEl = null;
          for (const sel of cfg.btnCSS) {
            btnEl = document.querySelector(sel);
            if (btnEl && !btnEl.disabled) break;
          }
          if (btnEl) {
            btnEl.click();
            console.log(`[Os Studio RPA] ${cfg.name} 가동 완료`);
          }
        }, 1500);

        // 알림
        const n = document.createElement('div');
        n.style.cssText = 'position:fixed;top:20px;right:20px;background:#00c73c;color:#fff;padding:16px 24px;border-radius:10px;font-weight:bold;z-index:99999;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.3);font-family:sans-serif';
        n.textContent = `⚡ Os Studio: ${cfg.name} 발주서 입력 완료`;
        document.body.appendChild(n);
        setTimeout(() => n.remove(), 4000);
      }
    });
    addLog(`✅ [${config.name}] 주입 완료`, 'ok');
  } catch (e) {
    addLog(`❌ [${config.name}] 주입 실패: ${e.message}`, 'err');
  }
}

async function executeOnSite(domain, config, lines) {
  const tabs = await chrome.tabs.query({});
  const targetTab = tabs.find(t => t.url && t.url.includes(domain));
  if (targetTab) {
    await injectToTab(targetTab.id, lines[0], config);
  } else {
    chrome.tabs.create({ url: config.url }, (tab) => {
      chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
        if (tabId === tab.id && info.status === 'complete') {
          chrome.tabs.onUpdated.removeListener(listener);
          setTimeout(() => injectToTab(tab.id, lines[0], config), 3000);
        }
      });
    });
  }
}

// --- 초기화 ---
(async () => {
  try {
    const r = await fetch(DASHBOARD_URL + '/api/history', { signal: AbortSignal.timeout(3000) });
    if (r.ok) { setDot('dot-dashboard', true); addLog('대시보드 연결 OK', 'ok'); }
  } catch (e) { addLog('대시보드 미연결', 'err'); }
})();
