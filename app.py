import json
import random
import re
from html import escape as esc

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi",
    page_icon="🎒",
    layout="wide",
    initial_sidebar_state="expanded",
)

import ai_engine as ai  # noqa: E402
import content  # noqa: E402
import games_html as gh  # noqa: E402
import store  # noqa: E402
from avatar import adenmind_avatar  # noqa: E402
from curriculum import GAME_INFO, GAMES, MEB_CURRICULUM  # noqa: E402
from styles import BASE_CSS, EXTRA_CSS, GAME_CSS, HTMLGAME_CSS  # noqa: E402
from visuals import render_question_visual  # noqa: E402

SS = st.session_state
for _k, _v in {
    "selected_subject": None, "selected_unit": None, "selected_game": None, "view": "play",
    "player": "Misafir", "sound_on": True, "toasts": [], "am_pending": None, "plan": None,
    "coach_messages": [{"role": "assistant", "content": "Merhaba ben AdenMind, sana yardımcı olmak için buradayım! ✨"}],
}.items():
    SS.setdefault(_k, _v)

# =============================================================================
# DURUM VE GEZİNME (geri çağrılar: tek tıkla geçiş)
# =============================================================================


def new_gs():
    return {
        "data": None, "failed": False, "idx": 0, "correct": 0, "feedback": None, "show": False,
        "choice": None, "eval": None, "results": None, "guess": [], "used": [], "pool": [], "pool_for": -1,
        "msg": None, "nonce": random.randint(1000, 999999), "recorded": False,
    }


def reset_gs():
    SS["gs_ident"] = None


def get_gs(game):
    ident = (SS["selected_subject"], SS["selected_unit"], game)
    if SS.get("gs_ident") != ident or "gs" not in SS:
        SS["gs_ident"] = ident
        SS["gs"] = new_gs()
    return SS["gs"]


def go_home():
    SS.update(selected_subject=None, selected_unit=None, selected_game=None, view="play")
    reset_gs()


def go_karne():
    SS.update(view="karne", selected_game=None)
    reset_gs()


def pick_subject(s):
    SS.update(selected_subject=s, selected_unit=None, selected_game=None, view="play")
    reset_gs()


def pick_unit(u):
    SS.update(selected_unit=u, selected_game=None)
    reset_gs()


def pick_game(g):
    SS["selected_game"] = g
    reset_gs()


def go_unit(s, u):
    SS.update(selected_subject=s, selected_unit=u, selected_game=None, view="play")
    reset_gs()


def back_to_units():
    SS.update(selected_unit=None, selected_game=None)
    reset_gs()


def back_to_games():
    SS["selected_game"] = None
    reset_gs()


def regen():
    SS["gs"] = new_gs()


def set_player():
    SS["player"] = store.clean_name(SS.get("player_input"))
    SS["plan"] = None


def set_sound():
    SS["sound_on"] = bool(SS.get("sound_toggle"))


def _save_keys():
    # Kenar çubuğu oyun sırasında çizilmediği için widget değeri kaybolur; kalıcı kopyasını tut.
    SS["manual_groq_saved"] = SS.get("manual_groq", "")
    SS["manual_gemini_saved"] = SS.get("manual_gemini", "")


def P():
    return store.prof(SS["player"])


def flush_toasts():
    for t in SS.pop("toasts", []):
        st.toast(t)
    SS["toasts"] = []


# =============================================================================
# SES EFEKTİ (Streamlit tarafı oyunlar için)
# =============================================================================
SFX_HTML = """<script>(function(){try{
var W=window.parent,C=W.AudioContext||W.webkitAudioContext||window.AudioContext;
if(!W.__am_ac){W.__am_ac=new C();} var a=W.__am_ac; if(a.state==='suspended')a.resume();
function t(f,s,d,ty,v){var o=a.createOscillator(),g=a.createGain();o.type=ty||'sine';o.frequency.value=f;
g.gain.setValueAtTime(0.0001,a.currentTime+s);g.gain.exponentialRampToValueAtTime(v||0.18,a.currentTime+s+0.02);
g.gain.exponentialRampToValueAtTime(0.0001,a.currentTime+s+d);o.connect(g);g.connect(a.destination);
o.start(a.currentTime+s);o.stop(a.currentTime+s+d+0.05);}
var k="__K__";
if(k==="ok"){t(660,0,.12);t(880,.1,.18);}
else if(k==="bad"){t(220,0,.22,'sawtooth',.12);t(160,.16,.28,'sawtooth',.12);try{W.navigator.vibrate&&W.navigator.vibrate(120)}catch(e){}}
else if(k==="win"){[523,659,784,1047].forEach(function(f,i){t(f,i*.12,.22)})}
}catch(e){}})();</script><!--__N__-->"""


def sfx(kind):
    if not SS.get("sound_on", True):
        return
    with st.container(key="sfx"):
        components.html(SFX_HTML.replace("__K__", kind).replace("__N__", str(random.random())), height=0)


def flush_sound(gs):
    k = gs.pop("sound", None)
    if k:
        sfx(k)


# =============================================================================
# KART IZGARASI
# =============================================================================


def card_css(key, gradient, height):
    return (
        f".st-key-{key}{{margin-bottom:10px}}"
        f".st-key-{key} button{{position:relative;overflow:hidden;min-height:{height}px;"
        f"background:{gradient} !important;color:#fff !important;border-radius:28px !important;border:0 !important;"
        f"box-shadow:0 8px 0 rgba(0,0,0,.30),0 18px 32px rgba(0,0,0,.28) !important}}"
        f".st-key-{key} button::after{{content:'';position:absolute;right:-26px;top:-26px;width:100px;height:100px;"
        f"border-radius:50%;background:rgba(255,255,255,.18);pointer-events:none}}"
        f".st-key-{key} button::before{{content:'';position:absolute;left:-18px;bottom:-30px;width:70px;height:70px;"
        f"border-radius:22px;transform:rotate(25deg);background:rgba(255,255,255,.12);pointer-events:none}}"
        f".st-key-{key} button:hover{{transform:translateY(-6px) scale(1.015)}}"
        f".st-key-{key} button:active{{transform:translateY(5px);box-shadow:0 2px 0 rgba(0,0,0,.30) !important}}"
        f".st-key-{key} button p{{color:#fff !important;font-size:1.05rem !important;line-height:1.25 !important;"
        f"margin:0 !important;text-shadow:0 2px 6px rgba(0,0,0,.25)}}"
        f".st-key-{key} button p:first-child{{font-size:2.6rem !important;line-height:1.15 !important}}"
        f".st-key-{key} button p:nth-child(3){{font-size:.78rem !important;font-weight:600 !important;opacity:.92}}"
    )


def md_safe(text):
    text = str(text)
    for ch in ("\\", "*", "_", "`", "~", "$"):
        text = text.replace(ch, "\\" + ch)
    return re.sub(r"^(\s*\d+)([.)])", r"\1\\\2", text)


def card_grid(items, cols_n, prefix, on_pick, height):
    """items: (değer, ikon, ad, gradyan[, açıklama]). Karta tıklamak doğrudan seçer."""
    css = "".join(card_css(f"{prefix}_{i}", it[3], height) for i, it in enumerate(items))
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    for r in range(0, len(items), cols_n):
        cols = st.columns(cols_n)
        for j, it in enumerate(items[r:r + cols_n]):
            i = r + j
            label = f"{it[1]}\n\n**{md_safe(it[2])}**"
            if len(it) > 4 and it[4]:
                label += f"\n\n{md_safe(it[4])}"
            with cols[j]:
                st.button(label, key=f"{prefix}_{i}", on_click=on_pick, args=(it[0],))


# =============================================================================
# PROFİL, ROZET, KARNE
# =============================================================================


def stat_strip():
    p = P()
    lvl, into, need = store.level_info(p["xp"])
    goal = 3
    done = min(goal, store.games_today(p))
    streak = store.current_streak(p)
    acc = round(100 * p["correct"] / p["total"]) if p["total"] else 0
    st.markdown(
        '<div class="stats">'
        f'<div class="stat"><div class="k">👤 {esc(SS["player"])}</div><div class="v">Seviye {lvl}</div>'
        f'<div class="track"><div class="fill" style="width:{round(100 * into / need)}%"></div></div>'
        f'<div class="k" style="margin-top:4px">{p["xp"]} XP · sonraki seviyeye {need - into}</div></div>'
        f'<div class="stat"><div class="k">🔥 Günlük seri</div><div class="v">{streak} gün</div>'
        f'<div class="k">En iyi: {p["best_streak"]} gün</div></div>'
        f'<div class="stat"><div class="k">📅 Bugünkü hedef</div><div class="v">{done} / {goal} oyun</div>'
        f'<div class="track"><div class="fill" style="width:{round(100 * done / goal)}%"></div></div></div>'
        f'<div class="stat"><div class="k">🎯 Doğruluk</div><div class="v">%{acc}</div>'
        f'<div class="k">🏅 {len(p["badges"])} / {len(store.BADGES)} rozet</div></div>'
        "</div>",
        unsafe_allow_html=True,
    )


def _plan():
    p = P()
    weak = weak_units(p)
    if not weak:
        SS["plan"] = "Şu an zayıf bir ünite görünmüyor. Harika gidiyorsun! Yeni ünitelerle kendini denemeye devam et. 🌟"
        return
    lines = "\n".join(f"- {s} / {u}: %{pct} doğruluk" for s, u, pct in weak[:5])
    prompt = (
        "Sen AdenMind adlı sevimli bir 5. sınıf koçusun. Öğrencinin zayıf kaldığı üniteler:\n" + lines +
        "\nBu öğrenci için 3 günlük, her gün 15-20 dakikalık kısa ve motive edici bir tekrar planı yaz. "
        "Her güne bir ünite ve yapılacak 2 küçük etkinlik koy. Kısa maddeler kullan."
    )
    SS["plan"] = ai.generate(prompt, 0.7) or "Plan oluşturulamadı, biraz sonra tekrar dene."


def weak_units(p):
    out = []
    for key, v in p["stats"].items():
        if v["t"] >= 3 and v["c"] / v["t"] < 0.6:
            s, u = key.split("|", 1)
            out.append((s, u, round(100 * v["c"] / v["t"])))
    return sorted(out, key=lambda x: x[2])


def render_karne():
    p = P()
    st.button("⬅️ Ana Sayfa", key="back_karne", on_click=go_home)
    st.markdown(f'<div class="section-title">📊 {esc(SS["player"])} · Karnem</div>', unsafe_allow_html=True)
    stat_strip()

    st.markdown('<div class="section-title">🏅 Rozetlerim</div>', unsafe_allow_html=True)
    html = '<div class="badges">'
    for bid, (icon, title, desc, _fn) in store.BADGES.items():
        on = bid in p["badges"]
        html += (f'<div class="bdg {"on" if on else "off"}"><div class="i">{icon if on else "🔒"}</div>'
                 f'<div class="t">{esc(title)}</div><div class="d">{esc(desc)}</div></div>')
    st.markdown(html + "</div>", unsafe_allow_html=True)

    agg = {}
    for key, v in p["stats"].items():
        s = key.split("|", 1)[0]
        a = agg.setdefault(s, [0, 0])
        a[0] += v["c"]
        a[1] += v["t"]
    st.markdown('<div class="section-title">📈 Derslere Göre Başarım</div>', unsafe_allow_html=True)
    if not agg:
        st.info("Henüz puanlı bir oyun oynamadın. Bir oyun oyna, karnen burada dolsun! 🎮")
    else:
        bars = ""
        for s, (c, t) in sorted(agg.items(), key=lambda x: -x[1][1]):
            pct = round(100 * c / t) if t else 0
            bars += (f'<div class="bar"><span>{esc(s)}</span><div class="track"><div class="fill'
                     f'{" warn" if pct < 60 else ""}" style="width:{pct}%"></div></div><b>%{pct}</b></div>')
        st.markdown(bars, unsafe_allow_html=True)

    st.markdown('<div class="section-title">🎯 Tekrar Etmen Gereken Üniteler</div>', unsafe_allow_html=True)
    weak = weak_units(p)
    if not weak:
        st.success("Zayıf kaldığın bir ünite yok. Böyle devam! 🌟")
    for i, (s, u, pct) in enumerate(weak[:6]):
        st.button(f"🎯 {s} · {u} — %{pct} · Hemen çalış", key=f"weak_{i}", on_click=go_unit, args=(s, u))
    st.button("🦊 AdenMind'den Tekrar Planı İste", key="plan_btn", on_click=_plan)
    if SS.get("plan"):
        with st.container(border=True):
            st.markdown(SS["plan"])


# =============================================================================
# ADENMIND CANLI ASİSTAN
# =============================================================================
QUICK = [
    ("📝 Üniteyi özetle", "Bu üniteyi 5 kısa maddede özetle."),
    ("💡 İpucu ver", "Bu ünitede çalışırken bana işe yarayan bir ipucu ver."),
    ("🎯 Beni test et", "Bana bu üniteden tek bir soru sor, cevabı hemen söyleme."),
    ("🌟 Motive et", "Bana kısa ve içten bir motivasyon sözü söyle."),
]


def _am_queue(text):
    SS["am_pending"] = text


def am_reply(text):
    msgs = SS["coach_messages"]
    msgs.append({"role": "user", "content": text})
    hist = "\n".join(
        f"{'Öğrenci' if m['role'] == 'user' else 'AdenMind'}: {m['content']}" for m in msgs[-9:-1]
    )
    prompt = (
        "Sen AdenMind'sin: 5. sınıf MEB müfredatında öğrencilere yardım eden sevimli, cesaretlendirici bir yapay zekâ koçusun. "
        "Türkçe, sade ve en fazla 5 cümleyle konuş. Öğrenci açıkça istemedikçe cevabı hemen verme; önce ipucu ver.\n"
        f"Öğrencinin dersi: {SS.get('selected_subject') or 'Genel'}, ünitesi: {SS.get('selected_unit') or 'Genel konu'}.\n"
        f"Önceki konuşma:\n{hist}\nÖğrenci: {text}\nAdenMind:"
    )
    msgs.append({"role": "assistant", "content": ai.generate(prompt, 0.7) or "Şu an yanıt veremedim, biraz sonra tekrar dene!"})


def chat_bubble(role, text):
    text = esc(text).replace("\n", "<br>")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    if role == "assistant":
        return f'<div class="msg ai">{adenmind_avatar(30)}<div class="bub">{text}</div></div>'
    return f'<div class="msg me"><div class="bub">{text}</div></div>'


def speak_html(text):
    clean = re.sub(r"[*_`#]", "", text)
    payload = json.dumps(clean, ensure_ascii=False).replace("</", "<\\/")
    return (
        '<body style="margin:0;background:transparent"><button id="b" style="width:100%;height:40px;border:0;'
        'border-radius:14px;font-weight:800;cursor:pointer;font-family:system-ui;color:#042f2e;'
        'background:linear-gradient(135deg,#5eead4,#22d3ee)">🔊 Sesli Dinle</button><script>'
        f'const T={payload};const b=document.getElementById("b");'
        'b.onclick=function(){try{const s=window.speechSynthesis;if(s.speaking){s.cancel();b.textContent="🔊 Sesli Dinle";return}'
        'const u=new SpeechSynthesisUtterance(T);u.lang="tr-TR";u.rate=0.95;u.onend=function(){b.textContent="🔊 Sesli Dinle"};'
        's.cancel();s.speak(u);b.textContent="⏹️ Durdur"}catch(e){b.textContent="Tarayıcın sesi desteklemiyor"}};'
        "</script></body>"
    )


def render_adenmind(ns):
    st.markdown(
        f'<div class="am-card"><div class="am-wrap">{adenmind_avatar(64)}<span class="am-dot"></span></div>'
        '<div><div class="am-name">AdenMind</div><div class="am-sub">Canlı Asistan · çevrimiçi</div></div></div>',
        unsafe_allow_html=True,
    )
    qc = st.columns(2)
    for i, (label, text) in enumerate(QUICK):
        with qc[i % 2]:
            st.button(label, key=f"qk_{ns}_{i}", on_click=_am_queue, args=(text,))
    box = st.container(height=280)
    pend = SS.pop("am_pending", None)
    if pend:
        with st.spinner("AdenMind düşünüyor..."):
            am_reply(pend)
    with st.form(f"chat_form_{ns}", clear_on_submit=True):
        user_msg = st.text_input("Mesaj", label_visibility="collapsed", key=f"chat_in_{ns}",
                                 placeholder="AdenMind'e bir şey sor...")
        sent = st.form_submit_button("Gönder 🚀")
    if sent and user_msg.strip():
        with st.spinner("AdenMind düşünüyor..."):
            am_reply(user_msg.strip())
    msgs = SS["coach_messages"]
    with box:
        st.markdown("".join(chat_bubble(m["role"], m["content"]) for m in msgs), unsafe_allow_html=True)
    last = next((m["content"] for m in reversed(msgs) if m["role"] == "assistant"), "")
    components.html(speak_html(last), height=46)


def render_sidebar():
    with st.sidebar:
        st.button("🏠 Ana Sayfa", key="home_btn", on_click=go_home)
        st.button("📊 Karnem ve Rozetlerim", key="karne_btn", on_click=go_karne)
        st.text_input("👤 Takma adın", value=SS["player"], key="player_input", on_change=set_player, max_chars=20)
        st.toggle("🔊 Ses efektleri", value=SS["sound_on"], key="sound_toggle", on_change=set_sound)
        st.markdown("---")
        render_adenmind("side")
        with st.expander("🔑 Yapay zekâ bağlantısı"):
            s = ai.status()
            st.caption(
                f"Groq anahtarı: **{s['groq_keys']}** · Gemini anahtarı: **{s['gemini_keys']}**\n\n"
                "Sıra: önce tüm Groq anahtarları, sonra Gemini anahtarları denenir."
            )
            if s["last"]:
                st.caption(f"Son yanıt: {s['last']}")
            if s["error"]:
                st.caption(f"Son hata: {s['error']}")
            st.text_input("Groq anahtarı ekle", type="password", key="manual_groq", on_change=_save_keys)
            st.text_input("Gemini anahtarı ekle", type="password", key="manual_gemini", on_change=_save_keys)
            st.caption("Kalıcı kullanım için anahtarları `.streamlit/secrets.toml` içine yaz.")


# =============================================================================
# İÇERİK ÜRETİMİ (tekrarsız)
# =============================================================================
TR_LANG_SUBJECTS = ("İngilizce", "Almanca")


def get_items(gs, game, msg):
    """Oyun için içerik üretir: farklı alt konular, daha önce sorulanlar tekrarlanmaz."""
    if gs["data"] is not None:
        return gs["data"]
    kind, n, task = content.TASKS[game]
    if not gs["failed"]:
        spec = content.KINDS[kind]
        subject, unit = SS["selected_subject"], SS["selected_unit"]
        scope = f"{subject}|{unit}"
        seen_all = store.seen_stems(SS["player"], scope, 40)
        visual = subject in ("Fen Bilimleri", "Matematik")
        collected, stems = [], []
        with st.spinner(msg):
            for _ in range(2):
                need = n - len(collected)
                if need <= 0:
                    break
                prompt = content.build_prompt(subject, unit, kind, need, task, (seen_all + stems)[-30:], visual)
                data = ai.parse_json(ai.generate(prompt, 0.95))
                for raw in content.unwrap(data, spec["single"]):
                    it = spec["norm"](raw)
                    if not it:
                        continue
                    if not visual and "gorsel_tipi" in it:
                        it["gorsel_tipi"], it["gorsel_parametre"] = "yok", ""
                    stem = spec["stem"](it)
                    if content.is_dup(stem, seen_all + stems):
                        continue
                    collected.append(it)
                    stems.append(stem)
        minimum = 1 if spec["single"] else max(3, n // 2)
        if len(collected) >= minimum:
            items = collected[:n]
            store.mark_seen(SS["player"], scope, stems[:n])
            store.bank_add(f"{scope}|{kind}", items)
            gs.update(data=items, idx=0, correct=0, feedback=None)
            st.rerun()
        banked = store.bank_get(f"{scope}|{kind}")  # internet/anahtar yoksa: daha önce üretilenlerden
        if len(banked) >= minimum:
            gs.update(data=random.sample(banked, min(n, len(banked))), idx=0, correct=0, feedback=None, offline=True)
            st.rerun()
        gs["failed"] = True
    st.error("İçerik üretilemedi. `.streamlit/secrets.toml` içindeki Groq/Gemini anahtarlarını kontrol edip tekrar dene.")
    if SS.get("last_ai_error"):
        st.caption(f"Ayrıntı: {SS['last_ai_error']}")
    st.button("🔄 Tekrar Dene", key="retry", on_click=lambda: gs.update(failed=False))
    return None


def get_text(gs, prompt, msg):
    if gs["data"] is not None:
        return gs["data"]
    if not gs["failed"]:
        with st.spinner(msg):
            raw = ai.generate(prompt, 0.9)
        if raw and raw.strip():
            gs["data"] = raw.strip()
            st.rerun()
        gs["failed"] = True
    st.error("İçerik üretilemedi. Anahtarlarını kontrol edip tekrar dene.")
    st.button("🔄 Tekrar Dene", key="retry_t", on_click=lambda: gs.update(failed=False))
    return None


def get_dict(gs, prompt, required, msg):
    if gs["data"] is not None:
        return gs["data"]
    if not gs["failed"]:
        with st.spinner(msg):
            data = ai.parse_json(ai.generate(prompt, 0.9))
        if isinstance(data, dict) and all(k in data for k in required):
            gs["data"] = data
            st.rerun()
        gs["failed"] = True
    st.error("İçerik üretilemedi. Anahtarlarını kontrol edip tekrar dene.")
    st.button("🔄 Tekrar Dene", key="retry_d", on_click=lambda: gs.update(failed=False))
    return None


def ctx():
    lang = content.LANG_NOTE.get(SS["selected_subject"], "")
    return (f"Rastgelelik kimliği: {random.randint(10000, 999999)}\n"
            f"5. sınıf MEB müfredatı, Ders: {SS['selected_subject']}, Ünite: {SS['selected_unit']}.\n{lang}\n")


# =============================================================================
# SONUÇ KAYDI
# =============================================================================


def _record(game, correct, total, score):
    res = store.record_result(SS["player"], SS["selected_subject"], SS["selected_unit"], game, correct, total, score)
    for b in res["badges"]:
        SS["toasts"].append(f"🏅 Yeni rozet: {b}")
    if res["level_up"]:
        SS["toasts"].append("⬆️ Seviye atladın! Harikasın!")
    return res


def finish_game(gs, game, correct, total, score=None):
    if gs.get("recorded"):
        return
    if score is None:
        score = round(correct * 100 / total) if total else 0
    gs["xp_gain"] = _record(game, correct, total, score)["xp"]
    gs["recorded"] = True
    gs["sound"] = "win"
    flush_toasts()


def _report(game, score, total):
    """HTML oyunlarından gelen sonuç (gizli düğme tıklaması)."""
    _record(game, round(score * total / 100), total, score)


def result_card(gs, score, sub, title="Oyun Tamamlandı!"):
    stars = "⭐" * max(1, round(score / 20)) if score > 0 else "💪"
    st.markdown(
        f'<div class="result"><div class="trophy">🏆</div><h2>{esc(title)}</h2>'
        f'<div class="big">{score}<small> / 100</small></div><div style="font-size:2rem">{stars}</div>'
        f'<div>{esc(sub)}</div><div class="xp">+{gs.get("xp_gain", 0)} XP</div></div>',
        unsafe_allow_html=True,
    )


# =============================================================================
# TEK SORULUK YARIŞ MOTORU (Kazanım, Doğru/Yanlış, Boşluk Doldurma)
# =============================================================================


def _same(a, b):
    return str(a).strip().lower() == str(b).strip().lower()


def _answer(gs, value, q):
    ok = _same(value, q["correct"])
    if ok:
        gs["correct"] += 1
    label = next((lab for lab, val in q["options"] if _same(val, q["correct"])), q["correct"])
    gs["feedback"] = {"ok": ok, "label": label, "expl": q["expl"]}
    gs["sound"] = "ok" if ok else "bad"


def _next(gs):
    gs["idx"] += 1
    gs["feedback"] = None


def run_quiz(gs, game, items, build):
    total = len(items)
    idx = gs["idx"]
    if idx >= total:
        score = round(gs["correct"] * 100 / total)
        finish_game(gs, game, gs["correct"], total, score)
        result_card(gs, score, f"{gs['correct']} / {total} doğru")
        st.button("🔄 Yeni Sorularla Tekrar Oyna", key="again", on_click=regen)
        return

    q = build(items[idx])
    st.progress(idx / total)
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>Soru {idx + 1} / {total}</span>'
        f'<span class="score-chip">✔ {gs["correct"]} doğru</span></div>'
        f'<div class="qtext">{esc(str(q["text"]))}</div></div>',
        unsafe_allow_html=True,
    )
    vt, vp = q["visual"]
    if vt and vt != "yok":
        render_question_visual(vt, vp)

    fb = gs["feedback"]
    if fb:
        head, cls = ("🎉 Harika, doğru cevap!", "ok") if fb["ok"] else (
            f"❌ Olmadı! Doğru cevap: {esc(str(fb['label']))}", "bad")
        st.markdown(f'<div class="fb {cls}"><b>{head}</b><div>{esc(str(fb["expl"]))}</div></div>', unsafe_allow_html=True)
        st.button("➡️ Sonraki Soru" if idx < total - 1 else "🏆 Sonucu Gör",
                  key=f"next_{idx}", on_click=_next, args=(gs,))
    else:
        with st.container(key="optbox"):
            ocols = st.columns(2)
            for i, (label, value) in enumerate(q["options"]):
                with ocols[i % 2]:
                    st.button(md_safe(label), key=f"opt_{idx}_{i}", on_click=_answer, args=(gs, value, q))
        st.button("⏭️ Pas Geç", key=f"pass_{idx}", on_click=_next, args=(gs,))


def build_mcq(q):
    return {"text": q["soru"], "options": [(o, o[0]) for o in q["secenekler"]], "correct": q["dogru_cevap"],
            "expl": q.get("aciklama", ""), "visual": (q.get("gorsel_tipi"), q.get("gorsel_parametre", ""))}


def build_tf(q):
    return {"text": q["ifade"], "options": [("✅ DOĞRU", "D"), ("❌ YANLIŞ", "Y")], "correct": q["cevap"],
            "expl": q.get("aciklama", ""), "visual": (q.get("gorsel_tipi"), q.get("gorsel_parametre", ""))}


def build_fill(q):
    return {"text": q["cumle"], "options": [(o, o) for o in q["secenekler"]], "correct": q["dogru_kelime"],
            "expl": f"Doğru kelime: {q['dogru_kelime']}",
            "visual": (q.get("gorsel_tipi"), q.get("gorsel_parametre", ""))}


# =============================================================================
# ÖZEL OYUNLAR
# =============================================================================
def game_matching(gs, game):
    d = gs["data"][0]
    pairs = d["ciftler"]
    n = len(pairs)
    if "rorder" not in gs:
        gs.update(rorder=random.sample(range(n), n), sel=None, done=[], mist=0)

    def _ml(i):
        gs["sel"], gs["msg"] = i, None

    def _mr(j):
        if gs["sel"] is None:
            gs["msg"] = ("bad", "Önce soldan bir terim seç 👈")
        elif gs["sel"] == j:
            gs["done"].append(j)
            gs["sel"], gs["msg"], gs["sound"] = None, ("ok", "🎉 Doğru eşleşme!"), "ok"
        else:
            gs["mist"] += 1
            gs["sel"], gs["msg"], gs["sound"] = None, ("bad", "❌ Bu eşleşme değil, tekrar dene."), "bad"

    if len(gs["done"]) >= n:
        score = max(20, 100 - 10 * gs["mist"])
        finish_game(gs, game, max(0, n - gs["mist"]), n, score)
        result_card(gs, score, f"{gs['mist']} yanlış deneme")
        st.button("🔄 Yeni Eşleştirme", key="again", on_click=regen)
        return
    st.progress(len(gs["done"]) / n)
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>🔗 {len(gs["done"])} / {n} eşleşti</span>'
        f'<span class="score-chip">❌ {gs["mist"]} hata</span></div>'
        f'<div class="qtext">{esc(d["baslik"] or "Terimleri karşılıklarıyla eşleştir")}</div>'
        '<div class="k" style="margin-top:6px;color:#99f6e4">Önce soldan terimi, sonra sağdan karşılığını seç.</div></div>',
        unsafe_allow_html=True,
    )
    if gs["msg"]:
        (st.success if gs["msg"][0] == "ok" else st.error)(gs["msg"][1])
    cl, cr = st.columns(2)
    with cl, st.container(key="matchL"):
        for i, (left, _r) in enumerate(pairs):
            if i in gs["done"]:
                st.button(f"✅ {md_safe(left)}", key=f"ml_{i}", disabled=True)
            else:
                st.button(("👉 " if gs["sel"] == i else "") + md_safe(left), key=f"ml_{i}", on_click=_ml, args=(i,))
    with cr, st.container(key="matchR"):
        for j in gs["rorder"]:
            if j in gs["done"]:
                st.button(f"✅ {md_safe(pairs[j][1])}", key=f"mr_{j}", disabled=True)
            else:
                st.button(md_safe(pairs[j][1]), key=f"mr_{j}", on_click=_mr, args=(j,))


def game_ordering(gs, game):
    d = gs["data"][0]
    steps = d["adimlar"]
    n = len(steps)
    if "opool" not in gs:
        gs.update(opool=random.sample(range(n), n), pick=[], mist=0)
        if gs["opool"] == list(range(n)):
            gs["opool"].reverse()

    def _pick(k):
        if k == len(gs["pick"]):
            gs["pick"].append(k)
            gs["msg"], gs["sound"] = ("ok", "✅ Doğru sıra!"), "ok"
        else:
            gs["mist"] += 1
            gs["msg"], gs["sound"] = ("bad", "❌ Bu adım şimdi gelmez, başka bir adım dene."), "bad"

    def _reset():
        gs["pick"], gs["msg"] = [], None

    if len(gs["pick"]) >= n:
        score = max(20, 100 - 15 * gs["mist"])
        finish_game(gs, game, max(0, n - gs["mist"]), n, score)
        result_card(gs, score, f"{gs['mist']} yanlış deneme")
        st.markdown("".join(f'<div class="ochip"><b>{i + 1}</b>{esc(s)}</div>' for i, s in enumerate(steps)),
                    unsafe_allow_html=True)
        st.button("🔄 Yeni Sıralama", key="again", on_click=regen)
        return
    st.progress(len(gs["pick"]) / n)
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>🧩 {len(gs["pick"])} / {n}</span>'
        f'<span class="score-chip">❌ {gs["mist"]} hata</span></div>'
        f'<div class="qtext">{esc(d["gorev"])}</div></div>',
        unsafe_allow_html=True,
    )
    if gs["pick"]:
        st.markdown("".join(f'<div class="ochip"><b>{i + 1}</b>{esc(steps[k])}</div>' for i, k in enumerate(gs["pick"])),
                    unsafe_allow_html=True)
    if gs["msg"]:
        (st.success if gs["msg"][0] == "ok" else st.error)(gs["msg"][1])
    st.markdown(f"**{len(gs['pick']) + 1}. adım hangisi?**")
    with st.container(key="orderpool"):
        for k in gs["opool"]:
            if k not in gs["pick"]:
                st.button(md_safe(steps[k]), key=f"op_{k}", on_click=_pick, args=(k,))
    st.button("↺ Baştan Başla", key="o_reset", on_click=_reset)


def game_memory(gs, game):
    d = gs["data"][0]
    pairs = d["ciftler"]
    n = len(pairs)
    if "cards" not in gs:
        cards = [(i, p[0]) for i, p in enumerate(pairs)] + [(i, p[1]) for i, p in enumerate(pairs)]
        random.shuffle(cards)
        gs.update(cards=cards, flipped=[], matched=[], moves=0)

    def _flip(i):
        if len(gs["flipped"]) >= 2:
            gs["flipped"] = []
        if i in gs["flipped"] or i in gs["matched"]:
            return
        gs["flipped"].append(i)
        if len(gs["flipped"]) == 2:
            gs["moves"] += 1
            a, b = gs["flipped"]
            if gs["cards"][a][0] == gs["cards"][b][0]:
                gs["matched"] += [a, b]
                gs["flipped"] = []
                gs["msg"], gs["sound"] = ("ok", "🎉 Çifti buldun!"), "ok"
            else:
                gs["msg"], gs["sound"] = ("bad", "Eşleşmedi, bir sonraki kartta ikisi de kapanır."), "bad"

    if len(gs["matched"]) >= 2 * n:
        score = max(30, min(100, 100 - (gs["moves"] - n) * 8))
        finish_game(gs, game, round(score * n / 100), n, score)
        result_card(gs, score, f"{gs['moves']} hamlede bitirdin")
        st.button("🔄 Yeni Kartlar", key="again", on_click=regen)
        return
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>🃏 {len(gs["matched"]) // 2} / {n} çift</span>'
        f'<span class="score-chip">🎯 {gs["moves"]} hamle</span></div>'
        f'<div class="qtext">{esc(d["baslik"] or "Terim ile karşılığını bul")}</div></div>',
        unsafe_allow_html=True,
    )
    if gs["msg"]:
        (st.success if gs["msg"][0] == "ok" else st.warning)(gs["msg"][1])
    with st.container(key="mem"):
        for r in range(0, len(gs["cards"]), 4):
            cols = st.columns(4)
            for j, (pid, text) in enumerate(gs["cards"][r:r + 4]):
                i = r + j
                shown = i in gs["flipped"] or i in gs["matched"]
                with cols[j]:
                    st.button(("✅ " if i in gs["matched"] else "") + md_safe(text) if shown else "❓",
                              key=f"mem_{i}", disabled=i in gs["matched"], on_click=_flip, args=(i,))


def game_flashcards(gs, game):
    data = gs["data"]
    idx = gs["idx"]

    def _move(d):
        gs["idx"] = max(0, gs["idx"] + d)
        gs["show"] = False

    def _toggle():
        gs["show"] = not gs["show"]

    if idx >= len(data):
        finish_game(gs, game, 0, 0)
        st.markdown(f'<div class="result"><div class="trophy">🎉</div><h2>Tüm kartları gözden geçirdin!</h2>'
                    f'<div class="xp">+{gs.get("xp_gain", 0)} XP</div></div>', unsafe_allow_html=True)
        st.button("🔄 Başa Dön", key="again", on_click=lambda: gs.update(idx=0, show=False))
        return
    card = data[idx]
    st.progress(idx / len(data))
    st.markdown(f'<div class="flash" style="background:linear-gradient(135deg,#0d9488,#06b6d4)">'
                f'<div class="tag">Kart {idx + 1} / {len(data)}</div><div class="txt">❓ {esc(card["on_yuz"])}</div></div>',
                unsafe_allow_html=True)
    if gs["show"]:
        st.markdown(f'<div class="flash" style="background:linear-gradient(135deg,#7c3aed,#d946ef)">'
                    f'<div class="tag">Cevap / Açıklama</div><div class="txt">💡 {esc(card["arka_yuz"])}</div></div>',
                    unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("⬅️ Önceki", key="fc_prev", disabled=idx == 0, on_click=_move, args=(-1,))
    with c2:
        st.button("🙈 Cevabı Gizle" if gs["show"] else "👀 Cevabı Göster", key="fc_toggle", on_click=_toggle)
    with c3:
        st.button("Sonraki ➡️", key="fc_next", on_click=_move, args=(1,))


def game_words(gs, game):
    data = gs["data"]
    idx = gs["idx"]
    lang_plain = SS["selected_subject"] in TR_LANG_SUBJECTS
    up = (lambda s: s.upper()) if lang_plain else content.tr_upper
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if lang_plain else "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"
    if idx >= len(data):
        score = round(gs["correct"] * 100 / len(data))
        finish_game(gs, game, gs["correct"], len(data), score)
        result_card(gs, score, f"{gs['correct']} / {len(data)} kelime", "Tüm bulmacaları tamamladın!")
        st.button("🔄 Yeni Bulmaca", key="again", on_click=regen)
        return
    item = data[idx]
    word = up(item["kelime"])
    if gs["pool_for"] != idx:
        pool = list(word)
        extras = [c for c in alphabet if c not in pool]
        pool += random.sample(extras, min(3, len(extras)))
        random.shuffle(pool)
        gs.update(pool=pool, pool_for=idx, guess=[], used=[], msg=None)

    def _add(i, ch):
        if len(gs["guess"]) < len(word):
            gs["guess"].append(ch)
            gs["used"].append(i)
            gs["msg"] = None

    def _undo():
        if gs["guess"]:
            gs["guess"].pop()
            gs["used"].pop()

    def _clear():
        gs["guess"], gs["used"] = [], []

    def _skip():
        gs["idx"] += 1
        gs["msg"] = None

    def _check():
        if "".join(gs["guess"]) == word:
            gs["correct"] += 1
            gs["idx"] += 1
            gs["msg"], gs["sound"] = None, "ok"
        else:
            gs["msg"], gs["sound"] = ("bad", "❌ Eksik veya yanlış harf! Son harfi silip düzeltebilirsin."), "bad"

    st.progress(idx / len(data))
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>Bulmaca {idx + 1} / {len(data)} · {len(word)} harf</span>'
        f'<span class="score-chip">✔ {gs["correct"]} doğru</span></div>'
        f'<div class="qtext">💡 {esc(item["ipucu"])}</div></div>',
        unsafe_allow_html=True,
    )
    tiles = "".join(
        f'<div class="tile {"on" if i < len(gs["guess"]) else ""}">{esc(gs["guess"][i]) if i < len(gs["guess"]) else ""}</div>'
        for i in range(len(word)))
    st.markdown(f'<div class="tiles">{tiles}</div>', unsafe_allow_html=True)
    if gs["msg"]:
        st.error(gs["msg"][1])
    with st.container(key="letters"):
        for r in range(0, len(gs["pool"]), 8):
            cols = st.columns(8)
            for j, ch in enumerate(gs["pool"][r:r + 8]):
                i = r + j
                with cols[j]:
                    st.button("✔" if i in gs["used"] else ch, key=f"ch_{idx}_{i}", disabled=i in gs["used"],
                              on_click=_add, args=(i, ch))
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.button("🔄 Sıfırla", key="k_clear", on_click=_clear)
    with c2:
        st.button("↩️ Son Harfi Sil", key="k_undo", on_click=_undo)
    with c3:
        st.button("⏭️ Pas Geç", key="pass_k", on_click=_skip)
    with c4:
        st.button("✅ Kontrol Et", key="k_check", on_click=_check)


def game_scenario(gs, game):
    prompt = (ctx() + "Gerçek hayattan esinlenen, daha önce işlenmemiş özgün bir karar verme senaryosu ve çoktan seçmeli mini görev üret. "
              'Yalnızca geçerli JSON döndür: {"senaryo":"...","gorev_sorusu":"...",'
              '"secenekler":["A) ...","B) ...","C) ...","D) ..."],"ipucu":"..."}')
    iq = get_dict(gs, prompt, ("senaryo", "gorev_sorusu", "secenekler"), "Macera hazırlanıyor...")
    if not iq:
        return
    st.markdown(
        f'<div class="qcard"><div class="qmeta"><span>📖 Görev Senaryosu</span></div>'
        f'<div style="font-size:1.1rem;line-height:1.6">{esc(str(iq["senaryo"]))}</div>'
        f'<hr style="border-color:rgba(94,234,212,.3);margin:16px 0"><div class="qmeta"><span>🎯 Karar Noktası</span></div>'
        f'<div class="qtext">{esc(str(iq["gorev_sorusu"]))}</div></div>',
        unsafe_allow_html=True,
    )

    def _choose(opt):
        gs["choice"], gs["eval"] = opt, None

    def _hint():
        gs["show"] = not gs["show"]

    if gs["choice"] is None:
        with st.container(key="optbox"):
            cols = st.columns(2)
            for i, o in enumerate(iq["secenekler"]):
                with cols[i % 2]:
                    st.button(md_safe(o), key=f"iq_{i}", on_click=_choose, args=(o,))
    else:
        st.markdown(f'<div class="pill">Seçimin: {esc(str(gs["choice"]))}</div>', unsafe_allow_html=True)
        if gs["eval"] is None:
            with st.spinner("AdenMind değerlendiriyor..."):
                gs["eval"] = ai.generate(
                    f"Ders: {SS['selected_subject']}, Ünite: {SS['selected_unit']}.\nGörev Sorusu: {iq['gorev_sorusu']}\n"
                    f"Öğrencinin Seçtiği Şık: {gs['choice']}\n"
                    "Bu seçimin doğru olup olmadığını değerlendir, nedenini sevimli bir dille kısaca açıkla.", 0.5
                ) or "Değerlendirme yapılamadı, tekrar dene."
            finish_game(gs, game, 0, 0)
        st.info(gs["eval"])
        st.button("↩️ Başka Şık Dene", key="iq_retry", on_click=_choose, args=(None,))
    st.button("💡 AdenMind'den İpucu", key="iq_hint", on_click=_hint)
    if gs["show"]:
        st.info(f"🦊 **İpucu:** {iq.get('ipucu', '')}")


def game_activities(gs, game):
    prompt = (ctx() + "Evde veya sınıfta yapılabilecek, daha önce önerilmemiş 3 yaratıcı öğrenme etkinliği/deney öner. "
              "Her biri için gerekli malzemeleri ve adımları kısa maddelerle yaz. Markdown kullan.")
    text = get_text(gs, prompt, "Etkinlikler hazırlanıyor...")
    if text:
        with st.container(border=True):
            st.markdown(text)


def game_classic(gs, game):
    items = get_items(gs, game, "Yazılı soruları hazırlanıyor...")
    if not items:
        return
    with st.form("classic_form"):
        answers = []
        for i, cq in enumerate(items):
            st.markdown(
                f'<div class="qcard" style="padding:16px 22px"><div class="qmeta"><span>Soru {i + 1}</span></div>'
                f'<div class="qtext" style="font-size:1.15rem">{esc(str(cq["soru"]))}</div></div>',
                unsafe_allow_html=True)
            answers.append(st.text_area(f"Cevabın ({i + 1})", key=f"ans_{gs['nonce']}_{i}"))
        submitted = st.form_submit_button("📨 Yazılı Kâğıdını Puanlat")
    if submitted:
        gs["results"], total = [], 0
        with st.spinner("AdenMind kâğıdını okuyor..."):
            for i, cq in enumerate(items):
                pts = 0
                if answers[i].strip():
                    res = ai.generate(
                        f"Soru: {cq['soru']}\nİdeal cevap: {cq['beklenen_cevap']}\nÖğrenci: {answers[i]}\n"
                        "İlk satıra yalnızca 'PUAN: x/20' yaz (x 0-20 arası tam sayı). Sonra kısa, cesaretlendirici bir açıklama yaz.", 0.3)
                    m = re.search(r"PUAN\s*:\s*(\d+)", res or "")
                    pts = min(20, int(m.group(1))) if m else 0
                    gs["results"].append((i, res or "Değerlendirme yapılamadı."))
                total += pts
        score = round(total * 100 / (20 * len(items)))
        finish_game(gs, game, round(score * len(items) / 100), len(items), score)
        gs["final"] = score
    if gs["results"]:
        for i, res in gs["results"]:
            st.info(f"**Soru {i + 1} Değerlendirmesi**\n\n{res}")
        if gs.get("final") is not None:
            result_card(gs, gs["final"], "Yazılı sonucun", "Yazılı Tamamlandı!")


# =============================================================================
# OYUN ÜST BARI VE TAM EKRAN
# =============================================================================
FS_BUTTON = """<!DOCTYPE html><html><body style="margin:0;background:transparent">
<button id="fs" style="width:100%;height:46px;border:0;border-radius:18px;font-weight:800;font-size:15px;cursor:pointer;
font-family:'Segoe UI',system-ui,sans-serif;color:#042f2e;background:linear-gradient(135deg,#5eead4,#22d3ee);
box-shadow:0 5px 0 #0f766e">⛶ Tam Ekran</button>
<script>
document.getElementById('fs').onclick=function(){
  try{
    var d=window.parent.document, el=d.documentElement;
    if(!d.fullscreenElement&&!d.webkitFullscreenElement){(el.requestFullscreen||el.webkitRequestFullscreen).call(el);}
    else{(d.exitFullscreen||d.webkitExitFullscreen).call(d);}
  }catch(e){var e2=document.documentElement;(e2.requestFullscreen||e2.webkitRequestFullscreen).call(e2);}
};
</script></body></html>"""


def game_topbar(title):
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.3, 1.5, 3.3, 1.4])
    with c1:
        st.button("⬅️ Geri", key="back_game", on_click=back_to_games)
    with c2:
        components.html(FS_BUTTON, height=52)
    with c3:
        st.button("🔁 Yeni Sorular", key="regen_btn", on_click=regen)
    with c4:
        st.markdown(f'<div class="gamebar-title">{esc(title)}</div>', unsafe_allow_html=True)
    with c5:
        with st.popover("💬 AdenMind"):
            render_adenmind("pop")


# =============================================================================
# ANA AKIŞ
# =============================================================================
subj, unit, game = SS["selected_subject"], SS["selected_unit"], SS["selected_game"]
in_game = bool(SS["view"] == "play" and subj and unit and game)

css = BASE_CSS + EXTRA_CSS + (GAME_CSS if in_game else "") + (HTMLGAME_CSS if in_game and game in ("balon", "blitz") else "")
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
flush_toasts()

if not in_game:
    render_sidebar()
    st.markdown(
        '<div class="hero"><div class="badge">🎒</div><div><h1>MEB 5. Sınıf Akıllı Eğitsel Oyun Merkezi</h1>'
        "<small>AdenMind Koçluk · Murat KANDIRMAZ</small></div></div>",
        unsafe_allow_html=True,
    )

if SS["view"] == "karne":
    render_karne()

elif not subj:
    stat_strip()
    st.button("📊 Karnem ve Rozetlerim", key="karne_home", on_click=go_karne)
    st.markdown('<div class="section-title">🌟 Çalışmak istediğin dersi seç</div>', unsafe_allow_html=True)
    card_grid([(n, d["ikon"], n, d["renk"]) for n, d in MEB_CURRICULUM.items()], 3, "sub", pick_subject, 170)

elif not unit:
    data = MEB_CURRICULUM[subj]
    st.markdown(f'<div class="crumb"><span class="pill">{data["ikon"]} {esc(subj)}</span><span>›</span>'
                '<span class="pill alt">Ünite seç</span></div>', unsafe_allow_html=True)
    st.button("⬅️ Ders Seçimine Dön", key="back_subj", on_click=go_home)
    st.markdown('<div class="section-title">📚 Hangi üniteyi çalışalım?</div>', unsafe_allow_html=True)
    card_grid([(u, "📖", u, data["renk"]) for u in data["uniteler"]], 2, "unit", pick_unit, 120)

elif not game:
    data = MEB_CURRICULUM[subj]
    st.markdown(f'<div class="crumb"><span class="pill">{data["ikon"]} {esc(subj)}</span><span>›</span>'
                f'<span class="pill alt">{esc(unit)}</span></div>', unsafe_allow_html=True)
    st.button("↩️ Ünite Değiştir", key="back_unit", on_click=back_to_units)
    st.markdown('<div class="section-title">🎮 Bir oyun seç, hemen başlasın!</div>', unsafe_allow_html=True)
    card_grid([tuple(g) for g in GAMES], 3, "game", pick_game, 160)

else:
    gs = get_gs(game)
    game_topbar(f"{GAME_INFO[game][1]} {GAME_INFO[game][2]} · {subj} · {unit}")
    if gs.get("offline"):
        st.info("📴 Yapay zekâya ulaşılamadı; daha önce hazırlanan sorular gösteriliyor.")

    if game in ("balon", "blitz"):
        items = get_items(gs, game, "Sorular hazırlanıyor...")
        if items:
            with st.container(key="rep"):
                for s in range(0, 101, 10):
                    st.button(f"rep{s}", key=f"rep_{s}", on_click=_report, args=(game, s, len(items)))
            with st.container(key="htmlgame"):
                components.html(gh.build(game, items, SS["sound_on"]), height=760)

    elif game in ("sinav10", "dogruyanlis", "bosluk"):
        items = get_items(gs, game, "Sorular hazırlanıyor...")
        if items:
            run_quiz(gs, game, items, {"sinav10": build_mcq, "dogruyanlis": build_tf, "bosluk": build_fill}[game])

    elif game in ("eslestir", "hafiza", "siralama"):
        items = get_items(gs, game, "Oyun hazırlanıyor...")
        if items:
            {"eslestir": game_matching, "hafiza": game_memory, "siralama": game_ordering}[game](gs, game)

    elif game == "kartlar":
        if get_items(gs, game, "Kartlar hazırlanıyor..."):
            game_flashcards(gs, game)

    elif game == "kelime":
        if get_items(gs, game, "Bulmaca hazırlanıyor..."):
            game_words(gs, game)

    elif game == "oynayarak":
        game_scenario(gs, game)

    elif game == "etkinlik":
        game_activities(gs, game)

    elif game == "acik":
        game_classic(gs, game)

    flush_sound(gs)
    flush_toasts()
