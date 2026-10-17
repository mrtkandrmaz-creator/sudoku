import streamlit as st
import json
import re
import random
from groq import Groq
from google import genai

# ==========================================
# 1. SAYFA VE TEMA AYARLARI (Görsel Temaya Uygun Minimalist CSS)
# ==========================================
st.set_page_config(
    page_title="Pro Sudoku AI Studio",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Arka Plan */
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
    }
    
    /* Text Input Alanlarının CSS Özelleştirmesi */
    div[data-baseweb="input"] {
        border-radius: 4px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        height: 48px !important;
    }
    
    div[data-baseweb="input"]:focus-within {
        border-color: #64748b !important;
        box-shadow: 0 0 0 2px rgba(100, 116, 139, 0.2) !important;
    }
    
    /* Rakamların Metin Özellikleri ve Ortalanması */
    .stTextInput input {
        text-align: center !important;
        font-weight: 600 !important;
        font-size: 1.4rem !important;
        color: #1e293b !important;
        padding: 0 !important;
    }

    /* Sabit (AI Tarafından Verilen) Rakam Hücreleri */
    .fixed-cell {
        background-color: #f1f5f9;
        color: #334155;
        text-align: center;
        line-height: 48px;
        height: 48px;
        border-radius: 4px;
        border: 1px solid #e2e8f0;
        font-weight: 700;
        font-size: 1.4rem;
        user-select: none;
    }

    /* Görseldeki Çizgi Kalınlıkları ve Blok Ayrımı */
    .block-border-right {
        border-right: 3px solid #64748b !important;
        padding-right: 4px !important;
    }
    .block-border-bottom {
        border-bottom: 3px solid #64748b !important;
        padding-bottom: 4px !important;
    }
    
    /* Streamlit varsayılan boşluklarını daraltma */
    [data-testid="column"] {
        padding: 1px !important;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        background-color: #334155;
        color: #ffffff;
        border: none;
        padding: 10px 0;
    }
    .stButton>button:hover {
        background-color: #475569;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SECRETS OKUMA MEKANİZMASI ([api_keys])
# ==========================================
def get_groq_keys():
    try:
        if hasattr(st, "secrets") and "api_keys" in st.secrets:
            return list(st.secrets["api_keys"].get("groq_keys", []))
    except Exception:
        pass
    return []

def get_gemini_keys():
    try:
        if hasattr(st, "secrets") and "api_keys" in st.secrets:
            return list(st.secrets["api_keys"].get("gemini_keys", []))
    except Exception:
        pass
    return []

GROQ_KEYS = get_groq_keys()
GEMINI_KEYS = get_gemini_keys()

# ==========================================
# 3. YEREL SUDOKU ÜRETİCİSİ (FALLBACK/YEDEK)
# ==========================================
def generate_local_sudoku(sub_size, difficulty):
    N = sub_size * sub_size
    board = [[0] * N for _ in range(N)]
    
    for r in range(N):
        for c in range(N):
            board[r][c] = ((r * sub_size + r // sub_size + c) % N) + 1
            
    remove_rates = {"Kolay": 0.3, "Orta": 0.5, "Zor": 0.65, "Uzman": 0.75}
    rate = remove_rates.get(difficulty, 0.5)
    
    for r in range(N):
        for c in range(N):
            if random.random() < rate:
                board[r][c] = 0
                
    return board

# ==========================================
# 4. AI ENTEGRASYONU (Groq + Gemini GenAI SDK)
# ==========================================
def call_groq_api(prompt):
    if not GROQ_KEYS:
        raise ValueError("st.secrets['api_keys']['groq_keys'] altında hiç Groq API Key tanımlanmamış.")
    
    last_error = None
    models_to_try = ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"]
    
    for key in GROQ_KEYS:
        client = Groq(api_key=key)
        for model in models_to_try:
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Sen sadece geçerli JSON döndüren bir Sudoku motorusun. Yanıtında hiçbir markdown veya ekstra açıklama metni olmamalıdır."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                return completion.choices[0].message.content
            except Exception as e:
                last_error = e
                continue
            
    raise ValueError(f"Tüm Groq API anahtarları/modelleri başarısız oldu. Son Hata: {last_error}")

def call_gemini_api(prompt):
    if not GEMINI_KEYS:
        raise ValueError("st.secrets['api_keys']['gemini_keys'] altında hiç Gemini API Key tanımlanmamış.")
    
    last_error = None
    models_to_try = ["gemini-3.6-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    
    for key in GEMINI_KEYS:
        client = genai.Client(api_key=key)
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response.text
            except Exception as e:
                last_error = e
                continue

    raise ValueError(f"Tüm Gemini API anahtarları/modelleri başarısız oldu. Son Hata: {last_error}")

def generate_sudoku_ai(sub_box_size, difficulty):
    N = sub_box_size * sub_box_size
    prompt = f"""
    {N}x{N} boyutunda ({sub_box_size}x{sub_box_size} alt bloklardan oluşan) geçerli ve çözülebilir bir Sudoku tahtası üret.
    Zorluk Seviyesi: {difficulty}.
    
    Kurallar:
    - Rakamlar 1 ile {N} arasında olmalıdır.
    - Boş hücreleri 0 (sıfır) ile temsil et.
    - Çıktı kesinlikle geçerli bir JSON olmalıdır.
    
    JSON Formatı Örneği:
    {{
        "grid": [
            [0, 1, ...],
            [...]
        ]
    }}
    """
    
    raw_response = None
    used_service = None

    try:
        raw_response = call_groq_api(prompt)
        used_service = "Groq API"
    except Exception as e_groq:
        try:
            raw_response = call_gemini_api(prompt)
            used_service = "Gemini API"
        except Exception as e_gemini:
            st.warning("API yanıt vermediği için yerel algoritma ile bulmaca oluşturuldu.")
            grid = generate_local_sudoku(sub_box_size, difficulty)
            return grid, "Yerel Algoritma (Offline)"

    try:
        clean_json = re.sub(r'```json\s*|\s*```', '', raw_response).strip()
        data = json.loads(clean_json)
        grid = data.get("grid", [])
        
        if len(grid) == N and all(len(row) == N for row in grid):
            return grid, used_service
        else:
            grid = generate_local_sudoku(sub_box_size, difficulty)
            return grid, "Yerel Algoritma (Yedek)"
    except Exception:
        grid = generate_local_sudoku(sub_box_size, difficulty)
        return grid, "Yerel Algoritma (Yedek)"

# ==========================================
# 5. YARDIMCI VE KONTROL FONKSİYONLARI
# ==========================================
def is_valid_sudoku(grid, sub_size):
    N = sub_size * sub_size
    for i in range(N):
        row_vals = [grid[i][j] for j in range(N) if grid[i][j] != 0]
        col_vals = [grid[j][i] for j in range(N) if grid[j][i] != 0]
        if len(row_vals) != len(set(row_vals)) or len(col_vals) != len(set(col_vals)):
            return False

    for r in range(0, N, sub_size):
        for c in range(0, N, sub_size):
            block_vals = []
            for i in range(sub_size):
                for j in range(sub_size):
                    val = grid[r+i][c+j]
                    if val != 0:
                        block_vals.append(val)
            if len(block_vals) != len(set(block_vals)):
                return False
    return True

def is_solved(grid, sub_size):
    N = sub_size * sub_size
    for r in range(N):
        for c in range(N):
            if grid[r][c] == 0:
                return False
    return is_valid_sudoku(grid, sub_size)

# ==========================================
# 6. STATE (DURUM) YÖNETİMİ
# ==========================================
if "sub_size" not in st.session_state:
    st.session_state.sub_size = 3
if "board" not in st.session_state:
    st.session_state.board = None
if "initial_board" not in st.session_state:
    st.session_state.initial_board = None
if "active_service" not in st.session_state:
    st.session_state.active_service = None

# ==========================================
# 7. YAN PANEL (KONTROL MERKEZİ)
# ==========================================
with st.sidebar:
    st.title("🧩 Sudoku Ayarları")
    st.markdown("---")
    
    block_option = st.selectbox(
        "Izgara / Blok Formatı Seçin:",
        options=["2x2 (4x4 Izgara)", "3x3 (9x9 Standart)", "4x4 (16x16 Izgara)", "5x5 (25x25 Izgara)", "6x6 (36x36 Izgara)"],
        index=1
    )
    
    sub_size_map = {
        "2x2 (4x4 Izgara)": 2,
        "3x3 (9x9 Standart)": 3,
        "4x4 (16x16 Izgara)": 4,
        "5x5 (25x25 Izgara)": 5,
        "6x6 (36x36 Izgara)": 6
    }
    selected_sub_size = sub_size_map[block_option]
    
    difficulty = st.select_slider(
        "Zorluk Seviyesi:",
        options=["Kolay", "Orta", "Zor", "Uzman"]
    )
    
    st.markdown("---")
    
    if st.button("🚀 Yeni Oyun Oluştur", type="primary"):
        with st.spinner("AI Oyunu Hazırlıyor..."):
            grid, service = generate_sudoku_ai(selected_sub_size, difficulty)
            if grid:
                st.session_state.sub_size = selected_sub_size
                st.session_state.board = [row[:] for row in grid]
                st.session_state.initial_board = [row[:] for row in grid]
                st.session_state.active_service = service
                st.rerun()

    if st.session_state.active_service:
        st.success(f"Aktif Motor:\n**{st.session_state.active_service}**")
        
    st.info(f"Yüklenen Key Sayıları:\n- Groq: **{len(GROQ_KEYS)} Adet**\n- Gemini: **{len(GEMINI_KEYS)} Adet**")

# ==========================================
# 8. ANA EKRAN & İNTERAKTİF HÜCRELER
# ==========================================
st.title("🧩 Sudoku Oyunu")

if st.session_state.board is None:
    st.warning("Lütfen sol paneldeki **'Yeni Oyun Oluştur'** butonuna basarak oyunu başlatın.")
else:
    sub_size = st.session_state.sub_size
    N = sub_size * sub_size
    
    st.caption(f"Boyut: **{N}x{N}** | Bloklar: **{sub_size}x{sub_size}** | Değer Aralığı: **1 - {N}**")
    
    # Ortalanmış Sudoku Çerçevesi
    left_pad, main_col, right_pad = st.columns([1, 10, 1])
    
    with main_col:
        for r in range(N):
            cols = st.columns(N)
            for c in range(N):
                val = st.session_state.board[r][c]
                is_read_only = (st.session_state.initial_board[r][c] != 0)
                
                # Blok Ayrım Çizgileri
                border_class = ""
                if (c + 1) % sub_size == 0 and c < N - 1:
                    border_class += " block-border-right"
                if (r + 1) % sub_size == 0 and r < N - 1:
                    border_class += " block-border-bottom"
                
                key = f"cell_{r}_{c}"
                
                with cols[c]:
                    if is_read_only:
                        st.markdown(
                            f'<div class="fixed-cell {border_class}">{val}</div>', 
                            unsafe_allow_html=True
                        )
                    else:
                        current_str = str(val) if val != 0 else ""
                        input_val = st.text_input(
                            label=f"r{r}c{c}",
                            value=current_str,
                            key=key,
                            max_chars=2 if N > 9 else 1,
                            label_visibility="collapsed"
                        )
                        
                        # Girilen metnin rakam kontrolü ve güncellenmesi
                        if input_val.isdigit():
                            parsed_val = int(input_val)
                            if 1 <= parsed_val <= N:
                                st.session_state.board[r][c] = parsed_val
                            else:
                                st.session_state.board[r][c] = 0
                        else:
                            st.session_state.board[r][c] = 0

    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🔍 Hamleleri Kontrol Et"):
            if is_valid_sudoku(st.session_state.board, sub_size):
                if is_solved(st.session_state.board, sub_size):
                    st.balloons()
                    st.success("🎉 TEBRİKLER! Bulmacayı eksiksiz ve doğru şekilde çözdünüz!")
                else:
                    st.info("👍 Şimdiye kadar girdiğiniz tüm rakamlar kurallara uygun. Çözmeye devam edin!")
            else:
                st.error("⚠️ Tahtada çakışan (kural dışı) rakamlar var! Lütfen kontrol edin.")
                
    with col_btn2:
        if st.button("🔄 Sıfırla (Başa Dön)"):
            st.session_state.board = [row[:] for row in st.session_state.initial_board]
            st.rerun()
