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

# --- 1. KOŞULSUZ VE ESNEK TOML / SECRETS API TARAMA MOTORU ---


def get_all_api_keys():
  """Streamlit secrets (TOML) veya ortam değişkenlerinden

  tüm API anahtarlarını biçim fark etmeksizin koşulsuz toplar.
  """
  gemini_keys = []
  groq_keys = []

  # Streamlit Secrets (TOML) derinlemesine özyinelemeli tarama
  try:
    if hasattr(st, "secrets") and st.secrets:
      # 1. Doğrudan anahtarları kontrol et
      for top_key in st.secrets.keys():
        tk_lower = str(top_key).lower()
        try:
          val = str(st.secrets[top_key]).strip()
          if len(val) > 5:
            if (
                "gemini" in tk_lower
                or "google" in tk_lower
                or val.startswith("AIza")
            ):
              if val not in gemini_keys:
                gemini_keys.append(val)
            elif "groq" in tk_lower or val.startswith("gsk_"):
              if val not in groq_keys:
                groq_keys.append(val)
        except Exception:
          pass

      # 2. İç içe tabloları (nested dict) tarama
      def recursive_search(data):
        if isinstance(data, dict):
          for k, v in data.items():
            if isinstance(v, dict):
              recursive_search(v)
            elif isinstance(v, str):
              val = v.strip()
              k_lower = str(k).lower()
              if len(val) > 5:
                if (
                    "gemini" in k_lower
                    or "google" in k_lower
                    or val.startswith("AIza")
                ):
                  if val not in gemini_keys and not val.startswith("gsk_"):
                    gemini_keys.append(val)
                elif "groq" in k_lower or val.startswith("gsk_"):
                  if val not in groq_keys:
                    groq_keys.append(val)

      recursive_search(st.secrets)
  except Exception:
    pass

  # Sistem Ortam Değişkenleri Taraması
  for env_key, env_val in os.environ.items():
    env_lower = env_key.lower()
    if env_val and isinstance(env_val, str) and len(env_val.strip()) > 5:
      val = env_val.strip()
      if (
          "gemini" in env_lower
          or "google" in env_lower
          or val.startswith("AIza")
      ):
        if val not in gemini_keys:
          gemini_keys.append(val)
      elif "groq" in env_lower or val.startswith("gsk_"):
        if val not in groq_keys:
          groq_keys.append(val)

  # Manuel eklenenler (Session State)
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
  """Mutlaka gemini-3.6-flash ve Groq modellerini dener."""
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
        f"✅ Yapay Zeka Aktif!\n(Gemini: {len(gemini_keys)}, Groq:"
        f" {len(groq_keys)})"
    )
  else:
    st.warning("⚠️ TOML'dan anahtar okunamadı. Geçici girebilirsiniz:")
    m_key = st.text_input("API Key Girin:", type="password")
    if m_key:
      if m_key.startswith("AIza"):
        st.session_state["manual_gemini"] = m_key
        st.success("Gemini eklendi!")
        st.rerun()
      elif m_key.startswith("gsk_"):
        st.session_state["manual_groq"] = m_key
        st.success("Groq eklendi!")
        st.rerun()

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

# --- AŞAMA 1: DERS SEÇİMİ (BÜYÜK RENKLİ KARTLAR) ---
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

# --- AŞAMA 2: ÜNİTE SEÇİMİ (BÜYÜK RENKLİ KARTLAR) ---
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

# --- AŞAMA 3: OYUN VE SORU MODELLERİ (BÜYÜK RENKLİ KARTLAR) ---
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

  # 1. BALON PATLATMACA
  if curr_game == "balon":
    st.subheader("🎈 Balon Patlatmaca Soru Oyunu")
    if (
        "b_data" not in st.session_state
        or st.session_state.get("b_unit") != (curr_subj, curr_unit)
    ):
      st.session_state["b_data"] = None
      st.session_state["b_unit"] = (curr_subj, curr_unit)

    if st.button("🚀 Yapay Zeka ile Balon Soru Üret", key="gen_balloon"):
      with st.spinner("Yapay zeka soru hazırlıyor..."):
        prompt = f"""
                5. Sınıf MEB müfredatı, Ders: {curr_subj}, Ünite: {curr_unit}.
                Balon patlatmaca oyunu için AI destekli 4 şıklı soru üret.
                Kesinlikle şu JSON formatında ver:
                {{"soru": "Soru metni", "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."], "dogru_cevap": "A", "aciklama": "Açıklama"}}
                """
        res = ai_generate_content(prompt)
        if res:
          try:
            st.session_state["b_data"] = json.loads(
                re.sub(r"```json|```", "", res).strip()
            )
            st.rerun()
          except Exception:
            st.error("Üretim hatası.")

    if st.session_state["b_data"]:
      b_q = st.session_state["b_data"]
      st.markdown(f"### ❓ {b_q['soru']}")
      b_cols = st.columns(2)
      for idx, opt in enumerate(b_q["secenekler"]):
        with b_cols[idx % 2]:
          if st.button(f"🎈 {opt}", key=f"ball_{idx}"):
            if opt.startswith(b_q["dogru_cevap"]):
              st.balloons()
              st.success(f"🎉 Tebrikler! Doğru balon! {b_q['aciklama']}")
            else:
              st.error(
                  f"💥 Yanlış balon! Doğru cevap **{b_q['dogru_cevap']}**."
                  f" {b_q['aciklama']}"
              )

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
