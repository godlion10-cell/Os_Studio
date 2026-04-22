import os, json, re, sys, urllib.parse, uuid, random
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from google import genai
from google.genai import types
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
TEXT_MODELS = ['gemini-2.5-flash', 'gemini-2.5-flash-lite']

app = Flask(__name__)
SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_content')
os.makedirs(SAVE_DIR, exist_ok=True)

def get_today(): return datetime.now().strftime('%Y년 %m월 %d일')

SYSTEM_PROTOCOL = """
1. [수석 작가]: 인사말 절대 금지. 힐링은 감각적 묘사, 해커는 팩트폭행으로 시작.
2. [편집 감독]: Text→이미지→Text→이미지→Text 멀티미디어 흐름 필수.
3. [아트 디렉터]: No-Text, No-Watermark. Hyper-realistic, 8k, cinematic lighting.
"""

# MetaAgent
class MetaAgent:
    AI_PAT = ["안녕하세요","결론적으로","요약하자면","이처럼","중요한 것은","기억하세요","Let me","Bro","Here's"]
    SENT = {"dopamine":{"kw":["충격","폭탄","진짜","대박","레전드"],"t":"dark dramatic, neon, intense"},"oxytocin":{"kw":["따뜻","포근","힐링","고요","평화"],"t":"warm golden hour, soft bokeh, cozy"},"curiosity":{"kw":["비밀","몰랐","숨겨진","반전"],"t":"mysterious shadows, fog, suspense"},"urgency":{"kw":["지금","당장","마감","놓치면"],"t":"sharp focus, red highlights"}}
    def __init__(self): self.det=[]; self.s=None
    def scan(self):
        self.det=[]
        try:
            for fn in sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.json')],reverse=True)[:5]:
                with open(os.path.join(SAVE_DIR,fn),'r',encoding='utf-8') as f: d=json.load(f)
                for mk in ['hacker','healer']:
                    sc=''
                    md=d.get(mk,{})
                    if isinstance(md,dict): sc=md.get('script','') or md.get('blog',{}).get('script','') if isinstance(md.get('blog'),dict) else ''
                    for p in self.AI_PAT:
                        if p in sc: self.det.append(p)
        except: pass
        self.det=list(set(self.det))
    def reinforce(self):
        if not self.det: return ""
        return f"\n[🚨 금지어: {', '.join(self.det[:8])}. 커뮤니티식 날것 표현으로 대체.]\n"
    def sync(self,text):
        if not text: self.s="dopamine"; return
        sc={s:sum(1 for k in v["kw"] if k in text) for s,v in self.SENT.items()}
        self.s=max(sc,key=sc.get) if any(sc.values()) else "dopamine"
    def tone(self): return self.SENT.get(self.s or "dopamine",{}).get("t","cinematic")

meta = MetaAgent()

def clean_json(raw):
    t=raw.strip(); t=re.sub(r'^```\w*\n?','',t)
    if t.endswith('```'): t=t[:-3]
    return t.strip()

def call_text(prompt):
    for m in TEXT_MODELS:
        try:
            r=client.models.generate_content(model=m,contents=prompt,config=types.GenerateContentConfig(temperature=0.8))
            return json.loads(clean_json(r.text))
        except Exception as e: print(f"[{m}] {e}"); continue
    return None

def call_json(prompt):
    for m in TEXT_MODELS:
        try:
            r=client.models.generate_content(model=m,contents=prompt,config=types.GenerateContentConfig(response_mime_type="application/json"))
            return json.loads(r.text)
        except Exception as e: print(f"[{m}] {e}"); continue
    return None

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8"><title>Os Studio v18.2 - One-Click Empire</title>
    <style>
        :root{--bg:#f4f7f6;--side:#1a1a1b;--naver:#00c73c;--hacker:#ff4d4d;--healer:#00c73c}
        body{margin:0;display:flex;font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:var(--bg);height:100vh;overflow:hidden;color:#333}
        #sidebar{width:340px;background:var(--side);color:#999;display:flex;flex-direction:column;border-right:1px solid #333}
        .sidebar-section{padding:15px;border-bottom:1px solid #333;overflow-y:auto}
        .radar-title{font-size:13px;font-weight:bold;margin-bottom:12px;display:block;color:white}
        .chip{padding:8px 12px;margin:4px;background:#27272a;border-radius:6px;font-size:12px;cursor:pointer;display:inline-block;transition:0.2s}
        .chip:hover{transform:scale(1.05)}
        .chip.search{border-left:3px solid #3b82f6;color:#e2e8f0}.chip.search:hover{background:#3b82f6;color:#fff}
        .chip.home{border-left:3px solid #f43f5e;color:#e2e8f0}.chip.home:hover{background:#f43f5e;color:#fff}
        .history-item{padding:6px;font-size:11px;color:#aaa;cursor:pointer;display:flex;justify-content:space-between}
        .history-item:hover{color:#fff}.del-btn{color:#ff4d4d;cursor:pointer}
        #main{flex:1;display:flex;flex-direction:column;overflow:hidden}
        #toolbar{padding:15px;background:#fff;border-bottom:1px solid #ddd;display:flex;justify-content:space-between;align-items:center}
        .status-badge{padding:5px 10px;background:#e2e8f0;border-radius:20px;font-size:12px;font-weight:bold;color:#333}
        #editor-container{display:flex;flex:1;gap:10px;padding:10px;overflow:hidden}
        .pane{flex:1;background:#fff;border-radius:8px;border:1px solid #ddd;display:flex;flex-direction:column;overflow:hidden}
        .pane-header{padding:12px;background:#fafafa;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center}
        .copy-btn{padding:5px 10px;font-size:11px;cursor:pointer;border:1px solid #ddd;background:#fff;border-radius:4px;font-weight:bold}
        .copy-btn:hover{background:var(--naver);color:#fff;border-color:var(--naver)}
        .writing-area{flex:1;padding:40px;overflow-y:auto;text-align:center;word-break:keep-all;line-height:1.9;font-size:16px}
        .img-ph{display:block;width:85%;margin:20px auto;padding:30px;background:#f9f9f9;border:2px dashed #ccc;color:#888;font-size:13px;border-radius:8px}
        .factory-hub{height:350px;background:#1e1e1e;color:#a1a1aa;border-top:3px solid var(--naver);padding:15px;display:flex;flex-direction:column;gap:10px}
        .factory-title{color:#00c73c;font-weight:bold;font-size:16px;margin-bottom:5px}
        .prompt-textarea{flex:1;background:#2d2d30;color:#4af626;padding:15px;font-family:monospace;font-size:14px;border:1px solid #444;border-radius:6px;resize:none;width:100%;box-sizing:border-box;line-height:1.6;outline:none}
        .prompt-textarea:focus{border-color:#00c73c}
        .copy-pack-btn{padding:10px;background:#3b82f6;color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:bold;font-size:14px;width:100%;transition:0.2s}
        .copy-pack-btn:hover{background:#2563eb}
        #loading{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:1000;justify-content:center;align-items:center;flex-direction:column;color:#fff}
        .toast{position:fixed;bottom:30px;right:30px;background:var(--naver);color:#fff;padding:14px 24px;border-radius:10px;font-weight:bold;z-index:2000;animation:fi 2.5s}
        @keyframes fi{0%{opacity:0;transform:translateY(20px)}15%{opacity:1;transform:translateY(0)}85%{opacity:1}100%{opacity:0}}
        .ftab-row{display:flex;gap:3px;margin-bottom:8px}
        .ftab{flex:1;padding:6px 2px;font-size:10px;background:#2c3e50;color:#888;border:none;cursor:pointer;border-radius:3px;transition:0.2s}
        .ftab.active{background:var(--naver);color:#fff;font-weight:bold}
        .ftab:hover:not(.active){background:#3a3a3a;color:#ccc}
        .fbox{display:none;width:100%;height:80px;padding:8px;box-sizing:border-box;background:#222;border:1px solid #444;border-radius:4px;color:#ddd;font-size:11px;font-family:monospace;resize:none}
        .fbox.active{display:block}
        .mega-btn{width:100%;padding:10px;background:linear-gradient(135deg,#ff4d4d,#f59e0b);color:#fff;font-size:13px;font-weight:bold;border:none;border-radius:5px;cursor:pointer;margin-top:8px;transition:0.2s}
        .mega-btn:hover{transform:scale(1.02);opacity:0.9}
        .flog{margin-top:6px;font-size:10px;color:#666;height:50px;overflow-y:auto;background:#111;padding:5px;border-radius:3px;font-family:monospace}
    </style>
</head>
<body>
<div id="loading"><h2 style="color:#00c73c">⚙️ 이사회 풀가동 중...</h2><p>원고 작성 + Imagen 3 발주서 세팅</p></div>
<div id="sidebar">
    <div class="sidebar-section"><span class="radar-title">🔍 검색 유입형 (안정 트래픽)</span><div id="search-radar">레이더 가동 중...</div></div>
    <div class="sidebar-section"><span class="radar-title" style="color:#f43f5e">✨ 홈판 알고리즘형 (도파민)</span><div id="home-radar">레이더 가동 중...</div></div>
    <div class="sidebar-section"><span class="radar-title" style="color:#a1a1aa">💾 기록소</span><div id="history-list">없음</div>
        <button onclick="deleteAllHist()" style="width:100%;margin-top:6px;padding:4px;background:#444;border:none;color:#fff;border-radius:3px;cursor:pointer;font-size:11px">전체 삭제</button></div>
    <div class="sidebar-section" style="flex:1">
        <span class="radar-title" style="color:#f59e0b">🏭 4대 미디어 팩토리</span>
        <div class="ftab-row">
            <button class="ftab active" onclick="switchFactory(this,'img-p')">📷 구글</button>
            <button class="ftab" onclick="switchFactory(this,'vid-p')">🎬 Luma</button>
            <button class="ftab" onclick="switchFactory(this,'bgm-p')">🎵 Suno</button>
            <button class="ftab" onclick="switchFactory(this,'tts-p')">🗣️ Eleven</button>
        </div>
        <textarea id="img-p" class="fbox active" placeholder="Imagen 3 발주서 붙여넣기"></textarea>
        <textarea id="vid-p" class="fbox" placeholder="Luma Dream Machine 발주서"></textarea>
        <textarea id="bgm-p" class="fbox" placeholder="Suno AI 음악 발주서"></textarea>
        <textarea id="tts-p" class="fbox" placeholder="ElevenLabs 성우 발주서"></textarea>
        <button class="mega-btn" onclick="megaFactory()">🚀 전 공장 동시 가동</button>
        <div class="flog" id="flog">시스템 대기 중...</div>
    </div>
</div>
<div id="main">
    <div id="toolbar">
        <div><strong style="font-size:18px">Os Studio Sovereign Master</strong>
            <span id="current-topic" style="margin-left:15px;color:#666">레이더에서 주제를 클릭하세요.</span></div>
        <div class="status-badge">🟢 시스템 정상</div>
    </div>
    <div id="editor-container">
        <div class="pane">
            <div class="pane-header"><strong style="color:var(--hacker)">🔥 해커 모드 원고</strong><button class="copy-btn" onclick="copyPane('hacker-body')">원고 복사</button></div>
            <div class="writing-area" id="hacker-body">좌측 레이더에서 키워드를 클릭하세요.</div>
            <div class="factory-hub" style="background: #111; padding: 15px; border-top: 3px solid #00c73c; height: auto; min-height: 250px;">
                <span class="factory-title" style="color:white;">🖼️ 이미지팀 다이렉트 산출물 (자동 완성)</span>
                <div id="hacker-images" style="display: flex; gap: 10px; overflow-x: auto; margin-top: 10px;">
                    <div style="color:#666; font-size:12px; margin:20px auto;">원고가 생성되면 이곳에 이미지가 자동 배치됩니다.</div>
                </div>
            </div>
        </div>
        <div class="pane">
            <div class="pane-header"><strong style="color:var(--healer)">🍀 힐링 모드 원고</strong><button class="copy-btn" onclick="copyPane('healer-body')">원고 복사</button></div>
            <div class="writing-area" id="healer-body">원클릭으로 동시 작성됩니다.</div>
            <div class="factory-hub" style="background: #111; padding: 15px; border-top: 3px solid #00c73c; height: auto; min-height: 250px;">
                <span class="factory-title" style="color:white;">🖼️ 이미지팀 다이렉트 산출물 (자동 완성)</span>
                <div id="healer-images" style="display: flex; gap: 10px; overflow-x: auto; margin-top: 10px;">
                    <div style="color:#666; font-size:12px; margin:20px auto;">원고가 생성되면 이곳에 이미지가 자동 배치됩니다.</div>
                </div>
            </div>
        </div>
    </div>
</div>
<script>
function showToast(m){const t=document.createElement('div');t.className='toast';t.innerText=m;document.body.appendChild(t);setTimeout(()=>t.remove(),2600)}
function switchFactory(btn,id){document.querySelectorAll('.ftab').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.fbox').forEach(b=>b.classList.remove('active'));btn.classList.add('active');document.getElementById(id).classList.add('active')}
function flog(m){const l=document.getElementById('flog');const ts=new Date().toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit',second:'2-digit'});l.innerHTML+=`<div>[${ts}] ${m}</div>`;l.scrollTop=l.scrollHeight}
function megaFactory(){const img=document.getElementById('img-p').value.split('\n').filter(l=>l.trim());const vid=document.getElementById('vid-p').value.split('\n').filter(l=>l.trim());const bgm=document.getElementById('bgm-p').value.split('\n').filter(l=>l.trim());const tts=document.getElementById('tts-p').value.split('\n').filter(l=>l.trim());const total=img.length+vid.length+bgm.length+tts.length;if(!total){flog('❌ 모든 발주서 비어있음');return}flog(`🚀 전 공장 가동: ${total}건`);if(img.length){window.open('https://labs.google/fx/tools/image-fx','_blank');flog(`📷 Imagen: ${img.length}장`)}if(vid.length){window.open('https://lumalabs.ai/dream-machine','_blank');flog(`🎬 Luma: ${vid.length}편`)}if(bgm.length){window.open('https://suno.com/create','_blank');flog(`🎵 Suno: ${bgm.length}곡`)}if(tts.length){window.open('https://elevenlabs.io','_blank');flog(`🗣️ Eleven: ${tts.length}건`)}showToast(`${total}건 공장 가동!`)}
async function loadRadar(){try{const r=await fetch('/api/radar');const d=await r.json();const sA=Array.isArray(d.search)?d.search:Object.values(d.search||{});const hA=Array.isArray(d.home)?d.home:Object.values(d.home||{});
document.getElementById('search-radar').innerHTML=sA.map(k=>{const s=String(k).replace(/'/g,"\\'");return`<div class="chip search" onclick="runOneClick('${s}')"># ${k}</div>`}).join('');
document.getElementById('home-radar').innerHTML=hA.map(k=>{const s=String(k).replace(/'/g,"\\'");return`<div class="chip home" onclick="runOneClick('${s}')"># ${k}</div>`}).join('')}catch(e){document.getElementById('search-radar').innerText='새로고침'}}

async function runOneClick(kw){
    document.getElementById('current-topic').innerHTML=`작업 중: <b>${kw}</b>`;
    document.getElementById('loading').style.display='flex';
    try{const r=await fetch('/api/one-click-execute',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keyword:kw})});
    const d=await r.json();if(d.status==='error'){alert(d.message);return}
    renderData('hacker',d.hacker);renderData('healer',d.healer);
    showToast('원클릭 실행 완료');loadHistory()}catch(e){alert('통신 오류')}finally{document.getElementById('loading').style.display='none'}}

function renderData(mode,data){
    if(!data){document.getElementById(mode+'-body').innerHTML='<p style="color:#999">생성 실패</p>';return}
    let h=`<h1 style="font-size:22px;margin-bottom:25px">${data.title||''}</h1>`;
    let b=(data.script||'');
    const images = data.images || data.generated_images || [];
    b = b.replace(/\[📷\s*이미지\s*(\d+).*?\]/g, (match, p1) => {
        const idx = parseInt(p1) - 1;
        if (images[idx]) {
            return `<div class="img-ph" style="padding:10px;border:none"><img src="${images[idx]}" style="max-width:100%;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.1)"></div>`;
        }
        return `<div class="img-ph">📷 이미지 ${p1} (생성 중)</div>`;
    });
    h+=`<div>${b.replace(/\\n/g,'<br>')}</div>`;
    document.getElementById(mode+'-body').innerHTML=h;
    
    // 생성된 이미지를 화면 하단 팩토리 허브에 바로 꽂아버리기
    const imgContainer = document.getElementById(mode+'-images');
    imgContainer.innerHTML = ''; // 초기화
    
    images.forEach((url, index) => {
        const imgElement = `<div style="text-align: center; flex: 0 0 auto;">
                              <img src="${url}" style="height: 200px; border-radius: 8px; border: 2px solid #333;" alt="Generated Image">
                              <div style="font-size: 11px; margin-top: 5px; color: #888;">[이미지 ${index + 1}]</div>
                            </div>`;
        imgContainer.innerHTML += imgElement;
    });
    
    const pp=data.prompt_pack||[];
    if(pp.length){const cur=document.getElementById('img-p').value;document.getElementById('img-p').value=(cur?cur+'\n':'')+pp.join('\n');flog(`📦 ${mode} 발주서 ${pp.length}건 → 팩토리 자동 적재`)}
}

function copyPane(id){const r=document.createRange();r.selectNode(document.getElementById(id));window.getSelection().removeAllRanges();window.getSelection().addRange(r);document.execCommand('copy');window.getSelection().removeAllRanges();showToast('원고 복사 완료!')}
function copyPromptPack(id){navigator.clipboard.writeText(document.getElementById(id).value);showToast('발주서 복사 완료! Labs FX에 붙여넣으세요')}

async function loadHistory(){try{const r=await fetch('/api/history');const f=await r.json();const el=document.getElementById('history-list');if(!f.length){el.innerText='없음';return}
el.innerHTML=f.map(x=>`<div class="history-item"><span onclick="loadSingle('${x.fn}')">${x.dp}</span><span class="del-btn" onclick="event.stopPropagation();delOne('${x.fn}')">×</span></div>`).join('')}catch(e){}}
async function loadSingle(n){try{const r=await fetch('/api/history/'+n);const d=await r.json();if(d.hacker)renderData('hacker',d.hacker);if(d.healer)renderData('healer',d.healer)}catch(e){}}
async function delOne(n){if(!confirm('삭제?'))return;await fetch('/api/delete-selected',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filenames:[n]})});showToast('삭제');loadHistory()}
async function deleteAllHist(){if(!confirm('전부 삭제?'))return;await fetch('/api/delete-all',{method:'POST'});showToast('전체 삭제');loadHistory()}
window.onload=()=>{loadRadar();loadHistory()}
</script>
</body></html>
"""

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/radar')
def get_radar():
    # 분석팀장의 뇌 구조를 사장님의 기획 의도에 맞게 완전히 뜯어고칩니다.
    prompt = f"""
    오늘 날짜: {get_today()}. 
    당신은 최상급 미디어 트렌드 분석가입니다. 사장님을 위해 두 가지 명확한 카테고리로 가장 핫하고 돈이 되는 키워드를 각각 5개씩 뽑아주세요.
    
    1. [search] (검색 유입형): 사람들이 정보를 얻기 위해 네이버나 구글에 '직접 타자를 쳐서 검색'하는 키워드. 
       - 특징: 정보성, 해결책, 안정적 트래픽, ~하는 법, ~후기, ~지원금 등.
       - 예시: "2026년 청년 도약 계좌 조건", "아이폰 18 프로 맥스 실사용 후기", "연말정산 환급금 조회 방법"
       
    2. [home] (홈판 알고리즘형): 네이버 메인 홈이나 구글 디스커버에 떴을 때 썸네일과 제목만 보고 호기심에 이끌려 무심코 클릭하게 되는 도파민 유발 키워드. 
       - 특징: 자극적, 트렌디, 공감, 분노, 숨겨진 비밀, ~하는 진짜 이유 등.
       - 예시: "90년대생이 입사 1년 만에 퇴사하는 진짜 이유", "강남 꼬마빌딩 반토막 충격", "의사들이 절대 안 먹는 3가지 음식"
    
    반드시 아래 JSON 양식에 맞춰 정확히 반환하세요:
    {{
        "search": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
        "home": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"]
    }}
    """
    
    try:
        # 모델을 2.0으로 업그레이드하여 통찰력 강화
        res = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt, 
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return jsonify(json.loads(res.text.strip()))
        
    except Exception as e:
        print(f"레이더 엔진 에러: {e}")
        # 만약 API 오류가 나더라도 화면이 비어있지 않게 비상용 키워드를 던져줍니다.
        return jsonify({
            "search": ["2026년 정부 지원금", "chatGPT 실전 사용법", "미국 배당주 추천"],
            "home": ["월 1000만원 자동수익의 비밀", "평생 후회하는 3가지 소비", "지금 안 사면 품절되는 가성비템"]
        })

@app.route('/api/history')
def get_history():
    files=[]
    for fn in sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.json')],reverse=True)[:30]:
        try:
            with open(os.path.join(SAVE_DIR,fn),'r',encoding='utf-8') as f: d=json.load(f)
            dp=d.get('keyword',fn[:20])
        except: dp=fn[:20]
        files.append({"fn":fn,"dp":dp})
    return jsonify(files)

@app.route('/api/history/<name>')
def history_single(name):
    p=os.path.join(SAVE_DIR,os.path.basename(name))
    if not os.path.exists(p): return jsonify({"error":"없음"}),404
    with open(p,'r',encoding='utf-8') as f: return jsonify(json.load(f))

@app.route('/api/delete-selected', methods=['POST'])
def delete_selected():
    for fn in request.get_json().get('filenames',[]):
        p=os.path.join(SAVE_DIR,os.path.basename(fn))
        if os.path.exists(p): os.remove(p)
    return jsonify({"status":"ok"})

@app.route('/api/delete-all', methods=['POST'])
def delete_all():
    for f in os.listdir(SAVE_DIR):
        fp=os.path.join(SAVE_DIR,f)
        if os.path.isfile(fp): os.remove(fp)
    return jsonify({"status":"ok"})

@app.route('/api/one-click-execute', methods=['POST'])
def one_click_execute():
    kw=request.get_json().get('keyword','')
    today=get_today()
    meta.scan(); rf=meta.reinforce()

    def process_agent(mode):
        # AI 검열 회피 및 정확한 출력 양식 지시
        prompt = f"""
        주제: '{kw}', 작성 모드: '{mode}'. 
        1. [작가]: 블로그 본문을 작성하되, 안전 가이드라인을 준수하여 작성할 것. 
        본문 중간중간 사진이 들어갈 자리에 오직 텍스트로만 '[📷 이미지 1 위치]', '[📷 이미지 2 위치]' 라고 표시할 것. (절대 HTML <img> 태그나 마크다운 링크를 사용하지 말 것!)
        2. [이미지팀장]: 본문 내용에 맞는 실사 사진 프롬프트를 영문으로 2개 작성할 것.
        ★ 프롬프트 끝에 반드시 추가: ", hyper-realistic, 8k resolution, raw photo, detailed, shot on DSLR, NO DRAWING, NO SKETCH"
        
        JSON: {{
            "title": "제목",
            "script": "본문 내용...",
            "prompts": ["1번 프롬프트", "2번 프롬프트"]
        }}
        """
        
        try:
            res = client.models.generate_content(model=TEXT_MODELS[0], contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
            
            raw_text = res.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            data = json.loads(raw_text.strip())
            
            # 엔진에 직접 프롬프트를 쏴서 이미지 URL 생성 (버그 수정 완료)
            image_urls = []
            for eng_prompt in data.get('prompts', []):
                encoded_prompt = urllib.parse.quote(eng_prompt)
                # 너무 큰 숫자 대신, 정상적인 범위의 난수로 시드값 생성
                safe_seed = random.randint(1, 999999)
                direct_image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={safe_seed}"
                image_urls.append(direct_image_url)
                
            return {
                "title": data.get("title", f"{kw}에 대한 글"),
                "script": data.get("script", "내용을 불러오지 못했습니다."),
                "generated_images": image_urls
            }
            
        except Exception as e:
            print(f"[{mode} 모드 에러 발생]: {e}")
            return {
                "title": f"⚠️ {mode} 모드 일시적 생성 지연",
                "script": "AI 서버와의 연결이 지연되었거나, 주제가 안전 필터에 걸렸습니다. 다른 키워드를 클릭하거나 다시 시도해 주세요.",
                "generated_images": []
            }

    hacker=process_agent("해커")
    healer=process_agent("힐링")

    if not hacker and not healer:
        return jsonify({"status":"error","message":"AI 생성 실패. 재시도."})

    try:
        safe_kw=re.sub(r'\W+','_',kw)[:15]
        fn=f"empire_{datetime.now().strftime('%y%m%d_%H%M%S')}_{safe_kw}.json"
        with open(os.path.join(SAVE_DIR,fn),'w',encoding='utf-8') as f:
            json.dump({"keyword":kw,"hacker":hacker,"healer":healer},f,ensure_ascii=False,indent=4)
        print(f"[SAVED] {fn}")
    except Exception as e: print(f"[SAVE] {e}")

    return jsonify({"hacker":hacker,"healer":healer})

if __name__=='__main__': app.run(debug=True,port=5000)