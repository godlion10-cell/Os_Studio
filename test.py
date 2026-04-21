import google.generativeai as genai

# 🚨 여기에 방금 구글에서 받은 키를 정확히 넣어주세요
TEST_API_KEY = "AIzaSyB71ZRmGp2RQUm_d_uESoMOkPLLIuq6PZ8"
 

print("🤖 제미나이 엔진 단독 테스트를 시작합니다...")
genai.configure(api_key=TEST_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

try:
    response = model.generate_content("테스트입니다. '준비 완료'라고 딱 네 글자만 대답해줘.")
    print("\n✅ 성공! 엔진이 살아있습니다: ", response.text)
except Exception as e:
    print("\n❌ 실패! 구글이 죽은 키를 줬습니다 에러내용: ", e)