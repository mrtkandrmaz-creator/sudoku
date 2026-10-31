import base64
import json
import os
import random
import re
from html import escape as esc

import streamlit as st
import streamlit.components.v1 as components

# =============================================================================
# SAYFA AYARI
# =============================================================================
st.set_page_config(
    page_title="MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi",
    page_icon="🎒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# 1. API ANAHTARLARI VE YAPAY ZEKA MOTORU
# =============================================================================


def get_all_api_keys():
    gemini_keys, groq_keys = [], []
    try:
        if hasattr(st, "secrets") and "api_keys" in st.secrets:
            block = st.secrets["api_keys"]
            for name, target in (("groq_keys", groq_keys), ("gemini_keys", gemini_keys)):
                if name in block:
                    for k in block[name]:
                        if isinstance(k, str) and len(k.strip()) > 5 and k.strip() not in target:
                            target.append(k.strip())
    except Exception:
        pass
    if st.session_state.get("manual_gemini") and st.session_state["manual_gemini"] not in gemini_keys:
        gemini_keys.append(st.session_state["manual_gemini"])
    if st.session_state.get("manual_groq") and st.session_state["manual_groq"] not in groq_keys:
        groq_keys.append(st.session_state["manual_groq"])
    return gemini_keys, groq_keys


gemini_keys, groq_keys = get_all_api_keys()
has_gemini = False
has_groq = False

try:
    import google.generativeai as genai

    has_gemini = bool(gemini_keys)
except ImportError:
    pass

try:
    from groq import Groq

    has_groq = bool(groq_keys)
except ImportError:
    pass


def ai_generate_content(prompt_text):
    if has_groq:
        for gr_key in groq_keys:
            try:
                client = Groq(api_key=gr_key)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt_text}],
                    temperature=0.95,
                )
                if completion.choices[0].message.content:
                    return completion.choices[0].message.content
            except Exception:
                continue
    if has_gemini:
        for g_key in gemini_keys:
            try:
                genai.configure(api_key=g_key)
                for model_name in ["gemini-3.6-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
                    try:
                        response = genai.GenerativeModel(model_name).generate_content(prompt_text)
                        if response and response.text:
                            return response.text
                    except Exception:
                        continue
            except Exception:
                continue
    return None


def parse_json(text):
    """Yapay zeka cevabından JSON'u güvenle ayıklar."""
    if not text:
        return None
    cleaned = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    m = re.search(r"(\[.*\]|\{.*\})", cleaned, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return None
    return None


def is_valid(data, expect, required=()):
    if expect is str:
        return isinstance(data, str) and bool(data.strip())
    if not isinstance(data, expect) or not data:
        return False
    items = data if isinstance(data, list) else [data]
    return all(isinstance(i, dict) and set(required) <= set(i) for i in items)


# =============================================================================
# 2. MEB 5. SINIF MÜFREDATI
# =============================================================================
MEB_CURRICULUM = {
    "Türkçe": {
        "renk": "linear-gradient(135deg, #ff6b81, #ff9a76)",
        "ikon": "📖",
        "uniteler": [
            "1. Tema: Sözcükte Anlam",
            "2. Tema: Cümlede Anlam",
            "3. Tema: Parçada Anlam",
            "4. Tema: Metin Türleri",
            "5. Tema: Noktalama İşaretleri",
        ],
    },
    "Matematik": {
        "renk": "linear-gradient(135deg, #06b6d4, #3b82f6)",
        "ikon": "📐",
        "uniteler": [
            "1. Ünite: Doğru, Doğru Parçası, Nokta, Işın, Dikme",
            "2. Ünite: Geometrik Nicelikler",
            "3. Ünite: Geometrik Kavramlar ve Üçgenler",
            "4. Ünite: Doğal Sayılar",
            "5. Ünite: Kesirler",
            "6. Ünite: Ondalık Gösterimler",
            "7. Ünite: Veri İşleme",
        ],
    },
    "Fen Bilimleri": {
        "renk": "linear-gradient(135deg, #10b981, #2dd4bf)",
        "ikon": "🔬",
        "uniteler": [
            "1. Ünite: Güneş, Dünya ve Ay",
            "2. Ünite: Canlılar Dünyası",
            "3. Ünite: Kuvvetin Etkisi",
            "4. Ünite: Madde ve Değişim",
            "5. Ünite: Işığın Yayılması",
            "6. Ünite: İnsan ve Çevre",
            "7. Ünite: Elektrik Devreleri",
        ],
    },
    "Sosyal Bilgiler": {
        "renk": "linear-gradient(135deg, #f59e0b, #fbbf24)",
        "ikon": "🌍",
        "uniteler": [
            "1. Ünite: Birlikte Yaşamak",
            "2. Ünite: Evimiz Dünya",
            "3. Ünite: Kültür ve Miras",
            "4. Ünite: Yaşayan Türkiye",
            "5. Ünite: Üreten Türkiye",
            "6. Ünite: Yönetime Katılıyorum",
        ],
    },
    "Din Kültürü ve Ahlak Bilgisi": {
        "renk": "linear-gradient(135deg, #8b5cf6, #c084fc)",
        "ikon": "🌙",
        "uniteler": [
            "1. Ünite: Allah İnancı",
            "2. Ünite: Ramazan ve Oruç",
            "3. Ünite: Hz. Muhammed ve Aile Hayatı",
            "4. Ünite: Çevremizde Dinin İzleri",
            "5. Ünite: Ahlaki Değerler",
        ],
    },
    "İngilizce": {
        "renk": "linear-gradient(135deg, #ec4899, #fb7185)",
        "ikon": "🗣️",
        "uniteler": [
            "Unit 1: Hello!",
            "Unit 2: My Town",
            "Unit 3: Games and Hobbies",
            "Unit 4: My Daily Routine",
            "Unit 5: Health",
            "Unit 6: Movies",
            "Unit 7: Party Time",
            "Unit 8: Fitness",
        ],
    },
    "Almanca": {
        "renk": "linear-gradient(135deg, #84cc16, #22c55e)",
        "ikon": "🇩🇪",
        "uniteler": [
            "Lektion 1: Hallo! Ich heiße...",
            "Lektion 2: Meine Familie",
            "Lektion 3: Meine Schulsachen",
            "Lektion 4: Zahlen und Farben",
            "Lektion 5: Hobbys und Freizeit",
        ],
    },
}

GAMES = [
    ("balon", "🎈", "Balon Patlatmaca", "linear-gradient(135deg, #f43f5e, #fb923c)"),
    ("sinav10", "🧠", "5 Soruluk Kazanım Yarışması", "linear-gradient(135deg, #06b6d4, #2563eb)"),
    ("dogruyanlis", "✅", "Doğru / Yanlış Meydan Okuması", "linear-gradient(135deg, #10b981, #14b8a6)"),
    ("bosluk", "📝", "Boşluk Doldurma Yarışması", "linear-gradient(135deg, #f59e0b, #f97316)"),
    ("kartlar", "🃏", "Soru Kartları", "linear-gradient(135deg, #8b5cf6, #d946ef)"),
    ("oynayarak", "🎯", "Oynayarak Öğren", "linear-gradient(135deg, #0ea5e9, #6366f1)"),
    ("etkinlik", "📚", "Etkinliklerle Öğren", "linear-gradient(135deg, #22c55e, #84cc16)"),
    ("kelime", "🔤", "Kelime Avı Bulmacası", "linear-gradient(135deg, #eab308, #f59e0b)"),
    ("acik", "✍️", "Klasik Yazılı Simülatörü", "linear-gradient(135deg, #6366f1, #a855f7)"),
]
GAME_INFO = {g[0]: g for g in GAMES}

# =============================================================================
# 3. DURUM (SESSION STATE)
# =============================================================================


def new_gs():
    """Her oyunun kendi geçici durumu."""
    return {
        "data": None, "failed": False, "idx": 0, "score": 0, "feedback": None,
        "show": False, "choice": None, "eval": None, "results": None,
        "guess": [], "used": [], "pool": [], "pool_for": -1, "msg": None,
        "nonce": random.randint(1000, 999999),
    }


for _k, _v in {
    "selected_subject": None,
    "selected_unit": None,
    "selected_game": None,
    "coach_messages": [
        {"role": "assistant", "content": "Merhaba ben AdenMind, sana yardımcı olmak için buradayım! ✨"}
    ],
}.items():
    st.session_state.setdefault(_k, _v)


def get_gs(game):
    ident = (st.session_state["selected_subject"], st.session_state["selected_unit"], game)
    if st.session_state.get("gs_ident") != ident or "gs" not in st.session_state:
        st.session_state["gs_ident"] = ident
        st.session_state["gs"] = new_gs()
    return st.session_state["gs"]


# --- Gezinme geri çağrıları (tek tıkla geçiş için) ---
def go_home():
    st.session_state.update(selected_subject=None, selected_unit=None, selected_game=None)


def pick_subject(s):
    st.session_state.update(selected_subject=s, selected_unit=None, selected_game=None)


def pick_unit(u):
    st.session_state.update(selected_unit=u, selected_game=None)


def pick_game(g):
    st.session_state["selected_game"] = g


def back_to_units():
    st.session_state.update(selected_unit=None, selected_game=None)


def back_to_games():
    st.session_state["selected_game"] = None


def regen():
    st.session_state["gs"] = new_gs()


# =============================================================================
# 4. ADENMIND AVATARI (turkuaz, modern)
# =============================================================================
AVATAR_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5eead4"/><stop offset="1" stop-color="#0891b2"/></linearGradient>
<linearGradient id="face" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f0fdfa"/><stop offset="1" stop-color="#99f6e4"/></linearGradient>
<radialGradient id="eye" cx="50%" cy="38%" r="65%"><stop offset="0" stop-color="#ecfeff"/><stop offset="1" stop-color="#22d3ee"/></radialGradient>
</defs>
<circle cx="60" cy="60" r="58" fill="url(#bg)"/>
<circle cx="60" cy="60" r="52" fill="none" stroke="#ffffff" stroke-opacity=".25" stroke-width="2"/>
<polygon points="26,54 31,16 60,38" fill="#0f766e"/>
<polygon points="94,54 89,16 60,38" fill="#0f766e"/>
<polygon points="33,44 35,26 51,38" fill="#5eead4"/>
<polygon points="87,44 85,26 69,38" fill="#5eead4"/>
<rect x="21" y="36" width="78" height="64" rx="31" fill="url(#face)"/>
<rect x="29" y="51" width="62" height="35" rx="17" fill="#0b3b4a"/>
<ellipse cx="46" cy="68" rx="8.5" ry="10.5" fill="url(#eye)"/>
<ellipse cx="74" cy="68" rx="8.5" ry="10.5" fill="url(#eye)"/>
<circle cx="43" cy="64" r="2.8" fill="#fff"/>
<circle cx="71" cy="64" r="2.8" fill="#fff"/>
<path d="M52 92 Q60 99 68 92" fill="none" stroke="#0e7490" stroke-width="3.2" stroke-linecap="round"/>
<circle cx="30" cy="92" r="4.5" fill="#2dd4bf" opacity=".55"/>
<circle cx="90" cy="92" r="4.5" fill="#2dd4bf" opacity=".55"/>
<path d="M96 22 l2.4 6 6 2.4 -6 2.4 -2.4 6 -2.4 -6 -6 -2.4 6 -2.4z" fill="#fef08a"/>
</svg>"""
AVATAR_B64 = base64.b64encode(AVATAR_SVG.encode("utf-8")).decode()


def adenmind_avatar(size=44):
    return (
        f'<img class="am-avatar" src="data:image/svg+xml;base64,{AVATAR_B64}" '
        f'width="{size}" height="{size}" alt="AdenMind">'
    )


# =============================================================================
# 5. STİLLER
# =============================================================================
BASE_CSS = """
.stApp{
  background:
    radial-gradient(circle, rgba(94,234,212,.09) 2px, transparent 2.6px) 0 0/40px 40px,
    radial-gradient(700px 420px at 6% -4%, rgba(45,212,191,.24), transparent 62%),
    radial-gradient(640px 420px at 100% 8%, rgba(6,182,212,.20), transparent 62%),
    radial-gradient(560px 380px at 60% 112%, rgba(16,185,129,.15), transparent 62%),
    #071a24 !important;
  background-attachment: fixed;
  color:#e6fffb;
}
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"]{color:#e6fffb}
[data-testid="stHeader"]{background:transparent}
.block-container{padding-top:2.2rem;max-width:1250px}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#06222c,#0a3340);border-right:1px solid rgba(94,234,212,.2)}

/* ---- Başlık ---- */
.hero{position:relative;overflow:hidden;display:flex;align-items:center;gap:18px;padding:22px 28px;
  border-radius:30px;color:#fff;margin-bottom:26px;
  background:linear-gradient(135deg,#0d9488 0%,#06b6d4 55%,#22d3ee 100%);
  box-shadow:0 10px 0 rgba(4,47,46,.55),0 26px 50px rgba(6,182,212,.25)}
.hero:before,.hero:after{content:"";position:absolute;background:rgba(255,255,255,.14)}
.hero:before{width:190px;height:190px;border-radius:50%;right:-45px;top:-80px}
.hero:after{width:110px;height:110px;border-radius:30px;transform:rotate(22deg);right:150px;bottom:-60px}
.hero .badge{font-size:2.2rem;background:rgba(255,255,255,.2);border-radius:22px;padding:8px 14px;
  box-shadow:0 5px 0 rgba(0,0,0,.18)}
.hero h1{margin:0;font-size:1.6rem;font-weight:800;color:#fff !important;line-height:1.2}
.hero small{opacity:.92;font-weight:600;color:#fff}

.crumb{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:4px 0 14px;font-weight:700}
.pill{padding:8px 16px;border-radius:999px;background:linear-gradient(135deg,#14b8a6,#06b6d4);color:#042f2e;
  box-shadow:0 4px 0 #0f766e}
.pill.alt{background:rgba(255,255,255,.1);color:#e6fffb;border:1px solid rgba(94,234,212,.4);box-shadow:none}
.section-title{font-size:1.35rem;font-weight:800;margin:6px 0 14px}

/* ---- Butonlar ---- */
.stButton>button,.stFormSubmitButton>button{
  width:100%;min-height:48px;border-radius:18px;font-weight:800;border:0 !important;padding:.6rem 1.1rem;
  display:flex;align-items:center;justify-content:center;text-align:center;
  color:#042f2e !important;background:linear-gradient(135deg,#5eead4,#22d3ee) !important;
  box-shadow:0 5px 0 #0f766e;transition:transform .15s,box-shadow .15s,filter .15s}
.stButton>button p,.stFormSubmitButton>button p{color:inherit !important;margin:0}
.stButton>button:hover{transform:translateY(-2px);filter:brightness(1.06);box-shadow:0 7px 0 #0f766e}
.stButton>button:active{transform:translateY(4px);box-shadow:0 1px 0 #0f766e}
.stButton>button:disabled{opacity:.45;filter:grayscale(.4)}
[class*="st-key-back"] button,[class*="st-key-pass"] button,[class*="st-key-home"] button{
  background:rgba(255,255,255,.08) !important;color:#e6fffb !important;
  border:1px solid rgba(94,234,212,.4) !important;box-shadow:0 4px 0 rgba(0,0,0,.35) !important}
.st-key-optbox button,.st-key-letters button{
  background:rgba(255,255,255,.07) !important;color:#e6fffb !important;
  border:2px solid rgba(94,234,212,.45) !important;box-shadow:0 5px 0 rgba(0,0,0,.35) !important;
  height:96px;min-height:96px;max-height:96px;padding:6px 16px;overflow:hidden;
  border-radius:22px;font-size:.98rem;line-height:1.2;justify-content:flex-start;text-align:left}
.st-key-optbox button p{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden;text-align:left}
.st-key-optbox button:hover,.st-key-letters button:hover{
  background:linear-gradient(135deg,#14b8a6,#06b6d4) !important;color:#042f2e !important}
.st-key-letters button{height:58px;min-height:58px;max-height:58px;justify-content:center;text-align:center;font-size:1.3rem;padding:0}
[data-testid="stPopover"] button{
  background:linear-gradient(135deg,#14b8a6,#06b6d4) !important;color:#042f2e !important;font-weight:800;
  border-radius:18px !important;border:0 !important;min-height:48px;box-shadow:0 5px 0 #0f766e}
div[data-testid="stHorizontalBlock"]{gap:1.1rem}

/* ---- Girdiler ---- */
/* Tarayıcı/Streamlit açık tema kullansa bile yazılar görünsün: kutu arka planı KOYU, yazı AÇIK */
html{color-scheme:dark}
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],
[data-testid="stTextInput"] [data-baseweb="input"] > div,[data-testid="stTextArea"] [data-baseweb="textarea"]{
  background:#0c2a38 !important;background-color:#0c2a38 !important;border-color:rgba(94,234,212,.55) !important;
  border-radius:14px !important}
.stTextInput input,.stTextArea textarea,[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea{
  background:#0c2a38 !important;background-color:#0c2a38 !important;color:#f0fdfa !important;
  -webkit-text-fill-color:#f0fdfa !important;caret-color:#5eead4 !important;
  border:1.5px solid rgba(94,234,212,.4) !important;border-radius:14px !important}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{
  color:#8fc9c3 !important;-webkit-text-fill-color:#8fc9c3 !important;opacity:1 !important}
.stTextInput input:-webkit-autofill,.stTextArea textarea:-webkit-autofill{
  -webkit-text-fill-color:#f0fdfa !important;-webkit-box-shadow:0 0 0 1000px #0c2a38 inset !important}
[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] *{color:#e6fffb !important}
[data-testid="stAlert"]{background:rgba(94,234,212,.12) !important;border:1px solid rgba(94,234,212,.35);border-radius:16px}
[data-testid="stAlert"],[data-testid="stAlert"] *{color:#e6fffb !important}
[data-testid="stForm"]{border:1px solid rgba(94,234,212,.3);border-radius:22px;background:rgba(255,255,255,.04)}
/* AdenMind penceresi (açılır kutu) ve sohbet alanı: koyu zemin */
[data-testid="stPopoverBody"],[data-baseweb="popover"] > div{
  background:#071a24 !important;background-color:#071a24 !important;border:1px solid rgba(94,234,212,.4) !important}
[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"] p{color:#e6fffb}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:rgba(94,234,212,.35) !important}

/* ---- Soru kartı ---- */
.qcard{background:linear-gradient(160deg,rgba(255,255,255,.09),rgba(255,255,255,.03));
  border:2px solid rgba(94,234,212,.45);border-radius:28px;padding:24px 28px;margin:8px 0 16px;
  box-shadow:0 8px 0 rgba(0,0,0,.28),0 20px 40px rgba(0,0,0,.25)}
.qmeta{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;font-weight:800;color:#5eead4}
.score-chip{background:#fef08a;color:#713f12;padding:5px 14px;border-radius:999px;font-weight:800}
.qtext{font-size:clamp(1.15rem,2.4vw,1.7rem);font-weight:800;line-height:1.4;color:#f0fdfa}
.fb{border-radius:24px;padding:18px 22px;margin:10px 0 14px;font-size:1.05rem;color:#fff;
  box-shadow:0 6px 0 rgba(0,0,0,.28)}
.fb.ok{background:linear-gradient(135deg,#059669,#14b8a6)}
.fb.bad{background:linear-gradient(135deg,#e11d48,#fb7185)}
.fb div{margin-top:6px;opacity:.95;font-weight:600}
.result{text-align:center;padding:44px 20px;border-radius:32px;margin:12px 0 18px;
  background:linear-gradient(160deg,rgba(45,212,191,.22),rgba(6,182,212,.10));border:2px solid rgba(94,234,212,.5)}
.result .trophy{font-size:4.5rem;animation:amfloat 2.6s ease-in-out infinite}
.result .big{font-size:3.4rem;font-weight:900;color:#5eead4}
.result .big small{font-size:1.3rem;color:#99f6e4}
.flash{border-radius:30px;padding:28px 30px;text-align:center;color:#fff;margin:10px 0 18px;
  height:240px;display:flex;flex-direction:column;justify-content:center;align-items:center;overflow:hidden;
  box-shadow:0 10px 0 rgba(0,0,0,.3),0 24px 44px rgba(0,0,0,.3)}
.flash .tag{font-size:.9rem;font-weight:800;opacity:.85;margin-bottom:10px}
.flash .txt{font-size:clamp(1.2rem,2.6vw,1.9rem);font-weight:800;line-height:1.4}
.tiles{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:12px 0 18px}
.tile{width:54px;height:62px;border-radius:16px;display:flex;align-items:center;justify-content:center;
  font-size:1.7rem;font-weight:900;background:rgba(255,255,255,.08);border:2px dashed rgba(94,234,212,.5);color:#fef08a}
.tile.on{background:linear-gradient(135deg,#14b8a6,#06b6d4);border:2px solid #5eead4;color:#042f2e;
  box-shadow:0 5px 0 #0f766e}
.gamebar-title{padding:12px 18px;border-radius:18px;background:rgba(255,255,255,.07);
  border:1px solid rgba(94,234,212,.35);font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* ---- AdenMind ---- */
.am-card{display:flex;align-items:center;gap:14px;padding:14px;border-radius:24px;margin-bottom:12px;
  background:linear-gradient(135deg,rgba(45,212,191,.25),rgba(6,182,212,.12));
  border:1px solid rgba(94,234,212,.4);box-shadow:0 6px 0 rgba(0,0,0,.25)}
.am-wrap{position:relative;animation:amfloat 3.2s ease-in-out infinite}
.am-avatar{border-radius:50%;box-shadow:0 0 0 3px rgba(94,234,212,.55),0 8px 22px rgba(6,182,212,.45);vertical-align:middle}
.am-dot{position:absolute;right:1px;bottom:3px;width:14px;height:14px;border-radius:50%;background:#34d399;
  border:2.5px solid #06222c;animation:ampulse 1.8s infinite}
.am-name{font-weight:900;font-size:1.15rem;color:#f0fdfa}
.am-sub{font-size:.78rem;color:#99f6e4;font-weight:600}
.msg{display:flex;gap:8px;margin:9px 0;align-items:flex-end}
.msg.me{justify-content:flex-end}
.bub{max-width:82%;padding:9px 13px;border-radius:18px;font-size:.85rem;line-height:1.45}
.msg.ai .bub{background:rgba(94,234,212,.12);border:1px solid rgba(94,234,212,.3);border-bottom-left-radius:5px;color:#e6fffb}
.msg.me .bub{background:linear-gradient(135deg,#2dd4bf,#06b6d4);color:#042f2e;font-weight:700;border-bottom-right-radius:5px}
@keyframes amfloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
@keyframes ampulse{0%{box-shadow:0 0 0 0 rgba(52,211,153,.7)}70%{box-shadow:0 0 0 9px rgba(52,211,153,0)}100%{box-shadow:0 0 0 0 rgba(52,211,153,0)}}
"""

# Oyun modu: kenar çubuğu ve üst bar gizlenir, oyun tüm ekranı kaplar
GAME_CSS = """
section[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="collapsedControl"],
[data-testid="stHeader"],[data-testid="stToolbar"],footer{display:none !important}
.block-container{max-width:1100px !important;padding:.8rem 1.2rem 1.5rem !important;min-height:100vh}
"""

BALLOON_CSS = """
.block-container{max-width:100% !important;padding:.6rem .8rem !important}
.st-key-balloon_wrap iframe{height:calc(100vh - 96px) !important;width:100% !important;border-radius:26px;
  border:2px solid rgba(94,234,212,.35)}
"""


CARD_H = 150  # TÜM sayfalardaki (ders, ünite, oyun) kartların ortak, sabit yüksekliği


def card_css(key, gradient, height=CARD_H):
    """Bir butonu tamamen oyun kartına çevirir (tek tıkla seçim). Yükseklik sabittir; uzun yazılar kırpılır."""
    return (
        f".st-key-{key}{{margin-bottom:10px}}"
        f".st-key-{key} button{{position:relative;overflow:hidden;height:{CARD_H}px !important;"
        f"min-height:{CARD_H}px !important;max-height:{CARD_H}px !important;padding:10px 16px !important;"
        f"background:{gradient} !important;color:#fff !important;border-radius:28px !important;border:0 !important;"
        f"box-shadow:0 8px 0 rgba(0,0,0,.30),0 18px 32px rgba(0,0,0,.28) !important}}"
        f".st-key-{key} button::after{{content:'';position:absolute;right:-26px;top:-26px;width:100px;height:100px;"
        f"border-radius:50%;background:rgba(255,255,255,.18);pointer-events:none}}"
        f".st-key-{key} button::before{{content:'';position:absolute;left:-18px;bottom:-30px;width:70px;height:70px;"
        f"border-radius:22px;transform:rotate(25deg);background:rgba(255,255,255,.12);pointer-events:none}}"
        f".st-key-{key} button:hover{{transform:translateY(-6px) scale(1.015)}}"
        f".st-key-{key} button:active{{transform:translateY(5px);box-shadow:0 2px 0 rgba(0,0,0,.30) !important}}"
        f".st-key-{key} button p{{color:#fff !important;font-size:1.1rem !important;line-height:1.25 !important;"
        f"margin:0 !important;text-shadow:0 2px 6px rgba(0,0,0,.25)}}"
        f".st-key-{key} button p:first-child{{font-size:2.3rem !important;line-height:1.15 !important;"
        f"-webkit-line-clamp:1 !important}}"
        f".st-key-{key} button > div{{width:100%;height:100%;display:flex;flex-direction:column;"
        f"align-items:center;justify-content:center;gap:4px}}"
        f".st-key-{key} button p{{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;"
        f"overflow:hidden;text-align:center;width:100%}}"
    )


def card_grid(items, cols_n, prefix, on_pick, height):
    """items: [(değer, ikon, ad, gradyan)]. Karta tıklamak doğrudan seçer."""
    css = "".join(card_css(f"{prefix}_{i}", it[3], height) for i, it in enumerate(items))
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    for r in range(0, len(items), cols_n):
        cols = st.columns(cols_n)
        for j, it in enumerate(items[r:r + cols_n]):
            i = r + j
            with cols[j]:
                st.button(f"{it[1]}\n\n**{it[2]}**", key=f"{prefix}_{i}", on_click=on_pick, args=(it[0],))


def md_safe(text):
    """Buton etiketlerinde markdown/LaTeX karışmasını önler."""
    text = str(text).replace("$", "\\$")
    return re.sub(r"^(\s*\d+)([.)])", r"\1\\\2", text)


def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


# =============================================================================
# 6. SORU GÖRSELLERİ (cevabı ifşa etmeyen illüstrasyonlar)
# =============================================================================


def _frame(inner, caption, cap_color, bg, border, w=260, h=180):
    body = (
        '<div style="display:flex;justify-content:center;margin:6px 0">'
        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'style="background:{bg};border-radius:16px;border:1px solid {border}">'
        f'{inner}<rect x="0" y="{h - 30}" width="{w}" height="30" fill="rgba(0,0,0,0.4)"/>'
        f'<text x="{w // 2}" y="{h - 11}" fill="{cap_color}" font-size="12" font-weight="bold" '
        f'text-anchor="middle">{caption}</text></svg></div>'
    )
    components.html(body, height=h + 16)


def render_question_visual(tip, param):
    if not tip or tip == "yok":
        return
    p = str(param).lower()

    if tip in ("ucgen", "aci"):
        deg = 50
        try:
            deg = int(re.search(r"\d+", str(param)).group())
        except Exception:
            pass
        if "dik" in p or deg == 90:
            arc = '<polyline points="115,55 115,65 125,65" fill="none" stroke="#ef4444" stroke-width="2.5"/>'
        else:
            arc = '<path d="M 103 69 A 28 28 0 0 0 147 69" fill="none" stroke="#facc15" stroke-width="3" stroke-linecap="round"/>'
        inner = f"""
        <defs><linearGradient id="tg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="rgba(56,189,248,.25)"/><stop offset="100%" stop-color="rgba(99,102,241,.05)"/></linearGradient></defs>
        <polygon points="125,45 35,145 215,145" fill="url(#tg)" stroke="#38bdf8" stroke-width="3.5" stroke-linejoin="round"/>
        {arc}
        <text x="125" y="35" fill="#38bdf8" font-size="15" font-weight="800" text-anchor="middle">A</text>
        <text x="23" y="150" fill="#38bdf8" font-size="15" font-weight="800">B</text>
        <text x="220" y="150" fill="#38bdf8" font-size="15" font-weight="800">C</text>
        <g transform="translate(107,80)"><rect width="36" height="18" fill="#0f172a" rx="5" stroke="#facc15" stroke-width="1.5"/>
        <text x="18" y="13" fill="#facc15" font-size="11" font-weight="bold" text-anchor="middle">{deg}°</text></g>"""
        _frame(inner, f"📐 m(A) = {deg}° | Geometri Modeli", "#94a3b8",
               "linear-gradient(135deg,#1e293b,#0f172a)", "rgba(56,189,248,.3)")

    elif tip == "ay_evresi":
        inner = """
        <circle cx="30" cy="30" r="1" fill="#fff"/><circle cx="220" cy="40" r="1.5" fill="#fff"/><circle cx="200" cy="130" r="1" fill="#fff"/>
        <circle cx="130" cy="80" r="40" fill="#94a3b8" stroke="#cbd5e1" stroke-width="2"/>
        <circle cx="115" cy="70" r="7" fill="#64748b" opacity=".4"/><circle cx="145" cy="95" r="9" fill="#64748b" opacity=".4"/>
        <circle cx="130" cy="60" r="5" fill="#64748b" opacity=".4"/>
        <path d="M 130 40 A 40 40 0 0 1 130 120 Z" fill="rgba(15,23,42,.75)"/>"""
        _frame(inner, "🌕 Ay Gözlem Modeli", "#38bdf8", "linear-gradient(135deg,#0b1329,#1c2541)", "#38bdf8")

    elif tip == "gunes":
        inner = """
        <defs><radialGradient id="sun" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#fffbeb"/>
        <stop offset="40%" stop-color="#f59e0b"/><stop offset="90%" stop-color="#ea580c"/><stop offset="100%" stop-color="#b91c1c"/></radialGradient></defs>
        <circle cx="130" cy="80" r="54" fill="none" stroke="#fde047" stroke-width="3" stroke-dasharray="8,6" opacity=".7"/>
        <circle cx="130" cy="80" r="45" fill="url(#sun)"/>
        <circle cx="115" cy="70" r="4" fill="#7f1d1d" opacity=".8"/><circle cx="145" cy="90" r="5" fill="#7f1d1d" opacity=".8"/>
        <circle cx="130" cy="95" r="3" fill="#7f1d1d" opacity=".8"/>"""
        _frame(inner, "☀️ Güneş Yüzeyi ve Katmanları", "#facc15", "linear-gradient(135deg,#0f172a,#2e1005)", "#f59e0b")

    elif tip == "dunya":
        inner = """
        <defs><radialGradient id="earth" cx="40%" cy="40%" r="60%"><stop offset="0%" stop-color="#38bdf8"/>
        <stop offset="70%" stop-color="#0284c7"/><stop offset="100%" stop-color="#0369a1"/></radialGradient></defs>
        <circle cx="130" cy="80" r="44" fill="url(#earth)" stroke="#60a5fa" stroke-width="2"/>
        <path d="M 105 60 Q 125 45 140 65 Q 130 90 105 75 Z" fill="#15803d" opacity=".9"/>
        <path d="M 125 95 Q 150 85 155 110 Q 130 115 120 95 Z" fill="#15803d" opacity=".9"/>
        <path d="M 100 55 Q 110 50 120 55" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".7"/>
        <path d="M 135 95 Q 145 90 155 95" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".7"/>
        <line x1="112" y1="25" x2="148" y2="135" stroke="#facc15" stroke-width="2" stroke-dasharray="4,4"/>"""
        _frame(inner, "🌍 Dünya ve Atmosfer Modeli", "#38bdf8", "linear-gradient(135deg,#0284c7,#0f172a)", "#38bdf8")

    elif tip == "karsilastirma":
        inner = """
        <circle cx="55" cy="80" r="36" fill="#f59e0b" stroke="#facc15" stroke-width="2"/>
        <circle cx="55" cy="80" r="28" fill="#ea580c" opacity=".5"/>
        <text x="55" y="84" fill="#fff" font-size="10" font-weight="bold" text-anchor="middle">Güneş</text>
        <circle cx="155" cy="80" r="15" fill="#0284c7" stroke="#38bdf8" stroke-width="1.5"/>
        <path d="M 150 75 Q 155 72 160 78 Z" fill="#15803d"/>
        <text x="155" y="106" fill="#38bdf8" font-size="10" font-weight="bold" text-anchor="middle">Dünya</text>
        <circle cx="215" cy="80" r="6" fill="#94a3b8" stroke="#cbd5e1" stroke-width="1"/>
        <text x="215" y="100" fill="#cbd5e1" font-size="9" font-weight="bold" text-anchor="middle">Ay</text>"""
        _frame(inner, "🔭 Boyut Karşılaştırma Modeli", "#c084fc", "linear-gradient(135deg,#0b1329,#1c2541)", "#a855f7")

    elif tip == "tutulma":
        inner = """
        <polygon points="35,80 140,65 140,95" fill="rgba(250,204,21,.15)"/>
        <circle cx="35" cy="80" r="22" fill="#f59e0b" stroke="#fde047" stroke-width="1.5"/>
        <circle cx="130" cy="80" r="8" fill="#94a3b8" stroke="#cbd5e1" stroke-width="1"/>
        <circle cx="205" cy="80" r="16" fill="#0284c7" stroke="#38bdf8" stroke-width="1.5"/>
        <path d="M 200 75 Q 205 72 210 78 Z" fill="#15803d"/>"""
        _frame(inner, "🪐 Gök Cisimlerinin Dizilimi", "#f87171", "linear-gradient(135deg,#0f172a,#030712)", "#ef4444")

    elif tip == "dinamometre":
        newton = 5
        try:
            newton = int(re.search(r"\d+", str(param)).group())
        except Exception:
            pass
        sy = 40 + min(newton * 7, 75)
        inner = f"""
        <circle cx="90" cy="15" r="8" fill="none" stroke="#94a3b8" stroke-width="3"/>
        <rect x="75" y="23" width="30" height="12" fill="#64748b" rx="3"/>
        <rect x="55" y="35" width="70" height="135" fill="rgba(56,189,248,.1)" stroke="#38bdf8" stroke-width="3" rx="8"/>
        <line x1="60" y1="50" x2="70" y2="50" stroke="#94a3b8" stroke-width="2"/><line x1="60" y1="70" x2="70" y2="70" stroke="#94a3b8" stroke-width="2"/>
        <line x1="60" y1="90" x2="70" y2="90" stroke="#94a3b8" stroke-width="2"/><line x1="60" y1="110" x2="70" y2="110" stroke="#94a3b8" stroke-width="2"/>
        <line x1="60" y1="130" x2="70" y2="130" stroke="#94a3b8" stroke-width="2"/>
        <path d="M 90 35 Q 65 {35 + sy / 4} 115 {35 + sy / 2} Q 65 {35 + 3 * sy / 4} 90 {35 + sy}" fill="none" stroke="#facc15" stroke-width="3.5"/>
        <rect x="65" y="{35 + sy}" width="50" height="20" fill="#f43f5e" rx="4"/>
        <text x="90" y="{49 + sy}" fill="#fff" font-size="12" font-weight="bold" text-anchor="middle">{newton} N</text>
        <path d="M 90 {55 + sy} L 90 {75 + sy}" fill="none" stroke="#94a3b8" stroke-width="3"/>"""
        _frame(inner, "⚙️ Dinamometre", "#38bdf8", "#0f172a", "#38bdf8", w=180, h=240)


# =============================================================================
# 7. ADENMIND CANLI ASİSTAN
# =============================================================================


def chat_bubble(role, content):
    text = esc(content).replace("\n", "<br>")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    if role == "assistant":
        return f'<div class="msg ai">{adenmind_avatar(30)}<div class="bub">{text}</div></div>'
    return f'<div class="msg me"><div class="bub">{text}</div></div>'


def render_adenmind(ns):
    st.markdown(
        f'<div class="am-card"><div class="am-wrap">{adenmind_avatar(64)}<span class="am-dot"></span></div>'
        '<div><div class="am-name">AdenMind</div><div class="am-sub">Canlı Asistan · çevrimiçi</div></div></div>',
        unsafe_allow_html=True,
    )
    box = st.container(height=300)
    with st.form(f"chat_form_{ns}", clear_on_submit=True):
        user_msg = st.text_input(
            "Mesaj", label_visibility="collapsed", key=f"chat_in_{ns}", placeholder="AdenMind'e bir şey sor..."
        )
        sent = st.form_submit_button("Gönder 🚀")
    msgs = st.session_state["coach_messages"]
    if sent and user_msg.strip():
        msgs.append({"role": "user", "content": user_msg.strip()})
        prompt = (
            "Sen 5. sınıf MEB müfredatı odaklı, sevimli ve bilgili akıllı koçsun. Adın AdenMind. "
            f"Öğrencinin dersi: {st.session_state.get('selected_subject') or 'Genel'}, "
            f"ünite: {st.session_state.get('selected_unit') or 'Genel Konu'}. "
            f"Öğrencinin sorusu: {user_msg.strip()}. Kısa ve sevimli rehberlik yap."
        )
        with st.spinner("AdenMind düşünüyor..."):
            reply = ai_generate_content(prompt)
        msgs.append({"role": "assistant", "content": reply or "Yanıt oluşturulamadı, tekrar dene!"})
    with box:
        st.markdown("".join(chat_bubble(m["role"], m["content"]) for m in msgs), unsafe_allow_html=True)


# =============================================================================
# 8. ORTAK OYUN YARDIMCILARI
# =============================================================================
FS_BUTTON = """<!DOCTYPE html><html><body style="margin:0;background:transparent">
<button id="fs" style="width:100%;height:46px;border:0;border-radius:18px;font-weight:800;font-size:15px;cursor:pointer;
font-family:'Segoe UI',system-ui,sans-serif;color:#042f2e;background:linear-gradient(135deg,#5eead4,#22d3ee);
box-shadow:0 5px 0 #0f766e">⛶ Tam Ekran</button>
<script>
document.getElementById('fs').onclick=function(){
  try{
    var d=window.parent.document, el=d.documentElement;
    if(!d.fullscreenElement&&!d.webkitFullscreenElement){(el.requestFullscreen||el.webkitRequestFullscreen).call(el);}
    else{(d.exitFullscreen||d.webkitExitFullscreen).call(d);}
  }catch(e){var e2=document.documentElement;(e2.requestFullscreen||e2.webkitRequestFullscreen).call(e2);}
};
</script></body></html>"""


def game_topbar(title):
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.3, 1.5, 3.3, 1.4])
    with c1:
        st.button("⬅️ Geri", key="back_game", on_click=back_to_games)
    with c2:
        components.html(FS_BUTTON, height=52)
    with c3:
        st.button("🔁 Yeni Sorular", key="regen_btn", on_click=regen)
    with c4:
        st.markdown(f'<div class="gamebar-title">{esc(title)}</div>', unsafe_allow_html=True)
    with c5:
        with st.popover("💬 AdenMind"):
            render_adenmind("pop")


def _retry(gs):
    gs["failed"] = False


# --- Tekrarsız içerik: daha önce sorulanlar (tüm oyunlar için ortak, dosyada kalıcı) ---
_HIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soru_gecmisi.json")
_STOP = {
    "aşağıdakilerden", "aşağıdaki", "hangisi", "hangisidir", "hangisinde", "hangileri", "nedir", "kaçtır", "için",
    "olan", "olarak", "ile", "bir", "bu", "şu", "ve", "veya", "gibi", "daha", "çok", "göre", "kadar", "değildir",
    "doğrudur", "yanlıştır", "doğru", "yanlış", "ifadelerden", "cümlelerden", "söylenebilir", "ifade", "soru", "cevap",
    "which", "the", "what", "is", "are", "and", "for", "welche", "der", "die", "das", "ist", "und",
}
_STYLES = [
    "günlük hayat senaryosu", "neden-sonuç ilişkisi", "karşılaştırma", "tablo/liste/veri yorumlama",
    "'hangisi yanlıştır?' biçimi", "kısa problem çözme", "kavram tanımlama", "örnek bulma", "çıkarım yapma",
    "gözlem/deney yorumu", "kural/özellik bilgisi", "tahmin ve sonuç çıkarma",
]
_SEEDS = [
    "market", "okul bahçesi", "uzay", "futbol", "mutfak", "harita", "müze", "orman", "deniz", "pazar", "kütüphane",
    "bisiklet", "bahçe", "tren yolculuğu", "doğum günü", "kamp", "hayvanat bahçesi", "kitap fuarı", "pastane",
    "bilim şenliği", "köy", "liman", "tiyatro", "yağmurlu gün", "piknik", "spor salonu", "gökyüzü", "çiftlik",
]


@st.cache_resource
def _hist_store():
    try:
        with open(_HIST_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def hist_get(scope, limit=150):
    return list(_hist_store().get(scope, []))[-limit:]


def hist_add(scope, stems):
    h = _hist_store()
    lst = h.setdefault(scope, [])
    lst.extend(s[:140] for s in stems if s)
    del lst[:-150]
    try:
        tmp = _HIST_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False)
        os.replace(tmp, _HIST_PATH)
    except Exception:
        pass  # dosya yazılamıyorsa geçmiş yalnızca bellekte tutulur


def _norm(s):
    s = str(s).replace("I", "ı").replace("İ", "i").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def _tok(s):
    # Sayılar da sayılır: "12 kalemden 5'i" ile "15 kalemden 7'si" farklı problemlerdir.
    return {w for w in _norm(s).split() if (len(w) > 2 or any(c.isdigit() for c in w)) and w not in _STOP}


def is_dup(stem, others, thr=0.8):
    na, ta = _norm(stem), _tok(stem)
    for o in others:
        if na == _norm(o):
            return True
        tb = _tok(o)
        if ta and tb and len(ta & tb) / len(ta | tb) >= thr:
            return True
    return False


def item_stem(it):
    if not isinstance(it, dict):
        return ""
    for k in ("soru", "ifade", "cumle", "on_yuz", "senaryo"):
        if it.get(k):
            return str(it[k])
    if it.get("kelime"):
        return f"{it['kelime']} {it.get('ipucu', '')}"
    return ""


def shuffle_item(it):
    """Doğru şık hep aynı harfte çıkmasın diye şıkları karıştırır."""
    try:
        if "secenekler" in it and "dogru_cevap" in it:
            ans = str(it["dogru_cevap"]).strip()[:1].upper()
            opts = [re.sub(r"^\s*[A-Da-d][\)\.\:\-]\s*", "", str(o)).strip() for o in it["secenekler"]]
            if ans and ans in "ABCD" and len(opts) <= 4 and all(opts) and "ABCD".index(ans) < len(opts):
                right = opts[" ABCD".index(ans) - 1]
                random.shuffle(opts)
                it["secenekler"] = [f"{'ABCD'[i]}) {o}" for i, o in enumerate(opts)]
                it["dogru_cevap"] = "ABCD"[opts.index(right)]
        elif "secenekler" in it and "dogru_kelime" in it:
            random.shuffle(it["secenekler"])
    except Exception:
        pass
    return it


def diversity_block(seen, n):
    lines = ["", "ÇEŞİTLİLİK KURALLARI:",
             "- Her öğe ünitenin FARKLI bir alt konusunu/kazanımını işlesin; hiçbiri diğerine benzemesin.",
             "- Biçim çeşitliliği için sırasıyla şunlardan yararlan: "
             + "; ".join(random.sample(_STYLES, min(len(_STYLES), max(3, n)))) + ".",
             "- Senaryo/örnek ilhamı: " + ", ".join(random.sample(_SEEDS, 3)) + "."]
    if seen:
        lines.append("DAHA ÖNCE SORULANLAR (bunları ve benzerlerini KESİNLİKLE tekrar etme):")
        lines += [f"- {s[:90]}" for s in seen[-40:]]
    lines.append("Yalnızca istenen biçimde geçerli JSON döndür.")
    return "\n".join(lines)


def load_data(gs, prompt, expect, required=(), msg="Hazırlanıyor..."):
    """Veri yoksa yapay zekadan otomatik üretir. Önceki oyunlarda sorulanlar tekrar edilmez."""
    if gs["data"] is not None:
        return gs["data"]
    if not gs["failed"]:
        scope = f"{st.session_state['selected_subject']}|{st.session_state['selected_unit']}"
        seen = hist_get(scope)
        m = re.search(r"TAM (\d+) ADET", prompt, re.I)
        n = int(m.group(1)) if (m and expect is list) else 0
        data, stems = None, []
        with st.spinner(msg):
            if expect is list and n:
                fresh, last_valid = [], None
                for _ in range(3):  # tekrar edenler elenirse eksik kalanı yeniden iste
                    need = n - len(fresh)
                    if need <= 0:
                        break
                    p = re.sub(r"TAM \d+ ADET", f"TAM {need + 1} ADET", prompt, flags=re.I)
                    got = parse_json(ai_generate_content(p + diversity_block(seen + stems, need + 1)))
                    if not is_valid(got, list, required):
                        continue
                    last_valid = got
                    for it in got:
                        s = item_stem(it)
                        if s and is_dup(s, seen + stems):
                            continue
                        fresh.append(shuffle_item(it))
                        stems.append(s)
                if len(fresh) >= min(3, n):
                    data = fresh[:n]
                    stems = stems[:n]
                elif last_valid:  # yapay zekâ hep aynı şeyleri verdiyse oyunu yine de aç
                    data = [shuffle_item(i) for i in last_valid[:n]]
                    stems = [item_stem(i) for i in data]
            else:
                for _ in range(2):
                    extra = ""
                    if seen:
                        extra = ("\nDAHA ÖNCE İŞLENENLER (bunlardan FARKLI bir konu/senaryo seç):\n"
                                 + "\n".join(f"- {s[:110]}" for s in seen[-20:])
                                 + "\nİlham için: " + ", ".join(random.sample(_SEEDS, 3)) + ".")
                    raw = ai_generate_content(prompt + extra)
                    got = raw.strip() if (expect is str and raw) else parse_json(raw)
                    if not is_valid(got, expect, required):
                        continue
                    s = item_stem(got) if expect is dict else str(got)[:100]
                    data, stems = got, [s]
                    if not (s and is_dup(s, seen)):
                        break
        if data is not None:
            hist_add(scope, stems)
            gs.update(data=data, idx=0, score=0, feedback=None)
            st.rerun()
        gs["failed"] = True
    st.error("İçerik üretilemedi. API anahtarlarını kontrol edip tekrar deneyin.")
    st.button("🔄 Tekrar Dene", key="retry", on_click=_retry, args=(gs,))
    return None


def ctx():
    return (
        f"Rastgelelik Kimliği: {random.randint(10000, 999999)}\n"
        f"5. Sınıf MEB müfredatı, Ders: {st.session_state['selected_subject']}, "
        f"Ünite: {st.session_state['selected_unit']}.\n"
    )


VISUAL_RULES = """
GÖRSEL VE NESNE KURALLARI:
1. K, L, M gibi soyut harfler yerine gerçek nesne adlarını kullan (Dünya, Ay, Güneş, Dinamometre vb.).
2. Görsel asla doğru cevabı ifşa etmemeli; yalnızca konuyu betimlemeli.
3. Sadece konuya gerçekten uygunsa 'gorsel_tipi' alanına şunlardan birini yaz:
   'gunes','dunya','ay_evresi','karsilastirma','tutulma','dinamometre' (Fen Bilimleri),
   'ucgen' (Matematik, üçgen/açı; gorsel_parametre örn. '50 derece').
4. Görsel gerekmeyen tüm sorularda gorsel_tipi: 'yok', gorsel_parametre: '' yaz.
"""

MCQ_FORMAT = """
Yalnızca geçerli JSON liste döndür, başka metin yazma:
[{"soru":"...","secenekler":["A) ...","B) ...","C) ...","D) ..."],"dogru_cevap":"A","aciklama":"...","gorsel_tipi":"yok","gorsel_parametre":""}]
"""


# --- Tek soru modu motoru (Kazanım, Doğru/Yanlış, Boşluk Doldurma) ---
def _same(a, b):
    return str(a).strip().lower() == str(b).strip().lower()


def _answer(gs, value, q, per_q):
    ok = _same(value, q["correct"])
    if ok:
        gs["score"] += per_q
    label = next((lab for lab, val in q["options"] if _same(val, q["correct"])), q["correct"])
    gs["feedback"] = {"ok": ok, "label": label, "expl": q["expl"]}


def _next(gs):
    gs["idx"] += 1
    gs["feedback"] = None


def run_quiz(gs, items, build):
    total = len(items)
    idx = gs["idx"]
    per_q = max(1, 100 // total)

    if idx >= total:
        score = gs["score"]
        stars = "⭐" * max(1, round(score / 20)) if score > 0 else "💪"
        st.markdown(
            f'<div class="result"><div class="trophy">🏆</div><h2>Oyun Tamamlandı!</h2>'
            f'<div class="big">{score}<small> / 100</small></div><div style="font-size:2rem">{stars}</div></div>',
            unsafe_allow_html=True,
        )
        st.button("🔄 Yeni Sorularla Tekrar Oyna", key="again", on_click=regen)
        return

    q = build(items[idx])
    st.progress(idx / total)
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>Soru {idx + 1} / {total}</span>'
        f'<span class="score-chip">⭐ {gs["score"]} puan</span></div>'
        f'<div class="qtext">{esc(str(q["text"]))}</div></div>',
        unsafe_allow_html=True,
    )
    vt, vp = q["visual"]
    if vt and vt != "yok":
        render_question_visual(vt, vp)

    fb = gs["feedback"]
    if fb:
        if fb["ok"]:
            head, cls = "🎉 Harika, doğru cevap!", "ok"
        else:
            head, cls = f"❌ Olmadı! Doğru cevap: {esc(str(fb['label']))}", "bad"
        st.markdown(
            f'<div class="fb {cls}"><b>{head}</b><div>{esc(str(fb["expl"]))}</div></div>', unsafe_allow_html=True
        )
        st.button(
            "➡️ Sonraki Soru" if idx < total - 1 else "🏆 Sonucu Gör",
            key=f"next_{idx}", on_click=_next, args=(gs,),
        )
    else:
        with st.container(key="optbox"):
            ocols = st.columns(2)
            for i, (label, value) in enumerate(q["options"]):
                with ocols[i % 2]:
                    st.button(md_safe(label), key=f"opt_{idx}_{i}", on_click=_answer, args=(gs, value, q, per_q))
        st.button("⏭️ Pas Geç", key=f"pass_{idx}", on_click=_next, args=(gs,))


def build_mcq(q):
    opts = [(o, "ABCD"[i] if i < 4 else str(i)) for i, o in enumerate(q["secenekler"])]
    return {
        "text": q["soru"], "options": opts, "correct": str(q["dogru_cevap"]).strip()[:1].upper(),
        "expl": q.get("aciklama", ""), "visual": (q.get("gorsel_tipi"), q.get("gorsel_parametre", "")),
    }


def build_tf(q):
    return {
        "text": q["ifade"], "options": [("✅ DOĞRU", "D"), ("❌ YANLIŞ", "Y")],
        "correct": str(q["cevap"]).strip()[:1].upper(), "expl": q.get("aciklama", ""),
        "visual": (q.get("gorsel_tipi"), q.get("gorsel_parametre", "")),
    }


def build_fill(q):
    return {
        "text": q["cumle"], "options": [(o, o) for o in q["secenekler"]], "correct": q["dogru_kelime"],
        "expl": f"Doğru kelime: {q['dogru_kelime']}",
        "visual": (q.get("gorsel_tipi"), q.get("gorsel_parametre", "")),
    }


# =============================================================================
# 9. BALON PATLATMACA (tam ekran HTML oyunu)
# =============================================================================
BALLOON_HTML = """<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}
html,body{margin:0;height:100%;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif;color:#e6fffb}
body{background:radial-gradient(circle,rgba(94,234,212,.10) 2px,transparent 2.6px) 0 0/40px 40px,
 radial-gradient(900px 500px at 12% 0%,rgba(45,212,191,.28),transparent 60%),
 radial-gradient(700px 500px at 100% 100%,rgba(6,182,212,.24),transparent 60%),#071a24}
#app{position:relative;width:100%;height:100%;overflow:hidden}
#sky{position:absolute;inset:0;overflow:hidden}
.timer{position:absolute;top:0;left:0;height:7px;width:100%;z-index:8;background:linear-gradient(90deg,#2dd4bf,#22d3ee);transition:width .1s linear}
.timer.low{background:linear-gradient(90deg,#f43f5e,#fb923c)}
.hud{position:absolute;top:14px;left:0;right:0;display:flex;justify-content:space-between;gap:10px;padding:0 16px;z-index:7}
.chip{background:rgba(7,26,36,.75);border:1.5px solid rgba(94,234,212,.5);border-radius:999px;padding:8px 18px;font-weight:800;
 backdrop-filter:blur(6px);font-size:clamp(13px,1.6vw,17px)}
.chip.s{background:#fef08a;color:#713f12;border-color:#fde047}
#q{position:absolute;top:62px;left:50%;transform:translateX(-50%);width:min(94%,920px);z-index:7;text-align:center;
 background:rgba(7,26,36,.85);border:2px solid rgba(94,234,212,.55);border-radius:26px;padding:14px 22px;
 font-size:clamp(15px,2.3vw,24px);font-weight:800;line-height:1.35;box-shadow:0 8px 0 rgba(0,0,0,.3)}
.balloon{position:absolute;bottom:-200px;width:clamp(120px,20vw,215px);aspect-ratio:.82;cursor:pointer;z-index:3;
 animation:rise var(--d,9s) linear infinite;-webkit-tap-highlight-color:transparent}
.balloon .in{width:100%;height:100%;border-radius:50% 50% 48% 48%/55% 55% 45% 45%;
 background:radial-gradient(circle at 32% 26%,rgba(255,255,255,.6),transparent 36%),linear-gradient(160deg,var(--c1),var(--c2));
 display:flex;align-items:center;justify-content:center;text-align:center;padding:14% 12% 20%;font-weight:800;
 font-size:clamp(12px,1.55vw,17px);line-height:1.2;color:#fff;text-shadow:0 2px 4px rgba(0,0,0,.35);
 box-shadow:inset -10px -14px 26px rgba(0,0,0,.2),0 14px 26px rgba(0,0,0,.35);animation:sway 2.6s ease-in-out infinite alternate}
.balloon::after{content:"";position:absolute;left:50%;top:99%;width:2px;height:70px;background:rgba(255,255,255,.35);transform:translateX(-50%)}
.balloon:hover .in{filter:brightness(1.12)}
.balloon.paused{animation-play-state:paused;cursor:default}
.balloon.right .in{animation:none;outline:7px solid #34d399;transform:scale(1.1)}
.balloon.wrong .in{animation:shake .45s;outline:7px solid #fb7185}
.balloon.fade{opacity:.15;transition:opacity .4s}
@keyframes rise{from{transform:translateY(0)}to{transform:translateY(-150vh)}}
@keyframes sway{from{transform:rotate(-3deg) translateX(-6px)}to{transform:rotate(3deg) translateX(6px)}}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-12px)}75%{transform:translateX(12px)}}
.banner{position:absolute;left:50%;bottom:20px;transform:translateX(-50%) translateY(40px);opacity:0;z-index:9;
 width:min(94%,760px);text-align:center;padding:16px 22px;border-radius:24px;font-weight:800;color:#fff;
 font-size:clamp(14px,1.9vw,19px);transition:all .3s;pointer-events:none;box-shadow:0 8px 0 rgba(0,0,0,.3)}
.banner.show{opacity:1;transform:translateX(-50%) translateY(0)}
.banner.ok{background:linear-gradient(135deg,#059669,#14b8a6)}
.banner.bad{background:linear-gradient(135deg,#e11d48,#fb7185)}
.banner small{display:block;margin-top:6px;font-weight:600;opacity:.95}
#end{position:absolute;inset:0;z-index:20;display:none;align-items:center;justify-content:center;flex-direction:column;
 gap:14px;background:rgba(7,26,36,.92);text-align:center}
#end .t{font-size:clamp(60px,12vw,110px)}
#end .sc{font-size:clamp(34px,6vw,64px);font-weight:900;color:#5eead4}
#end button{border:0;border-radius:20px;padding:16px 34px;font-size:18px;font-weight:800;cursor:pointer;color:#042f2e;
 background:linear-gradient(135deg,#5eead4,#22d3ee);box-shadow:0 6px 0 #0f766e}
</style></head><body>
<div id="app">
  <div class="timer" id="bar"></div>
  <div class="hud"><div class="chip" id="qc">Soru 1</div><div class="chip" id="tm">⏱ 30</div><div class="chip s" id="sc">⭐ 0</div></div>
  <div id="q"></div>
  <div id="sky"></div>
  <div class="banner" id="bn"></div>
  <div id="end"><div class="t">🏆</div><div style="font-size:clamp(20px,3vw,30px);font-weight:800">Oyun Tamamlandı!</div>
   <div class="sc" id="fsc"></div><button id="again">🔄 Aynı Sorularla Tekrar Oyna</button></div>
</div>
<script>
const Q = __QUESTIONS__;
const COLORS=[['#14b8a6','#0f766e'],['#06b6d4','#0e7490'],['#8b5cf6','#5b21b6'],['#f43f5e','#be123c']];
const TIME=30; const total=Q.length;
let idx=0,score=0,timer=null,locked=false;
const $=id=>document.getElementById(id);
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
function load(){
  clearInterval(timer);
  if(idx>=total){finish();return}
  locked=false;
  const q=Q[idx];
  $('qc').textContent='Soru '+(idx+1)+' / '+total;
  $('sc').textContent='⭐ '+score;
  $('q').textContent=q.soru;
  $('bn').className='banner';
  const sky=$('sky'); sky.innerHTML='';
  const opts=q.secenekler.slice(0,4);
  const slots=shuffle(opts.map((_,i)=>i));
  const correct='ABCD'.indexOf(String(q.dogru_cevap).trim().charAt(0).toUpperCase());
  opts.forEach((opt,i)=>{
    const b=document.createElement('div'); b.className='balloon';
    const c=COLORS[i%4];
    b.style.setProperty('--c1',c[0]); b.style.setProperty('--c2',c[1]);
    b.style.left=(3+slots[i]*24.5)+'%';
    b.style.setProperty('--d',(8+Math.random()*3).toFixed(1)+'s');
    b.style.animationDelay='-'+(Math.random()*6).toFixed(1)+'s';
    const inner=document.createElement('div'); inner.className='in'; inner.textContent=opt;
    b.appendChild(inner);
    b.onclick=()=>answer(i,correct);
    sky.appendChild(b);
  });
  const start=Date.now();
  timer=setInterval(()=>{
    const left=Math.max(0,TIME-(Date.now()-start)/1000);
    $('tm').textContent='⏱ '+Math.ceil(left);
    $('bar').style.width=(left/TIME*100)+'%';
    $('bar').className='timer'+(left<8?' low':'');
    if(left<=0){answer(-1,correct)}
  },100);
}
function answer(i,correct){
  if(locked)return; locked=true; clearInterval(timer);
  const q=Q[idx]; const ok=(i===correct);
  const pts=Math.round(100/total);
  if(ok)score+=pts;
  $('sc').textContent='⭐ '+score;
  document.querySelectorAll('.balloon').forEach((b,j)=>{
    b.classList.add('paused');
    if(j===correct)b.classList.add('right'); else if(j===i)b.classList.add('wrong'); else b.classList.add('fade');
  });
  const bn=$('bn');
  const head=ok?('🎉 Harika! +'+pts+' puan'):((i<0?'⏰ Süre doldu! ':'❌ Olmadı! ')+'Doğru cevap: '+(q.secenekler[correct]||''));
  bn.textContent=head;
  if(q.aciklama){const s=document.createElement('small'); s.textContent=q.aciklama; bn.appendChild(s);}
  bn.className='banner show '+(ok?'ok':'bad');
  setTimeout(()=>{idx++;load()},2800);
}
function finish(){
  $('fsc').textContent=score+' / 100';
  $('end').style.display='flex';
}
$('again').onclick=()=>{idx=0;score=0;$('end').style.display='none';load()};
load();
</script></body></html>"""


# =============================================================================
# 10. ANA AKIŞ
# =============================================================================
subj = st.session_state["selected_subject"]
unit = st.session_state["selected_unit"]
game = st.session_state["selected_game"]
in_game = bool(subj and unit and game)

css = BASE_CSS + (GAME_CSS if in_game else "") + (BALLOON_CSS if in_game and game == "balon" else "")
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# --- Kenar çubuğu: oyun dışında görünür ---
if not in_game:
    with st.sidebar:
        st.button("🏠 Ana Sayfaya Dön", key="home_btn", on_click=go_home)
        st.markdown("---")
        render_adenmind("side")

# --- Üst başlık: oyun dışında görünür ---
if not in_game:
    st.markdown(
        '<div class="hero"><div class="badge">🎒</div><div><h1>MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi</h1>'
        "<small>AdenMind Koçluk · Murat KANDIRMAZ</small></div></div>",
        unsafe_allow_html=True,
    )

# --- AŞAMA 1: DERS SEÇİMİ (karta tıklamak yeterli) ---
if not subj:
    st.markdown('<div class="section-title">🌟 Çalışmak istediğin dersi seç</div>', unsafe_allow_html=True)
    items = [(name, d["ikon"], name, d["renk"]) for name, d in MEB_CURRICULUM.items()]
    card_grid(items, 3, "sub", pick_subject, CARD_H)

# --- AŞAMA 2: ÜNİTE SEÇİMİ ---
elif not unit:
    data = MEB_CURRICULUM[subj]
    st.markdown(
        f'<div class="crumb"><span class="pill">{data["ikon"]} {esc(subj)}</span><span>›</span>'
        '<span class="pill alt">Ünite seç</span></div>',
        unsafe_allow_html=True,
    )
    st.button("⬅️ Ders Seçimine Dön", key="back_subj", on_click=go_home)
    st.markdown('<div class="section-title">📚 Hangi üniteyi çalışalım?</div>', unsafe_allow_html=True)
    items = [(u, "📖", u, data["renk"]) for u in data["uniteler"]]
    card_grid(items, 3, "unit", pick_unit, CARD_H)

# --- AŞAMA 3: OYUN SEÇİMİ ---
elif not game:
    data = MEB_CURRICULUM[subj]
    st.markdown(
        f'<div class="crumb"><span class="pill">{data["ikon"]} {esc(subj)}</span><span>›</span>'
        f'<span class="pill alt">{esc(unit)}</span></div>',
        unsafe_allow_html=True,
    )
    st.button("↩️ Ünite Değiştir", key="back_unit", on_click=back_to_units)
    st.markdown('<div class="section-title">🎮 Bir oyun seç, hemen başlasın!</div>', unsafe_allow_html=True)
    items = [(g[0], g[1], g[2], g[3]) for g in GAMES]
    card_grid(items, 3, "game", pick_game, CARD_H)

# --- AŞAMA 4: OYUN (tam ekran düzeni) ---
else:
    gs = get_gs(game)
    ikon = GAME_INFO[game][1]
    game_topbar(f"{ikon} {GAME_INFO[game][2]} · {subj} · {unit}")

    # 1. Balon patlatmaca
    if game == "balon":
        prompt = (
            ctx() + "TAM 5 ADET özgün, gerçek hayat senaryolu çoktan seçmeli (A, B, C, D) soru üret.\n"
            + VISUAL_RULES + MCQ_FORMAT
        )
        data = load_data(gs, prompt, list, ("soru", "secenekler", "dogru_cevap"), "Balon soruları hazırlanıyor...")
        if data:
            payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
            with st.container(key="balloon_wrap"):
                components.html(BALLOON_HTML.replace("__QUESTIONS__", payload), height=760)

    # 2. 5 soruluk kazanım yarışması
    elif game == "sinav10":
        prompt = ctx() + "TAM 5 ADET yepyeni çoktan seçmeli (4 şıklı) soru üret.\n" + VISUAL_RULES + MCQ_FORMAT
        data = load_data(gs, prompt, list, ("soru", "secenekler", "dogru_cevap"), "Kazanım soruları hazırlanıyor...")
        if data:
            run_quiz(gs, data, build_mcq)

    # 3. Doğru / Yanlış
    elif game == "dogruyanlis":
        prompt = (
            ctx() + "TAM 5 ADET yepyeni Doğru veya Yanlış önermesi üret. Doğru ve yanlış önermeleri dengeli dağıt.\n"
            + VISUAL_RULES
            + 'Yalnızca geçerli JSON liste döndür: [{"ifade":"...","cevap":"D","aciklama":"...",'
            '"gorsel_tipi":"yok","gorsel_parametre":""}] (cevap yalnızca D veya Y olsun).'
        )
        data = load_data(gs, prompt, list, ("ifade", "cevap"), "Önermeler hazırlanıyor...")
        if data:
            run_quiz(gs, data, build_tf)

    # 4. Boşluk doldurma
    elif game == "bosluk":
        prompt = (
            ctx() + "Cümle içinde boşluk (____) bırakılmış TAM 5 adet soru üret. Her soruda 4 seçenek olsun.\n"
            + VISUAL_RULES
            + 'Yalnızca geçerli JSON liste döndür: [{"cumle":"... ____ ...","dogru_kelime":"...",'
            '"secenekler":["...","...","...","..."],"gorsel_tipi":"yok","gorsel_parametre":""}]'
        )
        data = load_data(gs, prompt, list, ("cumle", "dogru_kelime", "secenekler"), "Sorular hazırlanıyor...")
        if data:
            run_quiz(gs, data, build_fill)

    # 5. Soru kartları
    elif game == "kartlar":
        prompt = (
            ctx() + "TAM 5 ADET yepyeni flashcard üret. Yalnızca geçerli JSON liste döndür: "
            '[{"on_yuz":"...","arka_yuz":"..."}]'
        )
        data = load_data(gs, prompt, list, ("on_yuz", "arka_yuz"), "Kartlar hazırlanıyor...")
        if data:
            idx = gs["idx"]
            if idx < len(data):
                card = data[idx]
                st.progress(idx / len(data))
                st.markdown(
                    f'<div class="flash" style="background:linear-gradient(135deg,#0d9488,#06b6d4)">'
                    f'<div class="tag">Kart {idx + 1} / {len(data)}</div>'
                    f'<div class="txt">❓ {esc(str(card["on_yuz"]))}</div></div>',
                    unsafe_allow_html=True,
                )
                if gs["show"]:
                    st.markdown(
                        f'<div class="flash" style="background:linear-gradient(135deg,#7c3aed,#d946ef)">'
                        f'<div class="tag">Cevap / Açıklama</div>'
                        f'<div class="txt">💡 {esc(str(card["arka_yuz"]))}</div></div>',
                        unsafe_allow_html=True,
                    )

                def _fc_move(d):
                    gs["idx"] = max(0, gs["idx"] + d)
                    gs["show"] = False

                def _fc_toggle():
                    gs["show"] = not gs["show"]

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.button("⬅️ Önceki", key="fc_prev", disabled=idx == 0, on_click=_fc_move, args=(-1,))
                with c2:
                    st.button("🙈 Cevabı Gizle" if gs["show"] else "👀 Cevabı Göster", key="fc_toggle", on_click=_fc_toggle)
                with c3:
                    st.button("Sonraki ➡️", key="fc_next", on_click=_fc_move, args=(1,))
            else:
                st.markdown(
                    '<div class="result"><div class="trophy">🎉</div><h2>Tüm kartları gözden geçirdin!</h2></div>',
                    unsafe_allow_html=True,
                )
                st.button("🔄 Başa Dön", key="again", on_click=lambda: gs.update(idx=0, show=False))

    # 6. Oynayarak öğren
    elif game == "oynayarak":
        prompt = (
            ctx() + "Gerçek hayattan esinlenen bir karar verme senaryosu ve çoktan seçmeli mini görev üret. "
            'Yalnızca geçerli JSON döndür: {"senaryo":"...","gorev_sorusu":"...",'
            '"secenekler":["A) ...","B) ...","C) ...","D) ..."],"ipucu":"..."}'
        )
        iq = load_data(gs, prompt, dict, ("senaryo", "gorev_sorusu", "secenekler"), "Macera hazırlanıyor...")
        if iq:
            st.markdown(
                f'<div class="qcard"><div class="qmeta"><span>📖 Görev Senaryosu</span></div>'
                f'<div style="font-size:1.1rem;line-height:1.6">{esc(str(iq["senaryo"]))}</div>'
                f'<hr style="border-color:rgba(94,234,212,.3);margin:16px 0">'
                f'<div class="qmeta"><span>🎯 Karar Noktası</span></div>'
                f'<div class="qtext">{esc(str(iq["gorev_sorusu"]))}</div></div>',
                unsafe_allow_html=True,
            )

            def _choose(opt):
                gs["choice"] = opt
                gs["eval"] = None

            def _hint():
                gs["show"] = not gs["show"]

            if gs["choice"] is None:
                with st.container(key="optbox"):
                    cols = st.columns(2)
                    for i, o in enumerate(iq["secenekler"]):
                        with cols[i % 2]:
                            st.button(md_safe(o), key=f"iq_{i}", on_click=_choose, args=(o,))
            else:
                st.markdown(f'<div class="pill">Seçimin: {esc(str(gs["choice"]))}</div>', unsafe_allow_html=True)
                if gs["eval"] is None:
                    with st.spinner("AdenMind değerlendiriyor..."):
                        gs["eval"] = ai_generate_content(
                            f"Ders: {subj}, Ünite: {unit}.\nGörev Sorusu: {iq['gorev_sorusu']}\n"
                            f"Öğrencinin Seçtiği Şık: {gs['choice']}\n"
                            "Bu seçimin doğru olup olmadığını değerlendir, nedenini sevimli bir dille kısaca açıkla."
                        ) or "Değerlendirme yapılamadı, tekrar dene."
                st.info(gs["eval"])
                st.button("↩️ Başka Şık Dene", key="iq_retry", on_click=_choose, args=(None,))
            st.button("💡 AdenMind'den İpucu", key="iq_hint", on_click=_hint)
            if gs["show"]:
                st.info(f"🦊 **İpucu:** {iq.get('ipucu', '')}")

    # 7. Etkinliklerle öğren
    elif game == "etkinlik":
        prompt = (
            ctx() + "Evde veya sınıfta yapılabilecek 3 adet yaratıcı öğrenme etkinliği, deney veya pratik uygulama öner. "
            "Her biri için gerekli malzemeleri ve adımları kısa maddelerle yaz. Markdown kullan."
        )
        text = load_data(gs, prompt, str, (), "Etkinlikler hazırlanıyor...")
        if text:
            with st.container(border=True):
                st.markdown(text)

    # 8. Kelime avı
    elif game == "kelime":
        prompt = (
            ctx() + "TAM 5 ADET anahtar kelime (tek sözcük, 4-10 harf, Türkçe veya dersin diline uygun) ve tanım ipucu üret. "
            'Yalnızca geçerli JSON liste döndür: [{"kelime":"TERİM","ipucu":"..."}]'
        )
        data = load_data(gs, prompt, list, ("kelime", "ipucu"), "Bulmaca hazırlanıyor...")
        if data:
            idx = gs["idx"]
            if idx < len(data):
                item = data[idx]
                word = tr_upper(re.sub(r"\s+", "", str(item["kelime"])))
                if gs["pool_for"] != idx:
                    pool = list(word)
                    extras = [c for c in "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ" if c not in pool]
                    pool += random.sample(extras, min(3, len(extras)))
                    random.shuffle(pool)
                    gs.update(pool=pool, pool_for=idx, guess=[], used=[])

                def _add(i, ch, n):
                    if len(gs["guess"]) < n:
                        gs["guess"].append(ch)
                        gs["used"].append(i)
                        gs["msg"] = None

                def _undo():
                    if gs["guess"]:
                        gs["guess"].pop()
                        gs["used"].pop()

                def _clear():
                    gs["guess"], gs["used"] = [], []

                def _skip():
                    gs["idx"] += 1
                    gs["msg"] = None

                def _check():
                    if "".join(gs["guess"]) == word:
                        gs["score"] += max(1, 100 // len(data))
                        gs["idx"] += 1
                        gs["msg"] = ("ok", "🎉 Tebrikler, doğru kelime!")
                    else:
                        gs["msg"] = ("bad", "❌ Eksik veya yanlış harf! Son harfi silip düzeltebilirsin.")

                st.progress(idx / len(data))
                st.markdown(
                    f'<div class="qcard"><div class="qmeta"><span>Bulmaca {idx + 1} / {len(data)} · '
                    f'{len(word)} harf</span><span class="score-chip">⭐ {gs["score"]} puan</span></div>'
                    f'<div class="qtext">💡 {esc(str(item["ipucu"]))}</div></div>',
                    unsafe_allow_html=True,
                )
                tiles = "".join(
                    f'<div class="tile {"on" if i < len(gs["guess"]) else ""}">'
                    f'{esc(gs["guess"][i]) if i < len(gs["guess"]) else ""}</div>'
                    for i in range(len(word))
                )
                st.markdown(f'<div class="tiles">{tiles}</div>', unsafe_allow_html=True)
                if gs["msg"]:
                    (st.success if gs["msg"][0] == "ok" else st.error)(gs["msg"][1])

                with st.container(key="letters"):
                    for r in range(0, len(gs["pool"]), 8):
                        cols = st.columns(8)
                        for j, ch in enumerate(gs["pool"][r:r + 8]):
                            i = r + j
                            used = i in gs["used"]
                            with cols[j]:
                                st.button(
                                    "✔" if used else ch, key=f"ch_{idx}_{i}", disabled=used,
                                    on_click=_add, args=(i, ch, len(word)),
                                )
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.button("🔄 Sıfırla", key="k_clear", on_click=_clear)
                with c2:
                    st.button("↩️ Son Harfi Sil", key="k_undo", on_click=_undo)
                with c3:
                    st.button("⏭️ Pas Geç", key="pass_k", on_click=_skip)
                with c4:
                    st.button("✅ Kontrol Et", key="k_check", on_click=_check)
            else:
                st.markdown(
                    f'<div class="result"><div class="trophy">🏆</div><h2>Tüm bulmacaları tamamladın!</h2>'
                    f'<div class="big">{gs["score"]}<small> / 100</small></div></div>',
                    unsafe_allow_html=True,
                )
                st.button("🔄 Yeni Bulmaca", key="again", on_click=regen)

    # 9. Klasik yazılı simülatörü
    elif game == "acik":
        prompt = (
            ctx() + "TAM 5 ADET açık uçlu yazılı sorusu ve ideal cevaplarını üret. "
            'Yalnızca geçerli JSON liste döndür: [{"soru":"...","beklenen_cevap":"..."}]'
        )
        data = load_data(gs, prompt, list, ("soru", "beklenen_cevap"), "Yazılı soruları hazırlanıyor...")
        if data:
            with st.form("classic_form"):
                answers = []
                for i, cq in enumerate(data):
                    st.markdown(
                        f'<div class="qcard" style="padding:16px 22px"><div class="qmeta"><span>Soru {i + 1}</span></div>'
                        f'<div class="qtext" style="font-size:1.15rem">{esc(str(cq["soru"]))}</div></div>',
                        unsafe_allow_html=True,
                    )
                    answers.append(st.text_area(f"Cevabın ({i + 1})", key=f"ans_{gs['nonce']}_{i}"))
                submitted = st.form_submit_button("📨 Yazılı Kağıdını Puanlat")
            if submitted:
                gs["results"] = []
                with st.spinner("AdenMind kâğıdını okuyor..."):
                    for i, cq in enumerate(data):
                        if answers[i].strip():
                            res = ai_generate_content(
                                f"Soru: {cq['soru']}\nİdeal cevap: {cq['beklenen_cevap']}\nÖğrenci: {answers[i]}\n"
                                "0-20 arası puan ve kısa, cesaretlendirici bir açıklama ver."
                            )
                            gs["results"].append((i, res or "Değerlendirme yapılamadı."))
            for i, res in gs["results"] or []:
                st.info(f"**Soru {i + 1} Değerlendirmesi**\n\n{res}")
