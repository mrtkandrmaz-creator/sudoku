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
  """Streamlit secrets içindeki [api_keys] tablosunu doğrudan ve hatasız okur."""
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
  """Önce Groq, ardından Gemini modellerini dener."""
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
        "renk": "#ff4b4b",
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
        "renk": "#1c83e1",
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
        "renk": "#00cc96",
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
        "renk": "#ffa15a",
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
        "renk": "#ab63fa",
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
        "renk": "#ff6692",
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
        "renk": "#b6e880",
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

# --- 3. MEB TARZI BÜYÜK KART TASARIMI (CSS) ---
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #0056b3, #0080ff);
        padding: 20px;
        border-radius: 14px;
        color: white;
        text-align: center;
        font-weight: bold;
        font-size: 26px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .card-box {
        padding: 24px;
        border-radius: 14px;
        color: white;
        text-align: center;
        font-weight: bold;
        font-size: 22px;
        margin-bottom: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.18);
    }
    </style>
    <div class="main-header">🎒 MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi (Murat KANDIRMAZ)</div>
""",
    unsafe_allow_html=True,
)

# --- 4. SOL MENÜ (API DURUM GÖSTERGESİ) ---
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
    st.rerun()

# --- 5. SESSION STATE TANIMLARI ---
if "selected_subject" not in st.session_state:
  st.session_state["selected_subject"] = None
if "selected_unit" not in st.session_state:
  st.session_state["selected_unit"] = None
if "selected_game" not in st.session_state:
  st.session_state["selected_game"] = None

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
            <div class="card-box" style="background-color: {data['renk']};">
                <div style="font-size: 38px;">{data['ikon']}</div>
                <div style="margin-top: 8px;">{subj}</div>
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
    st.rerun()

  st.markdown("---")

  unit_cols = st.columns(2)
  for idx, unit_name in enumerate(curr_data["uniteler"]):
    u_col = unit_cols[idx % 2]
    with u_col:
      st.markdown(
          f"""
            <div class="card-box" style="background-color: {curr_data['renk']}; opacity: 0.95;">
                <div style="font-size: 20px;">📖 {unit_name}</div>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(
          f"Seç: {unit_name}", key=f"unit_{idx}", use_container_width=True
      ):
        st.session_state["selected_unit"] = unit_name
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
        <div style="background-color: {curr_data['renk']}; padding: 14px; border-radius: 10px; color: white; margin-bottom: 20px; font-weight: bold; font-size: 18px;">
            <b>Seçilen Ders:</b> {curr_subj} &nbsp;|&nbsp; <b>Ünite:</b> {curr_unit}
        </div>
    """,
      unsafe_allow_html=True,
  )

  if st.button("↩️ Ünite Değiştir", key="back_unit"):
    st.session_state["selected_unit"] = None
    st.rerun()

  st.markdown("### 🎮 Lütfen Bir Oyun / Soru Modülü Kartına Tıklayın")

  games = [
      {"id": "balon", "isim": "🎈 Balon Patlatmaca", "renk": "#ff6b6b"},
      {
          "id": "sinav10",
          "isim": "🧠 5 Soruluk MEB Kazanım Oyunu",
          "renk": "#1c83e1",
      },
      {"id": "acik", "isim": "✍️ Klasik Yazılı Simülatörü", "renk": "#00cc96"},
      {"id": "kelime", "isim": "🔤 Kelime Avı & Bulmaca", "renk": "#ffa15a"},
      {"id": "koc", "isim": "🤖 Yapay Zeka Koçum", "renk": "#ab63fa"},
  ]

  g_cols = st.columns(3)
  for g_idx, g_item in enumerate(games):
    with g_cols[g_idx % 3]:
      st.markdown(
          f"""
            <div class="card-box" style="background-color: {g_item['renk']};">
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
        st.rerun()

# --- AŞAMA 4: OYUN VE SORU MODELLERİNİN ÇALIŞTIRILMASI ---
else:
  curr_subj = st.session_state["selected_subject"]
  curr_unit = st.session_state["selected_unit"]
  curr_game = st.session_state["selected_game"]

  if st.button("⬅️ Oyun / Mod Seçimine Geri Dön", key="back_game"):
    st.session_state["selected_game"] = None
    st.rerun()

  st.markdown("---")

  # 1. BALON PATLATMACA (5 SORU, 50 SANİYE, HAREKETLİ BALONLAR, WEB AUDIO SESLERİ)
  if curr_game == "balon":
    st.subheader(f"🎈 {curr_subj} — Klasik Balon Patlatmaca Oyunu")

    if (
        "balloon_5_questions" not in st.session_state
        or st.session_state.get("b_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["balloon_5_questions"] = None
      st.session_state["b_unit_key"] = (curr_subj, curr_unit)

    if st.button("🚀 Balon Patlatmaca Oyununu Başlat", key="gen_5_balloons"):
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
            st.rerun()
          except Exception as e:
            st.error(f"Soru çözümleme hatası: {e}")

    if st.session_state["balloon_5_questions"]:
      questions_json = json.dumps(
          st.session_state["balloon_5_questions"], ensure_ascii=False
      )

      html_balloon_game = f"""
            <!DOCTYPE html>
            <html lang="tr">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        background: linear-gradient(135deg, #1e1e2f, #2a2a40);
                        color: white;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        text-align: center;
                        margin: 0;
                        padding: 10px;
                        overflow: hidden;
                    }}
                    #game-container {{
                        position: relative;
                        width: 100%;
                        height: 480px;
                        background: radial-gradient(circle, #22223b 0%, #11111d 100%);
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
                        border: 3px solid #ff4b4b;
                    }}
                    .header-bar {{
                        display: flex;
                        justify-content: space-between;
                        padding: 12px 20px;
                        background: rgba(0,0,0,0.4);
                        font-size: 18px;
                        font-weight: bold;
                    }}
                    .question-box {{
                        font-size: 20px;
                        font-weight: bold;
                        padding: 15px 20px;
                        background: rgba(255, 255, 255, 0.1);
                        margin: 10px;
                        border-radius: 10px;
                        border-left: 5px solid #ff4b4b;
                    }}
                    .balloon {{
                        position: absolute;
                        width: 95px;
                        height: 115px;
                        border-radius: 50% 50% 50% 50% / 40% 40% 60% 60%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-weight: bold;
                        font-size: 14px;
                        text-align: center;
                        cursor: pointer;
                        box-shadow: inset -10px -10px 20px rgba(0,0,0,0.3), 0 5px 15px rgba(0,0,0,0.3);
                        animation: floatUp 8s linear infinite;
                        padding: 10px;
                        user-select: none;
                    }}
                    .balloon::after {{
                        content: "";
                        position: absolute;
                        bottom: -12px;
                        left: 45px;
                        width: 2px;
                        height: 15px;
                        background: #aaa;
                    }}
                    @keyframes floatUp {{
                        0% {{ bottom: -130px; transform: scale(1); }}
                        50% {{ transform: scale(1.05); }}
                        100% {{ bottom: 500px; transform: scale(1); }}
                    }}
                    .feedback-overlay {{
                        position: absolute;
                        top: 0; left: 0; width: 100%; height: 100%;
                        background: rgba(0,0,0,0.85);
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        font-size: 28px;
                        z-index: 10;
                        display: none;
                    }}
                </style>
            </head>
            <body>
                <div class="header-bar">
                    <span id="q-counter">Soru: 1 / 5</span>
                    <span id="timer" style="color: #ff4b4b;">Süre: 50 sn</span>
                    <span id="score">Puan: 0</span>
                </div>
                
                <div id="game-container">
                    <div class="question-box" id="question-text">Soru yükleniyor...</div>
                    <div id="balloons-area" style="position:relative; width:100%; height:330px;"></div>
                    
                    <div class="feedback-overlay" id="overlay">
                        <div id="feedback-icon" style="font-size: 60px; margin-bottom: 10px;">🎉</div>
                        <div id="feedback-msg" style="font-size: 22px; padding: 0 20px;">Tebrikler!</div>
                    </div>
                </div>

                <script>
                    const questions = {questions_json};
                    let currentIdx = 0;
                    let score = 0;
                    let timeLeft = 50;
                    let timerInterval = null;
                    let gameActive = true;

                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

                    function playSuccessSound() {{
                        if (audioCtx.state === 'suspended') audioCtx.resume();
                        let osc = audioCtx.createOscillator();
                        let gain = audioCtx.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(400, audioCtx.currentTime);
                        osc.frequency.exponentialRampToValueAtTime(800, audioCtx.currentTime + 0.3);
                        gain.gain.setValueAtTime(0.4, audioCtx.currentTime);
                        gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
                        osc.connect(gain);
                        gain.connect(audioCtx.destination);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 0.3);
                    }}

                    function playWrongSound() {{
                        if (audioCtx.state === 'suspended') audioCtx.resume();
                        let osc = audioCtx.createOscillator();
                        let gain = audioCtx.createGain();
                        osc.type = 'sawtooth';
                        osc.frequency.setValueAtTime(150, audioCtx.currentTime);
                        osc.frequency.setValueAtTime(100, audioCtx.currentTime + 0.15);
                        gain.gain.setValueAtTime(0.4, audioCtx.currentTime);
                        gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
                        osc.connect(gain);
                        gain.connect(audioCtx.destination);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 0.3);
                    }}

                    function loadQuestion() {{
                        if (currentIdx >= questions.length || currentIdx >= 5) {{
                            endGame();
                            return;
                        }}
                        gameActive = true;
                        timeLeft = 50;
                        document.getElementById('timer').innerText = "Süre: " + timeLeft + " sn";
                        document.getElementById('q-counter').innerText = "Soru: " + (currentIdx + 1) + " / 5";
                        
                        let q = questions[currentIdx];
                        document.getElementById('question-text').innerText = q.soru;
                        
                        let area = document.getElementById('balloons-area');
                        area.innerHTML = '';

                        let colors = ['#ff4b4b', '#1c83e1', '#00cc96', '#ffa15a'];
                        
                        q.secenekler.forEach((opt, idx) => {{
                            let b = document.createElement('div');
                            b.className = 'balloon';
                            b.style.backgroundColor = colors[idx % colors.length];
                            b.style.left = (12 + idx * 21) + '%';
                            b.style.animationDuration = (6 + Math.random() * 4) + 's';
                            b.style.animationDelay = (idx * 0.4) + 's';
                            b.innerText = opt;
                            
                            b.onclick = () => {{
                                if (!gameActive) return;
                                gameActive = false;
                                clearInterval(timerInterval);
                                
                                let chosenLetter = opt.charAt(0).toUpperCase();
                                let correctLetter = q.dogru_cevap.charAt(0).toUpperCase();
                                
                                let overlay = document.getElementById('overlay');
                                let icon = document.getElementById('feedback-icon');
                                let msg = document.getElementById('feedback-msg');
                                overlay.style.display = 'flex';

                                if (chosenLetter === correctLetter) {{
                                    playSuccessSound();
                                    score += 20;
                                    document.getElementById('score').innerText = "Puan: " + score;
                                    icon.innerText = "🎈💥 🎉";
                                    msg.innerHTML = "Tebrikler! Doğru Balon!<br><span style='font-size:16px; color:#00cc96;'>" + q.aciklama + "</span>";
                                }} else {{
                                    playWrongSound();
                                    icon.innerText = "❌ ⚠️";
                                    msg.innerHTML = "Yanlış Balon!<br>Doğru Cevap: <b>" + q.dogru_cevap + "</b><br><span style='font-size:16px; color:#ff4b4b;'>" + q.aciklama + "</span>";
                                }}

                                setTimeout(() => {{
                                    overlay.style.display = 'none';
                                    currentIdx++;
                                    loadQuestion();
                                }, 3500);
                            }};
                            
                            area.appendChild(b);
                        }});

                        if(timerInterval) clearInterval(timerInterval);
                        timerInterval = setInterval(() => {{
                            timeLeft--;
                            document.getElementById('timer').innerText = "Süre: " + timeLeft + " sn";
                            if (timeLeft <= 0) {{
                                clearInterval(timerInterval);
                                if(gameActive) {{
                                    gameActive = false;
                                    playWrongSound();
                                    let overlay = document.getElementById('overlay');
                                    document.getElementById('feedback-icon').innerText = "⏰ ⚠️";
                                    document.getElementById('feedback-msg').innerText = "Süre Bitti!";
                                    overlay.style.display = 'flex';
                                    setTimeout(() => {{
                                        overlay.style.display = 'none';
                                        currentIdx++;
                                        loadQuestion();
                                    }, 2500);
                                }}
                            }}
                        }}, 1000);
                    }}

                    function endGame() {{
                        let area = document.getElementById('game-container');
                        area.innerHTML = `
                            <div style="padding: 60px; font-size: 28px;">
                                🏆 <b>Oyun Tamamlandı!</b><br><br>
                                Toplam Puanınız: <span style="color: #00cc96; font-size: 38px;">${{score}} / 100</span><br><br>
                                <button onclick="location.reload()" style="padding: 12px 24px; font-size: 20px; background: #00cc96; color: white; border: none; border-radius: 8px; cursor: pointer;">Tekrar Oyna 🔄</button>
                            </div>
                        `;
                    }}

                    loadQuestion();
                </script>
            </body>
            </html>
            """
      st.components.v1.html(html_balloon_game, height=535)

  # 2. 5 SORULUK MEB KAZANIM OYUNU (60 Saniye Süreli İnteraktif Bilgi Yarışması)
  elif curr_game == "sinav10":
    st.subheader(f"🧠 {curr_subj} — 5 Soruluk MEB Kazanım Yarışması")

    if (
        "quiz_5_data" not in st.session_state
        or st.session_state.get("q_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["quiz_5_data"] = None
      st.session_state["q_unit_key"] = (curr_subj, curr_unit)

    if st.button("🚀 Kazanım Yarışmasını Başlat", key="gen_5_quiz"):
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
            st.rerun()
          except Exception:
            st.error("Biçim hatası.")

    if st.session_state["quiz_5_data"]:
      q_json = json.dumps(
          st.session_state["quiz_5_data"], ensure_ascii=False
      )
      html_quiz_game = f"""
            <!DOCTYPE html>
            <html lang="tr">
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        background: linear-gradient(135deg, #0f172a, #1e293b);
                        color: white;
                        font-family: 'Segoe UI', Tahoma, sans-serif;
                        text-align: center;
                        margin: 0;
                        padding: 10px;
                    }}
                    .quiz-card {{
                        background: rgba(255, 255, 255, 0.05);
                        border: 2px solid #1c83e1;
                        border-radius: 14px;
                        padding: 20px;
                        max-width: 700px;
                        margin: 0 auto;
                        box-shadow: 0 6px 20px rgba(0,0,0,0.4);
                    }}
                    .opt-btn {{
                        display: block;
                        width: 100%;
                        padding: 12px;
                        margin: 10px 0;
                        background: #1c83e1;
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-size: 18px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: 0.2s;
                        text-align: left;
                    }}
                    .opt-btn:hover {{ background: #0056b3; transform: scale(1.01); }}
                </style>
            </head>
            <body>
                <div class="quiz-card">
                    <div style="display: flex; justify-content: space-between; font-weight: bold; margin-bottom: 15px;">
                        <span id="q-num">Soru: 1 / 5</span>
                        <span id="q-timer" style="color: #ff4b4b;">Süre: 60 sn</span>
                        <span id="q-score">Puan: 0</span>
                    </div>
                    <div id="q-text" style="font-size: 20px; font-weight: bold; margin-bottom: 20px; text-align: left;">Yükleniyor...</div>
                    <div id="options-area"></div>
                    <div id="q-feedback" style="margin-top: 15px; font-size: 18px; font-weight: bold;"></div>
                </div>

                <script>
                    const quizData = {q_json};
                    let qIdx = 0;
                    let totalScore = 0;
                    let timeRemaining = 60;
                    let qTimer = null;
                    let active = true;

                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    function playSound(type) {{
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
                    }}

                    function loadQ() {{
                        if (qIdx >= quizData.length || qIdx >= 5) {{
                            document.querySelector('.quiz-card').innerHTML = `
                                <h2>🏆 Yarışma Tamamlandı!</h2>
                                <p style="font-size: 24px;">Toplam Puanınız: <span style="color: #00cc96;">${{totalScore}} / 100</span></p>
                                <button onclick="location.reload()" class="opt-btn" style="text-align:center; background:#00cc96;">Yeniden Oyna 🔄</button>
                            `;
                            return;
                        }}
                        active = true;
                        timeRemaining = 60;
                        document.getElementById('q-num').innerText = "Soru: " + (qIdx + 1) + " / 5";
                        document.getElementById('q-timer').innerText = "Süre: 60 sn";
                        document.getElementById('q-feedback').innerText = "";

                        let q = quizData[qIdx];
                        document.getElementById('q-text').innerText = q.soru;
                        let area = document.getElementById('options-area');
                        area.innerHTML = '';

                        q.secenekler.forEach(opt => {{
                            let btn = document.createElement('button');
                            btn.className = 'opt-btn';
                            btn.innerText = opt;
                            btn.onclick = () => checkAnswer(opt, q);
                            area.appendChild(btn);
                        }});

                        if(qTimer) clearInterval(qTimer);
                        qTimer = setInterval(() => {{
                            timeRemaining--;
                            document.getElementById('q-timer').innerText = "Süre: " + timeRemaining + " sn";
                            if(timeRemaining <= 0) {{
                                clearInterval(qTimer);
                                if(active) {{
                                    active = false;
                                    playSound('lose');
                                    document.getElementById('q-feedback').innerHTML = "<span style='color:#ff4b4b;'>⏰ Süre Bitti! Doğru: " + q.dogru_cevap + "</span>";
                                    setTimeout(() => {{ qIdx++; loadQ(); }}, 3000);
                                }}
                            }}
                        }}, 1000);
                    }}

                    function checkAnswer(chosen, q) {{
                        if(!active) return;
                        active = false;
                        clearInterval(qTimer);

                        let chosenLetter = chosen.charAt(0).toUpperCase();
                        let correctLetter = q.dogru_cevap.charAt(0).toUpperCase();
                        let fb = document.getElementById('q-feedback');

                        if(chosenLetter === correctLetter) {{
                            playSound('win');
                            totalScore += 20;
                            document.getElementById('q-score').innerText = "Puan: " + totalScore;
                            fb.innerHTML = "<span style='color:#00cc96;'>🎉 Doğru! " + q.aciklama + "</span>";
                        }} else {{
                            playSound('lose');
                            fb.innerHTML = "<span style='color:#ff4b4b;'>❌ Yanlış! Doğru Cevap: " + q.dogru_cevap + "<br>" + q.aciklama + "</span>";
                        }}

                        setTimeout(() => {{ qIdx++; loadQ(); }}, 3500);
                    }}

                    loadQ();
                </script>
            </body>
            </html>
            """
      st.components.v1.html(html_quiz_game, height=450)

  # 3. KLASİK YAZILI SİMÜLATÖRÜ (5 Açık Uçlu Soru ve AI Değerlendirme)
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
          total_points = 0
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

  # 4. KELİME AVI & BULMACA (5 Kavram Bulmacası)
  elif curr_game == "kelime":
    st.subheader(f"🔤 {curr_subj} — 5 Soruluk Kelime Avı & Bulmaca")

    if (
        "puz_5_data" not in st.session_state
        or st.session_state.get("p_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["puz_5_data"] = None
      st.session_state["p_unit_key"] = (curr_subj, curr_unit)

    if st.button("🔍 Kelime Bulmacasını Başlat", key="gen_puz5"):
      with st.spinner("Yapay zeka 5 önemli kavram bulmacası hazırlıyor..."):
        prompt = f"""
                5. Sınıf {curr_subj} {curr_unit} için TAM 5 ADET önemli anahtar kelime ve tanım ipucu üret.
                JSON formatında liste olarak ver:
                [
                  {{"kelime": "TERİM", "ipucu": "Tanımı"}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["puz_5_data"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            pass

    if st.session_state["puz_5_data"]:
      with st.form("puz_5_form"):
        p_res = {}
        for idx, item in enumerate(st.session_state["puz_5_data"]):
          st.markdown(f"**Bulmaca İpucu {idx+1}:** {item['ipucu']}")
          p_res[idx] = st.text_input(
              f"Kelime {idx+1} Tahmini:", key=f"puz_in_{idx}"
          )
          st.markdown("---")

        if st.form_submit_button("Bulmacaları Kontrol Et"):
          correct_count = 0
          for idx, item in enumerate(st.session_state["puz_5_data"]):
            user_input = p_res.get(idx, "").strip().upper()
            target = item["kelime"].upper()
            if user_input == target:
              st.success(f"✅ Soru {idx+1} Doğru! ({target})")
              correct_count += 20
            else:
              st.error(
                  f"❌ Soru {idx+1} Yanlış. Doğru Cevap: **{item['kelime']}**"
              )
          st.balloons()
          st.info(f"🏆 Toplam Kelime Avı Puanı: {correct_count} / 100")

  # 5. YAPAY ZEKA KOÇUM
  elif curr_game == "koc":
    st.subheader(f"🤖 {curr_subj} Canlı Yapay Zeka Öğretmen Koçu")
    user_q = st.text_input("Aklına takılan soruyu sor:")
    if st.button("Koçuma Sor", key="ask_coach"):
      if user_q:
        with st.spinner("Öğretmeniniz yanıtlıyor..."):
          ans = ai_generate_content(
              f"Sen 5. sınıf öğretmenisin. Ders: {curr_subj}, Ünite:"
              f" {curr_unit}. Öğrencinin Sorusu: {user_q}"
          )
          if ans:
            st.success(ans)

<FollowUp/>
