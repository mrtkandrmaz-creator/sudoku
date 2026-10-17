import streamlit as st
import json
import re
import random
from groq import Groq
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
    
    # Basit bir geçerli matris türetme
    for r in range(N):
        for c in range(N):
            board[r][c] = ((r * sub_size + r // sub_size + c) % N) + 1
            
    # Hücre boşaltma (Zorluk seviyesine göre)
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
    # Güncellenmiş Groq Modelleri
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
    # Güncellenmiş Gemini Modelleri
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

    # 1. Öncelik: Groq API
    try:
        raw_response = call_groq_api(prompt)
        used_service = "Groq API"
    except Exception as e_groq:
        # 2. Öncelik/Yedek: Gemini API
        try:
            raw_response = call_gemini_api(prompt)
            used_service = "Gemini API (3.8 Flash)"
        except Exception as e_gemini:
            # 3. Son Çare: Yerel Python Sudoku Algoritması
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
            # Yapı bozuk gelirse yerel koda düş
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
