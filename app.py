import streamlit as st
import json
import re
import os
import requests
from google import genai

# ==========================================
# 1. SAYFA VE TEMA AYARLARI (Modern UI CSS)
# ==========================================
st.set_page_config(
    page_title="Pro Sudoku AI Studio",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    div[data-baseweb="input"] {
        border-radius: 8px !important;
        border: 1px solid #334155 !important;
        background-color: #1e293b !important;
        color: #f8fafc !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.4) !important;
    }
    .stNumberInput input {
        text-align: center !important;
        font-weight: bold !important;
        font-size: 1.2rem !important;
        color: #f8fafc !important;
    }
    .block-border-right {
        border-right: 3px solid #64748b !important;
    }
    .block-border-bottom {
        border-bottom: 3px solid #64748b !important;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GELİŞMİŞ VE ESNEK SECRETS OKUMA
# ==========================================
def fetch_all_keys(service_prefix):
    """
    st.secrets ve env içerisindeki tüm uyumlu API key'leri toplar.
    Birden fazla key tanımlanmışsa hepsini liste olarak döndürür.
    """
    keys = []
    
    # Environment Variables Kontrolü
    for k, v in os.environ.items():
        if service_prefix.lower() in k.lower() and isinstance(v, str) and v.strip():
            keys.append(v.strip())

    # Streamlit Secrets Taraması (Özyinelemeli/Recursive)
    def extract_keys(data):
        if isinstance(data, dict):
            for k, v in data.items():
                if service_prefix.lower() in k.lower():
                    if isinstance(v, str) and v.strip():
                        keys.append(v.strip())
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, str) and item.strip():
                                keys.append(item.strip())
                    elif isinstance(v, dict):
                        extract_keys(v)
                else:
                    extract_keys(v)

    if hasattr(st, "secrets"):
        try:
            extract_keys(dict(st.secrets))
        except Exception:
            pass

    # Tekilleştır (Sıralamayı koruyarak)
    seen = set()
    unique_keys = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)
            
    return unique_keys

GROQ_KEYS = fetch_all_keys("groq")
GEMINI_KEYS = fetch_all_keys("gemini")

# ==========================================
# 3. AI ENTEGRASYONU (Groq + Gemini Çoklu Key Desteği)
# ==========================================
def call_groq_api(prompt):
    if not GROQ_KEYS:
        raise ValueError("Hiçbir Groq API Key tanımlanmamış.")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    last_error = None

    # Tanımlı tüm Groq key'lerini sırayla dener
    for key in GROQ_KEYS:
        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "Sen sadece geçerli JSON döndüren bir Sudoku motorusun. Yanıtında hiçbir markdown veya ekstra açıklama metni olmamalıdır."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"}
            }
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            last_error = e
            continue
            
    raise ValueError(f"Tüm Groq API anahtarları başarısız oldu. Son Hata: {last_error}")

def call_gemini_api(prompt):
    if not GEMINI_KEYS:
        raise ValueError("Hiçbir Gemini API Key tanımlanmamış.")
    
    last_error = None
    
    # Tanımlı tüm Gemini key'lerini sırayla dener
    for key in GEMINI_KEYS:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            last_error = e
            continue

    raise ValueError(f"Tüm Gemini API anahtarları başarısız oldu. Son Hata: {last_error}")

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

    # 1. Öncelik: Groq API
    try:
        raw_response = call_groq_api(prompt)
        used_service = "Groq API (Llama 3.3)"
    except Exception as e_groq:
        # 2. Öncelik/Yedek: Gemini API
        try:
            raw_response = call_gemini_api(prompt)
            used_service = "Gemini API (2.5 Flash)"
        except Exception as e_gemini:
            st.error(f"Her iki API de yanıt vermedi.\n\n• Groq Hatası: {e_groq}\n\n• Gemini Hatası: {e_gemini}")
            return None, None

    try:
        clean_json = re.sub(r'```json\s*|\s*```', '', raw_response).strip()
        data = json.loads(clean_json)
        grid = data.get("grid", [])
        
        if len(grid) == N and all(len(row) == N for row in grid):
            return grid, used_service
        else:
            st.warning("API gelen veriyi doğru boyutta döndürmedi, tekrar deneniyor...")
            return None, None
    except Exception as parse_error:
        st.error(f"JSON yanıtı işlenirken hata oluştu: {parse_error}")
        return None, None

# ==========================================
# 4. YARDIMCI VE KONTROL FONKSİYONLARI
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
# 5. STATE (DURUM) YÖNETİMİ
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
# 6. YAN PANEL (KONTROL MERKEZİ)
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
        st.success(f"Aktif AI Servisi:\n**{st.session_state.active_service}**")
        
    st.info(f"Tespit Edilen API Key Sayıları:\n- Groq: **{len(GROQ_KEYS)} Adet**\n- Gemini: **{len(GEMINI_KEYS)} Adet**")

# ==========================================
# 7. ANA EKRAN & İNTERAKTİF HÜCRELER
# ==========================================
st.title("🎮 Pro Sudoku AI Edition")

if st.session_state.board is None:
    st.warning("Lütfen sol paneldeki **'Yeni Oyun Oluştur'** butonuna basarak oyunu başlatın.")
else:
    sub_size = st.session_state.sub_size
    N = sub_size * sub_size
    
    st.caption(f"Boyut: **{N}x{N}** | Bloklar: **{sub_size}x{sub_size}** | Değer Aralığı: **1 - {N}**")
    
    grid_container = st.container()
    
    with grid_container:
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
                
                key = f"cell_{r}_{c}"
                
                if is_read_only:
                    cols[c].markdown(
                        f"""<div style="
                            background-color: #334155; 
                            color: #60a5fa; 
                            text-align: center; 
                            padding: 10px 0; 
                            border-radius: 8px; 
                            font-weight: bold; 
                            font-size: 1.2rem;
                            margin-bottom: 8px;"
                            class="{border_class}">
                            {val}
                        </div>""", 
                        unsafe_allow_html=True
                    )
                else:
                    input_val = cols[c].number_input(
                        label=f"r{r}c{c}",
                        min_value=0,
                        max_value=N,
                        value=int(val),
                        step=1,
                        key=key,
                        label_visibility="collapsed"
                    )
                    st.session_state.board[r][c] = input_val

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
