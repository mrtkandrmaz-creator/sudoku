# -*- coding: utf-8 -*-
import streamlit as st
import random
import json
import io
import time
import urllib.request
import os
import matplotlib.pyplot as plt
import numpy as np

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
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
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
# 2. MEB ONAYLI UNICODE KORUMALI SORU BANKASI
# ==========================================
MEB_QUESTION_POOL = {
    "Fen Bilimleri": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": [
            {
                "id": 1, "type": "MCQ",
                "question_text": "G\u00fcne\u015f ile ilgili verilen a\u015fa\u011f\u0131dakilerden hangisi yanlı\u015ft\u0131r?",
                "options": {"A": "G\u00fcne\u015f, katmanlardan olu\u015fan devasa bir gaz küresidir.", "B": "G\u00fcne\u015f yüzeyindeki so\u011fuk bölgelere 'G\u00fcne\u015f lekesi' adı verilir.", "C": "G\u00fcne\u015f, Dünya'm\u0131za en yakın yıldızdır.", "D": "G\u00fcne\u015f'in yüzey sıcaklığı merkezindeki sıcaklıktan daha fazladır."},
                "correct_answer": "D", "solution_explanation": "Güneş'in merkez sıcaklığı yaklaşık 15 milyon °C iken, yüzey sıcaklığı yaklaşık 6000 °C'dir.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 2, "type": "MCQ",
                "question_text": "Galileo Galilei, kendi tasarladığı teleskopla G\u00fcne\u015f lekelerini gözlemlemiş ve bu lekelerin hep aynı yöne doğru kaydığını fark etmiştir. Bu gözlem neyi kanıtlar?",
                "options": {"A": "G\u00fcne\u015f'in Dünya etrafında dolandığını", "B": "G\u00fcne\u015f'in kendi ekseni etrafında döndüğünü", "C": "G\u00fcne\u015f'in şeklinin tam bir küp olduğunu", "D": "G\u00fcne\u015f'in katmanlarının bulunmadığını"},
                "correct_answer": "B", "solution_explanation": "Güneş lekelerinin düzenli kayması Güneş'in kendi ekseni etrafında döndüğünü kanıtlar.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 3, "type": "MCQ",
                "question_text": "Dünya'nın şekli ve hareketleri ile ilgili aşağıda verilen bilgilerden hangisi doğrudur?",
                "options": {"A": "Dünya, kutuplardan şişkin, ekvatordan basıktır.", "B": "Dünya kendi etrafındaki bir tam turunu 365 gün 6 saatte tamamlar.", "C": "Dünya'nın kendi etrafında dönmesi sonucu gece ve gündüz birbirini takip eder.", "D": "Dünya, G\u00fcne\u015f etrafında saat yönünde dolanır."},
                "correct_answer": "C", "solution_explanation": "Dünya'nın kendi ekseni etrafındaki dönmesi gece ve gündüzü oluşturur.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 4, "type": "MCQ",
                "question_text": "G\u00fcne\u015f, Dünya ve Ay'ın büyüklükleri karşılaştırıldığında doğru sıralama nasıldır?",
                "options": {"A": "G\u00fcne\u015f > Dünya > Ay", "B": "Dünya > G\u00fcne\u015f > Ay", "C": "G\u00fcne\u015f > Ay > Dünya", "D": "Ay > Dünya > G\u00fcne\u015f"},
                "correct_answer": "A", "solution_explanation": "Boyut sıralaması: Güneş > Dünya > Ay şeklindedir.", "points": 10, "has_diagram": True, "diagram_type": "sun_earth_moon"
            },
            {
                "id": 5, "type": "MCQ",
                "question_text": "Aşağıdakilerden hangisi Ay'ın ana evrelerinden biri değildir?",
                "options": {"A": "Yeni Ay", "B": "İlk Dördün", "C": "Hilal", "D": "Dolunay"},
                "correct_answer": "C", "solution_explanation": "Hilal ara evredir.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 6, "type": "OPEN",
                "question_text": "G\u00fcne\u015f'in içten dışa doğru katmanlarının isimlerini sırasıyla yazınız.",
                "options": {},
                "correct_answer": "Çekirdek, Işık Küre, Renk Küre, Taç Küre",
                "solution_explanation": "Sırasıyla: Çekirdek, Işık Küre, Renk Küre, Taç Küre.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 7, "type": "OPEN",
                "question_text": "Dünya'nın kendi ekseni etrafındaki dönme hareketi ne kadar sürer ve neyi oluşturur?",
                "options": {},
                "correct_answer": "24 saatte tamamlanır, gece ve gündüzü oluşturur.",
                "solution_explanation": "1 tam tur 24 saattir ve gece-gündüzü meydana getirir.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 8, "type": "OPEN",
                "question_text": "Ay'ın hep aynı yüzünü görmemizin temel sebebi nedir?",
                "options": {},
                "correct_answer": "Kendi ekseni etrafındaki dönme süresi ile Dünya etrafındaki dolanma süresinin eşit olması.",
                "solution_explanation": "Süreler eşit olduğu için hep aynı yüzü görünür.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 9, "type": "OPEN",
                "question_text": "Ay atmosferinin çok ince olmasının sonuçları nelerdir?",
                "options": {},
                "correct_answer": "Sıcaklık farkı çok fazladır ve göktaşları krater oluşturur.",
                "solution_explanation": "Atmosfer koruma sağlayamadığı için kraterler ve aşırı sıcaklık farkları görülür.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 10, "type": "OPEN",
                "question_text": "Güneş tutulması hangi evrede gerçekleşir?",
                "options": {},
                "correct_answer": "Yeni Ay evresinde gerçekleşir.",
                "solution_explanation": "Ay, Güneş ile Dünya arasına Yeni Ay evresinde girer.",
                "points": 10, "has_diagram": False, "diagram_type": None
            }
        ]
    },
    "Matematik": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": [
            {
                "id": 1, "type": "MCQ",
                "question_text": "Okunuşu 'Yüz iki milyon bin kırk beş' olan doğal sayı hangisidir?",
                "options": {"A": "102 001 045", "B": "102 010 045", "C": "120 001 045", "D": "102 001 450"},
                "correct_answer": "A", "solution_explanation": "102 milyon 001 bin 045", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 2, "type": "MCQ",
                "question_text": "845 392 716 sayısının milyonlar bölüğündeki rakamların toplamı kaçtır?",
                "options": {"A": "14", "B": "17", "C": "19", "D": "21"},
                "correct_answer": "B", "solution_explanation": "8 + 4 + 5 = 17", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 3, "type": "MCQ",
                "question_text": "87 604 - 39 485 işleminin sonucu kaçtır?",
                "options": {"A": "48 119", "B": "48 219", "C": "47 119", "D": "49 119"},
                "correct_answer": "A", "solution_explanation": "Çıkarma işlemi sonucu 48 119'dur.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 4, "type": "MCQ",
                "question_text": "İlk gün 24 580, ikinci gün 3 420 fazla fidan dikilmiştir. Toplam kaç fidan dikilmiştir?",
                "options": {"A": "48 000", "B": "51 000", "C": "52 580", "D": "56 000"},
                "correct_answer": "C", "solution_explanation": "24580 + 28000 = 52580", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 5, "type": "MCQ",
                "question_text": "73 408 925 sayısındaki '3' ve '4' rakamlarının basamak değerleri toplamı kaçtır?",
                "options": {"A": "3 004 000", "B": "3 040 000", "C": "3 400 000", "D": "30 040 000"},
                "correct_answer": "B", "solution_explanation": "3 000 000 + 40 000 = 3 040 000", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 6, "type": "OPEN",
                "question_text": "4, 0, 7, 2, 9 rakamlarıyla yazılabilen en büyük ve en küçük beş basamaklı sayıların farkı kaçtır?",
                "options": {},
                "correct_answer": "76 521",
                "solution_explanation": "97420 - 20479 = 76521",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 7, "type": "OPEN",
                "question_text": "18 450 TL televizyon ve 14 300 TL çamaşır makinesi alan kişi satıcıya 35 000 TL vermiştir. Kaç TL para üstü almalıdır?",
                "options": {},
                "correct_answer": "2 250 TL",
                "solution_explanation": "35000 - 32750 = 2250 TL",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 8, "type": "OPEN",
                "question_text": "Çiftlikte 1450 koyun, koyunlardan 380 fazla inek ve ineklerden 520 eksik tavuk vardır. Toplam hayvan sayısı kaçtır?",
                "options": {},
                "correct_answer": "4 460",
                "solution_explanation": "1450 + 1830 + 1310 = 4460",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 9, "type": "OPEN",
                "question_text": "ABC üçgeninde A açısı 65°, B açısı 50° ise C açısı kaç derecedir?",
                "options": {},
                "correct_answer": "65 derece",
                "solution_explanation": "180 - (65 + 50) = 65°",
                "points": 10, "has_diagram": True, "diagram_type": "triangle"
            },
            {
                "id": 10, "type": "OPEN",
                "question_text": "Yüzler basamağında 4, binler basamağında 7 olan en küçük beş basamaklı doğal sayı kaçtır?",
                "options": {},
                "correct_answer": "17 400",
                "solution_explanation": "Sayı 17 400'dür.",
                "points": 10, "has_diagram": False, "diagram_type": None
            }
        ]
    }
}

def get_fallback_exam(subject, term):
    questions = []
    for i in range(1, 6):
        questions.append({
            "id": i, "type": "MCQ",
            "question_text": f"5. Sınıf {subject} dersi {term} dönemi örnek soru {i}?",
            "options": {"A": "Doğru seçenek", "B": "Çeldirici 1", "C": "Çeldirici 2", "D": "Çeldirici 3"},
            "correct_answer": "A", "solution_explanation": "Bu sorunun doğru yanıtı A seçeneğidir.",
            "points": 10, "has_diagram": False, "diagram_type": None
        })
    for i in range(6, 11):
        questions.append({
            "id": i, "type": "OPEN",
            "question_text": f"5. Sınıf {subject} dersi {term} dönemi açık uçlu soru {i-5}?",
            "options": {},
            "correct_answer": "Örnek ideal yanıt.",
            "solution_explanation": "Detaylı açıklama.",
            "points": 10, "has_diagram": False, "diagram_type": None
        })
    return {
        "school_name": "Şehit Öğretmen 5. Sınıf Ortaokulu",
        "subject": subject,
        "term": term,
        "questions": questions
    }

# ==========================================
# 3. GÖRSEL ÇİZİM MOTORU (MATPLOTLIB)
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
# 4. TÜRKÇE FONT & REPORTLAB DÜZENİ
# ==========================================
@st.cache_resource
def setup_turkish_pdf_fonts():
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
        self.line(297.5, 40, 297.5, 720)
        font_name = "TR-Regular" if "TR-Regular" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
        self.setFont(font_name, 8)
        self.setFillColor(colors.HexColor("#616161"))
        self.drawString(25, 20, "MEB 5. Sınıf Soru Fabrikası - Murat KANDIRMAZ")
        self.drawRightString(570, 20, f"Sayfa {self._pageNumber} / {total_pages}")
        self.restoreState()

def build_pdf_exam(exam_data, show_answers=False):
    f_norm, f_bold, f_oblique = setup_turkish_pdf_fonts()
    buffer = io.BytesIO()
    
    doc = BaseDocTemplate(
        buffer, pagesize=A4, leftMargin=25, rightMargin=25, topMargin=25, bottomMargin=35
    )

    frame_header = Frame(25, 730, 545, 90, id='header_frame', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0)
    frame_left_p1 = Frame(25, 35, 255, 685, id='left_col_p1', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=5)
    frame_right_p1 = Frame(315, 35, 255, 685, id='right_col_p1', topPadding=0, bottomPadding=0, leftPadding=5, rightPadding=0)
    frame_left_p2 = Frame(25, 35, 255, 770, id='left_col_p2', topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=5)
    frame_right_p2 = Frame(315, 35, 255, 770, id='right_col_p2', topPadding=0, bottomPadding=0, leftPadding=5, rightPadding=0)

    doc.addPageTemplates([
        PageTemplate(id='FirstPage', frames=[frame_header, frame_left_p1, frame_right_p1]),
        PageTemplate(id='LaterPages', frames=[frame_left_p2, frame_right_p2])
    ])

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ExamTitle', fontName=f_bold, fontSize=11, leading=14, alignment=1, textColor=colors.HexColor("#1A237E"))
    q_style = ParagraphStyle('QuestionText', fontName=f_bold, fontSize=8.5, leading=11, textColor=colors.HexColor("#212121"), spaceAfter=4)
    opt_style = ParagraphStyle('OptionText', fontName=f_norm, fontSize=8, leading=10, textColor=colors.HexColor("#424242"))
    sol_style = ParagraphStyle('SolutionText', fontName=f_oblique, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#1B5E20"))

    story = []
    header_text = f"<b>{exam_data['school_name'].upper()}</b><br/>" \
                  f"<b>2026-2027 EĞİTİM-ÖĞRETİM YILI 5. SINIF {exam_data['subject'].upper()} DERSİ</b><br/>" \
                  f"<u>{exam_data['term'].upper()} DEĞERLENDİRME SINAVI</u>"
    if show_answers:
        header_text += " <font color='red'><b>[ DETAYLI CEVAP ANAHTARI ]</b></font>"

    story.append(Paragraph(header_text, title_style))
    story.append(Spacer(1, 6))
    
    info_data = [[
        Paragraph("<b>Adı Soyadı:</b> ....................................", opt_style),
        Paragraph("<b>Sınıf/Şube:</b> 5 / .......", opt_style),
        Paragraph("<b>Numara:</b> .............", opt_style),
        Paragraph("<b>Puan:</b> .......", opt_style)
    ]]
    t_info = Table(info_data, colWidths=[180, 110, 110, 145])
    t_info.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#424242")), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 3), ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F5F5F5"))]))
    story.append(t_info)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#FF6B00"), spaceAfter=0))

    story.append(FrameBreak())
    story.append(NextPageTemplate('LaterPages'))

    for idx, q in enumerate(exam_data['questions'], start=1):
        q_elements = []
        q_header = f"<b>Soru {idx} ({q.get('points', 10)} Puan):</b> {q['question_text']}"
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
            t_opts = Table([
                [Paragraph(f"<b>A)</b> {opts.get('A', '')}", opt_style), Paragraph(f"<b>B)</b> {opts.get('B', '')}", opt_style)],
                [Paragraph(f"<b>C)</b> {opts.get('C', '')}", opt_style), Paragraph(f"<b>D)</b> {opts.get('D', '')}", opt_style)]
            ], colWidths=[120, 120])
            t_opts.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 2)]))
            q_elements.append(t_opts)
        else:
            if not show_answers:
                q_elements.append(Spacer(1, 4))
                t_lines = Table([[""], [""]], colWidths=[240], rowHeights=[14, 14])
                t_lines.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#BDBDBD"))]))
                q_elements.append(t_lines)
                
        if show_answers:
            q_elements.append(Spacer(1, 3))
            ans_box = f"<b>Cevap:</b> {q.get('correct_answer', '')}<br/><b>Açıklama:</b> {q.get('solution_explanation', '')}"
            t_sol = Table([[Paragraph(ans_box, sol_style)]], colWidths=[240])
            t_sol.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 0.6, colors.HexColor("#2E7D32")), ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E8F5E9")), ('PADDING', (0,0), (-1,-1), 4)]))
            q_elements.append(t_sol)

        q_elements.append(Spacer(1, 10))
        story.append(KeepTogether(q_elements))

    doc.build(story, canvasmaker=TwoColumnCanvas)
    buffer.seek(0)
    return buffer

# ==========================================
# 5. STREAMLIT STATE & ARAYÜZ (TEK TEK SORU GÖSTERME MİMARİSİ)
# ==========================================
MEB_CURRICULUM = {
    "Fen Bilimleri": {"1. Dönem 1. Yazılı (Ekim/Kasım)": ["Güneş'in Yapısı ve Özellikleri", "Dünya'nın Şekli ve Hareketleri"]},
    "Matematik": {"1. Dönem 1. Yazılı (Ekim/Kasım)": ["Doğal Sayılar ve İşlemler"]},
    "Türkçe": {"1. Dönem 1. Yazılı (Ekim/Kasım)": ["Sözcükte Anlam ve Paragraf"]},
    "Sosyal Bilgiler": {"1. Dönem 1. Yazılı (Ekim/Kasım)": ["Birey ve Toplum"]},
    "Din Kültürü ve Ahlak Bilgisi": {"1. Dönem 1. Yazılı (Ekim/Kasım)": ["Allah İnancı"]},
    "İngilizce": {"1. Dönem 1. Yazılı (Ekim/Kasım)": ["Unit 1 & Unit 2"]},
    "Almanca": {"1. Dönem 1. Yazılı (Ekim/Kasım)": ["Hallo! & Meine Schule"]}
}

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
if 'current_q_index' not in st.session_state:
    st.session_state.current_q_index = 0

st.sidebar.header("⚙️ Sınav Ayarları")
selected_subject = st.sidebar.selectbox("📖 Ders Seçiniz", list(MEB_CURRICULUM.keys()))
terms_available = list(MEB_CURRICULUM[selected_subject].keys())
selected_term = st.sidebar.selectbox("📅 Sınav Dönemi Seçiniz", terms_available)
selected_units = MEB_CURRICULUM[selected_subject][selected_term]
st.sidebar.info(f"📌 **Dahil Üniteler:**\n" + "\n".join([f"- {u}" for u in selected_units]))
st.sidebar.divider()

if st.sidebar.button("🎲 Yeni Sınav Hazırla", use_container_width=True):
    with st.spinner("Sınav Hazırlanıyor..."):
        if selected_subject in MEB_QUESTION_POOL and selected_term in MEB_QUESTION_POOL[selected_subject]:
            pool = MEB_QUESTION_POOL[selected_subject][selected_term]
            mcqs = [q for q in pool if q['type'] == 'MCQ'][:5]
            opens = [q for q in pool if q['type'] == 'OPEN'][:5]
            exam_json = {
                "school_name": "Şehit Öğretmen 5. Sınıf Ortaokulu",
                "subject": selected_subject,
                "term": selected_term,
                "questions": mcqs + opens
            }
        else:
            exam_json = get_fallback_exam(selected_subject, selected_term)
            
        st.session_state.exam_data = exam_json
        st.session_state.exam_started = False
        st.session_state.exam_completed = False
        st.session_state.user_answers = {}
        st.session_state.current_q_index = 0
        st.success("✅ Sınav başarıyla yüklendi! Başlamak için 'Sınavı Başlat' butonuna basınız.")

if st.session_state.exam_data:
    exam = st.session_state.exam_data
    pdf_exam = build_pdf_exam(exam, show_answers=False)
    pdf_sol = build_pdf_exam(exam, show_answers=True)
    
    col_pdf1, col_pdf2 = st.columns(2)
    with col_pdf1:
        st.download_button("📄 MEB Çift Sütun Formatında Sınav Kağıdı İndir (PDF)", data=pdf_exam, file_name=f"5_Sinif_{exam['subject']}_Yazili_Sinavi.pdf", mime="application/pdf", use_container_width=True)
    with col_pdf2:
        st.download_button("🔑 Çözüm & Cevap Anahtarı İndir (PDF)", data=pdf_sol, file_name=f"5_Sinif_{exam['subject']}_Cevap_Anahtari.pdf", mime="application/pdf", use_container_width=True)

    st.divider()

    # --- DURUM 1: SINAV BAŞLAMADI ---
    if not st.session_state.exam_started and not st.session_state.exam_completed:
        st.warning("⏱️ Sınav hazır! Soruları tek tek çözmek ve süreyi başlatmak için aşağıdaki butona tıklayın.")
        if st.button("🚀 SINAVI BAŞLAT", type="primary", use_container_width=True):
            st.session_state.exam_started = True
            st.session_state.start_time = time.time()
            st.session_state.current_q_index = 0
            st.rerun()

    # --- DURUM 2: SINAV DEVAM EDİYOR (HER SAYFADA TEK SORU) ---
    elif st.session_state.exam_started and not st.session_state.exam_completed:
        elapsed_time = int(time.time() - st.session_state.start_time)
        minutes, seconds = divmod(elapsed_time, 60)
        
        total_qs = len(exam['questions'])
        curr_idx = st.session_state.current_q_index
        q = exam['questions'][curr_idx]
        q_id = q['id']

        # Üst Bilgi & Süre & İlerleme Çubuğu
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            st.markdown(f"### 📝 Soru {curr_idx + 1} / {total_qs}")
        with col_t2:
            st.markdown(f"**⏱️ Süre:** `{minutes:02d}:{seconds:02d}`")
            
        st.progress((curr_idx + 1) / total_qs)
        st.divider()

        # Soru Kartı
        st.markdown(f"""
        <div class="question-card">
            <div>
                <span class="{'badge-mcq' if q['type']=='MCQ' else 'badge-open'}">
                    { 'Çoktan Seçmeli' if q['type']=='MCQ' else 'Açık Uçlu' }
                </span>
                <strong style="margin-left: 10px;">Puan: 10</strong>
            </div>
            <p style="font-size: 17px; margin-top: 15px; font-weight: 600;">{q['question_text']}</p>
        </div>
        """, unsafe_allow_html=True)

        if q.get('has_diagram') and q.get('diagram_type'):
            img_buf = generate_question_image(q['diagram_type'])
            if img_buf:
                st.image(img_buf, width=320)

        # Cevap Giriş Alanı
        saved_ans = st.session_state.user_answers.get(q_id, None)

        if q['type'] == 'MCQ':
            opts = q.get('options', {})
            formatted_opts = [f"{k}) {v}" for k, v in opts.items()]
            
            # Kayıtlı cevabın indeksini bul
            default_index = None
            if saved_ans:
                for idx, opt_str in enumerate(formatted_opts):
                    if opt_str.startswith(saved_ans):
                        default_index = idx
                        break

            selected = st.radio(
                "Lütfen seçiminizi yapınız:",
                formatted_opts,
                key=f"radio_q_{q_id}",
                index=default_index
            )
            if selected:
                st.session_state.user_answers[q_id] = selected[0]
        else:
            user_text = st.text_area(
                "Cevabınızı buraya yazınız:",
                value=saved_ans if saved_ans else "",
                key=f"textarea_q_{q_id}"
            )
            if user_text:
                st.session_state.user_answers[q_id] = user_text

        st.markdown("<br/>", unsafe_allow_html=True)

        # Navigasyon Butonları (Önceki / Sonraki / Sınavı Bitir)
        nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
        
        with nav_col1:
            if curr_idx > 0:
                if st.button("⬅️ Önceki Soru", use_container_width=True):
                    st.session_state.current_q_index -= 1
                    st.rerun()
                    
        with nav_col3:
            if curr_idx < total_qs - 1:
                if st.button("Sonraki Soru ➡️", type="primary", use_container_width=True):
                    st.session_state.current_q_index += 1
                    st.rerun()
            else:
                if st.button("🛑 SINAVI BİTİR VE KARNEYİ GÖR", type="primary", use_container_width=True):
                    st.session_state.exam_started = False
                    st.session_state.exam_completed = True
                    st.rerun()

    # --- DURUM 3: SINAV BİTTİ & KARNE ---
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

        st.info("ℹ️ **Not:** Açık uçlu sorular öğretmen değerlendirmesi gerektirdiği için otomatize teste dahil edilmemiştir.")
        st.divider()
        st.subheader("📝 Detaylı Soru Çözümleri ve Cevap Anahtarı")

        for q in exam['questions']:
            q_id = q['id']
            user_ans = st.session_state.user_answers.get(q_id, "Yanıt Verilmedi")
            correct_ans = q.get('correct_answer', '')

            st.markdown(f"**Soru {q_id}: {q['question_text']}**")
            if q['type'] == 'MCQ':
                is_correct = (user_ans == correct_ans)
                if is_correct:
                    st.success(f"✅ **Doğru!** Cevabınız: **{user_ans}**")
                else:
                    st.error(f"❌ **Yanlış!** Doğru Cevap: **{correct_ans}** | Sizin Cevabınız: **{user_ans}**")
            else:
                st.warning(f"📝 **Sizin Yanıtınız:** {user_ans}\n\n**İdeal/Örnek Cevap:** {correct_ans}")

            with st.expander("🔍 Detaylı Adım Adım Çözüm Açıklaması"):
                st.write(q.get('solution_explanation', 'Çözüm açıklaması bulunamadı.'))
            st.write("---")

else:
    st.info("👈 Sınav oluşturmak için sol menüden dersinizi ve sınav döneminizi seçip **'Yeni Sınav Hazırla'** butonuna tıklayınız.")
