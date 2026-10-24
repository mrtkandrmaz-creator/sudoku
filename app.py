import json
import os
import random
import re
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi",
    page_icon="🎒",
    layout="wide",
)

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
          return completion.choices[0].message.content
      except Exception:
        continue

  if has_gemini and gemini_keys:
    for g_key in gemini_keys:
      try:
        genai.configure(api_key=g_key)
        for model_name in [
            "gemini-3.6-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro",
        ]:
          try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt_text)
            if response and response.text:
              return response.text
          except Exception:
            continue
      except Exception:
        continue

  return None


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
            "5. Ünite: Üreten Türkiye",
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
if "coach_open" not in st.session_state:
  st.session_state["coach_open"] = False
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


# --- 6. SORUYA BİREBİR UYUMLU AKILLI SVG GÖRSEL MOTORU ---
def render_question_visual(gorsel_tipi, param):
  if not gorsel_tipi or gorsel_tipi == "yok":
    return

  if gorsel_tipi in ["ucgen", "aci"]:
    deg = 60
    try:
      deg = int(re.search(r"\d+", str(param)).group())
    except Exception:
      pass

    import math

    rad = math.radians(deg)
    x_top = int(30 + 140 * math.cos(rad))
    y_top = int(140 - 120 * math.sin(rad))
    if x_top < 50:
      x_top = 50
    if x_top > 190:
      x_top = 190

    is_right_angle = "dik" in str(param).lower() or deg == 90
    right_angle_svg = (
        '<polyline points="170,130 170,110 190,110" fill="none" stroke="#f43f5e"'
        ' stroke-width="3"/>'
        if is_right_angle
        else ""
    )

    svg_code = f"""
        <svg width="240" height="160" viewBox="0 0 240 160" style="background:#0f172a; border-radius:12px; display:block; margin: 10px auto; border: 2px solid #38bdf8;">
            <polygon points="30,140 {x_top},{y_top} 210,140" fill="none" stroke="#38bdf8" stroke-width="4"/>
            {right_angle_svg}
            <path d="M 55 140 A 25 25 0 0 1 65 115" fill="none" stroke="#facc15" stroke-width="3"/>
            <text x="75" y="125" fill="#facc15" font-size="15" font-weight="bold">{deg}°</text>
            <text x="100" y="155" fill="#ffffff" font-size="12">Açı Değeri: {deg}°</text>
        </svg>
        """
    st.markdown(svg_code, unsafe_allow_html=True)

  elif gorsel_tipi == "dinamometre":
    newton = 5
    try:
      newton = int(re.search(r"\d+", str(param)).group())
    except Exception:
      pass
    spring_y = 40 + min(newton * 7, 75)
    svg_code = f"""
        <svg width="180" height="220" viewBox="0 0 180 220" style="background:#0f172a; border-radius:12px; display:block; margin: 10px auto; border: 2px solid #38bdf8;">
            <rect x="75" y="10" width="30" height="20" fill="#94a3b8" rx="5"/>
            <rect x="55" y="30" width="70" height="140" fill="none" stroke="#38bdf8" stroke-width="4" rx="10"/>
            <path d="M 90 30 Q 65 {30+spring_y/4} 115 {30+spring_y/2} Q 65 {30+3*spring_y/4} 90 {30+spring_y}" fill="none" stroke="#facc15" stroke-width="3"/>
            <rect x="65" y="{30+spring_y}" width="50" height="25" fill="#f43f5e" rx="4"/>
            <text x="75" y="{47+spring_y}" fill="#ffffff" font-size="14" font-weight="bold">{newton} N</text>
            <text x="35" y="200" fill="#38bdf8" font-size="12">Ölçülen Kuvvet</text>
        </svg>
        """
    st.markdown(svg_code, unsafe_allow_html=True)

  elif gorsel_tipi in ["ay_evresi", "cember"]:
    phase_name = str(param)
    svg_code = f"""
        <svg width="220" height="160" viewBox="0 0 220 160" style="background:#0f172a; border-radius:12px; display:block; margin: 10px auto; border: 2px solid #38bdf8;">
            <circle cx="45" cy="80" r="28" fill="#f59e0b"/>
            <text x="25" y="84" fill="#000000" font-size="10" font-weight="bold">GÜNEŞ</text>
            <circle cx="170" cy="80" r="26" fill="#334155" stroke="#94a3b8" stroke-width="2"/>
            <path d="M 170 54 A 26 26 0 0 1 170 106 Z" fill="#f8fafc"/>
            <text x="125" y="135" fill="#38bdf8" font-size="13" font-weight="bold">{phase_name}</text>
        </svg>
        """
    st.markdown(svg_code, unsafe_allow_html=True)


# --- 7. SOL MENÜ ---
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


# --- 8. SAĞ ALT KÖŞE: 50 KURUŞ BOYUTUNDA SEVİMLİ AVATAR & DİKEY CANLI SOHBET ---

# Avatar açma/kapama butonunu tetiklemek için özel CSS ve Container
st.markdown(
    f"""
    <style>
    /* 50 kuruş para boyutunda (yaklaşık 45-50px) yuvarlak sevimli avatar düğmesi */
    .floating-avatar-btn {{
        position: fixed;
        bottom: 25px;
        right: 25px;
        width: 50px;
        height: 50px;
        background: {c_bg_gradient};
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        cursor: pointer;
        z-index: 99999;
        transition: transform 0.2s ease;
        border: 2px solid white;
    }}
    .floating-avatar-btn:hover {{
        transform: scale(1.1);
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# Sağ alt köşe etkileşimli butonu
with st.container():
  # Görünmez ama tıklanabilir Streamlit butonunu absolute konumlandırılmış şık bir avatarın altına konumlandırıyoruz
  if st.session_state["coach_open"]:
    if st.button("❌", key="close_avatar_float", help="Asistanı Kapat"):
      st.session_state["coach_open"] = False
      st.rerun()
  else:
    if st.button("🦊", key="open_avatar_float", help="AdenMind Canlı Asistan"):
      st.session_state["coach_open"] = True
      st.rerun()

# Eğer asistan açıksa sağ altta dikey, modern mobil sohbet penceresi belirir
if st.session_state["coach_open"]:
  st.markdown(
      f"""
        <div style="
            position: fixed; 
            bottom: 85px; 
            right: 20px; 
            width: 330px; 
            height: 440px; 
            background: #ffffff; 
            border: 2px solid {c_border}; 
            border-radius: 20px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.25); 
            z-index: 99998; 
            display: flex;
            flex-direction: column;
            overflow: hidden;
        ">
            <!-- Üst Modern Başlık -->
            <div style="background: {c_bg_gradient}; padding: 10px 14px; color: white; display: flex; align-items: center; justify-content: space-between; font-weight: bold; font-size: 14px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 20px;">🦊</span>
                    <span>AdenMind</span>
                </div>
                <span style="font-size: 11px; opacity: 0.9; background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 10px;">Çevrimiçi</span>
            </div>
        </div>
    """,
      unsafe_allow_html=True,
  )

  # Sohbet mesajları dikey akış alanı
  chat_container = st.container()
  with chat_container:
    st.markdown(
        """
        <div style="position: fixed; bottom: 140px; right: 28px; width: 314px; height: 310px; overflow-y: auto; z-index: 99999; padding-right: 4px;">
        """,
        unsafe_allow_html=True,
    )

    for msg in st.session_state["coach_messages"]:
      if msg["role"] == "assistant":
        st.markdown(
            f"""
                <div style="display: flex; align-items: flex-start; gap: 6px; margin-bottom: 8px;">
                    <div style="font-size: 16px;">🦊</div>
                    <div style="background-color: {c_bubble_ai}; padding: 8px 10px; border-radius: 12px; border-top-left-radius: 2px; color: {c_text_color}; font-size: 12px; max-width: 85%; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        {msg['content']}
                    </div>
                </div>
                """,
            unsafe_allow_html=True,
        )
      else:
        st.markdown(
            f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 8px;">
                    <div style="background-color: {c_bubble_user}; padding: 8px 10px; border-radius: 12px; border-top-right-radius: 2px; color: #1e293b; font-size: 12px; max-width: 85%; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                        {msg['content']}
                    </div>
                </div>
                """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

  # Dikey sohbet alt form giriş alanı
  st.markdown(
      """
        <div style="position: fixed; bottom: 90px; right: 28px; width: 314px; z-index: 99999; background: white; padding-top: 4px;">
    """,
      unsafe_allow_html=True,
  )
  with st.form("vertical_chat_form", clear_on_submit=True):
    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
      user_msg = st.text_input(
          "Mesaj yaz...", label_visibility="collapsed", key="v_msg"
      )
    with col_btn:
      submitted = st.form_submit_button("Gönder")

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

  st.markdown("</div>", unsafe_allow_html=True)


# --- AŞAMA 1: DERS SEÇİMİ (KARTLARA DİREKT TIKLAMA) ---
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

# --- AŞAMA 2: ÜNİTE SEÇİMİ (KARTLARA DİREKT TIKLAMA) ---
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

# --- AŞAMA 3: OYUN, ETKİNLİK VE SORU MODELLERİ ---
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
          "isim": "✅ Doğru / Yanlış Meydan Okuması",
          "renk": "linear-gradient(135deg, #38ef7d, #11998e)",
      },
      {
          "id": "bosluk",
          "isim": "📝 Boşluk Doldurma Yarışması",
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

    if st.button("🚀 Balon Sorularını Üret", key="gen_5_balloons"):
      with st.spinner("Yapay zeka soru ve görsel çizimlerini hazırlıyor..."):
        prompt = f"""
                5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {curr_unit}.
                TAM 5 ADET çoktan seçmeli (4 şıklı: A, B, C, D) soru üret.
                Matematik için açı (örn: 50 derece, çeşitkenar/dik üçgen), çember; Fen için dinamometre veya Ay evresi soruları üret.
                Soru metnindeki açı değerini veya özellikleri gorsel_parametre alanına yaz.
                JSON formatında liste olarak ver:
                [
                  {{
                    "soru": "Soru metni",
                    "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
                    "dogru_cevap": "A",
                    "aciklama": "Açıklama",
                    "gorsel_tipi": "aci", 
                    "gorsel_parametre": "50 derece"
                  }}
                ]
                (gorsel_tipi: 'aci', 'ucgen', 'dinamometre', 'ay_evresi', 'cember' veya 'yok')
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["balloon_5_questions"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.session_state["game_started"] = False
            st.rerun()
          except Exception as e:
            st.error(f"Hata: {e}")

    if st.session_state["balloon_5_questions"]:
      if not st.session_state["game_started"]:
        st.success("✅ Görsel Uyumlu Sorular Hazır! Oyunu başlatmak için tıklayın.")
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

  # 2. 5 SORULUK MEB KAZANIM OYUNU (HER SAYFADA TEK SORU MANTIĞI)
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

    if st.button("🚀 Görsel Uyumlu Kazanım Sorularını Üret", key="gen_kazanim"):
      with st.spinner(
          "Yapay zeka MEB kazanım sorularını ve özel şemaları hazırlıyor..."
      ):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                TAM 5 ADET çoktan seçmeli (4 şıklı) soru üret. 
                Matematik soruları için açı (örn: 50 derece, dik veya çeşitkenar üçgen); Fen soruları için dinamometre veya Ay evresi içersin. Soruya tam uygun görsel tipi belirtin.
                JSON liste formatında şu yapıda ver:
                [
                  {{
                    "soru": "...", 
                    "secenekler": ["A)...", "B)...", "C)...", "D)..."], 
                    "dogru_cevap": "A", 
                    "aciklama": "...",
                    "gorsel_tipi": "aci",
                    "gorsel_parametre": "50 derece"
                  }}
                ]
                (gorsel_tipi: 'aci', 'ucgen', 'dinamometre', 'ay_evresi' veya 'yok')
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["kazanim_list"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.session_state["kazanim_idx"] = 0
            st.session_state["kazanim_score"] = 0
            st.session_state["kazanim_answers"] = {}
            st.rerun()
          except Exception:
            pass

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

        col_prev, col_next = st.columns(2)
        with col_prev:
          if k_idx > 0 and st.button(
              "⬅️ Önceki Soruya Dön", use_container_width=True
          ):
            st.session_state["kazanim_idx"] -= 1
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
              chosen_letter = (
                  selected_option.charAt(0).upper()
                  if hasattr(selected_option, "charAt")
                  else selected_option[0].upper()
              )
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
    st.subheader(f"✅ {curr_subj} — Doğru / Yanlış Meydan Okuması")
    if (
        "dy_questions" not in st.session_state
        or st.session_state.get("dy_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["dy_questions"] = None
      st.session_state["dy_unit_key"] = (curr_subj, curr_unit)
      st.session_state["dy_score"] = 0
      st.session_state["dy_current_q"] = 0
      st.session_state["dy_feedback"] = ""

    if st.button("🚀 Yeni D/Y Yarışmasını Başlat", key="gen_dy"):
      with st.spinner("Önermeler hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                TAM 5 ADET Doğru veya Yanlış önermesi üret. JSON formatında liste ver:
                [
                  {{"ifade": "...", "cevap": "D", "aciklama": "...", "gorsel_tipi": "yok", "gorsel_parametre": ""}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["dy_questions"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.session_state["dy_score"] = 0
            st.session_state["dy_current_q"] = 0
            st.session_state["dy_feedback"] = ""
            st.rerun()
          except Exception:
            pass

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
          col_d, col_y = st.columns(2)
          with col_d:
            if st.button("✅ DOĞRU (D)", use_container_width=True):
              if q_item["cevap"].upper() == "D":
                st.session_state["dy_score"] += 20
                st.session_state["dy_feedback"] = (
                    f"🎉 **Doğru!**<br><span"
                    f" style='color:#10b981;'>{q_item['aciklama']}</span>"
                )
              else:
                st.session_state["dy_feedback"] = (
                    f"❌ **Yanlış!** Doğru cevap Yanlış (Y) idi.<br><span"
                    f" style='color:#f43f5e;'>{q_item['aciklama']}</span>"
                )
              st.rerun()
          with col_y:
            if st.button("❌ YANLIŞ (Y)", use_container_width=True):
              if q_item["cevap"].upper() == "Y":
                st.session_state["dy_score"] += 20
                st.session_state["dy_feedback"] = (
                    f"🎉 **Doğru!**<br><span"
                    f" style='color:#10b981;'>{q_item['aciklama']}</span>"
                )
              else:
                st.session_state["dy_feedback"] = (
                    f"❌ **Yanlış!** Doğru cevap Doğru (D) idi.<br><span"
                    f" style='color:#f43f5e;'>{q_item['aciklama']}</span>"
                )
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
    st.subheader(f"📝 {curr_subj} — Boşluk Doldurma Yarışması")
    if (
        "fill_blanks" not in st.session_state
        or st.session_state.get("f_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["fill_blanks"] = None
      st.session_state["f_unit_key"] = (curr_subj, curr_unit)

    if st.button("✨ Boşluk Doldurma Sorularını Üret", key="gen_fill"):
      with st.spinner("Sorular hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                Cümle içinde boşluk bırakılmış 5 adet soru üret. JSON liste formatında ver:
                [
                  {{"cumle": "Güneş kendi ekseni etrafında ... döner.", "dogru_kelime": "saat yönünün tersine", "secenekler": ["saat yönünün tersine", "saat yönünde", "kuzeye", "güneye"], "gorsel_tipi": "yok", "gorsel_parametre": ""}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["fill_blanks"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            pass

    if st.session_state["fill_blanks"]:
      fdata = st.session_state["fill_blanks"]
      with st.form("fill_form"):
        f_ans = {}
        for idx, fq in enumerate(fdata):
          st.markdown(f"**Soru {idx+1}:** {fq['cumle']}")
          if "gorsel_tipi" in fq and fq["gorsel_tipi"] != "yok":
            render_question_visual(
                fq.get("gorsel_tipi"), fq.get("gorsel_parametre", "")
            )
          f_ans[idx] = st.selectbox(
              f"Boşluğa gelecek kelimeyi seç ({idx+1}):",
              fq["secenekler"],
              index=None,
              key=f"f_{idx}",
          )
          st.markdown("---")
        if st.form_submit_button("Cevapları Kontrol Et"):
          fscore = 0
          for idx, fq in enumerate(fdata):
            if f_ans[idx] == fq["dogru_kelime"]:
              fscore += 20
              st.success(f"Soru {idx+1} Doğru!")
            else:
              st.error(
                  f"Soru {idx+1} Yanlış! Doğru kelime: **{fq['dogru_kelime']}**"
              )
          st.info(f"🏆 Toplam Puanınız: {fscore} / 100")

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

    if st.button("✨ Soru Kartlarını Dağıt", key="gen_fc"):
      with st.spinner("Kartlar hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                Önemli kavram ve soruları içeren 5 adet flashcard üret. JSON liste formatında ver:
                [
                  {{"on_yuz": "Kavram/Soru", "arka_yuz": "Açıklama/Cevap"}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["flashcards"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.session_state["fc_idx"] = 0
            st.rerun()
          except Exception:
            pass

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
        col_prev, col_next = st.columns(2)
        with col_prev:
          if f_idx > 0 and st.button(
              "⬅️ Önceki Kart", use_container_width=True
          ):
            st.session_state["fc_idx"] -= 1
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
    st.info(
        "Bu modül, konuları oyunlaştırılmış senaryolar, interaktif bulmacalar"
        " ve mini görevlerle pekiştirmenizi sağlar."
    )
    if st.button("🚀 Oynayarak Öğren Görevini Başlat"):
      with st.spinner("Görev yükleniyor..."):
        prompt = f"5. Sınıf {curr_subj} {curr_unit} için eğlenceli ve interaktif bir oynayarak öğren görev senaryosu ve ipuçları üret."
        res = ai_generate_content(prompt)
        if res:
          st.markdown(res)

  # 7. ETKİNLİKLERLE ÖĞREN
  elif curr_game == "etkinlik":
    st.subheader(f"📚 {curr_subj} — Etkinliklerle Öğren Merkezi")
    st.info(
        "MEB müfredatına uyumlu günlük etkinlikler, deneyler ve pratik uygulama"
        " adımları."
    )
    if st.button("🚀 Etkinlik Önerisi Getir"):
      with st.spinner("Etkinlik hazırlanıyor..."):
        prompt = f"5. Sınıf {curr_subj} {curr_unit} için evde veya sınıfta yapılabilecek 3 adet yaratıcı öğrenme etkinliği öner."
        res = ai_generate_content(prompt)
        if res:
          st.markdown(res)

  # 8. KELİME AVI
  elif curr_game == "kelime":
    st.subheader(f"🔤 {curr_subj} — Kelime Avı Bulmacası")
    if (
        "puz_items" not in st.session_state
        or st.session_state.get("p_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["puz_items"] = None
      st.session_state["p_unit_key"] = (curr_subj, curr_unit)
      st.session_state["puz_idx"] = 0
      st.session_state["puz_score"] = 0
      st.session_state["user_guess"] = []

    if st.button("🔍 Kelime Avını Başlat", key="gen_puz"):
      with st.spinner("Bulmaca kelimeleri hazırlanıyor..."):
        prompt = f"""
                5. Sınıf {curr_subj} {curr_unit} için 5 adet anahtar kelime ve tanım ipucu üret.
                JSON liste formatında ver:
                [
                  {{"kelime": "TERİM", "ipucu": "..."}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["puz_items"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.session_state["puz_idx"] = 0
            st.session_state["puz_score"] = 0
            st.session_state["user_guess"] = []
            st.rerun()
          except Exception:
            pass

    if st.session_state["puz_items"]:
      items = st.session_state["puz_items"]
      p_idx = st.session_state["puz_idx"]
      if p_idx < len(items):
        cur_item = items[p_idx]
        t_word = cur_item["kelime"].upper()
        st.info(f"💡 İpucu: {cur_item['ipucu']}")

        if f"pool_{p_idx}" not in st.session_state:
          pool = list(t_word)
          while len(pool) < len(t_word) + 3:
            pool.append(random.choice("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"))
          random.shuffle(pool)
          st.session_state[f"pool_{p_idx}"] = pool

        user_g = st.session_state["user_guess"]
        st.write("Oluşturulan:", "".join(user_g))

        cols = st.columns(len(st.session_state[f"pool_{p_idx}"]))
        for l_i, l_char in enumerate(st.session_state[f"pool_{p_idx}"]):
          with cols[l_i]:
            if st.button(l_char, key=f"hb_{p_idx}_{l_i}_{l_char}"):
              if len(st.session_state["user_guess"]) < len(t_word):
                st.session_state["user_guess"].append(l_char)
                st.rerun()

        if st.button("Kontrol Et"):
          if "".join(st.session_state["user_guess"]) == t_word:
            st.success("🎉 Doğru!")
            st.session_state["puz_idx"] += 1
            st.session_state["user_guess"] = []
            st.rerun()
          else:
            st.error("Tekrar dene.")
      else:
        st.success("Tüm kelimeler tamamlandı!")

  # 9. KLASİK YAZILI SİMÜLATÖRÜ
  elif curr_game == "acik":
    st.subheader(f"✍️ {curr_subj} — Klasik Yazılı Simülatörü")
    if (
        "classic_exam" not in st.session_state
        or st.session_state.get("c_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["classic_exam"] = None
      st.session_state["c_unit_key"] = (curr_subj, curr_unit)

    if st.button("✨ Yazılı Sınavını Başlat", key="gen_classic"):
      with st.spinner("Sorular hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                TAM 5 ADET açık uçlu yazılı sorusu ve ideal cevapları JSON liste formatında ver:
                [
                  {{"soru": "...", "beklenen_cevap": "..."}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["classic_exam"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            pass

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
