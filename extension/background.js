// background.js - AI Flow 4321 Service Worker (v2 - Scripting Injection)
const FACTORY_MAP = {
  image: {
    url: 'https://labs.google/fx/tools/image-fx',
    name: 'Google Labs FX',
    selectors: {
      input: ["textarea[placeholder*='Describe']","textarea[aria-label*='prompt']","textarea","[contenteditable='true']"],
      submit: ["button.generate-btn","button[aria-label*='Generate']","button[aria-label*='Create']","button[data-testid*='generate']","button[type='submit']"]
    },
    cooldown: 20000
  },
  video: {
    url: 'https://app.runwayml.com',
    name: 'Runway ML',
    selectors: {
      input: ["div[contenteditable='true'].prompt-input","div[contenteditable='true']","textarea[placeholder*='Describe']","textarea"],
      submit: ["button[data-testid='generate-button']","button[aria-label*='Generate']","button[aria-label*='Create']","button[type='submit']"]
    },
    cooldown: 60000
  },
  audio: {
    url: 'https://suno.com/create',
    name: 'Suno',
    selectors: {
      input: ["textarea[name='prompt']","textarea[placeholder*='song']","textarea[placeholder*='describe']","textarea","input[type='text']","[contenteditable='true']"],
      submit: ["button.create-song","button[aria-label*='Create']","button[aria-label*='Generate']","button[data-testid*='create']","button[type='submit']"]
    },
    cooldown: 30000
  }
};

chrome.runtime.onInstalled.addListener(() => {
  console.log('[AI Flow 4321] v2 installed');
  chrome.storage.local.clear();
});

// --- 핵심: chrome.scripting으로 프롬프트 주입 + 버튼 클릭 ---
async function injectPromptAndClick(tabId, promptText, selectors) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: (text, sels) => {
        // 입력창 찾기 (폴백 체인)
        let inputEl = null;
        for (const sel of sels.input) {
          inputEl = document.querySelector(sel);
          if (inputEl) break;
        }
        if (!inputEl) {
          console.log('[AI Flow] 입력창 없음');
          return { success: false, error: 'input_not_found' };
        }

        // 입력
        inputEl.focus();
        if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
          // React/Vue 등 프레임워크 호환 입력
          const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement?.prototype || window.HTMLInputElement?.prototype, 'value'
          )?.set;
          if (nativeSetter) nativeSetter.call(inputEl, text);
          else inputEl.value = text;
          inputEl.dispatchEvent(new Event('input', { bubbles: true }));
          inputEl.dispatchEvent(new Event('change', { bubbles: true }));
        } else {
          // contenteditable
          inputEl.textContent = '';
          inputEl.textContent = text;
          inputEl.dispatchEvent(new InputEvent('input', { bubbles: true, data: text }));
        }

        // 제출 버튼 찾기 + 1초 후 클릭
        setTimeout(() => {
          let btnEl = null;
          for (const sel of sels.submit) {
            btnEl = document.querySelector(sel);
            if (btnEl) break;
          }
          if (btnEl && !btnEl.disabled) {
            btnEl.click();
            console.log('[AI Flow] 버튼 클릭 완료');
          }
        }, 1000);

        // 알림 표시
        const n = document.createElement('div');
        n.style.cssText = 'position:fixed;top:20px;right:20px;background:#00c73c;color:#fff;padding:16px 24px;border-radius:10px;font-weight:bold;z-index:99999;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.3);font-family:sans-serif';
        n.textContent = '⚡ AI Flow: 프롬프트 주입 완료';
        document.body.appendChild(n);
        setTimeout(() => n.remove(), 4000);

        return { success: true };
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

  // 단일 플랫폼 공장 가동
  if (msg.type === 'START_FACTORY') {
    const factory = FACTORY_MAP[msg.platform];
    if (!factory) { sendResponse({ error: 'unknown platform' }); return; }

    chrome.tabs.create({ url: factory.url }, (tab) => {
      // 탭 로드 완료 대기
      chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
        if (tabId === tab.id && info.status === 'complete') {
          chrome.tabs.onUpdated.removeListener(listener);
          // 3초 추가 대기 후 주입
          setTimeout(async () => {
            const prompts = msg.prompts || [];
            await processQueue(tab.id, prompts, factory, 0);
          }, 3000);
        }
      });
      sendResponse({ tabId: tab.id, status: 'launched' });
    });
    return true;
  }

  // 전 공장 동시 가동
  if (msg.type === 'START_ALL_FACTORIES') {
    const results = {};
    const platforms = ['image', 'video', 'audio'];
    let launched = 0;

    platforms.forEach(platform => {
      const prompts = msg[platform + 'Prompts'] || [];
      if (!prompts.length) return;

      const factory = FACTORY_MAP[platform];
      chrome.tabs.create({ url: factory.url }, (tab) => {
        results[platform] = tab.id;
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
});

// --- 순차 큐 처리 ---
async function processQueue(tabId, prompts, factory, index) {
  if (index >= prompts.length) {
    console.log(`[AI Flow] ${factory.name}: 모든 작업 완료 (${prompts.length}건)`);
    // 완료 알림
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

  // 진행 알림
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
    // 쿨다운 후 다음 프롬프트
    setTimeout(() => processQueue(tabId, prompts, factory, index + 1), factory.cooldown);
  }
}
