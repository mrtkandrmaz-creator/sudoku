import json
import os
import random
import re
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="MEB 5. Sınıf İnteraktif Öğrenme Merkezi",
    page_icon="🎒",
    layout="wide",
)

# --- 1. KUSURSUZ VE GÜÇLENDİRİLMİŞ API MOTORU ---


def get_all_api_keys():
  """Streamlit secrets, environment variables veya manuel girişleri tarar."""
  gemini_keys = []
  groq_keys = []

  # 1. Streamlit Secrets
  try:
    if hasattr(st, "secrets") and st.secrets:
      for key, val in st.secrets.items():
        key_upper = str(key).upper()
        if val and isinstance(val, str) and len(val.strip()) > 5:
          if "GEMINI" in key_upper or "GOOGLE" in key_upper:
            if val.strip() not in gemini_keys:
              gemini_keys.append(val.strip())
          elif "GROQ" in key_upper:
            if val.strip() not in groq_keys:
              groq_keys.append(val.strip())
  except Exception:
    pass

  # 2. Ortam Değişkenleri
  for env_key, env_val in os.environ.items():
    env_upper = env_key.upper()
    if env_val and isinstance(env_val, str) and len(env_val.strip()) > 5:
      if (
          "GEMINI" in env_upper or "GOOGLE" in env_upper
      ) and env_val.strip() not in gemini_keys:
        gemini_keys.append(env_val.strip())
      elif "GROQ" in env_upper and env_val.strip() not in groq_keys:
        groq_keys.append(env_val.strip())

  # 3. Session State (Arayüzden manuel girildiyse)
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
  """Yapay zeka modelleri arasında yedekli (failover) çağrı yapar."""
  # 1. Önce Gemini dene
  if has_gemini and gemini_keys:
    for g_key in gemini_keys:
      try:
        genai.configure(api_key=g_key)
        for model_name in [
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

  # 2. Gemini başarısızsa Groq dene
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

# --- 3. MEB TARZI MODERN ARAYÜZ (CSS) ---
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
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
        border: none;
        width: 100%;
    }
    </style>
    <div class="main-header">🎒 MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi (Murat KANDIRMAZ)</div>
""",
    unsafe_allow_html=True,
)

# --- 4. SOL MENÜ & API KONTROL PANELİ ---
with st.sidebar:
  st.subheader("⚙️ Sistem & API Durumu")
  if not gemini_keys and not groq_keys:
    st.warning("⚠️ Otomatik API bulunamadı. Geçici anahtar girin:")
    m_key = st.text_input(
        "Gemini (AIza...) veya Groq (gsk_...)", type="password"
    )
    if m_key:
      if m_key.startswith("AIza"):
        st.session_state["manual_gemini"] = m_key
        has_gemini = True
        st.success("Gemini eklendi!")
        st.rerun()
      elif m_key.startswith("gsk_"):
        st.session_state["manual_groq"] = m_key
        has_groq = True
        st.success("Groq eklendi!")
        st.rerun()
  else:
    st.success("✅ Yapay Zeka Devrede")

  st.markdown("---")
  st.markdown("### 📌 Navigasyon")
  nav_choice = st.radio(
      "Gitmek İstediğiniz Yer:",
      ["🏠 Ana Sayfa (Ders Seçim Paneli)", "📊 İlerleme ve Rozetlerim"],
  )

# --- 5. ANA SAYFA: MEB TARZI RENKLİ DERS KUTULARI (DASHBOARD) ---
if nav_choice == "🏠 Ana Sayfa (Ders Seçim Paneli)":
  if (
      "selected_subject" not in st.session_state
      or "selected_unit" not in st.session_state
  ):
    st.session_state["selected_subject"] = "Türkçe"
    st.session_state["selected_unit"] = MEB_CURRICULUM["Türkçe"]["uniteler"][0]

  st.markdown(
      "### 🌟 Ders Seçin ve Eğlenceli Oyun Moduyla Öğrenmeye Başlayın!"
  )
  st.markdown(
      "Aşağıdaki MEB derslerinden birini seçerek ünite bazlı oyunlara"
      " geçiş yapabilirsiniz."
  )

  # 3 Sütunlu Renkli Dashboard Kutuları
  subjects = list(MEB_CURRICULUM.keys())
  cols = st.columns(3)

  for i, subj in enumerate(subjects):
    col_idx = i % 3
    data = MEB_CURRICULUM[subj]
    with cols[col_idx]:
      # Renkli HTML Kutucuk Kartı
      st.markdown(
          f"""
                <div style="background-color: {data['renk']}; padding: 20px; border-radius: 12px; color: white; text-align: center; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 style="margin:0; font-size: 36px;">{data['ikon']}</h1>
                    <h3 style="margin: 10px 0 0 0; color: white;">{subj}</h3>
                </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(f"📚 {subj} Seç", key=f"btn_{subj}"):
        st.session_state["selected_subject"] = subj
        st.session_state["selected_unit"] = data["uniteler"][0]
        st.rerun()

  st.markdown("---")

  # Seçilen Dersin Ünite ve Oyun Alanı
  curr_subj = st.session_state["selected_subject"]
  curr_data = MEB_CURRICULUM[curr_subj]

  st.markdown(f"### 🎯 Seçilen Ders: {curr_data['ikon']} {curr_subj}")

  selected_unit = st.selectbox(
      "📖 Ünite veya Konu Seçin:",
      curr_data["uniteler"],
      index=curr_data["uniteler"].index(st.session_state["selected_unit"])
      if st.session_state["selected_unit"] in curr_data["uniteler"]
      else 0,
  )
  st.session_state["selected_unit"] = selected_unit

  # Oyun Modu Sekmeleri
  st.markdown("### 🎮 Oyun ve Soru Modelleri")
  game_mode = st.tabs([
      "🎈 Balon Patlatmaca",
      "🧠 10 Soruluk MEB Sınavı",
      "✍️ Açık Uçlu Soru Köşesi",
      "🔤 Kelime Avı & Bulmaca",
      "🤖 Yapay Zeka Koçum",
  ])

  # --- OYUN MODU 1: BALON PATLATMACA ---
  with game_mode[0]:
    st.subheader("🎈 Balon Patlatmaca Soru Oyunu")
    st.write(
        "Sorunun doğru cevabını içeren balonu patlat, puanları kap! MEB"
        " eğitsel oyun tarzı."
    )

    if (
        "balloon_data" not in st.session_state
        or st.session_state.get("b_unit") != (curr_subj, selected_unit)
    ):
      st.session_state["balloon_data"] = None
      st.session_state["b_unit"] = (curr_subj, selected_unit)

    if st.button("🚀 Balonları Hazırla"):
      if not gemini_keys and not groq_keys:
        st.warning("Lütfen sol menüden API anahtarı girin.")
      else:
        with st.spinner("Balonlar şişiriliyor, sorular hazırlanıyor..."):
          prompt = f"""
                    5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {selected_unit}.
                    Balon patlatmaca oyunu için 1 adet eğlenceli soru ve 4 şık (A, B, C, D) hazırla.
                    JSON formatında ver:
                    {{"soru": "Soru metni", "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."], "dogru_cevap": "A", "aciklama": "Açıklama"}}
                    """
          res = ai_generate_content(prompt)
          if res:
            try:
              cleaned = re.sub(r"```json|```", "", res).strip()
              st.session_state["balloon_data"] = json.loads(cleaned)
              st.rerun()
            except Exception:
              st.error("Veri işlenemedi.")

    if st.session_state["balloon_data"]:
      b_q = st.session_state["balloon_data"]
      st.markdown(f"### ❓ {b_q['soru']}")

      b_cols = st.columns(2)
      for idx, opt in enumerate(b_q["secenekler"]):
        with b_cols[idx % 2]:
          if st.button(f"🎈 {opt}", key=f"ball_{idx}"):
            if opt.startswith(b_q["dogru_cevap"]):
              st.balloons()
              st.success(f"🎉 Tebrikler! Doğru balonu patlattın! {b_q['aciklama']}")
            else:
              st.error(
                  f"💥 Yanlış balon! Doğru cevap **{b_q['dogru_cevap']}**"
                  f" olacaktı. {b_q['aciklama']}"
              )

  # --- OYUN MODU 2: 10 SORULUK MEB SINAVI ---
  with game_mode[1]:
    st.subheader(f"🧠 10 Soruluk {curr_subj} MEB Kazanım Sınavı")
    st.write(
        "Gerçek yazılı sınavı provası için 10 soruluk kapsamlı test çözün."
    )

    if (
        "exam_10" not in st.session_state
        or st.session_state.get("exam_unit") != (curr_subj, selected_unit)
    ):
      st.session_state["exam_10"] = None
      st.session_state["exam_unit"] = (curr_subj, selected_unit)

    if st.button("📝 10 Soruluk Sınavı Başlat"):
      if not gemini_keys and not groq_keys:
        st.warning("Lütfen sol menüden API anahtarı girin.")
      else:
        with st.spinner(
            "Yapay zeka 10 adet MEB kalitesinde soru hazırlıyor..."
        ):
          prompt = f"""
                    5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {selected_unit}.
                    Lütfen tam 10 adet çoktan seçmeli, 4 şıklı (A, B, C, D) sınav sorusu hazırla.
                    Yanıtı kesinlikle şu JSON formatında bir liste olarak ver:
                    [
                      {{
                        "soru": "Soru metni",
                        "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
                        "dogru_cevap": "A",
                        "aciklama": "Açıklama"
                      }}
                    ]
                    """
          res = ai_generate_content(prompt)
          if res:
            try:
              cleaned = re.sub(r"```json|```", "", res).strip()
              st.session_state["exam_10"] = json.loads(cleaned)
              st.rerun()
            except Exception:
              st.error("Sınav soruları oluşturulurken biçim hatası oluştu.")

    if st.session_state["exam_10"]:
      exam = st.session_state["exam_10"]
      with st.form("exam_10_form"):
        user_ans_10 = {}
        for q_i, q in enumerate(exam):
          st.markdown(f"**Soru {q_i+1}:** {q['soru']}")
          user_ans_10[q_i] = st.radio(
              f"Şıklar (Soru {q_i+1}):",
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
              f"🎉 Sınav Sonucu: {corrects * 10} / 100 Puan ({corrects} Doğru,"
              f" {10-corrects} Yanlış)"
          )
          with st.expander("📖 Çözüm ve Açıklamalar"):
            for q_i, q in enumerate(exam):
              st.markdown(
                  f"**Soru {q_i+1}:** Doğru Cevap: **{q['dogru_cevap']}**"
              )
              st.info(q["aciklama"])

  # --- OYUN MODU 3: AÇIK UÇLU SORU KÖŞESİ ---
  with game_mode[2]:
    st.subheader("✍️ Açık Uçlu Soru ve Yapay Zeka Değerlendirme")
    st.write(
        "Yazılılarda karşınıza çıkabilecek klasik açık uçlu soruları yanıtlayın,"
        " yapay zeka öğretmen puanlasın!"
    )

    if (
        "open_q" not in st.session_state
        or st.session_state.get("open_unit") != (curr_subj, selected_unit)
    ):
      st.session_state["open_q"] = None
      st.session_state["open_unit"] = (curr_subj, selected_unit)

    if st.button("✨ Açık Uçlu Soru Getir"):
      if not gemini_keys and not groq_keys:
        st.warning("Lütfen sol menüden API anahtarı girin.")
      else:
        with st.spinner("Klasik soru hazırlanıyor..."):
          prompt = f"""
                    5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {selected_unit}.
                    1 adet klasik (açık uçlu) yazılı sorusu ve ideal cevap anahtarını hazırla.
                    JSON formatında ver:
                    {{"soru": "Klasik soru metni?", "beklenen_cevap": "Öğrencinin yazması gereken temel anahtar kelimeler ve açıklama"}}
                    """
          res = ai_generate_content(prompt)
          if res:
            try:
              cleaned = re.sub(r"```json|```", "", res).strip()
              st.session_state["open_q"] = json.loads(cleaned)
              st.rerun()
            except Exception:
              st.error("Hata oluştu.")

    if st.session_state["open_q"]:
      oq = st.session_state["open_q"]
      st.markdown(f"**Soru:** {oq['soru']}")
      student_text = st.text_area(
          "Cevabınızı buraya yazın:", placeholder="Kendi cümlelerinizle açıklayın..."
      )

      if st.button("Cevabımı Yapay Zekaya Değerlendir"):
        if student_text:
          with st.spinner("Öğretmen yanıtınızı inceliyor..."):
            eval_prompt = f"""
                        Sen 5. sınıf öğretmenisin.
                        Soru: {oq['soru']}
                        İdeal Cevap: {oq['beklenen_cevap']}
                        Öğrencinin Yanıtı: {student_text}
                        
                        Lütfen öğrencinin cevabını 100 üzerinden puanla, eksiklerini sevecen bir dille açıkla.
                        """
            feedback = ai_generate_content(eval_prompt)
            if feedback:
              st.success(feedback)
            else:
              st.error("Değerlendirilemedi.")
        else:
          st.warning("Lütfen bir şeyler yazın.")

  # --- OYUN MODU 4: KELİME AVI & BULMACA ---
  with game_mode[3]:
    st.subheader("🔤 Kelime Avı & Bulmaca")
    if (
        "puz_data" not in st.session_state
        or st.session_state.get("puz_unit") != (curr_subj, selected_unit)
    ):
      st.session_state["puz_data"] = None
      st.session_state["puz_unit"] = (curr_subj, selected_unit)

    if st.button("🔍 Kelime Bulmaca Üret"):
      if not gemini_keys and not groq_keys:
        st.warning("API anahtarı gerekli.")
      else:
        with st.spinner("Kelimeler seçiliyor..."):
          prompt = f"5. Sınıf {curr_subj} {selected_unit} için 3 önemli anahtar kelime ve tanımını JSON ver: [{{\"kelime\":\"TERİM\",\"ipucu\":\"Tanım\"}}]"
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
      with st.form("puz_f"):
        p_ans = {}
        for idx, item in enumerate(st.session_state["puz_data"]):
          st.markdown(f"**İpucu:** {item['ipucu']}")
          p_ans[idx] = st.text_input(f"Cevap {idx+1}:", key=f"p_{idx}")
        if st.form_submit_button("Kontrol Et"):
          for idx, item in enumerate(st.session_state["puz_data"]):
            if p_ans.get(idx, "").strip().upper() == item["kelime"].upper():
              st.success(f"✅ Doğru! ({item['kelime']})")
            else:
              st.error(
                  f"❌ Yanlış. Doğru: **{item['kelime']}**"
              )

  # --- OYUN MODU 5: YAPAY ZEKA KOÇUM ---
  with game_mode[4]:
    st.subheader(f"🤖 {curr_subj} Canlı Yapay Zeka Koçu")
    q_txt = st.text_input(
        "Anlamadığın bir yer mi oldu? Bana sor:",
        placeholder="Örn: Bu konuyu bana hikaye gibi anlat.",
    )
    if st.button("Soruyu Sor"):
      if q_txt:
        with st.spinner("Öğretmeniniz yanıtlıyor..."):
          ans = ai_generate_content(
              f"Sen 5. sınıf öğretmenisin. Ders: {curr_subj}, Soru: {q_txt}"
          )
          if ans:
            st.success(ans)

# --- İLERLEME VE ROZETLERİM ---
elif nav_choice == "📊 İlerleme ve Rozetlerim":
  st.subheader("📊 Öğrenci İlerleme Paneli ve Kazanım Rozetleri")
  st.info(
      "Harika gidiyorsun Murat! Çözdüğün testler ve oynadığın oyunlarla rozetleri"
      " topla."
  )

  c1, c2, c3 = st.columns(3)
  with c1:
    st.metric("Çözülen Soru Sayısı", "45", "+12 bugün")
  with c2:
    st.metric("Tamamlanan Üniteler", "3", "Harika")
  with c3:
    st.metric("Kazanılan Rozetler", "🏆 4 Rozet", "Altın Öğrenci")

  st.markdown("### 🏅 Kazanılan Rozetler")
  st.write(
      "⭐ **Kelime Avcısı** | 🎯 **10'da 10 Tam İsabet** | 🎈 **Balon Patlatma"
      " Ustası** | 🚀 **MEB Kaşifi**"
  )
