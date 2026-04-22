import os
import json
import re
import io
import sys
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
TEXT_MODELS = ['gemini-2.5-flash', 'gemini-2.5-flash-lite']
IMAGE_MODEL = 'imagen-3.0-generate-002'

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, 'saved_content')
IMG_DIR = os.path.join(SAVE_DIR, 'images')
os.makedirs(SAVE_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

def get_today():
    return datetime.now().strftime('%Y년 %m월 %d일')

HUMAN_PROMPT = """
[멀티채널 통합 가이드라인]
1. 모든 정보는 현재 시점 최신 팩트 기반.
2. 말투: '안녕하세요' 금지. 진짜 사람의 찐후기 톤. (힐링: 감성 묘사 / 해커: 팩트 폭행)
3. 이미지 배치: 원고에 [📷 이미지 1: 설명], [📷 이미지 2: 설명], [📷 이미지 3: 설명] 총 3개 삽입 포인트 필수.
4. 화풍: 실사 기반 하이퍼리얼리즘. cinematic lighting, close-up, high detailed textures. (카툰/일러스트 금지)
"""

# =========================================================
# [v17.5] SovereignMetaAgent - 자가 진화형 메타 에이전트
# =========================================================
class SovereignMetaAgent:
    """이전 원고를 분석해 프롬프트를 자동 강화하고, 감성 동기화로 이미지 톤을 조율하는 메타 에이전트"""

    # AI가 자주 쓰는 패턴 (감지 → 다음 생성에서 금지 강도 상향)
    AI_PATTERNS = [
        "안녕하세요", "결론적으로", "요약하자면", "이처럼", "중요한 것은",
        "기억하세요", "마지막으로", "첫째,", "둘째,", "셋째,",
        "Let me", "Bro", "Here's", "In conclusion"
    ]

    SENTIMENT_MAP = {
        "dopamine": {"keywords": ["충격", "폭탄", "진짜", "미쳤", "대박", "ㄹㅇ", "레전드"],
                     "visual_tone": "dark dramatic lighting, high contrast, neon accents, intense atmosphere"},
        "oxytocin": {"keywords": ["따뜻", "포근", "힐링", "쉼", "고요", "안도", "평화"],
                     "visual_tone": "warm golden hour lighting, soft bokeh, cozy atmosphere, gentle tones"},
        "curiosity": {"keywords": ["비밀", "몰랐", "알고보니", "숨겨진", "반전", "진실"],
                      "visual_tone": "mysterious shadows, fog, dim lighting, cinematic suspense"},
        "urgency": {"keywords": ["지금", "당장", "마감", "서둘러", "놓치면", "한정"],
                    "visual_tone": "sharp focus, clock elements, red highlights, fast-paced energy"}
    }

    def __init__(self):
        self.logs = []
        self.detected_issues = []
        self.dominant_sentiment = None

    def scan_previous_outputs(self, max_scan=5):
        """이전 저장 원고를 스캔해 AI 패턴 적발"""
        self.detected_issues = []
        try:
            files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.json')], reverse=True)[:max_scan]
            for fname in files:
                with open(os.path.join(SAVE_DIR, fname), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # hacker/healer 양쪽 스캔
                for mode_key in ['hacker', 'healer']:
                    mode_data = data.get(mode_key, {})
                    blog = mode_data.get('blog', mode_data)  # 구버전 호환
                    script = blog.get('script', '') if isinstance(blog, dict) else ''
                    for pattern in self.AI_PATTERNS:
                        if pattern in script:
                            self.detected_issues.append(pattern)
        except Exception as e:
            print(f"[Meta] Scan error: {e}")
        
        self.detected_issues = list(set(self.detected_issues))  # 중복 제거
        if self.detected_issues:
            print(f"[Meta] AI 패턴 {len(self.detected_issues)}건 적발: {self.detected_issues[:5]}")
        return self.detected_issues

    def build_reinforcement(self):
        """적발된 AI 패턴을 기반으로 프롬프트 강화 지시문 생성"""
        if not self.detected_issues:
            return ""
        banned = ', '.join([f'"{p}"' for p in self.detected_issues[:10]])
        return f"""
    [🚨 메타 에이전트 자가 튜닝 - 강도 200%]
    이전 원고 분석 결과, 아래 AI 패턴이 감지되었다. 이번 생성에서는 절대 사용 금지:
    금지어 목록: {banned}
    대체 전략: 위 표현 대신 커뮤니티식 날것 표현, 감탄사, 불완전한 문장을 사용하라.
    """

    def analyze_sentiment(self, script_text):
        """원고 텍스트의 감성 주파수를 분석"""
        if not script_text:
            return "dopamine"
        scores = {}
        for sentiment, info in self.SENTIMENT_MAP.items():
            score = sum(1 for kw in info["keywords"] if kw in script_text)
            scores[sentiment] = score
        self.dominant_sentiment = max(scores, key=scores.get) if any(scores.values()) else "dopamine"
        print(f"[Meta] 감성 분석: {scores} → 지배 감성: {self.dominant_sentiment}")
        return self.dominant_sentiment

    def get_visual_tone(self, sentiment=None):
        """감성에 맞는 비주얼 톤 지시문 반환"""
        s = sentiment or self.dominant_sentiment or "dopamine"
        return self.SENTIMENT_MAP.get(s, {}).get("visual_tone", "cinematic lighting, high detail")

    def organic_sync_prompt(self, script_text):
        """글의 감성을 분석하고 이미지 프롬프트에 동기화할 톤 반환"""
        sentiment = self.analyze_sentiment(script_text)
        tone = self.get_visual_tone(sentiment)
        return f"Visual atmosphere: {tone}."

# 글로벌 메타 에이전트 인스턴스
meta_agent = SovereignMetaAgent()

def clean_json(raw):
    text = raw.strip()
    text = re.sub(r'^```\w*\n?', '', text)
    if text.endswith('```'): text = text[:-3]
    return text.strip()

def call_gemini_text(prompt):
    """텍스트 생성 (폴백 포함)"""
    for m_id in TEXT_MODELS:
        try:
            res = client.models.generate_content(
                model=m_id, contents=prompt,
                config=types.GenerateContentConfig(temperature=0.8)
            )
            return json.loads(clean_json(res.text))
        except Exception as e:
            print(f"[{m_id}] Text Error: {e}")
            continue
    return None

def call_gemini_trends(prompt):
    """트렌드 생성 (JSON mime)"""
    for m_id in TEXT_MODELS:
        try:
            res = client.models.generate_content(
                model=m_id, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(res.text)
        except Exception as e:
            print(f"[{m_id}] Trend Error: {e}")
            continue
    return None

def generate_image(prompt_text, save_filename):
    """Imagen 3으로 이미지 생성 → 저장 → 상대경로 반환"""
    try:
        response = client.models.generate_images(
            model=IMAGE_MODEL,
            prompt=f"Cinematic realistic photograph, high detail: {prompt_text}",
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                output_mime_type="image/png"
            )
        )
        if response.generated_images:
            img = response.generated_images[0].image
            filepath = os.path.join(IMG_DIR, save_filename)
            img.save(filepath)
            return f"images/{save_filename}"
    except Exception as e:
        print(f"[Imagen] Error: {e}")
    return None

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Os Studio v16.6 - Visual Sovereign</title>
    <style>
        :root { --bg: #f5f6f8; --sidebar: #1e1e1e; --naver-green: #00c73c; --accent: #3b82f6; --danger: #ff4d4d; }
        body { margin: 0; display: flex; font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background: var(--bg); height: 100vh; overflow: hidden; color: #333; }
        
        #sidebar { width: 340px; background: var(--sidebar); color: #999; display: flex; flex-direction: column; border-right: 1px solid #333; }
        .sidebar-section { padding: 15px; border-bottom: 1px solid #333; overflow-y: auto; }
        .keyword-chip { padding: 6px 10px; margin: 3px; background: #333; border-radius: 4px; font-size: 11px; cursor: pointer; display: inline-block; color: var(--naver-green); transition: 0.2s; }
        .keyword-chip:hover { background: #444; color: white; }
        .history-item { padding: 8px; background: #27272a; border-radius: 4px; margin-bottom: 5px; font-size: 11px; cursor: pointer; color: #a1a1aa; display: flex; align-items: center; }
        .history-item:hover { color: white; background: #333; }
        .history-item input { margin-right: 8px; accent-color: var(--naver-green); }
        .history-item span { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .history-controls { display: flex; gap: 5px; margin-bottom: 10px; }
        .history-btn { flex: 1; padding: 5px; font-size: 11px; cursor: pointer; background: #333; color: #ccc; border: none; border-radius: 3px; }
        .history-btn:hover { background: #444; }

        #main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        #toolbar { padding: 15px; background: white; border-bottom: 1px solid #ddd; display: flex; gap: 10px; justify-content: center; align-items: center; }
        input#keyword { padding: 10px; width: 350px; border: 1px solid #ddd; border-radius: 6px; outline: none; font-size: 14px; }
        .gen-btn { padding: 10px 20px; background: var(--naver-green); color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .gen-btn:hover { background: #00b336; }
        
        #editor-container { display: flex; flex: 1; overflow: hidden; gap: 10px; padding: 10px; }
        .editor-pane { flex: 1; background: white; border: 1px solid #ddd; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .pane-header { padding: 10px 15px; background: #fafafa; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .copy-btn { padding: 5px 10px; font-size: 11px; cursor: pointer; border: 1px solid #ddd; background: white; border-radius: 4px; font-weight: bold; }
        .copy-btn:hover { background: var(--naver-green); color: white; border-color: var(--naver-green); }
        
        .writing-area { flex: 1; padding: 40px 25px; overflow-y: auto; text-align: center; word-break: keep-all; line-height: 1.8; font-size: 16px; color: #333; }
        .writing-area img { max-width: 90%; margin: 20px auto; border-radius: 8px; display: block; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .img-placeholder { display: block; width: 85%; margin: 20px auto; padding: 40px; background: #f9f9f9; border: 2px dashed #ccc; color: #888; font-size: 13px; border-radius: 8px; }

        .sns-hub { background: #f8f9fa; padding: 20px; border-top: 2px solid var(--naver-green); font-size: 12px; text-align: left; line-height: 1.6; max-height: 250px; overflow-y: auto; }
        .sns-hub pre { white-space: pre-wrap; background: white; padding: 10px; border-radius: 4px; margin: 8px 0; font-size: 12px; }
        .sns-meta { display: flex; gap: 15px; margin-bottom: 10px; align-items: center; }
        .sns-prompt-img { width: 100px; height: 100px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd; }
        
        #loading { display: none; position: fixed; inset: 0; background: rgba(255,255,255,0.95); z-index: 1000; justify-content: center; align-items: center; flex-direction: column; }
        .toast { position: fixed; bottom: 30px; right: 30px; background: var(--naver-green); color: white; padding: 14px 24px; border-radius: 10px; font-weight: bold; z-index: 2000; animation: fadeInOut 2.5s; }
        @keyframes fadeInOut { 0%{opacity:0;transform:translateY(20px)} 15%{opacity:1;transform:translateY(0)} 85%{opacity:1} 100%{opacity:0} }
    </style>
</head>
<body>
    <div id="loading">
        <h2 style="color: var(--naver-green);">🖼️ 이미지 + 원고를 동시에 생성 중...</h2>
        <p style="color: #999;">블로그 이미지 3장 + SNS 이미지 1장 × 2모드 = 약 30초 소요</p>
    </div>
    
    <div id="sidebar">
        <div class="sidebar-section">
            <h5 style="color: #00c73c; margin: 0 0 10px 0;">🔍 실시간 레이더</h5>
            <div id="trends">로딩 중...</div>
        </div>
        <div class="sidebar-section" style="flex: 2;">
            <h5 style="color: #a1a1aa; margin: 0 0 10px 0;">💾 영혼의 저장소</h5>
            <div class="history-controls">
                <button class="history-btn" onclick="toggleAllCheck(true)">전체 선택</button>
                <button class="history-btn" onclick="deleteSelected()" style="color: var(--danger);">선택 삭제</button>
                <button class="history-btn" onclick="deleteAll()" style="color: var(--danger); font-weight:bold;">전체 삭제</button>
            </div>
            <div id="history-list">기록 없음</div>
        </div>
    </div>

    <div id="main">
        <div id="toolbar">
            <input type="text" id="keyword" placeholder="주제를 입력하거나 레이더를 클릭">
            <button class="gen-btn" onclick="generateVisual()">💎 비주얼 통합 생성</button>
        </div>
        <div id="editor-container">
            <div class="editor-pane">
                <div class="pane-header">
                    <strong>🔥 뉴로-해커 허브</strong>
                    <button class="copy-btn" onclick="copyPane('hacker-blog')">블로그 복사</button>
                </div>
                <div class="writing-area" id="hacker-blog">주제를 입력하고 생성을 눌러주세요.</div>
                <div class="sns-hub" id="hacker-sns"></div>
            </div>
            <div class="editor-pane">
                <div class="pane-header">
                    <strong>🍀 딥 소울 (힐링)</strong>
                    <button class="copy-btn" onclick="copyPane('healer-blog')">블로그 복사</button>
                </div>
                <div class="writing-area" id="healer-blog">이미지와 함께 작성됩니다.</div>
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

        function setKW(v) { document.getElementById('keyword').value = v; generateVisual(); }

        async function generateVisual() {
            const kw = document.getElementById('keyword').value;
            if(!kw) return alert('키워드를 입력하세요.');
            document.getElementById('loading').style.display = 'flex';
            try {
                const res = await fetch('/api/generate-visual', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'}, 
                    body: JSON.stringify({ keyword: kw }) 
                });
                const data = await res.json();
                if(data.status === 'error') { alert(data.message); return; }
                renderPane('hacker', data.hacker);
                renderPane('healer', data.healer);
                showToast('비주얼 통합 생성 + 저장 완료');
                loadHistory();
            } catch(e) { alert('통신 오류'); }
            finally { document.getElementById('loading').style.display = 'none'; }
        }

        function renderPane(mode, data) {
            if(!data || !data.blog) { 
                document.getElementById(mode + '-blog').innerHTML = '<p style="color:#999;">생성 실패</p>'; 
                return; 
            }
            let blog = `<h1 style="font-size:22px; margin-bottom:30px;">${data.blog.title || ''}</h1>`;
            let body = (data.blog.script || '');
            
            // 이미지 마커를 실제 이미지 또는 placeholder로 교체
            const images = data.blog.images || [];
            body = body.replace(/\[📷\s*이미지\s*(\d+):\s*(.*?)\]/g, (match, num, desc) => {
                const idx = parseInt(num) - 1;
                const imgPath = images[idx];
                if(imgPath) return `<img src="/saved_content/${imgPath}" alt="${desc}">`;
                return `<div class="img-placeholder">📷 이미지 ${num}: ${desc}</div>`;
            });
            
            blog += `<div>${body.replace(/\\n/g, '<br>')}</div>`;
            document.getElementById(mode + '-blog').innerHTML = blog;
            
            // SNS
            let snsHTML = '';
            const promptImg = data.sns && data.sns.prompt_image;
            if(promptImg) {
                snsHTML += `<div class="sns-meta"><img src="/saved_content/${promptImg}" class="sns-prompt-img" alt="SNS 이미지"><strong>SNS 프롬프트 이미지</strong></div>`;
            }
            snsHTML += `<b>🎬 쇼츠 대본:</b><pre>${data.sns ? (data.sns.shorts || '') : ''}</pre>`;
            snsHTML += `<hr style="border-color:#eee;"><b>📸 인스타 캡션:</b><pre>${data.sns ? (data.sns.insta || '') : ''}</pre>`;
            document.getElementById(mode + '-sns').innerHTML = snsHTML;
        }

        function copyPane(id) {
            const range = document.createRange();
            range.selectNode(document.getElementById(id));
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
            document.execCommand('copy');
            window.getSelection().removeAllRanges();
            showToast('복사 완료! 네이버에 붙여넣으세요');
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

        function toggleAllCheck(val) { document.querySelectorAll('.hist-check').forEach(c => c.checked = val); }

        async function deleteSelected() {
            const selected = Array.from(document.querySelectorAll('.hist-check:checked')).map(c => c.dataset.name);
            if(!selected.length) return alert('삭제할 항목을 선택하세요.');
            if(!confirm(`${selected.length}개 삭제?`)) return;
            await fetch('/api/delete-selected', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ filenames: selected }) });
            showToast(`${selected.length}개 삭제 완료`);
            loadHistory();
        }

        async function deleteAll() {
            if(!confirm('모든 기록 삭제? 되돌릴 수 없습니다.')) return;
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

@app.route('/saved_content/<path:filename>')
def serve_saved_content(filename):
    return send_from_directory(SAVE_DIR, filename)

# --- API Routes ---

@app.route('/api/trends')
def get_trends():
    today = get_today()
    prompt = f"""
    오늘은 {today}이다. 지금 시점 대한민국에서 화제인 키워드를 뽑아라.
    1. 검색용(재테크, 정책뉴스, 상품리뷰): 정보성 키워드 8개
    2. 홈판용(스타일, 뷰티, 연예/드라마): 자극적 키워드 8개
    JSON: {{"search": [], "home": []}}
    """
    result = call_gemini_trends(prompt)
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
    for f in filenames:
        safe = os.path.basename(f)
        path = os.path.join(SAVE_DIR, safe)
        if os.path.exists(path): os.remove(path)
    return jsonify({"status": "success"})

@app.route('/api/delete-all', methods=['POST'])
def delete_all():
    for f in os.listdir(SAVE_DIR):
        fpath = os.path.join(SAVE_DIR, f)
        if os.path.isfile(fpath): os.remove(fpath)
    return jsonify({"status": "success"})

@app.route('/api/generate-visual', methods=['POST'])
def generate_visual():
    kw = request.get_json().get('keyword', '')
    today = get_today()
    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")

    # [v17.5] 메타 에이전트: 이전 원고 스캔 → 프롬프트 자가 강화
    meta_agent.scan_previous_outputs()
    reinforcement = meta_agent.build_reinforcement()

    def get_bundle(mode_name, mode_desc):
        # 1. 텍스트 + 이미지 프롬프트 생성 (메타 에이전트 강화 포함)
        prompt = f"""
        주제: '{kw}', 모드: {mode_desc}. 오늘: {today}.
        {HUMAN_PROMPT}
        {reinforcement}
        JSON 형식으로만 응답:
        {{
            "blog": {{ 
                "title": "훅 제목", 
                "script": "블로그 본문 (최소 800자, [📷 이미지 1: 설명] [📷 이미지 2: 설명] [📷 이미지 3: 설명] 3개 포함)", 
                "image_prompts": ["영어 이미지 프롬프트 3개 (cinematic, realistic)"] 
            }},
            "sns": {{ 
                "shorts": "9컷 쇼츠 대본", 
                "insta": "인스타 캡션 + 해시태그 10개",
                "prompt_image_prompt": "영어 SNS 타이틀 이미지 프롬프트 1개"
            }}
        }}
        """
        data = call_gemini_text(prompt)
        if not data:
            return None

        # [v17.5] 메타 에이전트: 감성 분석 → 이미지 톤 동기화
        script_text = data.get('blog', {}).get('script', '')
        visual_sync = meta_agent.organic_sync_prompt(script_text)

        # 2. 블로그 이미지 3장 생성 (감성 동기화 톤 적용)
        generated_images = []
        img_prompts = data.get('blog', {}).get('image_prompts', [])
        for i, img_prompt in enumerate(img_prompts[:3]):
            fname = f"img_{timestamp}_{mode_name}_{i+1}.png"
            synced_prompt = f"{img_prompt}. {visual_sync}"  # 감성 톤 주입
            path = generate_image(synced_prompt, fname)
            generated_images.append(path)
            if path:
                print(f"[IMG] {fname} 생성 완료 (감성: {meta_agent.dominant_sentiment})")

        # 3. SNS 타이틀 이미지 1장 생성 (감성 동기화)
        sns_prompt = data.get('sns', {}).get('prompt_image_prompt', '')
        prompt_img_path = None
        if sns_prompt:
            sns_fname = f"prompt_{timestamp}_{mode_name}.png"
            synced_sns = f"{sns_prompt}. {visual_sync}"
            prompt_img_path = generate_image(synced_sns, sns_fname)
            if prompt_img_path:
                print(f"[IMG] SNS {sns_fname} 생성 완료")

        # 결과 조립 (메타 데이터 포함)
        data['blog']['images'] = generated_images
        data['sns']['prompt_image'] = prompt_img_path
        data['meta'] = {
            'sentiment': meta_agent.dominant_sentiment,
            'visual_tone': meta_agent.get_visual_tone(),
            'ai_patterns_blocked': len(meta_agent.detected_issues)
        }
        return data

    hacker = get_bundle("hacker", "츤데레 코치. 팩트 폭행. IT/게임 비유. 단정형 화법.")
    healer = get_bundle("healer", "따뜻한 치유자. ASMR 톤. 감각적 묘사. 미니어처 공방 서사.")

    if not hacker and not healer:
        return jsonify({"status": "error", "message": "AI 생성 실패. 재시도 해주세요."})

    # 자동 저장
    try:
        safe_kw = re.sub(r'\W+', '_', kw)[:15]
        filename = f"visual_{timestamp}_{safe_kw}.json"
        save_data = {"keyword": kw, "hacker": hacker, "healer": healer}
        with open(os.path.join(SAVE_DIR, filename), 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        print(f"[SAVED] {filename}")
    except Exception as e:
        print(f"[SAVE ERROR] {e}")

    return jsonify({"hacker": hacker, "healer": healer})

if __name__ == '__main__':
    app.run(debug=True, port=5000)