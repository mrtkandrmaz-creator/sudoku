import streamlit as st
import random
import json
import re
import io
import time
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# ReportLab Imports for Professional PDF Generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# API SDKs
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM CSS
# ==========================================
st.set_page_config(
    page_title="Soru Fabrikası (Murat KANDIRMAZ) - MEB 5. Sınıf",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Header Bar Styling */
    .header-bar {
        background: linear-gradient(90deg, #FF6B00 0%, #FF8800 100%);
        padding: 18px 25px;
        border-radius: 12px;
        color: white;
        font-weight: 700;
        font-size: 24px;
        box-shadow: 0 4px 15px rgba(255, 107, 0, 0.3);
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-sub {
        font-size: 14px;
        font-weight: 400;
        opacity: 0.9;
    }
    
    /* Quiz & Question Card Styling */
    .question-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-left: 6px solid #FF6B00;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .badge-mcq {
        background-color: #e3f2fd;
        color: #0d47a1;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
    }
    .badge-open {
        background-color: #fbe9e7;
        color: #d84315;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Custom Header Bar
st.markdown("""
<div class="header-bar">
    <div>🎓 MEB 5. Sınıf Soru Fabrikası <span style="font-size: 18px;">(Murat KANDIRMAZ)</span></div>
    <div class="header-sub">Yazılı Öncesi Akıllı Sınav & Çalışma Hazırlık Robotu</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. SECRET TARAMA & DİNAMİK API KULLANIMI
# ==========================================
def extract_api_keys():
    """
    secrets.toml içerisindeki [api_keys] altındaki listeleri ve 
    diğer tüm Gemini / Groq anahtarlarını otomatik tespit eder.
    """
    gemini_keys = []
    groq_keys = []
    
    def parse_value(key_name, val):
        key_upper = str(key_name).upper()
        if isinstance(val, str):
            if "GEMINI" in key_upper:
                gemini_keys.append(val.strip())
            elif "GROQ" in key_upper:
                groq_keys.append(val.strip())
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    if "GEMINI" in key_upper:
                        gemini_keys.append(item.strip())
                    elif "GROQ" in key_upper:
                        groq_keys.append(item.strip())

    def search_dict(d):
        for k, v in d.items():
            if isinstance(v, dict):
                search_dict(v)
            else:
                parse_value(k, v)
                    
    try:
        search_dict(st.secrets)
    except Exception:
        pass
        
    return list(set(gemini_keys)), list(set(groq_keys))

GEMINI_KEYS, GROQ_KEYS = extract_api_keys()

def generate_llm_response(prompt):
    """
    Tüm Gemini ve Groq API'lerini sırayla dener (Load-balancer / Fallback).
    Bir API hata verirse/limite takılırsa diğerine geçer.
    """
    providers = []
    for k in GEMINI_KEYS:
        providers.append(("gemini", k))
    for k in GROQ_KEYS:
        providers.append(("groq", k))
        
    random.shuffle(providers) # Yük dağılımı
    
    if not providers:
        st.error("🚨 `.streamlit/secrets.toml` içerisinde geçerli Gemini veya Groq API Anahtarı bulunamadı!")
        return None

    last_error = ""
    for provider_type, api_key in providers:
        try:
            if provider_type == "gemini" and genai:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.7, "response_mime_type": "application/json"}
                )
                return response.text
            elif provider_type == "groq" and Groq:
                client = Groq(api_key=api_key)
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "Sen MEB müfredatına %100 uyumlu JSON formatında çıktı üreten uzman bir öğretmensin."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"}
                )
                return chat_completion.choices[0].message.content
        except Exception as e:
            last_error = str(e)
            continue
            
    st.error(f"Tüm API denemeleri başarısız oldu. Son hata: {last_error}")
    return None

# ==========================================
# 3. MEB MÜFREDAT VE SINAV DÖNEMLERİ DATA
# ==========================================
MEB_CURRICULUM = {
    "Matematik": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Doğal Sayılar (Okuma, Yazma, Bölükler)", "Doğal Sayılarla Toplama ve Çıkarma İşlemleri"],
        "1. Dönem 2. Yazılı (Aralık/Ocak)": ["Doğal Sayılarla Çarpma ve Bölme İşlemleri", "Kesirler (Bileşik, Tam Sayılı Kesirler)", "Kesirlerle Toplama ve Çıkarma"],
        "2. Dönem 1. Yazılı (Mart/Nisan)": ["Ondalık Gösterim (Basamak Değerleri, Yuvarlama)", "Yüzdeler", "Temel Geometrik Kavramlar ve Çizimler"],
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": ["Üçgen ve Dörtgenler (Açılar, Özellikler)", "Veri Toplama ve Değerlendirme", "Uzunluk ve Zaman Ölçme", "Alan Ölçme"]
    },
    "Fen Bilimleri": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Güneş'in Yapısı ve Özellikleri", "Dünya'nın Şekli ve Hareketleri"],
        "1. Dönem 2. Yazılı (Aralık/Ocak)": ["Ay'ın Yapısı, Özellikleri ve Evreleri", "Dünya, Güneş ve Ay Sistemleri"],
        "2. Dönem 1. Yazılı (Mart/Nisan)": ["Canlıları Tanıyalım (Mikroskobik Canlılar, Mantarlar, Bitkiler, Hayvanlar)", "Kuvvetin Ölçülmesi ve Sürtünme"],
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": ["Maddenin Hal Değişimi", "Maddenin Ayırt Edici Özellikleri", "Işığın Yayılması ve Yansıması", "Işık ve Gölge"]
    },
    "Türkçe": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Sözcükte Anlam (Gerçek, Mecaz, Terim)", "Söz Sanatları"],
        "1. Dönem 2. Yazılı (Aralık/Ocak)": ["Cümlede Anlam (Neden-Sonuç, Amaç-Sonuç)", "Paragrafta Ana Fikir ve Yardımcı Fikir"],
        "2. Dönem 1. Yazılı (Mart/Nisan)": ["Noktalama İşaretleri ve Yazım Kuralları", "Metin Türleri (Hikaye, Masal, Fabl)"],
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": ["Görsel Okuma ve Grafikler", "Sözel Mantık ve Akıl Yürütme"]
    },
    "Sosyal Bilgiler": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Birey ve Toplum (Haklar, Sorumluluklar, Rolleri)"],
        "1. Dönem 2. Yazılı (Aralık/Ocak)": ["Kültür ve Miras (Anadolu ve Mezopotamya Uygarlıkları)", "Çevremizdeki Doğal ve Beşeri Unsurlar"],
        "2. Dönem 1. Yazılı (Mart/Nisan)": ["İnsanlar, Yerler ve Çevreler (Yeryüzü Şekilleri, İklim, İnsan Faaliyetleri)"],
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": ["Üretim, Tüketim ve Dağıtım", "Etkin Vatandaşlık (Yönetim Biçimleri, Katılım)"]
    },
    "Din Kültürü ve Ahlak Bilgisi": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Allah İnancı (Allah Vardır ve Birdir, Allah Yaradandır)", "İhlas Suresi ve Anlamı"],
        "1. Dönem 2. Yazılı (Aralık/Ocak)": ["Ramazan ve Oruç (Oruç İbadeti, Sahur, İftar, Teravih)", "Kültürümüzde Ramazan ve Oruç"],
        "2. Dönem 1. Yazılı (Mart/Nisan)": ["Adap ve Nezaket (Nezaket Kuralları, Selamlaşma Adabı, İletişim)", "Tahiyyat Duası ve Anlamı"],
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": ["Hz. Muhammed ve Aile Hayatı (Peygamberimizin Ailesi)", "Çevremizde Dinin İzleri (Mimaride, Musikide, Edebiyatta)"]
    },
    "İngilizce": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Unit 1: Hello (Greetings, Countries, Nationalities, School Subjects)"],
        "1. Dönem 2. Yazılı (Aralık/Ocak)": ["Unit 2: My Town (Places in a town, Directions)", "Unit 3: Games and Hobbies"],
        "2. Dönem 1. Yazılı (Mart/Nisan)": ["Unit 4: My Daily Routine (Time, Daily Activities)", "Unit 5: Health (Illnesses, Suggestions)"],
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": ["Unit 6: Movies (Types of movies, Expressing likes/dislikes)", "Unit 7: Party Time", "Unit 8: Fitness"]
    },
    "Almanca": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Hallo! (Begrüßung, Sich vorstellen - Begrüßungsformeln, Name, Alter)"],
        "1. Dönem 2. Yazılı (Aralık/Ocak)": ["Meine Schule (Schulsachen, Schulfächer, Zahlen bis 20)"],
        "2. Dönem 1. Yazılı (Mart/Nisan)": ["Meine Familie und Tiere (Familienmitglieder, Haustiere)"],
        "2. Dönem 2. Yazılı (Mayıs/Haziran)": ["Meine Hobbys und Freizeit (Aktivitäten, Wochentage, Vorlieben)"]
    }
}

# ==========================================
# 4. GÖRSEL ÇİZİM MOTORU (MATPLOTLIB)
# ==========================================
def generate_question_image(diagram_type, details=None):
    """
    Soruya özel Matplotlib tabanlı matematik/geometri/fen görselleri üretir.
    """
    fig, ax = plt.subplots(figsize=(4, 3), dpi=120)
    
    if diagram_type == "triangle":
        p1, p2, p3 = [0, 0], [4, 0], [2, 3]
        triangle = plt.Polygon([p1, p2, p3], fill=None, edgecolor='#FF6B00', linewidth=2.5)
        ax.add_patch(triangle)
        ax.text(p1[0]-0.2, p1[1]-0.2, 'A', fontsize=12, fontweight='bold')
        ax.text(p2[0]+0.1, p2[1]-0.2, 'B', fontsize=12, fontweight='bold')
        ax.text(p3[0], p3[1]+0.2, 'C', fontsize=12, fontweight='bold')
        if details and "angle" in details:
            ax.text(2, 0.3, f"{details.get('angle_value', '60')}°", color='red', fontsize=10)
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 4)
        ax.axis('off')
        
    elif diagram_type in ["space_system", "sun_earth_moon"]:
        sun = plt.Circle((1, 2), 0.7, color='#FF8C00', label='Güneş')
        earth = plt.Circle((4, 2), 0.4, color='#1E90FF', label='Dünya')
        moon = plt.Circle((5.2, 2), 0.15, color='#A9A9A9', label='Ay')
        
        ax.add_patch(sun)
        ax.add_patch(earth)
        ax.add_patch(moon)
        
        ax.text(1, 1.0, 'Güneş', horizontalalignment='center', fontweight='bold', color='#FF8C00')
        ax.text(4, 1.3, 'Dünya', horizontalalignment='center', fontweight='bold', color='#1E90FF')
        ax.text(5.2, 1.6, 'Ay', horizontalalignment='center', fontweight='bold', color='#A9A9A9')
        
        orbit = plt.Circle((4, 2), 1.2, fill=False, linestyle='--', color='gray', alpha=0.5)
        ax.add_patch(orbit)
        
        ax.set_xlim(-0.5, 6.5)
        ax.set_ylim(0, 4)
        ax.axis('off')
        
    elif diagram_type == "fraction_pie":
        sizes = [1, 1, 1, 1]
        colors_list = ['#FF6B00', '#FF6B00', '#E0E0E0', '#E0E0E0']
        ax.pie(sizes, colors=colors_list, wedgeprops={"edgecolor":"black", "linewidth":1.5})
        
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
# 5. GERÇEK MEB FORMATINDA PDF ÜRETİCİ
# ==========================================
def build_pdf_exam(exam_data, show_answers=False):
    """
    ReportLab kütüphanesi ile yüksek kalitede, MEB standartlarında PDF üretir.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ExamTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=colors.HexColor("#1A237E")
    )
    
    q_style = ParagraphStyle(
        'QuestionText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#212121"),
        spaceAfter=6
    )
    
    opt_style = ParagraphStyle(
        'OptionText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#424242")
    )
    
    sol_style = ParagraphStyle(
        'SolutionText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1B5E20")
    )

    story = []
    
    header_text = f"<b>{exam_data['school_name'].upper()}</b><br/>" \
                  f"<b>2026-2027 EĞİTİM-ÖĞRETİM YILI 5. SINIF {exam_data['subject'].upper()} DERSİ</b><br/>" \
                  f"<u>{exam_data['term'].upper()} DEĞERLENDİRME SINAVI</u>"
                  
    if show_answers:
        header_text += " <font color='red'><b>[ DETAYLI CEVAP ANAHTARI & ÇÖZÜM FASİKÜLÜ ]</b></font>"

    story.append(Paragraph(header_text, title_style))
    story.append(Spacer(1, 10))
    
    info_data = [
        [
            Paragraph("<b>Adı Soyadı:</b> ........................................", opt_style),
            Paragraph("<b>Sınıf / Şube:</b> 5 / .......", opt_style),
            Paragraph("<b>Numara:</b> ............", opt_style),
            Paragraph("<b>ALDIĞI PUAN:</b> .......", opt_style)
        ]
    ]
    t_info = Table(info_data, colWidths=[200, 100, 100, 120])
    t_info.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#424242")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F5F5F5"))
    ]))
    story.append(t_info)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#FF6B00"), spaceAfter=15))

    for idx, q in enumerate(exam_data['questions'], start=1):
        q_elements = []
        
        q_header = f"<b>Soru {idx} ({q.get('points', 10)} Puan):</b> {q['question_text']}"
        q_elements.append(Paragraph(q_header, q_style))
        
        if q.get('has_diagram') and q.get('diagram_type'):
            img_buf = generate_question_image(q['diagram_type'])
            if img_buf:
                rl_img = RLImage(img_buf, width=150, height=112)
                q_elements.append(Spacer(1, 4))
                q_elements.append(rl_img)
                q_elements.append(Spacer(1, 4))
        
        if q['type'] == 'MCQ':
            opts = q.get('options', {})
            opt_table_data = [
                [Paragraph(f"<b>A)</b> {opts.get('A', '')}", opt_style), Paragraph(f"<b>B)</b> {opts.get('B', '')}", opt_style)],
                [Paragraph(f"<b>C)</b> {opts.get('C', '')}", opt_style), Paragraph(f"<b>D)</b> {opts.get('D', '')}", opt_style)]
            ]
            t_opts = Table(opt_table_data, colWidths=[250, 250])
            t_opts.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 3),
            ]))
            q_elements.append(t_opts)
        else:
            if not show_answers:
                q_elements.append(Spacer(1, 5))
                line_data = [[""], [""]]
                t_lines = Table(line_data, colWidths=[520], rowHeights=[18, 18])
                t_lines.setStyle(TableStyle([
                    ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#BDBDBD")),
                ]))
                q_elements.append(t_lines)
                
        if show_answers:
            q_elements.append(Spacer(1, 4))
            ans_box = f"<b>Doğru Cevap / Yanıt:</b> {q.get('correct_answer', '')}<br/>" \
                      f"<b>Detaylı Çözüm Açıklaması:</b> {q.get('solution_explanation', '')}"
            
            t_sol = Table([[Paragraph(ans_box, sol_style)]], colWidths=[520])
            t_sol.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#2E7D32")),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E8F5E9")),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            q_elements.append(t_sol)

        q_elements.append(Spacer(1, 12))
        story.append(KeepTogether(q_elements))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# 6. LLM PROMPT VE SORU ÜRETİMİ
# ==========================================
def generate_meb_exam(subject, term, units):
    prompt = f"""
    Sen MEB (Milli Eğitim Bakanlığı) 5. Sınıf {subject} dersi müfredatına %100 hakim uzman bir ölçme ve değerlendirme öğretmenisin.
    
    Lütfen şu sınav için TAM OLARAK 10 SORUDAN oluşan yazılı sınavı JSON formatında üret:
    - Ders: 5. Sınıf {subject}
    - Sınav Dönemi: {term}
    - Kapsanan Üniteler: {', '.join(units)}
    
    KRİTİK KURALLAR:
    1. Sınavda TAM 10 soru olmalıdır.
    2. 7 Soru Çoktan Seçmeli (MCQ), 3 Soru Açık Uçlu (OPEN) olmalıdır.
    3. Çoktan Seçmeli sorularda 4 ŞIK (A, B, C, D) bulunmalı ve hepsi mantıklı, birbirinden tamamen farklı olmalıdır.
    4. Yalnızca Matematik ve Fen Bilimleri derslerinde uygun sorular için "has_diagram": true yapabilir ve "diagram_type" seçebilirsin.
    5. Her soru için pedagojik, detaylı, adım adım açık yazılmış çözümler ekle.
    
    ÇIKTI FORMATI (Sadece geçerli JSON döndür):
    {{
        "school_name": "Şehit Öğretmen 5. Sınıf Ortaokulu",
        "subject": "{subject}",
        "term": "{term}",
        "questions": [
            {{
                "id": 1,
                "type": "MCQ",
                "question_text": "Soru metni...",
                "options": {{
                    "A": "Şık A",
                    "B": "Şık B",
                    "C": "Şık C",
                    "D": "Şık D"
                }},
                "correct_answer": "A",
                "solution_explanation": "Adım adım detaylı çözüm açıklaması...",
                "points": 10,
                "has_diagram": false,
                "diagram_type": null
            }},
            {{
                "id": 8,
                "type": "OPEN",
                "question_text": "Açık uçlu soru metni...",
                "correct_answer": "Örnek ideal cevap...",
                "solution_explanation": "Öğrencinin vermesi gereken puanlama detayları...",
                "points": 10,
                "has_diagram": false,
                "diagram_type": null
            }}
        ]
    }}
    """
    
    raw_response = generate_llm_response(prompt)
    if not raw_response:
        return None
        
    try:
        clean_json = raw_response.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()
            
        data = json.loads(clean_json)
        return data
    except Exception as e:
        st.error(f"Soru verisi işlenirken format hatası oluştu: {e}")
        return None

# ==========================================
# 7. STREAMLIT STATE & ARAYÜZ
# ==========================================

if 'exam_started' not in st.session_state:
    st.session_state.exam_started = False
if 'exam_data' not in st.session_state:
    st.session_state.exam_data = None
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'exam_completed' not in st.session_state:
    st.session_state.exam_completed = False

# SIDEBAR: Sınav Parametreleri
st.sidebar.header("⚙️ Sınav Ayarları")

selected_subject = st.sidebar.selectbox("📖 Ders Seçiniz", list(MEB_CURRICULUM.keys()))
terms_available = list(MEB_CURRICULUM[selected_subject].keys())
selected_term = st.sidebar.selectbox("📅 Sınav Dönemi Seçiniz", terms_available)

selected_units = MEB_CURRICULUM[selected_subject][selected_term]
st.sidebar.info(f"📌 **Dahil Üniteler:**\n" + "\n".join([f"- {u}" for u in selected_units]))

st.sidebar.divider()

if st.sidebar.button("🎲 Yeni Sınav Hazırla", use_container_width=True):
    with st.spinner("MEB Müfredatına uygun 10 özgün soru hazırlanıyor..."):
        exam_json = generate_meb_exam(selected_subject, selected_term, selected_units)
        if exam_json:
            st.session_state.exam_data = exam_json
            st.session_state.exam_started = False
            st.session_state.exam_completed = False
            st.session_state.user_answers = {}
            st.success("✅ Sınav başarıyla oluşturuldu! Başlamak için 'Sınavı Başlat' butonuna basınız.")

# ==========================================
# 8. ANA EKRAN & SINAV MODU
# ==========================================

if st.session_state.exam_data:
    exam = st.session_state.exam_data
    
    pdf_exam = build_pdf_exam(exam, show_answers=False)
    pdf_sol = build_pdf_exam(exam, show_answers=True)
    
    col_pdf1, col_pdf2 = st.columns(2)
    with col_pdf1:
        st.download_button(
            "📄 MEB Formatında Sınav Kağıdı İndir (PDF)",
            data=pdf_exam,
            file_name=f"5_Sinif_{exam['subject']}_Yazili_Sinavi.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    with col_pdf2:
        st.download_button(
            "🔑 Çözüm & Cevap Anahtarı İndir (PDF)",
            data=pdf_sol,
            file_name=f"5_Sinif_{exam['subject']}_Cevap_Anahtari.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    st.divider()

    # --- DURUM 1: SINAV BAŞLAMADI ---
    if not st.session_state.exam_started and not st.session_state.exam_completed:
        st.warning("⏱️ Sınav hazır! Soruları görmek ve süreyi başlatmak için aşağıdaki butona tıklayın.")
        if st.button("🚀 SINAVI BAŞLAT", type="primary", use_container_width=True):
            st.session_state.exam_started = True
            st.session_state.start_time = time.time()
            st.rerun()

    # --- DURUM 2: SINAV DEVAM EDİYOR ---
    elif st.session_state.exam_started and not st.session_state.exam_completed:
        elapsed_time = int(time.time() - st.session_state.start_time)
        minutes, seconds = divmod(elapsed_time, 60)
        
        c_timer, c_end = st.columns([3, 1])
        with c_timer:
            st.subheader(f"⏱️ Geçen Süre: {minutes:02d}:{seconds:02d}")
        with c_end:
            if st.button("🛑 SINAVI BİTİR", type="primary", use_container_width=True):
                st.session_state.exam_started = False
                st.session_state.exam_completed = True
                st.rerun()

        st.progress(len(st.session_state.user_answers) / 10.0)

        for q in exam['questions']:
            q_id = q['id']
            st.markdown(f"""
            <div class="question-card">
                <div>
                    <span class="{'badge-mcq' if q['type']=='MCQ' else 'badge-open'}">
                        { 'Çoktan Seçmeli' if q['type']=='MCQ' else 'Açık Uçlu' }
                    </span>
                    <strong style="margin-left: 10px;">Soru {q_id} ({q.get('points', 10)} Puan)</strong>
                </div>
                <p style="font-size: 16px; margin-top: 10px;">{q['question_text']}</p>
            </div>
            """, unsafe_allow_html=True)

            if q.get('has_diagram') and q.get('diagram_type'):
                img_buf = generate_question_image(q['diagram_type'])
                if img_buf:
                    st.image(img_buf, width=320)

            if q['type'] == 'MCQ':
                opts = q.get('options', {})
                formatted_opts = [f"{k}) {v}" for k, v in opts.items()]
                selected = st.radio(
                    f"Cevabınız (Soru {q_id}):",
                    formatted_opts,
                    key=f"q_{q_id}",
                    index=None
                )
                if selected:
                    st.session_state.user_answers[q_id] = selected[0]
            else:
                user_text = st.text_area(f"Cevabınızı buraya yazınız (Soru {q_id}):", key=f"q_{q_id}")
                if user_text:
                    st.session_state.user_answers[q_id] = user_text

            st.write("---")

    # --- DURUM 3: SINAV BİTTİ ---
    elif st.session_state.exam_completed:
        st.balloons()
        st.success("🎉 Sınavı tamamladınız! Aşağıdan sonuçlarınızı ve detaylı çözümleri inceleyebilirsiniz.")

        total_score = 0
        mcq_count = 0
        
        for q in exam['questions']:
            q_id = q['id']
            user_ans = st.session_state.user_answers.get(q_id, "Boş")
            correct_ans = q.get('correct_answer', '')

            st.markdown(f"### Soru {q_id}: {q['question_text']}")
            
            if q['type'] == 'MCQ':
                mcq_count += 1
                is_correct = (user_ans == correct_ans)
                if is_correct:
                    total_score += q.get('points', 10)
                    st.success(f"✅ **Tebrikler!** Doğru Cevap: **{correct_ans}** | Sizin Cevabınız: **{user_ans}**")
                else:
                    st.error(f"❌ **Yanlış!** Doğru Cevap: **{correct_ans}** | Sizin Cevabınız: **{user_ans}**")
            else:
                st.info(f"📝 **Açık Uçlu Soru Cevabınız:** {user_ans}\n\n**İdeal Cevap:** {correct_ans}")

            with st.expander("🔍 Detaylı Çözümü ve Açıklamayı Gör"):
                st.write(q.get('solution_explanation', 'Çözüm açıklaması mevcut değil.'))
            st.divider()

        st.metric(label="Çoktan Seçmeli Sorulardan Tahmini Puanınız", value=f"{total_score} Puan")

else:
    st.info("👈 Sınav oluşturmak için sol menüden dersinizi ve sınav döneminizi seçip **'Yeni Sınav Hazırla'** butonuna tıklayınız.")
