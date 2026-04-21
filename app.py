from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
import json
import re
import datetime
import requests
from dotenv import load_dotenv

# 1. 환경 변수 로드 (오직 구글 API 키 하나면 끝납니다!)
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2. 제미나이 통합 엔진 세팅
genai.configure(api_key=GEMINI_API_KEY)

# 텍스트 작가 모델 (원고 생성)
text_model = genai.GenerativeModel('gemini-2.5-flash')

# 이미지 예술가 모델 (Imagen 3) - ImageGenerationModel로 별도 세팅
image_model = genai.ImageGenerationModel('imagen-3.0-generate-001')

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# 📡 실시간 트렌드 레이더 (검색용/홈판용 10개씩)
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
        # 에러 발생 시 비상용 더미 데이터
        return jsonify({
            "search_trends": ["환율 전망", "벚꽃 개화시기", "신축 아파트 청약", "아이폰 17 루머", "오늘의 날씨", "주식 시장", "봄 여행지 추천", "건강 검진 예약", "전기차 보조금", "대학 입시 일정"],
            "home_trends": ["직장인 부업 성공기", "연예인 단골 맛집", "주식 폭락 대비책", "봄철 피부 관리법", "인생 영화 추천", "다이어트 식단", "요즘 뜨는 카페", "자동차 할부 꿀팁", "여행 숙소 비교", "재테크 실패담"]
        })

# ✍️ & 🎨 [통합 엔진] 네이버 에디터 원고 + 제미나이 실사 이미지 생성
@app.route('/api/generate-full', methods=['POST'])
def generate_full():
    data = request.json
    keyword = data.get('keyword', '테스트 키워드')

    try:
        # 1단계: 제미나이가 원고와 '정밀 이미지 프롬프트'를 동시 생성
        text_prompt = f"""
        주제: '{keyword}'
        
        [작성 지시]
        - 네이버 블로그 HTML 형식으로 작성. (<div style="text-align:center; line-height:2.2;">로 전체를 감싸세요.)
        - 절대로 '안녕하세요', '오늘은'으로 시작하지 마세요. 서정적이고 시적인 문장으로 시작하세요.
        - 원고 중간 자연스러운 위치에 [IMG_1], [IMG_2] 표시를 넣으세요.
        - 각 이미지 위치에 맞는 정밀 실사 이미지 프롬프트를 영문으로 작성하세요.
          (규칙: Photorealistic, 8K, Cinematic Lighting, NO TEXT, NO NUMBERS 필수 포함)
        - 하단에 쿠팡 파트너스 추천 상품 2개와 해시태그 5개를 반드시 추가하세요.
        
        [출력 형식]: 순수 JSON만 출력하세요. 마크다운 기호(```json)는 절대 금지.
        {{
            "title": "블로그 제목",
            "html": "전체 HTML 원고...",
            "img_prompts": ["이미지1 영문 프롬프트", "이미지2 영문 프롬프트"]
        }}
        """
        text_res = text_model.generate_content(text_prompt)
        raw = re.search(r'\{.*\}', text_res.text, re.DOTALL).group()
        content = json.loads(raw)

        # 2단계: 이미지 생성 (Imagen 3 시도 → 실패 시 무료 엔진 자동 전환)
        generated_images = []
        os.makedirs('static/images', exist_ok=True)

        for i, img_prompt in enumerate(content.get('img_prompts', [])):
            final_prompt = f"Photorealistic, 8K resolution, cinematic lighting, NO TEXT, NO NUMBERS, NO WATERMARK: {img_prompt}"
            image_filename = f"gen_{i+1}_{re.sub(r'[^a-zA-Z0-9가-힣]', '_', keyword)[:20]}.png"
            image_path = os.path.join('static', 'images', image_filename)

            imagen_success = False
            try:
                # 🥇 1순위: Imagen 3 (Google Cloud 유료 계정 환경에서 작동)
                img_response = image_model.generate_images(
                    prompt=final_prompt,
                    number_of_images=1,
                    safety_filter_level="block_only_high",
                    person_generation="allow_adult"
                )
                img_response.images[0].save(image_path)
                generated_images.append(f"/static/images/{image_filename}")
                imagen_success = True
            except Exception:
                pass  # Imagen 실패 시 무료 엔진으로 폴백

            if not imagen_success:
                # 🥈 2순위: Pollinations.ai 무료 실사 이미지 (API 키 불필요)
                pollinations_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(final_prompt)}?width=1024&height=576&model=flux&nologo=true&enhance=true"
                generated_images.append(pollinations_url)

        # 3단계: 원고 내 [IMG_N] placeholder를 실제 이미지 태그로 교체
        final_html = content.get('html', '')
        for i, url in enumerate(generated_images):
            final_html = final_html.replace(
                f"[IMG_{i+1}]",
                f'<img src="{url}" style="max-width:100%; border-radius:12px; margin:20px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">'
            )

        return jsonify({
            "status": "success",
            "title": content.get('title', ''),
            "html": final_html
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == '__main__':
    os.makedirs('static/images', exist_ok=True)
    app.run(debug=True, port=5000)
