import streamlit as st
import json
import re
import random
from groq import Groq
from google import genai

# ==========================================
# 1. SAYFA VE BEYAZ/TURUNCU TEMA AYARLARI
# ==========================================
st.set_page_config(
    page_title="Cyber Sudoku Nexus",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Açık Tema Arka Plan */
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 2px solid #e2e8f0;
    }

    /* Hücre Kutuları - Tam Kare ve Net */
    div[data-baseweb="input"] {
        aspect-ratio: 1 / 1 !important;
        width: 100% !important;
        height: auto !important;
        border-radius: 6px !important;
        border: 2px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    div[data-baseweb="input"]:focus-within {
        border-color: #f97316 !important;
        box-shadow: 0 0 8px rgba(249, 115, 22, 0.4) !important;
    }
    
    /* Kullanıcının Yazdığı Rakamlar - Net ve Okunaklı */
    .stTextInput input {
        text-align: center !important;
        font-weight: 800 !important;
        font-size: 1.25rem !important;
        color: #0f172a !important;
        background-color: transparent !important;
        padding: 0 !important;
    }

    /* Sabit Hücreler (AI Rakamları) */
    .fixed-cell {
        aspect-ratio: 1 / 1 !important;
        width: 100% !important;
        background-color: #ffedd5;
        color: #c2410c;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        border: 2px solid #fdba74;
        font-weight: 800;
        font-size: 1.25rem;
        user-select: none;
    }

    /* Kalın Turuncu Blok Kenarlıkları */
    .block-border-right {
        border-right: 4px solid #f97316 !important;
    }
    .block-border-bottom {
        border-bottom: 4px solid #f97316 !important;
    }
    
    /* Büyük Turuncu Butonlar */
    div.stButton > button:first-child {
        width: 100%;
        border-radius: 8px;
        font-weight: 800;
        font-size: 1.05rem;
        background: #f97316;
        color: #ffffff;
        border: none;
        padding: 12px 0;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3);
        margin-top: 10px;
    }
    div.stButton > button:first-child:hover {
        background: #ea580c;
        box-shadow: 0 6px 18px rgba(249, 115, 22, 0.5);
        transform: translateY(-2px);
    }
    
    .timer-card {
        background: #ffffff;
        border: 2px solid #f97316;
        padding: 10px 18px;
        border-radius: 8px;
        text-align: center;
        font-weight: 800;
        font-size: 1.1rem;
        color: #ea580c;
        box-shadow: 0 2px 8px rgba(249, 115, 22, 0.15);
        margin-bottom: 15px;
    }
    
    .welcome-card {
        background: #ffffff;
        border: 2px solid #fed7aa;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SECRETS OKUMA
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
# 3. YEREL SUDOKU ÜRETİCİSİ (YEDEK)
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
# 4. AI ENTEGRASYONU
# ==========================================
def call_groq_api(prompt):
    if not GROQ_KEYS:
        raise ValueError("Groq anahtarı yok.")
    models_to_try = ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"]
    for key in GROQ_KEYS:
        client = Groq(api_key=key)
        for model in models_to_try:
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Sadece geçerli JSON döndüren bir Sudoku motorusun."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                return completion.choices[0].message.content
            except Exception:
                continue
    raise ValueError("Groq başarısız.")

def call_gemini_api(prompt):
    if not GEMINI_KEYS:
        raise ValueError("Gemini anahtarı yok.")
    models_to_try = ["gemini-3.6-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    for key in GEMINI_KEYS:
        client = genai.Client(api_key=key)
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                return response.text
            except Exception:
                continue
    raise ValueError("Gemini başarısız.")

def generate_sudoku_ai(sub_box_size, difficulty):
    N = sub_box_size * sub_box_size
    prompt = f"""
    {N}x{N} boyutunda ({sub_box_size}x{sub_box_size} alt bloklu) geçerli bir Sudoku üret.
    Zorluk: {difficulty}. Boş hücreleri 0 yap. Kesinlikle geçerli JSON döndür:
    {{"grid": [[...]]}}
    """
    try:
        raw = call_groq_api(prompt)
        service = "Groq API"
    except Exception:
        try:
            raw = call_gemini_api(prompt)
            service = "Gemini API"
        except Exception:
            return generate_local_sudoku(sub_box_size, difficulty), "Yerel Algoritma"

    try:
        clean_json = re.sub(r'```json\s*|\s*```', '', raw).strip()
        data = json.loads(clean_json)
        grid = data.get("grid", [])
        if len(grid) == N and all(len(row) == N for row in grid):
            return grid, service
    except Exception:
        pass
    
    return generate_local_sudoku(sub_box_size, difficulty), "Yerel Algoritma"

# ==========================================
# 5. KONTROL FONKSİYONLARI
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
# 6. STATE YÖNETİMİ
# ==========================================
if "sub_size" not in st.session_state:
    st.session_state.sub_size = 3
if "board" not in st.session_state:
    st.session_state.board = None
if "initial_board" not in st.session_state:
    st.session_state.initial_board = None
if "active_service" not in st.session_state:
    st.session_state.active_service = None
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "game_won" not in st.session_state:
    st.session_state.game_won = False

# ==========================================
# 7. YAN PANEL
# ==========================================
with st.sidebar:
    st.title("🧩 Sudoku Ayarları")
    st.markdown("---")
    
    difficulty = st.selectbox(
        "Zorluk Derecesi:",
        options=["Kolay", "Orta", "Zor", "Uzman"],
        index=1
    )
    
    block_option = st.selectbox(
        "Izgara / Blok Formatı:",
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
    
    st.markdown("---")
    
    if st.button("🚀 Oyuna Başla"):
        with st.spinner("Bulmaca Hazırlanıyor..."):
            grid, service = generate_sudoku_ai(selected_sub_size, difficulty)
            if grid:
                st.session_state.sub_size = selected_sub_size
                st.session_state.board = [row[:] for row in grid]
                st.session_state.initial_board = [row[:] for row in grid]
                st.session_state.active_service = service
                st.session_state.game_started = True
                st.session_state.game_won = False
                st.rerun()

    if st.session_state.game_started:
        if st.button("🛑 Oyunu Bitir"):
            st.session_state.game_started = False
            st.session_state.board = None
            st.session_state.initial_board = None
            st.session_state.game_won = False
            st.rerun()

    if st.session_state.active_service:
        st.success(f"Motor: **{st.session_state.active_service}**")

# ==========================================
# 8. ANA EKRAN & OYUN AKIŞI
# ==========================================
st.title("🧩 Modern Sudoku Studio")

if not st.session_state.game_started:
    st.markdown("""
    <div class="welcome-card">
        <h2 style="color: #ea580c; margin-top: 0;">✨ Hoş Geldiniz!</h2>
        <p style="font-size: 1.05rem; line-height: 1.6; color: #334155;">
            Yapay zeka ile desteklenen <b>Modern Sudoku Studio</b> platformuna hoş geldiniz. 
            Açık renkli, göz yormayan turuncu tasarımıyla sol panelden ayarlarınızı yapıp 
            <b>"Oyuna Başla"</b> butonuna basarak oynamaya başlayabilirsiniz.
        </p>
        <hr style="border-color: #fed7aa; margin: 15px 0;">
        <p style="color: #f97316; font-weight: 700;">
            🚀 Başlamak için sol menüden turuncu butona tıklayın!
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    sub_size = st.session_state.sub_size
    N = sub_size * sub_size
    
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(f"**Boyut:** {N}x{N} | **Blok:** {sub_size}x{sub_size}")
    with top_col2:
        st.markdown(f'<div class="timer-card">⏱️ Aktif Oyundasınız</div>', unsafe_allow_html=True)

    def update_cell(r, c):
        val = st.session_state[f"cell_{r}_{c}"]
        if val.isdigit():
            num = int(val)
            if 1 <= num <= N:
                st.session_state.board[r][c] = num
            else:
                st.session_state.board[r][c] = 0
        else:
            st.session_state.board[r][c] = 0
            
        # Son rakam girildiğinde anında otomatik kontrol
        if is_solved(st.session_state.board, sub_size):
            st.session_state.game_won = True

    _, main_col, _ = st.columns([0.5, 9, 0.5])
    
    with main_col:
        for r in range(N):
            cols = st.columns(N)
            for c in range(N):
                val = st.session_state.board[r][c]
                is_read_only = (st.session_state.initial_board[r][c] != 0)
                
                border_class = ""
                if (c + 1) % sub_size == 0 and c < N - 1:
                    border_class += " block-border-right"
                if (r + 1) % sub_size == 0 and r < N - 1:
                    border_class += " block-border-bottom"
                
                cell_key = f"cell_{r}_{c}"
                
                with cols[c]:
                    if is_read_only:
                        st.markdown(
                            f'<div class="fixed-cell {border_class}">{val}</div>', 
                            unsafe_allow_html=True
                        )
                    else:
                        current_str = str(val) if val != 0 else ""
                        st.text_input(
                            label=f"r{r}c{c}",
                            value=current_str,
                            key=cell_key,
                            max_chars=2 if N > 9 else 1,
                            label_visibility="collapsed",
                            on_change=update_cell,
                            args=(r, c)
                        )

    # Otomatik Zafer Bildirimi
    if st.session_state.game_won:
        st.balloons()
        st.success("🎉 TEBRİKLER! Bulmacadaki tüm rakamları eksiksiz ve doğru şekilde tamamladınız!")

    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔍 Hamleleri Kontrol Et"):
            if is_valid_sudoku(st.session_state.board, sub_size):
                if is_solved(st.session_state.board, sub_size):
                    st.balloons()
                    st.success("🎉 TEBRİKLER! Bulmacayı kusursuz bir şekilde tamamladınız!")
                else:
                    st.info("👍 Şimdiye kadarki tüm hamleleriniz kurallara uygun. Çözmeye devam edin!")
            else:
                st.error("⚠️ Dikkat! Tahtada çakışan (kural dışı) rakamlar var. Kontrol ediniz.")
                
    with col_btn2:
        if st.button("🔄 Oyunu Sıfırla"):
            st.session_state.board = [row[:] for row in st.session_state.initial_board]
            st.session_state.game_won = False
            st.rerun()
