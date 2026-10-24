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

# --- 1. AKILLI API VE YEDEK SORU MOTORU (ASLA HATA VERMEZ) ---


def get_all_api_keys():
  """Secrets, environment veya manuel anahtarları toplar."""
  gemini_keys = []
  groq_keys = []

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

  for env_key, env_val in os.environ.items():
    env_upper = env_key.upper()
    if env_val and isinstance(env_val, str) and len(env_val.strip()) > 5:
      if (
          "GEMINI" in env_upper or "GOOGLE" in env_upper
      ) and env_val.strip() not in gemini_keys:
        gemini_keys.append(env_val.strip())
      elif "GROQ" in env_upper and env_val.strip() not in groq_keys:
        groq_keys.append(env_val.strip())

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


# Çevrimdışı / Yedek MEB Soru Veritabanı (API çalışmasa bile oyunlar çalışır)
FALLBACK_QUESTIONS = {
    "Türkçe": {
        "balon": {
            "soru": (
                "Aşağıdaki cümlelerin hangisinde 'altında' sözcüğü mecmu"
                " anlamda kullanılmıştır?"
            ),
            "secenekler": [
                "A) Masanın altında bir kedi var.",
                "B) Bu işin altında senin parmağın var.",
                "C) Ağacın altında dinlendik.",
                "D) Halının altında anahtar unutulmuş.",
            ],
            "dogru_cevap": "B",
            "aciklama": (
                "Gerçek anlamdan uzaklaşarak yeni bir anlam kazandığı için"
                " mecazdır."
            ),
        },
        "kelime": [
            {
                "kelime": "TERİM",
                "ipucu": "Bilim, sanat veya meslek dalıyla ilgili özel kavram.",
            },
            {
                "kelime": "DEYİM",
                "ipucu": (
                    "Genellikle gerçek anlamından uzak kendine özgü kalıplaşmış"
                    " söz grubu."
                ),
            },
            {
                "kelime": "MECAZ",
                "ipucu": (
                    "Bir sözcüğün gerçek anlamı dışında başka bir anlamda"
                    " kullanılması."
                ),
            },
        ],
    },
    "Matematik": {
        "balon": {
            "soru": (
                "34567 doğal sayısının binler basamağındaki rakamın basamak"
                " değeri kaçtır?"
            ),
            "secenekler": [
                "A) 4000",
                "B) 500",
                "C) 400",
                "D) 30000",
            ],
            "dogru_cevap": "A",
            "aciklama": (
                "Binler basamağında 4 vardır, basamak değeri 4 x 1000 = 4000'dir."
            ),
        },
        "kelime": [
            {
                "kelime": "KESİR",
                "ipucu": (
                    "Bütünün eş parçalarından birini veya birkaçını belirten"
                    " ifade."
                ),
            },
            {
                "kelime": "PAY",
                "ipucu": (
                    "Kesir çizgisinin üstündeki sayı, eş parçadan kaç tanesini"
                    " gösterir."
                ),
            },
            {
                "kelime": "PAYDA",
                "ipucu": (
                    "Bütünün kaç eş parçaya bölündüğünü gösteren alt sayı."
                ),
            },
        ],
    },
    "Fen Bilimleri": {
        "balon": {
            "soru": (
                "Güneş, Dünya ve Ay'ın birbirine göre hareketleri ile ilgili"
                " hangisi yanlıştır?"
            ),
            "secenekler": [
                "A) Dünya kendi etrafında döner.",
                "B) Ay, Dünya etrafında dolanır.",
                "C) Güneş, Dünya'nın etrafında döner.",
                "D) Dünya, Güneş etrafında dolanır.",
            ],
            "dogru_cevap": "C",
            "aciklama": (
                "Güneş sabit değildir kendi ekseni etrafında döner ancak"
                " Dünya'nın etrafında dönmez."
            ),
        },
        "kelime": [
            {
                "kelime": "EVRE",
                "ipucu": "Ay'ın şekil değişikliklerinin her bir durumu.",
            },
            {
                "kelime": "KUVVET",
                "ipucu": "Cisimleri hareket ettiren, durduran etki.",
            },
            {
                "kelime": "SÜRTÜNME",
                "ipucu": (
                    "Yüzeylerin teması sonucu hareketi zorlaştıran kuvvet."
                ),
            },
        ],
    },
}


def ai_generate_content(prompt_text):
  """Yapay zeka modelleri arasında yedekli çağrı yapar, hata durumunda yedek döner."""
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

# --- 3. ARAYÜZ TASARIMI (CSS) ---
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

# --- 4. SOL MENÜ (API YARDIMCI GİRİŞİ) ---
with st.sidebar:
  st.subheader("⚙️ API Yapılandırma")
  if not gemini_keys and not groq_keys:
    st.info(
        "💡 Otomatik anahtar yoksa test için buraya API anahtarınızı"
        " yapıştırabilirsiniz:"
    )
    m_key = st.text_input(
        "Gemini (AIza...) veya Groq (gsk_...)", type="password"
    )
    if m_key:
      if m_key.startswith("AIza"):
        st.session_state["manual_gemini"] = m_key
        st.success("Gemini eklendi!")
        st.rerun()
      elif m_key.startswith("gsk_"):
        st.session_state["manual_groq"] = m_key
        st.success("Groq eklendi!")
        st.rerun()
  else:
    st.success("✅ Yapay Zeka Aktif")

  st.markdown("---")
  if st.button("🏠 Ana Sayfaya Dön (Ders Seçimi)"):
    st.session_state["selected_subject"] = None
    st.session_state["selected_unit"] = None
    st.rerun()

# --- 5. NAVİGASYON AKIŞI: DERS -> ÜNİTE -> OYUNLAR ---

# Session state tanımları
if "selected_subject" not in st.session_state:
  st.session_state["selected_subject"] = None
if "selected_unit" not in st.session_state:
  st.session_state["selected_unit"] = None

# AŞAMA 1: DERS SEÇİMİ (DASHBOARD - RENKLİ KUTUCUKLAR)
if st.session_state["selected_subject"] is None:
  st.markdown(
      "### 🌟 Lütfen Çalışmak İstediğiniz MEB Dersini Seçin (Dashboard)"
  )
  st.markdown(
      "Aşağıdaki renkli ders kutucuklarından birine tıklayarak devam edin."
  )

  subjects = list(MEB_CURRICULUM.keys())
  cols = st.columns(3)

  for i, subj in enumerate(subjects):
    col_idx = i % 3
    data = MEB_CURRICULUM[subj]
    with cols[col_idx]:
      st.markdown(
          f"""
                <div style="background-color: {data['renk']}; padding: 22px; border-radius: 12px; color: white; text-align: center; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h1 style="margin:0; font-size: 38px;">{data['ikon']}</h1>
                    <h3 style="margin: 10px 0 0 0; color: white;">{subj}</h3>
                </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(f"📚 {subj} Seç", key=f"dash_btn_{subj}"):
        st.session_state["selected_subject"] = subj
        st.rerun()

# AŞAMA 2: ÜNİTE SEÇİMİ (YENİ EKRANDA RENKLİ KUTUCUKLAR)
elif (
    st.session_state["selected_subject"] is not None
    and st.session_state["selected_unit"] is None
):
  curr_subj = st.session_state["selected_subject"]
  curr_data = MEB_CURRICULUM[curr_subj]

  st.markdown(
      f"### {curr_data['ikon']} {curr_subj} — Ünite / Konu Seçim Ekranı"
  )
  st.write("Çalışmak istediğiniz alt üniteyi aşağıdaki kutucuklardan seçin:")

  if st.button("⬅️ Ders Seçimine Geri Dön"):
    st.session_state["selected_subject"] = None
    st.rerun()

  st.markdown("---")

  # Üniteleri renkli kutucuklar şeklinde listeleme
  unit_cols = st.columns(2)
  for idx, unit_name in enumerate(curr_data["uniteler"]):
    u_col = unit_cols[idx % 2]
    with u_col:
      st.markdown(
          f"""
                <div style="background-color: {curr_data['renk']}; opacity: 0.9; padding: 15px; border-radius: 10px; color: white; text-align: center; margin-bottom: 12px; font-weight: bold; font-size: 16px;">
                    📖 {unit_name}
                </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button(f"Seç: {unit_name}", key=f"unit_btn_{idx}"):
        st.session_state["selected_unit"] = unit_name
        st.rerun()

# AŞAMA 3: OYUN VE SORU MODELLERİ (SEÇİLEN DERS VE ÜNİTE ÜZERİNDEN)
else:
  curr_subj = st.session_state["selected_subject"]
  curr_unit = st.session_state["selected_unit"]
  curr_data = MEB_CURRICULUM[curr_subj]

  # Üst bilgi çubuğu
  st.markdown(
      f"""
        <div style="background-color: {curr_data['renk']}; padding: 12px; border-radius: 8px; color: white; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
            <span><b>Ders:</b> {curr_subj} &nbsp;|&nbsp; <b>Ünite:</b> {curr_unit}</span>
        </div>
    """,
      unsafe_allow_html=True,
  )

  col_back, _ = st.columns([1, 4])
  with col_back:
    if st.button("↩️ Ünite Değiştir"):
      st.session_state["selected_unit"] = None
      st.rerun()

  st.markdown("### 🎮 MEB İnteraktif Oyun ve Soru Modelleri")
  game_mode = st.tabs([
      "🎈 Balon Patlatmaca",
      "🧠 10 Soruluk MEB Sınavı",
      "✍️ Açık Uçlu Soru Köşesi",
      "🔤 Kelime Avı & Bulmaca",
      "🤖 Yapay Zeka Koçum",
  ])

  # --- MOD 1: BALON PATLATMACA ---
  with game_mode[0]:
    st.subheader("🎈 Balon Patlatmaca Soru Oyunu")
    if (
        "b_data" not in st.session_state
        or st.session_state.get("b_unit") != (curr_subj, curr_unit)
    ):
      st.session_state["b_data"] = None
      st.session_state["b_unit"] = (curr_subj, curr_unit)

    if st.button("🚀 Yeni Balon Soru Üret"):
      with st.spinner("Balonlar hazırlanıyor..."):
        prompt = f"5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}. Balon patlatmaca için 4 şıklı soru hazırla. JSON: {{\"soru\": \"...\", \"secenekler\": [\"A) ...\", \"B) ...\", \"C) ...\", \"D) ...\"], \"dogru_cevap\": \"A\", \"aciklama\": \"...\"}}"
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["b_data"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            pass
        # Fallback veri
        if not st.session_state["b_data"]:
          st.session_state["b_data"] = FALLBACK_QUESTIONS.get(
              curr_subj, FALLBACK_QUESTIONS["Türkçe"]
          )["balon"]
          st.rerun()

    # Eğer veri yoksa varsayılan yedek yükle
    if not st.session_state["b_data"]:
      st.session_state["b_data"] = FALLBACK_QUESTIONS.get(
          curr_subj, FALLBACK_QUESTIONS["Türkçe"]
      )["balon"]

    b_q = st.session_state["b_data"]
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

  # --- MOD 2: 10 SORULUK MEB SINAVI ---
  with game_mode[1]:
    st.subheader(f"🧠 10 Soruluk {curr_subj} MEB Kazanım Sınavı")
    if (
        "exam_10" not in st.session_state
        or st.session_state.get("ex_unit") != (curr_subj, curr_unit)
    ):
      st.session_state["exam_10"] = None
      st.session_state["ex_unit"] = (curr_subj, curr_unit)

    if st.button("📝 10 Soruluk Sınavı Başlat"):
      with st.spinner("10 adet MEB kalitesinde soru hazırlanıyor..."):
        prompt = f"5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}. 10 adet 4 şıklı çoktan seçmeli soru listesi JSON formatında ver: [{{\"soru\": \"...\", \"secenekler\": [\"A) ...\", \"B) ...\", \"C) ...\", \"D) ...\"], \"dogru_cevap\": \"A\", \"aciklama\": \"...\"}}] "
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["exam_10"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            pass

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

        if st.form_submit_button("Sınavı Tamamla"):
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

  # --- MOD 3: AÇIK UÇLU SORU KÖŞESİ ---
  with game_mode[2]:
    st.subheader("✍️ Açık Uçlu Soru ve Yapay Zeka Değerlendirme")
    if (
        "open_q" not in st.session_state
        or st.session_state.get("op_unit") != (curr_subj, curr_unit)
    ):
      st.session_state["open_q"] = None
      st.session_state["op_unit"] = (curr_subj, curr_unit)

    if st.button("✨ Klasik Soru Getir"):
      with st.spinner("Soru hazırlanıyor..."):
        prompt = f"5. Sınıf MEB, Ders: {curr_subj}, Ünite: {curr_unit}. 1 adet açık uçlu yazılı sorusu ve ideal cevap anahtarını JSON ver: {{\"soru\": \"...\", \"beklenen_cevap\": \"...\"}}"
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
      if st.button("Yapay Zekaya Değerlendir"):
        if stu_ans:
          with st.spinner("Değerlendiriliyor..."):
            fb = ai_generate_content(
                f"Sen 5. sınıf öğretmenisin. Soru: {oq['soru']}, İdeal Cevap:"
                f" {oq['beklenen_cevap']}, Öğrencinin Cevabı: {stu_ans}."
                " Puanla ve açıkla."
            )
            if fb:
              st.success(fb)
        else:
          st.warning("Cevap yazın.")

  # --- MOD 4: KELİME AVI & BULMACA ---
  with game_mode[3]:
    st.subheader("🔤 Kelime Avı & Bulmaca")
    if st.button("🔍 Kelimeleri Getir"):
      st.session_state["puz"] = FALLBACK_QUESTIONS.get(
          curr_subj, FALLBACK_QUESTIONS["Türkçe"]
      )["kelime"]

    if "puz" in st.session_state and st.session_state["puz"]:
      with st.form("puz_form"):
        p_res = {}
        for idx, item in enumerate(st.session_state["puz"]):
          st.markdown(f"**İpucu:** {item['ipucu']}")
          p_res[idx] = st.text_input(f"Kelime {idx+1}:", key=f"p_{idx}")
        if st.form_submit_button("Kontrol Et"):
          for idx, item in enumerate(st.session_state["puz"]):
            if p_res.get(idx, "").strip().upper() == item["kelime"].upper():
              st.success(f"✅ Doğru! ({item['kelime']})")
            else:
              st.error(f"❌ Yanlış. Doğru: **{item['kelime']}**")

  # --- MOD 5: YAPAY ZEKA KOÇUM ---
  with game_mode[4]:
    st.subheader(f"🤖 {curr_subj} Canlı Yapay Zeka Koçu")
    user_q = st.text_input("Aklına takılan soruyu sor:")
    if st.button("Koçuma Sor"):
      if user_q:
        with st.spinner("Öğretmeniniz yanıtlıyor..."):
          ans = ai_generate_content(
              f"Sen 5. sınıf öğretmenisin. Ders: {curr_subj}, Ünite:"
              f" {curr_unit}. Soru: {user_q}"
          )
          if ans:
            st.success(ans)
