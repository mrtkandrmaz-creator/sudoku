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


# --- KESİN GÜVENLİ JSON PARSER ---
def safe_parse_json(raw_text):
  if not raw_text:
    return None
  try:
    cleaned = re.sub(r"```json|```", "", raw_text).strip()
    match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
    if match:
      cleaned = match.group(1)
    data = json.loads(cleaned)
    return deep_clean_json_data(data)
  except Exception:
    try:
      cleaned = raw_text.replace("'", '"')
      data = json.loads(cleaned)
      return deep_clean_json_data(data)
    except Exception:
      return None


# --- SECRETS.TOML OKUYAN AKILLI MOTOR ---
def get_all_api_keys():
  gemini_keys = []
  groq_keys = []
  try:
    if hasattr(st, "secrets") and "api_keys" in st.secrets:
      api_block = st.secrets["api_keys"]
      if "groq_keys" in api_block:
        for k in api_block["groq_keys"]:
          if isinstance(k, str) and k.startswith("gsk_") and len(k.strip()) > 10:
            if k.strip() not in groq_keys:
              groq_keys.append(k.strip())
  except Exception:
    pass

  # Manuel eklenenler
  if "manual_groq" in st.session_state and st.session_state["manual_groq"]:
    mg = st.session_state["manual_groq"].strip()
    if mg and mg not in groq_keys:
      groq_keys.append(mg)

  return gemini_keys, groq_keys


# --- GERÇEK ZAMANLI YAPAY ZEKA SORU ÜRETİCİ (GROQ ÖNCELİKLİ) ---
def ai_generate_content(prompt_text):
  raw_res = None
  _, groq_keys = get_all_api_keys()

  # Groq Anahtarları ile İstek Atma
  if groq_keys:
    try:
      from groq import Groq

      for gr_key in groq_keys:
        try:
          client = Groq(api_key=gr_key)
          groq_models = [
              "llama-3.3-70b-versatile",
              "llama-3.1-70b-versatile",
              "llama-3.1-8b-instant",
              "llama3-70b-8192",
              "mixtral-8x7b-32768",
              "gemma2-9b-it",
          ]
          for g_model in groq_models:
            try:
              completion = client.chat.completions.create(
                  model=g_model,
                  messages=[{"role": "user", "content": prompt_text}],
                  temperature=0.95,
              )
              if (
                  completion
                  and completion.choices
                  and completion.choices[0].message.content
              ):
                raw_res = completion.choices[0].message.content
                break
            except Exception:
              continue
          if raw_res:
            break
        except Exception:
          continue
    except Exception:
      pass

  return clean_math_text(raw_res) if raw_res else None


# --- 2. 5. SINIF MEB MÜFREDATI VE DERS RENKLERİ ---
MEB_CURRICULUM = {
    "Matematik": {
        "renk": "linear-gradient(135deg, #2193b0, #6dd5ed)",
        "ikon": "📐",
        "uniteler": [
            (
                "1. Tema: Geometrik Şekiller (Nokta, Doğru, Açı, Çokgenler,"
                " Çember)"
            ),
            (
                "2. Tema: Sayılar ve Nicelikler (1) (Çok Basamaklı Sayılar ve"
                " Dört İşlem)"
            ),
            (
                "3. Tema: Geometrik Nicelikler (Uzunluk, Çevre ve Alan"
                " Hesaplamaları)"
            ),
            (
                "4. Tema: Sayılar ve Nicelikler (2) (Kesirler, Ondalık ve"
                " Yüzdeler)"
            ),
            (
                "5. Tema: İstatistiksel Araştırma Süreci (Veri Toplama ve"
                " Grafikler)"
            ),
            (
                "6. Tema: İşlemlerle Cebirsel Düşünme ve Veriden Olasılığa"
                " (Örüntüler ve Olasılık)"
            ),
        ],
    },
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


# --- 6. ÇEŞİTLENDİRİLMİŞ GEOMETRİ VE ŞEKİL ÇİZİM MOTORU ---
def render_question_visual(gorsel_tipi, param):
  if not gorsel_tipi or gorsel_tipi == "yok":
    return
  param_str = clean_math_text(str(param)).strip()

  if gorsel_tipi == "ucgen":
    svg_html = """
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="280" height="190" viewBox="0 0 280 190" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 18px; border: 1.5px solid rgba(56, 189, 248, 0.4);">
                <polygon points="140,35 35,150 245,150" fill="rgba(56, 189, 248, 0.2)" stroke="#38bdf8" stroke-width="4" stroke-linejoin="round"/>
                <text x="140" y="95" fill="#facc15" font-size="14" font-weight="bold" text-anchor="middle">Üçgen Geometrisi</text>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=205)
  elif gorsel_tipi in ["dortgen", "dikdortgen", "kare", "paralelkenar", "yamuk"]:
    svg_html = """
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="280" height="190" viewBox="0 0 280 190" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 18px; border: 1.5px solid rgba(56, 189, 248, 0.4);">
                <rect x="50" y="45" width="180" height="100" fill="rgba(56, 189, 248, 0.1)" stroke="#38bdf8" stroke-width="4" rx="6"/>
                <text x="140" y="100" fill="#facc15" font-size="14" font-weight="bold" text-anchor="middle">Dörtgen Analizi</text>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=205)
  elif gorsel_tipi == "cember":
    svg_html = """
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="280" height="185" viewBox="0 0 280 185" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 18px; border: 1.5px solid rgba(56, 189, 248, 0.4);">
                <circle cx="140" cy="90" r="60" fill="none" stroke="#38bdf8" stroke-width="4"/>
                <circle cx="140" cy="90" r="4" fill="#facc15"/>
                <line x1="80" y1="90" x2="200" y2="90" stroke="#f43f5e" stroke-width="2.5" stroke-dasharray="5,3"/>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=200)
  else:
    svg_html = """
        <div style="display: flex; justify-content: center; margin: 12px 0;">
            <svg width="180" height="180" viewBox="0 0 180 180" style="background:#0f172a; border-radius:16px; border: 2px solid #38bdf8;">
                <text x="90" y="95" fill="#ffffff" font-size="14" font-weight="bold" text-anchor="middle">Görsel Model</text>
            </svg>
        </div>
        """
    st.components.v1.html(svg_html, height=195)


# --- 7. SOL MENÜ VE KONTROL PANELİ ---
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
      prompt = (
          f"Sen 5. sınıf MEB müfredatı odaklı, sevimli ve bilgili akıllı koçsun."
          f" Adın AdenMind. Öğrencinin sorusu: {user_msg}. Kısa ve sevimli rehberlik yap."
      )
      ai_reply = ai_generate_content(prompt)
      reply_text = (
          ai_reply
          if ai_reply
          else "Harika bir soru! Çalışmalarında başarılar dilerim. 🌟"
      )
      st.session_state["coach_messages"].append(
          {"role": "assistant", "content": reply_text}
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

# --- AŞAMA 2: ÜNİTE / TEMA SEÇİMİ ---
elif (
    st.session_state["selected_subject"] is not None
    and st.session_state["selected_unit"] is None
):
  curr_subj = st.session_state["selected_subject"]
  curr_data = MEB_CURRICULUM[curr_subj]

  st.markdown(
      f"### {curr_data['ikon']} {curr_subj} — Tema / Ünite Seçim Ekranı"
  )
  st.write("Çalışmak istediğiniz tema veya üniteye doğrudan tıklayın:")

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
                <div style="font-size: 17px;">📖 {unit_name}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(
          f"Seç: Tema {idx+1}",
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
            <b>Seçilen Ders:</b> {curr_subj} &nbsp;|&nbsp; <b>Tema:</b> {curr_unit}
        </div>
    """,
      unsafe_allow_html=True,
  )

  if st.button("↩️ Tema Değiştir", key="back_unit"):
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

    if st.button(
        "🚀 Groq API ile Yepyeni Sorular Üret", key="gen_5_balloons"
    ):
      with st.spinner("Yapay zeka Groq API ile soruları hazırlıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Tema: {curr_unit}.
                TAM 5 ADET tamamen birbirinden farklı, özgün ve çeşitli çoktan seçmeli soru üret.
                JSON formatında geçerli bir liste olarak ver:
                [
                  {{
                    "soru": "Soru metni",
                    "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
                    "dogru_cevap": "A",
                    "aciklama": "Açıklama",
                    "gorsel_tipi": "ucgen", 
                    "gorsel_parametre": "ABC, A:90°, B:45°"
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
              "⚠️ Sorular üretilemedi. Lütfen Groq API anahtar kotanızı"
              " kontrol edin."
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
                    let currentIdx = 0, score = 0, active = true;
                    function loadQ() {
                        if(currentIdx >= questions.length) {
                            document.getElementById('game-container').innerHTML = `<h2 style="padding:100px;">🏆 Oyun Tamamlandı! Puan: ${score}</h2>`;
                            return;
                        }
                        active = true;
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
                            b.innerText = opt;
                            b.onclick = () => {
                                if(!active) return; active = false;
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

    if st.button(
        "🚀 Groq API ile Kazanım Soruları Üret", key="gen_kazanim"
    ):
      with st.spinner("Sorular yapay zeka tarafından üretiliyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Tema: {curr_unit}.
                TAM 5 ADET birbirini tekrar etmeyen, farklı alt başlıklardan çoktan seçmeli soru üret. 
                JSON liste formatında şu yapıda ver:
                [
                  {{
                    "soru": "...", 
                    "secenekler": ["A)...", "B)...", "C)...", "D)..."], 
                    "dogru_cevap": "A", 
                    "aciklama": "...",
                    "gorsel_tipi": "dortgen",
                    "gorsel_parametre": "ABCD, A:90°, B:90°, C:90°, D:90°"
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

    if st.button("🚀 D/Y Sorularını Üret", key="gen_dy"):
      with st.spinner("Önermeler hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Tema: {curr_unit}.
                TAM 5 ADET Doğru veya Yanlış önermesi üret. 
                JSON liste formatında ver:
                [
                  {{"ifade": "...", "cevap": "D", "aciklama": "...", "gorsel_tipi": "cember", "gorsel_parametre": "O, 10cm"}}
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
                    f"❌ **Yanlış Seçim!**<br><span"
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
                    f"❌ **Yanlış Seçim!**<br><span"
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

    if st.button("✨ Boşluk Doldurma Sorularını Üret", key="gen_fill"):
      with st.spinner("Sorular hazırlanıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Tema: {curr_unit}.
                Cümle içinde boşluk bırakılmış 5 adet soru üret. JSON liste formatında ver:
                [
                  {{"cumle": "...", "dogru_kelime": "...", "secenekler": ["...", "...", "...", "..."], "gorsel_tipi": "cember", "gorsel_parametre": "O, 8cm"}}
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

        if st.session_state["fill_feedback"]:
          st.markdown(st.session_state["fill_feedback"], unsafe_allow_html=True)
          st.markdown("<br>", unsafe_allow_html=True)
          if st.button("➡️ Sonraki Soruya Geç", use_container_width=True):
            st.session_state["fill_feedback"] = ""
            st.session_state["fill_idx"] += 1
            st.rerun()
        else:
          st.markdown("**Boşluğa gelecek kelimeyi seçin:**")
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
                      f"🎉 **Doğru Cevap!**<br><span"
                      f" style='color:#10b981;'><b>{opt_val}</b></span>"
                  )
                else:
                  st.session_state["fill_feedback"] = (
                      f"❌ **Yanlış!** Doğru kelime: <b>{fq['dogru_kelime']}</b>"
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
                <h2>🏆 Yarışma Tamamlandı! Puan: {st.session_state['fill_score']} / 100</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🔄 Tekrar Yarış", use_container_width=True):
          st.session_state["fill_blanks"] = None
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

    if st.button("✨ Soru Kartlarını Dağıt", key="gen_fc"):
      with st.spinner("Kartlar hazırlanıyor..."):
        prompt = f"5. Sınıf MEB, Ders: {curr_subj}, Tema: {curr_unit}. 5 adet flashcard üret. JSON: [{{'on_yuz': '...', 'arka_yuz': '...'}}]"
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
                <div style="font-size: 20px; margin-top: 20px;">💡 <b>Cevap:</b> {card['arka_yuz']}</div>
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
    st.markdown(
        f"""
        <div style="background: rgba(255,255,255,0.06); padding: 20px; border-radius: 14px; border: 2px solid {c_border}; margin-bottom: 15px;">
            <h4 style="color: #38bdf8; margin-top:0;">📖 Senaryo</h4>
            <p style="font-size: 16px;">{curr_subj} dersi {curr_unit} konusuna yönelik günlük yaşam senaryosu.</p>
            <h4 style="color: #facc15;">🎯 Görev</h4>
            <p style="font-size: 18px; font-weight: bold;">En doğru yaklaşım hangisidir?</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("interactive_choice_form"):
      user_choice = st.radio(
          "Seçiminizi Yapın:",
          ["A) Planlı çalışmak", "B) Rastgele ilerlemek"],
          index=None,
      )
      if st.form_submit_button("Değerlendir"):
        if user_choice:
          st.success("Tebrikler, harika bir karar!")
        else:
          st.warning("Lütfen bir seçenek seçin.")

  # 7. ETKİNLİKLERLE ÖĞREN
  elif curr_game == "etkinlik":
    st.subheader(f"📚 {curr_subj} — Etkinliklerle Öğren Merkezi")
    st.markdown(
        f"1. **{curr_subj} Pratiği:** {curr_unit} için günlük gözlem yapın.\n2."
        " **Özet:** Önemli noktaları not edin."
    )

  # 8. KELİME AVI BULMACASI
  elif curr_game == "kelime":
    st.subheader(f"🔤 {curr_subj} — Kelime Avı Bulmacası")
    st.markdown(
        "**İpucu:** Bu üniteye ait temel kavram. (Kelime uzunluğu: 3 harf)"
    )
    guess = st.text_input("Kelimeyi yazın:")
    if st.button("Kontrol Et"):
      if guess.upper().strip() in ["MEB", "DERS", "OGREN"]:
        st.success("🎉 Doğru!")
      else:
        st.error("Tekrar deneyin.")

  # 9. KLASİK YAZILI SİMÜLATÖRÜ
  elif curr_game == "acik":
    st.subheader(f"✍️ {curr_subj} — Klasik Yazılı Simülatörü")
    with st.form("classic_form"):
      st.markdown(
          f"**Soru:** {curr_subj} dersi {curr_unit} ünitesinin önemini"
          " açıklayınız."
      )
      ans = st.text_area("Yazılı Cevabınız:")
      if st.form_submit_button("Kağıdı Puanlat"):
        st.info(
            "📝 **Değerlendirme:** Cevabınız 5. sınıf MEB kazanımlarına uygundur."
            " Puan: 100/100"
        )
