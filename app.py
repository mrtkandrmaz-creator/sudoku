import json
import os
import random
import re
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="MEB Tarzı İnteraktif Oyunla Öğrenme Platformu",
    page_icon="🎮",
    layout="wide",
)

# --- 1. KUSURSUZ VE GARANTİLİ API ANAHTARI TARAMA MOTORU ---


def get_all_api_keys():
  """Streamlit secrets, ortam değişkenleri (environment variables) ve

  yerel os üzerinden anahtarları esnek ve garantili toplar.
  """
  gemini_keys = []
  groq_keys = []

  # 1. YÖNTEM: Streamlit Secrets kontrolü
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

  # 2. YÖNTEM: Sistem Ortam Değişkenleri (Environment Variables / .env) kontrolü
  for env_key, env_val in os.environ.items():
    env_upper = env_key.upper()
    if env_val and isinstance(env_val, str) and len(env_val.strip()) > 5:
      if (
          "GEMINI" in env_upper or "GOOGLE" in env_upper
      ) and env_val.strip() not in gemini_keys:
        gemini_keys.append(env_val.strip())
      elif "GROQ" in env_upper and env_val.strip() not in groq_keys:
        groq_keys.append(env_val.strip())

  return gemini_keys, groq_keys


gemini_keys, groq_keys = get_all_api_keys()

# Kütüphane Yükleme Kontrolleri
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
  """Çoklu API anahtarları arasında sırayla dener (Failover mekanizması)."""
  # Önce Gemini
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

  # Gemini başarısızsa Groq
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


# --- 2. 5. SINIF MEB MÜFREDATI ---
MEB_CURRICULUM = {
    "Türkçe": [
        "1. Tema: Sözcükte Anlam",
        "2. Tema: Cümlede Anlam",
        "3. Tema: Parçada Anlam",
        "4. Tema: Metin Türleri ve Yazım Kuralları",
        "5. Tema: Noktalama İşaretleri",
    ],
    "Matematik": [
        "1. Ünite: Doğal Sayılar ve İşlemler",
        "2. Ünite: Kesirler",
        "3. Ünite: Ondalık Gösterimler",
        "4. Ünite: Temel Geometrik Kavramlar",
        "5. Ünite: Veri İşleme",
    ],
    "Fen Bilimleri": [
        "1. Ünite: Güneş, Dünya ve Ay",
        "2. Ünite: Canlılar Dünyası",
        "3. Ünite: Kuvvetin Etkisi",
        "4. Ünite: Madde ve Değişim",
        "5. Ünite: Işığın Yayılması",
        "6. Ünite: İnsan ve Çevre",
        "7. Ünite: Elektrik Devreleri",
    ],
    "Sosyal Bilgiler": [
        "1. Ünite: Birlikte Yaşamak",
        "2. Ünite: Evimiz Dünya",
        "3. Ünite: Kültür ve Miras",
        "4. Ünite: Yaşayan Türkiye",
        "5. Ünite: Üreten Türkiye",
        "6. Ünite: Yönetime Katılıyorum",
    ],
    "Din Kültürü ve Ahlak Bilgisi": [
        "1. Ünite: Allah İnancı",
        "2. Ünite: Ramazan ve Oruç",
        "3. Ünite: Hz. Muhammed ve Aile Hayatı",
        "4. Ünite: Çevremizde Dinin İzleri",
        "5. Ünite: Ahlaki Değerler",
    ],
    "İngilizce": [
        "Unit 1: Hello!",
        "Unit 2: My Town",
        "Unit 3: Games and Hobbies",
        "Unit 4: My Daily Routine",
        "Unit 5: Health",
        "Unit 6: Movies",
        "Unit 7: Party Time",
        "Unit 8: Fitness",
        "Unit 9: The Animal Shelter",
        "Unit 10: Festivals",
    ],
    "Almanca": [
        "Lektion 1: Hallo! Ich heiße...",
        "Lektion 2: Meine Familie",
        "Lektion 3: Meine Schulsachen",
        "Lektion 4: Zahlen und Farben",
        "Lektion 5: Hobbys und Freizeit",
    ],
}

# --- 3. ARAYÜZ TASARIMI ---
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        padding: 18px;
        border-radius: 12px;
        color: white;
        text-align: center;
        font-weight: bold;
        font-size: 26px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stButton>button {
        background-color: #2a5298;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #1e3c72;
        color: white;
    }
    </style>
    <div class="main-header">🎮 MEB İnteraktif Oyunla Öğrenme Platformu (Murat KANDIRMAZ)</div>
""",
    unsafe_allow_html=True,
)

# Sidebar Üzerinden Canlı API Durum Bilgisi ve Manuel Giriş Seçeneği
with st.sidebar:
  st.title("📌 Menü ve Ayarlar")

  # Eğer secrets veya environment'ta anahtar yoksa kullanıcıya arayüzden geçici anahtar girme imkanı sunalım
  if not gemini_keys and not groq_keys:
    st.error(
        "⚠️ Sistemde otomatik API anahtarı bulunamadı! Test edebilmek için"
        " aşağıya anahtar girebilirsiniz:"
    )
    manual_key = st.text_input(
        "Gemini veya Groq API Key Girin:", type="password"
    )
    if manual_key:
      if manual_key.startswith("AIza"):
        gemini_keys.append(manual_key)
        has_gemini = True
        st.success("Gemini API Anahtarı eklendi!")
      elif manual_key.startswith("gsk_"):
        groq_keys.append(manual_key)
        has_groq = True
        st.success("Groq API Anahtarı eklendi!")
  else:
    st.success("✅ Yapay Zeka API Bağlantısı Aktif!")

  selected_subject = st.selectbox(
      "📚 Ders Seçiniz", list(MEB_CURRICULUM.keys())
  )
  selected_unit = st.selectbox(
      "📖 Ünite Seçiniz", MEB_CURRICULUM[selected_subject]
  )

  game_mode = st.selectbox(
      "🎯 İnteraktif Oyun Modu:",
      [
          "🔤 Kelime Avı & Bulmaca",
          "⚖️ Doğru / Yanlış Bulmaca",
          "🧠 Çoktan Seçmeli Meb Sınavı",
          "🤖 Yapay Zeka Eğitmenimle Soru-Cevap",
      ],
  )

# --- OYUN MODU 1: KELİME AVI & BULMACA ---
if game_mode == "🔤 Kelime Avı & Bulmaca":
  st.subheader(f"🔤 Kelime Avı & Bulmaca — {selected_subject}")
  st.write(
      "Bu ünitedeki anahtar kavramları bulmaca bulmacaları ve tanım"
      " eşleştirmeleriyle öğren!"
  )

  if (
      "puzzle_data" not in st.session_state
      or st.session_state.get("puzzle_unit") != (selected_subject, selected_unit)
  ):
    st.session_state["puzzle_data"] = None
    st.session_state["puzzle_unit"] = (selected_subject, selected_unit)

  if st.button("🔍 Bulmaca Kelimelerini Üret"):
    if not gemini_keys and not groq_keys:
      st.warning(
          "Lütfen sol menüden API anahtarı girin veya secrets.toml"
          " yapılandırmanızı tamamlayın."
      )
    else:
      with st.spinner(
          "Yapay zeka MEB müfredatına uygun kelime avı hazırlıyor..."
      ):
        prompt = f"""
                Sen uzman bir 5. Sınıf MEB müfredat öğretmenisin.
                Ders: {selected_subject}
                Ünite: {selected_unit}
                
                Bu üniteyle ilgili tam 4 adet önemli anahtar kelime ve bu kelimelerin kısa tanımlarını seç.
                Yanıtı sadece aşağıdaki JSON formatında ver, başka hiçbir metin ekleme:
                [
                  {{"kelime": "TERİM", "ipucu": "Tanımı veya bulmaca ipucu cümlesi"}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            cleaned = re.sub(r"```json|```", "", res).strip()
            st.session_state["puzzle_data"] = json.loads(cleaned)
            st.rerun()
          except Exception:
            st.error("Veri işlenirken hata oluştu. Lütfen tekrar deneyin.")
        else:
          st.error(
              "Yapay zeka yanıt veremedi. API anahtarınızın kotasını kontrol"
              " edin."
          )

  if st.session_state["puzzle_data"]:
    items = st.session_state["puzzle_data"]
    with st.form("puzzle_form"):
      user_guesses = {}
      for i, item in enumerate(items):
        st.markdown(f"**İpucu {i+1}:** {item['ipucu']}")
        st.caption(f"Karakter Sayısı: {len(item['kelime'])} harfli")
        user_guesses[i] = st.text_input(
            f"Cevabınız (İpucu {i+1}):", key=f"puz_{i}"
        )
        st.markdown("---")

      sub = st.form_submit_button("Bulmacayı Kontrol Et")
      if sub:
        correct_count = 0
        for i, item in enumerate(items):
          ans = user_guesses.get(i, "").strip().upper()
          if ans == item["kelime"].upper():
            correct_count += 1
            st.success(f"✅ İpucu {i+1} Doğru! ({item['kelime']})")
          else:
            st.error(
                f"❌ İpucu {i+1} Yanlış. Doğru Cevap: **{item['kelime']}**"
            )

        if correct_count == len(items):
          st.balloons()
          st.success("🏆 Tebrikler! Kelime avı bulmacasını tamamen bitirdin!")

# --- OYUN MODU 2: DOĞRU / YANLIŞ BULMACA ---
elif game_mode == "⚖️ Doğru / Yanlış Bulmaca":
  st.subheader(f"⚖️ Doğru / Yanlış Bulmaca — {selected_subject}")
  st.write(
      "Cümlelerin doğru mu yanlış mı olduğunu tahmin et, puanları topla!"
  )

  if (
      "dw_data" not in st.session_state
      or st.session_state.get("dw_unit") != (selected_subject, selected_unit)
  ):
    st.session_state["dw_data"] = None
    st.session_state["dw_unit"] = (selected_subject, selected_unit)

  if st.button("⚡ D/Y Sorularını Üret"):
    if not gemini_keys and not groq_keys:
      st.warning("Lütfen sol menüden API anahtarı girin.")
    else:
      with st.spinner("Doğru/Yanlış bulmaca soruları hazırlanıyor..."):
        prompt = f"""
                Sen uzman bir 5. Sınıf MEB öğretmenisin. 
                Ders: {selected_subject}
                Ünite: {selected_unit}
                
                Bu konuyla ilgili 5 adet Doğru veya Yanlış türünde cümle hazırla.
                Yanıtı sadece şu JSON formatında ver:
                [
                  {{"ifade": "Cümle buraya", "cevap": "Doğru", "aciklama": "Neden doğru/yanlış olduğu açıklaması"}},
                  {{"ifade": "Cümle buraya", "cevap": "Yanlış", "aciklama": "Açıklama"}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            cleaned = re.sub(r"```json|```", "", res).strip()
            st.session_state["dw_data"] = json.loads(cleaned)
            st.rerun()
          except Exception:
            st.error("Biçim hatası oluştu.")
        else:
          st.error("Yapay zeka yanıt veremedi.")

  if st.session_state["dw_data"]:
    dw_list = st.session_state["dw_data"]
    with st.form("dw_form"):
      dw_answers = {}
      for idx, item in enumerate(dw_list):
        st.markdown(f"**Soru {idx+1}:** {item['ifade']}")
        dw_answers[idx] = st.radio(
            "Seçiminiz:", ["Doğru", "Yanlış"], key=f"dw_{idx}", index=None
        )
        st.markdown("---")

      if st.form_submit_button("Sonuçları Değerlendir"):
        corrects = 0
        for idx, item in enumerate(dw_list):
          if dw_answers.get(idx) == item["cevap"]:
            corrects += 1
            st.success(
                f"Soru {idx+1}: Doğru Bildiniz! 👏 Açıklama: {item['aciklama']}"
            )
          else:
            st.error(
                f"Soru {idx+1}: Yanlış. Doğru cevap **{item['cevap']}** olacaktı."
                f" Açıklama: {item['aciklama']}"
            )
        st.info(f"Toplam Skor: {corrects} / {len(dw_list)}")

# --- OYUN MODU 3: ÇOKTAN SEÇMELİ MEB SINAVI ---
elif game_mode == "🧠 Çoktan Seçmeli Meb Sınavı":
  st.subheader(f"🧠 {selected_subject} — MEB Kazanım Testi")
  st.write("LGS ve MEB yazılı sınavlarına hazırlık için çoktan seçmeli test.")

  if (
      "quiz_data" not in st.session_state
      or st.session_state.get("q_unit") != (selected_subject, selected_unit)
  ):
    st.session_state["quiz_data"] = None
    st.session_state["q_unit"] = (selected_subject, selected_unit)

  if st.button("🚀 Test Sorularını Getir"):
    if not gemini_keys and not groq_keys:
      st.warning("Lütfen sol menüden API anahtarı girin.")
    else:
      with st.spinner("Sorular üretiliyor..."):
        prompt = f"""
                5. Sınıf MEB müfredatı, Ders: {selected_subject}, Ünite: {selected_unit}.
                4 şıklı (A, B, C, D) 4 adet çoktan seçmeli soru hazırla.
                JSON formatında ver:
                [
                  {{"soru": "Soru?", "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."], "dogru_cevap": "A", "aciklama": "..."}}
                ]
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            cleaned = re.sub(r"```json|```", "", res).strip()
            st.session_state["quiz_data"] = json.loads(cleaned)
            st.rerun()
          except Exception:
            st.error("Hata oluştu.")

  if st.session_state["quiz_data"]:
    quiz = st.session_state["quiz_data"]
    with st.form("quiz_main"):
      user_q_ans = {}
      for idx, q in enumerate(quiz):
        st.markdown(f"**Soru {idx+1}:** {q['soru']}")
        user_q_ans[idx] = st.radio(
            f"Şıklar (Soru {idx+1}):", q["secenekler"], key=f"mq_{idx}", index=None
        )
        st.markdown("---")

      if st.form_submit_button("Testi Bitir"):
        score_c = 0
        for idx, q in enumerate(quiz):
          if user_q_ans.get(idx) and user_q_ans.get(idx).startswith(
              q["dogru_cevap"]
          ):
            score_c += 1
        st.balloons()
        st.success(
            f"🎉 Sınav Bitti! Puanınız: {score_c * 25} / 100 ({score_c} Doğru)"
        )
        for idx, q in enumerate(quiz):
          st.info(f"Soru {idx+1} Açıklama: {q['aciklama']}")

# --- OYUN MODU 4: YAPAY ZEKA EĞİTMENİM ---
elif game_mode == "🤖 Yapay Zeka Eğitmenimle Soru-Cevap":
  st.subheader(f"🤖 {selected_subject} - Canlı AI Eğitmen")
  st.write(
      f"Seçtiğin ünite ({selected_unit}) hakkında kafana takılanları sor, eğlenceli"
      " bir dille anlatalım!"
  )

  question = st.text_input(
      "Merak ettiğin soruyu yaz:", placeholder="Örn: Bu konuyu bana örnekle..."
  )
  if st.button("Cevap Al"):
    if not gemini_keys and not groq_keys:
      st.warning("Lütfen sol menüden API anahtarı girin.")
    elif question:
      with st.spinner("Eğitmen yanıtlıyor..."):
        prompt = f"""
                Sen 5. sınıf öğrencisine rehberlik eden sevecen bir MEB öğretmenisin.
                Ders: {selected_subject}, Ünite: {selected_unit}
                Soru: {question}
                Öğrencinin yaş seviyesine uygun, sade ve örnekli bir açıklama yap.
                """
        ans = ai_generate_content(prompt)
        if ans:
          st.success(ans)
        else:
          st.error("Yapay zekaya ulaşılamadı.")
    else:
      st.warning("Lütfen bir soru yazın.")
