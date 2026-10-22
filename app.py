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
# 2. MEB ONAYLI %100 TÜRKÇE SORU BANKASI
# ==========================================
MEB_QUESTION_POOL = {
    "Fen Bilimleri": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": [
            {
                "id": 1, "type": "MCQ",
                "question_text": "Güneş ile ilgili verilen aşağıdakilerden hangisi yanlıştır?",
                "options": {"A": "Güneş, katmanlardan oluşan devasa bir gaz küresidir.", "B": "Güneş yüzeyindeki soğuk bölgelere 'Güneş lekesi' adı verilir.", "C": "Güneş, Dünya'mıza en yakın yıldızdır.", "D": "Güneş'in yüzey sıcaklığı merkezindeki sıcaklıktan daha fazladır."},
                "correct_answer": "D", "solution_explanation": "Güneş'in merkez sıcaklığı yaklaşık 15 milyon °C iken, yüzey sıcaklığı yaklaşık 6000 °C'dir. Yani merkez sıcaklığı yüzeyinden çok daha fazladır.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 2, "type": "MCQ",
                "question_text": "Galileo Galilei, kendi tasarladığı teleskopla Güneş lekelerini gözlemlemiş ve bu lekelerin hep aynı yöne doğru kaydığını fark etmiştir. Galileo'nun yaptığı bu gözlem aşağıdaki sonuçlardan hangisini kanıtlar?",
                "options": {"A": "Güneş'in Dünya etrafında dolandığını", "B": "Güneş'in kendi ekseni etrafında döndüğünü", "C": "Güneş'in şeklinin tam bir küp olduğunu", "D": "Güneş'in katmanlarının bulunmadığını"},
                "correct_answer": "B", "solution_explanation": "Güneş lekelerinin düzenli olarak aynı yöne doğru kayması, Güneş'in kendi ekseni etrafında dönme hareketi yaptığını kanıtlar.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 3, "type": "MCQ",
                "question_text": "Dünya'nın şekli ve hareketleri ile ilgili aşağıda verilen bilgilerden hangisi doğrudur?",
                "options": {"A": "Dünya, kutuplardan şişkin, ekvatordan basıktır.", "B": "Dünya kendi etrafındaki bir tam turunu 365 gün 6 saatte tamamlar.", "C": "Dünya'nın kendi etrafında dönmesi sonucu gece ve gündüz birbirini takip eder.", "D": "Dünya, Güneş etrafında saat yönünde dolanır."},
                "correct_answer": "C", "solution_explanation": "Dünya ekvatordan şişkin, kutuplardan basıktır. Kendi etrafındaki dönmesini 24 saatte tamamlar ve bu hareket gece-gündüzü oluşturur. Güneş etrafındaki dolanımı saat yönünün tersinedir.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 4, "type": "MCQ",
                "question_text": "Dünya, Güneş ve Ay'ın büyüklükleri karşılaştırıldığında doğru sıralama aşağıdakilerden hangisidir?",
                "options": {"A": "Güneş > Dünya > Ay", "B": "Dünya > Güneş > Ay", "C": "Güneş > Ay > Dünya", "D": "Ay > Dünya > Güneş"},
                "correct_answer": "A", "solution_explanation": "Boyut olarak en büyük gök cismi Güneş, orta büyüklükte Dünya ve en küçükleri ise Ay'dır (Güneş > Dünya > Ay).", "points": 10, "has_diagram": True, "diagram_type": "sun_earth_moon"
            },
            {
                "id": 5, "type": "MCQ",
                "question_text": "Aşağıdakilerden hangisi Ay'ın ana evrelerinden biri değildir?",
                "options": {"A": "Yeni Ay", "B": "İlk Dördün", "C": "Hilal", "D": "Dolunay"},
                "correct_answer": "C", "solution_explanation": "Hilal ve şişkin ay, ana evreler (Yeni Ay, İlk Dördün, Dolunay, Son Dördün) arasındaki ara evrelerdir.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 6, "type": "OPEN",
                "question_text": "Güneş'in içten dışa doğru katmanlarının isimlerini sırasıyla yazınız.",
                "options": {},
                "correct_answer": "Çekirdek, Işık Küre, Renk Küre, Taç Küre",
                "solution_explanation": "Güneş en içten dışa doğru sırasıyla Çekirdek, Işık Küre (Fotosfer), Renk Küre (Kromosfer) ve Taç Küre katmanlarından oluşur.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 7, "type": "OPEN",
                "question_text": "Dünya'nın kendi ekseni etrafındaki dönme hareketi ne kadar sürede tamamlanır ve bu hareket sonucunda hangi temel olay gerçekleşir?",
                "options": {},
                "correct_answer": "24 saatte (1 günde) tamamlanır. Gece ve gündüz oluşur.",
                "solution_explanation": "Dünya kendi ekseni etrafındaki tam turunu 24 saatte tamamlar ve bu hareket sonucunda gece ile gündüz birbirini takip eder.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 8, "type": "OPEN",
                "question_text": "Ay'ın Dünya'ya olan uzaklığı sürekli değişmesine rağmen Dünya'dan bakıldığında Ay'ı hep aynı yüzde (aynı tarafını) görmemizin temel sebebi nedir?",
                "options": {},
                "correct_answer": "Ay'ın kendi ekseni etrafındaki dönme süresi ile Dünya etrafındaki dolanma süresinin eşit olması (yaklaşık 27 gün 8 saat).",
                "solution_explanation": "Ay kendi etrafında dönerken aynı sürede Dünya etrafında da tur atar, bu yüzden hep aynı yüzü bize dönük kalır.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 9, "type": "OPEN",
                "question_text": "Ay atmosferinin çok ince olmasının Ay yüzeyindeki sıcaklık farkları ve göktaşları açısından sonuçları nelerdir kısaca açıklayınız.",
                "options": {},
                "correct_answer": "Atmosfer olmadığı için gece ile gündüz arasındaki sıcaklık farkı çok fazladır ve göktaşları yanmadan doğrudan yüzeye çarparak kraterler oluşturur.",
                "solution_explanation": "Atmosfer ısıyı tutamadığı için aşırı sıcaklık farkları olur ve göktaşları engellenemez.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 10, "type": "OPEN",
                "question_text": "Güneş tutulması olayı hangi ana evrede ve hangi gök cisminin araya girmesiyle gerçekleşir?",
                "options": {},
                "correct_answer": "Yeni Ay evresinde, Ay'ın Dünya ile Güneş arasına girmesiyle gerçekleşir.",
                "solution_explanation": "Güneş tutulması yeni ay evresinde Ay'ın Güneş'i kapatmasıyla oluşur.",
                "points": 10, "has_diagram": False, "diagram_type": None
            }
        ]
    },
    "Matematik": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": [
            {
                "id": 1, "type": "MCQ",
                "question_text": "Okunuşu 'Yüz iki milyon bin kırk beş' olan doğal sayı aşağıdakilerden hangisidir?",
                "options": {"A": "102 001 045", "B": "102 010 045", "C": "120 001 045", "D": "102 001 450"},
                "correct_answer": "A", "solution_explanation": "Milyonlar bölüğü: 102, Binler bölüğü: 001, Birler bölüğü: 045 -> 102 001 045", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 2, "type": "MCQ",
                "question_text": "845 392 716 sayısının milyonlar bölüğündeki rakamların toplamı kaçtır?",
                "options": {"A": "14", "B": "17", "C": "19", "D": "21"},
                "correct_answer": "B", "solution_explanation": "Milyonlar bölüğü 845'tir. Rakamlar toplamı: 8 + 4 + 5 = 17.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 3, "type": "MCQ",
                "question_text": "87 604 - 39 485 işleminin sonucu kaçtır?",
                "options": {"A": "48 119", "B": "48 219", "C": "47 119", "D": "49 119"},
                "correct_answer": "A", "solution_explanation": "87604 - 39485 = 48119.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 4, "type": "MCQ",
                "question_text": "Bir ormandaki fidan dikme etkinliğinde ilk gün 24 580 fidan, ikinci gün ise ilk günden 3 420 fazla fidan dikilmiştir. İki günde toplam kaç fidan dikilmiştir?",
                "options": {"A": "48 000", "B": "51 000", "C": "52 580", "D": "56 000"},
                "correct_answer": "C", "solution_explanation": "İkinci gün: 24580 + 3420 = 28000. İki gün toplam: 24580 + 28000 = 52580.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 5, "type": "MCQ",
                "question_text": "73 408 925 sayısındaki '3' rakamının basamak değeri ile '4' rakamının basamak değerinin toplamı kaçtır?",
                "options": {"A": "3 004 000", "B": "3 040 000", "C": "3 400 000", "D": "30 040 000"},
                "correct_answer": "B", "solution_explanation": "3 milyonluk basamakta (3 000 000), 4 on binlik basamakta (40 000). Toplam: 3 040 000.", "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 6, "type": "OPEN",
                "question_text": "4, 0, 7, 2, 9 rakamlarını birer kez kullanarak yazılabilecek en büyük beş basamaklı doğal sayı ile en küçük beş basamaklı doğal sayının farkı kaçtır?",
                "options": {},
                "correct_answer": "76 521",
                "solution_explanation": "En büyük sayı: 97420, En küçük sayı: 20479. Fark: 97420 - 20479 = 76521.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 7, "type": "OPEN",
                "question_text": "Bir beyaz eşya mağazasından 18 450 TL'ye televizyon ve 14 300 TL'ye çamaşır makinesi alan bir kişi, satıcıya 35 000 TL vermiştir. Buna göre kaç TL para üstü almalıdır?",
                "options": {},
                "correct_answer": "2 250 TL",
                "solution_explanation": "Toplam tutar: 18450 + 14300 = 32750 TL. Para üstü: 35000 - 32750 = 2250 TL.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 8, "type": "OPEN",
                "question_text": "Bir çiftlikte 1450 koyun vardır. Koyunların sayısından 380 fazla inek, ineklerin sayısından 520 eksik tavuk olduğuna göre çiftlikteki toplam hayvan sayısı kaçtır?",
                "options": {},
                "correct_answer": "4 460",
                "solution_explanation": "Koyun: 1450, İnek: 1450 + 380 = 1830, Tavuk: 1830 - 520 = 1310. Toplam: 1450 + 1830 + 1310 = 4460.",
                "points": 10, "has_diagram": False, "diagram_type": None
            },
            {
                "id": 9, "type": "OPEN",
                "question_text": "ABC üçgeninde A açısı 65 derece, B açısı 50 derece ise C açısı kaç derecedir?",
                "options": {},
                "correct_answer": "65 derece",
                "solution_explanation": "Üçgenin iç açılar toplamı 180 derecedir. 65 + 50 = 115. 180 - 115 = 65 derece.",
                "points": 10, "has_diagram": True, "diagram_type": "triangle"
            },
            {
                "id": 10, "type": "OPEN",
                "question_text": "Yüzler basamağında 4, binler basamağında 7 olan en küçük beş basamaklı doğal sayı kaçtır?",
                "options": {},
                "correct_answer": "17 400",
                "solution_explanation": "On binler basamağı 1, binler 7, yüzler 4, onlar ve birler 0 seçilmelidir -> 17 400.",
                "points": 10, "has_diagram": False, "diagram_type": None
            }
        ]
    }
}

# Varsayılan havuz (Diğer dersler için dinamik şablon üretici)
def get_fallback_exam(subject, term):
    questions = []
    for i in range(1, 6):
        questions.append({
            "id": i, "type": "MCQ",
            "question_text": f"5. Sınıf {subject} dersi {term} dönemi ile ilgili temel kazanım sorusu {i}?",
            "options": {"A": "Birinci doğru seçenek", "B": "İkinci çeldirici seçenek", "C": "Üçüncü çeldirici seçenek", "D": "Dördüncü çeldirici seçenek"},
            "correct_answer": "A", "solution_explanation": f"Bu sorunun doğru yanıtı A şıkkıdır çünkü {subject} müfredatına tam uygundur.",
            "points": 10, "has_diagram": False, "diagram_type": None
        })
    for i in range(6, 11):
        questions.append({
            "id": i, "type": "OPEN",
            "question_text": f"5. Sınıf {subject} dersi {term} dönemi açık uçlu değerlendirme sorusu {i-5}?",
            "options": {},
            "correct_answer": "Örnek ideal öğrenci yanıtı ve anahtar kelimeler.",
            "solution_explanation": "Öğrenci bu soruda temel kavramları eksiksiz açıklamalıdır.",
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
    
    header_text = f"<b>{exam_data['school_name'].upper()}</b><br/>" \
                  f"<b>2026-2027 EĞİTİM-ÖĞRETİM YILI 5. SINIF {exam_data['subject'].upper()} DERSİ</b><br/>" \
                  f"<u>{exam_data['term'].upper()} DEĞERLENDİRME SINAVI</u>"
                  
    if show_answers:
        header_text += " <font color='red'><b>[ DETAYLI CEVAP ANAHTARI ]</b></font>"

    story.append(Paragraph(header_text, title_style))
    story.append(Spacer(1, 6))
    
    info_data = [
        [
            Paragraph("<b>Adı Soyadı:</b> ....................................", opt_style),
            Paragraph("<b>Sınıf/Şube:</b> 5 / .......", opt_style),
            Paragraph("<b>Numara:</b> .............", opt_style),
            Paragraph("<b>Puan:</b> .......", opt_style)
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
            opt_table_data = [
                [Paragraph(f"<b>A)</b> {opts.get('A', '')}", opt_style), Paragraph(f"<b>B)</b> {opts.get('B', '')}", opt_style)],
                [Paragraph(f"<b>C)</b> {opts.get('C', '')}", opt_style), Paragraph(f"<b>D)</b> {opts.get('D', '')}", opt_style)]
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
            ans_box = f"<b>Cevap:</b> {q.get('correct_answer', '')}<br/>" \
                      f"<b>Açıklama:</b> {q.get('solution_explanation', '')}"
            
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
# 5. STREAMLIT STATE & ARAYÜZ
# ==========================================
MEB_CURRICULUM = {
    "Fen Bilimleri": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Güneş'in Yapısı ve Özellikleri", "Dünya'nın Şekli ve Hareketleri"]
    },
    "Matematik": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Doğal Sayılar ve İşlemler"]
    },
    "Türkçe": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Sözcükte Anlam ve Paragraf"]
    },
    "Sosyal Bilgiler": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Birey ve Toplum"]
    },
    "Din Kültürü ve Ahlak Bilgisi": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Allah İnancı"]
    },
    "İngilizce": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Unit 1 & Unit 2"]
    },
    "Almanca": {
        "1. Dönem 1. Yazılı (Ekim/Kasım)": ["Hallo! & Meine Schule"]
    }
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

st.sidebar.header("⚙️ Sınav Ayarları")
selected_subject = st.sidebar.selectbox("📖 Ders Seçiniz", list(MEB_CURRICULUM.keys()))
terms_available = list(MEB_CURRICULUM[selected_subject].keys())
selected_term = st.sidebar.selectbox("📅 Sınav Dönemi Seçiniz", terms_available)

selected_units = MEB_CURRICULUM[selected_subject][selected_term]
st.sidebar.info(f"📌 **Dahil Üniteler:**\n" + "\n".join([f"- {u}" for u in selected_units]))

st.sidebar.divider()

if st.sidebar.button("🎲 Yeni Sınav Hazırla", use_container_width=True):
    with st.spinner("MEB Müfredatına uygun 5 Çoktan Seçmeli + 5 Açık Uçlu Sınav Yükleniyor..."):
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
        st.success("✅ Sınav başarıyla yüklendi! Başlamak için 'Sınavı Başlat' butonuna basınız.")

# ==========================================
# 6. ANA EKRAN & SINAV MODU
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

    if not st.session_state.exam_started and not st.session_state.exam_completed:
        st.warning("⏱️ Sınav hazır! Soruları görmek ve süreyi başlatmak için aşağıdaki butona tıklayın.")
        if st.button("🚀 SINAVI BAŞLAT", type="primary", use_container_width=True):
            st.session_state.exam_started = True
            st.session_state.start_time = time.time()
            st.rerun()

    elif st.session_state.exam_started and not st.session_state.exam_completed:
        elapsed_time = int(time.time() - st.session_state.start_time)
        minutes, seconds = divmod(elapsed_time, 60)
        
        st.subheader(f"⏱️ Geçen Süre: {minutes:02d}:{seconds:02d}")
        st.progress(len(st.session_state.user_answers) / 10.0)

        for q in exam['questions']:
            q_id = q['id']
            st.markdown(f"""
            <div class="question-card">
                <div>
                    <span class="{'badge-mcq' if q['type']=='MCQ' else 'badge-open'}">
                        { 'Çoktan Seçmeli' if q['type']=='MCQ' else 'Açık Uçlu' }
                    </span>
                    <strong style="margin-left: 10px;">Soru {q_id} (10 Puan)</strong>
                </div>
                <p style="font-size: 16px; margin-top: 10px;">{q['question_text']}</p>
            </div>
            """, unsafe_allow_html=True)

            if q.get('has_diagram') and q.get('diagram_type'):
                img_buf = generate_question_image(q['diagram_type'])
                if img_buf:
                    st.image(img_buf, width=300)

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

        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("🛑 SINAVI BİTİR VE KARNEYİ GÖR", type="primary", use_container_width=True):
            st.session_state.exam_started = False
            st.session_state.exam_completed = True
            st.rerun()

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
