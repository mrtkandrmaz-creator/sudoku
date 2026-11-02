"""Öğrenci profili, ilerleme takibi, Yanlış Defteri, günlük görevler ve seri.
Veriler profiller/<ad>.json dosyasında tutulur. app.py ile AYNI klasörde durmalıdır."""
import base64
import hashlib
import json
import os
import re
import zlib
from datetime import datetime, timedelta, timezone

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiller")
INTERVALS = [1, 3, 7, 14]      # Yanlış Defteri: kutu 0..3 sonrası tekrar aralığı (gün); 4. doğruda "öğrenildi"
MAX_WRONG = 200


def now():
    return datetime.now(timezone(timedelta(hours=3)))


def today():
    return now().strftime("%Y-%m-%d")


def slug(name):
    s = re.sub(r"[^0-9a-zA-ZçğıöşüÇĞİÖŞÜ _-]", "", (name or "").strip())[:24].strip()
    return s


def _path(name):
    return os.path.join(DIR, hashlib.sha1(slug(name).lower().encode("utf-8")).hexdigest()[:16] + ".json")


def new_profile(name):
    return {"name": slug(name), "created": today(), "xp": 0, "streak": 0, "best_streak": 0, "last_day": "",
            "days": {}, "stats": {}, "wrong": [], "mastered": 0, "claimed": {}, "badges": [], "games": 0}


def load(name):
    name = slug(name)
    if len(name) < 2:
        return None
    try:
        with open(_path(name), encoding="utf-8") as f:
            p = json.load(f)
        base = new_profile(name)
        base.update(p)
        return base
    except Exception:
        return new_profile(name)


def save(p):
    try:
        os.makedirs(DIR, exist_ok=True)
        with open(_path(p["name"]), "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False)
        return True
    except Exception:
        return False


def export_code(p):
    return base64.urlsafe_b64encode(zlib.compress(json.dumps(p, ensure_ascii=False).encode("utf-8"), 9)).decode("ascii")


def import_code(code):
    try:
        d = json.loads(zlib.decompress(base64.urlsafe_b64decode(code.strip().encode("ascii"))).decode("utf-8"))
        if not isinstance(d, dict) or "name" not in d:
            return None
        base = new_profile(d["name"])
        base.update(d)
        return base
    except Exception:
        return None


# ---------------- kayıt ----------------
def _day(p):
    return p["days"].setdefault(today(), {"correct": 0, "wrong": 0, "games": 0, "arcade": 0, "review": 0, "subjects": []})


def touch(p):
    """Bugün çalışıldığını işler ve seriyi günceller."""
    t = today()
    _day(p)
    if p["last_day"] != t:
        y = (now() - timedelta(days=1)).strftime("%Y-%m-%d")
        p["streak"] = p["streak"] + 1 if p["last_day"] == y else 1
        p["best_streak"] = max(p["best_streak"], p["streak"])
        p["last_day"] = t
    for k in sorted(p["days"])[:-60]:  # eski günleri sınırla
        del p["days"][k]


def qid(subject, text):
    return hashlib.sha1((subject + "|" + re.sub(r"\s+", " ", text.strip().lower())).encode("utf-8")).hexdigest()[:12]


def rec_answer(p, subject, unit, game, q, ok):
    """q: {'text','options':[(label,value)],'correct','expl'}"""
    touch(p)
    d = _day(p)
    st = p["stats"].setdefault(subject or "Genel", {}).setdefault(unit or "Genel", {"c": 0, "w": 0})
    if subject and subject not in d["subjects"]:
        d["subjects"].append(subject)
    if ok:
        d["correct"] += 1
        st["c"] += 1
        p["xp"] += 5
    else:
        d["wrong"] += 1
        st["w"] += 1
        text = str(q.get("text", ""))
        opts = [[str(a), str(b)] for a, b in (q.get("options") or [])]
        if text and len(opts) >= 2:
            i = qid(subject or "", text)
            it = next((x for x in p["wrong"] if x["id"] == i), None)
            if it:
                it["box"], it["due"] = 0, today()
            else:
                p["wrong"].append({"id": i, "subject": subject or "Genel", "unit": unit or "Genel", "text": text, "options": opts,
                                   "correct": str(q.get("correct", "")), "expl": str(q.get("expl", "")), "box": 0, "due": today(), "added": today()})
                del p["wrong"][:-MAX_WRONG]
    _after(p)


def rec_game(p, subject, unit, game, score):
    touch(p)
    d = _day(p)
    d["games"] += 1
    p["games"] += 1
    p["xp"] += 20 + (10 if score >= 80 else 0)
    _after(p)


def rec_arcade(p, key):
    touch(p)
    _day(p)["arcade"] += 1
    p["xp"] += 5
    _after(p)


def due_wrong(p, n=5):
    t = today()
    due = [x for x in p["wrong"] if x["due"] <= t]
    due.sort(key=lambda x: (x["box"], x["due"]))
    return due[:n]


def review(p, item_id, ok):
    touch(p)
    d = _day(p)
    d["review"] += 1
    it = next((x for x in p["wrong"] if x["id"] == item_id), None)
    if not it:
        return
    if ok:
        p["xp"] += 8
        if it["box"] >= len(INTERVALS) - 1:
            p["wrong"].remove(it)
            p["mastered"] += 1
            p["xp"] += 15
        else:
            it["due"] = (now() + timedelta(days=INTERVALS[it["box"]])).strftime("%Y-%m-%d")
            it["box"] += 1
    else:
        it["box"] = 0
        it["due"] = (now() + timedelta(days=1)).strftime("%Y-%m-%d")
    _after(p)


# ---------------- günlük görevler ----------------
TASK_POOL = [
    ("correct", "🎯 {n} soruyu doğru yanıtla", 8),
    ("games", "🎮 {n} oyunu tamamla", 2),
    ("arcade", "🕹️ Oyun salonunda {n} oyun aç", 1),
    ("review", "📓 Yanlış Defterinden {n} soruyu tekrarla", 3),
    ("subjects", "📚 {n} farklı derste çalış", 2),
]


def daily_tasks(p):
    seed = int(hashlib.sha1((p["name"] + today()).encode("utf-8")).hexdigest()[:8], 16)
    pool = TASK_POOL[:]
    if not p["wrong"]:
        pool = [t for t in pool if t[0] != "review"]
    order = sorted(range(len(pool)), key=lambda i: (seed >> i) * 2654435761 % 1000)
    d = p["days"].get(today(), {})
    out = []
    for i in order[:3]:
        k, label, n = pool[i]
        cur = len(d.get("subjects", [])) if k == "subjects" else d.get(k, 0)
        out.append({"key": k, "label": label.format(n=n), "target": n, "cur": min(cur, n), "done": cur >= n})
    return out


BADGES = [
    ("ilk", "🌱 İlk Adım", lambda p: p["games"] >= 1),
    ("seri3", "🔥 3 Gün Serisi", lambda p: p["best_streak"] >= 3),
    ("seri7", "⚡ 7 Gün Serisi", lambda p: p["best_streak"] >= 7),
    ("dogru50", "🎯 50 Doğru", lambda p: _total(p)[0] >= 50),
    ("dogru200", "🏹 200 Doğru", lambda p: _total(p)[0] >= 200),
    ("oyun10", "🎮 10 Oyun", lambda p: p["games"] >= 10),
    ("defter", "📓 Defter Ustası (5 soru öğrenildi)", lambda p: p["mastered"] >= 5),
    ("xp500", "⭐ 500 XP", lambda p: p["xp"] >= 500),
]


def _total(p):
    c = sum(u["c"] for s in p["stats"].values() for u in s.values())
    w = sum(u["w"] for s in p["stats"].values() for u in s.values())
    return c, w


def _after(p):
    t = today()
    cl = p["claimed"].setdefault(t, [])
    for k in list(p["claimed"]):
        if k != t:
            del p["claimed"][k]
    for task in daily_tasks(p):
        if task["done"] and task["key"] not in cl:
            cl.append(task["key"])
            p["xp"] += 15
    for bid, _, ok in BADGES:
        if bid not in p["badges"] and ok(p):
            p["badges"].append(bid)
    save(p)


def level(xp):
    lv, need, left = 1, 100, xp
    while left >= need:
        left -= need
        lv += 1
        need = 100 + (lv - 1) * 40
    return lv, left, need


def weak_topics(p, min_n=3, k=3):
    rows = []
    for s, us in p["stats"].items():
        for u, v in us.items():
            n = v["c"] + v["w"]
            if n >= min_n:
                rows.append((v["c"] / n, n, s, u))
    rows.sort()
    return [r for r in rows if r[0] < 0.8][:k]


def total(p):
    return _total(p)
