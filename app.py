from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. 환경 변수 무시하고 직접 키 꽂아넣기
# load_dotenv() # <--- 이 줄은 지우거나 앞에 #을 붙여주세요.
GEMINI_API_KEY = "AIzaSyACB4--EZm5cXBF6bI56z7GFDLfR3ecvhY"

# 2. 최신 제미나이 2.5 엔진 세팅
# 사장님 계정에서 확인된 최신 모델명을 정확히 타격합니다.
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash') 

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/trends')
def get_trends():
    # 현재는 샘플 데이터, 추후 크롤러 연결 예정
    mock_trends = ["위르겐 클린스만", "토트넘 경기 일정", "국내 힐링 여행지", "비트코인 반감기", "환율 전망"]
    return jsonify({"trends": mock_trends})

@app.route('/api/generate', methods=['POST'])
def generate_post():
    data = request.json
    keyword = data.get('keyword', '테스트 키워드')
    post_type = data.get('type', 'search')

    try:
        # 3. 사장님의 '오스(Os)' 스타일 전용 프롬프트
        prompt = f"""
        당신은 네이버 블로그 전문 카피라이터이며, '오스 스튜디오'의 수석 작가입니다.
        주제 키워드: '{keyword}'
        원고 성향: '{post_type}'

        [작성 규칙]
        1. 오프닝: 절대로 '안녕하세요', '오늘'로 시작하지 마십시오. 
           주제와 관련된 서정적이고 철학적인, 혹은 독자의 공감을 즉각 자극하는 시적인 한 문장으로 시작하세요.
        2. 이미지 가이드: 본문 중간에 `[이미지 검색 키워드: 주제와 관련된 텍스트 없는 감성적인 풍경]` 태그를 자연스럽게 2회 삽입하세요.
        3. 수익화 로직: 글 하단에 해당 주제와 어울리는 '쿠팡 파트너스 추천 상품' 2개와 관련 해시태그 5개를 반드시 포함하세요.
        4. 출력 형식: 네이버 블로그 가운데 정렬에 최적화되도록 모든 내용을 <div style="text-align: center; line-height: 2.2;"> 태그로 감싸서 HTML로 출력하세요.
        5. 주의: ```html 같은 마크다운 코드 블록 기호는 절대 넣지 말고 순수 HTML 태그와 텍스트만 출력하세요.
        """

        # 4. 최신 엔진으로 원고 생성
        response = model.generate_content(prompt)
        raw_content = response.text

        # 5. [강력한 세탁 로직] 마크다운 잔재 및 불필요한 기호 제거
        clean_content = raw_content.replace("```html", "").replace("```", "").strip()

        return jsonify({
            "status": "success",
            "html": clean_content
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "html": f"<div style='color:red; padding:20px;'>🚨 AI 엔진 가동 중 오류 발생: {str(e)}</div>"
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
