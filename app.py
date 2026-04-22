import os
import json
import time
import re
import sys
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 🛡️ 인코딩 방어
if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODELS = ['gemini-2.5-flash', 'gemini-2.5-flash-lite']  # 검증된 모델만

app = Flask(__name__)
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_content')
os.makedirs(SAVE_DIR, exist_ok=True)

HUMANIZER_PROTOCOL = """
[CRITICAL: 안티-AI 감지 및 100% 휴머나이징 규칙]
1. AI 금지어 절대 삭제: "결론적으로", "요약하자면", "이처럼", "중요한 것은", "기억하세요".
2. 의도적 불완전함: 너무 완벽한 문어체를 쓰지 마라. "아니 진짜로,", "솔직히 말해서", "하아...", "~랄까?" 같은 인간의 구어체 추임새를 문단마다 1개씩 자연스럽게 섞을 것.
3. 시청자 빙의: 가르치려 들지 말고, 멱살 잡고 끌고 가거나(도파민), 옆에 앉아 등을 토닥여라(옥시토신).
4. 문장 호흡 파괴: 긴 문장 뒤에는 무조건 아주 짧은 단문을 배치하여 리듬감을 만든다.
"""

VISUAL_GUARDRAIL = """
[CRITICAL: 영상 생성 8대 가드레일 강제 적용]
비디오 프롬프트 작성 시 끝에 무조건 다음 문장을 영어로 붙일 것:
"Lock temporal and spatial continuity. Unbroken single-take. Preserve cinematic film grain and precise textures. Strictly preserve all visible Hangul. Zero temporal flickering or AI plastic look."
"""

def get_previous_titles(max_count=10):
    """이전 저장 원고 제목 수집 (중복 방지용)"""
    titles = []
    try:
        for fname in sorted(os.listdir(SAVE_DIR), reverse=True)[:max_count]:
            if not fname.endswith('.json'): continue
            with open(os.path.join(SAVE_DIR, fname), 'r', encoding='utf-8') as f:
                meta = json.load(f)
            titles.append(meta.get('title', ''))
    except: pass
    return [t for t in titles if t]

def clean_json_response(raw_text):
    text = raw_text.strip()
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    return text.strip()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Os Studio v15.1 - Real World Edition</title>
    <style>
        :root { --bg: #09090b; --panel: #18181b; --text: #e4e4e7; --accent: #3b82f6; --dopamine: #ef4444; --oxytocin: #10b981; }
        body { margin: 0; display: flex; font-family: sans-serif; background: var(--bg); color: var(--text); height: 100vh; overflow: hidden; }
        #sidebar { width: 300px; background: var(--panel); border-right: 1px solid #27272a; padding: 20px; overflow-y: auto; }
        .history-item { padding: 12px; margin-bottom: 8px; background: #27272a; border-radius: 8px; font-size: 13px; cursor: pointer; color: #a1a1aa; transition: 0.2s; }
        .history-item:hover { background: #3f3f46; color: white; }
        .history-actions { display: flex; gap: 6px; margin-top: 6px; }
        .history-actions button { padding: 3px 8px; font-size: 11px; border-radius: 4px; }
        #main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        #toolbar { padding: 20px; background: var(--panel); border-bottom: 1px solid #27272a; display: flex; gap: 15px; justify-content: center; align-items: center; }
        input { padding: 12px; width: 400px; border-radius: 8px; border: 1px solid #3f3f46; background: #27272a; color: white; outline: none; font-size: 15px; }
        button { padding: 12px 24px; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; color: white; transition: 0.2s; }
        .btn-dopamine { background: var(--dopamine); }
        .btn-dopamine:hover { background: #dc2626; transform: translateY(-1px); }
        .btn-oxytocin { background: var(--oxytocin); }
        .btn-oxytocin:hover { background: #059669; transform: translateY(-1px); }
        .btn-naver { background: #2db400; font-size: 11px; padding: 4px 10px; }
        #content { padding: 30px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; align-items: center; gap: 20px; }
        .card { background: var(--panel); padding: 30px; border-radius: 12px; width: 100%; max-width: 900px; border: 1px solid #27272a; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }
        th, td { border: 1px solid #3f3f46; padding: 12px; text-align: left; }
        th { background: #27272a; color: var(--accent); }
        pre { white-space: pre-wrap; line-height: 1.8; font-size: 15px; color: #d4d4d8; }
        #loading { display: none; position: fixed; inset: 0; background: rgba(9,9,11,0.95); z-index: 1000; justify-content: center; align-items: center; flex-direction: column; }
        .series-label { display: flex; align-items: center; gap: 8px; color: #a1a1aa; font-size: 13px; cursor: pointer; }
        .series-label input { width: 18px; height: 18px; accent-color: var(--accent); }
        .toast { position: fixed; bottom: 30px; right: 30px; background: #2db400; color: white; padding: 14px 24px; border-radius: 10px; font-weight: bold; z-index: 2000; animation: fadeInOut 2.5s ease-in-out; }
        @keyframes fadeInOut { 0% { opacity:0; transform:translateY(20px); } 15% { opacity:1; transform:translateY(0); } 85% { opacity:1; } 100% { opacity:0; } }
    </style>
</head>
<body>
    <div id="loading">
        <h2 style="color: var(--accent);">엔진 구동 중...</h2>
        <p style="color: #71717a;">인간의 뇌 구조에 맞는 대본을 조립하고 있습니다.</p>
    </div>

    <div id="sidebar">
        <h3 style="color: var(--accent); margin-top: 0;">저장된 기록</h3>
        <button onclick="loadHistoryList()" style="width: 100%; background: #3f3f46; margin-bottom: 15px; font-size: 13px;">새로고침</button>
        <div id="history-list"></div>
    </div>

    <div id="main">
        <div id="toolbar">
            <input type="text" id="keyword" placeholder="키워드 입력 (예: 이직, 주식, 고양이)">
            <label class="series-label">
                <input type="checkbox" id="series-mode"> 시리즈 모드
            </label>
            <button class="btn-dopamine" onclick="generate('DOPAMINE')">뉴로-해커 모드</button>
            <button class="btn-oxytocin" onclick="generate('OXYTOCIN')">힐링 ASMR 모드</button>
        </div>
        
        <div id="content">
            <div class="card" id="output-area" style="display: none;">
                <span class="badge" id="mode-badge"></span>
                <h2 id="out-title" style="margin-top:0;"></h2>
                <div style="color: #a1a1aa; margin-bottom: 20px;">페르소나: <span id="out-persona" style="color: #fbbf24;"></span></div>
                
                <h3 style="color: var(--accent); border-bottom: 1px solid #3f3f46; padding-bottom: 10px;">대본</h3>
                <pre id="out-script"></pre>
                
                <h3 style="color: var(--accent); border-bottom: 1px solid #3f3f46; padding-bottom: 10px; margin-top: 40px;">시각화 설계도</h3>
                <div id="out-table"></div>
            </div>
        </div>
    </div>

    <script>
        function showToast(msg) {
            const t = document.createElement('div');
            t.className = 'toast';
            t.innerText = msg;
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 2600);
        }

        function renderOutput(data, mode) {
            document.getElementById('output-area').style.display = 'block';
            const badge = document.getElementById('mode-badge');
            
            if(mode === 'DOPAMINE') {
                badge.innerText = 'DOPAMINE MODE';
                badge.style.background = 'var(--dopamine)';
            } else if(mode === 'OXYTOCIN') {
                badge.innerText = 'OXYTOCIN MODE';
                badge.style.background = 'var(--oxytocin)';
            } else {
                badge.innerText = 'LOADED';
                badge.style.background = 'var(--accent)';
            }
            
            document.getElementById('out-title').innerText = data.title || '';
            document.getElementById('out-persona').innerText = data.persona || '';
            document.getElementById('out-script').innerText = typeof data.script === 'string' ? data.script : JSON.stringify(data.script, null, 2);
            
            const prompts = data.prompts || [];
            let tableHTML = '<table><tr><th>컷</th><th>나레이션/대사</th><th>이미지 프롬프트</th><th>비디오 프롬프트</th></tr>';
            prompts.forEach(p => {
                tableHTML += `<tr><td>${p.cut||''}</td><td>${p.text||''}</td><td>${p.img||''}</td><td>${p.vid||''}</td></tr>`;
            });
            tableHTML += '</table>';
            document.getElementById('out-table').innerHTML = tableHTML;
            
            document.getElementById('content').scrollTo(0, 0);
        }

        async function generate(mode) {
            const kw = document.getElementById('keyword').value;
            const isSeries = document.getElementById('series-mode').checked;
            if(!kw) return alert('키워드를 입력하세요.');
            
            document.getElementById('loading').style.display = 'flex';
            document.getElementById('output-area').style.display = 'none';

            try {
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ keyword: kw, mode: mode, series_mode: isSeries })
                });
                const result = await res.json();
                
                if(result.status === 'success') {
                    renderOutput(result.data, mode);
                    loadHistoryList();
                    showToast('생성 + 자동 저장 완료');
                } else {
                    alert('생성 실패: ' + result.message);
                }
            } catch(e) {
                alert('통신 오류: ' + e.message);
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }

        async function loadHistoryList() {
            try {
                const res = await fetch('/api/history');
                const files = await res.json();
                const list = document.getElementById('history-list');
                list.innerHTML = files.map(f => `
                    <div class="history-item">
                        <div onclick="loadSingleHistory('${f.filename}')" style="cursor:pointer;">${f.display}</div>
                        <div class="history-actions">
                            <button class="btn-naver" onclick="event.stopPropagation(); copyNaverFormat('${f.filename}')">네이버 복사</button>
                        </div>
                    </div>`
                ).join('');
            } catch(e) {}
        }

        async function loadSingleHistory(filename) {
            try {
                const res = await fetch(`/api/history/${filename}`);
                const result = await res.json();
                if(result.status === 'success') {
                    renderOutput(result.data, 'LOADED');
                }
            } catch(e) {
                alert('파일을 불러오지 못했습니다.');
            }
        }

        async function copyNaverFormat(filename) {
            try {
                const res = await fetch(`/api/naver-format/${filename}`);
                const data = await res.json();
                if(data.error) { alert(data.error); return; }
                await navigator.clipboard.writeText(data.naver_html);
                showToast('네이버 블로그 양식 복사 완료!');
            } catch(e) { alert('복사 실패: ' + e.message); }
        }

        window.onload = loadHistoryList;
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/history')
def get_history():
    files = []
    for fname in sorted(os.listdir(SAVE_DIR), reverse=True):
        if not fname.endswith('.json'): continue
        try:
            with open(os.path.join(SAVE_DIR, fname), 'r', encoding='utf-8') as f:
                meta = json.load(f)
            display = meta.get('title', fname)[:40]
            files.append({"filename": fname, "display": display})
        except:
            files.append({"filename": fname, "display": fname})
    return jsonify(files)

@app.route('/api/history/<filename>')
def get_single_history(filename):
    filepath = os.path.join(SAVE_DIR, os.path.basename(filename))
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return jsonify({"status": "success", "data": data})
    return jsonify({"status": "error", "message": "파일 없음"})

@app.route('/api/naver-format/<filename>')
def naver_format(filename):
    try:
        filepath = os.path.join(SAVE_DIR, os.path.basename(filename))
        if not os.path.exists(filepath):
            return jsonify({"error": "파일 없음"}), 404
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        title = data.get('title', '')
        script = data.get('script', '')
        persona = data.get('persona', '')
        # 대본을 네이버 블로그 HTML로 변환
        paragraphs = [p.strip() for p in script.split('\\n') if p.strip()]
        if not paragraphs:
            paragraphs = [p.strip() for p in script.split('\n') if p.strip()]
        body_html = ''.join([f'<p style="font-size:16px; line-height:2.0; margin-bottom:20px;">{p}</p>' for p in paragraphs])
        naver_html = f"""<div style="text-align:center; font-family:'Nanum Gothic',sans-serif; color:#333;">
<h2 style="font-size:24px; font-weight:bold; margin-bottom:30px; line-height:1.6;">{title}</h2>
<p style="color:#888; font-size:14px; margin-bottom:40px;">{persona}</p>
{body_html}
</div>"""
        return jsonify({"naver_html": naver_html, "title": title})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate():
    req = request.get_json()
    keyword = req.get('keyword', '')
    mode = req.get('mode', 'DOPAMINE')
    series_mode = req.get('series_mode', False)

    # 📚 이전 원고 중복 방지 / 시리즈 연결
    prev_titles = get_previous_titles()
    prev_section = ""
    if prev_titles:
        title_list = "\n".join([f"  - {t}" for t in prev_titles])
        if series_mode:
            prev_section = f"""
    [시리즈 모드 ON]
    아래는 이전에 생성한 콘텐츠 제목 목록이다. 이 글들의 **후속편/시리즈**로 작성하라.
    - 이전 글과 자연스럽게 이어지는 스토리라인.
    - 제목에 시리즈 넘버링 혹은 '후편', '그 후' 등 표시.
    [이전 글 목록]
{title_list}
"""
        else:
            prev_section = f"""
    [중복 방지]
    아래 제목들과 **완전히 다른 각도/관점/소재**로 작성하라. 같은 내용 반복 금지.
    [이전 글 목록]
{title_list}
"""

    if mode == 'DOPAMINE':
        mode_instruction = "[DOPAMINE 모드: 뇌과학 해커 & 팩트 폭행]\n- 츤데레 코치 빙의. 단정형 화법.\n- IT/게임 비유, 조선왕조실록 인용으로 권위 세우기.\n- 비주얼: 하이퍼리얼리티 또는 다크 다큐멘터리."
    else:
        mode_instruction = "[OXYTOCIN 모드: 클레이 ASMR 힐링]\n- 지친 마음을 다독이는 따뜻한 치유자.\n- 평화로운 미니어처 공방 서사.\n- 비주얼: 폴리머 클레이, 쫀득한 질감, 텅스텐 조명."

    master_prompt = f"""
    당신은 콘텐츠 디렉터입니다. 주제 키워드: '{keyword}'
    
    {mode_instruction}
    {prev_section}
    {HUMANIZER_PROTOCOL}
    {VISUAL_GUARDRAIL}

    아래의 JSON 형식으로만 정확히 출력하세요. (마크다운 백틱 금지, 순수 JSON만)
    {{
        "title": "클릭을 유도하는 훅 제목",
        "persona": "구체적인 타겟 페르소나",
        "script": "구어체 대본 (최소 800자 이상)",
        "prompts": [
            {{"cut": "1", "text": "대사", "img": "이미지 프롬프트 (영어)", "vid": "비디오 프롬프트 (영어)"}}
        ]
    }}
    """

    content = None
    for m_id in MODELS:
        try:
            res = client.models.generate_content(
                model=m_id, 
                contents=master_prompt,
                config=types.GenerateContentConfig(temperature=0.8)
            )
            clean_text = clean_json_response(res.text)
            content = json.loads(clean_text)
            break
        except Exception as e:
            print(f"[{m_id}] Error: {e}")
            continue

    if not content:
        return jsonify({"status": "error", "message": "AI 생성 중 오류가 발생했습니다. 다시 시도해주세요."})

    try:
        safe_kw = re.sub(r'\W+', '_', keyword)[:15]
        timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
        filename = f"{safe_kw}_{timestamp}.json"
        
        filepath = os.path.join(SAVE_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
        print(f"[SAVED] {filename}")
            
        return jsonify({"status": "success", "data": content})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)