# -*- coding: utf-8 -*-
import streamlit as st
import random
import json
import os

# API İstemci Kütüphaneleri
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

# ==========================================
# 1. SAYFA YAPILANDIRMASI VE ÖZEL CSS
# ==========================================
st.set_page_config(
    page_title="MEB Yazılı Sınav Modülü - Murat KANDIRMAZ",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .exam-header {
        border: 2px solid #333;
        padding: 20px;
        border-radius: 8px;
        background-color: #fff;
        color: #000;
        margin-bottom: 25px;
        text-align: center;
    }
    .question-box {
        background-color: #ffffff;
        border: 1px solid #ccc;
        border-left: 5px solid #1A237E;
        border-radius: 6px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        color: #000;
    }
    .answer-box {
        background-color: #e8f5e9;
        border: 1px solid #2e7d32;
        padding: 15px;
        border-radius: 6px;
        margin-top: 10px;
        color: #1b5e20;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MEB 5. SINIF TAM MÜFREDAT LİSTESİ
# ==========================================
MEB_FULL_CURRICULUM = {
    "Fen Bilimleri": [
        "1. Ünite: Güneş, Dünya ve Ay",
        "2. Ünite: Canlılar Dünyası",
        "3. Ünite: Kuvvetin Ölçülmesi ve Sürtünme",
        "4. Ünite: Madde ve Değişim",
        "5. Ünite: Işığın Yayılması",
        "6. Ünite: İnsan ve Çevre",
        "7. Ünite: Elektrik Devre Elemanları"
    ],
    "Matematik": [
        "1. Ünite: Doğal Sayılar ve Doğal Sayılarla İşlemler",
        "2. Ünite: Kesirler",
        "3. Ünite: Ondalık Gösterim",
        "4. Ünite: Temel Geometrik Kavramlar ve Çizimler",
        "5. Ünite: Üçgen ve Dörtgenler",
        "6. Ünite: Veri Toplama ve Değerlendirme",
        "7. Ünite: Uzunluk ve Zaman Ölçme"
    ],
    "Türkçe": [
        "Sözcükte ve Söz Öbeklerinde Anlam",
        "Cümlede Anlam ve Yorum",
        "Paragraf Analizi ve Anlatım Biçimleri",
        "Yazım Kuralları ve Noktalama İşaretleri"
    ],
    "Sosyal Bilgiler": [
        "Birey ve Toplum",
        "Kültürel Mirasımız",
        "İnsanlar, Yerler ve Çevreler",
        "Bilim, Teknoloji ve Toplum"
    ]
}

# ==========================================
# 3. SECRETS.TOML API OKUYUCU ([api_keys])
# ==========================================
def load_secrets_api_keys():
    groq_list = []
    gemini_list = []
    try:
        if "api_keys" in st.secrets:
            api_section = st.secrets["api_keys"]
            if "groq_keys" in api_section:
                groq_list = list(api_section["groq_keys"])
            if "gemini_keys" in api_section:
                gemini_list = list(api_section["gemini_keys"])
    except Exception:
        pass
    return groq_list, gemini_list

# ==========================================
# 4. YÜK DENGELEMELİ AI YAZILI SORU ÜRETİCİ
# ==========================================
def generate_written_exam_with_ai(subject, unit):
    groq_keys, gemini_keys = load_secrets_api_keys()

    prompt = f"""
    Sen MEB 5. sınıf müfredatına tam uygun klasik yazılı sınavı hazırlayan uzman bir ilköğretim öğretmenisin.
    Ders: {subject}
    Ünite/Konu: {unit}

    Lütfen bu üniteye ait tam olarak 5 adet Çoktan Seçmeli (MCQ) ve 5 adet Açık Uçlu / Klasik (OPEN) olmak üzere toplam 10 soru içeren bir yazılı sınav kağıdı hazırla.
    Sorular MEB kazanımlarına tam uygun, nitelikli ve yazılı sınav formatında olmalıdır.

    SADECE VE SADECE GEÇERLİ JSON DÖNDÜR.
    Şablon:
    {{
        "questions": [
            {{
                "id": 1,
                "type": "MCQ",
                "question_text": "Soru metni...",
                "options": {{"A": "A şıkkı", "B": "B şıkkı", "C": "C şıkkı", "D": "D şıkkı"}},
                "correct_answer": "A",
                "solution_explanation": "Çözüm açıklaması...",
                "points": 10
            }},
            {{
                "id": 6,
                "type": "OPEN",
                "question_text": "Açık uçlu soru metni...",
                "options": {{}},
                "correct_answer": "İdeal öğretmen/öğrenci yanıtı...",
                "solution_explanation": "Değerlendirme açıklaması...",
                "points": 10
            }}
        ]
    }}
    """

    last_error = ""

    # Groq Anahtarlarını Dene
    if Groq and groq_keys:
        for key in groq_keys:
            try:
                client = Groq(api_key=key.strip())
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Sen JSON formatında çıktı veren bir MEB yazılı sınav hazırlama robotusun."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                text = completion.choices[0].message.content.strip()
                parsed = json.loads(text)
                if "questions" in parsed and len(parsed["questions"]) > 0:
                    return parsed["questions"], f"Groq API ({key[:6]}...)"
            except Exception as e:
                last_error = str(e)
                continue

    # Gemini Anahtarlarını Dene
    if genai and gemini_keys:
        for key in gemini_keys:
            try:
                genai.configure(api_key=key.strip())
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                text = response.text.strip()
                if text.startswith("```json"): text = text[7:-3].strip()
                elif text.startswith("```"): text = text[3:-3].strip()
                
                parsed = json.loads(text)
                if "questions" in parsed and len(parsed["questions"]) > 0:
                    return parsed["questions"], f"Gemini API ({key[:6]}...)"
            except Exception as e:
                last_error = str(e)
                continue

    # Yedek Statik Şablon (API yanıt vermezse)
    st.error(f"⚠️ API anahtarları yanıt vermedi. Hata: {last_error}")
    return get_fallback_exam_questions(subject, unit), "Yerel Güvenli Şablon"

def get_fallback_exam_questions(subject, unit):
    questions = []
    for i in range(1, 6):
        questions.append({
            "id": i, "type": "MCQ",
            "question_text": f"5. Sınıf {subject} ({unit}) ünitesiyle ilgili MEB kazanımına uygun test sorusu {i}?",
            "options": {"A": "Doğru seçenek", "B": "Çeldirici 1", "C": "Çeldirici 2", "D": "Çeldirici 3"},
            "correct_answer": "A",
            "solution_explanation": "Bu sorunun doğru yanıtı A seçeneğidir.",
            "points": 10
        })
    for i in range(6, 11):
        questions.append({
            "id": i, "type": "OPEN",
            "question_text": f"5. Sınıf {subject} ({unit}) ünitesiyle ilgili klasik açık uçlu soru {i-5}?",
            "options": {},
            "correct_answer": "Örnek ideal öğrenci yanıtı ve anahtar kelimeler.",
            "solution_explanation": "Bu soruda öğrenciden temel kavramları açıklaması beklenmektedir.",
            "points": 10
        })
    return questions

# ==========================================
# 5. STREAMLIT ARAYÜZÜ (KLASİK YAZILI FORMATI)
# ==========================================
if 'exam_data' not in st.session_state:
    st.session_state.exam_data = None
if 'show_answers' not in st.session_state:
    st.session_state.show_answers = False

st.sidebar.header("⚙️ Sınav ve Müfredat Ayarları")
selected_subject = st.sidebar.selectbox("📖 Ders Seçiniz", list(MEB_FULL_CURRICULUM.keys()))
selected_unit = st.sidebar.selectbox("📚 Ünite Seçiniz", MEB_FULL_CURRICULUM[selected_subject])

groq_k, gemini_k = load_secrets_api_keys()
st.sidebar.info(f"🔑 **Sistem Durumu:**\n- Groq Anahtar: {len(groq_k)} adet\n- Gemini Anahtar: {len(gemini_k)} adet")

st.sidebar.divider()

if st.sidebar.button("📝 Klasik Yazılı Sınavı Oluştur", use_container_width=True):
    with st.spinner("MEB formatına uygun yazılı kağıdı hazırlanıyor..."):
        questions, provider = generate_written_exam_with_ai(selected_subject, selected_unit)
        st.session_state.exam_data = {
            "school_name": "ŞEHİT ÖĞRETMEN 5. SINIF ORTAOKULU",
            "academic_year": "2026-2027 EĞİTİM-ÖĞRETİM YILI",
            "subject": selected_subject,
            "unit": selected_unit,
            "provider": provider,
            "questions": questions
        }
        st.session_state.show_answers = False
        st.success("✅ Yazılı sınav kağıdı başarıyla oluşturuldu!")

# Ana Ekran Yazılı Kağıdı Görünümü
if st.session_state.exam_data:
    exam = st.session_state.exam_data
    
    # Resmi Yazılı Başlığı (PDF Yok, Doğrudan Ekranda Kağıt Formatı)
    st.markdown(f"""
    <div class="exam-header">
        <h3 style="margin:0; font-weight:bold;">{exam['school_name']}</h3>
        <p style="margin:5px 0; font-size:14px;">{exam['academic_year']} 5. SINIF {exam['subject'].upper()} DERSİ</p>
        <h4 style="margin:5px 0; color:#1A237E;">{exam['unit'].upper()} DEĞERLENDİRME SINAVI</h4>
        <hr style="border:0.5px solid #ccc; margin:10px 0;">
        <table style="width:100%; font-size:14px; text-align:left; margin-top:10px;">
            <tr>
                <td><b>Adı Soyadı:</b> ....................................................</td>
                <td><b>Sınıf/Şube:</b> 5 / .......</td>
                <td><b>Numara:</b> .............</td>
                <td><b>ALDIĞI PUAN:</b> .......</td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    # Cevap Anahtarı Göster / Gizle Butonu
    col_b1, col_b2 = st.columns([1, 4])
    with col_b1:
        if st.button("🔑 Cevap Anahtarını Aç/Kapat"):
            st.session_state.show_answers = not st.session_state.show_answers
            st.rerun()

    st.divider()

    # Soruları Listele (Klasik Yazılı Formatı - Tüm Sorular Alt Alta)
    for q in exam['questions']:
        q_id = q['id']
        q_type_str = "Çoktan Seçmeli" if q['type'] == 'MCQ' else "Açık Uçlu / Klasik"
        
        st.markdown(f"""
        <div class="question-box">
            <div style="font-size:12px; color:#555; margin-bottom:5px;"><b>[{q_type_str}]</b> ({q.get('points', 10)} Puan)</div>
            <div style="font-size:16px; font-weight:600; color:#222;">Soru {q_id}: {q['question_text']}</div>
        </div>
        """, unsafe_allow_html=True)

        if q['type'] == 'MCQ':
            opts = q.get('options', {})
            for key, val in opts.items():
                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>{key})</b> {val}")
        else:
            st.markdown("""
            <div style="border-bottom: 1px dashed #999; height: 35px; margin-top: 10px;"></div>
            <div style="border-bottom: 1px dashed #999; height: 35px; margin-top: 10px;"></div>
            """, unsafe_allow_html=True)

        # Cevap Anahtarı Açıksa Göster
        if st.session_state.show_answers:
            st.markdown(f"""
            <div class="answer-box">
                <b>Doğru Cevap / İdeal Yanıt:</b> {q.get('correct_answer', '')}<br>
                <b>Açıklama / Çözüm:</b> {q.get('solution_explanation', '')}
            </div>
            """, unsafe_allow_html=True)

        st.write("")

else:
    st.info("👈 Sınav kağıdı oluşturmak için sol menüden dersinizi ve ünitenizi seçip **'Klasik Yazılı Sınavı Oluştur'** butonuna tıklayınız.")
