import os, json, re, sys
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
        .factory-hub{max-height:220px;background:#1e1e1e;color:#a1a1aa;border-top:3px solid var(--naver);padding:15px;overflow-y:auto;font-family:monospace;font-size:12px}
        .factory-title{color:#00c73c;font-weight:bold;font-size:14px;margin-bottom:10px;display:block}
        .copy-pack-btn{padding:6px 12px;background:#3b82f6;color:#fff;border:none;border-radius:4px;cursor:pointer;float:right;font-weight:bold}
        .copy-pack-btn:hover{background:#2563eb}
        #loading{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:1000;justify-content:center;align-items:center;flex-direction:column;color:#fff}
        .toast{position:fixed;bottom:30px;right:30px;background:var(--naver);color:#fff;padding:14px 24px;border-radius:10px;font-weight:bold;z-index:2000;animation:fi 2.5s}
        @keyframes fi{0%{opacity:0;transform:translateY(20px)}15%{opacity:1;transform:translateY(0)}85%{opacity:1}100%{opacity:0}}
    </style>
</head>
<body>
<div id="loading"><h2 style="color:#00c73c">⚙️ 이사회 풀가동 중...</h2><p>원고 작성 + Imagen 3 발주서 세팅</p></div>
<div id="sidebar">
    <div class="sidebar-section"><span class="radar-title">🔍 검색 유입형 (안정 트래픽)</span><div id="search-radar">레이더 가동 중...</div></div>
    <div class="sidebar-section"><span class="radar-title" style="color:#f43f5e">✨ 홈판 알고리즘형 (도파민)</span><div id="home-radar">레이더 가동 중...</div></div>
    <div class="sidebar-section" style="flex:1"><span class="radar-title" style="color:#a1a1aa">💾 기록소</span><div id="history-list">없음</div>
        <button onclick="deleteAllHist()" style="width:100%;margin-top:10px;padding:5px;background:#444;border:none;color:#fff;border-radius:3px;cursor:pointer">전체 삭제</button></div>
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
            <div class="factory-hub">
                <span class="factory-title">📦 이미지팀장 발주서</span>
                <button class="copy-pack-btn" onclick="copyPromptPack('hacker-prompts')">발주서 복사</button>
                <pre id="hacker-prompts" style="white-space:pre-wrap;margin-top:10px">대기 중...</pre>
            </div>
        </div>
        <div class="pane">
            <div class="pane-header"><strong style="color:var(--healer)">🍀 힐링 모드 원고</strong><button class="copy-btn" onclick="copyPane('healer-body')">원고 복사</button></div>
            <div class="writing-area" id="healer-body">원클릭으로 동시 작성됩니다.</div>
            <div class="factory-hub">
                <span class="factory-title">📦 이미지팀장 발주서</span>
                <button class="copy-pack-btn" onclick="copyPromptPack('healer-prompts')">발주서 복사</button>
                <pre id="healer-prompts" style="white-space:pre-wrap;margin-top:10px">대기 중...</pre>
            </div>
        </div>
    </div>
</div>
<script>
function showToast(m){const t=document.createElement('div');t.className='toast';t.innerText=m;document.body.appendChild(t);setTimeout(()=>t.remove(),2600)}
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
    let b=(data.script||'').replace(/\[📷\s*이미지\s*(\d+)[:\s]*(.*?)\]/g,'<div class="img-ph">📷 이미지 $1: $2</div>');
    h+=`<div>${b.replace(/\\n/g,'<br>')}</div>`;
    document.getElementById(mode+'-body').innerHTML=h;
    const pp=data.prompt_pack||[];
    document.getElementById(mode+'-prompts').innerText=pp.join('\n')}

function copyPane(id){const r=document.createRange();r.selectNode(document.getElementById(id));window.getSelection().removeAllRanges();window.getSelection().addRange(r);document.execCommand('copy');window.getSelection().removeAllRanges();showToast('원고 복사 완료!')}
function copyPromptPack(id){navigator.clipboard.writeText(document.getElementById(id).innerText);showToast('발주서 복사 완료! AI Flow에 붙여넣으세요')}

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
    today=get_today()
    r=call_json(f"오늘 {today} 기준 한국 수익화 블로그 키워드. 검색용 5개, 홈판용 5개. JSON: {{\"search\":[],\"home\":[]}}")
    return jsonify(r or {"search":["재시도"],"home":["대기"]})

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

    def process(mode_name, mode_desc):
        prompt=f"""주제:'{kw}', 모드:{mode_desc}. 오늘:{today}.
{SYSTEM_PROTOCOL}{rf}
JSON만 응답:
{{"title":"훅 제목","script":"본문(최소800자). 도입(2~3문단)→[📷 이미지 1: 상황묘사]→전개(2~3문단)→[📷 이미지 2: 근거/증거]→핵심(2~3문단)→[📷 이미지 3: 결과]→마무리. 이미지 마커는 문단 사이 독립 줄.","prompt_pack":["각 이미지 마커에 대응하는 영어 실사 프롬프트 4개. No text, cinematic, 8k."]}}"""
        data=call_text(prompt)
        if not data: return None
        meta.sync(data.get('script',''))
        data['meta']={'sentiment':meta.s,'tone':meta.tone(),'blocked':len(meta.det)}
        return data

    hacker=process("hacker","츤데레 코치. 팩트폭행. IT비유. 단정형.")
    healer=process("healer","따뜻한 치유자. ASMR. 감각적 묘사.")

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