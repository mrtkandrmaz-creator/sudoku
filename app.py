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
      {"id": "sinav10", "isim": "🧠 10 Soruluk MEB Sınavı", "renk": "#1c83e1"},
      {"id": "acik", "isim": "✍️ Açık Uçlu Soru Köşesi", "renk": "#00cc96"},
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

  # 1. BALON PATLATMACA (5 SORU, 50 SANİYE, HAREKETLİ BALONLAR, SES EFEKTLERİ)
  if curr_game == "balon":
    st.subheader("🎈 Klasik Balon Patlatmaca Soru Oyunu")

    if (
        "balloon_5_questions" not in st.session_state
        or st.session_state.get("b_unit_key") != (curr_subj, curr_unit)
    ):
      st.session_state["balloon_5_questions"] = None
      st.session_state["b_unit_key"] = (curr_subj, curr_unit)

    if st.button(
        "🚀 5 Soruluk Balon Patlatmaca Oyununu Başlat", key="gen_5_balloons"
    ):
      with st.spinner(
          "Yapay zeka 5 adet balon patlatmaca sorusu hazırlıyor..."
      ):
        prompt = f"""
                5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {curr_unit}.
                Bu oyun için TAM 5 ADET çoktan seçmeli (4 şıklı: A, B, C, D) soru üret.
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

      # HTML5 / JS Animasyonlu, Sesli ve 50 Saniyeli Balon Oyunu Komponenti
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
                    }
                    #game-container {{
                        position: relative;
                        width: 100%;
                        height: 480px;
                        background: radial-gradient(circle, #22223b 0%, #11111d 100%);
                        border-radius: 16px;
                        overflow: hidden;
                        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
                        border: 3px solid #ff4b4b;
                    }
                    .header-bar {{
                        display: flex;
                        justify-content: space-between;
                        padding: 12px 20px;
                        background: rgba(0,0,0,0.4);
                        font-size: 18px;
                        font-weight: bold;
                    }
                    .question-box {{
                        font-size: 20px;
                        font-weight: bold;
                        padding: 15px 20px;
                        background: rgba(255, 255, 255, 0.1);
                        margin: 10px;
                        border-radius: 10px;
                        border-left: 5px solid #ff4b4b;
                    }
                    /* Hareketli Balonlar */
                    .balloon {{
                        position: absolute;
                        width: 90px;
                        height: 110px;
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
                    }
                    .balloon::after {{
                        content: "";
                        position: absolute;
                        bottom: -12px;
                        left: 42px;
                        width: 2px;
                        height: 15px;
                        background: #aaa;
                    }
                    @keyframes floatUp {{
                        0% {{ bottom: -120px; transform: scale(1); }}
                        50% {{ transform: scale(1.05); }}
                        100% {{ bottom: 500px; transform: scale(1); }}
                    }}
                    .feedback-overlay {{
                        position: absolute;
                        top: 0; left: 0; width: 100%; height: 100%;
                        background: rgba(0,0,0,0.8);
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
                    <span id="timer" style="color: #ff4b4b;">Süre: 50 sn</span>
                    <span id="score">Puan: 0</span>
                </div>
                
                <div id="game-container">
                    <div class="question-box" id="question-text">Soru yükleniyor...</div>
                    <div id="balloons-area" style="position:relative; width:100%; height:340px;"></div>
                    
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

                    // Web Audio API ses efektleri (Harici dosya gerektirmez)
                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

                    function playSuccessSound() {{
                        if (audioCtx.state === 'suspended') audioCtx.resume();
                        let osc = audioCtx.createOscillator();
                        let gain = audioCtx.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(400, audioCtx.currentTime);
                        osc.frequency.exponentialRampToValueAtTime(800, audioCtx.currentTime + 0.3);
                        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
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
                        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
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
                            b.style.left = (15 + idx * 20) + '%';
                            b.style.animationDuration = (6 + Math.random() * 4) + 's';
                            b.style.animationDelay = (idx * 0.5) + 's';
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
                                    msg.innerHTML = "Tebrikler! Doğru Patlatma!<br><span style='font-size:16px; color:#00cc96;'>" + q.aciklama + "</span>";
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

                        // 50 Saniye Sayacı
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

      st.components.v1.html(html_balloon_game, height=530)

  # 2. 10 SORULUK MEB SINAVI
  elif curr_game == "sinav10":
    st.subheader(f"🧠 10 Soruluk {curr_subj} MEB Kazanım Sınavı")
    if (
        "exam_10" not in st.session_state
        or st.session_state.get("ex_unit") != (curr_subj, curr_unit)
    ):
      st.session_state["exam_10"] = None
      st.session_state["ex_unit"] = (curr_subj, curr_unit)

    if st.button(
        "📝 Yapay Zeka ile 10 Soruluk Sınavı Başlat", key="gen_exam10"
    ):
      with st.spinner("Yapay zeka 10 adet sınav sorusu üretiyor..."):
        prompt = f"""
                5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {curr_unit}.
                Yapay zeka ile tam 10 adet çoktan seçmeli (4 şıklı) soru üret.
                JSON formatında liste olarak ver:
                [
                  {{"soru": "...", "secenekler": ["A)...", "B)...", "C)...", "D)..."], "dogru_cevap": "A", "aciklama": "..."}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["exam_10"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            st.error("Biçim hatası.")

    if st.session_state["exam_10"]:
      exam = st.session_state["exam_10"]
      with st.form("exam_form_10"):
        user_ans_10 = {}
        for q_i, q in enumerate(exam):
          st.markdown(f"**Soru {q_i+1}:** {q['soru']}")
          user_ans_10[q_i] = st.radio(
              f"Şıklar ({q_i+1}):",
              q["secenekler"],
              key=f"ex10_{q_i}",
              index=None,
          )
          st.markdown("---")

        if st.form_submit_button("Sınavı Tamamla ve Puanı Gör"):
          corrects = 0
          for q_i, q in enumerate(exam):
            ans = user_ans_10.get(q_i)
            if ans and ans.startswith(q["dogru_cevap"]):
              corrects += 1
          st.balloons()
          st.success(
              f"🎉 Sınav Puanı: {corrects * 10} / 100 ({corrects} Doğru)"
          )
          with st.expander("📖 Çözümler"):
            for q_i, q in enumerate(exam):
              st.info(
                  f"Soru {q_i+1} Cevap: **{q['dogru_cevap']}** —"
                  f" {q['aciklama']}"
              )

  # 3. AÇIK UÇLU SORU
  elif curr_game == "acik":
    st.subheader("✍️ Açık Uçlu Soru ve Yapay Zeka Değerlendirme")
    if (
        "open_q" not in st.session_state
        or st.session_state.get("op_unit") != (curr_subj, curr_unit)
    ):
      st.session_state["open_q"] = None
      st.session_state["op_unit"] = (curr_subj, curr_unit)

    if st.button("✨ Yapay Zeka ile Klasik Soru Getir", key="gen_open"):
      with st.spinner("Soru üretiliyor..."):
        prompt = f"""
                5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}.
                1 adet açık uçlu yazılı sorusu ve ideal cevap anahtarını JSON ver:
                {{"soru": "...", "beklenen_cevap": "..."}}
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["open_q"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            pass

    if st.session_state["open_q"]:
      oq = st.session_state["open_q"]
      st.markdown(f"**Soru:** {oq['soru']}")
      stu_ans = st.text_area("Cevabınız:")
      if st.button("Yapay Zekaya Değerlendir", key="eval_open"):
        if stu_ans:
          with st.spinner("Öğretmen yanıtınızı inceliyor..."):
            fb = ai_generate_content(
                f"Sen 5. sınıf öğretmenisin. Soru: {oq['soru']}, İdeal Cevap:"
                f" {oq['beklenen_cevap']}, Öğrencinin Cevabı: {stu_ans}."
                " Puanla ve açıkla."
            )
            if fb:
              st.success(fb)
        else:
          st.warning("Lütfen cevap yazın.")

  # 4. KELİME AVI & BULMACA
  elif curr_game == "kelime":
    st.subheader("🔤 Kelime Avı & Bulmaca")
    if (
        "puz_data" not in st.session_state
        or st.session_state.get("p_unit") != (curr_subj, curr_unit)
    ):
      st.session_state["puz_data"] = None
      st.session_state["p_unit"] = (curr_subj, curr_unit)

    if st.button("🔍 Yapay Zeka ile Kelimeleri Getir", key="gen_puz"):
      with st.spinner("Kavramlar üretiliyor..."):
        prompt = f"""
                5. Sınıf {curr_subj} {curr_unit} için AI destekli 3 önemli anahtar kelime üret.
                JSON formatında ver:
                [
                  {{"kelime": "TERİM", "ipucu": "Tanımı"}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["puz_data"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            pass

    if st.session_state["puz_data"]:
      with st.form("puz_form"):
        p_res = {}
        for idx, item in enumerate(st.session_state["puz_data"]):
          st.markdown(f"**İpucu:** {item['ipucu']}")
          p_res[idx] = st.text_input(f"Kelime {idx+1}:", key=f"p_{idx}")
        if st.form_submit_button("Kontrol Et"):
          for idx, item in enumerate(st.session_state["puz_data"]):
            if p_res.get(idx, "").strip().upper() == item["kelime"].upper():
              st.success(f"✅ Doğru! ({item['kelime']})")
            else:
              st.error(f"❌ Yanlış. Doğru: **{item['kelime']}**")

  # 5. YAPAY ZEKA KOÇUM
  elif curr_game == "koc":
    st.subheader(f"🤖 {curr_subj} Canlı Yapay Zeka Koçu")
    user_q = st.text_input(
        "Aklına takılan soruyu sor:", key="coach_input_box"
    )
    if st.button("Koçuma Sor", key="ask_coach"):
      if user_q:
        with st.spinner("Öğretmeniniz yanıtlıyor..."):
          ans = ai_generate_content(
              f"Sen 5. sınıf öğretmenisin. Ders: {curr_subj}, Ünite:"
              f" {curr_unit}. Soru: {user_q}"
          )
          if ans:
            st.success(ans)

<FollowUp/>
