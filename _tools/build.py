import sys, re, os
sys.path.insert(0, os.path.dirname(__file__))
from works_data import PERFORMANCES, EXTRA, YS_REVIEWS

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 사이트 폴더 = _tools 의 한 단계 위

rows = []
for line in PERFORMANCES.strip().splitlines():
    slug, date, title, credit, venue, note = line.split("|")
    rows.append(dict(slug=slug, date=date, title=title, credit=credit, venue=venue, note=note))

# 작품 순서: 첫 공연 순
order, works = [], {}
for r in rows:
    if r["slug"] not in works:
        works[r["slug"]] = {"title": r["title"], "credit": r["credit"], "rows": []}
        order.append(r["slug"])
    works[r["slug"]]["rows"].append(r)


# ---- 사람별 참여 기록 색인 ----
NAME_RE = re.compile(r"^[가-힣]{2,4}$")
NOT_PERSON = {"보통현상", "그린피그", "온스테이지", "공동창작", "공동구성", "공동재구성", "공동연구"}
people = {}  # 사람 키 -> {작품번호: {역할: {연도…}}}

# 동명이인: (이름, 역할에 들어 있는 말) -> 구분된 키. 새로 생기면 여기에 한 줄 추가.
SAME_NAME = [("박정근", "사진", "박정근(사진)"),
             ("박현지", "출연", "박현지(배우)"), ("박현지", "배우", "박현지(배우)")]

def person_key(name, role):
    for n, word, key in SAME_NAME:
        if name == n and word in role:
            return key
    return name

def anchor(key):
    return key.replace("(", "-").replace(")", "")

def show(key):
    return key.replace("(", " (")


# 같은 역할을 다르게 적은 것 (참여 기록에서만 통일)
SAME_ROLE = {"배우": "출연", "연기": "출연", "그래픽 디자인": "그래픽디자인", "기록 촬영": "기록촬영", "조명 오퍼": "조명 오퍼레이터", "배우·공동창작": "출연·공동창작", "무대감독·기획": "기획·무대감독"}

def clean_role(role):
    """참여 기록에 쓸 역할 이름: 연도·공연명·배역 같은 괄호 속 설명과 앞의 연도를 뗀다."""
    role = re.sub(r"\([^)]*\)", "", role)
    role = re.sub(r"^20\d\d\s+", "", role)
    role = role.strip() or "참여"
    return SAME_ROLE.get(role, role)

def credit(name, slug, role, year):
    name = name.strip()
    if NAME_RE.match(name) and name not in NOT_PERSON:
        m = re.search(r"(?:^|\()(20\d\d)\b", role)      # '출연(2022)', '2026 출연' 같은 연도 표시
        if m:
            year = m.group(1)
        role = clean_role(role)
        key = person_key(name, role)
        people.setdefault(key, {}).setdefault(slug, {}).setdefault(role, set()).add(year)

def parse_credit_line(slug, text, year):
    """'윤영선 원작, 전성현 글쓰기, 윤한솔 연출' 같은 줄에서 이름과 역할을 뽑는다."""
    text = re.sub(r"〈[^〉]*〉\s*", "", text)
    for role, names in re.findall(r"(\S+)\(([^)]*)\)", text):   # 공동연구(김현, 박수빈, …)
        for n in names.split(","):
            credit(n, slug, role, year)
    text = re.sub(r"\S+\([^)]*\)", "", text)
    for piece in re.split(r",\s*| · ", text):
        words = piece.split()
        if len(words) >= 2:
            for n in " ".join(words[:-1]).split("·"):
                credit(n, slug, words[-1], year)

for r in rows:
    parse_credit_line(r["slug"], r["credit"], r["date"][:4])
first_year = {}
for r in rows:
    first_year.setdefault(r["slug"], r["date"][:4])
for slug, ex in EXTRA.items():
    cr = ex.get("크레딧", [])
    # 연도가 안 적힌 크레딧은 같은 자료의 '출연(연도)'를 따르고, 없으면 첫 공연 연도
    base = next((m.group(1) for role, _ in cr for m in [re.search(r"(20\d\d)", role)] if m and "출연" in role),
                first_year.get(slug, ""))
    for role, names in cr:
        for n in names.split(","):
            n = n.strip()
            m = re.match(r"^(\S+)\((.+)\)$", n)            # 전선우(데스데모나)
            credit(m.group(1) if m else n, slug, role, base)      # 배역명은 참여 기록에 넣지 않는다

def linkify(text, role=""):
    def one(m):
        key = person_key(m.group(1), role)
        return f'<a href="who.html#{anchor(key)}">{m.group(1)}</a>' if key in people else m.group(1)
    return re.sub(r"(?<![가-힣])([가-힣]{2,4})(?![가-힣])", one, text)


# ---- 극장·작가 색인 준비 ----
VENUE_SAME = {"대학로 정보소극장": "정보소극장", "두산아트센터 스페이스111": "두산아트센터 Space111",
              "명동 삼일로창고극장": "삼일로창고극장"}
NOT_VENUE = {"전국 12개 지역 순회"}
ABROAD = {"도쿄": "도쿄", "요코하마": "요코하마", "뮌헨": "뮌헨", "말레이시아": "말레이시아", "선전": "선전"}
def venues_of(v):
    out = []
    for x in re.split(r";\s*|,\s*", v):
        x = VENUE_SAME.get(x.strip(), x.strip())
        if x and x not in NOT_VENUE:
            out.append(x)
    return out
def vid(v):
    return "v-" + re.sub(r"\s+", "-", v)
WRITER_ROLES = {"작", "원작", "작가", "글쓰기", "대본", "글", "작·연출"}
writers = {}  # 이름 -> {작품번호: [역할]}
for r in rows:
    t = re.sub(r"〈[^〉]*〉\s*", "", r["credit"])
    t = re.sub(r"\S+\([^)]*\)", "", t)
    for piece in re.split(r",\s*| · ", t):
        words = piece.split()
        if len(words) >= 2 and words[-1] in WRITER_ROLES:
            for n in " ".join(words[:-1]).split("·"):
                n = n.strip()
                if n and n not in NOT_PERSON:
                    roles = writers.setdefault(n, {}).setdefault(r["slug"], [])
                    if words[-1] not in roles: roles.append(words[-1])

def page(slug):
    return f"w{slug}.html"

HEAD = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{t} - 그린피그</title>
<link rel="stylesheet" href="style.css">
"""

def rev_line(x):
    d, u, label, src = x
    return f'{d} <a href="{u}">{label}</a>' + (f" ({src})" if src else "")

def dkey(d):
    return tuple(int(p) for p in d.split("."))

def perf_line(r, main_title):
    s = r["date"]
    if r["title"] != main_title:
        s += f" 〈{r['title']}〉"
    s += " / " + ", ".join(f'<a href="theaters.html#{vid(v)}">{v}</a>' for v in venues_of(r["venue"])) if venues_of(r["venue"]) else f" / {r['venue']}"
    if r["note"]:
        s += f" - {r['note']}"
    return s

for i, slug in enumerate(order):
    w = works[slug]; ex = EXTRA.get(slug, {})
    t = w["title"]
    out = [HEAD.format(t=t)]
    out.append(f'<p><a href="index.html">그린피그</a> &gt; <a href="archive.html">아카이브</a> &gt; {t}</p>\n')
    out.append(f"<h2>〈{t}〉</h2>")
    out.append(f"<p>{linkify(w['credit'])}</p>\n")
    if os.path.exists(f"{SITE}/w{slug}.jpg"):
        files = [f"w{slug}.jpg"]
        n = 2
        while os.path.exists(f"{SITE}/w{slug}-{n}.jpg"):
            files.append(f"w{slug}-{n}.jpg"); n += 1
        caps = ex.get("포스터", [])
        if len(files) == 1 and not caps:
            out.append(f'<p><img src="{files[0]}" alt="〈{t}〉 포스터" width="300"></p>\n')
        else:  # 포스터가 여러 장이면 나란히 (언제·어디 포스터인지는 마우스를 올리면 보인다)
            cells = []
            for k, f in enumerate(files):
                cap = caps[k] if k < len(caps) else ""
                alt = f"〈{t}〉 포스터" + (f" ({cap})" if cap else "")
                cells.append(f'<span><a href="{f}"><img src="{f}" alt="{alt}" title="{cap}" width="200"></a></span>')
            out.append('<p class="posters">\n' + "\n".join(cells) + "\n</p>\n")
    else:
        out.append(f'<!-- 포스터가 생기면 w{slug}.jpg 로 저장하고 아래 줄의 주석을 풀어 주세요 -->\n<!-- <p><img src="w{slug}.jpg" alt="〈{t}〉 포스터" width="300"></p> -->\n')
    if "소개" in ex:
        out.append(f"<h3>작품 소개</h3>\n<p>{ex['소개']}</p>\n")
    out.append("<h3>공연 기록</h3>\n<p>\n" + "<br>\n".join(perf_line(r, t) for r in w["rows"]) + "\n</p>\n")
    if "수상" in ex:
        out.append("<h3>수상</h3>\n<p>\n" + "<br>\n".join(ex["수상"]) + "\n</p>\n")
    if "크레딧" in ex:
        out.append("<h3>크레딧</h3>\n<p>\n" + "<br>\n".join(f"{k}: {linkify(v, k)}" for k, v in ex["크레딧"]) + "\n</p>\n")
    if "리뷰" in ex:
        out.append("<h3>리뷰·기사</h3>\n<p>\n" + "<br>\n".join(rev_line(x) for x in ex["리뷰"]) + "\n</p>\n")
    if "비평" in ex:
        out.append("<h3>비평</h3>\n<p>\n" + "<br>\n".join(ex["비평"]) + "\n</p>\n")
    nav = []
    if i > 0:
        p = order[i-1]; nav.append(f'이전: <a href="{page(p)}">〈{works[p]["title"]}〉</a>')
    if i < len(order) - 1:
        n = order[i+1]; nav.append(f'다음: <a href="{page(n)}">〈{works[n]["title"]}〉</a>')
    out.append("<hr>\n<p>" + " | ".join(nav) + '<br>\n<a href="archive.html">아카이브로 돌아가기</a> | <a class="random" href="archive.html">아무 작품이나</a></p>\n')
    open(f"{SITE}/{page(slug)}", "w").write("\n".join(out))

# 아카이브 다시 만들기: 연도별 목록 + 기존 기타·수상 블록 유지
old = open(f"{SITE}/archive.html").read()
tail = old[old.index('<h3 id="other">'):]
years = sorted({r["date"][:4] for r in rows}, reverse=True)
a = [HEAD.format(t="아카이브")]
a.append('<p><a href="index.html">그린피그</a> &gt; 아카이브</p>\n')
a.append("<p>\n" + " | ".join(f'<a href="#y{y}">{y}</a>' for y in years) +
         '\n<br>\n<a href="#other">기타 공연·낭독</a> | <a href="#awards">수상</a> | <a href="theaters.html">극장별</a> | <a href="writers.html">작가별</a> | <a href="chronology.html">인쇄용 연보</a> | <a class="random" href="archive.html">아무 작품이나</a>\n</p>\n')
all_venues = {v for r in rows for v in venues_of(r["venue"])}
abroad = {k for r in rows for k in ABROAD if k in r["venue"]}
STATS = (f'<p>{years[-1]}–{years[0]}, {int(years[0]) - int(years[-1])}년. 작품 {len(order)}편, 공연 기록 {len(rows)}건, '
         f'극장 {len(all_venues)}곳(해외 {len(abroad)}개 도시), 크레딧에 오른 이름 {{N_PEOPLE}}명.</p>\n')
a.append(STATS)
a.append("<!-- 새 공연은 해당 연도 맨 아래에 한 줄 추가. 형식: 날짜 <a href=\"w번호.html\">〈제목〉</a> 작·연출 / 공연장 - 비고<br> -->\n")
for y in years:
    lines = []
    for r in rows:
        if r["date"][:4] != y: continue
        s = f'{r["date"]} <a href="{page(r["slug"])}">〈{r["title"]}〉</a> {r["credit"]} / {r["venue"]}'
        if r["note"]: s += f' - {r["note"]}'
        lines.append(s)
    a.append(f'<h3 id="y{y}">{y}</h3>\n<p>\n' + "<br>\n".join(lines) + "\n</p>\n")
a.append(tail)
open(f"{SITE}/archive.html", "w").write("\n".join(a))
print(len(order), "works,", len(rows), "performances")

# 텍스트 페이지의 관객 리뷰 부분 다시 만들기 (작품별, 최근 공유 순)
groups = []
for slug in order:
    revs = EXTRA.get(slug, {}).get("리뷰")
    if revs:
        revs = sorted(revs, key=lambda x: dkey(x[0]), reverse=True)
        y = works[slug]["rows"][0]["date"][:4]
        groups.append((dkey(revs[0][0]), f'<b><a href="{page(slug)}">〈{works[slug]["title"]}〉</a> {y}</b>', revs))
groups.append((dkey(YS_REVIEWS[0][0]), "<b>역사시비프로젝트 2024 (전반)</b>", YS_REVIEWS))
groups.sort(key=lambda g: g[0], reverse=True)
block = '<h3 id="reviews">관객 리뷰·기사</h3>\n\n'
block += "\n\n".join("<p>" + h + "<br>\n" + "<br>\n".join(rev_line(x) for x in revs) + "\n</p>" for _, h, revs in groups) + "\n\n"
t = open(f"{SITE}/texts.html").read()
a, b = t.index('<h3 id="reviews">'), t.index('<h3 id="criticism">')
t = t[:a] + block + t[b:]
t = t.replace('<a href="#reviews">관객 리뷰</a>', '<a href="#reviews">관객 리뷰·기사</a>')
open(f"{SITE}/texts.html", "w").write(t)
print(len(groups), "review groups")


# ---- 참여 기록 페이지(who.html)와 사람 페이지의 이름 링크 ----
INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
def initial(n):
    return INITIALS[(ord(n[0]) - 0xAC00) // 588]
names = sorted(people)
groups_by_init = {}
for n in names:
    groups_by_init.setdefault(initial(n), []).append(n)
pos = {slug: i for i, slug in enumerate(order)}
h = [HEAD.format(t="참여 기록")]
h.append('<p><a href="index.html">그린피그</a> &gt; <a href="people.html">사람</a> &gt; 참여 기록</p>\n')
h.append("<h2>참여 기록</h2>")
h.append("<p>" + " ".join(f'<a href="#{c}">{c}</a>' for c in INITIALS if c in groups_by_init) + "</p>\n")
for c in INITIALS:
    if c not in groups_by_init: continue
    h.append(f'<h3 id="{c}">{c}</h3>')
    for n in groups_by_init[c]:
        items = []  # (최근 연도, 작품 순서, 줄)
        for s_, roles in people[n].items():
            by_years = {}
            for role, ys in roles.items():
                by_years.setdefault(tuple(sorted(ys)), []).append(role)
            for ys, rs in by_years.items():
                items.append((ys[-1], pos[s_], f'{", ".join(ys)} <a href="{page(s_)}">〈{works[s_]["title"]}〉</a> {", ".join(rs)}'))
        items.sort(key=lambda x: (x[0], x[1]), reverse=True)
        h.append(f'<p id="{anchor(n)}"><b>{show(n)}</b><br>\n' + "<br>\n".join(x[2] for x in items) + "\n</p>")
h.append('\n<hr>\n<p><a href="people.html">사람으로 돌아가기</a></p>\n')
open(f"{SITE}/who.html", "w").write("\n".join(h))

pp = open(f"{SITE}/people.html").read()
pp = re.sub(r'<a href="who\.html#[^"]*">([^<]*)</a>', r"\1", pp)          # 기존 링크 풀기
a, b = pp.index("<h2>사람</h2>"), pp.index("<hr>")
mid = re.sub(r"(?m)^(?!<)(.+)$", lambda m: linkify(m.group(1)), pp[a:b])   # 이름 줄만
mid = mid.replace('<p>\n<a href="who.html">전체 참여 기록</a>\n</p>\n\n', "")
mid = mid.rstrip("\n") + '\n\n<p>\n<a href="who.html">전체 참여 기록</a>\n</p>\n\n'
pp = pp[:a] + mid + pp[b:]
pp = pp.replace("<p>이름을 누르면 참여한 작품이 나옵니다.</p>\n", "")
open(f"{SITE}/people.html", "w").write(pp)
print(len(people), "people indexed")


# ---- 인쇄용 공연 연보(chronology.html) ----
arch = open(f"{SITE}/archive.html").read()
def tail_lines(anchor):
    blk = arch[arch.index(f'<h3 id="{anchor}">'):]
    blk = blk[blk.index("<p>") + 3: blk.index("</p>")]
    return [l.replace("<br>", "").strip() for l in blk.strip().splitlines() if l.strip()]
OTHER_RE = re.compile(r"^(\S+) 〈(.+?)〉\s*(.*?) / (.*?)(?: - (.*))?$")
def cell(x):
    return f"<td>{x}</td>"
c = [HEAD.format(t="공연 연보")]
c.append('<p class="noprint"><a href="index.html">그린피그</a> &gt; <a href="archive.html">아카이브</a> &gt; 공연 연보</p>\n')
c.append(f"<h2>그린피그 공연 연보 {years[-1]}–{years[0]}</h2>")
c.append('<p class="noprint">인쇄하거나 PDF로 저장하면 지원서 첨부용으로 쓸 수 있습니다.</p>\n')
c.append('<div class="wide"><table class="chrono">\n<tr><th>연도</th><th>기간</th><th>작품</th><th>작·연출</th><th>공연장</th><th>비고</th></tr>')
for y in years:
    first = True
    for r in rows:
        if r["date"][:4] != y: continue
        d = r["date"][5:] if r["date"].startswith(y + ".") else r["date"]
        c.append("<tr>" + cell(y if first else "") + cell(d) + cell(f"〈{r['title']}〉") + cell(r["credit"]) + cell(r["venue"]) + cell(r["note"]) + "</tr>")
        first = False
c.append("</table></div>\n")
c.append("<h3>기타 공연·낭독</h3>")
c.append('<div class="wide"><table class="chrono">\n<tr><th>기간</th><th>작품</th><th>작·연출</th><th>공연장</th><th>비고</th></tr>')
for l in tail_lines("other"):
    m = OTHER_RE.match(l)
    if m:
        c.append("<tr>" + "".join(cell(x or "") for x in (m.group(1), f"〈{m.group(2)}〉", m.group(3), m.group(4), m.group(5))) + "</tr>")
c.append("</table></div>\n")
c.append("<h3>수상</h3>\n<p>\n" + "<br>\n".join(tail_lines("awards")) + "\n</p>\n")
c.append('<hr class="noprint">\n<p>그린피그 · greenpig.kr@gmail.com · wearegreenpig.github.io</p>\n')
open(f"{SITE}/chronology.html", "w").write("\n".join(c))

# ---- 첫 페이지 "N년 전 오늘" ----
def span(d):
    """'2012.4.19–29' → (2012, 4, 19, 끝 연, 끝 월, 끝 일). 일자를 알 수 없으면 None."""
    m = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})(.*)$", d)
    if not m: return None
    y, mo, da, rest = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
    e = re.match(r"^–(?:(\d{4})\.)?(?:(\d{1,2})\.)?(\d{1,2})$", rest.strip())
    if e:
        return (y, mo, da, int(e.group(1) or y), int(e.group(2) or mo), int(e.group(3)))
    return (y, mo, da, y, mo, da)
data = []
for r in rows:
    sp = span(r["date"])
    if sp:
        data.append(list(sp) + [r["title"], page(r["slug"]), r["venue"].split(";")[0]])
import json as _json
script = ("<!-- 오늘 -->\n<p id=\"today\" hidden></p>\n<script>\n"
  "// 지난 공연 가운데 오늘 날짜에 막을 올렸거나 공연 중이던 것을 보여 준다 (build.py가 자동 생성)\n"
  "(function(){var P=" + _json.dumps(data, ensure_ascii=False) + ";\n"
  "var t=new Date(),Y=t.getFullYear(),M=t.getMonth()+1,D=t.getDate(),open=[],run=[];\n"
  "P.forEach(function(p){if(p[0]>=Y)return;var n=Y-p[0],s=new Date(p[0],p[1]-1,p[2]),e=new Date(p[3],p[4]-1,p[5]),d=new Date(p[0],M-1,D),d2=new Date(p[0]+1,M-1,D);\n"
  "var x=function(k){return k+'년 전 오늘, <a href=\"'+p[7]+'\">〈'+p[6]+'〉</a> ';};\n"
  "if(p[1]==M&&p[2]==D)open.push(x(n)+'개막 ('+p[8]+')');else if(d>s&&d<=e)run.push(x(n)+'공연 중 ('+p[8]+')');else if(d2>s&&d2<=e&&p[0]+1<Y)run.push(x(n-1)+'공연 중 ('+p[8]+')');});\n"
  "var l=open.concat(run).slice(0,2);if(l.length){var el=document.getElementById('today');el.innerHTML=l.join('<br>');el.hidden=false;}})();\n"
  "</script>\n<!-- /오늘 -->\n")
ix = open(f"{SITE}/index.html").read()
ix = re.sub(r"<!-- 오늘 -->.*?<!-- /오늘 -->\n", "", ix, flags=re.S)
k = ix.rindex("<hr>")                       # 소식 아래, 이메일 위
ix = ix[:k] + script + "\n" + ix[k:]
open(f"{SITE}/index.html", "w").write(ix)


# ---- 극장별(theaters.html), 작가별(writers.html), 아무 작품이나(random.js) ----
by_venue = {}
for r in rows:
    for v in venues_of(r["venue"]):
        by_venue.setdefault(v, []).append(r)
tv = [HEAD.format(t="극장별")]
tv.append('<p><a href="index.html">그린피그</a> &gt; <a href="archive.html">아카이브</a> &gt; 극장별</p>\n')
tv.append("<h2>극장별</h2>")
for v, rs in sorted(by_venue.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    lines = [f'{r["date"]} <a href="{page(r["slug"])}">〈{r["title"]}〉</a>' + (f' - {r["note"]}' if r["note"] else "") for r in rs]
    tv.append(f'<p id="{vid(v)}"><b>{v}</b> ({len(rs)})<br>\n' + "<br>\n".join(lines) + "\n</p>")
tv.append('\n<hr>\n<p><a href="archive.html">아카이브로 돌아가기</a></p>\n')
open(f"{SITE}/theaters.html", "w").write("\n".join(tv))

wv = [HEAD.format(t="작가별")]
wv.append('<p><a href="index.html">그린피그</a> &gt; <a href="archive.html">아카이브</a> &gt; 작가별</p>\n')
wv.append("<h2>작가별</h2>")
for n, ws in sorted(writers.items(), key=lambda kv: (-len(kv[1]), kv[0])):
    lines = [f'{works[s]["rows"][0]["date"][:4]} <a href="{page(s)}">〈{works[s]["title"]}〉</a> {", ".join(ws[s])}'
             for s in sorted(ws, key=lambda s: pos[s])]
    name = f'<a href="who.html#{n}">{n}</a>' if n in people else n
    wv.append(f'<p><b>{name}</b> ({len(ws)})<br>\n' + "<br>\n".join(lines) + "\n</p>")
wv.append('\n<hr>\n<p><a href="archive.html">아카이브로 돌아가기</a></p>\n')
open(f"{SITE}/writers.html", "w").write("\n".join(wv))

open(f"{SITE}/random.js", "w").write(
    "// '아무 작품이나' 링크를 무작위 작품 페이지로 바꾼다 (build.py가 자동 생성)\n"
    "var W=" + _json.dumps([page(s) for s in order]) + ";\n"
    "document.querySelectorAll('a.random').forEach(function(a){a.href=W[Math.floor(Math.random()*W.length)];});\n")

# ---- 찾기(search.html)용 색인 search.js ----
# 한 줄 = [종류, 보이는 글, 주소, 덧붙임 글, 찾을 글]
idx = []
for slug in order:
    w = works[slug]; ex = EXTRA.get(slug, {})
    yrs = sorted({r["date"][:4] for r in w["rows"]})
    yr = yrs[0] + (f"–{yrs[-1]}" if len(yrs) > 1 else "")
    places = ", ".join(dict.fromkeys(v for r in w["rows"] for v in venues_of(r["venue"])))
    names = " ".join(n for role, ns in ex.get("크레딧", []) for n in ns.split(","))
    hay = " ".join([w["title"], w["credit"], places, " ".join(r["date"] for r in w["rows"]), names, ex.get("소개", "")])
    idx.append(["작품", f'〈{w["title"]}〉', page(slug), f'{yr}. {w["credit"]}', hay])
for k in sorted(people):
    idx.append(["사람", show(k), f"who.html#{anchor(k)}", f"{len(people[k])}작품", k])
for v, rs in sorted(by_venue.items()):
    idx.append(["극장", v, f"theaters.html#{vid(v)}", f"{len(rs)}회", v])
for n in sorted(writers):
    if n not in people:
        idx.append(["작가", n, "writers.html", f"{len(writers[n])}작품", n])
open(f"{SITE}/search.js", "w").write(
    "// 찾기 페이지의 색인 (build.py가 자동 생성)\nvar S=" + _json.dumps(idx, ensure_ascii=False, separators=(",", ":")) + ";\n")

ar = open(f"{SITE}/archive.html").read().replace("{N_PEOPLE}", str(len(people)))
open(f"{SITE}/archive.html", "w").write(ar)

# 공통 머리말과 최종 수정 날짜
import finish
finish.main()
