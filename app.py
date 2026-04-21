import os
import json
import re
import time
import requests
import traceback
from flask import Flask, request, jsonify, render_template_string, redirect
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 시스템 설정
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 서버 과부하 방어용 모델 체인
MODELS = ['gemini-1.5-pro', 'gemini-1.5-flash'] 

app = Flask(__name__)

# 이미지 저장소 확보
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ----------------------------------------------------------------
# [FRONT-END] UI: v5.1 통합 대시보드
# ----------------------------------------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Os Studio v5.1 MASTER - Naver/Google Profit Machine</title>
    <style>
        body { margin: 0; display: flex; font-family: 'Nanum Gothic', sans-serif; background: #f0f2f5; height: 100vh; overflow: hidden; }
        #sidebar { width: 280px; background: #fff; border-right: 1px solid #ddd; padding: 20px; overflow-y: auto; flex-shrink: 0; }
        .trend-item { padding: 10px; cursor: pointer; border-bottom: 1px solid #eee; font-size: 14px; transition: 0.2s; }
        .trend-item:hover { background: #f1f8e9; color: #2db400; font-weight:bold; }
        
        #main-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        #toolbar { background: #fff; padding: 15px; border-bottom: 1px solid #ddd; display: flex; justify-content: center; gap: 15px; align-items: center; }
        
        #content-area { display: flex; flex: 1; overflow-y: auto; padding: 20px; gap: 20px; justify-content: center; }
        #editor-canvas { width: 700px; background: #fff; padding: 50px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); min-height: 1200px; }
        
        #title-display { font-size: 26px; font-weight: bold; text-align: center; margin-bottom: 30px; border-bottom: 2px solid #eee; padding-bottom: 15px; }
        #editor-body { font-size: 17px; line-height: 2.2; text-align: center; outline: none; color: #333; }
        img { max-width: 100%; border-radius: 12px; margin: 30px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        
        .cliffhanger { background:#111; color:#fff; padding:20px; border-radius:10px; margin-top:40px; text-align:center; font-weight:bold; }
        .cpa-banner { background: linear-gradient(135deg, #ff416c, #ff4b2b); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-top: 20px; cursor: pointer; animation: pulse 2s infinite; text-decoration: none; display: block; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0 rgba(255, 65, 108, 0.7);} 70% {box-shadow: 0 0 0 15px rgba(255, 65, 108, 0);} 100% {box-shadow: 0 0 0 0 rgba(255, 65, 108, 0);} }
        
        #right-panel { width: 380px; display: flex; flex-direction: column; gap: 15px; overflow-y: auto; }
        .info-card { background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #ddd; font-size: 14px; }
        .card-title { font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; color: #333; }
        pre { white-space: pre-wrap; background: #f9f9f9; padding: 10px; border-radius: 5px; font-size: 12px; line-height: 1.6; }
        
        #loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 1000; color: #fff; flex-direction: column; justify-content: center; align-items: center; }
    </style>
</head>
<body>
    <div id="loading-overlay">
        <h1 style="color: #2db400;">🔥 Os 엔진 풀가동 중...</h1>
        <p>A급 원고, 쇼츠 대본, 이미지, 수익 펀넬을 동시 추출 중입니다.</p>
    </div>

    <div id="sidebar">
        <h2 style="color: #2db400;">Os Radar 📡</h2>
        <div id="search-trends">트렌드 로딩 중...</div>
        <hr>
        <div id="home-trends"></div>
    </div>

    <div id="main-container">
        <div id="toolbar">
            <select id="mode-select" style="padding: 10px; border-radius: 5px;">
                <option value="naver">Naver (감성/반자동)</option>
                <option value="blogspot">Blogspot (구글/자동)</option>
            </select>
            <input type="text" id="target-keyword" placeholder="키워드 입력" style="width: 300px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
            <button onclick="generateAll()" style="background: #2db400; color: white; border: none; padding: 12px 25px; border-radius: 5px; cursor: pointer; font-weight: bold;">💎 통합 수익화 생성</button>
        </div>

        <div id="content-area">
            <div id="editor-canvas">
                <div id="title-display">제목</div>
                <div id="editor-body" contenteditable="true">원고가 여기에 생성됩니다.</div>
                <div id="funnel-area"></div>
            </div>

            <div id="right-panel">
                <div class="info-card" style="background: #e3f2fd;">
                    <div class="card-title">📈 수익 예측 리포트</div>
                    <div id="stats-info">대기 중...</div>
                </div>
                <div class="info-card">
                    <div class="card-title">📱 쇼츠/릴스 대본</div>
                    <pre id="shorts-display"></pre>
                </div>
                <div class="info-card">
                    <div class="card-title">🎥 CF급 영상 프롬프트</div>
                    <div id="image-prompts-display" style="font-size: 11px;"></div>
                </div>
                <div class="info-card" style="background: #f3e5f5;">
                    <div class="card-title">🔥 알고리즘 팩</div>
                    <div id="seo-tags" style="font-weight:bold; color:#8e24aa;"></div>
                    <pre id="insta-caption" style="margin-top:10px;"></pre>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function loadTrends() {
            try {
                const res = await fetch('/api/trends');
                const data = await res.json();
                document.getElementById('search-trends').innerHTML = '<h4>🔍 검색용</h4>' + data.search_trends.map(t => `<div class="trend-item" onclick="setKeyword('${t}')">${t}</div>`).join('');
                document.getElementById('home-trends').innerHTML = '<h4>🏠 홈판용</h4>' + data.home_trends.map(t => `<div class="trend-item" onclick="setKeyword('${t}')">${t}</div>`).join('');
            } catch(e) { document.getElementById('search-trends').innerText = "로딩 실패 (F5를 눌러주세요)"; }
        }
        function setKeyword(k) { document.getElementById('target-keyword').value = k; }

        async function generateAll() {
            const kw = document.getElementById('target-keyword').value;
            const mode = document.getElementById('mode-select').value;
            if(!kw) return alert("키워드를 입력해주세요.");

            document.getElementById('loading-overlay').style.display = 'flex';
            
            try {
                const res = await fetch('/api/generate-full', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ keyword: kw, mode: mode })
                });
                const data = await res.json();

                if(data.status === "success") {
                    document.getElementById('title-display').innerText = data.title;
                    document.getElementById('editor-body').innerHTML = data.html;
                    
                    document.getElementById('funnel-area').innerHTML = `
                        <div class="cliffhanger">🔒 [비공개] ${data.cliffhanger}</div>
                        <a href="${data.cloaked_cpa_link}" target="_blank" class="cpa-banner">
                            <h3>🚨 [마감임박] ${data.cpa_banner}</h3>
                        </a>`;

                    document.getElementById('stats-info').innerHTML = `✅ 예상 조회수: <strong>${data.stats.views.toLocaleString()}회</strong><br>💰 예상 수익: <strong>${data.stats.revenue.toLocaleString()}원</strong>`;
                    document.getElementById('shorts-display').innerText = data.shorts_script;
                    document.getElementById('seo-tags').innerText = data.seo_tags.join(' ');
                    document.getElementById('insta-caption').innerText = data.insta_caption;
                    document.getElementById('image-prompts-display').innerHTML = data.img_prompts.map(p => `<p>🎬 ${p}</p>`).join('');

                    document.querySelectorAll('#editor-body img').forEach(img => img.src = img.src + "?v=" + Date.now());
                } else { alert("에러: " + data.message); }
            } catch(e) { alert("서버 통신 실패"); }
            finally { document.getElementById('loading-overlay').style.display = 'none'; }
        }
        window.onload = loadTrends;
    </script>
</body>
</html>
"""

# ----------------------------------------------------------------
# [BACK-END] 핵심 로직 (에러 방어막 및 수익화 이식)
# ----------------------------------------------------------------

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# ⚔️ [픽스 1] 트렌드 JSON 강제화 (점검중 해결)
@app.route('/api/trends')
def get_trends():
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # JSON 모드 강제 설정
        res = model.generate_content(
            "대한민국 핫트렌드 20개를 검색용 10개, 홈판용 10개로 나누어 JSON으로만 답해. {search_trends:[], home_trends:[]}",
            generation_config={"response_mime_type": "application/json"}
        )
        return jsonify(json.loads(res.text))
    except Exception as e:
        print(f"🚨 트렌드 에러: {e}")
        return jsonify({"search_trends": ["새로고침 요망"], "home_trends": ["점검중"]})

# ⚔️ [픽스 2] CPA 클로킹 링크 (저품질 회피)
@app.route('/go')
def redirect_cpa():
    target = request.args.get('target', 'https://www.coupang.com')
    return redirect(target)

@app.route('/api/generate-full', methods=['POST'])
def generate_full():
    data = request.get_json()
    keyword = data.get('keyword')
    mode = data.get('mode', 'naver')

    prompt = f"""
    당신은 A급 마케터이자 CF 영상 감독입니다.
    주제: '{keyword}'
    [작성 규칙]
    1. html: {'네이버 감성, 가운데 정렬' if mode=='naver' else '구글 SEO, 좌측 정렬'}. 본문 중간에 '환급', '대출', '지원금' 등 고단가 키워드로 문맥을 자연스럽게 전환할 것. [IMG_1], [IMG_2] 포함.
    2. shorts_script: 60초 분량, 시각/청각 지시문 포함.
    3. cliffhanger & cpa_banner: 독자를 미치게 만드는 카피라이팅 적용.
    4. stats: 조회수와 고단가 수익 예측.
    5. img_prompts: 영어로 작성된 CF 수준의 세로형(9:16) 실사 프롬프트 2개.
    6. seo_tags & insta_caption: 인스타 DM 유도 멘트 포함.
    반드시 JSON으로 응답: {{"title":"", "html":"", "shorts_script":"", "cliffhanger":"", "cpa_banner":"", "stats":{{"views":0, "revenue":0}}, "seo_tags":[], "insta_caption":"", "img_prompts":[]}}
    """

    content = None
    for model_name in MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            res = model.generate_content(prompt)
            content = json.loads(re.search(r'\{.*\}', res.text, re.DOTALL).group())
            
            if len(content.get('html', '')) < 600:
                print("⚠️ 원고가 짧아 FAQ 추가 중...")
                expand_res = model.generate_content(f"다음 HTML 끝에 '{keyword}' 관련 FAQ 3개를 추가해줘.\n{content.get('html', '')}")
                content['html'] = expand_res.text
            break
        except Exception as e:
            print(f"🚨 {model_name} 실패: {e}")
            continue

    if not content:
        # 서버에서 명확하게 JSON 에러를 내려줌
        return jsonify({"status": "error", "message": "구글 서버 과부하. 10초 뒤에 다시 눌러주세요!"}), 500

    try:
        # 🛡️ 융통성 패치 적용: 데이터가 누락되어도 .get()으로 에러 원천 차단
        final_html = content.get('html', '<p>본문 생성 실패</p>')

        if mode == 'naver':
            ghost_dict = {"요약하자면": "솔직히 정리해보면", "결론적으로": "아무튼 팩트는", "중요합니다": "진짜 중요해요!"}
            for k, v in ghost_dict.items():
                final_html = final_html.replace(k, v)

        generated_images = []
        for i, img_p in enumerate(content.get('img_prompts', [])):
            filename = f"os_v51_{int(time.time())}_{i}.jpg"
            save_path = os.path.join(IMAGE_FOLDER, filename)
            url = f"https://pollinations.ai/p/{requests.utils.quote(img_p)}?width=768&height=1024&model=flux&nologo=true"
            
            try:
                img_r = requests.get(url, timeout=30)
                if img_r.status_code == 200 and 'image' in img_r.headers.get('Content-Type', ''):
                    with open(save_path, 'wb') as f:
                        f.write(img_r.content)
                    generated_images.append(f"/static/images/{filename}")
                else: raise Exception("Invalid Content")
            except:
                placeholder = f'<div style="background:#fff3e0; padding:30px; border:2px dashed #ffb74d; border-radius:10px; color:#e65100; margin:30px 0;">🎁 [한정특가] {keyword} 관련 시크릿 혜택 확인하기</div>'
                generated_images.append(placeholder)

        for i, img_data in enumerate(generated_images):
            tag = f'<img src="{img_data}">' if img_data.startswith('/static') else img_data
            final_html = final_html.replace(f"[IMG_{i+1}]", tag)

        cloaked_link = f"/go?target=https://link.coupang.com/a/YOUR_ID"

        # 🛡️ 안전하게 JSON 반환 (KeyError 완전 박멸)
        return jsonify({
            "status": "success",
            "title": content.get('title', '제목을 불러오지 못했습니다'),
            "html": final_html,
            "cliffhanger": content.get('cliffhanger', '비공개 정보는 다음 글에서...'),
            "cpa_banner": content.get('cpa_banner', '클릭해서 혜택을 확인하세요!'),
            "shorts_script": content.get('shorts_script', '쇼츠 대본 생성 중 오류 발생'),
            "stats": content.get('stats', {"views": 0, "revenue": 0}),
            "seo_tags": content.get('seo_tags', ['#트렌드', '#추천']),
            "insta_caption": content.get('insta_caption', '프로필 링크를 확인해주세요!'),
            "img_prompts": content.get('img_prompts', []),
            "cloaked_cpa_link": cloaked_link
        })
    
    except Exception as e:
        print(f"🚨 파이썬 내부 조립 에러: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": "데이터 조립 중 서버 에러가 발생했습니다."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)