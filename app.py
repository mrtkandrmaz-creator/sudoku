import streamlit as st
import streamlit.components.v1 as components
import json
import re
import random
import time
from groq import Groq
from google import genai

# ==========================================
# 1. SAYFA KONFİGÜRASYONU
# ==========================================
st.set_page_config(
    page_title="Pro Sudoku Studio",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
# 5. STATE YÖNETİMİ
# ==========================================
if "sub_size" not in st.session_state:
    st.session_state.sub_size = 3
if "board" not in st.session_state:
    st.session_state.board = None
if "initial_board" not in st.session_state:
    st.session_state.initial_board = None
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "active_service" not in st.session_state:
    st.session_state.active_service = None

# ==========================================
# 6. YAN PANEL KONTROLLERİ
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
        options=[
            "2*2 (4 Kare)", 
            "3*3 (9 Kare)", 
            "4*4 (16 Kare)", 
            "5*5 (25 Kare)", 
            "6*6 (36 Kare)"
        ],
        index=1
    )
    
    sub_size_map = {
        "2*2 (4 Kare)": 2,
        "3*3 (9 Kare)": 3,
        "4*4 (16 Kare)": 4,
        "5*5 (25 Kare)": 5,
        "6*6 (36 Kare)": 6
    }
    selected_sub_size = sub_size_map[block_option]
    
    st.markdown("---")
    
    if st.button("🚀 Oyuna Başla", use_container_width=True):
        with st.spinner("Bulmaca Hazırlanıyor..."):
            grid, service = generate_sudoku_ai(selected_sub_size, difficulty)
            if grid:
                st.session_state.sub_size = selected_sub_size
                st.session_state.board = [row[:] for row in grid]
                st.session_state.initial_board = [row[:] for row in grid]
                st.session_state.active_service = service
                st.session_state.game_started = True
                st.rerun()

    if st.session_state.game_started:
        if st.button("🛑 Oyunu Bitir", use_container_width=True):
            st.session_state.game_started = False
            st.session_state.board = None
            st.session_state.initial_board = None
            st.rerun()

    if st.session_state.active_service:
        st.success(f"Aktif AI Motoru: **{st.session_state.active_service}**")

# ==========================================
# 7. MAIN INTERFACE & HTML5 CANVAS SUDOKU ENGINE
# ==========================================
st.title("🧩 Modern Pro Sudoku Studio")

if not st.session_state.game_started:
    st.markdown("""
    <div style="background: #ffffff; border: 2px solid #fed7aa; padding: 30px; border-radius: 12px; margin-top: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <h2 style="color: #ea580c; margin-top: 0;">✨ Hoş Geldiniz!</h2>
        <p style="font-size: 1.1rem; line-height: 1.6; color: #334155;">
            Sıfır gecikmeli, tam uyumlu ve net kenarlıklara sahip yeni Sudoku platformumuza hoş geldiniz.
            Sol menüden zorluk derecesini ve matris boyutunu seçip <b>"Oyuna Başla"</b> butonuna basarak anında oynamaya başlayabilirsiniz.
        </p>
        <hr style="border-color: #fed7aa; margin: 15px 0;">
        <p style="color: #f97316; font-weight: 700;">
            🚀 Oyuna başlamak için sol paneli kullanın.
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    sub_size = st.session_state.sub_size
    N = sub_size * sub_size
    initial_grid_json = json.dumps(st.session_state.initial_board)

    # HTML5/JS Sudoku Bileseni
    custom_sudoku_component = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            * {{
                box-sizing: border-box;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            body {{
                background-color: #f8fafc;
                margin: 0;
                padding: 10px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .header-bar {{
                width: 100%;
                max-width: 600px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #ffffff;
                padding: 12px 20px;
                border: 2px solid #ea580c;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 4px 12px rgba(234, 88, 12, 0.1);
            }}
            .timer-title {{
                font-size: 1.1rem;
                font-weight: 800;
                color: #ea580c;
            }}
            .timer-clock {{
                font-size: 1.2rem;
                font-weight: 900;
                color: #0f172a;
                font-mono: monospace;
            }}
            .sudoku-container {{
                display: inline-block;
                background: #0f172a;
                padding: 4px;
                border-radius: 8px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat({N}, 1fr);
                gap: 1px;
                background-color: #cbd5e1;
            }}
            .cell {{
                width: {520 // N}px;
                height: {520 // N}px;
                background-color: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: {max(1.0, 2.2 - (N * 0.08))}rem;
                font-weight: 800;
                color: #0f172a;
                outline: none;
                border: none;
                text-align: center;
                user-select: none;
                margin: 0;
                padding: 0;
                transition: background-color 0.15s ease;
            }}
            .cell:focus {{
                background-color: #ffedd5 !important;
                box-shadow: inset 0 0 0 2px #f97316;
            }}
            .fixed {{
                background-color: #f1f5f9;
                color: #ea580c;
                font-weight: 900;
                cursor: not-allowed;
            }}
            .border-right {{
                border-right: 3px solid #0f172a !important;
            }}
            .border-bottom {{
                border-bottom: 3px solid #0f172a !important;
            }}
            .win-banner {{
                display: none;
                width: 100%;
                max-width: 600px;
                background: #dcfce7;
                border: 2px solid #22c55e;
                color: #15803d;
                padding: 16px;
                border-radius: 10px;
                text-align: center;
                font-weight: 800;
                font-size: 1.2rem;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>

        <div class="header-bar">
            <div class="timer-title">⏱️ Geçen Süre</div>
            <div class="timer-clock" id="timer">00:00</div>
        </div>

        <div class="sudoku-container">
            <div class="grid" id="sudoku-grid"></div>
        </div>

        <div class="win-banner" id="win-banner">
            🎉 TEBRİKLER! Bulmacayı <span id="final-time"></span> sürede kusursuz tamamladınız!
        </div>

        <script>
            const N = {N};
            const subSize = {sub_size};
            const initialBoard = {initial_grid_json};
            let currentBoard = JSON.parse(JSON.stringify(initialBoard));
            let startTime = Date.now();
            let timerInterval = null;
            let isCompleted = false;

            // Timer Başlatma
            function startTimer() {{
                timerInterval = setInterval(() => {{
                    if (isCompleted) return;
                    let elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
                    let m = Math.floor(elapsedSeconds / 60).toString().padStart(2, '0');
                    let s = (elapsedSeconds % 60).toString().padStart(2, '0');
                    document.getElementById('timer').innerText = m + ":" + s;
                }}, 1000);
            }}

            // Sudoku Çözüm Kontrolü
            function checkSudokuSolved() {{
                for (let r = 0; r < N; r++) {{
                    for (let c = 0; c < N; c++) {{
                        if (currentBoard[r][c] === 0) return false;
                    }}
                }}

                // Satır ve Sütun Kontrolü
                for (let i = 0; i < N; i++) {{
                    let rowSet = new Set();
                    let colSet = new Set();
                    for (let j = 0; j < N; j++) {{
                        let rVal = currentBoard[i][j];
                        let cVal = currentBoard[j][i];
                        if (rowSet.has(rVal) || colSet.has(cVal)) return false;
                        rowSet.add(rVal);
                        colSet.add(cVal);
                    }}
                }}

                // Blok Kontrolü
                for (let r = 0; r < N; r += subSize) {{
                    for (let c = 0; c < N; c += subSize) {{
                        let blockSet = new Set();
                        for (let i = 0; i < subSize; i++) {{
                            for (let j = 0; j < subSize; j++) {{
                                let val = currentBoard[r + i][c + j];
                                if (blockSet.has(val)) return false;
                                blockSet.add(val);
                            }}
                        }}
                    }}
                }}
                return true;
            }}

            // Grid Render
            const gridEl = document.getElementById('sudoku-grid');
            for (let r = 0; r < N; r++) {{
                for (let c = 0; c < N; c++) {{
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.maxLength = N > 9 ? 2 : 1;
                    input.classList.add('cell');

                    if ((c + 1) % subSize === 0 && c < N - 1) input.classList.add('border-right');
                    if ((r + 1) % subSize === 0 && r < N - 1) input.classList.add('border-bottom');

                    if (initialBoard[r][c] !== 0) {{
                        input.value = initialBoard[r][c];
                        input.classList.add('fixed');
                        input.readOnly = true;
                    }} else {{
                        input.addEventListener('input', (e) => {{
                            if (isCompleted) return;
                            let val = e.target.value.trim();
                            if (/^\d+$/.test(val)) {{
                                let num = parseInt(val, 10);
                                if (num >= 1 && num <= N) {{
                                    currentBoard[r][c] = num;
                                }} else {{
                                    e.target.value = '';
                                    currentBoard[r][c] = 0;
                                }}
                            }} else {{
                                e.target.value = '';
                                currentBoard[r][c] = 0;
                            }}

                            // Anlık Bitiş Kontrolü
                            if (checkSudokuSolved()) {{
                                isCompleted = true;
                                clearInterval(timerInterval);
                                document.getElementById('final-time').innerText = document.getElementById('timer').innerText;
                                document.getElementById('win-banner').style.display = 'block';
                            }}
                        }});
                    }}
                    gridEl.appendChild(input);
                }
            }}

            startTimer();
        </script>
    </body>
    </html>
    """

    components.html(custom_sudoku_component, height=750, scrolling=False)
