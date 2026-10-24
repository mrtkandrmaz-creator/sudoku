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
            "4. Ünite: Geometrik Kavramlar",
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

# --- 3. MODERN MEB STİLLERİ (CSS) ---
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #4e54c8, #8f94fb);
        padding: 22px;
        border-radius: 16px;
        color: white;
        text-align: center;
        font-weight: 800;
        font-size: 28px;
        margin-bottom: 25px;
        box-shadow: 0 8px 25px rgba(78, 84, 200, 0.35);
        letter-spacing: 0.5px;
    }
    .card-box {
        padding: 26px;
        border-radius: 16px;
        color: white;
        text-align: center;
        font-weight: bold;
        font-size: 22px;
        margin-bottom: 12px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        transition: transform 0.3s ease;
    }
    .card-box:hover {
        transform: translateY(-4px);
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border-radius: 12px;
        font-weight: bold;
        border: none;
        padding: 12px 24px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: 0.3s;
    }
    .stButton>button:hover {
        opacity: 0.92;
        transform: scale(1.02);
    }
    </style>
    <div class="main-header">🎒 MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi (Murat KANDIRMAZ)</div>
""",
    unsafe_allow_html=True,
)

# --- 4. SOL MENÜ ---
with st.sidebar:
  st.subheader("⚙️ Sistem & API Durumu")
  if gemini_keys or groq_keys:
    st.success(
        f"✅ Yapay Zeka Aktif!\n(Groq: {len(groq_keys)}, Gemini:"
        f" {len(gemini_keys)})"
    )
  else:
    st.warning("⚠️ TOML'dan anahtar okunamadı.")

  st.markdown("---")
  if st.button("🏠 Ana Sayfaya Dön", key="home_btn", use_container_width=True):
    st.session_state["selected_subject"] = None
    st.session_state["selected_unit"] = None
    st.session_state["selected_game"] = None
    st.session_state["game_started"] = False
    st.rerun()

# --- 5. SESSION STATE TANIMLARI ---
if "selected_subject" not in st.session_state:
  st.session_state["selected_subject"] = None
if "selected_unit" not in st.session_state:
  st.session_state["selected_unit"] = None
if "selected_game" not in st.session_state:
  st.session_state["selected_game"] = None
if "game_started" not in st.session_state:
  st.session_state["game_started"] = False
if "coach_open" not in st.session_state:
  st.session_state["coach_open"] = False
if "coach_messages" not in st.session_state:
  st.session_state["coach_messages"] = [
      {
          "role": "assistant",
          "content": (
              "Merhaba! Ben senin Yapay Zeka Öğretmen Koçunum. Takıldığın bir"
              " soru ya da anlamadığın bir konu olursa bana her zaman"
              " sorabilirsin! 🤖"
          ),
      }
  ]

# --- 6. GLOBAL SAĞ ALT KÖŞE: AKILLI ASİSTAN (YAPAY ZEKA KOÇU) ---
st.markdown("---")
with st.container():
  col_space, col_trigger = st.columns([10, 2])
  with col_trigger:
    coach_btn_label = (
        "🤖 Koçu Kapat ❌"
        if st.session_state["coach_open"]
        else "🤖 Yapay Zeka Koçum 💬"
    )
    if st.button(coach_btn_label, key="toggle_coach_floating"):
      st.session_state["coach_open"] = not st.session_state["coach_open"]
      st.rerun()

if st.session_state["coach_open"]:
  with st.container():
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1e1b4b, #312e81); padding: 20px; border-radius: 16px; border: 2px solid #6366f1; box-shadow: 0 10px 30px rgba(0,0,0,0.4); margin-bottom: 25px;">
            <h3 style="color: #38bdf8; margin-top: 0;">🤖 Canlı Yapay Zeka Öğretmen Koçu</h3>
            <p style="color: #cbd5e1; font-size: 14px;">Hangi sayfada veya oyunda olursan ol, aklına takılanları bana sorabilirsin.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sohbet Geçmişini Göster
    for msg in st.session_state["coach_messages"]:
      if msg["role"] == "assistant":
        st.markdown(f"🤖 **Koç:** {msg['content']}")
      else:
        st.markdown(f"👤 **Sen:** {msg['content']}")

    # Soru Gönderme Formu
    with st.form("coach_chat_form", clear_on_submit=True):
      user_input = st.text_input("Koçuna bir şey sor:")
      submitted = st.form_submit_button("Gönder 🚀")
      if submitted and user_input:
        st.session_state["coach_messages"].append(
            {"role": "user", "content": user_input}
        )
        curr_s = st.session_state.get("selected_subject", "Genel")
        curr_u = st.session_state.get("selected_unit", "Genel Konu")
        prompt = (
            f"Sen 5. sınıf MEB müfredatı odaklı samimi ve bilgili bir öğretmen"
            f" koçusun. Öğrencinin seçtiği ders: {curr_s}, ünite: {curr_u}."
            f" Öğrencinin sorusu: {user_input}"
        )
        with st.spinner("Koçun düşünüyor..."):
          response = ai_generate_content(prompt)
          if response:
            st.session_state["coach_messages"].append(
                {"role": "assistant", "content": response}
            )
          else:
            st.session_state["coach_messages"].append(
                {
                    "role": "assistant",
                    "content": (
                        "Üzgünüm, şu anda yanıt oluşturamadım. Lütfen tekrar"
                        " dene."
                    ),
                }
            )
        st.rerun()

# --- AŞAMA 1: DERS SEÇİMİ ---
if st.session_state["selected_subject"] is None:
  st.markdown(
      "### 🌟 Lütfen Çalışmak İstediğiniz MEB Ders Kartına Tıklayın"
  )

  subjects = list(MEB_CURRICULUM.keys())
  cols = st.columns(3)

  for i, subj in enumerate(subjects):
    col_idx = i % 3
    data = MEB_CURRICULUM[subj]
    with cols[col_idx]:
      st.markdown(
          f"""
            <div class="card-box" style="background: {data['renk']};">
                <div style="font-size: 40px;">{data['ikon']}</div>
                <div style="margin-top: 10px;">{subj}</div>
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
  st.write("Çalışmak istediğiniz alt ünite kartına tıklayın:")

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
            <div class="card-box" style="background: {curr_data['renk']}; opacity: 0.95;">
                <div style="font-size: 20px;">📖 {unit_name}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(
          f"Seç: {unit_name}", key=f"unit_{idx}", use_container_width=True
      ):
        st.session_state["selected_unit"] = unit_name
        st.session_state["game_started"] = False
        st.rerun()

# --- AŞAMA 3: OYUN VE SORU MODELLERİ ---
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

  st.markdown("### 🎮 Lütfen Bir Oyun / Soru Modülü Kartına Tıklayın")

  games = [
      {
          "id": "balon",
          "isim": "🎈 Balon Patlatmaca",
          "renk": "linear-gradient(135deg, #ff416c, #ff4b2b)",
      },
      {
          "id": "sinav10",
          "isim": "🧠 5 Soruluk MEB Kazanım Oyunu",
          "renk": "linear-gradient(135deg, #2193b0, #6dd5ed)",
      },
      {
          "id": "dogruyanlis",
          "isim": "✅ Doğru / Yanlış Meydan Okuması",
          "renk": "linear-gradient(135deg, #38ef7d, #11998e)",
      },
      {
          "id": "kelime",
          "isim": "🔤 Kelime Avı (Harf Seçmeli Bulmaca)",
          "renk": "linear-gradient(135deg, #f2994a, #f2c94c)",
      },
      {
          "id": "acik",
          "isim": "✍️ Klasik Yazılı Simülatörü",
          "renk": "linear-gradient(135deg, #834d9b, #d04ed6)",
      },
  ]

  g_cols = st.columns(3)
  for g_idx, g_item in enumerate(games):
    with g_cols[g_idx % 3]:
      st.markdown(
          f"""
            <div class="card-box" style="background: {g_item['renk']};">
                <div>{g_item['isim']}</div>
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

# --- AŞAMA 4: OYUN VE SORU MODELLERİNİN ÇALIŞTIRILMASI ---
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
      with st.spinner(
          f"Yapay zeka {curr_subj} için 5 adet eğlenceli balon sorusu"
          " hazırlıyor..."
      ):
        prompt = f"""
                5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {curr_unit}.
                Balon patlatmaca oyunu için TAM 5 ADET çoktan seçmeli (4 şıklı: A, B, C, D) soru üret.
                Kesinlikle şu JSON formatında bir liste olarak ver:
                [
                  {{
                    "soru": "Soru metni buraya",
                    "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
                    "dogru_cevap": "A",
                    "aciklama": "Açıklama"
                  }}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            clean_res = re.sub(r"```json|```", "", res).strip()
            st.session_state["balloon_5_questions"] = json.loads(clean_res)
            st.session_state["game_started"] = False
            st.rerun()
          except Exception as e:
            st.error(f"Soru çözümleme hatası: {e}")

    if st.session_state["balloon_5_questions"]:
      if not st.session_state["game_started"]:
        st.success(
            "✅ Sorular Başarıyla Üretildi! Oyunu tam ekran başlatmak için"
            " aşağıdaki butona tıklayın."
        )
        if st.button(
            "✨ OYUNU BAŞLAT VE TAM EKRANA GEÇ 🎮",
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
            <head>
                <meta charset="UTF-8">
                <style>
                    body {
                        background: linear-gradient(135deg, #0f172a, #1e293b);
                        color: white;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        text-align: center;
                        margin: 0;
                        padding: 10px;
                        overflow: hidden;
                    }
                    #game-container {
                        position: relative;
                        width: 100%;
                        height: 540px;
                        background: radial-gradient(circle, #1e293b 0%, #0f172a 100%);
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
                        border: 3px solid #6366f1;
                    }
                    .header-bar {
                        display: flex;
                        justify-content: space-between;
                        padding: 14px 24px;
                        background: rgba(0,0,0,0.5);
                        font-size: 19px;
                        font-weight: bold;
                    }
                    .question-box {
                        font-size: 21px;
                        font-weight: bold;
                        padding: 16px 24px;
                        background: rgba(255, 255, 255, 0.08);
                        margin: 12px;
                        border-radius: 12px;
                        border-left: 6px solid #6366f1;
                    }
                    .balloon {
                        position: absolute;
                        width: 105px;
                        height: 125px;
                        border-radius: 50% 50% 50% 50% / 40% 40% 60% 60%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-weight: bold;
                        font-size: 14px;
                        text-align: center;
                        cursor: pointer;
                        box-shadow: inset -12px -12px 25px rgba(0,0,0,0.35), 0 6px 18px rgba(0,0,0,0.35);
                        animation: floatUp 8s linear infinite;
                        padding: 10px;
                        user-select: none;
                    }
                    .balloon::after {
                        content: "";
                        position: absolute;
                        bottom: -14px;
                        left: 50px;
                        width: 2px;
                        height: 16px;
                        background: #cbd5e1;
                    }
                    @keyframes floatUp {
                        0% { bottom: -140px; transform: scale(1); }
                        50% { transform: scale(1.06); }
                        100% { bottom: 520px; transform: scale(1); }
                    }
                    .feedback-overlay {
                        position: absolute;
                        top: 0; left: 0; width: 100%; height: 100%;
                        background: rgba(15, 23, 42, 0.9);
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        font-size: 28px;
                        z-index: 10;
                        display: none;
                    }
                </style>
            </head>
            <body>
                <div class="header-bar">
                    <span id="q-counter">Soru: 1 / 5</span>
                    <span id="timer" style="color: #f43f5e;">Süre: 50 sn</span>
                    <span id="score" style="color: #10b981;">Puan: 0</span>
                </div>
                
                <div id="game-container">
                    <div class="question-box" id="question-text">Soru yükleniyor...</div>
                    <div id="balloons-area" style="position:relative; width:100%; height:340px;"></div>
                    
                    <div class="feedback-overlay" id="overlay">
                        <div id="feedback-icon" style="font-size: 65px; margin-bottom: 12px;">🎉</div>
                        <div id="feedback-msg" style="font-size: 24px; padding: 0 20px;">Tebrikler!</div>
                    </div>
                </div>

                <script>
                    function goFullScreen() {
                        let elem = document.documentElement;
                        if (elem.requestFullscreen) {
                            elem.requestFullscreen().catch(() => {});
                        } else if (elem.webkitRequestFullscreen) {
                            elem.webkitRequestFullscreen();
                        } else if (elem.msRequestFullscreen) {
                            elem.msRequestFullscreen();
                        }
                    }
                    goFullScreen();

                    function exitFullScreen() {
                        if (document.exitFullscreen) {
                            document.exitFullscreen().catch(() => {});
                        } else if (document.webkitExitFullscreen) {
                            document.webkitExitFullscreen();
                        } else if (document.msExitFullscreen) {
                            document.msExitFullscreen();
                        }
                    }

                    const questions = """
            + questions_json
            + """;
                    let currentIdx = 0;
                    let score = 0;
                    let timeLeft = 50;
                    let timerInterval = null;
                    let gameActive = true;

                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

                    function playSuccessSound() {
                        if (audioCtx.state === 'suspended') audioCtx.resume();
                        let osc = audioCtx.createOscillator();
                        let gain = audioCtx.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(450, audioCtx.currentTime);
                        osc.frequency.exponentialRampToValueAtTime(850, audioCtx.currentTime + 0.3);
                        gain.gain.setValueAtTime(0.4, audioCtx.currentTime);
                        gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
                        osc.connect(gain);
                        gain.connect(audioCtx.destination);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 0.3);
                    }

                    function playWrongSound() {
                        if (audioCtx.state === 'suspended') audioCtx.resume();
                        let osc = audioCtx.createOscillator();
                        let gain = audioCtx.createGain();
                        osc.type = 'sawtooth';
                        osc.frequency.setValueAtTime(140, audioCtx.currentTime);
                        osc.frequency.setValueAtTime(90, audioCtx.currentTime + 0.15);
                        gain.gain.setValueAtTime(0.4, audioCtx.currentTime);
                        gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
                        osc.connect(gain);
                        gain.connect(audioCtx.destination);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 0.3);
                    }

                    function loadQuestion() {
                        if (currentIdx >= questions.length || currentIdx >= 5) {
                            endGame();
                            return;
                        }
                        gameActive = true;
                        timeLeft = 50;
                        document.getElementById('timer').innerText = "Süre: " + timeLeft + " sn";
                        document.getElementById('q-counter').innerText = "Soru: " + (currentIdx + 1) + " / 5";
                        
                        let q = questions[currentIdx];
                        document.getElementById('question-text').innerText = q.soru;
                        
                        let area = document.getElementById('balloons-area');
                        area.innerHTML = '';

                        let colors = ['linear-gradient(135deg, #ff416c, #ff4b2b)', 'linear-gradient(135deg, #2193b0, #6dd5ed)', 'linear-gradient(135deg, #11998e, #38ef7d)', 'linear-gradient(135deg, #f2994a, #f2c94c)'];
                        
                        q.secenekler.forEach((opt, idx) => {
                            let b = document.createElement('div');
                            b.className = 'balloon';
                            b.style.background = colors[idx % colors.length];
                            b.style.left = (10 + idx * 22) + '%';
                            b.style.animationDuration = (6 + Math.random() * 4) + 's';
                            b.style.animationDelay = (idx * 0.35) + 's';
                            b.innerText = opt;
                            
                            b.onclick = () => {
                                if (!gameActive) return;
                                gameActive = false;
                                clearInterval(timerInterval);
                                
                                let chosenLetter = opt.charAt(0).toUpperCase();
                                let correctLetter = q.dogru_cevap.charAt(0).toUpperCase();
                                
                                let overlay = document.getElementById('overlay');
                                let icon = document.getElementById('feedback-icon');
                                let msg = document.getElementById('feedback-msg');
                                overlay.style.display = 'flex';

                                if (chosenLetter === correctLetter) {
                                    playSuccessSound();
                                    score += 20;
                                    document.getElementById('score').innerText = "Puan: " + score;
                                    icon.innerText = "🎈💥 🎉";
                                    msg.innerHTML = "Tebrikler! Doğru Balon!<br><span style='font-size:16px; color:#10b981;'>" + q.aciklama + "</span>";
                                } else {
                                    playWrongSound();
                                    icon.innerText = "❌ ⚠️";
                                    msg.innerHTML = "Yanlış Balon!<br>Doğru Cevap: <b>" + q.dogru_cevap + "</b><br><span style='font-size:16px; color:#f43f5e;'>" + q.aciklama + "</span>";
                                }

                                setTimeout(() => {
                                    overlay.style.display = 'none';
                                    currentIdx++;
                                    loadQuestion();
                                }, 3500);
                            };
                            
                            area.appendChild(b);
                        });

                        if(timerInterval) clearInterval(timerInterval);
                        timerInterval = setInterval(() => {
                            timeLeft--;
                            document.getElementById('timer').innerText = "Süre: " + timeLeft + " sn";
                            if (timeLeft <= 0) {
                                clearInterval(timerInterval);
                                if(gameActive) {
                                    gameActive = false;
                                    playWrongSound();
                                    let overlay = document.getElementById('overlay');
                                    document.getElementById('feedback-icon').innerText = "⏰ ⚠️";
                                    document.getElementById('feedback-msg').innerText = "Süre Bitti!";
                                    overlay.style.display = 'flex';
                                    setTimeout(() => {
                                        overlay.style.display = 'none';
                                        currentIdx++;
                                        loadQuestion();
                                    }, 2500);
                                }
                            }
                        }, 1000);
                    }

                    function endGame() {
                        exitFullScreen();
                        let area = document.getElementById('game-container');
                        area.innerHTML = `
                            <div style="padding: 70px; font-size: 28px;">
                                🏆 <b>Oyun Tamamlandı!</b><br><br>
                                Toplam Puanınız: <span style="color: #10b981; font-size: 42px;">${score} / 100</span>
                            </div>
                        `;
                    }

                    loadQuestion();
                </script>
            </body>
            </html>
            """
        )
        st.components.v1.html(html_balloon_game, height=580)
        st.markdown("<br>", unsafe_allow_html=True)

        b_col1, b_col2 = st.columns(2)
        with b_col1:
          if st.button(
              "🔄 Tekrar Oyna",
              key="replay_balloon",
              use_container_width=True,
          ):
            st.session_state["game_started"] = False
            st.rerun()
        with b_col2:
          if st.button(
              "🏠 Ana Ekrana Dön",
              key="back_home_balloon",
              use_container_width=True,
          ):
            st.session_state["selected_subject"] = None
            st.session_state["selected_unit"] = None
            st.session_state["selected_game"] = None
            st.session_state["game_started"] = False
            st.rerun()

  # 2. 5 SORULUK MEB KAZANIM OYUNU
  elif curr_game == "sinav10":
    st.subheader(f"🧠 {curr_subj} — 5 Soruluk MEB Kazanım Yarışması")

    if (
        "quiz_5_data" not in st.session_state
        or st.session_state.get("q_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["quiz_5_data"] = None
      st.session_state["q_unit_key"] = (curr_subj, curr_unit)
      st.session_state["game_started"] = False

    if st.button("🚀 Kazanım Sorularını Üret", key="gen_5_quiz"):
      with st.spinner(f"Yapay zeka {curr_subj} için 5 kazanım sorusu üretiliyor..."):
        prompt = f"""
                5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {curr_unit}.
                Bu ünite için TAM 5 ADET çoktan seçmeli (4 şıklı) kazanım sorusu üret.
                JSON formatında liste olarak ver:
                [
                  {{"soru": "...", "secenekler": ["A)...", "B)...", "C)...", "D)..."], "dogru_cevap": "A", "aciklama": "..."}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["quiz_5_data"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.session_state["game_started"] = False
            st.rerun()
          except Exception:
            st.error("Biçim hatası.")

    if st.session_state["quiz_5_data"]:
      if not st.session_state["game_started"]:
        st.success(
            "✅ Yarışma Soruları Hazır! Tam ekranda başlatmak için aşağıdaki"
            " butona tıklayın."
        )
        if st.button(
            "✨ YARIŞMAYI BAŞLAT VE TAM EKRANA GEÇ 🧠",
            key="start_quiz_fullscreen",
            use_container_width=True,
        ):
          st.session_state["game_started"] = True
          st.rerun()
      else:
        q_json = json.dumps(
            st.session_state["quiz_5_data"], ensure_ascii=False
        )
        html_quiz_game = (
            """
            <!DOCTYPE html>
            <html lang="tr">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {
                        background: linear-gradient(135deg, #0f172a, #1e293b);
                        color: white;
                        font-family: 'Segoe UI', Tahoma, sans-serif;
                        text-align: center;
                        margin: 0;
                        padding: 10px;
                    }
                    .quiz-card {
                        background: rgba(255, 255, 255, 0.05);
                        border: 2px solid #38bdf8;
                        border-radius: 16px;
                        padding: 24px;
                        max-width: 750px;
                        margin: 0 auto;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                    }
                    .opt-btn {
                        display: block;
                        width: 100%;
                        padding: 14px;
                        margin: 12px 0;
                        background: linear-gradient(135deg, #0284c7, #0369a1);
                        color: white;
                        border: none;
                        border-radius: 10px;
                        font-size: 18px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: 0.2s;
                        text-align: left;
                    }
                    .opt-btn:hover { background: linear-gradient(135deg, #0369a1, #075985); transform: scale(1.01); }
                </style>
            </head>
            <body>
                <div class="quiz-card">
                    <div style="display: flex; justify-content: space-between; font-weight: bold; margin-bottom: 18px; font-size: 18px;">
                        <span id="q-num">Soru: 1 / 5</span>
                        <span id="q-timer" style="color: #f43f5e;">Süre: 60 sn</span>
                        <span id="q-score" style="color: #10b981;">Puan: 0</span>
                    </div>
                    <div id="q-text" style="font-size: 21px; font-weight: bold; margin-bottom: 22px; text-align: left;">Yükleniyor...</div>
                    <div id="options-area"></div>
                    <div id="q-feedback" style="margin-top: 18px; font-size: 18px; font-weight: bold;"></div>
                </div>

                <script>
                    function goFullScreen() {
                        let elem = document.documentElement;
                        if (elem.requestFullscreen) {
                            elem.requestFullscreen().catch(() => {});
                        } else if (elem.webkitRequestFullscreen) {
                            elem.webkitRequestFullscreen();
                        } else if (elem.msRequestFullscreen) {
                            elem.msRequestFullscreen();
                        }
                    }
                    goFullScreen();

                    function exitFullScreen() {
                        if (document.exitFullscreen) {
                            document.exitFullscreen().catch(() => {});
                        } else if (document.webkitExitFullscreen) {
                            document.webkitExitFullscreen();
                        } else if (document.msExitFullscreen) {
                            document.msExitFullscreen();
                        }
                    }

                    const quizData = """
            + q_json
            + """;
                    let qIdx = 0;
                    let totalScore = 0;
                    let timeRemaining = 60;
                    let qTimer = null;
                    let active = true;

                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    function playSound(type) {
                        if (audioCtx.state === 'suspended') audioCtx.resume();
                        let osc = audioCtx.createOscillator();
                        let gain = audioCtx.createGain();
                        osc.type = type === 'win' ? 'sine' : 'sawtooth';
                        osc.frequency.setValueAtTime(type === 'win' ? 500 : 150, audioCtx.currentTime);
                        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
                        gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
                        osc.connect(gain);
                        gain.connect(audioCtx.destination);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 0.25);
                    }

                    function loadQ() {
                        if (qIdx >= quizData.length || qIdx >= 5) {
                            exitFullScreen();
                            document.querySelector('.quiz-card').innerHTML = `
                                <h2>🏆 Yarışma Tamamlandı!</h2>
                                <p style="font-size: 24px;">Toplam Puanınız: <span style="color: #10b981; font-size: 40px;">${totalScore} / 100</span></p>
                            `;
                            return;
                        }
                        active = true;
                        timeRemaining = 60;
                        document.getElementById('q-num').innerText = "Soru: " + (qIdx + 1) + " / 5";
                        document.getElementById('q-timer').innerText = "Süre: 60 sn";
                        document.getElementById('q-feedback').innerText = "";

                        let q = quizData[qIdx];
                        document.getElementById('q-text').innerText = q.soru;
                        let area = document.getElementById('options-area');
                        area.innerHTML = '';

                        q.secenekler.forEach(opt => {
                            let btn = document.createElement('button');
                            btn.className = 'opt-btn';
                            btn.innerText = opt;
                            btn.onclick = () => checkAnswer(opt, q);
                            area.appendChild(btn);
                        });

                        if(qTimer) clearInterval(qTimer);
                        qTimer = setInterval(() => {
                            timeRemaining--;
                            document.getElementById('q-timer').innerText = "Süre: " + timeRemaining + " sn";
                            if(timeRemaining <= 0) {
                                clearInterval(qTimer);
                                if(active) {
                                    active = false;
                                    playSound('lose');
                                    document.getElementById('q-feedback').innerHTML = "<span style='color:#f43f5e;'>⏰ Süre Bitti! Doğru: " + q.dogru_cevap + "</span>";
                                    setTimeout(() => { qIdx++; loadQ(); }, 3000);
                                }
                            }
                        }, 1000);
                    }

                    function checkAnswer(chosen, q) {
                        if(!active) return;
                        active = false;
                        clearInterval(qTimer);

                        let chosenLetter = chosen.charAt(0).toUpperCase();
                        let correctLetter = q.dogru_cevap.charAt(0).toUpperCase();
                        let fb = document.getElementById('q-feedback');

                        if(chosenLetter === correctLetter) {
                            playSound('win');
                            totalScore += 20;
                            document.getElementById('q-score').innerText = "Puan: " + totalScore;
                            fb.innerHTML = "<span style='color:#10b981;'>🎉 Doğru! " + q.aciklama + "</span>";
                        } else {
                            playSound('lose');
                            fb.innerHTML = "<span style='color:#f43f5e;'>❌ Yanlış! Doğru Cevap: " + q.dogru_cevap + "<br>" + q.aciklama + "</span>";
                        }

                        setTimeout(() => { qIdx++; loadQ(); }, 3500);
                    }

                    loadQ();
                </script>
            </body>
            </html>
            """
        )
        st.components.v1.html(html_quiz_game, height=500)
        st.markdown("<br>", unsafe_allow_html=True)

        q_col1, q_col2 = st.columns(2)
        with q_col1:
          if st.button(
              "🔄 Tekrar Oyna", key="replay_quiz", use_container_width=True
          ):
            st.session_state["game_started"] = False
            st.rerun()
        with q_col2:
          if st.button(
              "🏠 Ana Ekrana Dön",
              key="back_home_quiz",
              use_container_width=True,
          ):
            st.session_state["selected_subject"] = None
            st.session_state["selected_unit"] = None
            st.session_state["selected_game"] = None
            st.session_state["game_started"] = False
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

    if st.button("🚀 Doğru/Yanlış Sorularını Üret", key="gen_dy"):
      with st.spinner("Yapay zeka 5 adet Doğru/Yanlış önermesi hazırlıyor..."):
        prompt = f"""
                5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {curr_unit}.
                Bu ünite için TAM 5 ADET Doğru veya Yanlış önermesi üret.
                JSON formatında liste olarak ver:
                [
                  {{"ifade": "Önerme metni", "cevap": "D", "aciklama": "Açıklama"}}
                ]
                (Not: cevap alanı sadece "D" veya "Y" olsun.)
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["dy_questions"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            st.error("Biçim hatası.")

    if st.session_state["dy_questions"]:
      with st.form("dy_form"):
        dy_answers = {}
        for idx, item in enumerate(st.session_state["dy_questions"]):
          st.markdown(f"**Önerme {idx+1}:** {item['ifade']}")
          dy_answers[idx] = st.radio(
              f"Seçiminiz ({idx+1}):", ["Doğru (D)", "Yanlış (Y)"], key=f"dy_{idx}"
          )
          st.markdown("---")

        if st.form_submit_button("Cevapları Kontrol Et"):
          score = 0
          for idx, item in enumerate(st.session_state["dy_questions"]):
            user_choice = dy_answers[idx][0]  # 'D' veya 'Y'
            correct_choice = item["cevap"].upper()
            if user_choice == correct_choice:
              st.success(
                  f"✅ Önerme {idx+1} Doğru! — Açıklama: {item['aciklama']}"
              )
              score += 20
            else:
              st.error(
                  f"❌ Önerme {idx+1} Yanlış. Doğru Cevap: **{correct_choice}** —"
                  f" Açıklama: {item['aciklama']}"
              )
          st.balloons()
          st.info(f"🏆 Toplam Puanınız: {score} / 100")
      st.markdown("<br>", unsafe_allow_html=True)
      if st.button("🏠 Ana Ekrana Dön", key="back_home_dy"):
        st.session_state["selected_subject"] = None
        st.session_state["selected_unit"] = None
        st.session_state["selected_game"] = None
        st.rerun()

  # 4. KELİME AVI (KUTUCUKLU HARF SEÇMELİ BULMACA)
  elif curr_game == "kelime":
    st.subheader(f"🔤 {curr_subj} — Kelime Avı (Harf Seçmeli Bulmaca)")

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
      with st.spinner("Yapay zeka bulmaca kelimelerini hazırlıyor..."):
        prompt = f"""
                5. Sınıf {curr_subj} {curr_unit} için TAM 5 ADET önemli anahtar kelime (en fazla 10 harfli Türkçe) ve tanım ipucu üret.
                JSON formatında liste olarak ver:
                [
                  {{"kelime": "TERİM", "ipucu": "Tanımı"}}
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
        current_item = items[p_idx]
        target_word = current_item["kelime"].upper()

        st.markdown(f"### 🎯 Bulmaca {p_idx+1} / {len(items)}")
        st.info(f"💡 **İpucu / Tanım:** {current_item['ipucu']}")

        if f"pool_{p_idx}" not in st.session_state:
          alphabet = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"
          pool = list(target_word)
          while len(pool) < max(8, len(target_word) + 3):
            pool.append(random.choice(alphabet))
          random.shuffle(pool)
          st.session_state[f"pool_{p_idx}"] = pool

        letter_pool = st.session_state[f"pool_{p_idx}"]

        st.markdown("#### Kelime Kutucukları:")
        user_guess = st.session_state["user_guess"]

        boxes_html = '<div style="display: flex; gap: 8px; justify-content: center; margin-bottom: 20px;">'
        for b_i in range(len(target_word)):
          char_in_box = user_guess[b_i] if b_i < len(user_guess) else ""
          boxes_html += (
              '<div style="width: 48px; height: 52px; border: 3px solid #6366f1;'
              " border-radius: 10px; display: flex; align-items: center;"
              " justify-content: center; font-size: 24px; font-weight: bold;"
              ' background: #1e1b4b; color: #38bdf8; box-shadow: 0 4px 12px'
              f' rgba(0,0,0,0.3);">{char_in_box}</div>'
          )
        boxes_html += "</div>"
        st.markdown(boxes_html, unsafe_allow_html=True)

        st.markdown(
            "#### 🔠 Harf Havuzu (Seçmek İçin Harflere Tıklayın):"
        )

        pool_cols = st.columns(len(letter_pool))
        for l_i, l_char in enumerate(letter_pool):
          with pool_cols[l_i]:
            if st.button(
                l_char, key=f"l_btn_{p_idx}_{l_i}_{l_char}", use_container_width=True
            ):
              if len(st.session_state["user_guess"]) < len(target_word):
                st.session_state["user_guess"].append(l_char)
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
          if st.button("⬅️ Son Harfi Sil", key=f"del_{p_idx}", use_container_width=True):
            if st.session_state["user_guess"]:
              st.session_state["user_guess"].pop()
              st.rerun()
        with col_b:
          if st.button("🔄 Tümünü Temizle", key=f"reset_{p_idx}", use_container_width=True):
            st.session_state["user_guess"] = []
            st.rerun()

        st.markdown("---")
        if st.button("✨ Tahmini Kontrol Et", key=f"check_{p_idx}", use_container_width=True):
          formed_word = "".join(st.session_state["user_guess"])
          if formed_word == target_word:
            st.success(f"🎉 Tebrikler! Doğru Kelime: {target_word}")
            st.session_state["puz_score"] += 20
            st.session_state["puz_idx"] += 1
            st.session_state["user_guess"] = []
            st.balloons()
            st.rerun()
          else:
            st.error(
                f"❌ Yanlış tahmin! (Oluşturduğunuz: {formed_word}). Tekrar"
                " deneyin."
            )
      else:
        st.markdown("## 🏆 Kelime Avı Tamamlandı!")
        st.markdown(
            f"Toplam Puanınız: **{st.session_state['puz_score']} / 100**"
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Tekrar Oyna", key="replay_puz", use_container_width=True):
          st.session_state["puz_items"] = None
          st.session_state["user_guess"] = []
          st.rerun()

      st.markdown("<br>", unsafe_allow_html=True)
      if st.button("🏠 Ana Ekrana Dön", key="back_home_puz", use_container_width=True):
        st.session_state["selected_subject"] = None
        st.session_state["selected_unit"] = None
        st.session_state["selected_game"] = None
        st.rerun()

  # 5. KLASİK YAZILI SİMÜLATÖRÜ
  elif curr_game == "acik":
    st.subheader(f"✍️ {curr_subj} — 5 Soruluk Klasik Yazılı Sınavı")

    if (
        "classic_exam" not in st.session_state
        or st.session_state.get("c_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["classic_exam"] = None
      st.session_state["c_unit_key"] = (curr_subj, curr_unit)

    if st.button("✨ Yazılı Sınavını Başlat (5 Soru)", key="gen_classic"):
      with st.spinner("Yapay zeka 5 adet yazılı klasik soru hazırlıyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                TAM 5 ADET açık uçlu yazılı sorusu ve ideal cevap anahtarlarını JSON liste formatında ver:
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
      with st.form("classic_exam_form"):
        user_answers = {}
        for idx, cq in enumerate(exam_list):
          st.markdown(f"**Soru {idx+1}:** {cq['soru']}")
          user_answers[idx] = st.text_area(
              f"Cevabınız ({idx+1}):", key=f"ans_{idx}"
          )
          st.markdown("---")

        if st.form_submit_button("Yazılı Kağıdını Yapay Zekaya Puanlat"):
          for idx, cq in enumerate(exam_list):
            ans = user_answers.get(idx, "")
            if ans.strip():
              with st.spinner(f"Soru {idx+1} inceleniyor..."):
                eval_res = ai_generate_content(
                    f"Sen 5. sınıf öğretmenisin. Soru: {cq['soru']}, İdeal Cevap:"
                    f" {cq['beklenen_cevap']}, Öğrencinin Cevabı: {ans}."
                    " Bu cevaba 0 ile 20 arası puan ver ve kısa açıklama yap."
                )
                st.info(f"**Soru {idx+1} Değerlendirmesi:**\n\n{eval_res}")
            else:
              st.warning(f"Soru {idx+1} boş bırakıldı (0 Puan).")
      st.markdown("<br>", unsafe_allow_html=True)
      if st.button("🏠 Ana Ekrana Dön", key="back_home_classic"):
        st.session_state["selected_subject"] = None
        st.session_state["selected_unit"] = None
        st.session_state["selected_game"] = None
        st.rerun()
