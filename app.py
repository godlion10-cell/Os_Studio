import os
import json
import re
import sys
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from google import genai
from google.genai import types
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODELS = ['gemini-2.5-flash', 'gemini-2.5-flash-lite']

app = Flask(__name__)
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_content')
os.makedirs(SAVE_DIR, exist_ok=True)

def get_today():
    return datetime.now().strftime('%Y년 %m월 %d일')

HUMAN_PROMPT = """
[딥 소울 가이드라인]
1. 인사말 절대 금지: "안녕하세요", "~마스터입니다" 쓰지 마라.
2. 오프닝: 힐링은 감각적 묘사로, 해커는 날카로운 페인포인트로 즉시 시작.
3. 현재 시점 기준 최신 정보만 취급. 과거 정보 금지.
4. 이미지 삽입구 3~4개 필수: [이미지 1: 설명] 형식.
5. 쇼츠: 60초 이내, 9컷 이내 강렬한 대사 위주.
6. 인스타: 감성적 첫 문장 + 해시태그 10개.
"""

def clean_json(raw):
    text = raw.strip()
    text = re.sub(r'^```\w*\n?', '', text)
    if text.endswith('```'): text = text[:-3]
    return text.strip()

def call_gemini(prompt, use_json_mime=False):
    for m_id in MODELS:
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json" if use_json_mime else None,
                temperature=0.8 if not use_json_mime else None
            )
            res = client.models.generate_content(model=m_id, contents=prompt, config=config)
            return json.loads(res.text) if use_json_mime else json.loads(clean_json(res.text))
        except Exception as e:
            print(f"[{m_id}] Error: {e}")
            continue
    return None

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Os Studio v16.5 - Clean Factory</title>
    <style>
        :root { --bg: #f8f9fa; --sidebar: #1a1a1b; --naver-green: #00c73c; --accent: #3b82f6; --danger: #ff4d4d; }
        body { margin: 0; display: flex; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background: var(--bg); height: 100vh; overflow: hidden; color: #333; }
        
        #sidebar { width: 340px; background: var(--sidebar); color: #999; display: flex; flex-direction: column; border-right: 1px solid #333; }
        .sidebar-section { padding: 15px; border-bottom: 1px solid #333; overflow-y: auto; }
        .keyword-chip { padding: 5px 10px; margin: 3px; background: #333; border-radius: 4px; font-size: 11px; cursor: pointer; display: inline-block; color: #00c73c; transition: 0.2s; }
        .keyword-chip:hover { background: #444; color: white; }
        
        .history-controls { display: flex; gap: 5px; margin-bottom: 10px; }
        .history-btn { flex: 1; padding: 5px; font-size: 11px; cursor: pointer; background: #333; color: #ccc; border: none; border-radius: 3px; transition: 0.2s; }
        .history-btn:hover { background: #444; }

        .history-item { display: flex; align-items: center; padding: 8px; background: #27272a; border-radius: 4px; margin-bottom: 5px; font-size: 11px; cursor: pointer; }
        .history-item:hover { background: #3a3a3a; }
        .history-item input[type="checkbox"] { margin-right: 8px; cursor: pointer; accent-color: var(--naver-green); }
        .history-item span { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #ccc; }

        #main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        #toolbar { padding: 15px; background: white; border-bottom: 1px solid #ddd; display: flex; gap: 10px; justify-content: center; align-items: center; }
        input#keyword { padding: 10px; width: 350px; border: 1px solid #ddd; border-radius: 6px; outline: none; font-size: 14px; }
        .gen-btn { padding: 10px 20px; background: var(--naver-green); color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .gen-btn:hover { background: #00b336; }
        
        #editor-container { display: flex; flex: 1; overflow: hidden; gap: 10px; padding: 10px; }
        .editor-pane { flex: 1; background: white; border: 1px solid #ddd; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; }
        .pane-header { padding: 10px 15px; background: #fafafa; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .copy-btn { padding: 5px 10px; font-size: 11px; cursor: pointer; border: 1px solid #ddd; background: white; border-radius: 4px; font-weight: bold; }
        .copy-btn:hover { background: var(--naver-green); color: white; border-color: var(--naver-green); }
        .writing-area { flex: 1; padding: 40px 25px; overflow-y: auto; text-align: center; word-break: keep-all; line-height: 1.8; font-size: 16px; }
        .sns-hub { background: #f8f9fa; padding: 20px; border-top: 2px solid #00c73c; font-size: 12px; text-align: left; line-height: 1.6; max-height: 250px; overflow-y: auto; }
        .sns-hub pre { white-space: pre-wrap; font-size: 12px; background: white; padding: 10px; border-radius: 4px; margin: 8px 0; }
        .img-guide { display: block; width: 85%; margin: 20px auto; padding: 30px; background: #fff; border: 2px dashed #ccc; color: #888; font-size: 13px; border-radius: 8px; }
        
        #loading { display: none; position: fixed; inset: 0; background: rgba(255,255,255,0.9); z-index: 1000; justify-content: center; align-items: center; flex-direction: column; }
        .toast { position: fixed; bottom: 30px; right: 30px; background: var(--naver-green); color: white; padding: 14px 24px; border-radius: 10px; font-weight: bold; z-index: 2000; animation: fadeInOut 2.5s; }
        @keyframes fadeInOut { 0%{opacity:0;transform:translateY(20px)} 15%{opacity:1;transform:translateY(0)} 85%{opacity:1} 100%{opacity:0} }
    </style>
</head>
<body>
    <div id="loading">
        <h2 style="color: var(--naver-green);">🧹 원고를 빚는 중...</h2>
        <p style="color: #999;">블로그 + 쇼츠 + 인스타 × 2모드 동시 생성</p>
    </div>
    
    <div id="sidebar">
        <div class="sidebar-section">
            <h5 style="color: #00c73c; margin: 0 0 10px 0;">🔍 실시간 레이더</h5>
            <div id="trends">로딩 중...</div>
        </div>
        <div class="sidebar-section" style="flex: 2;">
            <h5 style="color: #a1a1aa; margin: 0 0 10px 0;">💾 저장된 기록</h5>
            <div class="history-controls">
                <button class="history-btn" onclick="toggleAllCheck(true)">전체 선택</button>
                <button class="history-btn" onclick="toggleAllCheck(false)">선택 해제</button>
                <button class="history-btn" onclick="deleteSelected()" style="color: var(--danger);">선택 삭제</button>
                <button class="history-btn" onclick="deleteAll()" style="color: var(--danger); font-weight: bold;">전체 삭제</button>
            </div>
            <div id="history-list">기록 없음</div>
        </div>
    </div>

    <div id="main">
        <div id="toolbar">
            <input type="text" id="keyword" placeholder="주제를 입력하세요">
            <button class="gen-btn" onclick="generateDual()">💎 듀얼 소울 생성</button>
        </div>
        <div id="editor-container">
            <div class="editor-pane">
                <div class="pane-header">
                    <strong>🔥 뉴로-해커</strong>
                    <button class="copy-btn" onclick="copyPane('hacker-blog')">블로그 복사</button>
                </div>
                <div class="writing-area" id="hacker-blog">키워드를 입력하고 생성하세요.</div>
                <div class="sns-hub" id="hacker-sns"></div>
            </div>
            <div class="editor-pane">
                <div class="pane-header">
                    <strong>🍀 딥 소울 (힐링)</strong>
                    <button class="copy-btn" onclick="copyPane('healer-blog')">블로그 복사</button>
                </div>
                <div class="writing-area" id="healer-blog">듀얼 모드로 동시 작성됩니다.</div>
                <div class="sns-hub" id="healer-sns"></div>
            </div>
        </div>
    </div>

    <script>
        function showToast(msg) {
            const t = document.createElement('div');
            t.className = 'toast'; t.innerText = msg;
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 2600);
        }

        async function loadTrends() {
            try {
                const res = await fetch('/api/trends');
                const data = await res.json();
                const sArr = Array.isArray(data.search) ? data.search : Object.values(data.search || {});
                const hArr = Array.isArray(data.home) ? data.home : Object.values(data.home || {});
                const all = [...sArr, ...hArr];
                document.getElementById('trends').innerHTML = all.map(v => {
                    const s = String(v).replace(/'/g, "\\'");
                    return `<span class="keyword-chip" onclick="setKW('${s}')">${v}</span>`;
                }).join('');
            } catch(e) { document.getElementById('trends').innerText = '새로고침 하세요'; }
        }

        function setKW(v) { document.getElementById('keyword').value = v; generateDual(); }

        async function generateDual() {
            const kw = document.getElementById('keyword').value;
            if(!kw) return alert('키워드를 입력하세요.');
            document.getElementById('loading').style.display = 'flex';
            try {
                const res = await fetch('/api/generate-dual', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'}, 
                    body: JSON.stringify({ keyword: kw }) 
                });
                const data = await res.json();
                if(data.status === 'error') { alert(data.message); return; }
                renderPane('hacker', data.hacker);
                renderPane('healer', data.healer);
                showToast('듀얼 생성 + 자동 저장 완료');
                loadHistory();
            } catch(e) { alert('통신 오류'); }
            finally { document.getElementById('loading').style.display = 'none'; }
        }

        function renderPane(mode, data) {
            if(!data || !data.blog) { 
                document.getElementById(mode + '-blog').innerHTML = '<p style="color:#999;">생성 실패 - 재시도 해주세요</p>'; 
                return; 
            }
            let blog = `<h1 style="font-size:22px; margin-bottom: 25px;">${data.blog.title || ''}</h1>`;
            let body = (data.blog.script || '').replace(/\[이미지 \d+:\s*(.*?)\]/g, '<div class="img-guide">📷 사진 포인트: $1</div>');
            blog += `<div>${body.replace(/\\n/g, '<br>')}</div>`;
            document.getElementById(mode + '-blog').innerHTML = blog;
            
            let sns = '<b>🎬 쇼츠 대본:</b>';
            sns += `<pre>${data.sns ? (data.sns.shorts || '') : ''}</pre>`;
            sns += '<hr style="border-color:#eee;"><b>📸 인스타 캡션:</b>';
            sns += `<pre>${data.sns ? (data.sns.insta || '') : ''}</pre>`;
            document.getElementById(mode + '-sns').innerHTML = sns;
        }

        function copyPane(id) {
            const range = document.createRange();
            range.selectNode(document.getElementById(id));
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
            document.execCommand('copy');
            window.getSelection().removeAllRanges();
            showToast('복사 완료! 네이버 블로그에 붙여넣으세요');
        }

        async function loadHistory() {
            try {
                const res = await fetch('/api/history');
                const files = await res.json();
                const el = document.getElementById('history-list');
                if(!files.length) { el.innerText = '기록 없음'; return; }
                el.innerHTML = files.map(f => `
                    <div class="history-item">
                        <input type="checkbox" class="hist-check" data-name="${f.filename}">
                        <span onclick="loadSingle('${f.filename}')">${f.display}</span>
                    </div>
                `).join('');
            } catch(e) {}
        }

        function toggleAllCheck(val) {
            document.querySelectorAll('.hist-check').forEach(c => c.checked = val);
        }

        async function deleteSelected() {
            const selected = Array.from(document.querySelectorAll('.hist-check:checked')).map(c => c.dataset.name);
            if(!selected.length) return alert('삭제할 항목을 선택하세요.');
            if(!confirm(`${selected.length}개 기록을 삭제할까요?`)) return;
            await fetch('/api/delete-selected', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ filenames: selected }) });
            showToast(`${selected.length}개 삭제 완료`);
            loadHistory();
        }

        async function deleteAll() {
            if(!confirm('모든 기록을 삭제하시겠습니까? 되돌릴 수 없습니다.')) return;
            await fetch('/api/delete-all', { method: 'POST' });
            showToast('전체 삭제 완료');
            loadHistory();
        }

        async function loadSingle(name) {
            try {
                const res = await fetch(`/api/history/${name}`);
                const data = await res.json();
                if(data.hacker) renderPane('hacker', data.hacker);
                if(data.healer) renderPane('healer', data.healer);
            } catch(e) { alert('불러오기 실패'); }
        }

        window.onload = () => { loadTrends(); loadHistory(); };
    </script>
</body>
</html>
"""

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/trends')
def get_trends():
    today = get_today()
    prompt = f"""
    오늘은 {today}이다. 지금 시점 대한민국에서 화제인 키워드를 뽑아라.
    1. 검색용(재테크, 정책뉴스, 상품리뷰): 정보성 키워드 8개
    2. 홈판용(스타일, 뷰티, 연예/드라마): 자극적 키워드 8개
    JSON: {{"search": [], "home": []}}
    """
    result = call_gemini(prompt, use_json_mime=True)
    return jsonify(result or {"search": ["재시도 필요"], "home": ["대기 중"]})

@app.route('/api/history')
def get_history():
    files = []
    for fname in sorted(os.listdir(SAVE_DIR), reverse=True)[:30]:
        if not fname.endswith('.json'): continue
        try:
            with open(os.path.join(SAVE_DIR, fname), 'r', encoding='utf-8') as f:
                meta = json.load(f)
            display = meta.get('keyword', fname[:25])
        except:
            display = fname[:25]
        files.append({"filename": fname, "display": display})
    return jsonify(files)

@app.route('/api/history/<name>')
def history_single(name):
    safe = os.path.basename(name)
    fpath = os.path.join(SAVE_DIR, safe)
    if not os.path.exists(fpath):
        return jsonify({"error": "파일 없음"}), 404
    with open(fpath, 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))

@app.route('/api/delete-selected', methods=['POST'])
def delete_selected():
    filenames = request.get_json().get('filenames', [])
    deleted = 0
    for f in filenames:
        safe = os.path.basename(f)  # 경로 탈출 방지
        path = os.path.join(SAVE_DIR, safe)
        if os.path.exists(path):
            os.remove(path)
            deleted += 1
    return jsonify({"status": "success", "deleted": deleted})

@app.route('/api/delete-all', methods=['POST'])
def delete_all():
    deleted = 0
    for f in os.listdir(SAVE_DIR):
        if f.endswith('.json'):
            os.remove(os.path.join(SAVE_DIR, f))
            deleted += 1
    return jsonify({"status": "success", "deleted": deleted})

@app.route('/api/generate-dual', methods=['POST'])
def generate_dual():
    kw = request.get_json().get('keyword', '')
    today = get_today()

    def get_bundle(mode_desc):
        prompt = f"""
        주제: '{kw}', 모드: {mode_desc}. 오늘: {today}.
        {HUMAN_PROMPT}
        JSON 형식으로만 응답:
        {{
            "blog": {{ "title": "훅 제목", "script": "블로그 본문 (최소 800자, [이미지 1: 설명] 3~4개 포함)" }},
            "sns": {{ "shorts": "9컷 쇼츠 대본", "insta": "인스타 캡션 + 해시태그 10개" }}
        }}
        """
        return call_gemini(prompt, use_json_mime=False)

    hacker = get_bundle("츤데레 코치. 팩트 폭행. IT/게임 비유. 단정형 화법.")
    healer = get_bundle("따뜻한 치유자. ASMR 톤. 감각적 묘사. 미니어처 공방 서사.")

    if not hacker and not healer:
        return jsonify({"status": "error", "message": "AI 생성 실패. 재시도 해주세요."})

    # 자동 저장
    try:
        safe_kw = re.sub(r'\W+', '_', kw)[:15]
        filename = f"{datetime.now().strftime('%y%m%d_%H%M%S')}_{safe_kw}.json"
        save_data = {"keyword": kw, "hacker": hacker, "healer": healer}
        with open(os.path.join(SAVE_DIR, filename), 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        print(f"[SAVED] {filename}")
    except Exception as e:
        print(f"[SAVE ERROR] {e}")

    return jsonify({"hacker": hacker, "healer": healer})

if __name__ == '__main__':
    app.run(debug=True, port=5000)