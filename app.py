import random
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="MEB 5. Sınıf Oyunla Öğrenme Platformu",
    page_icon="🎒",
    layout="wide",
)

# --- 1. ÇOKLU API YÖNETİMİ VE BAĞLANTI (GEMINI & GROQ) ---


def get_api_keys():
  """Streamlit secrets üzerinden birden çok Gemini ve Groq anahtarını toplar."""
  gemini_keys = []
  groq_keys = []

  try:
    if "GEMINI_API_KEY" in st.secrets:
      gemini_keys.append(st.secrets["GEMINI_API_KEY"])
    for i in range(1, 10):
      key_name = f"GEMINI_API_KEY_{i}"
      if key_name in st.secrets:
        gemini_keys.append(st.secrets[key_name])
  except Exception:
    pass

  try:
    if "GROQ_API_KEY" in st.secrets:
      groq_keys.append(st.secrets["GROQ_API_KEY"])
    for i in range(1, 10):
      key_name = f"GROQ_API_KEY_{i}"
      if key_name in st.secrets:
        groq_keys.append(st.secrets[key_name])
  except Exception:
    pass

  return gemini_keys, groq_keys


gemini_keys, groq_keys = get_api_keys()

# API Kütüphanelerini İçe Aktarma Denemesi
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
  """Tanımlı çoklu API'ler arasında geçiş yaparak (yedekli) yapay zeka yanıtı üretir."""
  response_text = None

  # Önce Gemini dene
  if has_gemini and gemini_keys:
    for g_key in gemini_keys:
      try:
        genai.configure(api_key=g_key)
        # Güvenli model seçimi
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

  # Gemini başarısız olursa Groq dene
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


# --- 2. 5. SINIF MEB MÜFREDATI VE ÜNİTELERİ ---
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
        "4. Ünite: Temel Geometrik Kavramlar ve Çizimler",
        "5. Ünite: Veri İşleme ve Uzunluk Ölçme",
    ],
    "Fen Bilimleri": [
        "1. Ünite: Güneş, Dünya ve Ay",
        "2. Ünite: Canlılar Dünyası",
        "3. Ünite: Kuvvetin Etkisi",
        "4. Ünite: Madde ve Değişim",
        "5. Ünite: Işığın Yayılması",
        "6. Ünite: İnsan ve Çevre",
        "7. Ünite: Elektrik Devre Elemanları",
    ],
    "Sosyal Bilgiler": [
        "1. Ünite: Birlikte Yaşamak",
        "2. Ünite: Evimiz Dünya",
        "3. Ünite: Çevremizde Değerler ve Kültür",
        "4. Ünite: Yaşayan Türkiye",
        "5. Ünite: Üreten Türkiye",
        "6. Ünite: Yönetime Katılıyorum",
    ],
    "Din Kültürü ve Ahlak Bilgisi": [
        "1. Ünite: Allah İnancı",
        "2. Ünite: Ramazan ve Oruç İbadeti",
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

# --- 3. ARAYÜZ VE MENÜLER ---
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(90deg, #ff8c00, #ffa500);
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
        font-weight: bold;
        font-size: 24px;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #ff8c00;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover {
        background-color: #e07b00;
        color: white;
    }
    </style>
    <div class="main-header">🎒 5. Sınıf MEB Eğlenceli Öğrenme Merkezi (Murat KANDIRMAZ)</div>
""",
    unsafe_allow_html=True,
)

# API Durum Kontrolü ve Uyarı
if not gemini_keys and not groq_keys:
  st.warning(
      "⚠️ Yapay zeka anahtarları (Gemini veya Groq) algılanamadı! Sorular"
      " yerel havuzdan üretilecektir. Tam performans için `secrets.toml`"
      " dosyanızı ekleyin."
  )

# Yan Menü: Ders ve Mod Seçimi
st.sidebar.title("📌 Ders ve Mod Seçimi")
selected_subject = st.sidebar.selectbox(
    "Ders Seçiniz", list(MEB_CURRICULUM.keys())
)
selected_unit = st.sidebar.selectbox(
    "Ünite / Konu Seçiniz", MEB_CURRICULUM[selected_subject]
)

game_mode = st.sidebar.radio(
    "Öğrenme Modu Seçin:",
    [
        "🎯 AI Soru Fabrikası (Test Çöz)",
        "🧩 Kelime Eşleştirme & Bulmaca",
        "🤖 AI Akıllı Öğretmen (Koç)",
    ],
)

# --- MOD 1: AI SORU FABRİKASI ---
if game_mode == "🎯 AI Soru Fabrikası (Test Çöz)":
  st.subheader(f"🎯 {selected_subject} - {selected_unit} Test Alanı")
  st.write(
      "MEB müfredatına uygun olarak yapay zeka tarafından hazırlanan soruları"
      " çöz, puanları topla!"
  )

  if "quiz_data" not in st.session_state or st.session_state.get(
      "current_unit"
  ) != (selected_subject, selected_unit):
    st.session_state["quiz_data"] = None
    st.session_state["user_answers"] = {}
    st.session_state["current_unit"] = (selected_subject, selected_unit)

  if st.button("🚀 Bu Üniteden Yeni Sorular Üret"):
    with st.spinner("Yapay zeka MEB kazanımlarına uygun sorular hazırlıyor..."):
      prompt = f"""
            Sen uzman bir 5. Sınıf MEB müfredat öğretmenisin. 
            Ders: {selected_subject}
            Ünite/Konu: {selected_unit}
            
            Lütfen bu konuyla ilgili 5 adet çoktan seçmeli, 4 şıklı (A, B, C, D) eğlenceli ve öğretici soru hazırla.
            Yanıtı kesinlikle aşağıdaki JSON formatında ver, başka hiçbir metin ekleme:
            [
              {{
                "soru": "Soru metni buraya",
                "secenekler": ["A) şık", "B) şık", "C) şık", "D) şık"],
                "dogru_cevap": "A",
                "aciklama": "Çocuğun anlayacağı dilde kısa açıklama"
              }}
            ]
            """
      ai_response = ai_generate_content(prompt)
      if ai_response:
        import json
        import re

        try:
          # JSON temizleme
          cleaned = re.sub(r"```json|```", "", ai_response).strip()
          st.session_state["quiz_data"] = json.loads(cleaned)
          st.success("Sorular başarıyla yüklendi!")
        except Exception:
          st.error(
              "Sorular yüklenirken biçim hatası oluştu. Lütfen tekrar deneyin."
          )
          st.session_state["quiz_data"] = None
      else:
        st.error(
            "Yapay zeka yanıt veremedi. Lütfen API anahtarlarınızı kontrol"
            " edin."
        )

  # Soruları Göster
  if st.session_state["quiz_data"]:
    quiz = st.session_state["quiz_data"]
    with st.form(key="quiz_form"):
      score = 0
      for idx, q in enumerate(quiz):
        st.markdown(f"**Soru {idx+1}:** {q['soru']}")
        choice = st.radio(
            f"Seçiminiz (Soru {idx+1}):",
            q["secenekler"],
            key=f"q_{idx}",
            index=None,
        )
        st.session_state["user_answers"][idx] = choice
        st.markdown("---")

      submitted = st.form_submit_button("Sınavı Bitir ve Puanı Gör")
      if submitted:
        correct_count = 0
        for idx, q in enumerate(quiz):
          user_ans = st.session_state["user_answers"].get(idx)
          if user_ans and user_ans.startswith(q["dogru_cevap"]):
            correct_count += 1

        st.balloons()
        st.success(
            f"🎉 Sınav Tamamlandı! Toplam Puanınız: {correct_count * 20} / 100"
            f" ({correct_count} Doğru, {len(quiz)-correct_count} Yanlış)"
        )

        with st.expander("📖 Soru Çözümleri ve Açıklamalar"):
          for idx, q in enumerate(quiz):
            st.markdown(
                f"**Soru {idx+1}:** Doğru Cevap: **{q['dogru_cevap']}**"
            )
            st.info(f"Açıklama: {q['aciklama']}")

# --- MOD 2: KELİME EŞLEŞTİRME & BULMACA ---
elif game_mode == "🎯 Kelime Eşleştirme & Bulmaca" or game_mode == (
    "🧩 Kelime Eşleştirme & Bulmaca"
):
  st.subheader(f"🧩 {selected_subject} - Bilgi Kartları & Kelime Bulmaca")
  st.write(
      "Bu ünitenin en önemli kavramlarını öğrenmek için yapay zekadan anahtar"
      " kelimeler isteyin."
  )

  if st.button("✨ Ünite Terim Kartlarını Getir"):
    with st.spinner("Kavramlar hazırlanıyor..."):
      prompt = f"""
            5. Sınıf {selected_subject} dersi {selected_unit} konusu için en önemli 5 anahtar kelimeyi ve kısa açıklamalarını seç.
            Yanıtı JSON formatında şu şekilde ver:
            [
              {{"kelime": "Kavram", "tanim": "Çocuklar için basit açıklama"}}
            ]
            """
      res = ai_generate_content(prompt)
      if res:
        import json
        import re

        try:
          cleaned = re.sub(r"```json|```", "", res).strip()
          terms = json.loads(cleaned)
          for t in terms:
            st.info(f"🔑 **{t['kelime']}**: {t['tanim']}")
        except Exception:
          st.write(res)
      else:
        st.warning(
            "Yapay zekaya ulaşılamadı. Lütfen API ayarlarınızı kontrol edin."
        )

# --- MOD 3: AI AKILLI ÖĞRETMEN ---
elif game_mode == "🤖 AI Akıllı Öğretmen (Koç)":
  st.subheader(f"🤖 {selected_subject} Yapay Zeka Öğretmenim")
  st.write(
      f"Seçtiğin ünite ({selected_unit}) hakkında anlamadığın yerleri bana sor,"
      " sana örneklerle anlatayım!"
  )

  user_question = st.text_input(
      "Aklına takılan soruyu yaz:",
      placeholder="Örn: Bu konuyu bana bir masal gibi anlatır mısın?",
  )

  if st.button("Cevap Al"):
    if user_question:
      with st.spinner("Öğretmeniniz düşünüyor..."):
        prompt = f"""
                Sen 5. sınıfa giden bir öğrenciye öğretmenlik yapan, çok sevecen, açıklayıcı ve motive edici bir yapay zeka eğitim koçusun.
                Ders: {selected_subject}
                Ünite: {selected_unit}
                Öğrencinin Sorusu: {user_question}
                
                Lütfen 5. sınıf seviyesine uygun, anlaşılır, örnekli ve samimi bir dille yanıtla.
                """
        answer = ai_generate_content(prompt)
        if answer:
          st.success(answer)
        else:
          st.error(
              "Şu anda yapay zeka servislerine erişilemiyor. Lütfen tekrar"
              " deneyin."
          )
    else:
      st.warning("Lütfen bir soru yazın.")
