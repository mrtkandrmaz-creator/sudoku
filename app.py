import streamlit as st
import streamlit.components.v1 as components
import json
import re
import random

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
        with st.spinner("Yapay Zeka Bulmacayı Tasarlıyor..."):
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
        st.success(f"Motor: **{st.session_state.active_service}**")

# ==========================================
# 7. ANA EKRAN & PREMIUM UI BİLEŞENİ
# ==========================================
st.title("🧩 Pro Sudoku Studio")

if not st.session_state.game_started:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #ffffff 0%, #fff7ed 100%); border: 2px solid #fed7aa; padding: 35px; border-radius: 16px; margin-top: 20px; box-shadow: 0 10px 30px rgba(234, 88, 12, 0.08);">
        <h2 style="color: #ea580c; margin-top: 0; font-weight: 800;">✨ Profesyonel Sudoku Deneyimine Hoş Geldiniz</h2>
        <p style="font-size: 1.15rem; line-height: 1.7; color: #334155;">
            Yenilenen yüksek performanslı HTML5 Canvas mimarisi, kusursuz blok kenarlıkları ve anlık otomatik bitiş algoritmalarıyla donatılmıştır. 
            Sol panelden matris boyutunu ve zorluk derecesini seçip <b>"Oyuna Başla"</b> butonuna tıklayarak hemen maceraya atılabilirsiniz.
        </p>
        <hr style="border-color: #fed7aa; margin: 20px 0;">
        <p style="color: #f97316; font-weight: 700; font-size: 1.05rem;">
            🚀 Hazır olduğunuzda sol menüden turuncu butona tıklayın!
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    sub_size = st.session_state.sub_size
    N = sub_size * sub_size
    initial_grid_json = json.dumps(st.session_state.initial_board)

    custom_sudoku_component = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{
                background-color: #f8fafc;
                margin: 0;
                padding: 10px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }}
            .sudoku-wrapper {{
                background: #0f172a;
                padding: 6px;
                border-radius: 12px;
                box-shadow: 0 20px 35px -10px rgba(15, 23, 42, 0.3);
            }}
            .grid-container {{
                display: grid;
                grid-template-columns: repeat({N}, 1fr);
                gap: 1px;
                background-color: #475569;
            }}
            .sudoku-cell {{
                width: {min(520 // N, 65)}px;
                height: {min(520 // N, 65)}px;
                background-color: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: {max(1.1, 2.0 - (N * 0.06))}rem;
                font-weight: 800;
                color: #0f172a;
                outline: none;
                border: none;
                text-align: center;
                user-select: none;
                margin: 0;
                padding: 0;
                transition: all 0.1s ease;
            }}
            .sudoku-cell:focus {{
                background-color: #ffedd5 !important;
                box-shadow: inset 0 0 0 3px #f97316 !important;
                z-index: 20;
            }}
            .fixed-cell {{
                background-color: #f1f5f9;
                color: #ea580c;
                font-weight: 900;
                cursor: not-allowed;
            }}
            .border-right-thick {{
                border-right: 3px solid #0f172a !important;
            }}
            .border-bottom-thick {{
                border-bottom: 3px solid #0f172a !important;
            }}
        </style>
    </head>
    <body>

        <!-- Üst Bilgi Kartı -->
        <div class="w-full max-w-lg flex justify-between items-center bg-white border-2 border-orange-500 px-6 py-3.5 rounded-xl mb-6 shadow-sm">
            <div class="flex items-center space-x-2">
                <span class="text-xl">⏱️</span>
                <span class="font-extrabold text-orange-600 text-base">Geçen Süre:</span>
            </div>
            <div id="timer" class="font-black text-slate-800 text-xl tracking-wider font-mono">00:00</div>
        </div>

        <!-- Sudoku Tahtası -->
        <div class="sudoku-wrapper">
            <div class="grid-container" id="sudoku-grid"></div>
        </div>

        <!-- Zafer Kutlama Banner -->
        <div id="win-banner" class="hidden w-full max-w-lg bg-emerald-50 border-2 border-emerald-500 text-emerald-800 p-5 rounded-xl text-center font-extrabold text-lg mt-6 shadow-md animate-bounce">
            🎉 MÜKEMMEL! Bulmacayı <span id="final-time" class="text-emerald-600 underline"></span> sürede kusursuz tamamladınız!
        </div>

        <script>
            const N = {N};
            const subSize = {sub_size};
            const initialBoard = {initial_grid_json};
            let currentBoard = JSON.parse(JSON.stringify(initialBoard));
            let startTime = Date.now();
            let timerInterval = null;
            let isCompleted = false;

            // Sayaç Fonksiyonu
            function startTimer() {{
                timerInterval = setInterval(() => {{
                    if (isCompleted) return;
                    let elapsed = Math.floor((Date.now() - startTime) / 1000);
                    let m = Math.floor(elapsed / 60).toString().padStart(2, '0');
                    let s = (elapsed % 60).toString().padStart(2, '0');
                    document.getElementById('timer').innerText = m + ":" + s;
                }}, 1000);
            }}

            // Anlık Çözüm Denetleyicisi
            function checkSolved() {{
                for (let r = 0; r < N; r++) {{
                    for (let c = 0; c < N; c++) {{
                        if (currentBoard[r][c] === 0) return false;
                    }}
                }}
                for (let i = 0; i < N; i++) {{
                    let rSet = new Set();
                    let cSet = new Set();
                    for (let j = 0; j < N; j++) {{
                        let rVal = currentBoard[i][j];
                        let cVal = currentBoard[j][i];
                        if (rSet.has(rVal) || cSet.has(cVal)) return false;
                        rSet.add(rVal);
                        cSet.add(cVal);
                    }}
                }}
                for (let r = 0; r < N; r += subSize) {{
                    for (let c = 0; c < N; c += subSize) {{
                        let bSet = new Set();
                        for (let i = 0; i < subSize; i++) {{
                            for (let j = 0; j < subSize; j++) {{
                                let val = currentBoard[r + i][c + j];
                                if (bSet.has(val)) return false;
                                bSet.add(val);
                            }}
                        }}
                    }}
                }}
                return true;
            }}

            // Grid İnşası
            const gridEl = document.getElementById('sudoku-grid');
            for (let r = 0; r < N; r++) {{
                for (let c = 0; c < N; c++) {{
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.inputMode = 'numeric'; // Sadece sayısal klavye tetiklemesi için
                    input.pattern = '[0-9]*';
                    input.maxLength = N > 9 ? 2 : 1;
                    input.className = 'sudoku-cell';

                    if ((c + 1) % subSize === 0 && c < N - 1) input.classList.add('border-right-thick');
                    if ((r + 1) % subSize === 0 && r < N - 1) input.classList.add('border-bottom-thick');

                    if (initialBoard[r][c] !== 0) {{
                        input.value = initialBoard[r][c];
                        input.className += ' fixed-cell';
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

                            if (checkSolved()) {{
                                isCompleted = true;
                                clearInterval(timerInterval);
                                document.getElementById('final-time').innerText = document.getElementById('timer').innerText;
                                const banner = document.getElementById('win-banner');
                                banner.classList.remove('hidden');
                            }}
                        }});
                    }}
                    gridEl.appendChild(input);
                }}
            }}

            startTimer();
        </script>
    </body>
    </html>
    """

    components.html(custom_sudoku_component, height=680, scrolling=False)
