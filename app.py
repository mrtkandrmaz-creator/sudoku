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

genai = None
try:
    import google.generativeai as genai  # isteğe bağlı; yoksa REST ile doğrudan çağrılır
except Exception:
    genai = None
has_gemini = bool(gemini_keys)  # SDK kurulu olmasa da anahtar varsa Gemini REST üzerinden kullanılır

try:
    from groq import Groq

    has_groq = bool(groq_keys)
except ImportError:
    pass


_GEM_DEAD = set()
_GEM_FOUND = {}
GEMINI_PREFERRED = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]


def _gemini_models(key):
    """Önce Gemini 3.6; olmazsa sırayla eski sürümler. Hepsi 404 verirse hesabın gerçek model listesi sorulur."""
    names = list(GEMINI_PREFERRED)
    names += [m for m in _GEM_FOUND.get(key[-6:], []) if m not in names]
    return names


def _gemini_discover(key):
    """ListModels ile bu anahtarın erişebildiği 'flash' modellerini bulur (yeni sürüm adları için)."""
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=200"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))
    found = [m["name"].split("/")[-1] for m in data.get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]
             and "image" not in m["name"] and "tts" not in m["name"]]
    found.sort(reverse=True)
    _GEM_FOUND[key[-6:]] = found
    return found


def _gemini_call(key, model, prompt, fast):
    """Gemini'yi SDK'ya bağımlı olmadan REST ile çağırır."""
    import urllib.request
    import urllib.error
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7 if fast else 0.95}}
    if fast:
        body["generationConfig"]["maxOutputTokens"] = 400
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=25 if fast else 60) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:120]
        except Exception:
            pass
        raise Exception(f"HTTP {e.code} {detail}")
    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


AI_ERRORS = []


def ai_generate_content(prompt_text, fast=False):
    """fast=True: kısa/sohbet cevapları için hızlı modeller ve düşük token sınırı (AdenMind).
    Sıra: tüm Groq anahtarları -> tüm Gemini anahtarları. Hatalar AI_ERRORS'ta tutulur."""
    del AI_ERRORS[:]
    if has_groq:
        models = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"] if fast else ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
        for gr_key in groq_keys:
            for model in models:
                try:
                    kw = {"max_tokens": 320, "temperature": 0.7} if fast else {"temperature": 0.95}
                    client = Groq(api_key=gr_key, timeout=20.0 if fast else 45.0, max_retries=0)
                    completion = client.chat.completions.create(
                        model=model, messages=[{"role": "user", "content": prompt_text}], **kw
                    )
                    if completion.choices[0].message.content:
                        return completion.choices[0].message.content
                except Exception as e:  # noqa: BLE001
                    AI_ERRORS.append(f"groq/{model}: {str(e)[:80]}")
                    continue
    else:
        AI_ERRORS.append("groq anahtarı/paketi yok")
    if has_gemini:
        for g_key in gemini_keys:
            for attempt in range(2):
                if attempt == 1:  # tüm bilinen adlar 404 verdiyse hesabın gerçek model listesini sor
                    try:
                        if not _gemini_discover(g_key):
                            break
                    except Exception as e:  # noqa: BLE001
                        AI_ERRORS.append(f"gemini liste: {str(e)[:60]}")
                        break
                if _gemini_pass(g_key, prompt_text, fast):
                    return _GEM_LAST[0]
    else:
        AI_ERRORS.append("gemini anahtarı yok")
    return None


_GEM_LAST = [None]


def _gemini_pass(g_key, prompt_text, fast):
    """Bir anahtar için modelleri sırayla dener; başarıda metni _GEM_LAST'e yazıp True döner."""
    if True:
        if True:
            for model_name in _gemini_models(g_key):
                if (g_key[-6:], model_name) in _GEM_DEAD:
                    continue
                try:
                    text = _gemini_call(g_key, model_name, prompt_text, fast)
                    if text:
                        _GEM_LAST[0] = text
                        return True
                    AI_ERRORS.append(f"gemini/{model_name}: boş yanıt")
                except Exception as e:  # noqa: BLE001
                    msg = str(e)
                    AI_ERRORS.append(f"gemini/{model_name}: {msg[:80]}")
                    if "404" in msg or "not found" in msg.lower() or "NOT_FOUND" in msg:
                        _GEM_DEAD.add((g_key[-6:], model_name))
                    elif "API_KEY_INVALID" in msg or "API key not valid" in msg or "403" in msg:
                        return False  # bu anahtar geçersiz: sıradaki anahtara geç
                    continue
    return False


def local_coach_reply(msg, subject=None, unit=None):
    """Yapay zekâya ulaşılamazsa bile AdenMind'in mutlaka bir cevap vermesi için yerel yanıt üretici."""
    t = msg.lower().strip()
    expr = re.sub(r"[x×]", "*", t.replace(",", ".").replace("÷", "/").replace(":", "/"))
    m = re.fullmatch(r"[^0-9(]*([0-9+\-*/(). ]{3,})[^0-9)]*", expr)
    if m:
        try:
            e = m.group(1).strip()
            if re.fullmatch(r"[0-9+\-*/(). ]+", e) and any(c in e for c in "+-*/") and "**" not in e and len(e) <= 30:
                v = eval(e, {"__builtins__": {}}, {})  # noqa: S307 (yalnızca sayı ve işlem karakterleri)
                return f"İşlem sonucu: **{round(v, 4):g}** 🎯 Adımları kâğıtta kendin de yazıp kontrol et!"
        except Exception:
            pass
    if re.search(r"\b(merhaba|selam|hey|günaydın|iyi akşamlar)\b", t):
        return "Merhaba! Ben AdenMind 😊 Bugün hangi konuda çalışıyoruz? Bir soru sorabilir ya da oyun seçebilirsin!"
    if re.search(r"nasıl çalış|ders çalış|verim|odaklan|dikkat|motivasyon|sınav", t):
        return ("Şu planı dene: 1) 25 dk odaklı çalış, 5 dk mola ver. 2) Konuyu kendi cümlenle anlat. "
                "3) Öğrendiklerini oyunlarla pekiştir. Düzenli tekrar en güçlü yöntemdir! 💪")
    if re.search(r"teşekkür|sağ ol|eyvallah", t):
        return "Rica ederim! Birlikte öğrenmek çok güzel 🌟 Devam edelim mi?"
    where = f"{subject} dersi, {unit}" if subject and unit else (subject or "seçtiğin konu")
    return (f"Şu an yapay zekâ servisine ulaşamıyorum ama yanındayım! 📴 {where} için şunu öneririm: önce konunun anahtar "
            "kelimelerini yaz, sonra bir örnek üzerinde dene, ardından ilgili oyunda kendini test et. "
            "Sorunu biraz daha ayrıntılı yazarsan (örn. \"kesir nedir\") bağlantı gelince tam cevap verebilirim.")


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
    ("balon", "🎈", "Balon Patlatmaca", "linear-gradient(135deg, #f43f5e, #fb923c)", "Tam ekran · 30 sn süre"),
    ("blitz", "⚡", "Şimşek Turu", "linear-gradient(135deg, #eab308, #f97316)", "10 hızlı doğru/yanlış"),
    ("duo", "🦉", "Seviye Atla Dersi", "linear-gradient(135deg, #22c55e, #14b8a6)", "Duolingo tarzı · 3 kalp"),
    ("sinav10", "🧠", "Kazanım Yarışması", "linear-gradient(135deg, #06b6d4, #2563eb)", "5 çoktan seçmeli soru"),
    ("dogruyanlis", "✅", "Doğru / Yanlış", "linear-gradient(135deg, #10b981, #14b8a6)", "Açıklamalı önermeler"),
    ("bosluk", "📝", "Boşluk Doldurma", "linear-gradient(135deg, #f59e0b, #f97316)", "Cümleyi tamamla"),
    ("adam", "🪢", "Adam Asmaca", "linear-gradient(135deg, #8b5cf6, #6366f1)", "Harf seç, kelimeyi bul"),
    ("eslestir", "🔗", "Eşleştirme Atölyesi", "linear-gradient(135deg, #0ea5e9, #6366f1)", "Terim ve tanım eşle"),
    ("siralama", "🧩", "Doğru Sıralama", "linear-gradient(135deg, #ec4899, #f43f5e)", "Adımları sıraya diz"),
    ("cumle", "✍️", "Cümle Kur", "linear-gradient(135deg, #f97316, #ef4444)", "Kelimelere dokun, kur"),
    ("hafiza", "🃏", "Hafıza Kartları", "linear-gradient(135deg, #0ea5e9, #14b8a6)", "Çiftleri bul"),
    ("tekrar", "🔁", "Akıllı Tekrar", "linear-gradient(135deg, #a855f7, #ec4899)", "Bilmediklerin geri gelir"),
    ("kartlar", "🗂️", "Bilgi Kartları", "linear-gradient(135deg, #8b5cf6, #d946ef)", "Çevir ve öğren"),
    ("kelime", "🔤", "Kelime Avı", "linear-gradient(135deg, #84cc16, #22c55e)", "Harfleri sırala"),
    ("oynayarak", "🎯", "Oynayarak Öğren", "linear-gradient(135deg, #3b82f6, #6366f1)", "Senaryoda karar ver"),
    ("etkinlik", "📚", "Etkinliklerle Öğren", "linear-gradient(135deg, #22c55e, #84cc16)", "Evde yapılacak deneyler"),
    ("acik", "📄", "Klasik Yazılı", "linear-gradient(135deg, #6366f1, #a855f7)", "Yaz, AdenMind puanlasın"),
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
    "selected_arcade": None,
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
.st-key-letters button{width:100% !important;height:54px;min-height:54px;max-height:54px;justify-content:center;text-align:center;font-size:1.3rem;padding:0}
.st-key-letters,.st-key-letters > div[data-testid="stVerticalBlock"]{display:flex !important;flex-direction:row !important;
  flex-wrap:wrap !important;justify-content:center !important;gap:8px !important;max-width:640px;margin:8px auto}
.st-key-letters > div[data-testid="stElementContainer"],.st-key-letters .stElementContainer,.st-key-letters [data-testid="stElementContainer"]{
  width:54px !important;min-width:54px !important;flex:0 0 54px !important}
.st-key-letters [data-testid="stButton"],.st-key-letters .stButton{width:100% !important}
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

/* ---- Yeni oyunlar ---- */
.hm-word{font-size:clamp(1.6rem,4vw,2.6rem);letter-spacing:.18em;font-weight:900;color:#fef08a;text-align:center;margin:22px 0}
.st-key-matchL button,.st-key-matchR button,.st-key-orderpool button,.st-key-wordchips button{
  background:rgba(255,255,255,.07) !important;color:#e6fffb !important;
  border:2px solid rgba(94,234,212,.45) !important;box-shadow:0 5px 0 rgba(0,0,0,.35) !important;
  height:72px;min-height:72px;max-height:72px;padding:6px 14px;overflow:hidden;border-radius:20px;font-size:.98rem;line-height:1.2}
.st-key-matchL button p,.st-key-matchR button p,.st-key-orderpool button p,.st-key-wordchips button p{
  display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}
.st-key-matchL button:hover,.st-key-matchR button:hover,.st-key-orderpool button:hover,.st-key-wordchips button:hover{
  background:linear-gradient(135deg,#14b8a6,#06b6d4) !important;color:#042f2e !important}
.st-key-matchL button:disabled,.st-key-matchR button:disabled{
  background:linear-gradient(135deg,#059669,#14b8a6) !important;color:#fff !important;opacity:.85}
.st-key-mem button{height:104px;min-height:104px;max-height:104px;overflow:hidden;border-radius:22px;font-size:1.02rem;
  background:linear-gradient(135deg,#0ea5e9,#14b8a6) !important;color:#fff !important;box-shadow:0 6px 0 rgba(0,0,0,.3) !important}
.ochip{display:flex;gap:10px;align-items:center;padding:10px 14px;border-radius:16px;margin:6px 0;font-weight:700;
  background:linear-gradient(135deg,#14b8a6,#06b6d4);color:#042f2e;box-shadow:0 4px 0 #0f766e}
.ochip b{background:#042f2e;color:#5eead4;border-radius:99px;min-width:28px;height:28px;display:inline-flex;
  align-items:center;justify-content:center}
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
        f".st-key-{key}{{margin-bottom:10px;width:100% !important;max-width:100% !important}}"
        f".st-key-{key} > div,.st-key-{key} [data-testid='stButton'],.st-key-{key} .stButton{{width:100% !important;"
        f"max-width:100% !important;display:block !important}}"
        f".st-key-{key} button{{width:100% !important;min-width:100% !important;max-width:100% !important;"
        f"box-sizing:border-box !important;display:flex !important;align-items:center;justify-content:center;"
        f"position:relative;overflow:hidden;height:{CARD_H}px !important;"
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
        f".st-key-{key} button p:nth-child(3){{font-size:.78rem !important;font-weight:600 !important;opacity:.92;"
        f"-webkit-line-clamp:2 !important}}"
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
                label = f"{it[1]}\n\n**{md_safe(it[2])}**" + (f"\n\n{md_safe(it[4])}" if len(it) > 4 and it[4] else "")
                st.button(label, key=f"{prefix}_{i}", on_click=on_pick, args=(it[0],), use_container_width=True)


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
            "Sen 5. sınıf öğrencilerine yardım eden sevimli koç AdenMind'sin. Türkçe, en fazla 3 kısa cümleyle cevap ver. "
            f"Ders: {st.session_state.get('selected_subject') or 'Genel'}; ünite: {st.session_state.get('selected_unit') or 'Genel'}. "
            f"Soru: {user_msg.strip()}"
        )
        with loading("AdenMind yazıyor...", 3, compact=True, kind="chat"):
            reply = ai_generate_content(prompt, fast=True)
        if not reply:
            reply = local_coach_reply(user_msg.strip(), st.session_state.get("selected_subject"), st.session_state.get("selected_unit"))
            st.session_state["last_ai_error"] = "; ".join(AI_ERRORS[-3:])
        else:
            st.session_state["last_ai_error"] = ""
        msgs.append({"role": "assistant", "content": reply})
    with box:
        st.markdown("".join(chat_bubble(m["role"], m["content"]) for m in msgs), unsafe_allow_html=True)
    if st.session_state.get("last_ai_error"):
        st.caption("⚠️ Yapay zekâ servisi yanıt vermedi (yerel cevap kullanıldı): " + esc(st.session_state["last_ai_error"])[:160])


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



# =============================================================================
# YÜKLEME EKRANI: ekranın ortasında geri sayımlı "hazırlanıyor" kartı
# =============================================================================
import time
from contextlib import contextmanager

LOADER_CSS = """
.st-key-loader_box{position:fixed !important;inset:0;z-index:99999;display:flex !important;align-items:center;
  justify-content:center;background:rgba(2,20,25,.80);backdrop-filter:blur(6px);margin:0 !important}
.st-key-loader_small{position:fixed !important;right:22px;bottom:22px;z-index:99999;width:auto !important}
.st-key-loader_box > div,.st-key-loader_small > div{width:auto !important}
@property --ldn{syntax:'<integer>';inherits:false;initial-value:8}
.ld-card{width:min(88vw,360px);box-sizing:border-box;border-radius:28px;border:2px solid rgba(94,234,212,.5);padding:26px 18px;
  background:linear-gradient(160deg,#0b4a55,#052a31);box-shadow:0 20px 60px rgba(0,0,0,.55);text-align:center;color:#e6fffb;
  font-family:'Segoe UI',system-ui,sans-serif}
.ld-ring{position:relative;width:130px;height:130px;margin:0 auto 14px;border-radius:50%;
  background:conic-gradient(#2dd4bf calc(var(--p,0) * 1%),rgba(255,255,255,.12) 0)}
.ld-ring::before{content:'';position:absolute;inset:10px;border-radius:50%;background:#073a43}
.ld-spin{position:absolute;inset:-6px;border-radius:50%;border:5px solid transparent;border-top-color:#5eead4;
  border-right-color:rgba(94,234,212,.35);animation:ldspin 1s linear infinite}
.ld-num{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:42px;font-weight:900;
  animation:ldcount var(--est) linear forwards,ldhide .3s linear var(--est) forwards;counter-reset:ldn var(--ldn)}
.ld-num::after{content:counter(ldn)}
.ld-done{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:42px;opacity:0;
  animation:ldshow 1s ease var(--est) forwards,ldpulse 1.2s ease-in-out var(--est) infinite}
.ld-ring{animation:ldfill var(--est) linear forwards}
.ld-t{font-weight:800;font-size:18px}.ld-tip{font-size:13px;color:#8fd9cf;margin-top:6px}
.ld-dots span{animation:ldb 1.2s infinite;display:inline-block}.ld-dots span:nth-child(2){animation-delay:.2s}.ld-dots span:nth-child(3){animation-delay:.4s}
.ld-small{display:flex;align-items:center;gap:12px;padding:10px 16px;border-radius:20px;width:auto}
.ld-small .ld-ring{width:42px;height:42px;margin:0}.ld-small .ld-ring::before{inset:5px}.ld-small .ld-num,.ld-small .ld-done{font-size:15px}
.ld-small .ld-spin{border-width:3px;inset:-4px}.ld-small .ld-t{font-size:14px}
@keyframes ldspin{to{transform:rotate(360deg)}}
@keyframes ldcount{from{--ldn:var(--est-n)}to{--ldn:0}}
@keyframes ldfill{from{--p:0}to{--p:100}}
@keyframes ldshow{to{opacity:1}}
@keyframes ldhide{to{opacity:0}}
@keyframes ldpulse{50%{transform:scale(1.18)}}
@keyframes ldb{0%,80%,100%{opacity:.2;transform:translateY(0)}40%{opacity:1;transform:translateY(-4px)}}
@property --p{syntax:'<number>';inherits:true;initial-value:0}
"""


def _est_seconds(kind, default):
    h = st.session_state.get("load_times", {}).get(kind)
    if h:
        return max(2, min(40, round(sum(h[-4:]) / len(h[-4:]) + 1)))
    return default


@contextmanager
def loading(msg, default_est=8, compact=False, kind="gen"):
    """Ekranın ortasında geri sayımlı dönen daire gösterir; işlem bitince kaybolur. Süre tahmini ölçümlerden öğrenilir."""
    est = _est_seconds(kind, default_est)
    ph = st.empty()
    text = esc(str(msg).rstrip(".… "))
    cls = "ld-card ld-small" if compact else "ld-card"
    tip = "" if compact else '<div class="ld-tip">Sorular yapay zekâ ile sana özel hazırlanıyor ✨</div>'
    card = (
        f'<div class="{cls}" style="--est:{est}s;--est-n:{est}"><div class="ld-ring" style="--ldn:{est}">'
        '<div class="ld-spin"></div><div class="ld-num"></div><div class="ld-done">✨</div></div>'
        f'<div><div class="ld-t">{text}<span class="ld-dots"><span>.</span><span>.</span><span>.</span></span></div>{tip}</div></div>'
    )
    with ph.container(key="loader_small" if compact else "loader_box"):
        st.markdown(f"<style>{LOADER_CSS}</style>{card}", unsafe_allow_html=True)
    t0 = time.time()
    try:
        yield
    finally:
        ph.empty()
        st.session_state.setdefault("load_times", {}).setdefault(kind, []).append(time.time() - t0)


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
    if it.get("ciftler"):
        return "; ".join(str(p["sol"] if isinstance(p, dict) else p[0]) for p in it["ciftler"])
    if it.get("adimlar"):
        return f"{it.get('gorev', '')} {it['adimlar'][0]}"
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


# --- Soru bankası: yapay zekânın ürettikleri (yapay zekâ hiç yanıt vermezse yedek olarak kullanılır) ---
_BANK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soru_bankasi.json")


@st.cache_resource
def _bank_store():
    try:
        with open(_BANK_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def bank_get(key):
    return list(_bank_store().get(key, []))


def bank_add(key, items):
    b = _bank_store()
    lst = b.setdefault(key, [])
    have = {json.dumps(i, sort_keys=True, ensure_ascii=False) for i in lst}
    for it in items:
        j = json.dumps(it, sort_keys=True, ensure_ascii=False)
        if j not in have:
            lst.append(it)
            have.add(j)
    del lst[:-80]
    try:
        tmp = _BANK_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(b, f, ensure_ascii=False)
        os.replace(tmp, _BANK_PATH)
    except Exception:
        pass


# =============================================================================
# YEREL SORU ÜRETİCİLER (internet/anahtar gerektirmez; her çağrıda rastgele yeni sorular)
# =============================================================================
LANG_SUBJECTS = ("İngilizce", "Almanca")
EN_VOCAB = {
    "cat": "kedi", "dog": "köpek", "apple": "elma", "book": "kitap", "school": "okul", "teacher": "öğretmen",
    "friend": "arkadaş", "family": "aile", "mother": "anne", "father": "baba", "sister": "kız kardeş",
    "brother": "erkek kardeş", "house": "ev", "garden": "bahçe", "water": "su", "bread": "ekmek", "milk": "süt",
    "green": "yeşil", "yellow": "sarı", "blue": "mavi", "red": "kırmızı", "black": "siyah", "white": "beyaz",
    "pencil": "kalem", "desk": "sıra", "bag": "çanta", "door": "kapı", "window": "pencere", "table": "masa",
    "chair": "sandalye", "morning": "sabah", "night": "gece", "monday": "pazartesi", "sunday": "pazar",
    "happy": "mutlu", "big": "büyük", "small": "küçük", "swim": "yüzmek", "read": "okumak", "play": "oynamak",
    "football": "futbol", "music": "müzik", "movie": "film", "doctor": "doktor", "hospital": "hastane",
    "birthday": "doğum günü", "cake": "pasta", "gift": "hediye", "sun": "güneş", "moon": "ay", "star": "yıldız",
    "tree": "ağaç", "flower": "çiçek", "bird": "kuş", "fish": "balık", "horse": "at", "rabbit": "tavşan",
    "street": "sokak", "bridge": "köprü", "park": "park", "market": "market", "winter": "kış", "summer": "yaz",
}
DE_VOCAB = {
    "Hund": "köpek", "Katze": "kedi", "Buch": "kitap", "Schule": "okul", "Lehrer": "öğretmen", "Freund": "arkadaş",
    "Familie": "aile", "Mutter": "anne", "Vater": "baba", "Schwester": "kız kardeş", "Bruder": "erkek kardeş",
    "Haus": "ev", "Wasser": "su", "Brot": "ekmek", "Milch": "süt", "gelb": "sarı", "blau": "mavi", "rot": "kırmızı",
    "schwarz": "siyah", "Stift": "kalem", "Tisch": "masa", "Stuhl": "sandalye", "Tasche": "çanta",
    "Fenster": "pencere", "Apfel": "elma", "eins": "bir", "zwei": "iki", "drei": "üç", "vier": "dört",
    "sechs": "altı", "sieben": "yedi", "acht": "sekiz", "neun": "dokuz", "zehn": "on", "Montag": "pazartesi",
    "Sonntag": "pazar", "Sonne": "güneş", "Mond": "ay", "Baum": "ağaç", "Blume": "çiçek", "Vogel": "kuş",
    "Fisch": "balık", "Pferd": "at", "Auto": "araba", "Garten": "bahçe",
}
EN_SENT = [
    ("I like apples", "Elmaları severim"), ("She is my sister", "O benim kız kardeşim"),
    ("The cat is on the table", "Kedi masanın üstünde"), ("We play football in the park", "Parkta futbol oynarız"),
    ("My father is a doctor", "Babam bir doktor"), ("Tom reads a book", "Tom bir kitap okur"),
    ("I get up at seven", "Yedide kalkarım"), ("They are in the garden", "Onlar bahçede"),
    ("He has a red bag", "Onun kırmızı bir çantası var"), ("Our school is big", "Okulumuz büyük"),
    ("I can swim very well", "Çok iyi yüzebilirim"), ("What is your name", "Adın ne"),
]
DE_SENT = [
    ("Ich heiße Anna", "Benim adım Anna"), ("Das ist mein Bruder", "Bu benim erkek kardeşim"),
    ("Ich habe einen Hund", "Bir köpeğim var"), ("Wir gehen in die Schule", "Okula gidiyoruz"),
    ("Mein Vater ist Lehrer", "Babam öğretmen"), ("Die Katze ist klein", "Kedi küçük"),
    ("Das Buch ist rot", "Kitap kırmızı"), ("Wie alt bist du", "Kaç yaşındasın"),
    ("Ich spiele Fußball", "Futbol oynarım"), ("Die Tür ist offen", "Kapı açık"),
    ("Wir sind Freunde", "Biz arkadaşız"), ("Ich mag Äpfel", "Elmaları severim"),
]
MATH_DEF = {
    "Üçgen": "3 kenarlı çokgen", "Kare": "4 kenarı eşit dik dörtgen", "Dik açı": "90 derecelik açı",
    "Dar açı": "90°'den küçük açı", "Geniş açı": "90°'den büyük açı", "Payda": "Kesirde alttaki sayı",
    "Pay": "Kesirde üstteki sayı", "Çevre": "Kenar uzunlukları toplamı", "Işın": "Başlangıcı olan sonsuz çizgi",
    "Doğru": "İki yönde sonsuz uzanır", "Veri": "Toplanan bilgiler", "Ondalık": "Virgüllü gösterilen sayı",
    "Basamak": "Rakamın sayıdaki yeri", "Dikdörtgen": "Karşılıklı kenarları eşit", "Alan": "Yüzeyin kapladığı büyüklük",
}
MATH_WORDS = {
    "KESİR": "Bütünün eş parçalarını gösteren sayı", "PAYDA": "Kesirde alttaki sayı", "ÜÇGEN": "Üç kenarlı çokgen",
    "ÇEVRE": "Kenar uzunlukları toplamı", "TOPLAMA": "Sayıları birleştirme işlemi", "ÇARPMA": "Tekrarlı toplama işlemi",
    "BÖLME": "Eşit paylaştırma işlemi", "BASAMAK": "Rakamın sayıdaki yeri", "AÇI": "İki ışının birleştiği yer",
    "IŞIN": "Başlangıç noktası olan sonsuz çizgi", "DOĞRU": "İki yönde sonsuz uzanan çizgi",
    "NOKTA": "Boyutu olmayan konum", "ONDALIK": "Virgüllü gösterilen sayı", "KARE": "Dört kenarı eşit dikdörtgen",
    "ALAN": "Bir yüzeyin kapladığı büyüklük", "VERİ": "Toplanan bilgiler", "TABLO": "Verileri satır ve sütunda gösterir",
}
MATH_CONCEPTS = [
    ("İki noktadan kaç farklı doğru geçer?", "Bir tane", ["İki tane", "Üç tane", "Sonsuz tane"], "İki nokta tek bir doğruyu belirler."),
    ("Başlangıç noktası olan ve bir yönde sonsuza uzanan çizgiye ne denir?", "Işın", ["Doğru", "Doğru parçası", "Açı"], "Işının bir başlangıç noktası vardır."),
    ("İki ucu belli olan düz çizgiye ne denir?", "Doğru parçası", ["Işın", "Doğru", "Açı"], "Doğru parçasının uzunluğu ölçülebilir."),
    ("Bir doğruya dik olan doğrular arasındaki açı kaç derecedir?", "90", ["45", "180", "60"], "Dik doğrular 90° açı yapar."),
    ("Ortak başlangıç noktası olan iki ışının oluşturduğu şekle ne denir?", "Açı", ["Doğru", "Üçgen", "Çokgen"], "Açının köşesi ortak başlangıç noktasıdır."),
    ("Bir doğru üzerinde kaç tane nokta vardır?", "Sonsuz tane", ["Bir tane", "İki tane", "Yüz tane"], "Bir doğru sonsuz noktadan oluşur."),
]


def _mk(q, right, wrongs, expl=""):
    right = str(right)
    opts = [right]
    for w in wrongs:
        w = str(w)
        if w not in opts:
            opts.append(w)
    if len(opts) < 3:
        return None
    opts = opts[:4]
    random.shuffle(opts)
    return {"soru": q, "secenekler": [f"{'ABCD'[i]}) {o}" for i, o in enumerate(opts)],
            "dogru_cevap": "ABCD"[opts.index(right)], "aciklama": expl, "gorsel_tipi": "yok", "gorsel_parametre": ""}


def _near(r, k=5):
    c = [r + d for d in (-10, -2, -1, 1, 2, 10, -100, 100, 5, -5) if r + d >= 0 and r + d != r]
    random.shuffle(c)
    return c[:k]


def _dec(x):
    return f"{x:.2f}".replace(".", ",")


def _g_add():
    a, b = random.randint(120, 9800), random.randint(120, 9800)
    return _mk(f"{a} + {b} işleminin sonucu kaçtır?", a + b, _near(a + b), f"{a} + {b} = {a + b}")


def _g_sub():
    b = random.randint(120, 4800)
    a = b + random.randint(100, 5000)
    return _mk(f"{a} − {b} işleminin sonucu kaçtır?", a - b, _near(a - b), f"{a} − {b} = {a - b}")


def _g_mul():
    a, b = random.randint(12, 99), random.randint(3, 9)
    return _mk(f"{a} × {b} işleminin sonucu kaçtır?", a * b, _near(a * b), f"{a} × {b} = {a * b}")


def _g_div():
    b, r = random.randint(2, 9), random.randint(11, 99)
    return _mk(f"{b * r} ÷ {b} işleminin sonucu kaçtır?", r, _near(r), f"{b} × {r} = {b * r} olduğu için bölüm {r} olur.")


def _g_place():
    while True:
        n = random.randint(1000, 99999)
        s = str(n)
        p = random.randrange(len(s))
        if s[p] != "0" and s.count(s[p]) == 1:
            break
    d = int(s[p])
    val = d * 10 ** (len(s) - 1 - p)
    wrongs = [d * 10 ** k for k in range(len(s)) if d * 10 ** k != val]
    return _mk(f"{n} sayısında {d} rakamının basamak değeri kaçtır?", val, wrongs,
               f"{d} rakamı {len(s) - p}. basamakta olduğu için basamak değeri {val} olur.")


def _g_round():
    n = random.randint(1000, 99999)
    u = random.choice([10, 100])
    r = (n + u // 2) // u * u
    name = "onluğa" if u == 10 else "yüzlüğe"
    return _mk(f"{n} sayısının en yakın {name} yuvarlanmış hâli kaçtır?", r,
               [n // u * u, (n // u + 1) * u, r + u, r - u], f"{n} sayısı en yakın {name} yuvarlanınca {r} olur.")


def _g_pattern():
    a, d = random.randint(2, 50), random.randint(3, 25)
    seq = [a + i * d for i in range(4)]
    return _mk(f"{', '.join(map(str, seq))}, … örüntüsünde sıradaki sayı kaçtır?", a + 4 * d, _near(a + 4 * d),
               f"Örüntü her adımda {d} artıyor.")


def _g_equiv():
    b = random.randint(2, 9)
    a = random.randint(1, b - 1)
    k = random.randint(2, 5)
    return _mk(f"{a}/{b} kesrine denk olan kesir hangisidir?", f"{a * k}/{b * k}",
               [f"{a * k}/{b * k + 1}", f"{a * k + 1}/{b * k}", f"{a + k}/{b + k}"],
               f"Pay ve payda {k} ile çarpılınca denk kesir elde edilir.")


def _g_frac_of():
    d = random.choice([2, 3, 4, 5, 6, 8, 10])
    a = random.randint(1, d - 1)
    m = random.randint(2, 12)
    return _mk(f"{d * m} sayısının {a}/{d} kesri kaçtır?", a * m, _near(a * m),
               f"{d * m} ÷ {d} = {m}, {m} × {a} = {a * m}")


def _g_frac_cmp():
    d = random.randint(5, 12)
    nums = random.sample(range(1, d), 4)
    big = random.random() < .5
    right = max(nums) if big else min(nums)
    return _mk(f"Aşağıdaki kesirlerden hangisi en {'büyüktür' if big else 'küçüktür'}?", f"{right}/{d}",
               [f"{n}/{d}" for n in nums if n != right], "Paydalar eşit olduğunda payı büyük olan kesir daha büyüktür.")


def _g_improper():
    d = random.randint(2, 9)
    w, r = random.randint(1, 6), None
    r = random.randint(1, d - 1)
    n = d * w + r
    return _mk(f"{n}/{d} kesrinin tam sayılı kesir olarak yazılışı hangisidir?", f"{w} {r}/{d}",
               [f"{w + 1} {r}/{d}", f"{w} {d - r}/{d}" if d - r != r else f"{w} {r}/{d + 1}", f"{r} {w}/{d}"],
               f"{n} ÷ {d} = {w} kalan {r}")


def _g_dec_cmp():
    vals = random.sample([round(random.uniform(0.1, 9.99), 2) for _ in range(8)], 4)
    right = max(vals)
    return _mk("Aşağıdaki ondalık gösterimlerden hangisi en büyüktür?", _dec(right), [_dec(v) for v in vals if v != right],
               "Önce tam kısımlar, eşitse ondalık kısımlar karşılaştırılır.")


def _g_dec_add():
    a, b = round(random.uniform(1, 40), 1), round(random.uniform(1, 40), 1)
    s = round(a + b, 1)
    return _mk(f"{_dec(a)[:-1]} + {_dec(b)[:-1]} işleminin sonucu kaçtır?", _dec(s)[:-1],
               [_dec(round(s + d, 1))[:-1] for d in (0.1, -0.1, 1, -1, 10) if s + d > 0], "Virgüller alt alta gelecek şekilde toplanır.")


def _g_dec_to_frac():
    if random.random() < .5:
        k = random.randint(1, 9)
        return _mk(f"0,{k} ondalık gösteriminin kesir karşılığı hangisidir?", f"{k}/10", [f"{k}/100", f"1/{k}", f"{k}/1"],
                   f"Onda birler basamağı olduğu için {k}/10 olur.")
    n = random.choice([x for x in range(11, 100) if x % 10])
    return _mk(f"0,{n:02d} ondalık gösteriminin kesir karşılığı hangisidir?", f"{n}/100", [f"{n}/10", f"{n}/1000", f"{n * 10}/100"],
               f"Yüzde birler basamağına kadar olduğu için {n}/100 olur.")


def _g_dec_place():
    a, b, c = random.randint(1, 9), random.randint(1, 9), random.randint(1, 9)
    while len({a, b, c}) < 3:
        a, b, c = random.randint(1, 9), random.randint(1, 9), random.randint(1, 9)
    names = ["Birler basamağı", "Onda birler basamağı", "Yüzde birler basamağı", "Binde birler basamağı"]
    d, name = random.choice([(a, names[0]), (b, names[1]), (c, names[2])])
    return _mk(f"{a},{b}{c} sayısında {d} rakamı hangi basamaktadır?", name, [n for n in names if n != name],
               f"{a},{b}{c} sayısında birler {a}, onda birler {b}, yüzde birler {c} rakamıdır.")


def _g_rect_perim():
    a, b = random.randint(3, 40), random.randint(3, 40)
    return _mk(f"Kenar uzunlukları {a} cm ve {b} cm olan dikdörtgenin çevresi kaç cm'dir?", 2 * (a + b), _near(2 * (a + b)),
               f"Çevre = 2 × ({a} + {b}) = {2 * (a + b)}")


def _g_rect_area():
    a, b = random.randint(3, 30), random.randint(3, 30)
    return _mk(f"Kenar uzunlukları {a} cm ve {b} cm olan dikdörtgenin alanı kaç cm²'dir?", a * b, _near(a * b),
               f"Alan = {a} × {b} = {a * b}")


def _g_square():
    a = random.randint(3, 40)
    if random.random() < .5:
        return _mk(f"Bir kenarı {a} cm olan karenin çevresi kaç cm'dir?", 4 * a, _near(4 * a), f"Çevre = 4 × {a} = {4 * a}")
    return _mk(f"Bir kenarı {a} cm olan karenin alanı kaç cm²'dir?", a * a, _near(a * a), f"Alan = {a} × {a} = {a * a}")


def _g_triangle():
    x, y = random.randint(25, 85), random.randint(25, 85)
    return _mk(f"İki açısı {x}° ve {y}° olan üçgenin üçüncü açısı kaç derecedir?", 180 - x - y, _near(180 - x - y),
               f"Üçgenin iç açıları toplamı 180°'dir: 180 − {x} − {y} = {180 - x - y}")


def _g_angle_type():
    ang = random.choice(list(range(5, 180, 5)) + [90, 180])
    names = ["Dar açı", "Dik açı", "Geniş açı", "Doğru açı"]
    right = names[0] if ang < 90 else names[1] if ang == 90 else names[2] if ang < 180 else names[3]
    return _mk(f"{ang}° ölçüsündeki açı hangi tür açıdır?", right, [n for n in names if n != right],
               "Dar: 90°'den küçük, dik: 90°, geniş: 90°-180° arası, doğru: 180°.")


def _g_complement():
    x = random.randint(5, 85)
    return _mk(f"Ölçüsü {x}° olan açıyı 90°'ye (dik açıya) tamamlayan açı kaç derecedir?", 90 - x, _near(90 - x),
               f"90 − {x} = {90 - x}")


def _g_supplement():
    x = random.randint(20, 160)
    return _mk(f"Ölçüsü {x}° olan açıyı 180°'ye (doğru açıya) tamamlayan açı kaç derecedir?", 180 - x, _near(180 - x),
               f"180 − {x} = {180 - x}")


def _g_mode():
    vals = random.sample(range(1, 20), 4)
    m = vals[0]
    lst = [m] * 3 + vals[1:] + [random.choice(vals[1:])]
    random.shuffle(lst)
    return _mk(f"{', '.join(map(str, lst))} veri grubunda en çok tekrar eden değer kaçtır?", m, vals[1:] + [m + 1],
               f"{m} sayısı 3 kez tekrar ediyor.")


def _g_range():
    vals = random.sample(range(2, 60), 6)
    r = max(vals) - min(vals)
    return _mk(f"{', '.join(map(str, vals))} veri grubunun açıklığı (en büyük − en küçük) kaçtır?", r, _near(r),
               f"{max(vals)} − {min(vals)} = {r}")


def _g_concept():
    q, right, wrongs, expl = random.choice(MATH_CONCEPTS)
    return _mk(q, right, wrongs, expl)


def _math_gens(unit):
    u = unit.lower()
    if "doğal sayılar" in u:
        return [_g_add, _g_sub, _g_mul, _g_div, _g_place, _g_round, _g_pattern]
    if "kesir" in u:
        return [_g_equiv, _g_frac_of, _g_frac_cmp, _g_improper]
    if "ondalık" in u:
        return [_g_dec_cmp, _g_dec_add, _g_dec_to_frac, _g_dec_place]
    if "nicelik" in u:
        return [_g_rect_perim, _g_rect_area, _g_square]
    if "üçgen" in u:
        return [_g_triangle, _g_angle_type, _g_complement, _g_supplement]
    if "doğru" in u:
        return [_g_concept, _g_angle_type, _g_complement, _g_supplement]
    if "veri" in u:
        return [_g_mode, _g_range]
    return [_g_add, _g_sub, _g_mul, _g_div, _g_equiv, _g_rect_area]


def _tf_item(statement, true, expl=""):
    return {"ifade": statement, "cevap": "D" if true else "Y", "aciklama": expl, "gorsel_tipi": "yok", "gorsel_parametre": ""}


def _tf_math():
    r = random.random()
    if r < .35:
        a, b = random.randint(100, 5000), random.randint(100, 5000)
        ok = random.random() < .5
        return _tf_item(f"{a} + {b} = {a + b if ok else a + b + random.choice([-10, 10, 100, -100])}", ok, f"{a} + {b} = {a + b}")
    if r < .6:
        a, b = random.randint(12, 99), random.randint(3, 9)
        ok = random.random() < .5
        return _tf_item(f"{a} × {b} = {a * b if ok else a * b + random.choice([-b, b, 10, -10])}", ok, f"{a} × {b} = {a * b}")
    if r < .8:
        b = random.randint(2, 9)
        a, k = random.randint(1, b - 1), random.randint(2, 5)
        ok = random.random() < .5
        return _tf_item(f"{a}/{b} kesri {a * k}/{b * k + (0 if ok else 1)} kesrine denktir.", ok,
                        f"Denk kesir için pay ve payda aynı sayıyla çarpılır: {a}/{b} = {a * k}/{b * k}.")
    x, y = random.randint(30, 80), random.randint(30, 80)
    z = 180 - x - y
    ok = random.random() < .5
    return _tf_item(f"İç açıları {x}°, {y}° ve {z if ok else z + random.choice([-10, 10, 20])}° olan şekil bir üçgen olabilir.", ok,
                    "Üçgenin iç açıları toplamı 180°'dir.")


def _lang_vocab():
    return EN_VOCAB if st.session_state["selected_subject"] == "İngilizce" else DE_VOCAB


def _lang_mcq():
    v = _lang_vocab()
    items = list(v.items())
    w, tr = random.choice(items)
    lang = st.session_state["selected_subject"]
    if random.random() < .5:
        wrongs = random.sample([t for _, t in items if t != tr], 3)
        return _mk(f"'{w}' kelimesinin Türkçe karşılığı nedir?", tr, wrongs, f"{w} = {tr}")
    wrongs = random.sample([x for x, _ in items if x != w], 3)
    return _mk(f"'{tr}' sözcüğü {lang} nasıl söylenir?", w, wrongs, f"{tr} = {w}")


def _lang_tf():
    v = _lang_vocab()
    items = list(v.items())
    w, tr = random.choice(items)
    ok = random.random() < .5
    shown = tr if ok else random.choice([t for _, t in items if t != tr])
    return _tf_item(f"'{w}' kelimesi Türkçede '{shown}' anlamına gelir.", ok, f"{w} = {tr}")


def _lang_words():
    v = {k: t for k, t in _lang_vocab().items() if k.isascii() and 4 <= len(k) <= 9}
    w = random.choice(list(v))
    return {"kelime": w, "ipucu": f"Türkçesi: {v[w]}"}


def _pairs_from(d, k, maxlen):
    items = [(a, b) for a, b in d.items() if len(a) <= maxlen and len(b) <= maxlen]
    return random.sample(items, min(k, len(items)))


def local_source(kind, k):
    """Yerel üretici: `kind` türünde en çok k öğe (üretilemiyorsa boş liste)."""
    subj = st.session_state["selected_subject"]
    unit = st.session_state["selected_unit"] or ""
    out = []
    try:
        if subj == "Matematik":
            if kind == "mcq":
                gens = _math_gens(unit)
                out = [random.choice(gens)() for _ in range(k)]
            elif kind == "tf":
                out = [_tf_math() for _ in range(k)]
            elif kind == "words":
                out = [{"kelime": w, "ipucu": h} for w, h in random.sample(list(MATH_WORDS.items()), min(k, len(MATH_WORDS)))]
        elif subj in LANG_SUBJECTS:
            if kind == "mcq":
                out = [_lang_mcq() for _ in range(k)]
            elif kind == "tf":
                out = [_lang_tf() for _ in range(k)]
            elif kind == "words":
                out = [_lang_words() for _ in range(k)]
            elif kind == "cumle":
                sent = EN_SENT if subj == "İngilizce" else DE_SENT
                out = [{"cumle": a, "ceviri": b} for a, b in random.sample(sent, min(k, len(sent)))]
    except Exception:
        out = []
    return [o for o in out if o]


def local_dict(kind):
    """Eşleştirme / hafıza için yerel çift listesi."""
    subj = st.session_state["selected_subject"]
    maxlen = 30 if kind == "memo" else 90
    if subj == "Matematik":
        pairs = _pairs_from(MATH_DEF, 6, 34 if kind == "memo" else 90)
        title = "Terimleri tanımlarıyla eşleştir"
    elif subj in LANG_SUBJECTS:
        pairs = _pairs_from(_lang_vocab(), 6, maxlen)
        title = "Kelimeleri Türkçe karşılıklarıyla eşleştir"
    else:
        return None
    if kind not in ("pairs", "memo") or len(pairs) < 5:
        return None
    return {"baslik": title, "ciftler": [{"sol": a, "sag": b} for a, b in pairs]}


# =============================================================================
# İÇERİK ÜRETİMİ: çoğunlukla yapay zekâ + bir kısmı yerel üretici
# =============================================================================
def word_ok(it):
    w = re.sub(r"[\s\-]+", "", str(it.get("kelime", "")))
    if not re.fullmatch(r"[A-Za-zÇĞİÖŞÜçğıöşüÄäÖöÜüß]{3,10}", w) or not str(it.get("ipucu", "")).strip():
        return False
    if st.session_state["selected_subject"] in LANG_SUBJECTS and not w.isascii():
        return False
    if st.session_state["selected_subject"] not in LANG_SUBJECTS and re.search(r"[QWXqwxÄäß]", w):
        return False  # Türkçe klavyede bu harfler yok
    it["kelime"] = w
    return True


def sentence_ok(it):
    return 3 <= len(str(it.get("cumle", "")).split()) <= 10 and bool(str(it.get("ceviri", "")).strip())


def norm_pairs(d, lo=4, hi=6, maxlen=90):
    if not isinstance(d, dict):
        return None
    out, sl, sr = [], set(), set()
    for p in d.get("ciftler") or []:
        if isinstance(p, dict):
            left, right = str(p.get("sol", "")).strip(), str(p.get("sag", "")).strip()
        elif isinstance(p, (list, tuple)) and len(p) == 2:
            left, right = str(p[0]).strip(), str(p[1]).strip()
        else:
            continue
        kl, kr = _norm(left), _norm(right)
        if not left or not right or len(left) > maxlen or len(right) > maxlen or kl in sl or kr in sr or kl == kr:
            continue
        sl.add(kl)
        sr.add(kr)
        out.append((left, right))
    return {"baslik": str(d.get("baslik", "")).strip(), "ciftler": out[:hi]} if len(out) >= lo else None


def norm_memo(d):
    return norm_pairs(d, 5, 6, 34)


def norm_order(d):
    if not isinstance(d, dict):
        return None
    steps = d.get("adimlar") or d.get("adimlar_dogru_sirada") or []
    steps = [re.sub(r"^\s*(\d+|[a-eA-E])[\).:\-]\s*", "", str(s)).strip() for s in steps]
    steps = [s for s in steps if s]
    if len(steps) < 4 or len({_norm(s) for s in steps}) < len(steps):
        return None
    return {"gorev": str(d.get("gorev", "")).strip() or "Doğru sıraya diz", "adimlar": steps[:6]}


def fetch_list(prompt, required, n, scope, kind=None, item_ok=None):
    """n öğe üretir. Çoğunluk yapay zekâdan (önceki sorulanlar tekrarlanmaz), bir kısmı yerel üreticiden.
    (öğeler, kökler, yapay_zeka_kullanıldı_mı) döndürür; hiçbir şey üretilemezse None."""
    seen = hist_get(scope)
    items, stems = [], []

    def take_local(k):
        added = 0
        if not kind or k <= 0:
            return 0
        for it in local_source(kind, k * 3 + 2):
            s = item_stem(it)
            if not s or is_dup(s, seen + stems) or (item_ok and not item_ok(it)):
                continue
            items.append(shuffle_item(it))
            stems.append(s)
            added += 1
            if added >= k:
                break
        return added

    take_local(n // 3 if n >= 3 else 0)  # yerel pay: en çok 1/3
    local_items = list(items)
    n_ai = n - len(local_items)
    fresh, fresh_stems, last_valid = [], [], None
    for _ in range(3):  # tekrar edenler elenirse eksik kalanı yeniden iste
        need = n_ai - len(fresh)
        if need <= 0:
            break
        p = re.sub(r"TAM \d+ ADET", f"TAM {need + 1} ADET", prompt, flags=re.I)
        got = parse_json(ai_generate_content(p + diversity_block(seen + stems + fresh_stems, need + 1)))
        if not is_valid(got, list, required):
            continue
        last_valid = got
        for it in got:
            s = item_stem(it)
            if (s and is_dup(s, seen + stems + fresh_stems)) or (item_ok and not item_ok(it)):
                continue
            fresh.append(shuffle_item(it))
            fresh_stems.append(s)
    if n_ai <= 0 or len(fresh) >= min(3, n_ai):
        res = local_items + fresh[:n_ai]
        random.shuffle(res)
        if fresh:
            bank_add(f"{scope}|{'-'.join(required)}", fresh[:n_ai])
        return res, stems + fresh_stems[:n_ai], True
    # yapay zekâ yetersiz: önce yerel üreticiyle tamamla
    items.extend(fresh)
    stems.extend(fresh_stems)
    take_local(n - len(items))
    if len(items) >= min(3, n):
        random.shuffle(items)
        return items[:n], stems[:n], bool(fresh)
    if last_valid:  # yapay zekâ hep aynı şeyleri verdiyse oyunu yine de aç
        res = [shuffle_item(i) for i in last_valid if not item_ok or item_ok(i)][:n]
        if res:
            return res, [item_stem(i) for i in res], True
    banked = [b for b in bank_get(f"{scope}|{'-'.join(required)}") if not item_ok or item_ok(b)]
    if banked:
        res = random.sample(banked, min(n, len(banked)))
        return res, [item_stem(i) for i in res], False
    return None


def load_data(gs, prompt, expect, required=(), msg="Hazırlanıyor...", kind=None, post=None, item_ok=None):
    """Veri yoksa otomatik üretir (tek tıkla oyun açılır). Önceki oyunlarda sorulanlar tekrar edilmez."""
    if gs["data"] is not None:
        return gs["data"]
    if not gs["failed"]:
        scope = f"{st.session_state['selected_subject']}|{st.session_state['selected_unit']}"
        seen = hist_get(scope)
        m = re.search(r"TAM (\d+) ADET", prompt, re.I)
        n = int(m.group(1)) if (m and expect is list) else 0
        data, stems, used_ai = None, [], True
        with loading(msg, 8, kind="gen"):
            if expect is list and n:
                res = fetch_list(prompt, required, n, scope, kind, item_ok)
                if res:
                    data, stems, used_ai = res
            else:
                for attempt in range(2):
                    if expect is dict and kind and attempt == 0 and random.random() < 0.3:  # bazen yerel üretici
                        cand = local_dict(kind)
                        cand = post(cand) if (cand and post) else cand
                        if cand and not is_dup(item_stem(cand), seen):
                            data, stems, used_ai = cand, [item_stem(cand)], False
                            break
                    extra = ""
                    if seen:
                        extra = ("\nDAHA ÖNCE İŞLENENLER (bunlardan FARKLI bir konu/senaryo seç):\n"
                                 + "\n".join(f"- {s[:110]}" for s in seen[-20:])
                                 + "\nİlham için: " + ", ".join(random.sample(_SEEDS, 3)) + ".")
                    raw = ai_generate_content(prompt + extra)
                    got = raw.strip() if (expect is str and raw) else parse_json(raw)
                    if expect is dict and post and isinstance(got, dict):
                        got = post(got)
                    if got is None or not is_valid(got, expect, required):
                        continue
                    s = item_stem(got) if expect is dict else str(got)[:100]
                    data, stems, used_ai = got, [s], True
                    if not (s and is_dup(s, seen)):
                        break
                if data is None and expect is dict and kind:  # yapay zekâ yok: yerel üretici
                    cand = local_dict(kind)
                    cand = post(cand) if (cand and post) else cand
                    if cand:
                        data, stems, used_ai = cand, [item_stem(cand)], False
        if data is not None:
            hist_add(scope, stems)
            gs.update(data=data, idx=0, score=0, feedback=None, offline=not used_ai)
            st.rerun()
        gs["failed"] = True
    st.error("İçerik üretilemedi. API anahtarlarını kontrol edip tekrar deneyin.")
    st.button("🔄 Tekrar Dene", key="retry", on_click=_retry, args=(gs,))
    return None


YENI_NESIL = (
    "SORU ANLAYIŞI (MEB yeni nesil, Türkiye Yüzyılı Maarif Modeli, 10-20 yaş): sorular bağlam temelli olsun; "
    "kısa bir gerçek yaşam durumu, tablo, veri, grafik betimi ya da metin parçası içersin; ezber yerine yorum, "
    "çıkarım ve mantık yürütme istesin; değer/erdem/vatandaşlık ve günlük hayatla bağ kursun; "
    "sayısal veriler ve karşılaştırmalar kullan; sade ve anlaşılır Türkçe yaz.\n"
)


def ctx():
    return (
        f"Rastgelelik Kimliği: {random.randint(10000, 999999)}\n"
        f"5. Sınıf MEB müfredatı, Ders: {st.session_state['selected_subject']}, "
        f"Ünite: {st.session_state['selected_unit']}.\n"
        + YENI_NESIL
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


BLITZ_HTML = r"""<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
*{box-sizing:border-box}
html,body{margin:0;height:100%;overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif;color:#e6fffb}
body{background:radial-gradient(circle,rgba(94,234,212,.10) 2px,transparent 2.6px) 0 0/40px 40px,
 radial-gradient(900px 500px at 12% 0%,rgba(45,212,191,.28),transparent 60%),
 radial-gradient(700px 500px at 100% 100%,rgba(6,182,212,.24),transparent 60%),#071a24}
#app{position:relative;width:100%;height:100%;overflow:hidden}
.timer{position:absolute;top:0;left:0;height:7px;width:100%;z-index:8;background:linear-gradient(90deg,#2dd4bf,#22d3ee)}
.timer.low{background:linear-gradient(90deg,#f43f5e,#fb923c)}
.hud{position:absolute;top:14px;left:0;right:0;display:flex;justify-content:space-between;gap:10px;padding:0 16px;z-index:7}
.chip{background:rgba(7,26,36,.75);border:1.5px solid rgba(94,234,212,.5);border-radius:999px;padding:8px 18px;font-weight:800;
 backdrop-filter:blur(6px);font-size:clamp(13px,1.6vw,17px)}
.chip.s{background:#fef08a;color:#713f12;border-color:#fde047}
.banner{position:absolute;left:50%;bottom:20px;transform:translateX(-50%) translateY(40px);opacity:0;z-index:9;
 width:min(94%,760px);text-align:center;padding:16px 22px;border-radius:24px;font-weight:800;color:#fff;
 font-size:clamp(14px,1.9vw,19px);transition:all .3s;pointer-events:none;box-shadow:0 8px 0 rgba(0,0,0,.3)}
.banner.show{opacity:1;transform:translateX(-50%) translateY(0)}
.banner.ok{background:linear-gradient(135deg,#059669,#14b8a6)}
.banner.bad{background:linear-gradient(135deg,#e11d48,#fb7185)}
.banner small{display:block;margin-top:6px;font-weight:600;opacity:.95}
#end{position:absolute;inset:0;z-index:20;display:none;align-items:center;justify-content:center;flex-direction:column;
 gap:12px;background:rgba(7,26,36,.94);text-align:center;padding:20px;overflow:auto}
#end .t{font-size:clamp(56px,11vw,100px)}
#end .sc{font-size:clamp(34px,6vw,64px);font-weight:900;color:#5eead4}
#end .sv{font-weight:700;color:#99f6e4;min-height:22px}
#end button{border:0;border-radius:20px;padding:16px 34px;font-size:18px;font-weight:800;cursor:pointer;color:#042f2e;
 background:linear-gradient(135deg,#5eead4,#22d3ee);box-shadow:0 6px 0 #0f766e}
.review{max-width:760px;text-align:left;font-size:14px;line-height:1.45}
.review div{background:rgba(255,255,255,.07);border-left:4px solid #fb7185;border-radius:12px;padding:8px 12px;margin:6px 0}

#stage{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;padding:70px 18px 24px}
#card{width:min(94%,900px);min-height:190px;display:flex;align-items:center;justify-content:center;text-align:center;
 padding:26px 30px;border-radius:32px;font-weight:800;line-height:1.4;font-size:clamp(20px,3.2vw,36px);
 background:linear-gradient(160deg,rgba(255,255,255,.12),rgba(255,255,255,.04));border:3px solid rgba(94,234,212,.55);
 box-shadow:0 10px 0 rgba(0,0,0,.3),0 24px 44px rgba(0,0,0,.3);transition:background .2s,border-color .2s,transform .2s}
#card.ok{background:linear-gradient(135deg,#059669,#14b8a6);border-color:#6ee7b7;transform:scale(1.02)}
#card.bad{background:linear-gradient(135deg,#e11d48,#fb7185);border-color:#fecdd3}
#btns{display:flex;gap:18px;width:min(94%,900px)}
#btns button{flex:1;border:0;border-radius:26px;padding:clamp(18px,3.5vw,34px) 10px;font-size:clamp(18px,2.6vw,30px);
 font-weight:900;cursor:pointer;color:#fff;box-shadow:0 8px 0 rgba(0,0,0,.35);transition:transform .1s}
#btns button:active{transform:translateY(6px);box-shadow:0 2px 0 rgba(0,0,0,.35)}
#btns button:disabled{opacity:.5;cursor:default}
#bd{background:linear-gradient(135deg,#10b981,#14b8a6)} #by{background:linear-gradient(135deg,#f43f5e,#fb923c)}
#combo{font-weight:900;font-size:clamp(16px,2.2vw,24px);color:#fde047;min-height:30px}
#hint{opacity:.7;font-size:13px}
</style></head><body>
<div id="app">
  <div class="timer" id="bar"></div>
  <div class="hud"><div class="chip" id="qc">1 / 10</div><div class="chip" id="tm">⏱ 8</div><div class="chip s" id="sc">⭐ 0</div></div>
  <div id="stage">
    <div id="combo"></div>
    <div id="card"></div>
    <div id="btns"><button id="bd">✅ DOĞRU</button><button id="by">❌ YANLIŞ</button></div>
    <div id="hint">Klavye: D = Doğru · Y = Yanlış</div>
  </div>
  <div class="banner" id="bn"></div>
  <div id="end"><div class="t">⚡</div><div style="font-size:clamp(20px,3vw,30px);font-weight:800">Şimşek Turu Bitti!</div>
   <div class="sc" id="fsc"></div><div id="detail" style="font-weight:700"></div><div class="sv" id="sv"></div>
   <div class="review" id="rev"></div><button id="again">🔄 Tekrar Oyna</button></div>
</div>
<script>
const Q=__QUESTIONS__; const SOUND=true;

const $=id=>document.getElementById(id);
function shuffle(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
let _ac=null;
function _ctx(){
  try{
    const W=(window.parent&&(window.parent.AudioContext||window.parent.webkitAudioContext))?window.parent:window;
    if(!W.__am_ac){W.__am_ac=new (W.AudioContext||W.webkitAudioContext)();}
    _ac=W.__am_ac; if(_ac.state==='suspended')_ac.resume();
  }catch(e){_ac=null}
  return _ac;
}
function _tone(f,t0,d,type,vol){
  const a=_ctx(); if(!a)return;
  const o=a.createOscillator(), g=a.createGain();
  o.type=type||'sine'; o.frequency.value=f;
  g.gain.setValueAtTime(0.0001,a.currentTime+t0);
  g.gain.exponentialRampToValueAtTime(vol||0.18,a.currentTime+t0+0.02);
  g.gain.exponentialRampToValueAtTime(0.0001,a.currentTime+t0+d);
  o.connect(g); g.connect(a.destination); o.start(a.currentTime+t0); o.stop(a.currentTime+t0+d+0.05);
}
function sfx(k){
  if(!SOUND)return;
  try{
    if(k==='ok'){_tone(660,0,.12);_tone(880,.1,.18)}
    else if(k==='bad'){_tone(220,0,.22,'sawtooth',.12);_tone(160,.16,.28,'sawtooth',.12);try{navigator.vibrate&&navigator.vibrate(120)}catch(e){}}
    else if(k==='win'){[523,659,784,1047].forEach((f,i)=>_tone(f,i*.12,.22))}
    else if(k==='tick'){_tone(900,0,.05,'square',.06)}
  }catch(e){}
}
function report(score){
  try{
    const step=Math.max(0,Math.min(100,Math.round(score/10)*10));
    const b=window.parent.document.querySelector('.st-key-rep_'+step+' button');
    if(b){b.click();return true}
  }catch(e){}
  return false;
}

const TIME=8, total=Q.length;
let i=0,right=0,streak=0,best=0,locked=false,timer=null,wrong=[];
function score(){return Math.round(right*100/total)}
function show(){
  clearInterval(timer);
  if(i>=total){finish();return}
  locked=false;
  const q=Q[i];
  $('qc').textContent=(i+1)+' / '+total; $('sc').textContent='⭐ '+score();
  $('card').className=''; $('card').textContent=q.ifade;
  $('bd').disabled=$('by').disabled=false; $('bn').className='banner';
  $('combo').textContent=streak>=2?('🔥 '+streak+' seri!'):'';
  const start=Date.now();
  timer=setInterval(()=>{
    const left=Math.max(0,TIME-(Date.now()-start)/1000);
    $('tm').textContent='⏱ '+Math.ceil(left); $('bar').style.width=(left/TIME*100)+'%';
    $('bar').className='timer'+(left<3?' low':'');
    if(left<=0){pick('-')}
  },100);
}
function pick(a){
  if(locked)return; locked=true; clearInterval(timer);
  $('bd').disabled=$('by').disabled=true;
  const q=Q[i], ok=(a===q.cevap);
  if(ok){right++;streak++;best=Math.max(best,streak)}else{streak=0;wrong.push(q)}
  sfx(ok?'ok':'bad');
  $('card').className=ok?'ok':'bad';
  $('sc').textContent='⭐ '+score();
  if(!ok){
    const bn=$('bn');
    bn.textContent=(a==='-'?'⏰ Süre doldu! ':'❌ ')+'Doğru cevap: '+(q.cevap==='D'?'DOĞRU':'YANLIŞ');
    if(q.aciklama){const s=document.createElement('small');s.textContent=q.aciklama;bn.appendChild(s)}
    bn.className='banner show bad';
  }
  setTimeout(()=>{i++;show()},ok?650:2300);
}
function finish(){
  const sc=score();
  $('fsc').textContent=sc+' / 100';
  $('detail').textContent='Doğru: '+right+' / '+total+' · En uzun seri: '+best;
  const rev=$('rev'); rev.innerHTML='';
  wrong.slice(0,4).forEach(q=>{
    const d=document.createElement('div');
    d.textContent=q.ifade+' → '+(q.cevap==='D'?'DOĞRU':'YANLIŞ')+(q.aciklama?(' · '+q.aciklama):'');
    rev.appendChild(d);
  });
  $('end').style.display='flex'; sfx('win');
  $('sv').textContent=report(sc)?'✅ Sonucun karnene kaydedildi':'';
}
$('bd').onclick=()=>pick('D'); $('by').onclick=()=>pick('Y');
document.addEventListener('keydown',e=>{const k=e.key.toLowerCase(); if(k==='d')pick('D'); else if(k==='y')pick('Y')});
$('again').onclick=()=>{i=0;right=0;streak=0;best=0;wrong=[];$('end').style.display='none';show()};
show();
</script></body></html>"""


# =============================================================================
# YENİ ETKİLEŞİMLİ OYUNLAR
# =============================================================================
SS = st.session_state
TR_ALPHABET = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"
EN_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def show_result(score, sub="", title="Oyun Tamamlandı!", icon="🏆"):
    stars = "⭐" * max(1, round(score / 20)) if score > 0 else "💪"
    st.markdown(
        f'<div class="result"><div class="trophy">{icon}</div><h2>{esc(title)}</h2>'
        f'<div class="big">{score}<small> / 100</small></div><div style="font-size:2rem">{stars}</div>'
        f'<div>{esc(sub)}</div></div>',
        unsafe_allow_html=True,
    )


def _flash(ok, text):
    (st.success if ok else st.error)(text)


def mcq_prompt(n):
    return (ctx() + f"TAM {n} ADET yepyeni çoktan seçmeli (4 şıklı) soru üret.\n" + VISUAL_RULES + MCQ_FORMAT)


def tf_prompt(n, short=False):
    return (ctx() + f"TAM {n} ADET yepyeni Doğru veya Yanlış önermesi üret. Doğru ve yanlış önermeleri dengeli dağıt."
            + (" Her önerme en çok 18 kelime olsun.\n" if short else "\n") + VISUAL_RULES
            + 'Yalnızca geçerli JSON liste döndür: [{"ifade":"...","cevap":"D","aciklama":"...",'
              '"gorsel_tipi":"yok","gorsel_parametre":""}] (cevap yalnızca D veya Y olsun).')


def fill_prompt(n):
    return (ctx() + f"Cümle içinde boşluk (____) bırakılmış TAM {n} ADET soru üret. Her soruda 4 seçenek olsun.\n"
            + VISUAL_RULES
            + 'Yalnızca geçerli JSON liste döndür: [{"cumle":"... ____ ...","dogru_kelime":"...",'
              '"secenekler":["...","...","...","..."],"gorsel_tipi":"yok","gorsel_parametre":""}]')


def words_prompt(n):
    return (ctx() + f"TAM {n} ADET anahtar kelime (tek sözcük, yalnızca harf, 4-10 harf) ve tanım ipucu üret. "
            'Yalnızca geçerli JSON liste döndür: [{"kelime":"TERİM","ipucu":"..."}]')


# ------------------------------------------------------------------ ADAM ASMACA
def hangman_svg(wrong):
    c = "#5eead4"
    parts = [
        f'<circle cx="150" cy="62" r="18" fill="none" stroke="{c}" stroke-width="5"/>',
        f'<line x1="150" y1="80" x2="150" y2="132" stroke="{c}" stroke-width="5" stroke-linecap="round"/>',
        f'<line x1="150" y1="94" x2="124" y2="118" stroke="{c}" stroke-width="5" stroke-linecap="round"/>',
        f'<line x1="150" y1="94" x2="176" y2="118" stroke="{c}" stroke-width="5" stroke-linecap="round"/>',
        f'<line x1="150" y1="132" x2="128" y2="168" stroke="{c}" stroke-width="5" stroke-linecap="round"/>',
        f'<line x1="150" y1="132" x2="172" y2="168" stroke="{c}" stroke-width="5" stroke-linecap="round"/>',
    ]
    face = ('<circle cx="144" cy="58" r="2.4" fill="#fb7185"/><circle cx="156" cy="58" r="2.4" fill="#fb7185"/>'
            if wrong >= 6 else "")
    gallows = ('<line x1="40" y1="190" x2="170" y2="190" stroke="#fef08a" stroke-width="6" stroke-linecap="round"/>'
               '<line x1="70" y1="190" x2="70" y2="20" stroke="#fef08a" stroke-width="6" stroke-linecap="round"/>'
               '<line x1="70" y1="22" x2="150" y2="22" stroke="#fef08a" stroke-width="6" stroke-linecap="round"/>'
               '<line x1="150" y1="22" x2="150" y2="44" stroke="#fef08a" stroke-width="4" stroke-linecap="round"/>')
    return ('<div style="display:flex;justify-content:center"><svg width="230" height="200" viewBox="0 0 230 200" '
            'style="background:rgba(255,255,255,.05);border-radius:22px;border:1px solid rgba(94,234,212,.35)">'
            + gallows + "".join(parts[:wrong]) + face + "</svg></div>")


def game_hangman(gs, game):
    data = load_data(gs, words_prompt(5), list, ("kelime", "ipucu"), "Kelimeler hazırlanıyor...",
                     kind="words", item_ok=word_ok)
    if not data:
        return
    lang = SS["selected_subject"] in LANG_SUBJECTS
    up = (lambda s: s.upper()) if lang else tr_upper
    alphabet = EN_ALPHABET if lang else TR_ALPHABET
    idx = gs["idx"]
    if idx >= len(data):
        score = round(100 * gs.get("wins", 0) / len(data))
        show_result(score, f"{gs.get('wins', 0)} / {len(data)} kelimeyi kurtardın", icon="🪢")
        st.button("🔄 Yeni Kelimelerle Oyna", key="again", on_click=regen)
        return
    word = up(data[idx]["kelime"])
    if gs.get("g_for") != idx:
        gs.update(g=[], g_for=idx)
    guessed = gs["g"]
    wrong = [c for c in guessed if c not in word]
    won = all(c in guessed for c in word)
    lost = len(wrong) >= 6

    def _guess(ch):
        if ch not in gs["g"]:
            gs["g"].append(ch)

    def _next(w):
        gs["wins"] = gs.get("wins", 0) + (1 if w else 0)
        gs["idx"] += 1

    shown = " ".join(c if (c in guessed or lost) else "＿" for c in word)
    st.progress(idx / len(data))
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>Kelime {idx + 1} / {len(data)} · {len(word)} harf</span>'
        f'<span class="score-chip">{"❤️" * (6 - len(wrong))}{"🖤" * len(wrong)}</span></div>'
        f'<div class="qtext">💡 {esc(str(data[idx]["ipucu"]))}</div></div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(hangman_svg(len(wrong)), unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="hm-word">{esc(shown)}</div>', unsafe_allow_html=True)
        if won:
            st.success("🎉 Harika, kelimeyi buldun!")
        elif lost:
            st.error(f"💀 Adam asıldı! Doğru kelime: {word}")
    if won or lost:
        st.button("➡️ Sonraki Kelime" if idx < len(data) - 1 else "🏆 Sonucu Gör", key=f"hm_next_{idx}",
                  on_click=_next, args=(won,))
        return
    with st.container(key="letters"):
        for ch in alphabet:
            st.button("•" if ch in guessed else ch, key=f"hm_{idx}_{ch}", disabled=ch in guessed,
                      on_click=_guess, args=(ch,))


# ------------------------------------------------------------------ DUOLINGO TARZI DERS
def _duo_answer(gs, value):
    q = gs["queue"][0]
    ok = _same(value, q["correct"])
    if ok:
        gs["streak"] += 1
    else:
        gs["streak"] = 0
        gs["hearts"] -= 1
        q["missed"] = True
    label = next((lab for lab, val in q["options"] if _same(val, q["correct"])), q["correct"])
    gs["fb"] = {"ok": ok, "label": label, "expl": q["expl"]}


def _duo_next(gs):
    fb = gs["fb"]
    gs["fb"] = None
    q = gs["queue"].pop(0)
    if fb["ok"]:
        gs["done"] += 1
        if not q.get("missed"):
            gs["first_ok"] += 1
    elif gs["hearts"] > 0:
        gs["queue"].append(q)  # Duolingo gibi: yanlış yapılan soru dersin sonunda yeniden gelir


def game_duo(gs, game):
    if gs["data"] is None:
        if gs["failed"]:
            st.error("Ders hazırlanamadı. API anahtarlarını kontrol edip tekrar deneyin.")
            st.button("🔄 Tekrar Dene", key="retry", on_click=_retry, args=(gs,))
            return
        scope = f"{SS['selected_subject']}|{SS['selected_unit']}"
        queue = []
        with loading("Dersin hazırlanıyor", 10, kind="gen"):
            for prompt, req, n, kind, builder in (
                (mcq_prompt(4), ("soru", "secenekler", "dogru_cevap"), 4, "mcq", build_mcq),
                (tf_prompt(2), ("ifade", "cevap"), 2, "tf", build_tf),
                (fill_prompt(2), ("cumle", "dogru_kelime", "secenekler"), 2, None, build_fill),
            ):
                res = fetch_list(prompt, req, n, scope, kind)
                if res:
                    hist_add(scope, res[1])
                    queue += [builder(i) for i in res[0]]
        if len(queue) < 3:
            gs["failed"] = True
            st.rerun()
        random.shuffle(queue)
        gs.update(data=True, queue=queue, total=len(queue), done=0, hearts=3, streak=0, first_ok=0, fb=None)
        st.rerun()
    total = gs["total"]
    if gs["hearts"] <= 0 or not gs["queue"]:
        score = round(100 * gs["first_ok"] / total)
        if gs["hearts"] <= 0:
            show_result(score, "Kalpların bitti ama pes etme, tekrar dene!", "Kalpler Bitti", "💔")
        else:
            show_result(score, f"İlk denemede {gs['first_ok']} / {total} doğru", "Ders Tamamlandı!", "🦉")
        st.button("🔄 Yeni Ders Başlat", key="again", on_click=regen)
        return
    q = gs["queue"][0]
    st.progress(gs["done"] / total)
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>{"❤️" * gs["hearts"]}{"🖤" * (3 - gs["hearts"])}</span>'
        f'<span class="score-chip">🔥 seri {gs["streak"]}</span><span>{gs["done"]} / {total}</span></div>'
        f'<div class="qtext">{esc(str(q["text"]))}</div></div>',
        unsafe_allow_html=True,
    )
    vt, vp = q["visual"]
    if vt and vt != "yok":
        render_question_visual(vt, vp)
    fb = gs["fb"]
    if fb:
        head, cls = ("🎉 Harika!", "ok") if fb["ok"] else (f"❌ Doğru cevap: {esc(str(fb['label']))}", "bad")
        st.markdown(f'<div class="fb {cls}"><b>{head}</b><div>{esc(str(fb["expl"]))}</div></div>', unsafe_allow_html=True)
        st.button("DEVAM ➡️", key="duo_next", on_click=_duo_next, args=(gs,))
    else:
        with st.container(key="optbox"):
            cols = st.columns(2)
            for i, (label, value) in enumerate(q["options"]):
                with cols[i % 2]:
                    st.button(md_safe(label), key=f"duo_{i}", on_click=_duo_answer, args=(gs, value))


# ------------------------------------------------------------------ EŞLEŞTİRME
def game_matching(gs, game):
    d = load_data(gs, ctx() + "Ünitedeki 6 terimi/kavramı kısa tanımlarıyla eşleştirme etkinliği hazırla. "
                  'Yalnızca geçerli tek bir JSON nesnesi döndür: {"baslik":"...","ciftler":[{"sol":"terim","sag":"kısa tanım"}]}'
                  ' ("sol" ve "sag" değerleri birbirinden farklı olsun)', dict, ("ciftler",),
                  "Eşleştirme hazırlanıyor...", kind="pairs", post=norm_pairs)
    if not d:
        return
    pairs = d["ciftler"]
    n = len(pairs)
    if "rorder" not in gs:
        gs.update(rorder=random.sample(range(n), n), sel=None, done=[], mist=0)

    def _ml(i):
        gs["sel"], gs["msg"] = i, None

    def _mr(j):
        if gs["sel"] is None:
            gs["msg"] = ("bad", "Önce soldan bir terim seç 👈")
        elif gs["sel"] == j:
            gs["done"].append(j)
            gs["sel"], gs["msg"] = None, ("ok", "🎉 Doğru eşleşme!")
        else:
            gs["mist"] += 1
            gs["sel"], gs["msg"] = None, ("bad", "❌ Bu eşleşme değil, tekrar dene.")

    if len(gs["done"]) >= n:
        show_result(max(20, 100 - 10 * gs["mist"]), f"{gs['mist']} yanlış deneme", icon="🔗")
        st.button("🔄 Yeni Eşleştirme", key="again", on_click=regen)
        return
    st.progress(len(gs["done"]) / n)
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>🔗 {len(gs["done"])} / {n} eşleşti</span>'
        f'<span class="score-chip">❌ {gs["mist"]} hata</span></div>'
        f'<div class="qtext">{esc(d["baslik"] or "Terimleri karşılıklarıyla eşleştir")}</div>'
        '<div style="margin-top:6px;color:#99f6e4">Önce soldan terimi, sonra sağdan karşılığını seç.</div></div>',
        unsafe_allow_html=True,
    )
    if gs["msg"]:
        _flash(gs["msg"][0] == "ok", gs["msg"][1])
    cl, cr = st.columns(2)
    with cl, st.container(key="matchL"):
        for i, (left, _r) in enumerate(pairs):
            if i in gs["done"]:
                st.button(f"✅ {md_safe(left)}", key=f"ml_{i}", disabled=True)
            else:
                st.button(("👉 " if gs["sel"] == i else "") + md_safe(left), key=f"ml_{i}", on_click=_ml, args=(i,))
    with cr, st.container(key="matchR"):
        for j in gs["rorder"]:
            if j in gs["done"]:
                st.button(f"✅ {md_safe(pairs[j][1])}", key=f"mr_{j}", disabled=True)
            else:
                st.button(md_safe(pairs[j][1]), key=f"mr_{j}", on_click=_mr, args=(j,))


# ------------------------------------------------------------------ DOĞRU SIRALAMA
def game_ordering(gs, game):
    d = load_data(gs, ctx() + "Ünitede doğru sırası olan bir süreci/olay akışını/işlem basamaklarını sıralama etkinliği hazırla. "
                  'Yalnızca geçerli tek bir JSON nesnesi döndür: {"gorev":"... adımlarını doğru sıraya diz",'
                  '"adimlar":["...","...","...","...","..."]} ("adimlar" DOĞRU sırada, 5 adet, numarasız, birbirinden farklı)',
                  dict, ("adimlar",), "Sıralama hazırlanıyor...", kind="order", post=norm_order)
    if not d:
        return
    steps = d["adimlar"]
    n = len(steps)
    if "opool" not in gs:
        pool = random.sample(range(n), n)
        if pool == list(range(n)):
            pool.reverse()
        gs.update(opool=pool, pick=[], mist=0)

    def _pick(k):
        if k == len(gs["pick"]):
            gs["pick"].append(k)
            gs["msg"] = ("ok", "✅ Doğru sıra!")
        else:
            gs["mist"] += 1
            gs["msg"] = ("bad", "❌ Bu adım şimdi gelmez, başka bir adım dene.")

    def _reset():
        gs["pick"], gs["msg"] = [], None

    if len(gs["pick"]) >= n:
        show_result(max(20, 100 - 15 * gs["mist"]), f"{gs['mist']} yanlış deneme", icon="🧩")
        st.markdown("".join(f'<div class="ochip"><b>{i + 1}</b>{esc(s)}</div>' for i, s in enumerate(steps)),
                    unsafe_allow_html=True)
        st.button("🔄 Yeni Sıralama", key="again", on_click=regen)
        return
    st.progress(len(gs["pick"]) / n)
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>🧩 {len(gs["pick"])} / {n}</span>'
        f'<span class="score-chip">❌ {gs["mist"]} hata</span></div><div class="qtext">{esc(d["gorev"])}</div></div>',
        unsafe_allow_html=True,
    )
    if gs["pick"]:
        st.markdown("".join(f'<div class="ochip"><b>{i + 1}</b>{esc(steps[k])}</div>' for i, k in enumerate(gs["pick"])),
                    unsafe_allow_html=True)
    if gs["msg"]:
        _flash(gs["msg"][0] == "ok", gs["msg"][1])
    st.markdown(f"**{len(gs['pick']) + 1}. adım hangisi?**")
    with st.container(key="orderpool"):
        for k in gs["opool"]:
            if k not in gs["pick"]:
                st.button(md_safe(steps[k]), key=f"op_{k}", on_click=_pick, args=(k,))
    st.button("↺ Baştan Başla", key="o_reset", on_click=_reset)


# ------------------------------------------------------------------ HAFIZA KARTLARI
def game_memory(gs, game):
    d = load_data(gs, ctx() + "Hafıza kartı oyunu için 6 KISA çift hazırla (terim - karşılığı). "
                  'Yalnızca geçerli tek bir JSON nesnesi döndür: {"baslik":"...","ciftler":[{"sol":"kısa terim","sag":"kısa karşılığı"}]}'
                  ' ("sol" ve "sag" en çok 3 kelime olsun, hepsi birbirinden farklı olsun)', dict, ("ciftler",),
                  "Kartlar hazırlanıyor...", kind="memo", post=norm_memo)
    if not d:
        return
    pairs = d["ciftler"]
    n = len(pairs)
    if "cards" not in gs:
        cards = [(i, p[0]) for i, p in enumerate(pairs)] + [(i, p[1]) for i, p in enumerate(pairs)]
        random.shuffle(cards)
        gs.update(cards=cards, flipped=[], matched=[], moves=0)

    def _flip(i):
        if len(gs["flipped"]) >= 2:
            gs["flipped"] = []
        if i in gs["flipped"] or i in gs["matched"]:
            return
        gs["flipped"].append(i)
        if len(gs["flipped"]) == 2:
            gs["moves"] += 1
            a, b = gs["flipped"]
            if gs["cards"][a][0] == gs["cards"][b][0]:
                gs["matched"] += [a, b]
                gs["flipped"] = []
                gs["msg"] = ("ok", "🎉 Çifti buldun!")
            else:
                gs["msg"] = ("bad", "Eşleşmedi; bir sonraki kartta ikisi de kapanır.")

    if len(gs["matched"]) >= 2 * n:
        show_result(max(30, min(100, 100 - (gs["moves"] - n) * 8)), f"{gs['moves']} hamlede bitirdin", icon="🃏")
        st.button("🔄 Yeni Kartlar", key="again", on_click=regen)
        return
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>🃏 {len(gs["matched"]) // 2} / {n} çift</span>'
        f'<span class="score-chip">🎯 {gs["moves"]} hamle</span></div>'
        f'<div class="qtext">{esc(d["baslik"] or "Terim ile karşılığını bul")}</div></div>',
        unsafe_allow_html=True,
    )
    if gs["msg"]:
        _flash(gs["msg"][0] == "ok", gs["msg"][1])
    with st.container(key="mem"):
        for r in range(0, len(gs["cards"]), 4):
            cols = st.columns(4)
            for j, (_pid, text) in enumerate(gs["cards"][r:r + 4]):
                i = r + j
                shown = i in gs["flipped"] or i in gs["matched"]
                label = (("✅ " if i in gs["matched"] else "") + md_safe(text)) if shown else "❓"
                with cols[j]:
                    st.button(label, key=f"mem_{i}", disabled=i in gs["matched"], on_click=_flip, args=(i,))


# ------------------------------------------------------------------ CÜMLE KUR (Duolingo tarzı)
def game_sentence(gs, game):
    prompt = (ctx() + "TAM 5 ADET kısa (3-8 kelimelik) bilgi/örnek cümlesi ve Türkçe anlamını/açıklamasını üret. "
              'Yalnızca geçerli JSON liste döndür: [{"cumle":"...","ceviri":"..."}]')
    data = load_data(gs, prompt, list, ("cumle", "ceviri"), "Cümleler hazırlanıyor...", kind="cumle", item_ok=sentence_ok)
    if not data:
        return
    idx = gs["idx"]
    if idx >= len(data):
        score = round(100 * gs.get("pts", 0) / len(data))
        show_result(score, "Cümle kurma tamamlandı", icon="✍️")
        st.button("🔄 Yeni Cümleler", key="again", on_click=regen)
        return
    words = str(data[idx]["cumle"]).split()
    if gs.get("s_for") != idx:
        order = random.sample(range(len(words)), len(words))
        if [words[i] for i in order] == words and len(set(words)) > 1:
            order.reverse()
        gs.update(s_for=idx, spool=order, spick=[], smist=0, smsg=None)

    def _tap(i):
        if words[i] == words[len(gs["spick"])]:
            gs["spick"].append(i)
            gs["smsg"] = None
        else:
            gs["smist"] += 1
            gs["smsg"] = "❌ Bu kelime şimdi gelmez."

    def _undo():
        if gs["spick"]:
            gs["spick"].pop()

    def _next():
        gs["pts"] = gs.get("pts", 0) + max(0.0, 1 - 0.34 * gs["smist"])
        gs["idx"] += 1

    done = len(gs["spick"]) == len(words)
    st.progress(idx / len(data))
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>Cümle {idx + 1} / {len(data)}</span>'
        f'<span class="score-chip">❌ {gs["smist"]} hata</span></div>'
        f'<div class="qtext">🗣️ {esc(str(data[idx]["ceviri"]))}</div>'
        '<div style="margin-top:6px;color:#99f6e4">Kelimelere sırayla dokunarak cümleyi kur.</div></div>',
        unsafe_allow_html=True,
    )
    built = " ".join(words[i] for i in gs["spick"]) or "…"
    st.markdown(f'<div class="ochip" style="min-height:48px">{esc(built)}</div>', unsafe_allow_html=True)
    if gs["smsg"]:
        st.error(gs["smsg"])
    if done:
        st.success("🎉 Harika, cümleyi doğru kurdun!")
        st.button("➡️ Sonraki Cümle" if idx < len(data) - 1 else "🏆 Sonucu Gör", key=f"s_next_{idx}", on_click=_next)
        return
    with st.container(key="wordchips"):
        cols = st.columns(min(4, len(words)))
        for n_, i in enumerate([i for i in gs["spool"] if i not in gs["spick"]]):
            with cols[n_ % len(cols)]:
                st.button(md_safe(words[i]), key=f"w_{idx}_{i}", on_click=_tap, args=(i,))
    st.button("↩️ Son Kelimeyi Geri Al", key="s_undo", on_click=_undo)


# ------------------------------------------------------------------ ARALIKLI TEKRAR (Doping Hafıza tarzı)
def game_spaced(gs, game):
    prompt = (ctx() + "TAM 6 ADET yepyeni bilgi kartı üret (ön yüz: kısa soru/kavram, arka yüz: net cevap). "
              'Yalnızca geçerli JSON liste döndür: [{"on_yuz":"...","arka_yuz":"..."}]')
    data = load_data(gs, prompt, list, ("on_yuz", "arka_yuz"), "Kartlar hazırlanıyor...")
    if not data:
        return
    if "sq" not in gs:
        gs.update(sq=list(range(len(data))), again_n=0, show=False)

    def _know():
        gs["sq"].pop(0)
        gs["show"] = False

    def _again():
        gs["sq"].append(gs["sq"].pop(0))
        gs["again_n"] += 1
        gs["show"] = False

    def _reveal():
        gs["show"] = True

    total = len(data)
    if not gs["sq"]:
        score = round(100 * total / (total + gs["again_n"]))
        show_result(score, f"{gs['again_n']} kez tekrar ettin", "Hepsini Öğrendin!", "🧠")
        st.button("🔄 Yeni Kartlar", key="again", on_click=regen)
        return
    card = data[gs["sq"][0]]
    st.progress((total - len(gs["sq"])) / total)
    st.markdown(f'<div class="flash" style="background:linear-gradient(135deg,#0d9488,#06b6d4)">'
                f'<div class="tag">Kalan {len(gs["sq"])} kart · tekrar {gs["again_n"]}</div>'
                f'<div class="txt">❓ {esc(str(card["on_yuz"]))}</div></div>', unsafe_allow_html=True)
    if gs["show"]:
        st.markdown(f'<div class="flash" style="background:linear-gradient(135deg,#7c3aed,#d946ef)">'
                    f'<div class="tag">Cevap</div><div class="txt">💡 {esc(str(card["arka_yuz"]))}</div></div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.button("🔁 Tekrar göster", key="sp_again", on_click=_again)
        with c2:
            st.button("✅ Biliyordum", key="sp_know", on_click=_know)
    else:
        st.button("👀 Cevabı Göster", key="sp_show", on_click=_reveal)


# ------------------------------------------------------------------ ŞİMŞEK TURU (tam ekran, hızlı doğru/yanlış)
def game_blitz(gs, game):
    data = load_data(gs, tf_prompt(10, short=True), list, ("ifade", "cevap"), "Şimşek turu hazırlanıyor...", kind="tf")
    if data:
        payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        with st.container(key="balloon_wrap"):
            components.html(BLITZ_HTML.replace("__QUESTIONS__", payload), height=760)


NEW_GAMES = {
    "adam": game_hangman, "duo": game_duo, "eslestir": game_matching, "siralama": game_ordering,
    "hafiza": game_memory, "cumle": game_sentence, "tekrar": game_spaced, "blitz": game_blitz,
}



# =============================================================================
# 9b. OYUN SALONU: yapay zekâ ile oynanan tam ekran oyunlar (UNO, Sudoku, Satranç, ...)
# =============================================================================
ARCADE_SHARED = r'''<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#04252b;--bg2:#073b44;--card:#0b4a55;--line:rgba(94,234,212,.28);--t:#e6fffb;--mut:#8fd9cf;--ac:#2dd4bf;--ac2:#22d3ee;--bad:#fb7185;--ok:#4ade80;--gold:#fbbf24}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:radial-gradient(1200px 700px at 20% -10%,#0e6b73 0,transparent 60%),linear-gradient(160deg,#04252b,#06323a 60%,#041f26);color:var(--t);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;overflow:hidden}
#app{position:absolute;inset:0;display:flex;flex-direction:column;padding:10px 14px 12px;gap:8px;overflow:auto}
.top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.top h2{margin:0;font-size:19px;letter-spacing:.2px}
.sp{flex:1}
.chip{background:rgba(255,255,255,.08);border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-weight:700;font-size:14px}
.btn{border:0;border-radius:14px;padding:10px 16px;font-weight:800;font-size:15px;cursor:pointer;color:#042f2e;background:linear-gradient(135deg,#5eead4,#22d3ee);box-shadow:0 4px 0 #0f766e;font-family:inherit}
.btn:active{transform:translateY(3px);box-shadow:0 1px 0 #0f766e}
.btn.alt{background:rgba(255,255,255,.1);color:var(--t);box-shadow:0 4px 0 rgba(0,0,0,.35);border:1px solid var(--line)}
.btn.bad{background:linear-gradient(135deg,#fda4af,#fb7185);box-shadow:0 4px 0 #9f1239}
.btn[disabled]{opacity:.45;cursor:not-allowed}
.panel{background:rgba(255,255,255,.06);border:1px solid var(--line);border-radius:20px;padding:12px}
.center{display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;gap:12px;text-align:center}
.msg{min-height:24px;font-weight:700;color:var(--mut);text-align:center}
.msg.ok{color:var(--ok)}.msg.bad{color:var(--bad)}
.row{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;align-items:center}
.big{font-size:clamp(28px,6vw,52px);font-weight:900}
.stars{font-size:34px;letter-spacing:4px}
.pop{animation:pop .35s ease}
@keyframes pop{0%{transform:scale(.6);opacity:0}70%{transform:scale(1.08)}100%{transform:scale(1);opacity:1}}
.shake{animation:shake .35s}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-7px)}75%{transform:translateX(7px)}}
</style>
<script>
window.onerror=function(m){try{document.title='JSERR:'+m}catch(e){}};
const $=(s,r)=> (r||document).querySelector(s);
function h(tag,attrs,...kids){const e=document.createElement(tag);for(const k in (attrs||{})){const v=attrs[k];if(k==='class')e.className=v;else if(k==='style')e.style.cssText=v;else if(k.startsWith('on'))e[k]=v;else if(k==='html')e.innerHTML=v;else if(v===false||v==null)continue;else if(v===true)e.setAttribute(k,'');else e.setAttribute(k,v)}for(const c of kids.flat()){if(c==null||c===false)continue;e.append(c.nodeType?c:document.createTextNode(c))}return e}
const rnd=(a,b)=>a+Math.floor(Math.random()*(b-a+1));
const pick=a=>a[Math.floor(Math.random()*a.length)];
function shuf(a){a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
let _ac=null;
function beep(f,d,t,v){try{_ac=_ac||new (window.AudioContext||window.webkitAudioContext)();const o=_ac.createOscillator(),g=_ac.createGain();o.type=t||'sine';o.frequency.value=f;g.gain.value=v||.05;o.connect(g);g.connect(_ac.destination);o.start();g.gain.exponentialRampToValueAtTime(.0001,_ac.currentTime+(d||.15));o.stop(_ac.currentTime+(d||.15))}catch(e){}}
const sfx={ok(){beep(660,.12);setTimeout(()=>beep(880,.15),110)},bad(){beep(180,.25,'sawtooth',.04)},tap(){beep(520,.05,'square',.025)},win(){[523,659,784,1046].forEach((f,i)=>setTimeout(()=>beep(f,.2),i*120))}};
function store(k,v){try{if(v===undefined){return JSON.parse(localStorage.getItem('adenmind_'+k))}localStorage.setItem('adenmind_'+k,JSON.stringify(v))}catch(e){return null}}
</script>
'''

ARCADE_HTML = {}
ARCADE_HTML['uno'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.card{width:62px;height:92px;border-radius:10px;border:3px solid #fff;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:28px;color:#fff;position:relative;cursor:pointer;flex:none;box-shadow:0 4px 8px rgba(0,0,0,.4);transition:transform .15s;user-select:none;text-shadow:0 2px 0 rgba(0,0,0,.35)}
.card.R{background:#e11d48}.card.Y{background:#eab308;color:#422006;text-shadow:none}.card.G{background:#16a34a}.card.B{background:#2563eb}.card.W{background:linear-gradient(135deg,#e11d48 25%,#eab308 25% 50%,#16a34a 50% 75%,#2563eb 75%)}
.card.back{background:#111;border-color:#fff;color:#f43f5e;font-size:15px}
.card.can{transform:translateY(-12px);box-shadow:0 0 0 3px var(--gold),0 6px 12px rgba(0,0,0,.5)}
.card.no{opacity:.55;cursor:not-allowed}
.card small{position:absolute;top:3px;left:5px;font-size:12px}
.hand{display:flex;gap:-18px;justify-content:center;flex-wrap:wrap;gap:6px;padding:14px 4px 6px;max-height:210px;overflow:auto}
.bots{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.bot{padding:8px 12px;border-radius:16px;background:rgba(255,255,255,.07);border:2px solid transparent;text-align:center;min-width:110px}
.bot.act{border-color:var(--gold);background:rgba(251,191,36,.15)}
.mid{display:flex;align-items:center;justify-content:center;gap:22px}
.col{width:34px;height:34px;border-radius:50%;border:3px solid #fff;display:inline-block;vertical-align:middle}
.cp{display:flex;gap:10px;justify-content:center}.cp .col{width:54px;height:54px;cursor:pointer}
</style></head><body><div id="app"></div><script>
const app=$('#app');const COL=['R','Y','G','B'],CN={R:'Kırmızı',Y:'Sarı',G:'Yeşil',B:'Mavi'},CH={R:'#e11d48',Y:'#eab308',G:'#16a34a',B:'#2563eb'};
function deck(){const d=[];for(const c of COL){d.push({c,v:'0'});for(let n=1;n<=9;n++)d.push({c,v:''+n},{c,v:''+n});for(const v of['⊘','⇄','+2'])d.push({c,v},{c,v})}
 for(let i=0;i<4;i++)d.push({c:'W',v:'W'},{c:'W',v:'+4'});return d}
let P,draw_,disc,tp,cur,dir,color,over,busy,mustPick,names,stats={w:0,g:0},pend,unoMsg='';
function start(n){names=['Sen','Robo Ada','Robo Can','Robo Ege'].slice(0,n);draw_=shuf(deck());P=names.map(()=>[]);for(let i=0;i<7;i++)P.forEach(h=>h.push(draw_.pop()));
 while(true){tp=draw_.pop();if(tp.c==='W'||['⊘','⇄','+2'].includes(tp.v))draw_.unshift(tp);else break}
 disc=[tp];color=tp.c;cur=0;dir=1;over=false;busy=false;mustPick=false;pend=null;unoMsg='İlk kart açıldı. Sıra sende!';render()}
function total(){return draw_.length+disc.length+P.reduce((a,h)=>a+h.length,0)}
function drawCard(i){if(!draw_.length){const keep=disc.pop();draw_=shuf(disc);disc=[keep]}if(!draw_.length)return null;const c=draw_.pop();P[i].push(c);return c}
function playable(c){return c.c==='W'||c.c===color||c.v===tp.v}
function nxt(i,k=1){const n=names.length;return((i+dir*k)%n+n)%n}
function label(c){return c.v==='W'?'🌈':c.v}
function cardEl(c,opt){const e=h('div',{class:'card '+c.c+(opt.can?' can':'')+(opt.no?' no':''),onclick:opt.click},h('small',{},label(c)),label(c));return e}
function render(){app.innerHTML='';
 app.append(h('div',{class:'top'},h('h2',{},'🃏 UNO · Yapay zekâya karşı'),h('span',{class:'sp'}),h('span',{class:'chip'},'🏆 '+stats.w+' / '+stats.g),h('button',{class:'btn alt',onclick:menu},'☰ Menü')));
 app.append(h('div',{class:'bots'},names.slice(1).map((n,k)=>h('div',{class:'bot'+(cur===k+1&&!over?' act':'')},h('div',{},'🤖 '+n),h('div',{style:'font-weight:800'},'🂠 '+P[k+1].length+(P[k+1].length===1?'  UNO!':''))))));
 const topEl=cardEl(tp,{});const pile=h('div',{class:'card back',onclick:()=>{if(cur===0&&!over&&!busy&&!mustPick&&!pend)humanDraw()}},'UNO');
 app.append(h('div',{class:'mid'},h('div',{style:'text-align:center'},pile,h('div',{class:'msg'},'Deste '+draw_.length)),topEl,h('div',{style:'text-align:center'},h('span',{class:'col',style:'background:'+CH[color]}),h('div',{class:'msg'},CN[color],' · ',dir===1?'↻':'↺'))));
 app.append(h('div',{class:'msg '+(over?'ok':''),id:'ms'},unoMsg));
 if(pend){const cp=h('div',{class:'cp'},COL.map(c=>h('span',{class:'col',style:'background:'+CH[c],onclick:()=>chooseColor(c)})));app.append(h('div',{class:'msg'},'Renk seç:'),cp)}
 const my=P[0];const myTurn=cur===0&&!over&&!busy&&!pend;
 app.append(h('div',{class:'hand'},my.map((c,i)=>{const ok=myTurn&&playable(c)&&(!mustPick||i===my.length-1);return cardEl(c,{can:ok,no:myTurn&&!ok,click:()=>humanPlay(i)})})));
 if(mustPick&&myTurn)app.append(h('div',{class:'row'},h('button',{class:'btn alt',onclick:()=>{mustPick=false;advance(0)}},'Pas geç')));
 if(over)app.append(h('div',{class:'row'},h('button',{class:'btn',onclick:()=>start(names.length)},'Yeni el')))}
function say(s){unoMsg=s}
function humanDraw(){const c=drawCard(0);sfx.tap();if(c&&playable(c)){mustPick=true;say('Çektiğin kart oynanabilir: oyna ya da pas geç.');render()}else{say('Oynanacak kart yok, pas.');render();setTimeout(()=>advance(0),500)}}
function humanPlay(i){if(over||busy||cur!==0||pend)return;const c=P[0][i];if(!playable(c)||(mustPick&&i!==P[0].length-1))return;mustPick=false;sfx.tap();P[0].splice(i,1);place(0,c)}
function place(i,c){disc.push(c);tp=c;if(c.c!=='W')color=c.c;
 if(!P[i].length){over=true;if(i===0)stats.w++;stats.g++;say(i===0?'🎉 Kazandın!':'😅 '+names[i]+' kazandı');i===0?sfx.win():sfx.bad();render();return}
 let m=names[i]+': '+label(c)+' oynadı';if(P[i].length===1)m+=' – UNO!';say(m);
 if(c.c==='W'){if(i===0){pend=c;render();return}color=bestColor(P[i]);say(m+' · renk '+CN[color])}
 effect(i,c)}
function chooseColor(c){color=c;const card=pend;pend=null;effect(0,card)}
function effect(i,c){let skip=0,n=names.length;
 if(c.v==='⇄'){dir*=-1;if(n===2)skip=1}else if(c.v==='⊘')skip=1;
 else if(c.v==='+2'){const v=nxt(i);for(let k=0;k<2;k++)drawCard(v);skip=1}
 else if(c.v==='+4'){const v=nxt(i);for(let k=0;k<4;k++)drawCard(v);skip=1}
 render();advance(i,skip)}
function advance(i,skip=0){cur=nxt(i,1+skip);render();if(cur!==0&&!over){busy=true;setTimeout(botTurn,900)}}
function bestColor(h2){const cnt={R:0,Y:0,G:0,B:0};h2.forEach(c=>{if(cnt[c.c]!==undefined)cnt[c.c]++});return COL.reduce((a,b)=>cnt[b]>cnt[a]?b:a,pick(COL))}
function botTurn(){busy=false;if(over)return;const i=cur,hand=P[i];
 let opts=hand.map((c,k)=>({c,k})).filter(o=>playable(o.c));
 if(!opts.length){const c=drawCard(i);say(names[i]+' kart çekti');if(c&&playable(c))opts=[{c,k:hand.length-1}];else{render();return setTimeout(()=>advance(i),600)}}
 const nextN=P[nxt(i)].length;
 opts.sort((a,b)=>sc(b.c,nextN,hand)-sc(a.c,nextN,hand));const o=opts[0];hand.splice(o.k,1);sfx.tap();place(i,o.c)}
function sc(c,nextN,hand){let s=0;if(c.c==='W')s-=5;if(['+2','+4','⊘','⇄'].includes(c.v))s+=(nextN<=2?8:2);if(c.v==='+4')s-=(hand.length>3?6:0);
 if(c.c!=='W'&&hand.filter(x=>x.c===c.c).length>2)s+=3;if(/\d/.test(c.v))s+=+c.v/10;return s+Math.random()}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'🃏 UNO'),h('div',{class:'msg'},'Rengi ya da sayıyı eşleştir; özel kartları akıllıca kullan. İlk bitiren kazanır!'),
 h('div',{class:'row'},[[2,'1 rakip'],[3,'2 rakip'],[4,'3 rakip']].map(([n,l])=>h('button',{class:'btn',onclick:()=>start(n)},l)))))}
menu();
</script></body></html>
'''

ARCADE_HTML['sudoku'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.grid{display:grid;gap:0;border:3px solid var(--ac);border-radius:12px;overflow:hidden;background:#052f37;margin:auto}
.c{display:flex;align-items:center;justify-content:center;font-weight:800;cursor:pointer;border:1px solid rgba(94,234,212,.18);user-select:none;position:relative}
.c.given{color:#fff;background:rgba(255,255,255,.07)}
.c.mine{color:var(--ac2)}
.c.sel{background:rgba(45,212,191,.35)}
.c.peer{background:rgba(45,212,191,.12)}
.c.same{background:rgba(251,191,36,.28)}
.c.err{color:var(--bad)!important;background:rgba(251,113,133,.25)}
.c.bR{border-right:3px solid var(--ac)}.c.bB{border-bottom:3px solid var(--ac)}
.c .nt{position:absolute;inset:1px;display:grid;font-size:.38em;color:var(--mut);font-weight:600;line-height:1}
.pad .btn{min-width:46px;padding:10px 0}
</style></head><body><div id="app"></div><script>
const app=$('#app');
let N=9,BR=3,BC=3,sol,puz,cur,sel=-1,notes=false,nt,mist=0,t0=0,tm=null,hints=0,done=false;
function boxOf(r,c){return Math.floor(r/BR)*(N/BC)+Math.floor(c/BC)}
function ok(g,i,v){const r=Math.floor(i/N),c=i%N;for(let k=0;k<N;k++){if(g[r*N+k]===v&&k!==c)return false;if(g[k*N+c]===v&&k!==r)return false}
 const br=Math.floor(r/BR)*BR,bc=Math.floor(c/BC)*BC;for(let a=0;a<BR;a++)for(let b=0;b<BC;b++){const j=(br+a)*N+bc+b;if(j!==i&&g[j]===v)return false}return true}
function solve(g,limit,randomize){let count=0,res=null;
 function rec(){let best=-1,bc=99,bo=null;
  for(let i=0;i<N*N;i++)if(!g[i]){const o=[];for(let v=1;v<=N;v++)if(ok(g,i,v))o.push(v);if(o.length<bc){bc=o.length;best=i;bo=o;if(bc===0)return}}
  if(best<0){count++;if(!res)res=g.slice();return}
  if(randomize)bo=shuf(bo);
  for(const v of bo){g[best]=v;rec();g[best]=0;if(count>=limit)return}}
 rec();return{count,res}}
function gen(diff){const full=solve(new Array(N*N).fill(0),1,true).res;sol=full;
 const holes={4:[6,8,10],6:[16,20,24],9:[38,46,52]}[N][diff];
 let p=full.slice();const order=shuf([...Array(N*N).keys()]);let removed=0;
 for(const i of order){if(removed>=holes)break;const v=p[i];p[i]=0;const t=p.slice();if(solve(t,2).count!==1)p[i]=v;else removed++}
 puz=p;cur=p.slice();nt=Array.from({length:N*N},()=>new Set())}
function menu(){clearInterval(tm);app.innerHTML='';app.append(h('div',{class:'center'},
 h('div',{class:'big'},'🔢 Sudoku'),h('div',{class:'msg'},'Her satır, sütun ve kutuda sayılar bir kez geçmeli. Tek çözümlü yeni bulmaca her seferinde!'),
 h('div',{class:'row'},[[4,'Mini 4×4'],[6,'Orta 6×6'],[9,'Klasik 9×9']].map(([n,l])=>h('button',{class:'btn',onclick:()=>{N=n;BR=n===9?3:2;BC=n===4?2:3;pick2()}},l)))))}
function pick2(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'Zorluk'),h('div',{class:'row'},['Kolay','Orta','Zor'].map((l,i)=>h('button',{class:'btn',onclick:()=>start(i)},l)))))}
function start(d){app.innerHTML='<div class="center big">Hazırlanıyor…</div>';setTimeout(()=>{gen(d);sel=-1;mist=0;hints=0;done=false;t0=Date.now();draw();clearInterval(tm);tm=setInterval(tick,1000)},30)}
function tick(){const e=$('#tm');if(e)e.textContent='⏱ '+fmt((Date.now()-t0)/1000|0)}
function fmt(s){return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')}
function conflicts(i){return cur[i]&&!ok(cur,i,cur[i])}
function draw(){app.innerHTML='';
 app.append(h('div',{class:'top'},h('h2',{},'🔢 Sudoku '+N+'×'+N),h('span',{class:'sp'}),h('span',{class:'chip',id:'tm'},'⏱ 0:00'),h('span',{class:'chip'},'❌ '+mist),h('button',{class:'btn alt',onclick:menu},'☰ Menü')));
 const size=Math.min(innerHeight-250,innerWidth-40,560);const cs=Math.floor(size/N);
 const g=h('div',{class:'grid',style:`grid-template-columns:repeat(${N},${cs}px);font-size:${cs*.55}px`});
 for(let i=0;i<N*N;i++){const r=Math.floor(i/N),c=i%N;let cl='c '+(puz[i]?'given':(cur[i]?'mine':''));
  if(sel>=0){const sr=Math.floor(sel/N),sc=sel%N;if(i===sel)cl+=' sel';else if(cur[sel]&&cur[i]===cur[sel])cl+=' same';else if(sr===r||sc===c||boxOf(sr,sc)===boxOf(r,c))cl+=' peer'}
  if(conflicts(i))cl+=' err';if((c+1)%BC===0&&c<N-1)cl+=' bR';if((r+1)%BR===0&&r<N-1)cl+=' bB';
  const cell=h('div',{class:cl,style:`height:${cs}px`,onclick:()=>{sel=i;sfx.tap();draw()}},cur[i]||'');
  if(!cur[i]&&nt[i].size){const n=h('div',{class:'nt',style:`grid-template-columns:repeat(${BC},1fr)`});for(let v=1;v<=N;v++)n.append(h('span',{style:'text-align:center'},nt[i].has(v)?v:''));cell.append(n)}
  g.append(cell)}
 app.append(g);
 const pad=h('div',{class:'row pad'});for(let v=1;v<=N;v++)pad.append(h('button',{class:'btn',onclick:()=>put(v)},v));
 pad.append(h('button',{class:'btn alt',onclick:()=>put(0)},'⌫'));
 app.append(pad,h('div',{class:'row'},h('button',{class:'btn alt',onclick:()=>{notes=!notes;draw()}},notes?'✏️ Not: AÇIK':'✏️ Not: kapalı'),h('button',{class:'btn alt',onclick:hint},'💡 İpucu ('+hints+')'),h('button',{class:'btn alt',onclick:()=>start(0)},'🔄 Yeni')),h('div',{class:'msg',id:'ms'},''))}
function put(v){if(done||sel<0||puz[sel])return;
 if(notes&&v){nt[sel].has(v)?nt[sel].delete(v):nt[sel].add(v);cur[sel]=0;draw();return}
 cur[sel]=v;nt[sel].clear();if(v){if(sol[sel]!==v){mist++;sfx.bad()}else{sfx.ok();for(let i=0;i<N*N;i++)if(i!==sel)nt[i].delete(v)}}
 draw();check()}
function hint(){if(done)return;const empt=[];for(let i=0;i<N*N;i++)if(cur[i]!==sol[i])empt.push(i);if(!empt.length)return;const i=sel>=0&&cur[sel]!==sol[sel]?sel:pick(empt);cur[i]=sol[i];hints++;sel=i;draw();check()}
function check(){for(let i=0;i<N*N;i++)if(cur[i]!==sol[i])return;done=true;clearInterval(tm);sfx.win();
 const s=Math.max(1,3-Math.floor((mist+hints)/3));const secs=(Date.now()-t0)/1000|0;
 app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'stars'},'⭐'.repeat(s)+'☆'.repeat(3-s)),h('div',{class:'big'},'Bulmaca çözüldü! 🎉'),h('div',{class:'msg'},`Süre ${fmt(secs)} · Hata ${mist} · İpucu ${hints}`),h('div',{class:'row'},h('button',{class:'btn',onclick:()=>start(0)},'Yeni bulmaca'),h('button',{class:'btn alt',onclick:menu},'Menü'))));window.__won=true}
document.addEventListener('keydown',e=>{if(/^[1-9]$/.test(e.key)&&+e.key<=N)put(+e.key);else if(e.key==='Backspace'||e.key==='Delete')put(0);else if(sel>=0&&e.key.startsWith('Arrow')){const d={ArrowLeft:-1,ArrowRight:1,ArrowUp:-N,ArrowDown:N}[e.key];const n=sel+d;if(n>=0&&n<N*N&&!(Math.abs(d)===1&&Math.floor(n/N)!==Math.floor(sel/N))){sel=n;draw()}}});
menu();
</script></body></html>
'''

ARCADE_HTML['satranc'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.board{display:grid;grid-template-columns:repeat(8,1fr);border:3px solid var(--ac);border-radius:10px;overflow:hidden;margin:auto}
.sq{display:flex;align-items:center;justify-content:center;cursor:pointer;position:relative;user-select:none;line-height:1}
.sq.l{background:#cdeee8}.sq.d{background:#2a8f93}
.sq.sel{outline:4px solid var(--gold);outline-offset:-4px}
.sq.last{box-shadow:inset 0 0 0 100px rgba(251,191,36,.35)}
.sq.chk{box-shadow:inset 0 0 0 100px rgba(251,113,133,.65)}
.sq .dot{position:absolute;width:30%;height:30%;border-radius:50%;background:rgba(4,37,43,.45)}
.sq.cap::after{content:'';position:absolute;inset:3px;border:4px solid rgba(4,37,43,.5);border-radius:50%}
.pc{font-family:'Segoe UI Symbol','Noto Sans Symbols2','DejaVu Sans',serif;pointer-events:none}
.pc.w{color:#fff;text-shadow:0 0 2px #000,0 0 2px #000,0 0 3px #000,1px 1px 0 #000,-1px -1px 0 #000}
.pc.b{color:#0a1a1d;text-shadow:0 0 2px #7ee,0 0 1px #7ee}
</style></head><body><div id="app"></div><script>
// ===== MOTOR: 0..63, a8=0 ... h1=63; beyaz büyük harf, siyah küçük harf =====
const START='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const KN=[[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]],KG=[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]];
const isW=p=>p&&p>='A'&&p<='Z';
function parse(fen){const [bd,t,c,ep,hm]=fen.split(' ');const b=[];for(const ch of bd){if(ch==='/')continue;if(/\d/.test(ch)){for(let i=0;i<+ch;i++)b.push('')}else b.push(ch)}
 return{b,turn:t,cr:{K:c.includes('K'),Q:c.includes('Q'),k:c.includes('k'),q:c.includes('q')},ep:ep==='-'?-1:('abcdefgh'.indexOf(ep[0])+(8-+ep[1])*8),hm:+hm||0}}
function attacked(b,sq,byWhite){const r=sq>>3,c=sq&7;
 const pr=byWhite?r+1:r-1;if(pr>=0&&pr<8){for(const dc of[-1,1]){const cc=c+dc;if(cc>=0&&cc<8&&b[pr*8+cc]===(byWhite?'P':'p'))return true}}
 for(const[dr,dc]of KN){const rr=r+dr,cc=c+dc;if(rr>=0&&rr<8&&cc>=0&&cc<8&&b[rr*8+cc]===(byWhite?'N':'n'))return true}
 for(const[dr,dc]of KG){const rr=r+dr,cc=c+dc;if(rr>=0&&rr<8&&cc>=0&&cc<8&&b[rr*8+cc]===(byWhite?'K':'k'))return true}
 for(const[dr,dc]of KG){let rr=r+dr,cc=c+dc;while(rr>=0&&rr<8&&cc>=0&&cc<8){const p=b[rr*8+cc];if(p){const diag=dr&&dc;const q=byWhite?'Q':'q',rk=byWhite?'R':'r',bs=byWhite?'B':'b';if(p===q||(diag?p===bs:p===rk))return true;break}rr+=dr;cc+=dc}}
 return false}
function kingSq(b,w){return b.indexOf(w?'K':'k')}
function pseudo(s){const{b,turn}=s,w=turn==='w',out=[];
 for(let i=0;i<64;i++){const p=b[i];if(!p||isW(p)!==w)continue;const r=i>>3,c=i&7,t=p.toLowerCase();
  if(t==='p'){const d=w?-1:1,start=w?6:1,last=w?0:7;const r1=r+d;
   if(r1>=0&&r1<8&&!b[r1*8+c]){const to=r1*8+c;if(r1===last)for(const pr of'qrbn')out.push({f:i,t:to,pr});else{out.push({f:i,t:to});if(r===start&&!b[(r+2*d)*8+c])out.push({f:i,t:(r+2*d)*8+c,dp:1})}}
   for(const dc of[-1,1]){const cc=c+dc;if(cc<0||cc>7||r1<0||r1>7)continue;const to=r1*8+cc,q=b[to];
    if(q&&isW(q)!==w){if(r1===last)for(const pr of'qrbn')out.push({f:i,t:to,pr});else out.push({f:i,t:to})}
    else if(!q&&to===s.ep)out.push({f:i,t:to,ep:1})}}
  else if(t==='n'||t==='k'){for(const[dr,dc]of(t==='n'?KN:KG)){const rr=r+dr,cc=c+dc;if(rr<0||rr>7||cc<0||cc>7)continue;const q=b[rr*8+cc];if(!q||isW(q)!==w)out.push({f:i,t:rr*8+cc})}
   if(t==='k'){const row=w?7:0;if(i===row*8+4&&!attacked(b,i,!w)){
     if(s.cr[w?'K':'k']&&!b[row*8+5]&&!b[row*8+6]&&b[row*8+7]===(w?'R':'r')&&!attacked(b,row*8+5,!w)&&!attacked(b,row*8+6,!w))out.push({f:i,t:row*8+6,cs:1});
     if(s.cr[w?'Q':'q']&&!b[row*8+3]&&!b[row*8+2]&&!b[row*8+1]&&b[row*8]===(w?'R':'r')&&!attacked(b,row*8+3,!w)&&!attacked(b,row*8+2,!w))out.push({f:i,t:row*8+2,cs:2})}}}
  else{const dirs=t==='r'?KG.filter(d=>!(d[0]&&d[1])):t==='b'?KG.filter(d=>d[0]&&d[1]):KG;
   for(const[dr,dc]of dirs){let rr=r+dr,cc=c+dc;while(rr>=0&&rr<8&&cc>=0&&cc<8){const q=b[rr*8+cc];if(!q)out.push({f:i,t:rr*8+cc});else{if(isW(q)!==w)out.push({f:i,t:rr*8+cc});break}rr+=dr;cc+=dc}}}}
 return out}
function make(s,m){const b=s.b.slice(),w=s.turn==='w',p=b[m.f];let cap=b[m.t];
 b[m.t]=m.pr?(w?m.pr.toUpperCase():m.pr):p;b[m.f]='';
 if(m.ep){b[m.t+(w?8:-8)]='';cap='p'}
 if(m.cs===1){b[m.t-1]=b[m.t+1];b[m.t+1]=''}if(m.cs===2){b[m.t+1]=b[m.t-2];b[m.t-2]=''}
 const cr={...s.cr};
 if(p==='K'){cr.K=cr.Q=false}if(p==='k'){cr.k=cr.q=false}
 if(m.f===63||m.t===63)cr.K=false;if(m.f===56||m.t===56)cr.Q=false;if(m.f===7||m.t===7)cr.k=false;if(m.f===0||m.t===0)cr.q=false;
 return{b,turn:w?'b':'w',cr,ep:m.dp?(m.f+m.t)/2:-1,hm:(p.toLowerCase()==='p'||cap)?0:s.hm+1,cap}}
function legal(s){const w=s.turn==='w',out=[];for(const m of pseudo(s)){const n=make(s,m);if(!attacked(n.b,kingSq(n.b,w),!w))out.push(m)}return out}
function inCheck(s){const w=s.turn==='w';return attacked(s.b,kingSq(s.b,w),!w)}
function perft(s,d){if(!d)return 1;let n=0;for(const m of legal(s)){n+=d===1?1:perft(make(s,m),d-1)}return n}
// ===== YZ: alfa-beta + taş-kare tabloları =====
const VAL={p:100,n:320,b:330,r:500,q:900,k:0};
const PST={p:[0,0,0,0,0,0,0,0,50,50,50,50,50,50,50,50,10,10,20,30,30,20,10,10,5,5,10,25,25,10,5,5,0,0,0,20,20,0,0,0,5,-5,-10,0,0,-10,-5,5,5,10,10,-20,-20,10,10,5,0,0,0,0,0,0,0,0],
 n:[-50,-40,-30,-30,-30,-30,-40,-50,-40,-20,0,0,0,0,-20,-40,-30,0,10,15,15,10,0,-30,-30,5,15,20,20,15,5,-30,-30,0,15,20,20,15,0,-30,-30,5,10,15,15,10,5,-30,-40,-20,0,5,5,0,-20,-40,-50,-40,-30,-30,-30,-30,-40,-50],
 b:[-20,-10,-10,-10,-10,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,10,10,5,0,-10,-10,5,5,10,10,5,5,-10,-10,0,10,10,10,10,0,-10,-10,10,10,10,10,10,10,-10,-10,5,0,0,0,0,5,-10,-20,-10,-10,-10,-10,-10,-10,-20],
 r:[0,0,0,0,0,0,0,0,5,10,10,10,10,10,10,5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,0,0,0,5,5,0,0,0],
 q:[-20,-10,-10,-5,-5,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,5,5,5,0,-10,-5,0,5,5,5,5,0,-5,0,0,5,5,5,5,0,-5,-10,5,5,5,5,5,0,-10,-10,0,5,0,0,0,0,-10,-20,-10,-10,-5,-5,-10,-10,-20],
 k:[-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-20,-30,-30,-40,-40,-30,-30,-20,-10,-20,-20,-20,-20,-20,-20,-10,20,20,0,0,0,0,20,20,20,30,10,0,0,10,30,20]};
function evalS(s){let v=0;for(let i=0;i<64;i++){const p=s.b[i];if(!p)continue;const t=p.toLowerCase();if(isW(p))v+=VAL[t]+PST[t][i];else v-=VAL[t]+PST[t][i^56]}return v}
function order(s,ms){return ms.map(m=>{let sc=0;const cap=s.b[m.t];if(cap)sc=10*VAL[cap.toLowerCase()]-VAL[s.b[m.f].toLowerCase()]/10;if(m.pr)sc+=800;if(m.ep)sc=900;return[sc,m]}).sort((a,b)=>b[0]-a[0]).map(x=>x[1])}
let nodes=0;
function ab(s,d,al,be){nodes++;const ms=legal(s);const w=s.turn==='w';
 if(!ms.length)return inCheck(s)?(w?-99999-d:99999+d):0;
 if(s.hm>=100)return 0;
 if(d===0)return evalS(s);
 if(w){let best=-1e9;for(const m of order(s,ms)){const v=ab(make(s,m),d-1,al,be);if(v>best)best=v;if(v>al)al=v;if(al>=be)break}return best}
 else{let best=1e9;for(const m of order(s,ms)){const v=ab(make(s,m),d-1,al,be);if(v<best)best=v;if(v<be)be=v;if(al>=be)break}return best}}
function aiMove(s,depth,noise){const ms=order(s,legal(s));const w=s.turn==='w';let best=null,bv=w?-1e9:1e9;
 for(const m of shuf(ms)){const v=ab(make(s,m),depth-1,-1e9,1e9)+(Math.random()-.5)*noise;if(w?v>bv:v<bv){bv=v;best=m}}return best}
// ===== ARAYÜZ =====
const app=$('#app');const GL={P:'♙',N:'♘',B:'♗',R:'♖',Q:'♕',K:'♔'};const GB={p:'♟',n:'♞',b:'♝',r:'♜',q:'♛',k:'♚'};
const glyph=p=>isW(p)?'♙♘♗♖♕♔'['PNBRQK'.indexOf(p)]:'♟♞♝♜♛♚'['pnbrqk'.indexOf(p)];
let S,human='w',level=1,selSq=-1,lastM=null,over=false,thinking=false,hist=[],capW=[],capB=[],pendingPromo=null;
const LV=[{n:'Çaylak',d:1,z:120},{n:'Orta',d:2,z:30},{n:'Usta',d:3,z:8}];
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'♞ Satranç'),h('div',{class:'msg'},'Yapay zekâya karşı oyna. Rok, en passant ve vezir terfisi dahil tüm kurallar var.'),
 h('div',{class:'row'},LV.map((l,i)=>h('button',{class:'btn',onclick:()=>{level=i;side()}},l.n)))))}
function side(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'Rengini seç'),h('div',{class:'row'},h('button',{class:'btn',onclick:()=>start('w')},'⚪ Beyaz'),h('button',{class:'btn alt',onclick:()=>start('b')},'⚫ Siyah'),h('button',{class:'btn alt',onclick:()=>start(pick(['w','b']))},'🎲 Rastgele'))))}
function start(c){human=c;S=parse(START);selSq=-1;lastM=null;over=false;hist=[];capW=[];capB=[];pendingPromo=null;draw();maybeAI()}
function status(){const ms=legal(S);if(!ms.length){return inCheck(S)?(S.turn==='w'?'Şah mat! Siyah kazandı':'Şah mat! Beyaz kazandı'):'Pat – berabere'}
 if(S.hm>=100)return'50 hamle kuralı – berabere';const pcs=S.b.filter(x=>x&&x.toLowerCase()!=='k');if(!pcs.length)return'Yetersiz materyal – berabere';return inCheck(S)?'Şah!':''}
function draw(){app.innerHTML='';const st=status();const mate=/mat|berabere|Pat/.test(st);if(mate)over=true;
 app.append(h('div',{class:'top'},h('h2',{},'♞ Satranç · '+LV[level].n),h('span',{class:'sp'}),h('span',{class:'chip'},S.turn===human?'Sıra sende':'YZ düşünüyor…'),h('button',{class:'btn alt',onclick:()=>{if(hist.length>=2&&!thinking&&!over)undo()}},'↩ Geri al'),h('button',{class:'btn alt',onclick:menu},'☰ Menü')));
 const size=Math.min(innerHeight-190,innerWidth-30,640),cs=Math.floor(size/8);
 const flip=human==='b';const bd=h('div',{class:'board',style:`width:${cs*8+6}px;font-size:${cs*.78}px`});
 const tg=new Set(),caps=new Set();if(selSq>=0)for(const m of legal(S))if(m.f===selSq){tg.add(m.t);if(S.b[m.t]||m.ep)caps.add(m.t)}
 const ksq=inCheck(S)?kingSq(S.b,S.turn==='w'):-1;
 for(let k=0;k<64;k++){const i=flip?63-k:k,r=i>>3,c=i&7,p=S.b[i];
  let cl='sq '+((r+c)%2?'d':'l');if(i===selSq)cl+=' sel';if(lastM&&(i===lastM.f||i===lastM.t))cl+=' last';if(i===ksq)cl+=' chk';if(caps.has(i))cl+=' cap';
  const e=h('div',{class:cl,style:`height:${cs}px`,'data-sq':i,onclick:()=>click(i)});
  if(p)e.append(h('span',{class:'pc '+(isW(p)?'w':'b')},glyph(p)));if(tg.has(i)&&!caps.has(i))e.append(h('span',{class:'dot'}));bd.append(e)}
 app.append(bd);
 app.append(h('div',{class:'row'},h('span',{class:'chip'},'Aldıkların: '+(human==='w'?capW:capB).map(glyph).join('')),h('span',{class:'chip'},'YZ aldı: '+(human==='w'?capB:capW).map(glyph).join(''))));
 app.append(h('div',{class:'msg '+(mate?'ok':''),id:'ms'},st));
 if(pendingPromo){const o=h('div',{class:'row panel'},'Terfi: ',...['q','r','b','n'].map(x=>h('button',{class:'btn',onclick:()=>{const m={...pendingPromo,pr:x};pendingPromo=null;play(m)}},glyph(human==='w'?x.toUpperCase():x))));app.append(o)}}
function click(i){if(over||thinking||S.turn!==human||pendingPromo)return;const p=S.b[i];
 if(selSq>=0){const ms=legal(S).filter(m=>m.f===selSq&&m.t===i);if(ms.length){if(ms[0].pr){pendingPromo={f:selSq,t:i};selSq=-1;draw();return}play(ms[0]);return}}
 selSq=(p&&isW(p)===(human==='w'))?i:-1;sfx.tap();draw()}
function play(m){hist.push({S,lastM,capW:capW.slice(),capB:capB.slice()});const n=make(S,m);if(n.cap)(S.turn==='w'?capW:capB).push(n.cap);S=n;lastM=m;selSq=-1;n.cap?sfx.bad():sfx.tap();draw();maybeAI()}
function undo(){const k=S.turn===human?2:1;let h2;for(let i=0;i<k&&hist.length;i++)h2=hist.pop();if(h2){S=h2.S;lastM=h2.lastM;capW=h2.capW;capB=h2.capB}over=false;selSq=-1;draw()}
function maybeAI(){if(over||S.turn===human)return;thinking=true;setTimeout(()=>{const L=LV[level];const m=aiMove(S,L.d,L.z);thinking=false;if(m)play(m)},60)}
menu();
</script></body></html>
'''

ARCADE_HTML['sinema'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.word{font-size:clamp(34px,9vw,76px);font-weight:900;color:var(--gold);text-shadow:0 4px 0 rgba(0,0,0,.35);min-height:90px;display:flex;align-items:center;justify-content:center;text-align:center;padding:0 8px}
.cardx{width:min(94%,620px);border-radius:28px;border:3px solid var(--ac);background:linear-gradient(160deg,#0b4a55,#052a31);padding:22px 16px;text-align:center;box-shadow:0 14px 40px rgba(0,0,0,.4)}
.timer{font-size:clamp(40px,9vw,70px);font-weight:900}.timer.low{color:var(--bad);animation:pop .5s infinite alternate}
.tbar{height:10px;border-radius:99px;background:rgba(255,255,255,.12);overflow:hidden;width:min(90%,560px)}
.tbar i{display:block;height:100%;background:linear-gradient(90deg,#2dd4bf,#fbbf24,#fb7185);transition:width .2s linear}
.sel .btn{margin:3px}.sel .on{outline:3px solid var(--gold)}
.team{padding:8px 14px;border-radius:14px;background:rgba(255,255,255,.08);border:2px solid transparent;font-weight:800}
.team.act{border-color:var(--gold);background:rgba(251,191,36,.15)}
.hide{filter:blur(14px);user-select:none}
.mute{font-size:60px}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const CATS={
 'Filmler & Çizgi Filmler':['Aslan Kral','Kayıp Balık Nemo','Örümcek Adam','Karlar Ülkesi','Shrek','Tom ve Jerry','Pamuk Prenses','Külkedisi','Yeşil Hayalet','Toy Story','Harry Potter','Maymun Kral','Alaaddin','Pinokyo','Cin Ali','Heidi','Susam Sokağı','Red Kit','Fareli Köyün Kavalcısı','Küçük Prens','Hababam Sınıfı','Kurtlar Vadisi','Yedi Cüceler','Dünyayı Kurtaran Adam'],
 'Hayvanlar':['Zürafa','Penguen','Kanguru','Yunus','Kaplumbağa','Aslan','Maymun','Kelebek','Kartal','Fil','Timsah','Yarasa','Ahtapot','Tavşan','Köpekbalığı','Deve','Papağan','Karınca','Panda','Kurbağa','Horoz','Arı','Kirpi','Tilki'],
 'Meslekler':['Doktor','Aşçı','Pilot','İtfaiyeci','Terzi','Berber','Futbolcu','Ressam','Öğretmen','Polis','Çiftçi','Fotoğrafçı','Astronot','Mimar','Marangoz','Garson','Şoför','Dişçi','Müzisyen','Balıkçı','Veteriner','Dalgıç','Posta Dağıtıcısı','Bilim İnsanı'],
 'Okul & Ders Kavramları':['Güneş Tutulması','Su Döngüsü','Fotosentez','Mıknatıs','Deprem','Harita Okumak','Kesir','Üçgen','Cumhuriyet Bayramı','Volkan','Ay\'ın Evreleri','Elektrik Devresi','Kıta','Orman Yangını','Geri Dönüşüm','Teneffüs','Mikroskop','Atatürk','Çevre Temizliği','Deney Yapmak','Zeka Küpü','Kütüphane','Okul Servisi','Pusula'],
 'Spor & Oyun':['Basketbol','Yüzme','Voleybol','Bisiklet','Futbol','Tenis','Satranç','Halat Çekme','Ip Atlama','Kayak','Boks','Okçuluk','Jimnastik','Golf','Gizli Saklambaç','Körebe','Uçurtma Uçurmak','Paten','Dart','Dağa Tırmanmak'],
 'Gezilecek Yerler':['Kapadokya','Ayasofya','Anıtkabir','Pamukkale','Galata Kulesi','Eiffel Kulesi','Çanakkale Şehitliği','Boğaz Köprüsü','Efes Antik Kenti','Sümela Manastırı','Nemrut Dağı','Pisa Kulesi','Piramitler','Çin Seddi','Özgürlük Heykeli','Topkapı Sarayı']};
let S={};
function menu(){app.innerHTML='';S={cat:'Karışık',teams:2,time:60,rounds:2};
 const sel=h('div',{class:'sel center',style:'gap:10px'});
 app.append(h('div',{class:'top'},h('h2',{},'🤫 Sessiz Sinema'),h('span',{class:'sp'})),sel);
 function draw(){sel.innerHTML='';sel.append(h('div',{class:'mute'},'🎭'),h('div',{class:'msg'},'Kelimeyi SESSİZCE, sadece mimikle anlat; takımın bilsin! Sözcük söylemek, parmakla yazmak yok.'),
  h('div',{class:'msg'},'Konu'),h('div',{class:'row'},['Karışık',...Object.keys(CATS)].map(c=>h('button',{class:'btn alt'+(S.cat===c?' on':''),onclick:()=>{S.cat=c;draw()}},c))),
  h('div',{class:'msg'},'Takım sayısı'),h('div',{class:'row'},[2,3,4].map(n=>h('button',{class:'btn alt'+(S.teams===n?' on':''),onclick:()=>{S.teams=n;draw()}},n))),
  h('div',{class:'msg'},'Tur süresi (sn)'),h('div',{class:'row'},[30,45,60,90].map(n=>h('button',{class:'btn alt'+(S.time===n?' on':''),onclick:()=>{S.time=n;draw()}},n))),
  h('div',{class:'msg'},'Tur sayısı (her takım kaç kez oynasın)'),h('div',{class:'row'},[1,2,3].map(n=>h('button',{class:'btn alt'+(S.rounds===n?' on':''),onclick:()=>{S.rounds=n;draw()}},n))),
  h('button',{class:'btn',style:'margin-top:8px',onclick:start},'Başla ▶'))}
 draw()}
function poolFor(){const all=S.cat==='Karışık'?Object.values(CATS).flat():CATS[S.cat];return all}
function nextWord(){const all=poolFor();let used=store('used_'+S.cat)||[];let left=all.filter(w=>!used.includes(w)&&!S.seen.has(w));if(!left.length){used=[];left=all.filter(w=>!S.seen.has(w));if(!left.length){S.seen.clear();left=all.slice()}}
 const w=pick(left);S.seen.add(w);used.push(w);store('used_'+S.cat,used.slice(-200));return w}
function start(){S.seen=new Set();S.names=['🔴 Kırmızı','🔵 Mavi','🟢 Yeşil','🟡 Sarı'].slice(0,S.teams);S.score=S.names.map(()=>0);S.turn=0;S.total=S.teams*S.rounds;ready()}
function board(){return h('div',{class:'row'},S.names.map((n,i)=>h('div',{class:'team'+(i===S.turn%S.teams?' act':'')},n+': '+S.score[i])))}
function ready(){clearInterval(S.tm);app.innerHTML='';const t=S.turn%S.teams;
 app.append(h('div',{class:'top'},h('h2',{},'🤫 Sessiz Sinema'),h('span',{class:'sp'}),h('span',{class:'chip'},'Tur '+(Math.floor(S.turn/S.teams)+1)+'/'+S.rounds),h('button',{class:'btn alt',onclick:menu},'☰')),board(),
  h('div',{class:'center pop'},h('div',{class:'mute'},'🎬'),h('div',{class:'big'},S.names[t]+' takımı sahnede!'),h('div',{class:'msg'},'Bir oyuncu seçilsin. Kelimeyi sadece o görecek; diğerleri ekrana bakmasın.'),h('button',{class:'btn',onclick:play},'Kelimeyi göster ve süreyi başlat ⏱')))}
function play(){S.ok=0;S.pass=0;S.word=nextWord();S.end=Date.now()+S.time*1000;render();clearInterval(S.tm);S.tm=setInterval(tick,200)}
function tick(){const l=Math.max(0,S.end-Date.now());const e=$('#tmr');if(e){e.textContent=Math.ceil(l/1000);e.className='timer'+(l<8000?' low':'')}const b=$('#tb');if(b)b.style.width=(l/(S.time*10))+'%';if(l<=0){clearInterval(S.tm);endTurn()}}
function render(){app.innerHTML='';const t=S.turn%S.teams;
 app.append(h('div',{class:'top'},h('h2',{},S.names[t]),h('span',{class:'sp'}),h('span',{class:'chip'},'✓ '+S.ok),h('span',{class:'chip'},'⏭ '+S.pass+'/3')),
 h('div',{class:'center'},h('div',{class:'tbar'},h('i',{id:'tb',style:'width:'+(Math.max(0,S.end-Date.now())/(S.time*10))+'%'})),h('div',{class:'timer',id:'tmr'},Math.ceil(Math.max(0,S.end-Date.now())/1000)),
  h('div',{class:'cardx'},h('div',{class:'msg'},'🤐 Sessiz anlat!'),h('div',{class:'word'+(S.hide?' hide':''),id:'w'},S.word),h('button',{class:'btn alt',onclick:()=>{S.hide=!S.hide;$('#w').classList.toggle('hide',S.hide)}},'👁 Göster / Gizle')),
  h('div',{class:'row'},h('button',{class:'btn',onclick:right},'✓ Bildiler'),h('button',{class:'btn alt',disabled:S.pass>=3,onclick:pass},'⏭ Pas'))))}
function right(){S.ok++;S.score[S.turn%S.teams]++;sfx.ok();S.word=nextWord();render()}
function pass(){if(S.pass>=3)return;S.pass++;sfx.tap();S.word=nextWord();render()}
function endTurn(){sfx.bad();const t=S.turn%S.teams;app.innerHTML='';S.turn++;const fin=S.turn>=S.total;
 app.append(h('div',{class:'center pop'},h('div',{class:'big'},'⏰ Süre bitti!'),h('div',{class:'msg'},S.names[t]+' takımı '+S.ok+' kelime bildi.'),board(),
  fin?h('button',{class:'btn',onclick:result},'Sonuçlar 🏆'):h('button',{class:'btn',onclick:ready},'Sıradaki takım ▶')))}
function result(){const mx=Math.max(...S.score);const w=S.names.filter((n,i)=>S.score[i]===mx);sfx.win();app.innerHTML='';
 app.append(h('div',{class:'center pop'},h('div',{class:'mute'},'🏆'),h('div',{class:'big'},w.length>1?'Berabere: '+w.join(' & '):w[0]+' kazandı!'),board(),h('div',{class:'row'},h('button',{class:'btn',onclick:start},'Tekrar oyna'),h('button',{class:'btn alt',onclick:menu},'Menü')))); window.__won=true}
menu();
</script></body></html>
'''

ARCADE_HTML['kesir'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.bar{display:flex;width:min(92%,640px);height:90px;border-radius:16px;overflow:hidden;border:3px solid #fff;margin:6px auto;position:relative;background:#7c4a1e}
.pc{flex:1;border-right:3px dashed rgba(255,255,255,.9);display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;cursor:pointer;background:linear-gradient(135deg,#a0602a,#7c4a1e);transition:.25s;color:#fde68a}
.pc:last-child{border-right:0}.pc.on{background:linear-gradient(135deg,#fde047,#f59e0b);color:#422006;transform:scaleY(1.06)}
.bar.mini{height:46px;width:min(80%,420px)}
.orders{font-size:22px;font-weight:800}
.fr{display:inline-flex;flex-direction:column;align-items:center;line-height:1.05;vertical-align:middle;margin:0 4px}
.fr i{display:block;border-top:3px solid currentColor;width:100%;margin:2px 0}
.cut{width:42px;height:42px;border-radius:50%;font-size:22px;padding:0}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const fr=(a,b)=>h('span',{class:'fr'},h('span',{},a),h('i'),h('span',{},b));
const gcd=(a,b)=>b?gcd(b,a%b):a;
let lvl=0,score=0,L,parts=2,sel=new Set(),tries=0,done=false,streak=0,total=0;
function make(){const k=lvl%4;
 if(k===0){const d=rnd(2,8),n=rnd(1,d-1);return{kind:'cut',d,n,txt:'Çikolatayı eşit parçalara böl ve bir müşteriye tam olarak ',goal:true}}
 if(k===1){let d1=rnd(2,8),n1=rnd(1,d1-1),d2=rnd(2,8),n2=rnd(1,d2-1);while(n1*d2===n2*d1){d2=rnd(2,8);n2=rnd(1,d2-1)}return{kind:'cmp',a:[n1,d1],b:[n2,d2]}}
 if(k===2){const d=rnd(2,5),n=rnd(1,d-1),m=rnd(2,3);return{kind:'eq',d,n,m}}
 const d=rnd(3,8),a=rnd(1,d-2),b=rnd(1,d-1-a);return{kind:'add',d,a,b}}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'🍫 Kesir Dilimleme'),h('div',{class:'msg'},'Çikolatayı kes, kesirleri bul, karşılaştır, topla. Sezgiyle kesir öğren!'),h('button',{class:'btn',onclick:()=>{lvl=0;score=0;streak=0;total=0;next()}},'Başla')))}
function next(){L=make();parts=1;sel=new Set();tries=0;done=false;view()}
function head(){return h('div',{class:'top'},h('h2',{},'🍫 Kesir Dilimleme'),h('span',{class:'sp'}),h('span',{class:'chip'},'Seviye '+(lvl+1)),h('span',{class:'chip'},'⭐ '+score),h('button',{class:'btn alt',onclick:menu},'☰'))}
function barEl(d,selSet,click,mini){const b=h('div',{class:'bar'+(mini?' mini':'')});for(let i=0;i<d;i++)b.append(h('div',{class:'pc'+(selSet&&selSet.has(i)?' on':''),onclick:click?()=>click(i):null},selSet&&selSet.has(i)?'':''));return b}
function view(){app.innerHTML='';app.append(head());const box=h('div',{class:'center'});app.append(box);
 if(L.kind==='cut'){box.append(h('div',{class:'orders'},'🧒 "Bana ',fr(L.n,L.d),' ver!"'),h('div',{class:'msg'},'Önce çikolatayı '+L.d+' eşit parçaya böl, sonra parçaları seç.'),barEl(parts,sel,i=>{sel.has(i)?sel.delete(i):sel.add(i);sfx.tap();view()}),
  h('div',{class:'row'},h('button',{class:'btn alt cut',onclick:()=>{if(parts>1){parts--;sel=new Set();sfx.tap();view()}}},'−'),h('span',{class:'chip'},'✂️ '+parts+' parça'),h('button',{class:'btn alt cut',onclick:()=>{if(parts<12){parts++;sel=new Set();sfx.tap();view()}}},'+')),
  h('div',{class:'row'},h('span',{class:'chip'},'Seçtiğin: ',fr(sel.size,parts)),h('button',{class:'btn',onclick:()=>check(parts===L.d&&sel.size===L.n)},'Ver ✓')))}
 else if(L.kind==='cmp'){const[a,b]=[L.a,L.b];box.append(h('div',{class:'orders'},'Hangisi daha büyük?'),h('div',{},fr(a[0],a[1]),barEl(a[1],new Set([...Array(a[0]).keys()]),null,true)),h('div',{},fr(b[0],b[1]),barEl(b[1],new Set([...Array(b[0]).keys()]),null,true)),
  h('div',{class:'row'},h('button',{class:'btn',onclick:()=>check(a[0]*b[1]>b[0]*a[1])},'Üstteki'),h('button',{class:'btn',onclick:()=>check(a[0]*b[1]<b[0]*a[1])},'Alttaki')))}
 else if(L.kind==='eq'){const t=L.d*L.m;box.append(h('div',{class:'orders'},fr(L.n,L.d),' = ',fr('?',t),' ?'),h('div',{class:'msg'},'Çikolatayı '+t+' eşit parçaya böl ve aynı miktarı seç. Kaç parça yeter?'),barEl(t,new Set([...Array(L.n*L.m).keys()]),null,true),barEl(L.d,new Set([...Array(L.n).keys()]),null,true),
  h('div',{class:'row'},[L.n*L.m,L.n*L.m+1,Math.max(1,L.n*L.m-1),L.n+L.d].filter((x,i,a)=>a.indexOf(x)===i).sort(()=>Math.random()-.5).map(v=>h('button',{class:'btn',onclick:()=>check(v===L.n*L.m)},v))))}
 else{box.append(h('div',{class:'orders'},fr(L.a,L.d),' + ',fr(L.b,L.d),' = ?'),h('div',{},barEl(L.d,new Set([...Array(L.a).keys()]),null,true),barEl(L.d,new Set([...Array(L.b).keys()]),null,true)),
  h('div',{class:'row'},[...new Set([L.a+L.b,L.a+L.b+1,Math.max(1,L.a+L.b-1),L.a*L.b+1])].sort(()=>Math.random()-.5).map(v=>h('button',{class:'btn',onclick:()=>check(v===L.a+L.b)},fr(v,L.d)))))}
 box.append(h('div',{class:'msg',id:'ms'},''))}
function check(ok){if(done)return;total++;const ms=$('#ms');
 if(ok){done=true;streak++;const g=Math.max(1,3-tries);score+=g*10;sfx.ok();lvl++;ms.className='msg ok pop';ms.textContent='Harika! '+'⭐'.repeat(g)+(streak>2?'  🔥 seri '+streak:'');setTimeout(()=>{if(lvl>=12)end();else next()},1100)}
 else{tries++;streak=0;sfx.bad();ms.className='msg bad shake';ms.textContent=L.kind==='cut'&&parts!==L.d?'Önce parça sayısı '+L.d+' olmalı (payda).':'Tekrar dene!'}}
function end(){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🎉 Tüm seviyeler bitti!'),h('div',{class:'msg'},'Toplam puan: '+score),h('button',{class:'btn',onclick:menu},'Tekrar oyna')));window.__won=true}
menu();
</script></body></html>
'''

ARCADE_HTML['cebir'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.eq{display:flex;align-items:center;justify-content:center;gap:14px;font-size:clamp(26px,5vw,44px);font-weight:900;margin:8px 0}
.side{min-width:140px;min-height:84px;border:3px dashed var(--line);border-radius:20px;padding:8px 14px;display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap;background:rgba(255,255,255,.05)}
.t{padding:6px 14px;border-radius:14px;background:#0f766e;border:2px solid #5eead4}
.t.x{background:linear-gradient(135deg,#a855f7,#6366f1);border-color:#c4b5fd}
.t.n{background:#b45309;border-color:#fcd34d}
.ops .btn{min-width:64px}
</style></head><body><div id="app"></div><script>
const app=$('#app');
let E,moves,opt,lvl=0,score=0,hist=[],maxL=10,done=false,opKind='+',useX;
// denklem: a*x + b = c*x + d
function gen(l){let a=1,b=0,c=0,d,x=rnd(1,9);
 if(l<2){b=rnd(1,9);d=x+b}
 else if(l<4){a=rnd(2,5);d=a*x}
 else if(l<6){a=rnd(2,5);b=rnd(1,9);d=a*x+b}
 else if(l<8){a=rnd(2,6);c=rnd(1,a-1);b=rnd(1,9);d=(a-c)*x+b;a=a;[b,d]=[b,d];}
 else{b=-rnd(1,9);a=rnd(2,5);d=a*x+b;if(Math.random()<.5){c=rnd(1,a-1);d=(a-c)*x+b}}
 if(l>=6&&l<8){/* a x + b = c x + d  ->  (a-c)x = d-b ; yeniden kur */const e=(a-c)*x;d=e+b}
 return{a,b,c,d,x}}
function fmt(a,b,isLeft){let t=[];if(a)t.push(h('span',{class:'t x'},(a===1?'':a)+(useX?'x':'🐉')));if(b!==0||!a)t.push(h('span',{class:'t n'},(b>0&&a?'+':'')+b));return t}
function side(a,b){const e=h('div',{class:'side'});const parts=[];if(a)parts.push(h('span',{class:'t x'},(a===1?'':a===-1?'−':a)+(useX?'x':'🐉')));if(b!==0||!a)parts.push(h('span',{class:'t n'},(b>0&&a?'+ '+b:b<0&&a?'− '+(-b):b)));e.append(...parts);return e}
function solved(){return(E.a===1&&E.b===0&&E.c===0)}
function start(l){lvl=l;useX=l>=4;E=gen(l);hist=[];moves=0;done=false;opt=plan(E);view()}
function plan(e){let n=0,{a,b,c,d}=e;if(c){n++;a-=c;c=0}if(b){n++;d-=b;b=0}if(a!==1)n++;return n}
function view(){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},'🐉 Ejderha Cebir'),h('span',{class:'sp'}),h('span',{class:'chip'},'Seviye '+(lvl+1)+'/'+maxL),h('span',{class:'chip'},'Hamle '+moves+' (en iyi '+opt+')'),h('button',{class:'btn alt',onclick:menu},'☰')));
 const c=h('div',{class:'center'});app.append(c);
 c.append(h('div',{class:'msg'},useX?'x yalnız kalsın (x = sayı). İki tarafa da aynı işlemi uygula.':'🐉 ejderha (bilinmeyen) tek başına kalsın! Her işlem iki tarafa da uygulanır.'),
 h('div',{class:'eq'},side(E.a,E.b),'=',side(E.c,E.d)));
 const ops=h('div',{class:'row'},['+','−','×','÷'].map(o=>h('button',{class:'btn '+(o===opKind?'':'alt'),onclick:()=>{opKind=o;view()}},o)));
 c.append(ops);
 const nums=new Set();[E.b,E.d,E.a,E.c].forEach(v=>{if(v)nums.add(Math.abs(v))});
 if(opKind==='+'||opKind==='−'){const xs=E.c?['x terimi ('+E.c+(useX?'x':'🐉')+')']:[];}
 const pal=h('div',{class:'row ops'});
 if(opKind==='+'||opKind==='−'){[...nums].sort((x,y)=>x-y).forEach(n=>pal.append(h('button',{class:'btn',onclick:()=>apply(opKind,n)},opKind+n)));
  if(E.c)pal.append(h('button',{class:'btn',onclick:()=>applyX(opKind)},opKind+E.c+(useX?'x':'🐉')),h('button',{class:'btn',onclick:()=>applyX(opKind,E.a)},opKind+E.a+(useX?'x':'🐉')))}
 else{const ns=new Set();[E.a,E.b,E.d,E.c,2,3].forEach(v=>{if(v&&Math.abs(v)>1&&Math.abs(v)<=12)ns.add(Math.abs(v))});[...ns].sort((x,y)=>x-y).forEach(n=>pal.append(h('button',{class:'btn',onclick:()=>apply(opKind,n)},opKind+n)))}
 c.append(pal,h('div',{class:'msg',id:'ms'},''),h('div',{class:'row'},h('button',{class:'btn alt',onclick:undo},'↩ Geri al'),h('button',{class:'btn alt',onclick:()=>start(lvl)},'🔄 Yeniden')))}
function applyX(o,k){const n=k===undefined?E.c:k;const e={...E};const s=o==='+'?1:-1;e.a+=s*n;e.c+=s*n;commit(e)}
function apply(o,n){const e={...E};
 if(o==='+'||o==='−'){const s=o==='+'?n:-n;e.b+=s;e.d+=s}
 else if(o==='×'){e.a*=n;e.b*=n;e.c*=n;e.d*=n}
 else{for(const v of[e.a,e.b,e.c,e.d])if(v%n!==0)return msg('Bu bölme sayıları kesirli yapar; başka işlem dene.',1);e.a/=n;e.b/=n;e.c/=n;e.d/=n}
 commit(e)}
function msg(t,bad){const m=$('#ms');m.textContent=t;m.className='msg '+(bad?'bad shake':'ok')}
function commit(e){if(Math.abs(e.a)>60||Math.abs(e.d)>400||Math.abs(e.b)>400)return msg('Sayılar çok büyüdü.',1);hist.push(E);E=e;moves++;sfx.tap();
 if(E.a===0&&E.c===0)return undo(),msg('Ejderha kayboldu! Geri alındı.',1);
 if(E.a<E.c&&E.c){/* x sağda biriksin: tarafları çevir */const t={a:E.c,b:E.d,c:E.a,d:E.b};E=t}
 if(solved()){done=true;sfx.win();const stars=moves<=opt?3:moves<=opt+2?2:1;score+=stars;view();
  $('#ms').className='msg ok pop';$('#ms').textContent=(useX?'x':'🐉')+' = '+E.d+'  '+'⭐'.repeat(stars)+'  ';
  const nb=h('button',{class:'btn',onclick:()=>{if(lvl+1>=maxL)end();else start(lvl+1)}},lvl+1>=maxL?'Bitir':'Sonraki seviye ▶');$('#ms').after(nb);window.__solved=true;return}
 view()}
function undo(){if(done||!hist.length)return;E=hist.pop();moves=Math.max(0,moves-1);view()}
function end(){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🐉 Cebir ustası!'),h('div',{class:'msg'},'Toplam yıldız: '+score),h('button',{class:'btn',onclick:menu},'Başa dön')));window.__won=true}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'🐉 Ejderha Cebir'),h('div',{class:'msg'},'Denklem çözmeyi oyun gibi öğren: ejderhayı (x) yalnız bırak. Bir tarafa yaptığını diğer tarafa da yap!'),h('button',{class:'btn',onclick:()=>{score=0;start(0)}},'Başla')))}
menu();
</script></body></html>
'''

ARCADE_HTML['canavar'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.rod{display:flex;flex-direction:column;align-items:center;gap:3px;padding:8px 10px;border-radius:14px;background:rgba(255,255,255,.08);border:2px solid var(--line);cursor:pointer;min-width:58px}
.rod .u{display:flex;flex-direction:column;gap:2px}
.rod .u i{display:block;width:26px;height:12px;border-radius:4px}
.rod b{font-size:18px}
.mon{width:min(92%,430px);border-radius:28px;border:4px solid var(--ac);background:rgba(45,212,191,.12);padding:14px;text-align:center}
.mon .face{font-size:64px;line-height:1}
.frame{display:grid;grid-template-columns:repeat(5,28px);gap:4px;justify-content:center;margin:8px 0}
.frame span{width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,.12)}
.frame span.f{background:var(--gold)}
.tray{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;align-items:flex-end}
.dots{display:grid;grid-template-columns:repeat(5,18px);gap:3px;padding:6px}
.dots i{width:18px;height:18px;border-radius:50%;background:#fb7185}
</style></head><body><div id="app"></div><script>
const app=$('#app');const CLR=['#f87171','#fb923c','#facc15','#4ade80','#2dd4bf','#38bdf8','#818cf8','#c084fc','#f472b6','#94a3b8'];
let tgt,tray,got,lvl=0,score=0,moves,mode,cmp,done,msgT='',nextId=1;
function rod(v){return{id:nextId++,v}}
function newRound(){done=false;moves=0;mode=lvl%4===3?'cmp':'fill';
 if(mode==='cmp'){const a=rnd(2,10+Math.min(lvl,6)),b=rnd(2,10+Math.min(lvl,6));cmp={a,b:a===b?a+1:b}}
 else{const hi=Math.min(10,5+Math.floor(lvl/2)+1);tgt=rnd(4,hi+Math.floor(lvl/3));if(tgt>20)tgt=20;got=0;
  // havuz: toplam >= tgt, bazıları büyük (bölme gerektirir)
  tray=[];let sum=0;while(sum<tgt||tray.length<3){const v=rnd(1,Math.min(10,tgt+2));tray.push(rod(v));sum+=v;if(tray.length>6)break}
  if(sum<tgt)tray.push(rod(tgt-sum))}
 view()}
function dots(n){const d=h('div',{class:'dots'});for(let i=0;i<n;i++)d.append(h('i'));return d}
function head(){return h('div',{class:'top'},h('h2',{},'👾 Sayı Canavarları'),h('span',{class:'sp'}),h('span',{class:'chip'},'Tur '+(lvl+1)+'/12'),h('span',{class:'chip'},'⭐ '+score),h('button',{class:'btn alt',onclick:menu},'☰'))}
function rodEl(r,click){const u=h('div',{class:'u'});for(let i=0;i<r.v;i++)u.append(h('i',{style:'background:'+CLR[r.v-1]}));return h('div',{class:'rod',onclick:click},h('b',{},r.v),u)}
function view(){app.innerHTML='';app.append(head());const c=h('div',{class:'center'});app.append(c);
 if(mode==='cmp'){c.append(h('div',{class:'msg'},'Hangi canavarın daha çok yemeği var?'),h('div',{class:'row'},[['a',cmp.a],['b',cmp.b]].map(([k,v])=>h('div',{class:'mon',style:'width:230px;cursor:pointer',onclick:()=>cmpPick(v>(k==='a'?cmp.b:cmp.a))},h('div',{class:'face'},k==='a'?'👾':'👹'),dots(v)))),h('div',{class:'msg',id:'ms'},''));return}
 const fr=h('div',{class:'frame'});for(let i=0;i<Math.max(10,Math.ceil(tgt/5)*5);i++)fr.append(h('span',{class:i<got?'f':'',style:i>=tgt?'opacity:.25':''}));
 c.append(h('div',{class:'mon'},h('div',{class:'face'},got===tgt?'😋':'👾'),h('div',{class:'big'},got+' / '+tgt),fr),
  h('div',{class:'msg'},'Canavar tam '+tgt+' yemek istiyor! Çubuğa dokun; fazlaysa çubuk otomatik bölünür.'),
  h('div',{class:'tray'},tray.map(r=>rodEl(r,()=>feed(r)))),h('div',{class:'msg '+msgT,id:'ms'},''),h('div',{class:'row'},h('button',{class:'btn alt',onclick:()=>{newRound()}},'🔄 Yeni')))}
function feed(r){if(done)return;const need=tgt-got;sfx.tap();moves++;
 if(r.v<=need){got+=r.v;tray=tray.filter(x=>x!==r)}
 else{got+=need;const rest=r.v-need;tray=tray.filter(x=>x!==r);tray.push(rod(rest));msgT='ok';setTimeout(()=>{const m=$('#ms');if(m)m.textContent='✂️ '+r.v+' = '+need+' + '+rest},0)}
 if(got===tgt){done=true;sfx.ok();score+=moves<=3?3:moves<=5?2:1;lvl++;view();$('#ms').className='msg ok pop';$('#ms').textContent='Tıka basa doydu! 🎉';setTimeout(()=>{if(lvl>=12)end();else newRound()},1100)}else view()}
function cmpPick(ok){if(done)return;if(ok){done=true;sfx.ok();score+=2;lvl++;$('#ms').className='msg ok pop';$('#ms').textContent='Doğru! '+cmp.a+' ve '+cmp.b;setTimeout(()=>{if(lvl>=12)end();else newRound()},1000)}else{sfx.bad();$('#ms').className='msg bad shake';$('#ms').textContent='Dikkatle say!'}}
function end(){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🎉 Canavarlar doydu!'),h('div',{class:'msg'},'Puan: '+score),h('button',{class:'btn',onclick:menu},'Tekrar')));window.__won=true}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'👾 Sayı Canavarları'),h('div',{class:'msg'},'Sayı çubuklarıyla canavarları doyur. Sayıları parçala, birleştir ve karşılaştır!'),h('button',{class:'btn',onclick:()=>{lvl=0;score=0;newRound()}},'Başla')))}
menu();
</script></body></html>
'''

ARCADE_HTML['buyuk'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.cols{display:grid;gap:8px;justify-content:center;margin:6px 0}
.pl{background:rgba(255,255,255,.07);border:2px solid var(--line);border-radius:14px;padding:6px 4px;text-align:center;min-width:92px}
.pl h4{margin:0 0 4px;font-size:13px;color:var(--mut)}
.blk{display:flex;flex-wrap:wrap;gap:3px;justify-content:center;min-height:56px;align-content:flex-start}
.blk i{width:16px;height:16px;border-radius:4px;display:block}
.pl .n{font-size:26px;font-weight:900}
.pl.warn{border-color:var(--gold);background:rgba(251,191,36,.12)}
.mini{padding:5px 8px;font-size:12px;border-radius:10px;box-shadow:0 2px 0 #0f766e}
.words{font-size:clamp(18px,3.5vw,28px);font-weight:800;color:var(--gold)}
.eqn{font-size:clamp(24px,5vw,40px);font-weight:900}
</style></head><body><div id="app"></div><script>
const app=$('#app');const PN=['Birler','Onlar','Yüzler','Binler','On Binler','Yüz Binler'],PC=['#94a3b8','#38bdf8','#4ade80','#fbbf24','#fb7185','#c084fc'];
const O=['','bir','iki','üç','dört','beş','altı','yedi','sekiz','dokuz'],T=['','on','yirmi','otuz','kırk','elli','altmış','yetmiş','seksen','doksan'];
function words(n){if(n===0)return'sıfır';const g=x=>{let s='';const y=Math.floor(x/100),r=x%100;if(y)s+=(y>1?O[y]+' ':'')+'yüz ';if(r)s+=T[Math.floor(r/10)]+(r%10?' '+O[r%10]:'');return s.trim()};
 const b=Math.floor(n/1000),r=n%1000;let s='';if(b)s+=(b===1?'':g(b)+' ')+'bin ';if(r)s+=g(r);return s.replace(/\s+/g,' ').trim()}
let mode,A,B,cnt,sub,target,lvl=0,score=0,done,moves,P=4;
function digs(n,k){const d=[];for(let i=0;i<k;i++){d.push(n%10);n=Math.floor(n/10)}return d}
const val=d=>d.reduce((s,x,i)=>s+x*10**i,0);
function newRound(){done=false;moves=0;P=Math.min(6,3+Math.floor(lvl/3));const k=lvl%3;mode=['add','sub','build'][k];
 if(mode==='add'){do{A=rnd(10**(P-2),10**P-1-10**(P-2));B=rnd(10**(P-2),10**P-1-10**(P-2))}while(A+B>=10**P||!carries(A,B));cnt=digs(A,P).map((x,i)=>x+digs(B,P)[i]);target=A+B;sub=null}
 else if(mode==='sub'){do{A=rnd(10**(P-1),10**P-1);B=rnd(10**(P-2),A-1)}while(!borrows(A,B));cnt=digs(A,P);sub=digs(B,P);target=A-B}
 else{target=rnd(10**(P-1),10**P-1);cnt=new Array(P).fill(0);sub=null}
 view()}
function carries(a,b){const x=digs(a,7),y=digs(b,7);return x.some((v,i)=>v+y[i]>=10)}
function borrows(a,b){const x=digs(a,7),y=digs(b,7);return x.some((v,i)=>v<y[i])}
function hiNZ(i){for(let j=i+1;j<P;j++)if(cnt[j]>0)return j;return 0}
function borrow(i){const j=hiNZ(i);if(!j)return false;cnt[j]--;for(let k=j-1;k>i;k--)cnt[k]+=9;cnt[i]+=10;return true}
function pl(i){const c=cnt[i],e=h('div',{class:'pl'+(mode==='add'&&c>=10?' warn':'')+(mode==='sub'&&sub[i]>c?' warn':'')});e.append(h('h4',{},PN[i]),h('div',{class:'blk'},Array.from({length:Math.min(c,60)},()=>h('i',{style:'background:'+PC[i]}))),h('div',{class:'n'},c+(mode==='sub'?' − '+sub[i]:'')));
 const bt=h('div',{class:'row'});
 if(mode==='add'&&c>=10&&i<P-1)bt.append(h('button',{class:'btn mini',onclick:()=>{cnt[i]-=10;cnt[i+1]++;moves++;sfx.ok();view()}},'10 → 1 '+['onluk','yüzlük','binlik','on binlik','yüz binlik'][i]));
 if(mode==='sub'&&sub[i]>c&&hiNZ(i)>0)bt.append(h('button',{class:'btn mini',onclick:()=>{borrow(i);moves++;sfx.ok();view()}},'1 aç → 10'));
 if(mode==='build'){bt.append(h('button',{class:'btn mini alt',onclick:()=>{if(cnt[i]>0){cnt[i]--;sfx.tap();view()}}},'−'),h('button',{class:'btn mini',onclick:()=>{if(cnt[i]<9){cnt[i]++;sfx.tap();view()}}},'+'))}
 e.append(bt);return e}
function view(){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},'🔟 Büyük Sayılar'),h('span',{class:'sp'}),h('span',{class:'chip'},'Tur '+(lvl+1)+'/9'),h('span',{class:'chip'},'⭐ '+score),h('button',{class:'btn alt',onclick:menu},'☰')));
 const c=h('div',{class:'center'});app.append(c);
 if(mode==='add')c.append(h('div',{class:'eqn'},A.toLocaleString('tr-TR')+' + '+B.toLocaleString('tr-TR')+' = ?'),h('div',{class:'msg'},'Basamakları topladık. 10 veya daha fazla olan basamakta 10 tanesini bir üst basamağa çevir.'));
 else if(mode==='sub')c.append(h('div',{class:'eqn'},A.toLocaleString('tr-TR')+' − '+B.toLocaleString('tr-TR')+' = ?'),h('div',{class:'msg'},'Çıkarılacak sayı büyükse bir üst basamaktan 1 aç. Sonra "Çıkar" a bas.'));
 else c.append(h('div',{class:'words'},words(target)),h('div',{class:'msg'},'Okunuşu verilen sayıyı basamak bloklarıyla oluştur.'));
 const g=h('div',{class:'cols',style:`grid-template-columns:repeat(${P},minmax(86px,1fr));width:min(100%,${P*110}px)`});for(let i=P-1;i>=0;i--)g.append(pl(i));c.append(g);
 const cur=mode==='sub'?val(cnt):val(cnt);
 if(mode==='add')c.append(h('div',{class:'eqn'},'= '+(cnt.every(x=>x<10)?val(cnt).toLocaleString('tr-TR'):'…')),h('button',{class:'btn',disabled:!cnt.every(x=>x<10),onclick:()=>fin(val(cnt)===target)},'Tamam ✓'));
 else if(mode==='sub')c.append(h('button',{class:'btn',disabled:!cnt.every((x,i)=>x>=sub[i]),onclick:()=>fin(val(cnt.map((x,i)=>x-sub[i]))===target)},'Çıkar ✓'));
 else c.append(h('div',{class:'eqn'},val(cnt).toLocaleString('tr-TR')),h('button',{class:'btn',onclick:()=>fin(val(cnt)===target)},'Kontrol ✓'));
 c.append(h('div',{class:'msg',id:'ms'},''))}
function fin(ok){if(done)return;const m=$('#ms');if(ok){done=true;sfx.win();score+=moves<=P+2?3:2;lvl++;m.className='msg ok pop';m.textContent='Süper! Sonuç: '+target.toLocaleString('tr-TR')+' — '+words(target);setTimeout(()=>{if(lvl>=9)end();else newRound()},1700)}else{sfx.bad();m.className='msg bad shake';m.textContent='Tam tutmadı, bir daha bak.'}}
function end(){app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'🎉 Büyük sayılar fethedildi!'),h('div',{class:'msg'},'Puan: '+score),h('button',{class:'btn',onclick:menu},'Tekrar')));window.__won=true}
function menu(){app.innerHTML='';app.append(h('div',{class:'center'},h('div',{class:'big'},'🔟 Büyük Sayılar'),h('div',{class:'msg'},'Basamak bloklarıyla toplama, çıkarma ve sayı okuma. Eldeli toplama ve onluk bozmayı görerek öğren!'),h('button',{class:'btn',onclick:()=>{lvl=0;score=0;newRound()}},'Başla')))}
menu();
</script></body></html>
'''

ARCADE_HTML['zihin'] = r'''<!DOCTYPE html><html lang="tr"><head><!--SHARED--><style>
.cell{width:84px;height:84px;border-radius:18px;background:rgba(255,255,255,.1);border:2px solid var(--line);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:900;transition:.12s}
.cell.lit{background:var(--ac);transform:scale(1.08);box-shadow:0 0 22px var(--ac)}
.gridm{display:grid;gap:10px;justify-content:center}
.cat{width:200px;padding:14px;border-radius:20px;background:rgba(255,255,255,.07);border:2px solid var(--line);cursor:pointer;text-align:center}
.cat:hover{border-color:var(--ac)}.cat b{display:block;font-size:20px}.cat span{font-size:13px;color:var(--mut)}
.tbar{height:8px;border-radius:99px;background:rgba(255,255,255,.12);overflow:hidden;width:min(90%,520px)}
.tbar i{display:block;height:100%;background:linear-gradient(90deg,#2dd4bf,#22d3ee);transition:width .2s linear}
.word{font-size:clamp(40px,10vw,84px);font-weight:900}
</style></head><body><div id="app"></div><script>
const app=$('#app');
const CATS=[['mem','🧠','Hafıza','Işık dizisini hatırla'],['att','🎯','Dikkat','Renk–kelime çatışması'],['spd','⚡','Hız','Hızlı doğru/yanlış işlem'],['log','🧩','Mantık','Sayı örüntüsü'],['lan','🔤','Dil','Karışık harfleri düzelt'],['vis','👁️','Görsel','Farklı olanı bul']];
let sc=store('scores')||{},cur,round,pts,tEnd,tmr;
function menu(){clearInterval(tmr);app.innerHTML='';
 const tot=CATS.reduce((a,c)=>a+(sc[c[0]]||0),0);
 app.append(h('div',{class:'top'},h('h2',{},'🧠 Zihin Antrenmanı'),h('span',{class:'sp'}),h('span',{class:'chip'},'Zihin puanı: '+tot)),h('div',{class:'msg'},'Her oyun 45 saniye. En iyi skorların beyin haritanı doldurur!'));
 const g=h('div',{class:'row'},CATS.map(c=>h('div',{class:'cat',onclick:()=>begin(c[0])},h('div',{style:'font-size:38px'},c[1]),h('b',{},c[2]),h('span',{},c[3]),h('div',{class:'chip',style:'margin-top:8px;display:inline-block'},'En iyi: '+(sc[c[0]]||0)))));
 app.append(g,radar())}
function radar(){const n=CATS.length,R=110,cx=140,cy=130;const mx=Math.max(100,...CATS.map(c=>sc[c[0]]||0));
 const pt=(i,v)=>{const a=-Math.PI/2+i*2*Math.PI/n;return[cx+Math.cos(a)*R*v,cy+Math.sin(a)*R*v]};
 let s=`<svg viewBox="0 0 280 260" width="280" height="260" style="margin:auto;display:block">`;
 for(const k of[.33,.66,1])s+=`<polygon points="${CATS.map((c,i)=>pt(i,k).join(',')).join(' ')}" fill="none" stroke="rgba(94,234,212,.3)"/>`;
 s+=`<polygon points="${CATS.map((c,i)=>pt(i,(sc[c[0]]||0)/mx).join(',')).join(' ')}" fill="rgba(45,212,191,.45)" stroke="#2dd4bf" stroke-width="2"/>`;
 CATS.forEach((c,i)=>{const[x,y]=pt(i,1.18);s+=`<text x="${x}" y="${y}" fill="#e6fffb" font-size="12" text-anchor="middle" dominant-baseline="middle">${c[1]} ${c[2]}</text>`});
 return h('div',{html:s+'</svg>'})}
function begin(k){cur=k;pts=0;round=0;tEnd=Date.now()+45000;clearInterval(tmr);tmr=setInterval(()=>{const r=Math.max(0,tEnd-Date.now());const b=$('#tb');if(b)b.style.width=(r/450)+'%';if(r<=0&&!(cur==='mem'&&memBusy))finish()},150);
 app.innerHTML='';GAME[k]()}
function frame(title,body){app.innerHTML='';app.append(h('div',{class:'top'},h('h2',{},title),h('span',{class:'sp'}),h('span',{class:'chip',id:'pt'},'Puan '+pts),h('button',{class:'btn alt',onclick:menu},'☰')),h('div',{class:'center',style:'gap:14px'},h('div',{class:'tbar'},h('i',{id:'tb',style:'width:'+Math.max(0,(tEnd-Date.now())/450)+'%'})),body,h('div',{class:'msg',id:'ms'},'')))}
function add(n,ok){pts=Math.max(0,pts+n);const p=$('#pt');if(p)p.textContent='Puan '+pts;ok?sfx.ok():sfx.bad();const m=$('#ms');if(m){m.className='msg '+(ok?'ok':'bad');m.textContent=ok?'✓':'✗'}}
function finish(){clearInterval(tmr);const best=Math.max(sc[cur]||0,pts);const isNew=best>(sc[cur]||0);sc[cur]=best;store('scores',sc);sfx.win();
 app.innerHTML='';app.append(h('div',{class:'center pop'},h('div',{class:'big'},'⏱ Süre doldu!'),h('div',{class:'msg'},'Puan: '+pts+(isNew?'  🏅 Yeni rekor!':'')),h('div',{class:'row'},h('button',{class:'btn',onclick:()=>begin(cur)},'Tekrar'),h('button',{class:'btn alt',onclick:menu},'Menü'))));window.__fin=pts}
let memBusy=false;
const GAME={
 async mem(){let seq=[],len=2;const size=3;const lit=i=>{const e=$('#c'+i);if(e){e.classList.add('lit');setTimeout(()=>e.classList.remove('lit'),380)}};
  const cells=[];const g=h('div',{class:'gridm',style:`grid-template-columns:repeat(${size},84px)`});for(let i=0;i<9;i++)g.append(h('div',{class:'cell',id:'c'+i,onclick:()=>tap(i)},''));frame('🧠 Hafıza',g);
  let inp=[],accept=false;
  async function show(){memBusy=true;accept=false;inp=[];seq=Array.from({length:len},()=>rnd(0,8));$('#ms').textContent='İzle…';await sleep(500);for(const i of seq){lit(i);sfx.tap();await sleep(650)}memBusy=false;accept=true;if($('#ms'))$('#ms').textContent='Sıra sende';if(Date.now()>tEnd)finish()}
  function tap(i){if(!accept)return;lit(i);inp.push(i);const k=inp.length-1;if(seq[k]!==i){accept=false;add(0,false);len=Math.max(2,len-1);setTimeout(()=>{if(Date.now()<tEnd)show();else finish()},700);return}
   if(inp.length===seq.length){accept=false;add(seq.length*5,true);len++;setTimeout(()=>{if(Date.now()<tEnd)show();else finish()},700)}}
  window.__memSeq=()=>seq;window.__memTap=tap;show()},
 att(){const W=[['KIRMIZI','#ef4444'],['MAVİ','#3b82f6'],['YEŞİL','#22c55e'],['SARI','#eab308']];let ans;
  function nx(){const w=pick(W),c=Math.random()<.5?w:pick(W);ans=c[0];const body=h('div',{class:'center'},h('div',{class:'msg'},'Kelimenin ANLAMINA değil RENGİNE bak!'),h('div',{class:'word',style:'color:'+c[1]},w[0]),h('div',{class:'row'},W.map(x=>h('button',{class:'btn',style:'background:'+x[1]+';color:#fff',onclick:()=>{const ok=x[0]===ans;add(ok?10:-5,ok);nx()}},x[0]))));frame('🎯 Dikkat',body);window.__ans=()=>ans}nx()},
 spd(){function nx(){const a=rnd(3,19),b=rnd(2,12),op=pick(['+','−','×']);const r=op==='+'?a+b:op==='−'?a-b:a*b;const shown=Math.random()<.5?r:r+pick([-2,-1,1,2,10]);const ok=shown===r;
  frame('⚡ Hız',h('div',{class:'center'},h('div',{class:'big'},`${a} ${op} ${b} = ${shown}`),h('div',{class:'row'},h('button',{class:'btn',onclick:()=>{add(ok?8:-5,ok);nx()}},'✓ Doğru'),h('button',{class:'btn bad',onclick:()=>{add(!ok?8:-5,!ok);nx()}},'✗ Yanlış'))));window.__ok=ok}nx()},
 log(){function nx(){const t=rnd(0,3);let s=[],a=rnd(1,9),d=rnd(2,6),r=rnd(2,3),ans;
  if(t===0){s=[0,1,2,3].map(i=>a+d*i);ans=a+d*4}else if(t===1){s=[0,1,2,3].map(i=>a*r**i);ans=a*r**4}else if(t===2){s=[0,1,2,3].map(i=>(i+1)**2+a);ans=25+a}else{s=[a,d];for(let i=2;i<5;i++)s.push(s[i-1]+s[i-2]);ans=s[3]+s[4-0-1+0]-0;ans=s[4-1]+s[4-2];s=s.slice(0,4);ans=s[3]+s[2]}
  const o=shuf([...new Set([ans,ans+rnd(1,4),ans-rnd(1,4),ans+rnd(5,9)])].filter(x=>x>0));
  frame('🧩 Mantık',h('div',{class:'center'},h('div',{class:'big'},s.join(' , ')+' , ?'),h('div',{class:'row'},o.map(v=>h('button',{class:'btn',onclick:()=>{const ok=v===ans;add(ok?12:-4,ok);nx()}},v)))));window.__ans=ans}nx()},
 lan(){const WL=['OKUL','KİTAP','KALEM','DEFTER','ÖĞRETMEN','SINIF','BİLGİ','MATEMATİK','TÜRKİYE','ÇİÇEK','GÜNEŞ','DENİZ','ORMAN','HARİTA','ATLAS','MİKROSKOP','HÜCRE','KESİR','ÜÇGEN','ENERJİ','MADDE','İKLİM','CUMHURİYET','ÖZGÜRLÜK','KÜTÜPHANE'];let w;
  function nx(){w=pick(WL);let sh;do{sh=shuf([...w]).join('')}while(sh===w);let g=[];
   const t=h('div',{class:'center'},h('div',{class:'big'},sh),h('div',{class:'chip',id:'gs',style:'min-height:30px;font-size:22px'},''),h('div',{class:'row'},[...sh].map((ch,i)=>h('button',{class:'btn',id:'L'+i,onclick:e=>{g.push(ch);e.target.disabled=true;sfx.tap();$('#gs').textContent=g.join('');if(g.length===w.length){const ok=g.join('')===w;add(ok?w.length*2:-5,ok);setTimeout(nx,300)}}},ch))),h('button',{class:'btn alt',onclick:nx},'Geç'));
   frame('🔤 Dil',t);window.__word=w}nx()},
 vis(){let n=3;function nx(){n=Math.min(6,3+Math.floor(pts/60));const A=pick(['●','■','▲','◆','★','♥']);let B;do{B=pick(['●','■','▲','◆','★','♥'])}while(B===A);const idx=rnd(0,n*n-1);const hue=rnd(0,360);
   const g=h('div',{class:'gridm',style:`grid-template-columns:repeat(${n},64px)`});for(let i=0;i<n*n;i++)g.append(h('div',{class:'cell',style:`width:64px;height:64px;color:hsl(${hue},80%,65%)`,onclick:()=>{const ok=i===idx;add(ok?9:-5,ok);nx()}},i===idx?B:A));
   frame('👁️ Görsel',h('div',{class:'center'},h('div',{class:'msg'},'Farklı olan şekli bul!'),g));window.__odd=idx}nx()}};
menu();
</script></body></html>
'''

ARCADES = [('uno', '🃏', 'UNO', 'linear-gradient(135deg, #ef4444, #f59e0b)', 'Robot rakiplere karşı kart savaşı'), ('sudoku', '🔢', 'Sudoku', 'linear-gradient(135deg, #0ea5e9, #6366f1)', '4×4, 6×6, 9×9 mantık bulmacası'), ('satranc', '♞', 'Satranç', 'linear-gradient(135deg, #334155, #0f766e)', 'Yapay zekâya karşı tam kurallı'), ('sinema', '🤫', 'Sessiz Sinema', 'linear-gradient(135deg, #f43f5e, #9333ea)', 'Mimikle anlat, takımın bilsin'), ('kesir', '🍫', 'Kesir Dilimleme', 'linear-gradient(135deg, #f59e0b, #b45309)', 'Kes, böl, karşılaştır, topla'), ('cebir', '🐉', 'Ejderha Cebir', 'linear-gradient(135deg, #a855f7, #6366f1)', 'Denklemi oyunla çöz'), ('canavar', '👾', 'Sayı Canavarları', 'linear-gradient(135deg, #22c55e, #0d9488)', 'Sayı çubuklarıyla doyur'), ('buyuk', '🔟', 'Büyük Sayılar', 'linear-gradient(135deg, #ec4899, #8b5cf6)', 'Basamak blokları, eldeli işlem'), ('zihin', '🧠', 'Zihin Antrenmanı', 'linear-gradient(135deg, #14b8a6, #06b6d4)', 'Hafıza, dikkat, hız, mantık')]


def pick_arcade(k):
    st.session_state["selected_arcade"] = k


def leave_arcade():
    st.session_state["selected_arcade"] = None


def arcade_page(key):
    info = next(g for g in ARCADES if g[0] == key)
    c1, c2, c3 = st.columns([1.2, 1.3, 5.5])
    with c1:
        st.button("⬅️ Geri", key="back_arcade", on_click=leave_arcade)
    with c2:
        components.html(FS_BUTTON, height=52)
    with c3:
        st.markdown(f'<div class="gamebar-title">{info[1]} {esc(info[2])} · Oyun Salonu</div>', unsafe_allow_html=True)
    html = ARCADE_HTML[key].replace("<!--SHARED-->", ARCADE_SHARED)
    with st.container(key="balloon_wrap"):
        components.html(html, height=760)



# =============================================================================
# 10. ANA AKIŞ
# =============================================================================
subj = st.session_state["selected_subject"]
unit = st.session_state["selected_unit"]
game = st.session_state["selected_game"]
arcade = st.session_state.get("selected_arcade")
in_game = bool(subj and unit and game) or bool(arcade)

css = BASE_CSS + (GAME_CSS if in_game else "") + (BALLOON_CSS if (in_game and game == "balon") or arcade else "")
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
if arcade:
    arcade_page(arcade)

elif not subj:
    st.markdown('<div class="section-title">🌟 Çalışmak istediğin dersi seç</div>', unsafe_allow_html=True)
    items = [(name, d["ikon"], name, d["renk"]) for name, d in MEB_CURRICULUM.items()]
    card_grid(items, 3, "sub", pick_subject, CARD_H)
    st.markdown('<div class="section-title">🕹️ Yapay Zekâ ile Oyun Salonu</div>', unsafe_allow_html=True)
    card_grid([(g[0], g[1], g[2], g[3], g[4]) for g in ARCADES], 3, "arc", pick_arcade, CARD_H)

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
    items = [tuple(g) for g in GAMES]
    card_grid(items, 3, "game", pick_game, CARD_H)

# --- AŞAMA 4: OYUN (tam ekran düzeni) ---
else:
    gs = get_gs(game)
    ikon = GAME_INFO[game][1]
    game_topbar(f"{ikon} {GAME_INFO[game][2]} · {subj} · {unit}")
    if gs.get("offline"):
        st.info("📴 Yapay zekâya ulaşılamadı; yerel üretici / kayıtlı sorular kullanılıyor.")

    # 1. Balon patlatmaca
    if game == "balon":
        prompt = (
            ctx() + "TAM 5 ADET özgün, gerçek hayat senaryolu çoktan seçmeli (A, B, C, D) soru üret.\n"
            + VISUAL_RULES + MCQ_FORMAT
        )
        data = load_data(gs, prompt, list, ("soru", "secenekler", "dogru_cevap"), "Balon soruları hazırlanıyor...", kind="mcq")
        if data:
            payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
            with st.container(key="balloon_wrap"):
                components.html(BALLOON_HTML.replace("__QUESTIONS__", payload), height=760)

    # 2. 5 soruluk kazanım yarışması
    elif game == "sinav10":
        prompt = ctx() + "TAM 5 ADET yepyeni çoktan seçmeli (4 şıklı) soru üret.\n" + VISUAL_RULES + MCQ_FORMAT
        data = load_data(gs, prompt, list, ("soru", "secenekler", "dogru_cevap"), "Kazanım soruları hazırlanıyor...", kind="mcq")
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
        data = load_data(gs, prompt, list, ("ifade", "cevap"), "Önermeler hazırlanıyor...", kind="tf")
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
                    with loading("AdenMind değerlendiriyor", 5, kind="eval"):
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
        data = load_data(gs, prompt, list, ("kelime", "ipucu"), "Bulmaca hazırlanıyor...", kind="words", item_ok=word_ok)
        if data:
            idx = gs["idx"]
            if idx < len(data):
                item = data[idx]
                word = re.sub(r"\s+", "", str(item["kelime"]))
                word = word.upper() if subj in LANG_SUBJECTS else tr_upper(word)
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
                with loading("AdenMind kâğıdını okuyor", 6, kind="eval"):
                    for i, cq in enumerate(data):
                        if answers[i].strip():
                            res = ai_generate_content(
                                f"Soru: {cq['soru']}\nİdeal cevap: {cq['beklenen_cevap']}\nÖğrenci: {answers[i]}\n"
                                "0-20 arası puan ve kısa, cesaretlendirici bir açıklama ver."
                            )
                            gs["results"].append((i, res or "Değerlendirme yapılamadı."))
            for i, res in gs["results"] or []:
                st.info(f"**Soru {i + 1} Değerlendirmesi**\n\n{res}")

    elif game in NEW_GAMES:
        NEW_GAMES[game](gs, game)
