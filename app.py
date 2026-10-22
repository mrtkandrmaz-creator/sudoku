import streamlit as st
import random
import json
import re
import io
import time
import urllib.request
import os
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# ReportLab Imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, HRFlowable, FrameBreak, NextPageTemplate
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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
    .report-card {
        background-color: #f9fbe7;
        border: 2px solid #c0ca33;
        border-radius: 12px;
        padding: 25px;
        margin-bottom: 25px;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-bar">
    <div>🎓 MEB 5. Sınıf Soru Fabrikası <span style="font-size: 18px;">(Murat KANDIRMAZ)</span></div>
    <div class="header-sub">Yazılı Öncesi Akıllı Sınav & Çalışma Hazırlık Robotu</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# METİN TEMİZLEME & TÜRKÇE KARAKTER ONARICI
# ==========================================
def fix_turkish_chars(text):
    """
    Kare (■) veya hatalı çıkan Türkçe karakterleri düzeltir.
    """
    if not isinstance(text, str):
        return text
    
    replacements = {
        '■': 'ş',
        'þ': 'ş', 'Þ': 'Ş',
        'ð': 'ğ', 'Ð': 'Ğ',
        'ý': 'ı', 'Ý': 'İ',
        'þ': 'ş', 'Þ': 'Ş',
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
        
    return text

# ==========================================
# 2. SECRET TARAMA & DİNAMİK API KULLANIMI
# ==========================================
def extract_api_keys():
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
    providers = []
    for k in GEMINI_KEYS:
        providers.append(("gemini", k))
    for k in GROQ_KEYS:
        providers.append(("groq", k))
        
    random.shuffle(providers)
    
    if not providers:
        st.error("🚨 `.streamlit/secrets.toml` içerisinde geçerli Gemini veya Groq API Anahtarı bulunamadı!")
        return None

    last_error = ""
    for provider_type, api_key in providers:
        try:
            if provider_type == "gemini" and genai:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-3.6-flash")
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
# 3. MEB MÜFREDAT DATA
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
    fig, ax = plt.subplots(figsize=(2.8, 1.8), dpi=100)
    
    if diagram_type == "triangle":
        p1, p2, p3 = [0, 0], [4, 0], [2, 3]
        triangle = plt.Polygon([p1, p2, p3], fill=None, edgecolor='#FF6B00', linewidth=2)
        ax.add_patch(triangle)
        ax.text(p1[0]-0.2, p1[1]-0.2, 'A', fontsize=9, fontweight='bold')
        ax.text(p2[0]+0.1, p2[1]-0.2, 'B', fontsize=9, fontweight='bold')
        ax.text(p3[0], p3[1]+0.2, 'C', fontsize=9, fontweight='bold')
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 4)
        ax.axis('off')
        
    elif diagram_type in ["space_system", "sun_earth_moon"]:
        sun = plt.Circle((1, 2), 0.7, color='#FF8C00')
        earth = plt.Circle((4, 2), 0.4, color='#1E90FF')
        moon = plt.Circle((5.2, 2), 0.15, color='#A9A9A9')
        
        ax.add_patch(sun)
        ax.add_patch(earth)
        ax.add_patch(moon)
        
        ax.text(1, 0.9, 'Güneş', horizontalalignment='center', fontweight='bold', color='#FF8C00', fontsize=8)
        ax.text(4, 1.3, 'Dünya', horizontalalignment='center', fontweight='bold', color='#1E90FF', fontsize=8)
        ax.text(5.2, 1.6, 'Ay', horizontalalignment='center', fontweight='bold', color='#A9A9A9', fontsize=8)
        
        ax.set_xlim(-0.5, 6.5)
        ax.set_ylim(0, 4)
        ax.axis('off')
        
    elif diagram_type == "fraction_pie":
        sizes = [1, 1, 1, 1]
        colors_list = ['#FF6B00', '#FF6B00', '#E0E0E0', '#E0E0E0']
        ax.pie(sizes, colors=colors_list, wedgeprops={"edgecolor":"black", "linewidth":1})
        
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
# 5. TÜRKÇE FONT & REPORTLAB DÜZENİ
# ==========================================
@st.cache_resource
def setup_turkish_pdf_fonts():
    """
    Fontu doğrudan indirip ReportLab'e tanıtır ve varsayılan UTF-8 eşleşmesini kurar.
    """
    try:
        font_urls = {
            "TR-Regular": "https://raw.githubusercontent.com/google/fonts/main/ofl/dejavusans/DejaVuSans.ttf",
            "TR-Bold": "https://raw.githubusercontent.com/google/fonts/main/ofl/dejavusans/DejaVuSans-Bold.ttf",
            "TR-Oblique": "https://raw.githubusercontent.com/google/fonts/main/ofl/dejavusans/DejaVuSans-Oblique.ttf"
        }
        
        for name, url in font_urls.items():
            font_path = f"{name}.ttf"
            if not os.path.exists(font_path):
                urllib.request.urlretrieve(url, font_path)
            pdfmetrics.registerFont(TTFont(name, font_path))
            
        return "TR-Regular", "TR-Bold", "TR-Oblique"
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"

class TwoColumnCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_center_line_and_footer(num_pages)
            super().showPage()
        super().save()

    def draw_center_line_and_footer(self, total_pages):
        self.saveState()
        self.setStrokeColor(colors.HexColor("#BDBDBD"))
        self.setLineWidth(0.8)
        
        # Dikey Çizgi
        self.line(297.5, 40, 297.5, 720)
        
        self.setFont("TR-Regular" if "TR-Regular" in pdfmetrics.getRegisteredFontNames() else "Helvetica", 8)
        self.setFillColor(colors.HexColor("#616161"))
        self.drawString(25, 20, fix_turkish_chars("MEB 5. Sınıf Soru Fabrikası - Murat KANDIRMAZ"))
        self.drawRightString(570, 20, f"Sayfa {self._pageNumber} / {total_pages}")
        self.restoreState()

def build_pdf_exam(exam_data, show_answers=False):
    f_norm, f_bold, f_oblique = setup_turkish_pdf_fonts()

    buffer = io.BytesIO()
    
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25,
        rightMargin=25,
        topMargin=25,
        bottomMargin=35
    )

    frame_header = Frame(25, 730, 545, 90, id='header_frame', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0)
    frame_left_p1 = Frame(25, 35, 255, 685, id='left_col_p1', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=5)
    frame_right_p1 = Frame(315, 35, 255, 685, id='right_col_p1', topPadding=0, bottomPadding=0, leftPadding=5, rightPadding=0)

    frame_left_p2 = Frame(25, 35, 255, 770, id='left_col_p2', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=5)
    frame_right_p2 = Frame(315, 35, 255, 770, id='right_col_p2', topPadding=0, bottomPadding=0, leftPadding=5, rightPadding=0)

    first_page_template = PageTemplate(id='FirstPage', frames=[frame_header, frame_left_p1, frame_right_p1])
    later_page_template = PageTemplate(id='LaterPages', frames=[frame_left_p2, frame_right_p2])

    doc.addPageTemplates([first_page_template, later_page_template])

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ExamTitle',
        fontName=f_bold,
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#1A237E")
    )
    
    q_style = ParagraphStyle(
        'QuestionText',
        fontName=f_bold,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#212121"),
        spaceAfter=4
    )
    
    opt_style = ParagraphStyle(
        'OptionText',
        fontName=f_norm,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#424242")
    )
    
    sol_style = ParagraphStyle(
        'SolutionText',
        fontName=f_oblique,
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1B5E20")
    )

    story = []
    
    # --- HEADER FRAME İÇERİĞİ ---
    header_text = f"<b>{fix_turkish_chars(exam_data['school_name']).upper()}</b><br/>" \
                  f"<b>2026-2027 EĞİTİM-ÖĞRETİM YILI 5. SINIF {fix_turkish_chars(exam_data['subject']).upper()} DERSİ</b><br/>" \
                  f"<u>{fix_turkish_chars(exam_data['term']).upper()} DEĞERLENDİRME SINAVI</u>"
                  
    if show_answers:
        header_text += " <font color='red'><b>[ DETAYLI CEVAP ANAHTARI ]</b></font>"

    story.append(Paragraph(header_text, title_style))
    story.append(Spacer(1, 6))
    
    info_data = [
        [
            Paragraph(fix_turkish_chars("<b>Adı Soyadı:</b> ...................................."), opt_style),
            Paragraph(fix_turkish_chars("<b>Sınıf/Şube:</b> 5 / ......."), opt_style),
            Paragraph(fix_turkish_chars("<b>Numara:</b> ............"), opt_style),
            Paragraph(fix_turkish_chars("<b>Puan:</b> ......."), opt_style)
        ]
    ]
    t_info = Table(info_data, colWidths=[180, 110, 110, 145])
    t_info.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#424242")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 3),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F5F5F5"))
    ]))
    story.append(t_info)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#FF6B00"), spaceAfter=0))

    story.append(FrameBreak())
    story.append(NextPageTemplate('LaterPages'))

    # --- SORULARIN DİZİLİMİ ---
    for idx, q in enumerate(exam_data['questions'], start=1):
        q_elements = []
        clean_question_text = fix_turkish_chars(q['question_text'])
        q_header = f"<b>Soru {idx} ({q.get('points', 10)} Puan):</b> {clean_question_text}"
        q_elements.append(Paragraph(q_header, q_style))
        
        if q.get('has_diagram') and q.get('diagram_type'):
            img_buf = generate_question_image(q['diagram_type'])
            if img_buf:
                rl_img = RLImage(img_buf, width=110, height=70)
                q_elements.append(Spacer(1, 3))
                q_elements.append(rl_img)
                q_elements.append(Spacer(1, 3))
        
        if q['type'] == 'MCQ':
            opts = q.get('options', {})
            opt_a = fix_turkish_chars(opts.get('A', ''))
            opt_b = fix_turkish_chars(opts.get('B', ''))
            opt_c = fix_turkish_chars(opts.get('C', ''))
            opt_d = fix_turkish_chars(opts.get('D', ''))
            
            opt_table_data = [
                [Paragraph(f"<b>A)</b> {opt_a}", opt_style), Paragraph(f"<b>B)</b> {opt_b}", opt_style)],
                [Paragraph(f"<b>C)</b> {opt_c}", opt_style), Paragraph(f"<b>D)</b> {opt_d}", opt_style)]
            ]
            t_opts = Table(opt_table_data, colWidths=[120, 120])
            t_opts.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('PADDING', (0,0), (-1,-1), 2),
            ]))
            q_elements.append(t_opts)
        else:
            if not show_answers:
                q_elements.append(Spacer(1, 4))
                line_data = [[""], [""]]
                t_lines = Table(line_data, colWidths=[240], rowHeights=[14, 14])
                t_lines.setStyle(TableStyle([
                    ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#BDBDBD")),
                ]))
                q_elements.append(t_lines)
                
        if show_answers:
            q_elements.append(Spacer(1, 3))
            clean_correct = fix_turkish_chars(q.get('correct_answer', ''))
            clean_sol = fix_turkish_chars(q.get('solution_explanation', ''))
            ans_box = f"<b>Cevap:</b> {clean_correct}<br/>" \
                      f"<b>Açıklama:</b> {clean_sol}"
            
            t_sol = Table([[Paragraph(ans_box, sol_style)]], colWidths=[240])
            t_sol.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 0.6, colors.HexColor("#2E7D32")),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E8F5E9")),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            q_elements.append(t_sol)

        q_elements.append(Spacer(1, 10))
        story.append(KeepTogether(q_elements))

    doc.build(story, canvasmaker=TwoColumnCanvas)
    buffer.seek(0)
    return buffer

# ==========================================
# 6. LLM PROMPT VE SORU ÜRETİMİ
# ==========================================
def generate_meb_exam(subject, term, units):
    prompt = f"""
    Sen MEB (Milli Eğitim Bakanlığı) 5. Sınıf {subject} dersi müfredatına %100 hakim uzman bir öğretmen ve ölçme değerlendirme uzmanısın.
    
    Lütfen {subject} dersi için {term} dönemini kapsayan TAM 10 SORUDAN oluşan özgün bir sınav hazırlat:
    - Dahil Üniteler: {', '.join(units)}
    
    ÖNEMLİ KURALLAR:
    1. Sınavda TAM OLARAK 5 TANE Çoktan Seçmeli (MCQ) ve 5 TANE Açık Uçlu (OPEN) soru olmalıdır.
    2. Çoktan seçmeli soruların tamamında 4 farklı ve mantıklı şık (A, B, C, D) olmalıdır.
    3. Yalnızca Matematik ve Fen Bilimleri dersleri için gerekiyorsa "has_diagram": true ve uygun "diagram_type" ('triangle', 'space_system', 'fraction_pie') belirt.
    4. Türkçe karakterlerin (ş, ğ, ı, ö, ü, ç) eksiksiz ve doğru yazılmasına ÖZELLİKLE dikkat et.
    
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
                "options": {{ "A": "...", "B": "...", "C": "...", "D": "..." }},
                "correct_answer": "A",
                "solution_explanation": "Detaylı adım adım açıklama...",
                "points": 10,
                "has_diagram": false,
                "diagram_type": null
            }},
            {{
                "id": 6,
                "type": "OPEN",
                "question_text": "Açık uçlu soru metni...",
                "correct_answer": "İdeal cevap...",
                "solution_explanation": "Kapsamlı açıklama...",
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
    with st.spinner("MEB Müfredatına uygun 5 Çoktan Seçmeli + 5 Açık Uçlu Soru Hazırlanıyor..."):
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
            "📄 MEB Çift Sütun Formatında Sınav Kağıdı İndir (PDF)",
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
        
        st.subheader(f"⏱️ Geçen Süre: {minutes:02d}:{seconds:02d}")
        st.progress(len(st.session_state.user_answers) / 10.0)

        for q in exam['questions']:
            q_id = q['id']
            clean_q_text = fix_turkish_chars(q['question_text'])
            st.markdown(f"""
            <div class="question-card">
                <div>
                    <span class="{'badge-mcq' if q['type']=='MCQ' else 'badge-open'}">
                        { 'Çoktan Seçmeli' if q['type']=='MCQ' else 'Açık Uçlu' }
                    </span>
                    <strong style="margin-left: 10px;">Soru {q_id} (10 Puan)</strong>
                </div>
                <p style="font-size: 16px; margin-top: 10px;">{clean_q_text}</p>
            </div>
            """, unsafe_allow_html=True)

            if q.get('has_diagram') and q.get('diagram_type'):
                img_buf = generate_question_image(q['diagram_type'])
                if img_buf:
                    st.image(img_buf, width=300)

            if q['type'] == 'MCQ':
                opts = q.get('options', {})
                formatted_opts = [f"{k}) {fix_turkish_chars(v)}" for k, v in opts.items()]
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

        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("🛑 SINAVI BİTİR VE KARNEYİ GÖR", type="primary", use_container_width=True):
            st.session_state.exam_started = False
            st.session_state.exam_completed = True
            st.rerun()

    # --- DURUM 3: SINAV BİTTİ & ÖĞRENCİ KARNESİ ---
    elif st.session_state.exam_completed:
        st.balloons()
        
        mcq_correct = 0
        mcq_wrong = 0
        mcq_empty = 0
        mcq_score = 0
        
        for q in exam['questions']:
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

        st.markdown("""
        <div class="report-card">
            <h2 style="color: #33691E; text-align: center; margin-bottom: 5px;">📊 ÖĞRENCİ SINAV KARNESİ</h2>
            <p style="text-align: center; color: #558B2F;">5. Sınıf Değerlendirme ve Başarı Raporu</p>
        </div>
        """, unsafe_allow_html=True)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Test Puanı (MCQ)", f"{mcq_score} / 50")
        k2.metric("Doğru Cevap", f"{mcq_correct} Soru")
        k3.metric("Yanlış Cevap", f"{mcq_wrong} Soru")
        k4.metric("Boş Bırakılan", f"{mcq_empty} Soru")

        st.info("ℹ️ **Not:** Açık uçlu sorular öğretmen/veli değerlendirmesi gerektirdiği için otomatize teste dahil edilmemiştir.")

        st.divider()
        st.subheader("📝 Detaylı Soru Çözümleri ve Cevap Anahtarı")

        for q in exam['questions']:
            q_id = q['id']
            user_ans = st.session_state.user_answers.get(q_id, "Yanıt Verilmedi")
            correct_ans = fix_turkish_chars(q.get('correct_answer', ''))

            st.markdown(f"**Soru {q_id}: {fix_turkish_chars(q['question_text'])}**")
            
            if q['type'] == 'MCQ':
                is_correct = (user_ans == correct_ans)
                if is_correct:
                    st.success(f"✅ **Doğru!** Cevabınız: **{user_ans}**")
                else:
                    st.error(f"❌ **Yanlış!** Doğru Cevap: **{correct_ans}** | Sizin Cevabınız: **{user_ans}**")
            else:
                st.warning(f"📝 **Sizin Yanıtınız:** {user_ans}\n\n**İdeal/Örnek Cevap:** {correct_ans}")

            with st.expander("🔍 Detaylı Adım Adım Çözüm Açıklaması"):
                st.write(fix_turkish_chars(q.get('solution_explanation', 'Çözüm açıklaması bulunamadı.')))
            st.write("---")

else:
    st.info("👈 Sınav oluşturmak için sol menüden dersinizi ve sınav döneminizi seçip **'Yeni Sınav Hazırla'** butonuna tıklayınız.")
