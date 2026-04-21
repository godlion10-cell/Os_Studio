from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
import json
import re
import time
import datetime
import requests
from dotenv import load_dotenv

# 1. 환경 변수 로드
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2. 제미나이 통합 엔진 세팅
genai.configure(api_key=GEMINI_API_KEY)
text_model = genai.GenerativeModel('gemini-2.5-flash')

# 3. 절대경로로 이미지 저장 폴더 확보
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, 'static', 'images')
os.makedirs(IMG_DIR, exist_ok=True)
print(f"[IMG_DIR] {IMG_DIR}")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# 📡 실시간 트렌드 레이더
@app.route('/api/trends')
def get_trends():
    try:
        today = datetime.datetime.now().strftime("%Y년 %m월 %d일")
        prompt = f"""
        오늘은 {today}입니다. 이 날짜를 기준으로 한국 실시간 트렌드 20개를 분석하세요.
        검색용(Search) 10개, 홈판용(Home) 10개로 나누어 JSON 형식으로만 답변하세요.
        {{
            "search_trends": ["키워드1","키워드2","키워드3","키워드4","키워드5","키워드6","키워드7","키워드8","키워드9","키워드10"],
            "home_trends": ["키워드1","키워드2","키워드3","키워드4","키워드5","키워드6","키워드7","키워드8","키워드9","키워드10"]
        }}
        """
        response = text_model.generate_content(prompt)
        json_data = json.loads(re.search(r'\{.*\}', response.text, re.DOTALL).group())
        return jsonify(json_data)
    except Exception as e:
        print(f"⚠️ 트렌드 로드 실패 (더미 데이터 사용): {e}")
        return jsonify({
            "search_trends": ["환율 전망", "벚꽃 개화시기", "신축 아파트 청약", "아이폰 17 루머", "오늘의 날씨", "주식 시장", "봄 여행지 추천", "건강 검진 예약", "전기차 보조금", "대학 입시 일정"],
            "home_trends": ["직장인 부업 성공기", "연예인 단골 맛집", "주식 폭락 대비책", "봄철 피부 관리법", "인생 영화 추천", "다이어트 식단", "요즘 뜨는 카페", "자동차 할부 꿀팁", "여행 숙소 비교", "재테크 실패담"]
        })

# ✍️ & 🎨 [통합 엔진] 네이버 에디터 원고 + 실사 이미지 다운로드 저장
@app.route('/api/generate-full', methods=['POST'])
def generate_full():
    data = request.json
    keyword = data.get('keyword', '테스트')
    print(f"\n{'='*50}")
    print(f"🚀 원고 생성 시작! 키워드: [{keyword}]")
    print(f"{'='*50}")

    try:
        # 1단계: 제미나이가 원고 + 이미지 프롬프트 동시 생성
        text_prompt = f"""
        주제: '{keyword}'
        
        [작성 지시]
        - 제목(title): 주제에 어울리는 아이콘(🌿, 🏠, 💰, 💡, ✨ 등 중 선택)을 앞에 붙이고, 폰트는 크게.
        - 네이버 블로그 HTML 형식으로 작성. (전체를 <div style="text-align:center; line-height:2.2; font-size:16px;">로 감싸세요.)
        - 절대로 '안녕하세요', '오늘은'으로 시작하지 마세요. 서정적이고 시적인 문장으로 시작하세요.
        - 원고 중간 자연스러운 위치에 [IMG_1], [IMG_2] 표시를 넣으세요.
        - 각 이미지 위치에 맞는 상세 영문 이미지 프롬프트를 작성하세요. (Photorealistic, 8K, Cinematic Lighting, NO TEXT, NO NUMBERS 필수)
        - 하단에 쿠팡 파트너스 추천 상품 2개와 해시태그 5개를 반드시 추가하세요.
        
        [출력 형식]: 순수 JSON만 출력하세요. 마크다운 기호(```json)는 절대 금지.
        {{
            "title": "아이콘 + 크고 기억에 남는 블로그 제목",
            "html": "전체 HTML 원고...",
            "img_prompts": ["이미지1 영문 프롬프트", "이미지2 영문 프롬프트"]
        }}
        """
        print("✏️  제미나이 원고 생성 중...")
        text_res = text_model.generate_content(text_prompt)
        raw = re.search(r'\{.*\}', text_res.text, re.DOTALL).group()
        content = json.loads(raw)
        print(f"✅ 원고 생성 완료! 제목: {content.get('title', '(제목 없음)')}")

        # 2단계: Pollinations.ai로 이미지 다운로드 → 이중 검증 후 로컬 저장
        generated_image_paths = []
        img_prompts = content.get('img_prompts', [])
        print(f"🎨 이미지 {len(img_prompts)}개 생성 시작...")

        for i, prompt in enumerate(img_prompts):
            image_filename = f"os_{int(time.time())}_{i}.jpg"
            image_path = os.path.join(IMG_DIR, image_filename)

            try:
                encoded_prompt = requests.utils.quote(
                    f"photorealistic, high quality, NO TEXT, NO NUMBERS, NO WATERMARK: {prompt}"
                )
                download_url = (
                    f"https://pollinations.ai/p/{encoded_prompt}"
                    f"?width=1024&height=576&model=flux&nologo=true&seed={int(time.time())+i}"
                )
                print(f"   [{i+1}/{len(img_prompts)}] 다운로드 중...")

                r = requests.get(download_url, timeout=30)

                # ✅ 이중 검증: HTTP 200 + 최소 1KB 이상이어야 정상 이미지
                if r.status_code == 200 and len(r.content) > 1024:
                    with open(image_path, 'wb') as f:
                        f.write(r.content)
                    print(f"   ✅ 이미지 저장 성공! 경로: {image_path} ({len(r.content)//1024}KB)")
                    generated_image_paths.append(f"/static/images/{image_filename}")
                else:
                    print(f"   🚨 다운로드 실패 또는 파일 깨짐 (Status: {r.status_code}, Size: {len(r.content)}bytes)")

            except Exception as e:
                print(f"   🚨 이미지 [{i+1}] 에러: {str(e)}")

        # 3단계: [IMG_N]을 div로 감싼 이미지 태그로 교체 (가운데 정렬 강제)
        final_html = content.get('html', '')
        for i, img_url in enumerate(generated_image_paths):
            img_tag = f"""
            <div style="text-align: center; margin: 40px 0;">
                <img src="{img_url}?v={int(time.time())}" style="max-width: 100%; width: 680px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: block; margin: 0 auto;">
                <p style="color: #aaa; font-size: 0.85em; margin-top: 10px;">[AI가 생성한 이미지입니다]</p>
            </div>
            """
            final_html = final_html.replace(f"[IMG_{i+1}]", img_tag)

        # 4단계: 전체 원고를 가운데 정렬 div로 감싸서 반환
        wrapped_html = f'<div style="text-align: center; line-height: 2.4; font-size: 1.1em;">{final_html}</div>'

        print(f"🏁 완료! 저장된 이미지 수: {len(generated_image_paths)}/{len(img_prompts)}")
        print(f"{'='*50}\n")

        return jsonify({
            "status": "success",
            "title": content.get('title', keyword),
            "html": wrapped_html
        })

    except Exception as e:
        print(f"🚨 치명적 에러 발생: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
