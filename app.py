# -*- coding: utf-8 -*-
import streamlit as st
import random
import json
import os
import time
import io
import matplotlib.pyplot as plt
import numpy as np

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
    page_title="MEB Sınav Takvimi & İnteraktif Çizim Modülü - Murat KANDIRMAZ",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .exam-header {
        border: 2px solid #333;
        padding: 15px 20px;
        border-radius: 8px;
        background-color: #fff;
        color: #000;
        margin-bottom: 20px;
        text-align: center;
    }
    .question-card {
        background-color: #ffffff;
        border: 1px solid #ccc;
        border-left: 6px solid #1A237E;
        border-radius: 8px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.06);
        color: #000;
    }
    .answer-box {
        background-color: #e8f5e9;
        border: 1px solid #2e7d32;
        padding: 15px;
        border-radius: 6px;
        margin-top: 15px;
        color: #1b5e20;
    }
    .report-card {
        background-color: #f9fbe7;
        border: 2px solid #c0ca33;
        border-radius: 12px;
        padding: 25px;
        margin-bottom: 25px;
        color: #333;
    }
    .ai-feedback {
        background-color: #e3f2fd;
        border-left: 5px solid #1e88e5;
        padding: 12px;
        border-radius: 4px;
        margin-top: 8px;
        color: #0d47a1;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MEB 5. SINIF DÖNEM VE SINAV TAKVİMİ
# ==========================================
MEB_EXAM_SCHEDULE = {
    "Fen Bilimleri": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": "Gökyüzündeki Komşularımız ve Biz (Güneş, Dünya ve Ay'ın hareketleri, Ay'ın evreleri ve Ay modelleri) / Kuvveti Tanıyalım (Kuvvetin ölçülmesi ve dinamometreler, kütle-ağırlık ilişkisi, sürtünme kuvveti)",
        "1. Dönem 2. Yazılı (Aralık/Ocak)": "Madde ve Değişim / Işığın Yayılması",
        "2. Dönem 1. Yazılı (Mart/Nisan)": "Işığın Yansıması ve Madde ile Etkileşimi / İnsan ve Çevre",
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": "Elektrik Devre Elemanları ve Genel Yıl Sonu Değerlendirmesi"
    },
    "Matematik": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": "4. Tema: Geometrik Şekiller (Temel geometrik kavramlar, açı ölçüleri, çokgenler, çember ve daire) / 5. Tema: Geometrik Nicelikler (Uzunluk ölçme, dikdörtgenin çevre ve alanı)",
        "1. Dönem 2. Yazılı (Aralık/Ocak)": "Doğal Sayılar ve İşlemler / Kesirler ve Ondalık Gösterim",
        "2. Dönem 1. Yazılı (Mart/Nisan)": "Üçgen ve Dörtgenlerin Açı/Kenar Özellikleri / Veri Toplama",
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": "Zaman Ölçme Birimleri, Sıvı Ölçme ve Genel Tekrar"
    },
    "Türkçe": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": "Sözcükte ve Söz Öbeklerinde Anlam / Yazım Kuralları",
        "1. Dönem 2. Yazılı (Aralık/Ocak)": "Cümlede Anlam ve Paragraf Analizi",
        "2. Dönem 1. Yazılı (Mart/Nisan)": "Metin Türleri ve Söz Sanatları",
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": "Okuduğunu Anlama ve Yıl Sonu Genel Değerlendirme"
    },
    "Sosyal Bilgiler": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": "Birey ve Toplum / Haklarım ve Sorumluluklarım",
        "1. Dönem 2. Yazılı (Aralık/Ocak)": "Kültürel Mirasımız ve Çevremizdeki Tarihi Eserler",
        "2. Dönem 1. Yazılı (Mart/Nisan)": "İnsanlar, Yerler ve Çevreler / Doğal Afetler",
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": "Bilim, Teknoloji ve Toplum / Üretim, Tüketim"
    }
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
# 4. DEĞER UYUMLU MATPLOTLIB GÖRSEL ÇİZİM MOTORU
# ==========================================
def generate_question_image(diagram_type, custom_val=""):
    fig, ax = plt.subplots(figsize=(3.8, 2.6), dpi=130)
    
    if diagram_type == "sun_earth_moon":
        sun = plt.Circle((0.8, 2), 0.6, color='#FF8C00')
        earth = plt.Circle((3.2, 2), 0.35, color='#1E90FF')
        moon = plt.Circle((4.3, 2), 0.12, color='#A9A9A9')
        ax.add_patch(sun)
        ax.add_patch(earth)
        ax.add_patch(moon)
        ax.text(0.8, 1.1, 'Güneş', ha='center', fontweight='bold', color='#FF8C00', fontsize=8)
        ax.text(3.2, 1.3, 'Dünya', ha='center', fontweight='bold', color='#1E90FF', fontsize=8)
        ax.text(4.3, 1.6, 'Ay', ha='center', fontweight='bold', color='#A9A9A9', fontsize=8)
        ax.set_xlim(0, 5)
        ax.set_ylim(0.5, 3.5)
        ax.axis('off')

    elif diagram_type == "moon_phases":
        circle = plt.Circle((2, 2), 1.2, color='#333333', fill=True)
        ax.add_patch(circle)
        theta = np.linspace(-np.pi/2, np.pi/2, 100)
        x = 2 + 1.2 * np.cos(theta)
        y = 2 + 1.2 * np.sin(theta)
        ax.fill_betweenx(y, 2, x, color='#FFD700', alpha=0.9)
        ax.text(2, 0.4, "Ay Evresi Modeli", ha='center', fontsize=9, fontweight='bold', color='#333333')
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 4)
        ax.axis('off')

    elif diagram_type == "dynamometer":
        ax.plot([2, 2], [3.5, 3.8], color='black', linewidth=3)
        ax.plot([1.6, 2.4], [3.5, 3.5], color='black', linewidth=3)
        y_vals = np.linspace(1.8, 3.5, 15)
        x_vals = 2 + 0.18 * np.sin(np.linspace(0, 4*np.pi, 15))
        ax.plot(x_vals, y_vals, color='#FF6B00', linewidth=2.5)
        rect = plt.Rectangle((1.4, 1.0), 1.2, 2.7, fill=False, edgecolor='gray', linewidth=1.5, linestyle='--')
        ax.add_patch(rect)
        ax.plot([2, 2], [0.75, 1.0], color='black', linewidth=2)
        weight = plt.Rectangle((1.65, 0.2), 0.7, 0.55, color='#1E90FF')
        ax.add_patch(weight)
        label_text = f"Yük: {custom_val}" if custom_val else "Ölçüm (N)"
        ax.text(2, 0.47, label_text, color='white', fontsize=7.5, fontweight='bold', ha='center', va='center')
        ax.set_xlim(0.8, 3.2)
        ax.set_ylim(0, 4)
        ax.axis('off')

    elif diagram_type == "right_triangle":
        p1, p2, p3 = [0.5, 0.5], [3.5, 0.5], [0.5, 3.0]
        triangle = plt.Polygon([p1, p2, p3], fill=None, edgecolor='#1A237E', linewidth=2.5)
        ax.add_patch(triangle)
        ax.plot([0.5, 0.9, 0.9, 0.5], [0.5, 0.5, 0.9, 0.5], color='red', linewidth=1.5)
        ax.text(1.8, 1.4, f"Dik Üçgen\n{custom_val}", fontsize=8.5, color='#1A237E', fontweight='bold', ha='center')
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 3.5)
        ax.axis('off')

    elif diagram_type == "scalene_triangle":
        p1, p2, p3 = [0.5, 0.5], [3.8, 0.8], [1.5, 3.0]
        triangle = plt.Polygon([p1, p2, p3], fill=None, edgecolor='#FF6B00', linewidth=2.5)
        ax.add_patch(triangle)
        ax.text(1.8, 1.4, f"Çeşitkenar\n{custom_val}", fontsize=8.5, color='#FF6B00', fontweight='bold', ha='center')
        ax.set_xlim(0, 4.5)
        ax.set_ylim(0, 3.5)
        ax.axis('off')

    elif diagram_type == "isosceles_triangle":
        p1, p2, p3 = [0.8, 0.5], [3.2, 0.5], [2.0, 3.0]
        triangle = plt.Polygon([p1, p2, p3], fill=None, edgecolor='#2E7D32', linewidth=2.5)
        ax.add_patch(triangle)
        ax.text(2.0, 1.5, f"İkizkenar\n{custom_val}", fontsize=8.5, color='#2E7D32', fontweight='bold', ha='center')
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 3.5)
        ax.axis('off')

    elif diagram_type == "ray_segment":
        ax.plot([0.5, 3.5], [2, 2], color='#1A237E', linewidth=2.5, marker='o')
        ax.text(0.5, 2.25, 'A', fontsize=10, fontweight='bold')
        ax.text(3.5, 2.25, 'B', fontsize=10, fontweight='bold')
        label_str = custom_val if custom_val else "[AB] Doğru Parçası"
        ax.text(2, 1.4, label_str, fontsize=9, fontweight='bold', color='#333333', ha='center')
        ax.set_xlim(0, 4)
        ax.set_ylim(1, 3)
        ax.axis('off')

    elif diagram_type == "circle_radius":
        circle = plt.Circle((2, 2), 1.2, fill=False, edgecolor='#FF6B00', linewidth=2.5)
        ax.add_patch(circle)
        ax.plot([2, 3.2], [2, 2], color='#1E90FF', linewidth=2, marker='o')
        rad_label = f"r = {custom_val}" if custom_val else "r = 6 cm"
        ax.text(2.6, 2.15, rad_label, color='#1E90FF', fontsize=9, fontweight='bold')
        ax.plot(2, 2, marker='o', color='black')
        ax.text(1.85, 1.85, 'M', fontsize=8, fontweight='bold')
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 4)
        ax.axis('off')

    else:
        plt.close(fig)
        return None
        
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    buf.seek(0)
    plt.close(fig)
    return buf

# ==========================================
# 5. YÜK DENGELEMELİ AI YAZILI SORU ÜRETİCİ
# ==========================================
def generate_written_exam_with_ai(subject, exam_period, scope):
    groq_keys, gemini_keys = load_secrets_api_keys()

    prompt = f"""
    Sen MEB 5. sınıf müfredatına ve resmi sınav takvimine tam uygun klasik yazılı sınavı hazırlayan uzman bir ilköğretim öğretmenisin.
    Ders: {subject}
    Sınav Dönemi: {exam_period}
    Kapsanan Konular/Üniteler: {scope}

    Lütfen bu döneme ait tam olarak 5 adet Çoktan Seçmeli (MCQ) ve 5 adet Açık Uçlu / Klasik (OPEN) olmak üzere toplam 10 soru içeren bir yazılı sınav kağıdı hazırla.
    Sorular MEB kazanımlarına tam uygun, nitelikli ve yazılı sınav formatında olmalıdır.
    
    ÖNEMLİ (Görsel ve Değer Uyumu): 
    Görsel içeren sorular için "has_diagram": true yap, "diagram_type" alanını şu uygun değerlerden biri seç:
    ['sun_earth_moon', 'moon_phases', 'dynamometer', 'right_triangle', 'scalene_triangle', 'isosceles_triangle', 'ray_segment', 'circle_radius']
    Ayrıca soru metninde kullanılan sayısal değerleri (örn: "r = 5 cm" veya "30 N") "diagram_value" alanına string olarak mutlaka ekle (Görselin üzerine bu değer basılacaktır).
    Görsel gerekmeyen sorular için "has_diagram": false, "diagram_type": null ve "diagram_value": null yap.

    SADECE VE SADECE GEÇERLİ JSON DÖNDÜR.
    Şablon:
    {{
        "questions": [
            {{
                "id": 1,
                "type": "MCQ",
                "question_text": "Yarıçapı 5 cm olan bir çemberin...",
                "options": {{"A": "30 cm", "B": "25 cm", "C": "20 cm", "D": "15 cm"}},
                "correct_answer": "A",
                "solution_explanation": "Çözüm açıklaması...",
                "points": 10,
                "has_diagram": true,
                "diagram_type": "circle_radius",
                "diagram_value": "5 cm"
            }}
        ]
    }}
    """

    last_error = ""

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

    if genai and gemini_keys:
        for key in gemini_keys:
            try:
                genai.configure(api_key=key.strip())
                model = genai.GenerativeModel('gemini-3.6-flash')
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

    st.error(f"⚠️ API anahtarları yanıt vermedi. Hata: {last_error}")
    return get_fallback_exam_questions(subject, exam_period), "Yerel Güvenli Şablon"

def get_fallback_exam_questions(subject, exam_period):
    questions = []
    diag_types = ["right_triangle", "scalene_triangle", "isosceles_triangle", "ray_segment", "circle_radius"] if "Matematik" in subject else ["sun_earth_moon", "moon_phases", "dynamometer"]
    diag_vals = ["6 cm", "8 cm", "10 cm", "15 cm", "20 N"]
    
    for i in range(1, 6):
        questions.append({
            "id": i, "type": "MCQ",
            "question_text": f"5. Sınıf {subject} ({exam_period}) dönemi görsel destekli örnek test sorusu {i}?",
            "options": {"A": "Doğru seçenek", "B": "Çeldirici 1", "C": "Çeldirici 2", "D": "Çeldirici 3"},
            "correct_answer": "A",
            "solution_explanation": "Bu sorunun doğru yanıtı A seçeneğidir.",
            "points": 10,
            "has_diagram": True,
            "diagram_type": diag_types[(i-1) % len(diag_types)],
            "diagram_value": diag_vals[(i-1) % len(diag_vals)]
        })
    for i in range(6, 11):
        questions.append({
            "id": i, "type": "OPEN",
            "question_text": f"5. Sınıf {subject} ({exam_period}) dönemi klasik açık uçlu soru {i-5}?",
            "options": {},
            "correct_answer": "Örnek ideal öğrenci yanıtı ve anahtar kelimeler.",
            "solution_explanation": "Bu soruda öğrenciden temel kavramları açıklaması beklenmektedir.",
            "points": 10,
            "has_diagram": False,
            "diagram_type": None,
            "diagram_value": None
        })
    return questions

# ==========================================
# 6. YAPAY ZEKA ÖĞRETMEN DEĞERLENDİRME MOTORU
# ==========================================
def evaluate_open_questions_with_ai(open_eval_list):
    groq_keys, gemini_keys = load_secrets_api_keys()

    prompt = f"""
    Sen adil ve rehberlik edici bir MEB 5. sınıf öğretmenisisin.
    Aşağıdaki açık uçlu soruları, ideal cevapları ve öğrencilerin verdiği cevapları incele.
    Her soru maksimum 10 puandır. Öğrencinin cevabını doğruluk, kilit kavramlar ve eksiksiz anlatım bakımından 0 ile 10 arasında puanla ve kısa bir öğretmen dönütü yaz.

    Gelen Sorular ve Öğrenci Yanıtları:
    {json.dumps(open_eval_list, ensure_ascii=False)}

    SADECE VE SADECE GEÇERLİ JSON DÖNDÜR.
    Format Şablonu:
    {{
        "evaluations": [
            {{
                "id": 6,
                "score": 8,
                "feedback": "Cevabın büyük oranda doğru ancak eksik kavramlar var."
            }}
        ]
    }}
    """

    if Groq and groq_keys:
        for key in groq_keys:
            try:
                client = Groq(api_key=key.strip())
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Sen JSON çıktısı veren bir MEB sınav değerlendirme öğretmenisisin."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                text = completion.choices[0].message.content.strip()
                parsed = json.loads(text)
                if "evaluations" in parsed:
                    return {item["id"]: item for item in parsed["evaluations"]}
            except Exception:
                continue

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
                if "evaluations" in parsed:
                    return {item["id"]: item for item in parsed["evaluations"]}
            except Exception:
                continue

    fallback_eval = {}
    for item in open_eval_list:
        ans = item.get("user_answer", "").strip()
        score = 10 if len(ans) > 15 else (5 if len(ans) > 0 else 0)
        fallback_eval[item["id"]] = {
            "id": item["id"],
            "score": score,
            "feedback": "Açıklamanız yerel kontrol mekanizması ile değerlendirildi."
        }
    return fallback_eval

# ==========================================
# 7. STREAMLIT ARAYÜZÜ & STATE YÖNETİMİ
# ==========================================
if 'exam_data' not in st.session_state:
    st.session_state.exam_data = None
if 'exam_started' not in st.session_state:
    st.session_state.exam_started = False
if 'exam_completed' not in st.session_state:
    st.session_state.exam_completed = False
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'ai_evaluations' not in st.session_state:
    st.session_state.ai_evaluations = {}
if 'show_canvas' not in st.session_state:
    st.session_state.show_canvas = False

st.sidebar.header("⚙️ Sınav Takvimi & Müfredat")
selected_subject = st.sidebar.selectbox("📖 Ders Seçiniz", list(MEB_EXAM_SCHEDULE.keys()))
selected_period = st.sidebar.selectbox("📅 Sınav Dönemi Seçiniz", list(MEB_EXAM_SCHEDULE[selected_subject].keys()))

unit_scope = MEB_EXAM_SCHEDULE[selected_subject][selected_period]
st.sidebar.info(f"📌 **Dönem Kapsamı:**\n{unit_scope}")

groq_k, gemini_k = load_secrets_api_keys()
st.sidebar.info(f"🔑 **Sistem Durumu:**\n- Groq Anahtar: {len(groq_k)} adet\n- Gemini Anahtar: {len(gemini_k)} adet")

st.sidebar.divider()

if st.sidebar.button("📝 Dönem Sınav Kağıdı Hazırla", use_container_width=True):
    with st.spinner("MEB sınav takvimine uygun değer uyumlu sorular hazırlanıyor..."):
        questions, provider = generate_written_exam_with_ai(selected_subject, selected_period, unit_scope)
        st.session_state.exam_data = {
            "school_name": "ŞEHİT ÖĞRETMEN 5. SINIF ORTAOKULU",
            "academic_year": "2026-2027 EĞİTİM-ÖĞRETİM YILI",
            "subject": selected_subject,
            "period": selected_period,
            "scope": unit_scope,
            "provider": provider,
            "questions": questions
        }
        st.session_state.exam_started = False
        st.session_state.exam_completed = False
        st.session_state.current_question_index = 0
        st.session_state.user_answers = {}
        st.session_state.ai_evaluations = {}
        st.success("✅ Sınav soruları ve görsel şemaları hazırlandı! Başlatmak için butona tıklayınız.")

# --- DURUM 1: SORULAR HAZIR ANCAK SINAV BAŞLAMADI ---
if st.session_state.exam_data and not st.session_state.exam_started and not st.session_state.exam_completed:
    exam = st.session_state.exam_data
    st.markdown(f"""
    <div class="exam-header">
        <h3 style="margin:0; font-weight:bold;">{exam['school_name']}</h3>
        <p style="margin:4px 0; font-size:14px;">{exam['academic_year']} 5. SINIF {exam['subject'].upper()} DERSİ</p>
        <h4 style="margin:4px 0; color:#1A237E;">{exam['period'].upper()}</h4>
        <p style="margin:2px 0; font-size:12px; color:#555;">(Kapsam: {exam['scope']})</p>
        <hr style="border:0.5px solid #ccc; margin:15px 0;">
        <p style="font-size:16px; color:#2e7d32; font-weight:bold;">🎉 Sınav soruları ve görselleri hazır!</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 SINAVI BAŞLAT", type="primary", use_container_width=True):
        st.session_state.exam_started = True
        st.session_state.start_time = time.time()
        st.session_state.current_question_index = 0
        st.rerun()

# --- DURUM 2: SINAV DEVAM EDİYOR (HER SAYFADA TEK SORU & İNTERAKTİF KALEM) ---
elif st.session_state.exam_started and not st.session_state.exam_completed:
    exam = st.session_state.exam_data
    questions = exam['questions']
    total_q = len(questions)
    curr_idx = st.session_state.current_question_index
    current_q = questions[curr_idx]
    q_id = current_q['id']

    elapsed_time = int(time.time() - st.session_state.start_time)
    minutes, seconds = divmod(elapsed_time, 60)

    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        st.markdown(f"### 📝 Soru {curr_idx + 1} / {total_q}")
    with col_h2:
        st.markdown(f"**⏱️ Geçen Süre:** `{minutes:02d}:{seconds:02d}`")

    st.progress((curr_idx + 1) / total_q)
    st.divider()

    q_type_str = "Çoktan Seçmeli" if current_q['type'] == 'MCQ' else "Açık Uçlu / Klasik"
    st.markdown(f"""
    <div class="question-card">
        <div style="font-size:13px; color:#555; margin-bottom:8px;">
            <b>[{q_type_str}]</b> ({current_q.get('points', 10)} Puan)
        </div>
        <div style="font-size:18px; font-weight:600; color:#111; margin-bottom:15px;">
            {current_q['question_text']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Değer Uyumlu Görsel Çizim Entegrasyonu
    if current_q.get('has_diagram') and current_q.get('diagram_type'):
        d_val = current_q.get('diagram_value', '')
        img_buf = generate_question_image(current_q['diagram_type'], d_val)
        if img_buf:
            st.image(img_buf, width=340)

    # İnteraktif Kalem (Çizim Tahtası) Aç/Kapat Butonu
    col_btn_c1, col_btn_c2 = st.columns([1, 4])
    with col_btn_c1:
        if st.button("✏️ Çizim Kalemini Aç/Kapat"):
            st.session_state.show_canvas = not st.session_state.show_canvas
            st.rerun()

    if st.session_state.show_canvas:
        st.info("💡 Not: Aşağıdaki interaktif alanda dilediğiniz gibi çizim yapabilir, işaretleme ekleyebilirsiniz.")
        try:
            from streamlit_drawable_canvas import st_canvas
            st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=3,
                stroke_color="#FF6B00",
                background_color="#ffffff",
                height=200,
                width=500,
                drawing_mode="freedraw",
                key=f"canvas_q_{q_id}",
            )
        except ImportError:
            st.warning("⚠️ 'streamlit_drawable_canvas' kütüphanesi yüklü değil. Terminale `pip install streamlit-drawable-canvas` yazarak aktif edebilirsiniz.")

    saved_ans = st.session_state.user_answers.get(q_id, None)

    if current_q['type'] == 'MCQ':
        opts = current_q.get('options', {})
        formatted_opts = [f"{k}) {v}" for k, v in opts.items()]
        
        default_index = None
        if saved_ans:
            for idx, opt_str in enumerate(formatted_opts):
                if opt_str.startswith(saved_ans):
                    default_index = idx
                    break

        selected = st.radio("Cevabınızı seçiniz:", formatted_opts, key=f"radio_q_{q_id}", index=default_index)
        if selected:
            st.session_state.user_answers[q_id] = selected[0]
    else:
        user_text = st.text_area("Cevabınızı buraya yazınız:", value=saved_ans if saved_ans else "", key=f"textarea_q_{q_id}")
        if user_text:
            st.session_state.user_answers[q_id] = user_text

    st.markdown("<br/>", unsafe_allow_html=True)

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav1:
        if curr_idx > 0:
            if st.button("⬅️ Önceki Soru", use_container_width=True):
                st.session_state.current_question_index -= 1
                st.rerun()

    with col_nav3:
        if curr_idx < total_q - 1:
            if st.button("Sonraki Soru ➡️", type="primary", use_container_width=True):
                st.session_state.current_question_index += 1
                st.rerun()

    st.divider()

    if st.button("🛑 SINAVI BİTİR VE KARNEYİ GÖR", type="secondary", use_container_width=True):
        st.session_state.exam_started = False
        st.session_state.exam_completed = True
        
        with st.spinner("🤖 Yapay zeka öğretmen açık uçlu cevaplarınızı inceliyor ve 100 üzerinden notlandırıyor..."):
            open_eval_list = []
            for q in questions:
                if q['type'] == 'OPEN':
                    open_eval_list.append({
                        "id": q['id'],
                        "question_text": q['question_text'],
                        "correct_answer": q['correct_answer'],
                        "user_answer": st.session_state.user_answers.get(q['id'], "")
                    })
            st.session_state.ai_evaluations = evaluate_open_questions_with_ai(open_eval_list)
            
        st.rerun()

# --- DURUM 3: SINAV BİTTİ & KARNE (100 ÜZERİNDEN TAM DEĞERLENDİRME) ---
elif st.session_state.exam_completed:
    st.balloons()
    exam = st.session_state.exam_data
    questions = exam['questions']

    mcq_correct = 0
    mcq_wrong = 0
    mcq_empty = 0
    mcq_score = 0
    open_score = 0

    for q in questions:
        q_id = q['id']
        user_ans = st.session_state.user_answers.get(q_id, None)
        if q['type'] == 'MCQ':
            if not user_ans:
                mcq_empty += 1
            elif user_ans == q.get('correct_answer'):
                mcq_correct += 1
                mcq_score += 10
            else:
                mcq_wrong += 1
        elif q['type'] == 'OPEN':
            eval_data = st.session_state.ai_evaluations.get(q_id, {})
            open_score += eval_data.get('score', 0)

    total_100_score = mcq_score + open_score

    st.markdown(f"""
    <div class="report-card">
        <h2 style="color: #1b5e20; text-align: center; margin-bottom: 5px;">📊 YAZILI SINAV SONUÇ KARNESİ</h2>
        <h1 style="text-align: center; color: #1A237E; font-size: 48px; margin: 10px 0;">{total_100_score} / 100</h1>
        <p style="text-align: center; color: #558B2F; font-weight: bold;">{exam['subject']} - {exam['period']}</p>
    </div>
    """, unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("100 Üzerinden Toplam Not", f"{total_100_score}")
    k2.metric("Test Puanı (5 Soru)", f"{mcq_score} / 50")
    k3.metric("Açık Uçlu AI Puanı (5 Soru)", f"{open_score} / 50")
    k4.metric("Test Doğru / Yanlış", f"{mcq_correct} D / {mcq_wrong} Y")

    st.divider()
    st.subheader("📝 Detaylı Soru İncelemesi ve Yapay Zeka Öğretmen Dönütleri")

    for q in questions:
        q_id = q['id']
        user_ans = st.session_state.user_answers.get(q_id, "Yanıt Verilmedi")
        correct_ans = q.get('correct_answer', '')

        st.markdown(f"**Soru {q_id}: {q['question_text']}**")
        
        if q.get('has_diagram') and q.get('diagram_type'):
            d_val = q.get('diagram_value', '')
            img_buf = generate_question_image(q['diagram_type'], d_val)
            if img_buf:
                st.image(img_buf, width=300)

        if q['type'] == 'MCQ':
            is_correct = (user_ans == correct_ans)
            if is_correct:
                st.success(f"✅ **Doğru! (+10 Puan)** Cevabınız: **{user_ans}**")
            else:
                st.error(f"❌ **Yanlış! (0 Puan)** Doğru Cevap: **{correct_ans}** | Sizin Cevabınız: **{user_ans}**")
        else:
            eval_info = st.session_state.ai_evaluations.get(q_id, {})
            q_score = eval_info.get('score', 0)
            feedback = eval_info.get('feedback', 'Değerlendirme yapıldı.')

            st.warning(f"📝 **Sizin Yanıtınız:** {user_ans if user_ans else 'Boş Bırakıldı'}\n\n**İdeal/Örnek Cevap:** {correct_ans}")
            st.markdown(f"""
            <div class="ai-feedback">
                <b>👨‍🏫 Yapay Zeka Öğretmen Puanı: {q_score} / 10</b><br>
                <b>💬 Öğretmen Dönütü:</b> {feedback}
            </div>
            """, unsafe_allow_html=True)

        with st.expander("🔍 Detaylı Adım Adım Çözüm Açıklaması"):
            st.write(q.get('solution_explanation', 'Çözüm açıklaması bulunamadı.'))
        st.write("---")

    if st.button("🔄 Yeni Sınav Hazırla", use_container_width=True):
        st.session_state.exam_data = None
        st.session_state.exam_started = False
        st.session_state.exam_completed = False
        st.session_state.ai_evaluations = {}
        st.rerun()

else:
    st.info("👈 Sınav kağıdı oluşturmak için sol menüden dersinizi ve döneminizi seçip **'Dönem Sınav Kağıdı Hazırla'** butonuna tıklayınız.")
