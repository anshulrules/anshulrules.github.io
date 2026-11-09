# 모든 페이지에 공통 머리말(언어, 탭 아이콘, 공유 미리보기)과 발행일를 넣는다.
# build.py 끝에서 자동으로 불리며, 손으로 페이지를 고친 뒤 이것만 따로 돌려도 된다:
#   python3 _tools/finish.py
import os, re, json, glob, hashlib, html
from datetime import datetime, timezone, timedelta

TOOLS = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(TOOLS)
BASE = "https://wearegreenpig.github.io/"
STATE = os.path.join(TOOLS, "수정날짜.json")

DESC = {  # 작품 페이지가 아닌 페이지의 미리보기 설명
    "index.html": "불온한 상상력, 2006년부터. 극단 그린피그의 공연 기록과 소식.",
    "about.html": "생각이 세상을 바꾼다는 신념과 뜨거운 감성을 가진 사람들이 만든 공연단체, 그린피그.",
    "people.html": "그린피그의 대표, 연출, 배우.",
    "texts.html": "그린피그 공연에 관한 관객 리뷰, 기사, 비평.",
    "chronology.html": "그린피그 공연 연보. 2006년부터의 모든 공연과 수상.",
    "theaters.html": "그린피그가 공연한 극장들과 그곳에서 올린 작품.",
    "writers.html": "그린피그가 무대에 올린 작가들과 작품.",
    "who.html": "그린피그 공연에 참여한 사람들과 그들의 작품 목록.",
    "colophon.html": "이 사이트의 발행인.",
    "search.html": "그린피그의 작품, 사람, 극장 찾기.",
    "404.html": "찾으시는 페이지가 없습니다.",
    "archive.html": "2006년부터 지금까지 그린피그의 모든 공연 기록과 수상.",
}

META_RE = re.compile(r"<!-- 공통 머리말 -->.*?<!-- /공통 머리말 -->\n", re.S)
DATE_RE = re.compile(r'\n?<p class="updated">.*?</p>\n?', re.S)

def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()

def short(s, n=110):
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"

def describe(name, text):
    if name in DESC:
        return DESC[name]
    m = re.search(r"<h3>작품 소개</h3>\s*<p>(.*?)</p>", text, re.S)
    if m:  # 역사시비 작품은 공통 머리 문장을 빼고 그 달의 설명부터
        return short(re.sub(r"^역사시비프로젝트:.*?올렸다\.\s*", "역사시비프로젝트 ", plain(m.group(1))))
    m = re.search(r"</h2>\s*<p>(.*?)</p>", text, re.S)
    return short(plain(m.group(1))) if m else DESC["index.html"]

def core(text):  # 날짜 비교용: 자동으로 넣는 부분을 뺀 본문
    return DATE_RE.sub("", META_RE.sub("", text)).replace('<html lang="ko">\n', "")

def main():
    today = datetime.now(timezone(timedelta(hours=9)))
    today = f"{today.year}.{today.month}.{today.day}"
    try:
        state = json.load(open(STATE))
    except Exception:
        state = {}
    for path in sorted(glob.glob(os.path.join(SITE, "*.html"))):
        name = os.path.basename(path)
        text = open(path, encoding="utf-8").read()
        body = core(text)
        h = hashlib.sha1(body.encode()).hexdigest()
        old = state.get(name, {})
        date = old.get("date") if old.get("hash") == h else today
        state[name] = {"hash": h, "date": date}

        title = plain(re.search(r"<title>(.*?)</title>", body, re.S).group(1))
        url = BASE if name == "index.html" else BASE + name
        img = name.replace(".html", ".jpg")
        image = BASE + img if name.startswith("w") and os.path.exists(os.path.join(SITE, img)) else BASE + "og.png"
        desc = html.escape(describe(name, body), quote=True)
        meta = ("<!-- 공통 머리말 -->\n"
                '<link rel="icon" href="favicon.png" type="image/png">\n'
                '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
                '<link rel="author" href="humans.txt">\n'
                '<script src="random.js" defer></script>\n'
                # 로고를 눌러 고른 밤낮을 페이지가 그려지기 전에 적용 (theme.js)
                '<script src="theme.js"></script>\n'
                f'<meta name="description" content="{desc}">\n'
                '<meta property="og:site_name" content="그린피그">\n'
                f'<meta property="og:title" content="{html.escape(title, quote=True)}">\n'
                f'<meta property="og:description" content="{desc}">\n'
                f'<meta property="og:image" content="{image}">\n'
                f'<meta property="og:url" content="{url}">\n'
                '<meta property="og:type" content="website">\n'
                '<meta name="twitter:card" content="summary_large_image">\n'
                "<!-- /공통 머리말 -->\n")
        out = body.replace("<!doctype html>\n", '<!doctype html>\n<html lang="ko">\n', 1)
        out = out.replace('<link rel="stylesheet" href="style.css">\n',
                          '<link rel="stylesheet" href="style.css">\n' + meta, 1)
        # '발행일' 글자는 눈에 띄지 않는 '발행인' 페이지 링크
        out = out.rstrip("\n") + f'\n\n<p class="updated"><a class="hid" href="colophon.html">발행일</a> {date}</p>\n'
        if out != text:
            open(path, "w", encoding="utf-8").write(out)
    json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=0, sort_keys=True)

if __name__ == "__main__":
    main()
