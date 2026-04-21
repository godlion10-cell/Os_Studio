from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. 환경 변수 로드 (.env 파일에서 API 키 가져오기)
load_dotenv()

# 2. 제미나이 API 세팅
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("🚨 경고: .env 파일에 GEMINI_API_KEY가 설정되지 않았습니다!")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # 빠르고 똑똑한 최신 모델

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/trends')
def get_trends():
    # [CTO 노트] 다음 단계에서 크롤러로 교체될 임시 데이터
    mock_trends = ["위르겐 클린스만", "토트넘 경기 일정", "국내 힐링 여행지", "비트코인 반감기", "환율 전망"]
    return jsonify({"trends": mock_trends})

@app.route('/api/generate', methods=['POST'])
def generate_post():
    data = request.json
    keyword = data.get('keyword', '테스트 키워드')
    post_type = data.get('type', 'search')

    try:
        # 3. AI에게 내릴 엄격한 지시사항 (프롬프트)
        prompt = f"""
        당신은 네이버 블로그 전문 카피라이터입니다.
        타겟 키워드: '{keyword}'
        글의 성격: '{post_type}' (search: 정보성, home: 감성적/이슈성)

        [절대 규칙]
        1. '안녕하세요', '오늘은' 같은 진부한 인사말은 절대 금지. 주제와 어울리는 서정적이고 공감 가는 시적 문장으로 시작하세요.
        2. 본문 내용 중간에 딱 2번, `[이미지 검색 키워드: 주제와 어울리는 텍스트 없는 고화질 풍경]` 형태의 텍스트 태그를 자연스럽게 삽입하세요. 마크다운 이미지 태그(![])는 절대 쓰지 마세요.
        3. 본문이 끝난 후 맨 아래에 해당 키워드와 연관된 '쿠팡 파트너스 추천 상품 리스트' 2개를 가상의 상품명으로 제안하고, 관련된 해시태그 5개를 추가하세요.
        4. 출력 형식 (매우 중요): 네이버 블로그에 그대로 복사할 수 있도록, 생성된 모든 텍스트를 `<div style="text-align: center; line-height: 2.0; font-size: 16px;">` 태그로 감싸서 순수 HTML 문자열로만 반환하세요.
        5. 절대 마크다운 코드 블록 기호(```html 이나 ```)를 포함하지 마세요.
        """

        # 4. 제미나이에게 원고 요청
        response = model.generate_content(prompt)
        generated_text = response.text

        # 5. [핵심 에러 방어] 제미나이가 실수로 넣은 마크다운 찌꺼기 강제 제거
        cleaned_html = generated_text.replace("```html", "").replace("```", "").strip()

        # 6. 대시보드가 정확히 인식하는 규격(html)으로 포장해서 반환
        return jsonify({
            "status": "success",
            "html": cleaned_html
        })

    except Exception as e:
        # 에러 발생 시 대시보드 화면에 원인 출력
        return jsonify({
            "status": "error",
            "html": f"<div style='color:red; text-align:center;'><p>🚨 AI 원고 생성 중 에러가 발생했습니다.</p><p>{str(e)}</p></div>"
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
