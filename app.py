from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/trends')
def get_trends():
    # [Phase 1 임시 데이터] 나중에 크롤러 모듈로 교체할 것
    mock_trends = ["위르겐 클린스만", "토트넘 경기 일정", "국내 힐링 여행지", "비트코인 반감기", "환율 전망"]
    return jsonify({"trends": mock_trends})

@app.route('/api/generate', methods=['POST'])
def generate_post():
    data = request.json
    keyword = data.get('keyword', '테스트 키워드')
    post_type = data.get('type', 'search')
    
    # [네이버 블로그 스타일 강제 렌더링 템플릿]
    html_content = f"""
    <div style="text-align: center; max-width: 800px; margin: 0 auto; font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; font-size: 16px; line-height: 1.8; color: #333;">
        <p>화창한 아침, 광합성하기 좋은 날이네요.</p>
        <p><br></p>
        <p><strong>{keyword}</strong>에 대한 흥미로운 이야기를 시작해 봅니다.</p>
        <p>({post_type} 타겟팅에 맞춘 시적이고 흡입력 있는 AI 대본이 이곳에 렌더링됩니다.)</p>
        <p><br></p>
        <p>평범한 일상 속에서도 작은 발견이 주는 기쁨을 누리시길 바랍니다.</p>
        <p><br></p>
        <p style="color: #888;">#추천해시태그 #{keyword.replace(' ', '')} #인사이트 #트렌드</p>
        <p><br></p>
        <p style="font-weight: bold; color: #ff3f42;">[추천 아이템: {keyword} 관련 쿠팡 로켓배송 상품]</p>
    </div>
    """
    return jsonify({"status": "success", "html": html_content})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
