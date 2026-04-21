import os
import json
import re
import time
import requests
import traceback
from flask import Flask, request, jsonify, render_template_string, redirect
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 🛡️ [폴백 체인 준비] 무거운 모델 -> 가벼운 모델 순서
MODELS = ['gemini-1.5-pro', 'gemini-1.5-flash'] 

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ----------------------------------------------------------------
# [FRONT-END] 대시보드 (v4.5와 동일 구조, 상태창 강화)
# ----------------------------------------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Os Studio v5.0 - The One Ring</title>
    <style>
        body { margin: 0; display: flex; font-family: 'Nanum Gothic', sans-serif; background: #f0f2f5; height: 100vh; overflow: hidden; }
        #sidebar { width: 280px; background: #fff; border-right: 1px solid #ddd; padding: 20px; overflow-y: auto; flex-shrink: 0; }
        .trend-item { padding: 10px; cursor: pointer; border-bottom: 1px solid #eee; font-size: 14px; transition: 0.2s; }
        .trend-item:hover { background: #f1f8e9; color: #2db400; font-weight:bold; }
        #main-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        #toolbar { background: #fff; padding: 15px; border-bottom: 1px solid #ddd; display: flex; justify-content: center; gap: 15px; align-items: center; z-index: 10; }
        #content-area { display: flex; flex: 1; overflow-y: auto; padding: 20px; gap: 20px; justify-content: center; }
        #editor-canvas { width: 700px; background: #fff; padding: 50px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); min-height: 1200px; }
        #title-display { font-size: 26px; font-weight: bold; text-align: center; margin-bottom: 30px; border-bottom: 2px solid #eee; padding-bottom: 15px; }
        #editor-body { font-size: 17px; line-height: 2.2; text-align: center; outline: none; color: #333; }
        img { max-width: 100%; border-radius: 12px; margin: 30px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .cliffhanger { background:#111; color:#fff; padding:20px; border-radius:10px; margin-top:40px; text-align:center; font-weight:bold; }
        .cpa-banner { background: linear-gradient(135deg, #ff416c, #ff4b2b); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-top: 20px; cursor: pointer; animation: pulse 2s infinite; text-decoration: none; display: block; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0 rgba(255,65,108,0.7);} 70% {box-shadow: 0 0 0 15px rgba(255,65,108,0);} 100% {box-shadow: 0 0 0 0 rgba(255,65,108,0);} }
        /* 구글 스니펫 스내처 박스 */
        .snippet-box { background: #f8f9fa; border-left: 5px solid #4285f4; padding: 20px; margin-bottom: 30px; text-align: left; }
        #right-panel { width: 400px; display: flex; flex-direction: column; gap: 15px; overflow-y: auto; padding-right: 10px; }
        .info-card { background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #ddd; box-shadow: 0 2px 8px rgba(0,0,0,0.05); font-size: 14px; }
        .card-title { font-weight: bold; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 8px; color: #333; }
        pre { white-space: pre-wrap; font-family: 'Nanum Gothic', sans-serif; background: #f9f9f9; padding: 10px; border-radius: 5px; font-size: 13px; line-height: 1.5; }
        #loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 1000; color: #fff; flex-direction: column; justify-content: center; align-items: center; }
        #log-window { margin-top: 20px; font-family: monospace; color: #0f0; background: #000; padding: 10px; border-radius: 5px; width: 600px; height: 100px; overflow-y: auto; }
    </style>
</head>
<body>
    <div id="loading-overlay">
        <h1 style="color: #2db400;">💍 v5.0 절대 반지 가동 중...</h1>
        <p>방어막 및 공격형 SEO 로직이 활성화되었습니다.</p>
        <div id="log-window">시스템 부팅...</div>
    </div>
    <div id="sidebar"><h2 style="color: #2db400;">Os Radar 📡</h2><div id="search-trends"></div><hr><div id="home-trends"></div></div>
    <div id="main-container">
        <div id="toolbar">
            <select id="mode-select" style="padding: 10px; border-radius: 5px; border: 1px solid #ddd;">
                <option value="naver">Naver (고스트 에디터 ON)</option>
                <option value="blogspot">Blogspot (구글 스니펫 ON)</option>
            </select>
            <input type="text" id="target-keyword" placeholder="키워드 입력" style="width: 300px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
            <button onclick="generateAll()" style="background: #2db400; color: white; border: none; padding: 12px 25px; border-radius: 5px; cursor: pointer; font-weight: bold; font-size: 15px;">💍 v5.0 통합 생성</button>
        </div>
        <div id="content-area">
            <div id="editor-canvas">
                <div id="title-display">제목</div>
                <div id="editor-body" contenteditable="true"><p style="color:#aaa;">대기 중...</p></div>
                <div id="funnel-area"></div>
            </div>
            <div id="right-panel">
                <div class="info-card" id="seo-status"></div>
                <div class="info-card" id="shorts-status"></div>
                <div class="info-card" id="cpa-status"></div>
            </div>
        </div>
    </div>

    <script>
        function logMsg(msg) { 
            const lw = document.getElementById('log-window');
            lw.innerHTML += `<div>> ${msg}</div>`;
            lw.scrollTop = lw.scrollHeight;
        }

        async function loadTrends() {
            const res = await fetch('/api/trends');
            const data = await res.json();
            document.getElementById('search-trends').innerHTML = '<h4>🔍 검색 노출용</h4>' + data.search_trends.map(t => `<div class="trend-item" onclick="setKeyword('${t}')">${t}</div>`).join('');
            document.getElementById('home-trends').innerHTML = '<h4>🏠 홈판 공략용</h4>' + data.home_trends.map(t => `<div class="trend-item" onclick="setKeyword('${t}')">${t}</div>`).join('');
        }
        function setKeyword(k) { document.getElementById('target-keyword').value = k; }

        async function generateAll() {
            const kw = document.getElementById('target-keyword').value;
            const mode = document.getElementById('mode-select').value;
            if(!kw) return;
            document.getElementById('loading-overlay').style.display = 'flex';
            document.getElementById('log-window').innerHTML = '';
            logMsg(`엔진 시작: '${kw}'`);
            
            try {
                const res = await fetch('/api/generate-full', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ keyword: kw, mode: mode })
                });
                const data = await res.json();

                if(data.status === "success") {
                    document.getElementById('title-display').innerHTML = data.title;
                    document.getElementById('editor-body').innerHTML = data.html;
                    
                    // CPA 배너에 클로킹된 링크 적용
                    document.getElementById('funnel-area').innerHTML = `
                        <div class="cliffhanger">🔒 ${data.cliffhanger}</div>
                        <a href="${data.cloaked_cpa_link}" target="_blank" class="cpa-banner">
                            <h3 style="margin:0 0 10px 0;">🚨 [마감 임박]</h3>
                            <div style="font-size:18px; font-weight:bold;">${data.cpa_banner}</div>
                        </a>`;

                    document.getElementById('seo-status').innerHTML = `<div class="card-title">🔥 SEO & 알고리즘 팩</div>
                        <strong># 키워드 밀도:</strong> ${data.keyword_density}% (자동 패치 완료)<br>
                        <strong># 해시태그:</strong> ${data.seo_tags.join(' ')}<br>
                        <strong># 릴스 DM유도:</strong> <pre>${data.insta_caption}</pre>`;
                    document.getElementById('shorts-status').innerHTML = `<div class="card-title">📱 숏폼 대본 & CF 프롬프트</div>
                        <pre>${data.shorts_script}</pre>
                        <div style="font-size:12px; color:#666;">${data.img_prompts.join('<br><br>')}</div>`;
                    
                    document.querySelectorAll('#editor-body img').forEach(img => { img.src = img.src.split('?')[0] + "?t=" + new Date().getTime(); });
                } else { alert("에러: " + data.message); }
            } catch(e) { alert("통신 실패!"); }
            finally { document.getElementById('loading-overlay').style.display = 'none'; }
        }
        window.onload = loadTrends;
    </script>
</body>
</html>
"""

# ----------------------------------------------------------------
# [BACK-END] 절대반지 로직: 방어막 + 공격형 무기
# ----------------------------------------------------------------

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/trends')
def get_trends():
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content("대한민국 핫트렌드 20개를 검색용 10개, 홈판용 10개로 나누어 JSON {search_trends:[], home_trends:[]} 으로 반환.")
        return jsonify(json.loads(re.search(r'\{.*\}', res.text, re.DOTALL).group()))
    except:
        return jsonify({"search_trends": ["점검중"], "home_trends": ["점검중"]})

# ⚔️ [공격 2] CPA 링크 클로킹 라우터 (저품질 회피)
@app.route('/go')
def redirect_cpa():
    target = request.args.get('target', 'https://www.coupang.com')
    # 내부 서버를 거쳐서 외부로 튕겨냅니다. 블로그 봇은 단순 내부 링크로 인식.
    return redirect(target)

@app.route('/api/generate-full', methods=['POST'])
def generate_full():
    data = request.get_json()
    keyword = data.get('keyword')
    mode = data.get('mode', 'naver')

    prompt = f"""
    주제: '{keyword}'
    [작성 규칙]
    1. html: {'네이버 감성의 구어체' if mode=='naver' else '구글 검색 1위 탈환을 위한 전문적 SEO 문서'}. 
       - 중간에 '지원금', '환급', '대출' 등 고단가 광고 유발 단어 삽입.
       - 서로 다른 위치에 [IMG_1], [IMG_2] 삽입 필수.
       - 최상단에 구글 피처드 스니펫을 노리는 <div class="snippet-box"><h3>💡 핵심 요약 Q&A</h3><ul><li>...</li></ul></div> 를 반드시 포함할 것!
    2. shorts_script: 60초 숏폼 대본 (시각 지시문 포함).
    3. cliffhanger & cpa_banner 작성.
    4. seo_tags (5개) & insta_caption (DM 유도 멘트).
    5. img_prompts: CF 감독 수준의 수직형(9:16) 실사 이미지 프롬프트 2개 (영어).
    
    반드시 JSON으로 반환: {{"title":"", "html":"", "shorts_script":"", "cliffhanger":"", "cpa_banner":"", "seo_tags":[], "insta_caption":"", "img_prompts":[]}}
    """

    content = None
    
    # 🛡️ [방어 3 & 1] 폴백 체인 (Pro -> Flash) 및 길이 검증
    for model_name in MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            content = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
            
            # 🛡️ [방어 1] 원고 길이가 너무 짧으면 (예: 500자 이하) 'Auto-Expand' 발동
            if len(content['html']) < 500:
                print(f"⚠️ 원고가 짧습니다. {model_name} 로 늘리기 작업(Auto-Expand) 수행 중...")
                expand_prompt = f"다음 HTML 문서의 끝부분에, '{keyword}'와 관련된 '자주 묻는 질문(FAQ)' 3가지를 추가해서 분량을 늘려줘. 기존 HTML 전체와 합쳐서 JSON {{\"html\":\"...\"}} 으로만 반환해.\n\n{content['html']}"
                res_expand = model.generate_content(expand_prompt)
                expanded_data = json.loads(re.search(r'\{.*\}', res_expand.text, re.DOTALL).group())
                content['html'] = expanded_data['html']
                
            break # 성공 시 폴백 체인 탈출
        except Exception as e:
            print(f"🚨 {model_name} 실패: {e}. 다음 모델로 넘어갑니다.")
            continue
            
    if not content:
        return jsonify({"status": "error", "message": "모든 엔진이 과부하 상태입니다. 잠시 후 시도하세요."}), 500

    # ⚔️ [공격 3] The Ghost Editor (자가 검열 로직)
    if mode == 'naver':
        # 기계적인 단어를 인간미 넘치는 단어로 쾌속 치환
        ghost_dict = {
            "결론적으로": "아무튼 팩트를 말씀드리면",
            "요약하자면": "솔직히 딱 정리해보면",
            "이처럼": "진짜 보신 것처럼",
            "할 수 있습니다": "할 수 있더라고요!",
            "중요합니다": "진짜 중요해요. (별표 백개!)"
        }
        for ai_word, human_word in ghost_dict.items():
            content['html'] = content['html'].replace(ai_word, human_word)

    # ⚔️ [공격 1] SEO 키워드 밀도 (Density) 패치
    word_count = len(re.sub(r'<[^>]+>', '', content['html'])) # 태그 제외 글자수
    kw_count = content['html'].count(keyword)
    density = (kw_count / word_count * 100) if word_count > 0 else 0
    
    if density < 3.0: # 밀도가 3% 미만이면 강제 주입
        patch_text = f"<br><div style='color:#f0f2f5; font-size:1px;'>{keyword} " * int((word_count * 0.03) - kw_count) + "</div>"
        content['html'] += patch_text # 독자 눈에는 안 보이고(배경색) 로봇만 읽는 히든 텍스트 주입

    # 🛡️ [방어 2] 이미지 생성 및 실패 시 Smart Fallback Box 삽입
    generated_images = []
    for i, img_p in enumerate(content.get('img_prompts', [])):
        filename = f"os_v5_{int(time.time())}_{i}.jpg"
        save_path = os.path.join(IMAGE_FOLDER, filename)
        url = f"https://pollinations.ai/p/{requests.utils.quote(img_p)}?width=768&height=1024&model=flux&nologo=true"
        
        try:
            img_r = requests.get(url, timeout=20)
            if img_r.status_code == 200 and len(img_r.content) > 1024:
                with open(save_path, 'wb') as f:
                    f.write(img_r.content)
                generated_images.append(f"/static/images/{filename}")
            else: raise Exception("Invalid Image")
        except Exception as e:
            # 실패 시 엑스박스 대신 '광고 배너'로 빈칸 채우기 (스마트 폴백)
            placeholder = f'<a href="/go?target=https://coupa.ng/YOUR_LINK" style="display:block; background:#fff3e0; padding:30px; text-align:center; border:2px dashed #ffb74d; border-radius:10px; color:#e65100; text-decoration:none; margin:30px 0;">🎁 <strong>{keyword}</strong> 관련 시크릿 특가 확인하기 (클릭)</a>'
            generated_images.append(placeholder)

    # HTML 내 [IMG_1] 교체
    final_html = content['html']
    for i, img_data in enumerate(generated_images):
        if img_data.startswith('<a '): # 플레이스홀더인 경우
            final_html = final_html.replace(f"[IMG_{i+1}]", img_data)
        else: # 정상 이미지인 경우
            final_html = final_html.replace(f"[IMG_{i+1}]", f'<img src="{img_data}">')

    # 클로킹 된 CPA 링크 생성
    cloaked_link = "/go?target=https://link.coupang.com/a/YOUR_CPA_LINK"

    return jsonify({
        "status": "success",
        "title": content['title'],
        "html": final_html,
        "cliffhanger": content['cliffhanger'],
        "cpa_banner": content['cpa_banner'],
        "cloaked_cpa_link": cloaked_link,
        "seo_tags": content['seo_tags'],
        "insta_caption": content['insta_caption'],
        "shorts_script": content['shorts_script'],
        "img_prompts": content['img_prompts'],
        "keyword_density": round(density, 1)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)