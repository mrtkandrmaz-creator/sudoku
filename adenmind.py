"""AdenMind sohbet motoru: ChatGPT / Gemini gibi her konuda akıcı (akışlı) cevap verir.
app.py ile AYNI klasörde durmalıdır. Harici paket gerektirmez (yalnızca standart kütüphane)."""
import html
import json
import re
import urllib.error
import urllib.request

GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
_DEAD = set()          # (anahtar_sonu, model) -> 404 veren modeller bir daha denenmez
LAST_ERRORS = []

SYSTEM = (
    "Sen AdenMind'sin: ChatGPT ve Gemini gibi, her konuda yardımcı olan, bilgili, samimi ve dürüst bir yapay zekâ asistanısın. "
    "Ders ve ödev (matematik, fen, Türkçe, sosyal, İngilizce...), bilim, tarih, coğrafya, spor, müzik grupları, ünlüler, film, oyun, "
    "teknoloji, kodlama, güncel olaylar, günlük hayat, tavsiye, yaratıcı yazma, çeviri, özet, fikir üretme dâhil NE sorulursa cevap verirsin. "
    "Konu ders dışı olduğu için asla reddetme.\n"
    "ÜSLUP: Kullanıcının dilinde (varsayılan Türkçe) yaz. Selamlaşmayı yalnızca kullanıcı selam verirse yap; her mesajda 'merhaba' deme. "
    "Doğrudan cevaba gir, dolgu ve gereksiz övgü ('harika soru') kullanma. Uzunluğu soruya göre ayarla: basit olguya 1-3 cümle; "
    "açıklama, karşılaştırma, ödev, kod, hikâye gibi isteklerde gerektiği kadar ayrıntılı ve eksiksiz yaz. Cevabı asla yarım bırakma. "
    "Gerektiğinde Markdown kullan: kısa başlıklar, madde işaretleri, **kalın**, tablo yerine liste, kod için ``` blokları. "
    "Matematikte adım adım göster. Örnek ve benzetme kullanarak 10-20 yaşa uygun, anlaşılır anlat.\n"
    "DOĞRULUK: Emin olmadığın bilgiyi uydurma; 'kesin bilmiyorum' de. Güncel konularda (haber, skor, fiyat, yeni çıkanlar, "
    "kişiler/gruplar hakkında son durum) arama sonuçlarını kullan. Sohbet geçmişini hatırla ve 'bunu', 'peki ya o' gibi devam sorularını buna göre anla.\n"
    "GÜVENLİK: Zarar verici, tehlikeli, müstehcen ya da kişisel veri isteyen taleplerde nazikçe reddet ve güvenli bir alternatif öner."
)

LIVE_RE = re.compile(r"haber|son dakika|bugün|dün|yarın|şu an|şimdi|güncel|maç|skor|fikstür|puan durumu|fiyat|kur\b|dolar|euro|altın|borsa|"
                     r"kim kazandı|seçim|konser|albüm|yeni çıkan|vizyon|202\d|başkanı kim|şampiyon|trend|son durum|son çıkan|ne zaman çıkacak|"
                     r"kimdir|grubu|şarkıcı|oyuncu|futbolcu|dizi|film", re.I)


def needs_search(msg):
    return bool(LIVE_RE.search(msg))


def _post(url, body, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "AdenMind/2.0", **headers})
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "ignore")[:140]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} {detail}")


def _sse(resp):
    for raw in resp:
        line = raw.decode("utf-8", "ignore").strip()
        if line.startswith("data:"):
            d = line[5:].strip()
            if d and d != "[DONE]":
                try:
                    yield json.loads(d)
                except ValueError:
                    continue


def _gemini_stream(key, model, system, history, search):
    contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in history]
    body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}}
    if search:
        body["tools"] = [{"google_search": {}}]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
    try:
        resp = _post(url, body, {"x-goog-api-key": key}, 40)
    except RuntimeError as e:
        if search and "HTTP 400" in str(e):  # bu model arama aracını desteklemiyorsa aramasız dene
            body.pop("tools")
            resp = _post(url, body, {"x-goog-api-key": key}, 40)
        else:
            raise
    with resp:
        for ev in _sse(resp):
            cands = ev.get("candidates") or [{}]
            for p in (cands[0].get("content") or {}).get("parts", []):
                if p.get("text") and not p.get("thought"):
                    yield p["text"]


def _groq_stream(key, model, system, history):
    msgs = [{"role": "system", "content": system}] + [{"role": m["role"], "content": m["content"]} for m in history]
    body = {"model": model, "messages": msgs, "stream": True, "temperature": 0.7, "max_tokens": 4096}
    resp = _post("https://api.groq.com/openai/v1/chat/completions", body, {"Authorization": "Bearer " + key}, 30)
    with resp:
        for ev in _sse(resp):
            ch = (ev.get("choices") or [{}])[0].get("delta", {}).get("content")
            if ch:
                yield ch


def stream_answer(history, gemini_keys, groq_keys, context="", search=None):
    """Cevabı parça parça üretir. Sırayla Gemini (arama destekli) -> Groq dener.
    Hiçbiri çalışmazsa hiçbir şey üretmez (çağıran yerel cevaba geçer)."""
    del LAST_ERRORS[:]
    history = [m for m in history if m.get("content")][-24:]
    if not history:
        return
    system = SYSTEM + ("\n" + context if context else "")
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    use_search = needs_search(last_user) if search is None else search
    attempts = []
    for k in gemini_keys:
        for mdl in GEMINI_MODELS:
            attempts.append(("gemini", k, mdl))
    for k in groq_keys:
        for mdl in GROQ_MODELS:
            attempts.append(("groq", k, mdl))
    for kind, key, mdl in attempts:
        if (key[-6:], mdl) in _DEAD:
            continue
        got = False
        try:
            gen = _gemini_stream(key, mdl, system, history, use_search) if kind == "gemini" else _groq_stream(key, mdl, system, history)
            for chunk in gen:
                got = True
                yield chunk
            if got:
                return
            LAST_ERRORS.append(f"{kind}/{mdl}: boş yanıt")
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            LAST_ERRORS.append(f"{kind}/{mdl}: {msg[:80]}")
            if got:
                return  # akış ortasında koptu: yazılanı koru
            if "404" in msg or "NOT_FOUND" in msg:
                _DEAD.add((key[-6:], mdl))
            elif "API key" in msg or "API_KEY_INVALID" in msg or "HTTP 401" in msg or "HTTP 403" in msg:
                _DEAD.update((key[-6:], m) for m in GEMINI_MODELS + GROQ_MODELS)


def format_html(text):
    """Markdown'ı güvenli HTML'e çevirir: kod blokları, başlık, liste, kalın, italik, satır içi kod."""
    parts = re.split(r"```[^\n`]*\n?(.*?)(?:```|$)", text, flags=re.S)
    out = []
    for i, seg in enumerate(parts):
        if i % 2 == 1:
            out.append('<pre class="am-code">' + html.escape(seg.strip("\n")) + "</pre>")
            continue
        lines, in_ul, in_ol = [], False, False
        for ln in seg.split("\n"):
            e = html.escape(ln)
            e = re.sub(r"`([^`]+)`", r"<code>\1</code>", e)
            e = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e)
            e = re.sub(r"(?<![\*\w])\*(?!\s)([^*]+?)\*(?![\*\w])", r"<i>\1</i>", e)
            m_ul = re.match(r"\s*[-*•]\s+(.*)", e)
            m_ol = re.match(r"\s*(\d+)[.)]\s+(.*)", e)
            m_h = re.match(r"\s*#{1,4}\s+(.*)", e)
            if not m_ul and in_ul:
                lines.append("</ul>"); in_ul = False
            if not m_ol and in_ol:
                lines.append("</ol>"); in_ol = False
            if m_ul:
                if not in_ul:
                    lines.append("<ul>"); in_ul = True
                lines.append("<li>" + m_ul.group(1) + "</li>")
            elif m_ol:
                if not in_ol:
                    lines.append("<ol>"); in_ol = True
                lines.append("<li>" + m_ol.group(2) + "</li>")
            elif m_h:
                lines.append('<div class="am-h">' + m_h.group(1) + "</div>")
            elif e.strip():
                lines.append("<p>" + e + "</p>")
        if in_ul:
            lines.append("</ul>")
        if in_ol:
            lines.append("</ol>")
        out.append("".join(lines))
    return "".join(out)


CSS = """
.bub p{margin:0 0 .5em}.bub p:last-child{margin-bottom:0}.bub ul,.bub ol{margin:.2em 0 .5em 1.1em;padding:0}
.bub li{margin:.15em 0}.bub .am-h{font-weight:800;margin:.5em 0 .25em;color:#5eead4}
.bub code{background:rgba(0,0,0,.35);padding:1px 5px;border-radius:6px;font-size:.92em}
.bub pre.am-code{background:#04201f;border:1px solid rgba(94,234,212,.25);padding:10px;border-radius:12px;overflow-x:auto;
white-space:pre;font-family:ui-monospace,Consolas,monospace;font-size:.8rem;margin:.4em 0}
.msg.me .bub p{margin:0}.am-typing{display:inline-block;animation:amb 1s infinite}@keyframes amb{50%{opacity:.25}}
"""
