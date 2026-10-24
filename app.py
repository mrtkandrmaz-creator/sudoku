import json
import os
import random
import re
import time
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi",
    page_icon="🎒",
    layout="wide",
)


# --- KESİN METİN VE DERECE TEMİZLEME MOTORU ---
def clean_math_text(text):
  if not isinstance(text, str):
    return text
  text = re.sub(r"\\circ", "°", text)
  text = re.sub(r"\bcirc\b", "°", text, flags=re.IGNORECASE)
  text = re.sub(r"&deg;", "°", text)
  text = re.sub(r"°\s*°", "°", text)
  return text


def deep_clean_json_data(data):
  if isinstance(data, str):
    return clean_math_text(data)
  elif isinstance(data, list):
    return [deep_clean_json_data(item) for item in data]
  elif isinstance(data, dict):
    return {k: deep_clean_json_data(v) for k, v in data.items()}
  return data


# --- KESİN GÜVENLİ JSON PARSER (HATA RİSKİNİ SIFIRLAR) ---
def safe_parse_json(raw_text):
  if not raw_text:
    return None
  try:
    # Markdown kod bloklarını temizle
    cleaned = re.sub(r"```json|```", "", raw_text).strip()
    # İlk '[' ile son ']' arasını veya ilk '{' ile son '}' arasını yakala
    match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
    if match:
      cleaned = match.group(1)
    data = json.loads(cleaned)
    return deep_clean_json_data(data)
  except Exception:
    # Alternatif temizleme denemesi
    try:
      cleaned = raw_text.replace("'", '"')
      data = json.loads(cleaned)
      return deep_clean_json_data(data)
    except Exception:
      return None


# --- 1. [api_keys] TOML YAPISINI DOĞRUDAN OKUYAN KESİN MOTOR ---


def get_all_api_keys():
  gemini_keys = []
  groq_keys = []
  try:
    if hasattr(st, "secrets") and "api_keys" in st.secrets:
      api_block = st.secrets["api_keys"]
      if "groq_keys" in api_block:
        for k in api_block["groq_keys"]:
          if isinstance(k, str) and len(k.strip()) > 5:
            if k.strip() not in groq_keys:
              groq_keys.append(k.strip())
      if "gemini_keys" in api_block:
        for k in api_block["gemini_keys"]:
          if isinstance(k, str) and len(k.strip()) > 5:
            if k.strip() not in gemini_keys:
              gemini_keys.append(k.strip())
  except Exception:
    pass

  if "manual_gemini" in st.session_state and st.session_state["manual_gemini"]:
    if st.session_state["manual_gemini"] not in gemini_keys:
      gemini_keys.append(st.session_state["manual_gemini"])
  if "manual_groq" in st.session_state and st.session_state["manual_groq"]:
    if st.session_state["manual_groq"] not in groq_keys:
      groq_keys.append(st.session_state["manual_groq"])

  return gemini_keys, groq_keys


gemini_keys, groq_keys = get_all_api_keys()

has_gemini = False
has_groq = False

try:
  import google.generativeai as genai

  if gemini_keys:
    has_gemini = True
except ImportError:
  pass

try:
  from groq import Groq

  if groq_keys:
    has_groq = True
except ImportError:
  pass


def ai_generate_content(prompt_text):
  raw_res = None
  if has_groq and groq_keys:
    for gr_key in groq_keys:
      try:
        client = Groq(api_key=gr_key)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.7,
        )
        if completion.choices[0].message.content:
          raw_res = completion.choices[0].message.content
          break
      except Exception:
        continue

  if not raw_res and has_gemini and gemini_keys:
    for g_key in gemini_keys:
      try:
        genai.configure(api_key=g_key)
        for model_name in [
            "gemini-2.5-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]:
          try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt_text)
            if response and response.text:
              raw_res = response.text
              break
          except Exception:
            continue
        if raw_res:
          break
      except Exception:
        continue

  return clean_math_text(raw_res) if raw_res else None


# --- 2. 5. SINIF MEB MÜFREDATI VE DERS RENKLERİ ---
MEB_CURRICULUM = {
    "Türkçe": {
        "renk": "linear-gradient(135deg, #ff416c, #ff4b2b)",
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
        "renk": "linear-gradient(135deg, #2193b0, #6dd5ed)",
        "ikon": "📐",
        "uniteler": [
            "1. Ünite: Doğal Sayılar",
            "2. Ünite: Kesirler",
            "3. Ünite: Ondalık Gösterimler",
            "4. Ünite: Geometrik Kavramlar ve Üçgenler",
            "5. Ünite: Veri İşleme",
        ],
    },
    "Fen Bilimleri": {
        "renk": "linear-gradient(135deg, #11998e, #38ef7d)",
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
        "renk": "linear-gradient(135deg, #f2994a, #f2c94c)",
        "ikon": "🌍",
        "uniteler": [
            "1. Ünite: Birlikte Yaşamak",
            "2. Ünite: Evimiz Dünya",
            "3. Ünite: Kültür ve Miras",
            "4. Ünite: Yaşayan Türkiye",
            "5. Üreten Türkiye",
            "6. Ünite: Yönetime Katılıyorum",
        ],
    },
    "Din Kültürü ve Ahlak Bilgisi": {
        "renk": "linear-gradient(135deg, #834d9b, #d04ed6)",
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
        "renk": "linear-gradient(135deg, #ee0979, #ff6a00)",
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
        "renk": "linear-gradient(135deg, #56ab2f, #a8e063)",
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

# --- 3. SESSION STATE TANIMLARI ---
if "selected_subject" not in st.session_state:
  st.session_state["selected_subject"] = None
if "selected_unit" not in st.session_state:
  st.session_state["selected_unit"] = None
if "selected_game" not in st.session_state:
  st.session_state["selected_game"] = None
if "game_started" not in st.session_state:
  st.session_state["game_started"] = False
if "coach_theme" not in st.session_state:
  st.session_state["coach_theme"] = "Mavi-Beyaz"
if "coach_messages" not in st.session_state:
  st.session_state["coach_messages"] = [
      {
          "role": "assistant",
          "content": (
              "Merhaba ben AdenMind, sana yardımcı olmak için buradayım! 🦊✨"
          ),
      }
  ]

if "dy_score" not in st.session_state:
  st.session_state["dy_score"] = 0
if "dy_current_q" not in st.session_state:
  st.session_state["dy_current_q"] = 0
if "dy_feedback" not in st.session_state:
  st.session_state["dy_feedback"] = ""

if "kazanim_idx" not in st.session_state:
  st.session_state["kazanim_idx"] = 0
if "kazanim_score" not in st.session_state:
  st.session_state["kazanim_score"] = 0
if "kazanim_answers" not in st.session_state:
  st.session_state["kazanim_answers"] = {}

if "fill_idx" not in st.session_state:
  st.session_state["fill_idx"] = 0
if "fill_score" not in st.session_state:
  st.session_state["fill_score"] = 0
if "fill_feedback" not in st.session_state:
  st.session_state["fill_feedback"] = ""

# --- 4. TEMA RENK SEÇENEKLERİ ---
theme_choice = st.session_state["coach_theme"]
if theme_choice == "Pembe":
  c_bg_gradient = "linear-gradient(135deg, #ff758c, #ff7eb3)"
  c_border = "#ff477e"
  c_accent = "#d63384"
  c_bubble_user = "#ffccd5"
  c_bubble_ai = "#ffe5ec"
  c_text_color = "#590d22"
elif theme_choice == "Sarı-Kırmızı":
  c_bg_gradient = "linear-gradient(135deg, #f12711, #f5af19)"
  c_border = "#f5af19"
  c_accent = "#b91c1c"
  c_bubble_user = "#fef08a"
  c_bubble_ai = "#fef2f2"
  c_text_color = "#7f1d1d"
elif theme_choice == "Mavi-Beyaz":
  c_bg_gradient = "linear-gradient(135deg, #2563eb, #60a5fa)"
  c_border = "#3b82f6"
  c_accent = "#1d4ed8"
  c_bubble_user = "#e0f2fe"
  c_bubble_ai = "#f8fafc"
  c_text_color = "#1e3a8a"
else:  # Yeşil-Mavi
  c_bg_gradient = "linear-gradient(135deg, #38ef7d, #11998e)"
  c_border = "#0ea5e9"
  c_accent = "#0284c7"
  c_bubble_user = "#e0f2fe"
  c_bubble_ai = "#f0fdf4"
  c_text_color = "#0369a1"

# --- 5. STİLLER VE ARAYÜZ ---
st.markdown(
    f"""
    <style>
    .main-header {{
        background: {c_bg_gradient};
        padding: 22px;
        border-radius: 16px;
        color: white;
        text-align: center;
        font-weight: 800;
        font-size: 28px;
        margin-bottom: 25px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.25);
        letter-spacing: 0.5px;
    }}
    .card-box {{
        padding: 24px;
        border-radius: 16px;
        color: white;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        margin-bottom: 8px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        transition: transform 0.3s ease;
    }}
    .card-box:hover {{
        transform: translateY(-4px);
    }}
    .stButton>button {{
        background: {c_bg_gradient};
        color: white;
        border-radius: 12px;
        font-weight: bold;
        border: none;
        padding: 12px 24px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: 0.3s;
    }}
    .stButton>button:hover {{
        opacity: 0.92;
        transform: scale(1.02);
    }}
    </style>
    <div class="main-header">🎒 MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi & AdenMind Koçluk (Murat KANDIRMAZ)</div>
""",
    unsafe_allow_html=True,
)


# --- 6. KUSURSUZ DİNAMİK GEOMETRİ VE ŞEKİL MOTORU ---
def render_question_visual(gorsel_tipi, param):
  if not gorsel_tipi or gorsel_tipi == "yok":
    return

  param_str = clean_math_text(str(param)).strip()

  if gorsel_tipi == "ucgen":
    p_upper = param_str.upper()
    match_letters = re.search(r"([A-Z]{3})", p_upper)
    k1, k2, k3 = (
        list(match_letters.group(1)) if match_letters else ["A", "B", "C"]
    )

    deg_matches = re.findall(r"([A-Z])\s*:\s*(\d+°)", param_str)
    deg_dict = {m[0].upper(): m[1] for m in deg_matches}

    val1 = deg_dict.get(k1, "50°")
    val2 = deg_dict.get(k2, "60°")

    Ax, Ay = 140, 35
    Bx, By = 35, 150
    Cx, Cy = 245, 150

    svg_html = f"""
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="280" height="190" viewBox="0 0 280 190" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 18px; border: 1.5px solid rgba(56, 189, 248, 0.4); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);">
                <defs>
                    <linearGradient id="triGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="rgba(56, 189, 248, 0.4)" />
                        <stop offset="100%" stop-color="rgba(99, 102, 241, 0.1)" />
                    </linearGradient>
                </defs>
                <polygon points="{Ax},{Ay} {Bx},{By} {Cx},{Cy}" fill="url(#triGrad)" stroke="#38bdf8" stroke-width="4" stroke-linejoin="round"/>
                
                <text x="{Ax}" y="{Ay - 10}" fill="#38bdf8" font-size="15" font-weight="bold" text-anchor="middle">{k1}</text>
                <text x="{Bx - 12}" y="{By + 15}" fill="#38bdf8" font-size="15" font-weight="bold" text-anchor="middle">{k2}</text>
                <text x="{Cx + 12}" y="{By + 15}" fill="#38bdf8" font-size="15" font-weight="bold" text-anchor="middle">{k3}</text>
                
                <path d="M 126 58 Q 140 73 154 58" fill="none" stroke="#facc15" stroke-width="3" stroke-linecap="round"/>
                <text x="140" y="92" fill="#facc15" font-size="12" font-weight="bold" text-anchor="middle">{val1}</text>

                <path d="M 52 135 Q 68 142 62 124" fill="none" stroke="#facc15" stroke-width="3" stroke-linecap="round"/>
                <text x="75" y="128" fill="#facc15" font-size="12" font-weight="bold" text-anchor="middle">{val2}</text>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=205)

  elif gorsel_tipi in ["dortgen", "dikdortgen", "kare", "paralelkenar"]:
    p_upper = param_str.upper()
    match_letters = re.search(r"([A-Z]{4})", p_upper)
    d_letters = (
        list(match_letters.group(1)) if match_letters else ["A", "B", "C", "D"]
    )

    deg_matches = re.findall(r"([A-Z])\s*:\s*(\d+°|[\d\.]+cm)", param_str)
    deg_dict = {m[0].upper(): m[1] for m in deg_matches}
    lbl1 = deg_dict.get(d_letters[0], "90°")

    svg_html = f"""
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="280" height="190" viewBox="0 0 280 190" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 18px; border: 1.5px solid rgba(56, 189, 248, 0.4); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);">
                <rect x="50" y="45" width="180" height="100" fill="rgba(56, 189, 248, 0.1)" stroke="#38bdf8" stroke-width="4" rx="6"/>
                
                <text x="40" y="40" fill="#38bdf8" font-size="15" font-weight="bold" text-anchor="middle">{d_letters[0]}</text>
                <text x="245" y="40" fill="#38bdf8" font-size="15" font-weight="bold" text-anchor="middle">{d_letters[1]}</text>
                <text x="245" y="162" fill="#38bdf8" font-size="15" font-weight="bold" text-anchor="middle">{d_letters[2]}</text>
                <text x="40" y="162" fill="#38bdf8" font-size="15" font-weight="bold" text-anchor="middle">{d_letters[3]}</text>
                
                <rect x="105" y="84" width="70" height="24" fill="#0f172a" rx="6" stroke="#facc15" stroke-width="1.5"/>
                <text x="140" y="101" fill="#facc15" font-size="13" font-weight="bold" text-anchor="middle">{lbl1}</text>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=205)

  elif gorsel_tipi == "cember":
    val = "12 cm"
    try:
      num_match = re.search(r"(\d+)\s*(cm|m)?", param_str, re.IGNORECASE)
      if num_match:
        val = num_match.group(0)
    except Exception:
      pass

    svg_html = f"""
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="280" height="185" viewBox="0 0 280 185" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 18px; border: 1.5px solid rgba(56, 189, 248, 0.4); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5);">
                <circle cx="140" cy="90" r="60" fill="none" stroke="#38bdf8" stroke-width="4"/>
                <circle cx="140" cy="90" r="4" fill="#facc15"/>
                <text x="148" y="85" fill="#facc15" font-size="13" font-weight="bold">O</text>
                <line x1="80" y1="90" x2="200" y2="90" stroke="#f43f5e" stroke-width="2.5" stroke-dasharray="5,3"/>
                <rect x="105" y="75" width="70" height="22" fill="#0f172a" rx="5" stroke="#f43f5e" stroke-width="1.5"/>
                <text x="140" y="91" fill="#f43f5e" font-size="12" font-weight="bold" text-anchor="middle">{val}</text>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=200)

  elif gorsel_tipi == "ay_evresi":
    svg_html = f"""
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="280" height="180" viewBox="0 0 280 180" style="background: linear-gradient(135deg, #020617, #0b1329); border-radius: 18px; border: 1.5px solid #38bdf8; box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6);">
                <circle cx="140" cy="80" r="50" fill="#f1f5f9"/>
                <path d="M 140 30 A 50 50 0 0 0 140 130 Z" fill="rgba(10, 15, 30, 0.94)"/>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=195)

  elif gorsel_tipi == "gunes":
    svg_html = """
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="280" height="180" viewBox="0 0 280 180" style="background: linear-gradient(135deg, #090314, #1c0502); border-radius: 18px; border: 1.5px solid #f59e0b; box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6);">
                <circle cx="140" cy="80" r="52" fill="#f59e0b"/>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=195)

  elif gorsel_tipi == "dunya":
    svg_html = """
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="280" height="180" viewBox="0 0 280 180" style="background: linear-gradient(135deg, #020617, #0f172a); border-radius: 18px; border: 1.5px solid #38bdf8; box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6);">
                <circle cx="140" cy="80" r="48" fill="#0284c7"/>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=195)

  elif gorsel_tipi == "dinamometre":
    newton = "5 N"
    try:
      match_n = re.search(r"(\d+)\s*N", param_str, re.IGNORECASE)
      if match_n:
        newton = match_n.group(0)
    except Exception:
      pass
    svg_html = f"""
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="180" height="200" viewBox="0 0 180 200" style="background:#0f172a; border-radius:16px; border: 2px solid #38bdf8;">
                <rect x="55" y="35" width="70" height="145" fill="rgba(56, 189, 248, 0.12)" stroke="#38bdf8" stroke-width="3" rx="8"/>
                <text x="90" y="100" fill="#ffffff" font-size="14" font-weight="bold" text-anchor="middle">{newton}</text>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=215)


# --- 7. SOL MENÜ VE ADENMİND YAPAY ZEKA ROBOTU ---
with st.sidebar:
  st.subheader("🦊 AdenMind Tema Tercihi")
  selected_theme = st.radio(
      "Koçunun Renk Dünyasını Seç:",
      ["Mavi-Beyaz", "Sarı-Kırmızı", "Pembe", "Yeşil-Mavi"],
      index=[
          "Mavi-Beyaz",
          "Sarı-Kırmızı",
          "Pembe",
          "Yeşil-Mavi",
      ].index(st.session_state["coach_theme"])
      if st.session_state["coach_theme"]
      in ["Mavi-Beyaz", "Sarı-Kırmızı", "Pembe", "Yeşil-Mavi"]
      else 0,
  )
  if selected_theme != st.session_state["coach_theme"]:
    st.session_state["coach_theme"] = selected_theme
    st.rerun()

  st.markdown("---")
  if st.button("🏠 Ana Sayfaya Dön", key="home_btn", use_container_width=True):
    st.session_state["selected_subject"] = None
    st.session_state["selected_unit"] = None
    st.session_state["selected_game"] = None
    st.session_state["game_started"] = False
    st.rerun()

  st.markdown("---")
  st.markdown(
      f"""
        <div style="background: {c_bg_gradient}; padding: 10px; border-radius: 10px; color: white; display: flex; align-items: center; gap: 8px; font-weight: bold; font-size: 13px; margin-bottom: 10px;">
            <span style="font-size: 18px;">🦊</span>
            <span>AdenMind (Canlı Asistan)</span>
        </div>
    """,
      unsafe_allow_html=True,
  )

  sidebar_chat_box = st.container(height=320)
  with sidebar_chat_box:
    for msg in st.session_state["coach_messages"]:
      if msg["role"] == "assistant":
        st.markdown(
            f"""
                <div style="display: flex; align-items: flex-start; gap: 4px; margin-bottom: 6px;">
                    <div style="font-size: 14px;">🦊</div>
                    <div style="background-color: {c_bubble_ai}; padding: 6px 8px; border-radius: 8px; color: {c_text_color}; font-size: 11px;">
                        {msg['content']}
                    </div>
                </div>
                """,
            unsafe_allow_html=True,
        )
      else:
        st.markdown(
            f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 6px;">
                    <div style="background-color: {c_bubble_user}; padding: 6px 8px; border-radius: 8px; color: #1e293b; font-size: 11px;">
                        {msg['content']}
                    </div>
                </div>
                """,
            unsafe_allow_html=True,
        )

  with st.form("sidebar_chat_form", clear_on_submit=True):
    user_msg = st.text_input(
        "Asistana sor...", label_visibility="collapsed", key="s_msg"
    )
    submitted = st.form_submit_button("Gönder", use_container_width=True)

    if submitted and user_msg:
      st.session_state["coach_messages"].append(
          {"role": "user", "content": user_msg}
      )
      curr_s = st.session_state.get("selected_subject", "Genel")
      curr_u = st.session_state.get("selected_unit", "Genel Konu")
      prompt = (
          f"Sen 5. sınıf MEB müfredatı odaklı, sevimli ve bilgili akıllı koçsun."
          f" Adın AdenMind. Öğrencinin dersi: {curr_s}, ünite: {curr_u}."
          f" Öğrencinin sorusu: {user_msg}. Kısa ve sevimli rehberlik yap."
      )
      response = ai_generate_content(prompt)
      if response:
        st.session_state["coach_messages"].append(
            {"role": "assistant", "content": response}
        )
      else:
        st.session_state["coach_messages"].append(
            {
                "role": "assistant",
                "content": "Yanıt oluşturulamadı, tekrar dene!",
            }
        )
      st.rerun()


# --- AŞAMA 1: DERS SEÇİMİ ---
if st.session_state["selected_subject"] is None:
  st.markdown(
      "### 🌟 Lütfen Çalışmak İstediğiniz MEB Dersine Doğrudan Tıklayın"
  )
  subjects = list(MEB_CURRICULUM.keys())
  cols = st.columns(3)
  for i, subj in enumerate(subjects):
    col_idx = i % 3
    data = MEB_CURRICULUM[subj]
    with cols[col_idx]:
      st.markdown(
          f"""
            <div class="card-box" style="background: {data['renk']}; margin-bottom: 8px;">
                <div style="font-size: 38px;">{data['ikon']}</div>
                <div style="margin-top: 5px; font-size: 19px;">{subj}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(
          f"🚀 {subj} Dersine Gir",
          key=f"sub_{subj}",
          use_container_width=True,
      ):
        st.session_state["selected_subject"] = subj
        st.session_state["game_started"] = False
        st.rerun()

# --- AŞAMA 2: ÜNİTE SEÇİMİ ---
elif (
    st.session_state["selected_subject"] is not None
    and st.session_state["selected_unit"] is None
):
  curr_subj = st.session_state["selected_subject"]
  curr_data = MEB_CURRICULUM[curr_subj]

  st.markdown(
      f"### {curr_data['ikon']} {curr_subj} — Ünite / Konu Seçim Ekranı"
  )
  st.write("Çalışmak istediğiniz alt üniteye doğrudan tıklayın:")

  if st.button("⬅️ Ders Seçimine Geri Dön", key="back_subj"):
    st.session_state["selected_subject"] = None
    st.session_state["game_started"] = False
    st.rerun()

  st.markdown("---")

  unit_cols = st.columns(2)
  for idx, unit_name in enumerate(curr_data["uniteler"]):
    u_col = unit_cols[idx % 2]
    with u_col:
      st.markdown(
          f"""
            <div class="card-box" style="background: {curr_data['renk']}; opacity: 0.95; margin-bottom: 8px;">
                <div style="font-size: 18px;">📖 {unit_name}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(
          f"Seç: {unit_name[:25]}...",
          key=f"unit_{idx}",
          use_container_width=True,
      ):
        st.session_state["selected_unit"] = unit_name
        st.session_state["game_started"] = False
        st.rerun()

# --- AŞAMA 3: OYUN / ETKİNLİK MODÜLÜ SEÇİMİ ---
elif (
    st.session_state["selected_subject"] is not None
    and st.session_state["selected_unit"] is not None
    and st.session_state["selected_game"] is None
):
  curr_subj = st.session_state["selected_subject"]
  curr_unit = st.session_state["selected_unit"]
  curr_data = MEB_CURRICULUM[curr_subj]

  st.markdown(
      f"""
        <div style="background: {curr_data['renk']}; padding: 16px; border-radius: 12px; color: white; margin-bottom: 20px; font-weight: bold; font-size: 18px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
            <b>Seçilen Ders:</b> {curr_subj} &nbsp;|&nbsp; <b>Ünite:</b> {curr_unit}
        </div>
    """,
      unsafe_allow_html=True,
  )

  if st.button("↩️ Ünite Değiştir", key="back_unit"):
    st.session_state["selected_unit"] = None
    st.session_state["game_started"] = False
    st.rerun()

  st.markdown(
      "### 🎮 Oyun, Soru Kartları ve Eğitsel Etkinlik Modüllerini Seçin"
  )

  games = [
      {
          "id": "balon",
          "isim": "🎈 Balon Patlatmaca",
          "renk": "linear-gradient(135deg, #ff416c, #ff4b2b)",
      },
      {
          "id": "sinav10",
          "isim": "🧠 5 Soruluk MEB Kazanım Oyunu (Tek Soru Modu)",
          "renk": "linear-gradient(135deg, #2193b0, #6dd5ed)",
      },
      {
          "id": "dogruyanlis",
          "isim": "✅ Doğru / Yanlış Meydan Okuması (Tek Soru Modu)",
          "renk": "linear-gradient(135deg, #38ef7d, #11998e)",
      },
      {
          "id": "bosluk",
          "isim": "📝 Boşluk Doldurma Yarışması (Tek Soru Modu)",
          "renk": "linear-gradient(135deg, #f2994a, #f2c94c)",
      },
      {
          "id": "kartlar",
          "isim": "🃏 Soru Kartları (Flashcards)",
          "renk": "linear-gradient(135deg, #834d9b, #d04ed6)",
      },
      {
          "id": "oynayarak",
          "isim": "🎯 Oynayarak Öğren",
          "renk": "linear-gradient(135deg, #0284c7, #0369a1)",
      },
      {
          "id": "etkinlik",
          "isim": "📚 Etkinliklerle Öğren",
          "renk": "linear-gradient(135deg, #10b981, #047857)",
      },
      {
          "id": "kelime",
          "isim": "🔤 Kelime Avı Bulmacası",
          "renk": "linear-gradient(135deg, #f59e0b, #d97706)",
      },
      {
          "id": "acik",
          "isim": "✍️ Klasik Yazılı Simülatörü",
          "renk": "linear-gradient(135deg, #6366f1, #4338ca)",
      },
  ]

  g_cols = st.columns(3)
  for g_idx, g_item in enumerate(games):
    with g_cols[g_idx % 3]:
      st.markdown(
          f"""
            <div class="card-box" style="background: {g_item['renk']}; margin-bottom: 8px;">
                <div style="font-size: 18px;">{g_item['isim']}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(
          f"Seç: {g_item['isim'].split(' ')[1]}",
          key=f"game_{g_item['id']}",
          use_container_width=True,
      ):
        st.session_state["selected_game"] = g_item["id"]
        st.session_state["game_started"] = False
        st.rerun()

# --- AŞAMA 4: OYUN VE MODÜLLERİN ÇALIŞTIRILMASI ---
else:
  curr_subj = st.session_state["selected_subject"]
  curr_unit = st.session_state["selected_unit"]
  curr_game = st.session_state["selected_game"]

  if st.button("⬅️ Oyun / Mod Seçimine Geri Dön", key="back_game"):
    st.session_state["selected_game"] = None
    st.session_state["game_started"] = False
    st.rerun()

  st.markdown("---")

  visual_prompt_instruction = """
  (KUSURSUZ GÖRSEL VE METİN SENKRONİZASYONU TALİMATI):
  1. Soruda geçen tüm harfler ve açı/uzunluk değerleri görsel parametresine birebir aktarılacaktır.
  2. Asla 'circ' kelimesi kullanılmayacak, yalnızca standart derece işareti (°) kullanılacaktır.
  3. Gorsel_parametre alanı şu formatta doldurulmalıdır: 
     - Üçgenler için: "ABC, A:50°, B:60°"
     - Dörtgenler için: "ABCD, A:90°, B:8cm"
     - Çemberler için: "O, 12cm"
  """

  # 1. BALON PATLATMACA
  if curr_game == "balon":
    st.subheader(f"🎈 {curr_subj} — Klasik Balon Patlatmaca Oyunu")
    if (
        "balloon_5_questions" not in st.session_state
        or st.session_state.get("b_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["balloon_5_questions"] = None
      st.session_state["b_unit_key"] = (curr_subj, curr_unit)
      st.session_state["game_started"] = False

    if st.button("🚀 Yepyeni Balon Sorularını Üret", key="gen_5_balloons"):
      with st.spinner("Yapay zeka soruları hazırlıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                TAM 5 ADET benzersiz çoktan seçmeli soru üret.
                {visual_prompt_instruction}
                JSON formatında geçerli bir liste olarak ver:
                [
                  {{
                    "soru": "Soru metni",
                    "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
                    "dogru_cevap": "A",
                    "aciklama": "Açıklama",
                    "gorsel_tipi": "ucgen", 
                    "gorsel_parametre": "ABC, A:50°, B:60°"
                  }}
                ]
                """
        res = ai_generate_content(prompt)
        parsed = safe_parse_json(res)
        if parsed and isinstance(parsed, list):
          st.session_state["balloon_5_questions"] = parsed
          st.session_state["game_started"] = False
          st.rerun()
        else:
          st.error(
              "Sorular yüklenirken bir veri hatası oluştu. Lütfen tekrar"
              " deneyin."
          )

    if st.session_state["balloon_5_questions"]:
      if not st.session_state["game_started"]:
        st.success("✅ Sorular Hazır! Oyunu başlatmak için tıklayın.")
        if st.button(
            "✨ OYUNU BAŞLAT 🎮",
            key="start_balloon_fullscreen",
            use_container_width=True,
        ):
          st.session_state["game_started"] = True
          st.rerun()
      else:
        questions_json = json.dumps(
            st.session_state["balloon_5_questions"], ensure_ascii=False
        )
        html_balloon_game = (
            """
            <!DOCTYPE html>
            <html lang="tr">
            <head><meta charset="UTF-8"><style>
                body { background: #0f172a; color: white; font-family: sans-serif; text-align: center; margin: 0; padding: 10px; }
                #game-container { position: relative; width: 100%; height: 520px; background: #1e293b; border-radius: 16px; overflow: hidden; border: 3px solid #6366f1; }
                .header-bar { display: flex; justify-content: space-between; padding: 12px 20px; background: rgba(0,0,0,0.5); font-weight: bold; }
                .question-box { font-size: 18px; font-weight: bold; padding: 12px; background: rgba(255,255,255,0.08); margin: 10px; border-radius: 10px; text-align: left; }
                .balloon { position: absolute; width: 100px; height: 120px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 13px; text-align: center; cursor: pointer; animation: floatUp 7s linear infinite; padding: 8px; }
                @keyframes floatUp { 0% { bottom: -130px; } 100% { bottom: 500px; } }
            </style></head>
            <body>
                <div class="header-bar"><span id="q-counter">Soru: 1 / 5</span><span id="timer" style="color: #f43f5e;">Süre: 45 sn</span><span id="score" style="color: #10b981;">Puan: 0</span></div>
                <div id="game-container">
                    <div class="question-box" id="question-text">Yükleniyor...</div>
                    <div id="balloons-area" style="position:relative; width:100%; height:300px;"></div>
                </div>
                <script>
                    const questions = """
            + questions_json
            + """;
                    let currentIdx = 0, score = 0, timeLeft = 45, timerInterval = null, active = true;
                    function loadQ() {
                        if(currentIdx >= questions.length) {
                            document.getElementById('game-container').innerHTML = `<h2 style="padding:100px;">🏆 Oyun Tamamlandı! Puan: ${score}</h2>`;
                            return;
                        }
                        active = true; timeLeft = 45;
                        document.getElementById('q-counter').innerText = "Soru: " + (currentIdx + 1) + " / 5";
                        let q = questions[currentIdx];
                        document.getElementById('question-text').innerText = q.soru;
                        let area = document.getElementById('balloons-area'); area.innerHTML = '';
                        let cols = ['#ff416c', '#2193b0', '#11998e', '#f2994a'];
                        q.secenekler.forEach((opt, idx) => {
                            let b = document.createElement('div');
                            b.className = 'balloon';
                            b.style.background = cols[idx % cols.length];
                            b.style.left = (12 + idx * 21) + '%';
                            b.style.animationDelay = (idx * 0.3) + 's';
                            b.innerText = opt;
                            b.onclick = () => {
                                if(!active) return; active = false; clearInterval(timerInterval);
                                if(opt.charAt(0).toUpperCase() === q.dogru_cevap.charAt(0).toUpperCase()) {
                                    score += 20; document.getElementById('score').innerText = "Puan: " + score;
                                }
                                currentIdx++; loadQ();
                            };
                            area.appendChild(b);
                        });
                    }
                    loadQ();
                </script>
            </body></html>
            """
        )
        st.components.v1.html(html_balloon_game, height=560)

  # 2. 5 SORULUK MEB KAZANIM OYUNU
  elif curr_game == "sinav10":
    st.subheader(
        f"🧠 {curr_subj} — 5 Soruluk MEB Kazanım Yarışması (Tek Soru Modu)"
    )

    if (
        "kazanim_list" not in st.session_state
        or st.session_state.get("k_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["kazanim_list"] = None
      st.session_state["k_unit_key"] = (curr_subj, curr_unit)
      st.session_state["kazanim_idx"] = 0
      st.session_state["kazanim_score"] = 0
      st.session_state["kazanim_answers"] = {}

    if st.button("🚀 Yepyeni Kazanım Sorularını Üret", key="gen_kazanim"):
      with st.spinner("Sorular oluşturuluyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                TAM 5 ADET çoktan seçmeli soru üret. 
                {visual_prompt_instruction}
                JSON liste formatında şu yapıda ver:
                [
                  {{
                    "soru": "...", 
                    "secenekler": ["A)...", "B)...", "C)...", "D)..."], 
                    "dogru_cevap": "A", 
                    "aciklama": "...",
                    "gorsel_tipi": "ucgen",
                    "gorsel_parametre": "ABC, A:50°, B:60°"
                  }}
                ]
                """
        res = ai_generate_content(prompt)
        parsed = safe_parse_json(res)
        if parsed and isinstance(parsed, list):
          st.session_state["kazanim_list"] = parsed
          st.session_state["kazanim_idx"] = 0
          st.session_state["kazanim_score"] = 0
          st.session_state["kazanim_answers"] = {}
          st.rerun()
        else:
          st.error("Sorular üretilemedi. Lütfen tekrar deneyin.")

    if st.session_state["kazanim_list"]:
      k_list = st.session_state["kazanim_list"]
      k_idx = st.session_state["kazanim_idx"]

      if k_idx < len(k_list):
        q = k_list[k_idx]
        st.markdown(
            f"""
            <div style="background: rgba(255,255,255,0.06); padding: 22px; border-radius: 16px; border: 2px solid {c_border}; margin-bottom: 20px;">
                <div style="font-weight: bold; margin-bottom: 8px; color: #38bdf8;">Soru {k_idx + 1} / {len(k_list)}</div>
                <div style="font-size: 20px; font-weight: bold;">{q['soru']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "gorsel_tipi" in q and q["gorsel_tipi"] != "yok":
          render_question_visual(
              q.get("gorsel_tipi"), q.get("gorsel_parametre", "")
          )

        selected_option = st.radio(
            "Cevabınızı Seçin:",
            q["secenekler"],
            index=None,
            key=f"kazanim_radio_{k_idx}",
        )
        st.markdown("<br>", unsafe_allow_html=True)

        col_prev, col_pass, col_next = st.columns(3)
        with col_prev:
          if k_idx > 0 and st.button(
              "⬅️ Önceki Soru", use_container_width=True
          ):
            st.session_state["kazanim_idx"] -= 1
            st.rerun()
        with col_pass:
          if st.button("⏭️ Pas Geç", use_container_width=True):
            st.session_state["kazanim_idx"] += 1
            st.rerun()
        with col_next:
          if st.button(
              (
                  "Sonraki Soru ➡️"
                  if k_idx < len(k_list) - 1
                  else "Sınavı Tamamla 🏆"
              ),
              use_container_width=True,
          ):
            if selected_option:
              st.session_state["kazanim_answers"][k_idx] = selected_option
              chosen_letter = selected_option[0].upper()
              correct_letter = q["dogru_cevap"].upper()
              if chosen_letter == correct_letter:
                st.session_state["kazanim_score"] += 20
            st.session_state["kazanim_idx"] += 1
            st.rerun()
      else:
        st.markdown(
            f"""
            <div style="background: rgba(255,255,255,0.06); padding: 40px; border-radius: 16px; text-align: center;">
                <h2>🏆 Kazanım Sınavı Tamamlandı!</h2>
                <p style="font-size: 26px;">Toplam Puanınız: <span style="color: #10b981; font-size: 40px;">{st.session_state['kazanim_score']} / 100</span></p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Tekrar Sınav Ol", use_container_width=True):
          st.session_state["kazanim_list"] = None
          st.session_state["kazanim_idx"] = 0
          st.session_state["kazanim_score"] = 0
          st.session_state["kazanim_answers"] = {}
          st.rerun()

  # 3. DOĞRU / YANLIŞ MEYDAN OKUMASI
  elif curr_game == "dogruyanlis":
    st.subheader(
        f"✅ {curr_subj} — Doğru / Yanlış Meydan Okuması (Tek Soru Modu)"
    )
    if (
        "dy_questions" not in st.session_state
        or st.session_state.get("dy_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["dy_questions"] = None
      st.session_state["dy_unit_key"] = (curr_subj, curr_unit)
      st.session_state["dy_score"] = 0
      st.session_state["dy_current_q"] = 0
      st.session_state["dy_feedback"] = ""

    if st.button("🚀 Yepyeni D/Y Yarışmasını Başlat", key="gen_dy"):
      with st.spinner("Önermeler hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                TAM 5 ADET Doğru veya Yanlış önermesi üret. 
                {visual_prompt_instruction}
                JSON liste formatında ver:
                [
                  {{"ifade": "...", "cevap": "D", "aciklama": "...", "gorsel_tipi": "gunes", "gorsel_parametre": "gunes"}}
                ]
                """
        res = ai_generate_content(prompt)
        parsed = safe_parse_json(res)
        if parsed and isinstance(parsed, list):
          st.session_state["dy_questions"] = parsed
          st.session_state["dy_score"] = 0
          st.session_state["dy_current_q"] = 0
          st.session_state["dy_feedback"] = ""
          st.rerun()
        else:
          st.error("Sorular üretilemedi.")

    if st.session_state["dy_questions"]:
      questions = st.session_state["dy_questions"]
      q_idx = st.session_state["dy_current_q"]

      if q_idx < len(questions):
        q_item = questions[q_idx]
        st.markdown(
            f"""
            <div style="background: rgba(255,255,255,0.06); padding: 24px; border-radius: 16px; border: 2px solid {c_border}; margin-bottom: 20px;">
                <div style="font-weight: bold; margin-bottom: 10px; color: #38bdf8;">Soru: {q_idx + 1} / {len(questions)}</div>
                <div style="font-size: 20px; font-weight: bold;">{q_item['ifade']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if "gorsel_tipi" in q_item and q_item["gorsel_tipi"] != "yok":
          render_question_visual(
              q_item.get("gorsel_tipi"), q_item.get("gorsel_parametre", "")
          )

        if st.session_state["dy_feedback"]:
          st.markdown(st.session_state["dy_feedback"], unsafe_allow_html=True)
          st.markdown("<br>", unsafe_allow_html=True)
          if st.button("➡️ Sonraki Soruya Geç", use_container_width=True):
            st.session_state["dy_feedback"] = ""
            st.session_state["dy_current_q"] += 1
            st.rerun()
        else:
          col_d, col_y, col_pass = st.columns(3)
          with col_d:
            if st.button("✅ DOĞRU (D)", use_container_width=True):
              if q_item["cevap"].upper() == "D":
                st.session_state["dy_score"] += 20
                st.session_state["dy_feedback"] = (
                    f"🎉 **Doğru Seçim!**<br><span"
                    f" style='color:#10b981;'>{q_item['aciklama']}</span>"
                )
              else:
                st.session_state["dy_feedback"] = (
                    f"❌ **Yanlış Seçim!** Doğru cevap Yanlış (Y) idi.<br><span"
                    f" style='color:#f43f5e;'>{q_item['aciklama']}</span>"
                )
              st.rerun()
          with col_y:
            if st.button("❌ YANLIŞ (Y)", use_container_width=True):
              if q_item["cevap"].upper() == "Y":
                st.session_state["dy_score"] += 20
                st.session_state["dy_feedback"] = (
                    f"🎉 **Doğru Seçim!**<br><span"
                    f" style='color:#10b981;'>{q_item['aciklama']}</span>"
                )
              else:
                st.session_state["dy_feedback"] = (
                    f"❌ **Yanlış Seçim!** Doğru cevap Doğru (D) idi.<br><span"
                    f" style='color:#f43f5e;'>{q_item['aciklama']}</span>"
                )
              st.rerun()
          with col_pass:
            if st.button("⏭️ Pas Geç", use_container_width=True):
              st.session_state["dy_current_q"] += 1
              st.rerun()
      else:
        st.markdown(
            f"<h2>🏆 Yarışma Tamamlandı! Puan: {st.session_state['dy_score']} /"
            " 100</h2>",
            unsafe_allow_html=True,
        )
        if st.button("🔄 Tekrar Oyna", use_container_width=True):
          st.session_state["dy_questions"] = None
          st.rerun()

  # 4. BOŞLUK DOLDURMA YARIŞMASI
  elif curr_game == "bosluk":
    st.subheader(
        f"📝 {curr_subj} — Boşluk Doldurma Yarışması (Tek Soru Modu)"
    )
    if (
        "fill_blanks" not in st.session_state
        or st.session_state.get("f_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["fill_blanks"] = None
      st.session_state["f_unit_key"] = (curr_subj, curr_unit)
      st.session_state["fill_idx"] = 0
      st.session_state["fill_score"] = 0
      st.session_state["fill_feedback"] = ""

    if st.button("✨ Yepyeni Boşluk Doldurma Soruları Üret", key="gen_fill"):
      with st.spinner("Sorular hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                Cümle içinde boşluk bırakılmış 5 adet soru üret. 
                {visual_prompt_instruction}
                JSON liste formatında ver:
                [
                  {{"cumle": "...", "dogru_kelime": "...", "secenekler": ["...", "...", "...", "..."], "gorsel_tipi": "dunya", "gorsel_parametre": "dunya"}}
                ]
                """
        res = ai_generate_content(prompt)
        parsed = safe_parse_json(res)
        if parsed and isinstance(parsed, list):
          st.session_state["fill_blanks"] = parsed
          st.session_state["fill_idx"] = 0
          st.session_state["fill_score"] = 0
          st.session_state["fill_feedback"] = ""
          st.rerun()
        else:
          st.error("Sorular üretilemedi.")

    if st.session_state["fill_blanks"]:
      fdata = st.session_state["fill_blanks"]
      f_idx = st.session_state["fill_idx"]

      if f_idx < len(fdata):
        fq = fdata[f_idx]
        st.markdown(
            f"""
            <div style="background: rgba(255,255,255,0.06); padding: 22px; border-radius: 16px; border: 2px solid {c_border}; margin-bottom: 20px;">
                <div style="font-weight: bold; margin-bottom: 8px; color: #38bdf8;">Soru {f_idx + 1} / {len(fdata)}</div>
                <div style="font-size: 20px; font-weight: bold;">{fq['cumle']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "gorsel_tipi" in fq and fq["gorsel_tipi"] != "yok":
          render_question_visual(
              fq.get("gorsel_tipi"), fq.get("gorsel_parametre", "")
          )

        if st.session_state["fill_feedback"]:
          st.markdown(st.session_state["fill_feedback"], unsafe_allow_html=True)
          st.markdown("<br>", unsafe_allow_html=True)
          if st.button("➡️ Sonraki Soruya Geç", use_container_width=True):
            st.session_state["fill_feedback"] = ""
            st.session_state["fill_idx"] += 1
            st.rerun()
        else:
          st.markdown("**Boşluğa gelecek kelimeyi butonlara tıklayarak seçin:**")
          opt_cols = st.columns(2)
          for opt_i, opt_val in enumerate(fq["secenekler"]):
            with opt_cols[opt_i % 2]:
              if st.button(
                  f"📌 {opt_val}",
                  key=f"fill_btn_{f_idx}_{opt_i}",
                  use_container_width=True,
              ):
                if opt_val == fq["dogru_kelime"]:
                  st.session_state["fill_score"] += 20
                  st.session_state["fill_feedback"] = (
                      f"🎉 **Tebrikler, Doğru Cevap!**<br><span"
                      f" style='color:#10b981;'>Boşluğa gelebilecek en doğru"
                      f" kelime: <b>{opt_val}</b></span>"
                  )
                else:
                  st.session_state["fill_feedback"] = (
                      f"❌ **Yanlış Seçenek!**<br><span"
                      f" style='color:#f43f5e;'>Doğru kelime:"
                      f" <b>{fq['dogru_kelime']}</b> olmalıydı.</span>"
                  )
                st.rerun()

          st.markdown("<br>", unsafe_allow_html=True)
          if st.button("⏭️ Pas Geç", use_container_width=True):
            st.session_state["fill_idx"] += 1
            st.session_state["fill_feedback"] = ""
            st.rerun()
      else:
        st.markdown(
            f"""
            <div style="background: rgba(255,255,255,0.06); padding: 40px; border-radius: 16px; text-align: center;">
                <h2>🏆 Boşluk Doldurma Yarışması Tamamlandı!</h2>
                <p style="font-size: 26px;">Toplam Puanınız: <span style="color: #10b981; font-size: 40px;">{st.session_state['fill_score']} / 100</span></p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔄 Tekrar Yarış", use_container_width=True):
          st.session_state["fill_blanks"] = None
          st.session_state["fill_idx"] = 0
          st.session_state["fill_score"] = 0
          st.session_state["fill_feedback"] = ""
          st.rerun()

  # 5. SORU KARTLARI (FLASHCARDS)
  elif curr_game == "kartlar":
    st.subheader(f"🃏 {curr_subj} — Soru Kartları (Flashcards)")
    if (
        "flashcards" not in st.session_state
        or st.session_state.get("fc_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["flashcards"] = None
      st.session_state["fc_unit_key"] = (curr_subj, curr_unit)
      st.session_state["fc_idx"] = 0

    if st.button("✨ Yepyeni Soru Kartları Dağıt", key="gen_fc"):
      with st.spinner("Kartlar hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                5 adet flashcard üret. JSON liste formatında ver:
                [
                  {{"on_yuz": "...", "arka_yuz": "..."}}
                ]
                """
        res = ai_generate_content(prompt)
        parsed = safe_parse_json(res)
        if parsed and isinstance(parsed, list):
          st.session_state["flashcards"] = parsed
          st.session_state["fc_idx"] = 0
          st.rerun()
        else:
          st.error("Kartlar üretilemedi.")

    if st.session_state["flashcards"]:
      cards = st.session_state["flashcards"]
      f_idx = st.session_state["fc_idx"]
      if f_idx < len(cards):
        card = cards[f_idx]
        st.markdown(
            f"""
            <div style="background: {c_bg_gradient}; padding: 40px; border-radius: 20px; color: white; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.3); margin-bottom: 20px;">
                <div style="font-size: 14px; opacity: 0.8; margin-bottom: 10px;">Kart {f_idx+1} / {len(cards)}</div>
                <div style="font-size: 24px; font-weight: bold; margin-bottom: 20px;">❓ {card['on_yuz']}</div>
                <hr style="border-color: rgba(255,255,255,0.3);">
                <div style="font-size: 20px; margin-top: 20px;">💡 <b>Cevap / Açıklama:</b> {card['arka_yuz']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_prev, col_pass, col_next = st.columns(3)
        with col_prev:
          if f_idx > 0 and st.button(
              "⬅️ Önceki Kart", use_container_width=True
          ):
            st.session_state["fc_idx"] -= 1
            st.rerun()
        with col_pass:
          if st.button("⏭️ Pas Geç", use_container_width=True):
            st.session_state["fc_idx"] += 1
            st.rerun()
        with col_next:
          if f_idx < len(cards) - 1 and st.button(
              "Sonraki Kart ➡️", use_container_width=True
          ):
            st.session_state["fc_idx"] += 1
            st.rerun()
      else:
        st.success("Tüm kartları gözden geçirdiniz!")
        if st.button("🔄 Başa Dön", use_container_width=True):
          st.session_state["fc_idx"] = 0
          st.rerun()

  # 6. OYNAYARAK ÖĞREN
  elif curr_game == "oynayarak":
    st.subheader(f"🎯 {curr_subj} — Oynayarak Öğren Atölyesi")
    if (
        "interactive_quest" not in st.session_state
        or st.session_state.get("iq_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["interactive_quest"] = None
      st.session_state["iq_unit_key"] = (curr_subj, curr_unit)

    if st.button("🚀 Yepyeni İnteraktif Görev Başlat", key="gen_interactive_quest"):
      with st.spinner("Macera hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {curr_unit}.
                Gerçek hayattan esinlenen karar verme senaryosu ve çoktan seçmeli mini görev üret. 
                JSON formatında şu yapıda ver:
                {{
                  "senaryo": "...",
                  "gorev_sorusu": "...",
                  "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
                  "ipucu": "..."
                }}
                """
        res = ai_generate_content(prompt)
        parsed = safe_parse_json(res)
        if parsed and isinstance(parsed, dict):
          st.session_state["interactive_quest"] = parsed
          st.rerun()
        else:
          st.error("Görev üretilemedi.")

    if st.session_state["interactive_quest"]:
      iq = st.session_state["interactive_quest"]
      st.markdown(
          f"""
            <div style="background: rgba(255,255,255,0.06); padding: 20px; border-radius: 14px; border: 2px solid {c_border}; margin-bottom: 15px;">
                <h4 style="color: #38bdf8; margin-top:0;">📖 Görev Senaryosu</h4>
                <p style="font-size: 16px;">{iq.get('senaryo', '')}</p>
                <hr style="border-color: rgba(255,255,255,0.2);">
                <h4 style="color: #facc15;">🎯 Soru / Karar Noktası</h4>
                <p style="font-size: 18px; font-weight: bold;">{iq.get('gorev_sorusu', '')}</p>
            </div>
            """,
          unsafe_allow_html=True,
      )

      with st.form("interactive_choice_form"):
        user_choice = st.radio(
            "Cevabınızı Seçin:", iq.get("secenekler", []), index=None
        )
        submitted_choice = st.form_submit_button("Seçimi Gönder ve Değerlendir")

        if submitted_choice:
          if user_choice:
            eval_prompt = f"""
                        Ders: {curr_subj}, Ünite: {curr_unit}.
                        Görev Sorusu: {iq.get('gorev_sorusu')}
                        Öğrencinin Seçtiği Şık: {user_choice}
                        Bu seçimin doğru olup olmadığını değerlendir, nedenini sevimli bir dille açıkla.
                        """
            feedback = ai_generate_content(eval_prompt)
            st.success("Değerlendirme Tamamlandı! ✨")
            st.info(feedback)
          else:
            st.warning("Lütfen seçeneklerden birini işaretleyin!")

      if st.button("💡 AdenMind İpucu İste"):
        st.info(f"🦊 **AdenMind İpucu:** {iq.get('ipucu', '')}")

  # 7. ETKİNLİKLERLE ÖĞREN
  elif curr_game == "etkinlik":
    st.subheader(f"📚 {curr_subj} — Etkinliklerle Öğren Merkezi")
    st.info(
        "MEB müfredatına uyumlu günlük etkinlikler, deneyler ve pratik uygulama"
        " adımları."
    )
    if st.button("🚀 Yepyeni Etkinlik Önerisi Getir"):
      with st.spinner("Etkinlik hazırlanıyor..."):
        prompt = f"5. Sınıf {curr_subj} {curr_unit} için evde veya sınıfta yapılabilecek 3 adet yaratıcı öğrenme etkinliği öner."
        res = ai_generate_content(prompt)
        if res:
          st.markdown(res)

  # 8. KELİME AVI BULMACASI
  elif curr_game == "kelime":
    st.subheader(f"🔤 {curr_subj} — Kelime Avı Bulmacası")

    if (
        "puz_items" not in st.session_state
        or st.session_state.get("p_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["puz_items"] = None
      st.session_state["p_unit_key"] = (curr_subj, curr_unit)
      st.session_state["puz_idx"] = 0
      st.session_state["user_guess"] = []
      st.session_state["used_indices"] = []

    if st.button("🔍 Yepyeni Kelime Avını Başlat", key="gen_puz"):
      with st.spinner("Bulmaca kelimeleri hazırlanıyor..."):
        prompt = f"""
                5. Sınıf {curr_subj} {curr_unit} için 5 adet anahtar kelime ve tanım ipucu üret.
                JSON liste formatında ver:
                [
                  {{"kelime": "TERİM", "ipucu": "..."}}
                ]
                """
        res = ai_generate_content(prompt)
        parsed = safe_parse_json(res)
        if parsed and isinstance(parsed, list):
          st.session_state["puz_items"] = parsed
          st.session_state["puz_idx"] = 0
          st.session_state["user_guess"] = []
          st.session_state["used_indices"] = []
          keys_to_del = [
              k for k in st.session_state.keys() if k.startswith("pool_")
          ]
          for k in keys_to_del:
            del st.session_state[k]
          st.rerun()
        else:
          st.error("Bulmaca üretilemedi.")

    if st.session_state["puz_items"]:
      items = st.session_state["puz_items"]
      p_idx = st.session_state["puz_idx"]

      if p_idx < len(items):
        cur_item = items[p_idx]
        t_word = cur_item["kelime"].upper().strip()

        st.markdown(
            f"""
            <div style="background: rgba(255,255,255,0.06); padding: 18px; border-radius: 12px; margin-bottom: 15px;">
                <b>Bulmaca {p_idx + 1} / {len(items)}</b><br>
                <span style="font-size: 18px; color: #38bdf8;">💡 İpucu: {cur_item['ipucu']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        pool_key = f"pool_{p_idx}_{t_word}"
        if pool_key not in st.session_state:
          pool = list(t_word)
          extra_chars = [
              c for c in "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ" if c not in pool
          ]
          pool.extend(random.sample(extra_chars, min(3, len(extra_chars))))
          random.shuffle(pool)
          st.session_state[pool_key] = pool
          st.session_state["user_guess"] = []
          st.session_state["used_indices"] = []

        pool_chars = st.session_state[pool_key]
        user_g = st.session_state["user_guess"]
        used_idx = st.session_state["used_indices"]

        st.markdown(
            "**Oluşturduğunuz Kelime Kutuları:**", unsafe_allow_html=True
        )
        box_cols = st.columns(len(t_word))
        for i in range(len(t_word)):
          with box_cols[i]:
            char_val = user_g[i] if i < len(user_g) else "_"
            st.markdown(
                f"""
                <div style="background: #1e293b; border: 2px solid {c_border}; border-radius: 8px; padding: 12px; text-align: center; font-size: 22px; font-weight: bold; color: #facc15;">
                    {char_val}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            "**Seçebileceğiniz Karışık Harfler (Tıklayın):**",
            unsafe_allow_html=True,
        )

        char_cols = st.columns(len(pool_chars))
        for c_i, c_char in enumerate(pool_chars):
          with char_cols[c_i]:
            is_disabled = c_i in used_idx
            if not is_disabled:
              if st.button(c_char, key=f"char_btn_{p_idx}_{c_i}_{c_char}"):
                if len(st.session_state["user_guess"]) < len(t_word):
                  st.session_state["user_guess"].append(c_char)
                  st.session_state["used_indices"].append(c_i)
                  st.rerun()
            else:
              st.button(
                  "✔️", key=f"char_btn_used_{p_idx}_{c_i}", disabled=True
              )

        c_reset, c_backspace, c_pass, c_check = st.columns(4)
        with c_reset:
          if st.button("🔄 Sıfırla", use_container_width=True):
            st.session_state["user_guess"] = []
            st.session_state["used_indices"] = []
            st.rerun()
        with c_backspace:
          if st.button("↩️ Son Harfi Sil", use_container_width=True):
            if st.session_state["user_guess"] and st.session_state[
                "used_indices"
            ]:
              st.session_state["user_guess"].pop()
              st.session_state["used_indices"].pop()
              st.rerun()
        with c_pass:
          if st.button("⏭️ Pas Geç", use_container_width=True):
            st.session_state["puz_idx"] += 1
            st.session_state["user_guess"] = []
            st.session_state["used_indices"] = []
            st.rerun()
        with c_check:
          if st.button("✅ Kontrol Et", use_container_width=True):
            current_typed = "".join(st.session_state["user_guess"])
            if current_typed == t_word:
              st.success("🎉 Tebrikler, Doğru Kelime!")
              st.session_state["puz_idx"] += 1
              st.session_state["user_guess"] = []
              st.session_state["used_indices"] = []
              st.rerun()
            else:
              st.error(
                  "❌ Eksik veya yanlış harf kombinasyonu! 'Son Harfi Sil' veya"
                  " 'Sıfırla' ile düzeltebilirsiniz."
              )
      else:
        st.markdown(
            """
            <div style="background: rgba(255,255,255,0.06); padding: 30px; border-radius: 16px; text-align: center;">
                <h2>🏆 Tebrikler! Tüm Kelime Avı Bulmacalarını Tamamladınız!</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔄 Yeni Bulmaca Başlat", use_container_width=True):
          st.session_state["puz_items"] = None
          keys_to_del = [
              k for k in st.session_state.keys() if k.startswith("pool_")
          ]
          for k in keys_to_del:
            del st.session_state[k]
          st.rerun()

  # 9. KLASİK YAZILI SİMÜLATÖRÜ
  elif curr_game == "acik":
    st.subheader(f"✍️ {curr_subj} — Klasik Yazılı Simülatörü")
    if (
        "classic_exam" not in st.session_state
        or st.session_state.get("c_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["classic_exam"] = None
      st.session_state["c_unit_key"] = (curr_subj, curr_unit)

    if st.button("✨ Yepyeni Yazılı Sınavını Başlat", key="gen_classic"):
      with st.spinner("Yazılı soruları hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                TAM 5 ADET açık uçlu yazılı sorusu ve ideal cevapları JSON liste formatında ver:
                [
                  {{"soru": "...", "beklenen_cevap": "..."}}
                ]
                """
        res = ai_generate_content(prompt)
        parsed = safe_parse_json(res)
        if parsed and isinstance(parsed, list):
          st.session_state["classic_exam"] = parsed
          st.rerun()
        else:
          st.error("Yazılı soruları üretilemedi.")

    if st.session_state["classic_exam"]:
      exam_list = st.session_state["classic_exam"]
      with st.form("classic_form"):
        u_ans = {}
        for idx, cq in enumerate(exam_list):
          st.markdown(f"**Soru {idx+1}:** {cq['soru']}")
          u_ans[idx] = st.text_area(f"Cevabınız ({idx+1}):", key=f"ans_{idx}")
          st.markdown("---")
        if st.form_submit_button("Yazılı Kağıdını Puanlat"):
          for idx, cq in enumerate(exam_list):
            ans = u_ans.get(idx, "")
            if ans.strip():
              eval_res = ai_generate_content(
                  f"Soru: {cq['soru']}, İdeal: {cq['beklenen_cevap']}, Öğrenci:"
                  f" {ans}. 0-20 arası puan ve kısa açıklama ver."
              )
              st.info(f"Soru {idx+1} Değerlendirmesi:\n\n{eval_res}")
