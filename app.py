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

# API İstemci Kütüphaneleri
try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

# ReportLab İçe Aktarımları
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
# 1. SAYFA YAPILANDIRMASI VE ÖZEL CSS
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
    <div class="header-sub">Tam Otomatik Secrets.toml API Yük Dengelemeli Soru Robotu</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. MEB 5. SINIF TAM MÜFREDAT YAPISI
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
# 3. SECRETS.TOML API OKUYUCU (TAM UYUMLU)
# ==========================================
def load_secrets_api_keys():
    groq_list = []
    gemini_list = []

    try:
        # [api_keys] altındaki groq_keys ve gemini_keys listelerini doğrudan al
        if "api_keys" in st.secrets:
            api_section = st.secrets["api_keys"]
            if "groq_keys" in api_section:
                groq_list = list(api_section["groq_keys"])
            if "gemini_keys" in api_section:
                gemini_list = list(api_section["gemini_keys"])
        else:
            # Alternatif kök seviye listeler varsa yakala
            if "groq_keys" in st.secrets:
                groq_list = list(st.secrets["groq_keys"])
            if "gemini_keys" in st.secrets:
                gemini_list = list(st.secrets["gemini_keys"])
    except Exception:
        pass

    return groq_list, gemini_list

# ==========================================
# 4. YÜK DENGELEMELİ & DİNAMİK AI SORU ÜRETİCİ
# ==========================================
def generate_questions_with_ai(subject, unit):
    groq_keys, gemini_keys = load_secrets_api_keys()

    prompt = f"""
    Sen MEB 5. sınıf müfredatına tam hakim uzman bir ilköğretim öğretmenisin.
    Ders: {subject}
    Ünite/Konu: {unit}

    Lütfen bu ünite ile ilgili 5 adet Çoktan Seçmeli (MCQ) ve 5 adet Açık Uçlu (OPEN) olmak üzere toplam 10 özgün soru üret.
    Sorular MEB kazanımlarına tam uygun olmalıdır.
    Görsel gerekiyorsa "has_diagram": true yap ve "diagram_type" alanını şunlardan biri seç:
    ['moon_phases', 'dynamometer', 'circle_radius', 'equilateral_triangle', 'ray_segment', 'coordinate_grid', 'triangle_perpendicular', 'sun_earth_moon']
    Gerekmiyorsa "has_diagram": false ve "diagram_type": null yaz.

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
                "solution_explanation": "Açıklama...",
                "points": 10,
                "has_diagram": true,
                "diagram_type": "moon_phases"
            }}
        ]
    }}
    Açık uçlu (OPEN) sorular için "options": {{}} ve "correct_answer": "İdeal cevap" yaz.
    """

    last_error = ""

    # 1. Öncelik: Groq API (Çok Hızlı)
    if Groq and groq_keys:
        for key in groq_keys:
            try:
                client = Groq(api_key=key.strip())
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "Sen JSON formatında veri döndüren bir MEB soru robotusun."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                text = completion.choices[0].message.content.strip()
                parsed = json.loads(text)
                if "questions" in parsed and len(parsed["questions"]) > 0:
                    return parsed["questions"], f"Groq API ({key[:8]}...)"
            except Exception as e:
                last_error = f"Groq Hata: {e}"
                continue

    # 2. Öncelik: Gemini API (Yedek)
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
                    return parsed["questions"], f"Gemini API ({key[:8]}...)"
            except Exception as e:
                last_error = f"Gemini Hata: {e}"
                continue

    # Hiçbir anahtar çalışmazsa uyarı verip düşüş havuzunu döndür
    st.error(f"⚠️ Secrets içerisindeki anahtarlar yanıt vermedi. Son durum: {last_error}")
    return get_fallback_questions(subject, unit), "Yerel Statik Havuz"

def get_fallback_questions(subject, unit):
    questions = []
    for i in range(1, 6):
        questions.append({
            "id": i, "type": "MCQ",
            "question_text": f"5. Sınıf {subject} ({unit}) ünitesiyle ilgili örnek test sorusu {i}?",
            "options": {"A": "Doğru seçenek", "B": "Çeldirici A", "C": "Çeldirici B", "D": "Çeldirici C"},
            "correct_answer": "A", "solution_explanation": "Bu soru MEB müfredatına uygun olarak oluşturulmuştur.",
            "points": 10, "has_diagram": True if i in [2, 3] else False, "diagram_type": "moon_phases" if i==2 else "dynamometer" if i==3 else None
        })
    for i in range(6, 11):
        questions.append({
            "id": i, "type": "OPEN",
            "question_text": f"5. Sınıf {subject} ({unit}) ünitesiyle ilgili açık uçlu soru {i-5}?",
            "options": {},
            "correct_answer": "Örnek ideal öğrenci yanıtı.",
            "solution_explanation": "Kazanım açıklaması.",
            "points": 10, "has_diagram": False, "diagram_type": None
        })
    return questions

# ==========================================
# 5. GÖRSEL ÇİZİM MOTORU (MATPLOTLIB)
# ==========================================
def generate_question_image(diagram_type):
    fig, ax = plt.subplots(figsize=(3.2, 2.2), dpi=110)
    
    if diagram_type in ["triangle", "triangle_perpendicular"]:
        p1, p2, p3 = [0, 0], [4, 0], [2, 3]
        triangle = plt.Polygon([p1, p2, p3], fill=None, edgecolor='#FF6B00', linewidth=2)
        ax.add_patch(triangle)
        if diagram_type == "triangle_perpendicular":
            ax.plot([2, 2], [0, 3], color='#1E90FF', linestyle='--', linewidth=1.5)
            ax.text(2.1, 1.5, 'Dikme (h)', color='#1E90FF', fontsize=8, fontweight='bold')
        ax.text(p1[0]-0.2, p1[1]-0.2, 'A', fontsize=9, fontweight='bold')
        ax.text(p2[0]+0.1, p2[1]-0.2, 'B', fontsize=9, fontweight='bold')
        ax.text(p3[0], p3[1]+0.2, 'C', fontsize=9, fontweight='bold')
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 4)
        ax.axis('off')
        
    elif diagram_type == "sun_earth_moon":
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

    elif diagram_type == "moon_phases":
        circle = plt.Circle((2, 2), 1.2, color='#333333', fill=True)
        ax.add_patch(circle)
        theta = np.linspace(-np.pi/2, np.pi/2, 100)
        x = 2 + 1.2 * np.cos(theta)
        y = 2 + 1.2 * np.sin(theta)
        ax.fill_betweenx(y, 2, x, color='#FFD700', alpha=0.9)
        ax.text(2, 0.4, "Ay Evresi", horizontalalignment='center', fontsize=9, fontweight='bold', color='#333333')
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 4)
        ax.axis('off')

    elif diagram_type == "dynamometer":
        ax.plot([2, 2], [3.5, 3.8], color='black', linewidth=3)
        ax.plot([1.7, 2.3], [3.5, 3.5], color='black', linewidth=3)
        y_vals = np.linspace(2.0, 3.5, 15)
        x_vals = 2 + 0.2 * np.sin(np.linspace(0, 4*np.pi, 15))
        ax.plot(x_vals, y_vals, color='#FF6B00', linewidth=2.5)
        rect = plt.Rectangle((1.5, 1.2), 1.0, 2.5, fill=False, edgecolor='gray', linewidth=1.5, linestyle='--')
        ax.add_patch(rect)
        ax.plot([2, 2], [1.0, 1.2], color='black', linewidth=2)
        weight = plt.Rectangle((1.7, 0.4), 0.6, 0.6, color='#1E90FF')
        ax.add_patch(weight)
        ax.text(2, 0.7, 'G', color='white', fontsize=9, fontweight='bold', ha='center', va='center')
        ax.set_xlim(0.5, 3.5)
        ax.set_ylim(0, 4)
        ax.axis('off')

    elif diagram_type == "circle_radius":
        circle = plt.Circle((2, 2), 1.3, fill=False, edgecolor='#FF6B00', linewidth=2)
        ax.add_patch(circle)
        ax.plot([2, 3.3], [2, 2], color='#1E90FF', linewidth=2, marker='o')
        ax.text(2.65, 2.15, 'r = 6 cm', color='#1E90FF', fontsize=9, fontweight='bold')
        ax.plot(2, 2, marker='o', color='black')
        ax.text(1.85, 1.85, 'M', fontsize=9, fontweight='bold')
        ax.set_xlim(0, 4.5)
        ax.set_ylim(0, 4)
        ax.axis('off')

    elif diagram_type == "equilateral_triangle":
        p1, p2, p3 = [1, 0.5], [3, 0.5], [2, 2.8]
        triangle = plt.Polygon([p1, p2, p3], fill=None, edgecolor='#FF6B00', linewidth=2)
        ax.add_patch(triangle)
        ax.text(2, 1.5, '60°', fontsize=9, fontweight='bold', color='#1E90FF', ha='center')
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 3.5)
        ax.axis('off')

    elif diagram_type == "ray_segment":
        ax.plot([0.5, 3.5], [2, 2], color='#FF6B00', linewidth=2, marker='o')
        ax.text(0.5, 2.2, 'A', fontsize=10, fontweight='bold')
        ax.text(3.5, 2.2, 'B', fontsize=10, fontweight='bold')
        ax.text(2, 1.5, '[AB] Doğru Parçası', fontsize=9, fontweight='bold', color='#333333', ha='center')
        ax.set_xlim(0, 4)
        ax.set_ylim(1, 3)
        ax.axis('off')

    elif diagram_type == "coordinate_grid":
        ax.axhline(0, color='gray', linewidth=1)
        ax.axvline(0, color='gray', linewidth=1)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.plot(2, 3, marker='o', markersize=8, color='#FF6B00')
        ax.text(2.2, 3.1, 'A (2, 3)', fontsize=9, fontweight='bold', color='#FF6B00')
        ax.set_xlim(-1, 5)
        ax.set_ylim(-1, 5)
        ax.set_xticks(range(0, 5))
        ax.set_yticks(range(0, 5))
        
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
# 6. TÜRKÇE FONT & REPORTLAB PDF DÜZENİ
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
                  f"<b>2026-2027 EĞİTİM YILI 5. SINIF {exam_data['subject'].upper()}</b><br/>" \
                  f"<u>{exam_data['unit'].upper()} DEĞERLENDİRME SINAVI</u>"
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
# 7. STREAMLIT ARAYÜZ MİMARİSİ
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
if 'current_q_index' not in st.session_state:
    st.session_state.current_q_index = 0

st.sidebar.header("⚙️ Müfredat Ayarları")
selected_subject = st.sidebar.selectbox("📖 Ders Seçiniz", list(MEB_FULL_CURRICULUM.keys()))
selected_unit = st.sidebar.selectbox("📚 Ünite Seçiniz", MEB_FULL_CURRICULUM[selected_subject])

# Secrets Durumunu Göster
groq_k, gemini_k = load_secrets_api_keys()
st.sidebar.info(f"🔑 **secrets.toml Yüklü:**\n- Groq: {len(groq_k)} adet\n- Gemini: {len(gemini_k)} adet")

st.sidebar.divider()

if st.sidebar.button("🚀 AI ile Sınav Oluştur", use_container_width=True):
    with st.spinner("Yapay zeka soru setini ve görselleri hazırlıyor..."):
        questions, provider_used = generate_questions_with_ai(selected_subject, selected_unit)
        
        exam_json = {
            "school_name": "Şehit Öğretmen 5. Sınıf Ortaokulu",
            "subject": selected_subject,
            "unit": selected_unit,
            "provider": provider_used,
            "questions": questions
        }
        st.session_state.exam_data = exam_json
        st.session_state.exam_started = False
        st.session_state.exam_completed = False
        st.session_state.user_answers = {}
        st.session_state.current_q_index = 0
        st.success(f"✅ Soru seti {provider_used} kullanılarak başarıyla oluşturuldu!")

if st.session_state.exam_data:
    exam = st.session_state.exam_data
    pdf_exam = build_pdf_exam(exam, show_answers=False)
    pdf_sol = build_pdf_exam(exam, show_answers=True)
    
    col_pdf1, col_pdf2 = st.columns(2)
    with col_pdf1:
        st.download_button("📄 MEB Çift Sütun PDF Sınav Kağıdı İndir", data=pdf_exam, file_name=f"5_Sinif_{exam['subject']}_Yazili.pdf", mime="application/pdf", use_container_width=True)
    with col_pdf2:
        st.download_button("🔑 Çözüm & Cevap Anahtarı İndir", data=pdf_sol, file_name=f"5_Sinif_{exam['subject']}_Cevaplar.pdf", mime="application/pdf", use_container_width=True)

    st.divider()

    if not st.session_state.exam_started and not st.session_state.exam_completed:
        st.warning(f"⏱️ Sınav hazır! (Üretici: {exam.get('provider', 'AI')}) - Soruları tek tek çözmek ve süreyi başlatmak için butona basın.")
        if st.button("🚀 SINAVI BAŞLAT", type="primary", use_container_width=True):
            st.session_state.exam_started = True
            st.session_state.start_time = time.time()
            st.session_state.current_q_index = 0
            st.rerun()

    elif st.session_state.exam_started and not st.session_state.exam_completed:
        elapsed_time = int(time.time() - st.session_state.start_time)
        minutes, seconds = divmod(elapsed_time, 60)
        
        total_qs = len(exam['questions'])
        curr_idx = st.session_state.current_q_index
        q = exam['questions'][curr_idx]
        q_id = q['id']

        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            st.markdown(f"### 📝 Soru {curr_idx + 1} / {total_qs}")
        with col_t2:
            st.markdown(f"**⏱️ Süre:** `{minutes:02d}:{seconds:02d}`")
            
        st.progress((curr_idx + 1) / total_qs)
        st.divider()

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

        saved_ans = st.session_state.user_answers.get(q_id, None)

        if q['type'] == 'MCQ':
            opts = q.get('options', {})
            formatted_opts = [f"{k}) {v}" for k, v in opts.items()]
            
            default_index = None
            if saved_ans:
                for idx, opt_str in enumerate(formatted_opts):
                    if opt_str.startswith(saved_ans):
                        default_index = idx
                        break

            selected = st.radio("Lütfen seçiminizi yapınız:", formatted_opts, key=f"radio_q_{q_id}", index=default_index)
            if selected:
                st.session_state.user_answers[q_id] = selected[0]
        else:
            user_text = st.text_area("Cevabınızı buraya yazınız:", value=saved_ans if saved_ans else "", key=f"textarea_q_{q_id}")
            if user_text:
                st.session_state.user_answers[q_id] = user_text

        st.markdown("<br/>", unsafe_allow_html=True)

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

    elif st.session_state.exam_completed:
        st.balloons()
        mcq_correct, mcq_wrong, mcq_empty, mcq_score = 0, 0, 0, 0
        
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
    st.info("👈 Sınav oluşturmak için sol menüden dersinizi ve ünitenizi seçip **'AI ile Sınav Oluştur'** butonuna tıklayınız.")
