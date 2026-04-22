// background.js - AI Flow 4321 Service Worker (v3 - Smart Button Detection)
const FACTORY_MAP = {
  image: {
    url: 'https://labs.google/fx/tools/image-fx',
    name: 'Google Labs FX',
    selectors: {
      input: ["rich-textarea textarea","textarea[placeholder*='Describe']","textarea[aria-label*='prompt']","textarea","[contenteditable='true']","rich-textarea"],
      // 구글 최신 UI는 CSS 셀렉터만으로 찾기 어려움 → smartFind 사용
      submit: ["__SMART_FIND__"],
      keywords: ["만들기","create","generate"]
    },
    cooldown: 20000
  },
  video: {
    url: 'https://lumalabs.ai/dream-machine',
    name: 'Luma 영상 공장',
    selectors: {
      // 사장님이 완벽하게 찾아낸 입력창 과녁!
      input: ["textarea[placeholder*='Describe what you want']"],
      // 💡 버튼 과녁은 이제 몰라도 됩니다! 그냥 냅두세요. 알아서 엔터 칩니다.
      submit: [],
      keywords: ["generate","create"]
    },
    cooldown: 60000
  },
  audio: {
    url: 'https://suno.com/create',
    name: 'Suno Music',
    selectors: {
      input: ["textarea[name='prompt']","textarea[placeholder*='song']","textarea[placeholder*='describe']","textarea","input[type='text']","[contenteditable='true']"],
      submit: ["button.create-btn","button[aria-label*='Create']","button[aria-label*='Generate']","button[type='submit']"],
      keywords: ["create","만들기"]
    },
    cooldown: 30000
  },
  tts: {
    url: 'https://elevenlabs.io',
    name: 'ElevenLabs Voice',
    selectors: {
      input: ["textarea[name='text']","textarea[placeholder*='Enter']","textarea","[contenteditable='true']"],
      submit: ["button[type='submit']","button[aria-label*='Generate']","button[aria-label*='Convert']"],
      keywords: ["generate","convert"]
    },
    cooldown: 15000
  }
};

chrome.runtime.onInstalled.addListener(() => {
  console.log('[AI Flow 4321] v3 installed');
  chrome.storage.local.clear();
});

// --- 핵심: chrome.scripting으로 프롬프트 주입 + 스마트 버튼 탐색 ---
async function injectPromptAndClick(tabId, promptText, selectors) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: (text, sels) => {
        // ── 1단계: 입력창 찾기 (폴백 체인) ──
        let inputEl = null;
        for (const sel of sels.input) {
          try { inputEl = document.querySelector(sel); } catch(e) {}
          if (inputEl) break;
        }
        if (!inputEl) {
          console.log('[AI Flow] 입력창 없음');
          return;
        }

        // ── 2단계: React/Vue 호환 프롬프트 입력 ──
        inputEl.focus();
        if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
          const proto = inputEl.tagName === 'TEXTAREA' 
            ? window.HTMLTextAreaElement.prototype 
            : window.HTMLInputElement.prototype;
          const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
          if (nativeSetter) nativeSetter.call(inputEl, text);
          else inputEl.value = text;
          inputEl.dispatchEvent(new Event('input', { bubbles: true }));
          inputEl.dispatchEvent(new Event('change', { bubbles: true }));
        } else {
          // contenteditable / rich-textarea
          inputEl.textContent = '';
          inputEl.textContent = text;
          inputEl.dispatchEvent(new InputEvent('input', { bubbles: true, data: text }));
        }

        // ── 3단계: 1.5초 후 스마트 버튼 탐색 + 클릭 ──
        setTimeout(() => {
          let sendBtn = null;

          // 방법 A: CSS 셀렉터로 직접 탐색
          if (sels.submit[0] !== '__SMART_FIND__') {
            for (const sel of sels.submit) {
              try { sendBtn = document.querySelector(sel); } catch(e) {}
              if (sendBtn && !sendBtn.disabled) break;
              sendBtn = null;
            }
          }

          // 방법 B: 전체 버튼 스캔 (구글 최신 UI 대응)
          if (!sendBtn) {
            const allBtns = Array.from(document.querySelectorAll('button, [role="button"]'));
            const keywords = sels.keywords || ['create','generate','만들기'];
            
            for (const b of allBtns) {
              if (b.disabled) continue;
              const txt = (b.innerText || '').toLowerCase();
              const ariaLabel = (b.getAttribute('aria-label') || '').toLowerCase();
              
              for (const kw of keywords) {
                if (txt.includes(kw) || ariaLabel.includes(kw)) {
                  sendBtn = b;
                  break;
                }
              }
              if (sendBtn) break;
            }
          }

          // 방법 C: Enter 키 폴백
          if (sendBtn) {
            sendBtn.click();
            console.log('[AI Flow] 버튼 클릭:', sendBtn.innerText || sendBtn.getAttribute('aria-label'));
          } else {
            console.log('[AI Flow] 버튼 못 찾음 → Enter 키 전송');
            const target = document.querySelector('rich-textarea') 
              || document.querySelector('[contenteditable="true"]') 
              || document.querySelector('textarea');
            if (target) {
              target.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
              target.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
            }
          }
        }, 1500);

        // 알림
        const n = document.createElement('div');
        n.style.cssText = 'position:fixed;top:20px;right:20px;background:#00c73c;color:#fff;padding:16px 24px;border-radius:10px;font-weight:bold;z-index:99999;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.3);font-family:sans-serif';
        n.textContent = '⚡ AI Flow: 프롬프트 주입 완료';
        document.body.appendChild(n);
        setTimeout(() => n.remove(), 4000);
      },
      args: [promptText, selectors]
    });
    return true;
  } catch (e) {
    console.error('[AI Flow] Injection error:', e);
    return false;
  }
}

// --- 메시지 핸들러 ---
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  if (msg.type === 'START_FACTORY') {
    const factory = FACTORY_MAP[msg.platform];
    if (!factory) { sendResponse({ error: 'unknown platform' }); return; }
    chrome.tabs.create({ url: factory.url }, (tab) => {
      chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
        if (tabId === tab.id && info.status === 'complete') {
          chrome.tabs.onUpdated.removeListener(listener);
          setTimeout(async () => {
            await processQueue(tab.id, msg.prompts || [], factory, 0);
          }, 3000);
        }
      });
      sendResponse({ tabId: tab.id, status: 'launched' });
    });
    return true;
  }

  if (msg.type === 'START_ALL_FACTORIES') {
    const platforms = ['image', 'video', 'audio', 'tts'];
    let launched = 0;
    platforms.forEach(platform => {
      const prompts = msg[platform + 'Prompts'] || [];
      if (!prompts.length) return;
      const factory = FACTORY_MAP[platform];
      chrome.tabs.create({ url: factory.url }, (tab) => {
        chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
          if (tabId === tab.id && info.status === 'complete') {
            chrome.tabs.onUpdated.removeListener(listener);
            setTimeout(async () => {
              await processQueue(tab.id, prompts, factory, 0);
            }, 3000);
          }
        });
        launched++;
      });
    });
    sendResponse({ status: 'all_launched', count: launched });
    return true;
  }

  // 나머지 프롬프트 큐 처리 (popup에서 호출)
  if (msg.type === 'QUEUE_REMAINING') {
    const factory = FACTORY_MAP[msg.domain] || Object.values(FACTORY_MAP).find(f => f.name === msg.config?.name);
    if (factory && msg.tabId && msg.prompts) {
      processQueue(msg.tabId, msg.prompts, factory, 0);
    }
    sendResponse({ status: 'queued' });
    return true;
  }
});

// --- 순차 큐 처리 ---
async function processQueue(tabId, prompts, factory, index) {
  if (index >= prompts.length) {
    console.log(`[AI Flow] ${factory.name}: 전체 완료 (${prompts.length}건)`);
    try {
      await chrome.scripting.executeScript({
        target: { tabId },
        func: (total, name) => {
          const n = document.createElement('div');
          n.style.cssText = 'position:fixed;top:20px;right:20px;background:#00c73c;color:#fff;padding:20px 30px;border-radius:12px;font-weight:bold;z-index:99999;font-size:16px;box-shadow:0 4px 12px rgba(0,0,0,0.3);font-family:sans-serif';
          n.textContent = `🎉 AI Flow: ${name} ${total}건 전체 완료!`;
          document.body.appendChild(n);
          setTimeout(() => n.remove(), 8000);
        },
        args: [prompts.length, factory.name]
      });
    } catch (e) {}
    return;
  }

  console.log(`[AI Flow] ${factory.name}: ${index + 1}/${prompts.length}`);

  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: (idx, total, name) => {
        const old = document.getElementById('aiflow-progress');
        if (old) old.remove();
        const n = document.createElement('div');
        n.id = 'aiflow-progress';
        n.style.cssText = 'position:fixed;top:20px;right:20px;background:#3b82f6;color:#fff;padding:16px 24px;border-radius:10px;font-weight:bold;z-index:99999;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.3);font-family:sans-serif';
        n.textContent = `⚡ ${name}: ${idx + 1}/${total} 처리 중...`;
        document.body.appendChild(n);
        setTimeout(() => n.remove(), 5000);
      },
      args: [index, prompts.length, factory.name]
    });
  } catch (e) {}

  const success = await injectPromptAndClick(tabId, prompts[index], factory.selectors);

  if (success && index + 1 < prompts.length) {
    setTimeout(() => processQueue(tabId, prompts, factory, index + 1), factory.cooldown);
  }
}
