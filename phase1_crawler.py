"""
پروژه عملی دوم — بازیابی اطلاعات و جستجوی وب
فاز اول: خزنده وب برای سایت زومیت
نوشته‌شده با BeautifulSoup و requests
"""

import requests
from bs4 import BeautifulSoup
from collections import deque
import json
import time
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse


# ─────────────────────────────────────────────
# ثابت‌های پروژه
# ─────────────────────────────────────────────

# آدرس شروع خزنده
SEED_URL = "https://www.zoomit.ir/"

# دامنه‌ای که فقط باید داخل آن بمانیم
ALLOWED_DOMAIN = "zoomit.ir"

# حداقل تعداد صفحاتی که باید جمع‌آوری شود
MIN_PAGES = 100

# حداکثر تعداد صفحه برای جلوگیری از اجرای بی‌نهایت
MAX_PAGES = 200

# تأخیر بین هر درخواست (ثانیه) — رعایت ادب نسبت به سرور
REQUEST_DELAY = 1.5

# نام فایل خروجی
OUTPUT_FILE = "crawled_data.json"

# هدر درخواست HTTP — شبیه‌سازی مرورگر واقعی
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# الگوهایی که باید از کرال آن‌ها اجتناب کنیم (فایل، لاگین، و ...)
SKIP_EXTENSIONS = re.compile(
    r"\.(jpg|jpeg|png|gif|webp|svg|pdf|zip|mp4|mp3|css|js|ico|xml|rss)$",
    re.IGNORECASE,
)
SKIP_PATTERNS = re.compile(
    r"/(login|logout|register|signup|cart|checkout|account|feed|api)/",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────
# توابع کمکی
# ─────────────────────────────────────────────

def is_valid_url(url: str) -> bool:
    """
    بررسی می‌کند آیا URL داده‌شده معتبر و قابل کرال است یا نه.
    معیارها: داخل دامنه zoomit.ir باشد، پسوند فایل نداشته باشد،
    و مسیر ممنوعه نباشد.
    """
    try:
        parsed = urlparse(url)
        # فقط http و https مجاز است
        if parsed.scheme not in ("http", "https"):
            return False
        # باید داخل دامنه مجاز باشد
        if ALLOWED_DOMAIN not in parsed.netloc:
            return False
        # اگر پسوند فایل دارد، رد کن
        if SKIP_EXTENSIONS.search(parsed.path):
            return False
        # اگر مسیر ممنوعه دارد، رد کن
        if SKIP_PATTERNS.search(parsed.path):
            return False
        return True
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """
    URL را نرمال‌سازی می‌کند:
    - fragment (#) را حذف می‌کند
    - query string را حذف می‌کند (برای جلوگیری از صفحات تکراری)
    - اسلش انتهایی را یکسان می‌کند
    """
    parsed = urlparse(url)
    # fragment و query را حذف کن
    clean = parsed._replace(fragment="", query="")
    normalized = clean.geturl()
    # اگر آدرس با اسلش تمام نشد، اضافه کن — یکپارچگی
    if not normalized.endswith("/") and "." not in parsed.path.split("/")[-1]:
        normalized = normalized.rstrip("/") + "/"
    return normalized


def fetch_page(url: str) -> BeautifulSoup | None:
    """
    صفحه HTML را دانلود می‌کند و یک شیء BeautifulSoup برمی‌گرداند.
    در صورت بروز خطا، None برمی‌گرداند.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)

        # فقط صفحات HTML را پردازش کن
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return None

        # فقط صفحاتی با کد ۲۰۰ معتبرند
        if response.status_code != 200:
            return None

        # رمزگذاری صحیح متن فارسی
        response.encoding = response.apparent_encoding or "utf-8"
        return BeautifulSoup(response.text, "html.parser")

    except requests.RequestException as e:
        print(f"    [خطا] دانلود ناموفق: {url} — {e}")
        return None


def extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """
    تمام لینک‌های داخلی را از صفحه استخراج می‌کند.
    لینک‌های نسبی را به مطلق تبدیل می‌کند.
    """
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()

        # لینک‌های جاوا‌اسکریپت را رد کن
        if href.startswith("javascript:") or href == "#":
            continue

        # لینک نسبی را به مطلق تبدیل کن
        full_url = urljoin(base_url, href)

        # بررسی اعتبار لینک
        if is_valid_url(full_url):
            links.append(normalize_url(full_url))

    return links


def extract_page_data(soup: BeautifulSoup, url: str) -> dict | None:
    """
    اطلاعات مورد نیاز را از صفحه HTML استخراج می‌کند:
    - عنوان صفحه
    - محتوای اصلی
    - متن هدینگ‌ها (H1, H2, H3)
    - تاریخ انتشار
    - دسته‌بندی
    - آدرس صفحه
    """

    # ── عنوان صفحه ──────────────────────────────
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    # جایگزین: از تگ og:title استفاده کن
    if not title:
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", "").strip()

    # صفحاتی که عنوان ندارند را رد کن
    if not title:
        return None

    # ── هدینگ‌ها (H1, H2, H3) ───────────────────
    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            headings.append(text)

    # ── محتوای اصلی ─────────────────────────────
    body_text = ""

    # روش ۱: تگ‌های رایج محتوای مقاله در زومیت
    content_selectors = [
        {"name": "article"},
        {"class_": re.compile(r"article|post|content|body|text", re.I)},
        {"id": re.compile(r"article|post|content|body|main", re.I)},
    ]

    for selector in content_selectors:
        container = soup.find(**selector)
        if container:
            # اسکریپت و استایل‌ها را قبل از استخراج متن حذف کن
            for tag in container.find_all(["script", "style", "aside", "nav"]):
                tag.decompose()
            body_text = container.get_text(separator=" ", strip=True)
            if len(body_text) > 200:  # محتوای کافی داشته باشد
                break

    # روش ۲ (fallback): تمام پاراگراف‌های صفحه
    if len(body_text) < 200:
        paragraphs = soup.find_all("p")
        body_text = " ".join(p.get_text(strip=True) for p in paragraphs)

    # صفحات خیلی کوتاه (مثلاً صفحه ۴۰۴) را رد کن
    if len(body_text) < 100:
        return None

    # ── تاریخ انتشار ────────────────────────────
    pub_date = ""

    # روش ۱: تگ <time> با attribute datetime
    time_tag = soup.find("time")
    if time_tag:
        pub_date = time_tag.get("datetime", "") or time_tag.get_text(strip=True)

    # روش ۲: متادیتای Open Graph / Schema.org
    if not pub_date:
        for prop in ["article:published_time", "datePublished", "publish_date"]:
            meta = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if meta:
                pub_date = meta.get("content", "").strip()
                break

    # روش ۳: جستجوی JSON-LD (داده‌های ساختاریافته)
    if not pub_date:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    pub_date = data.get("datePublished", "")
                    if pub_date:
                        break
            except (json.JSONDecodeError, AttributeError):
                continue

    # ── دسته‌بندی/موضوع ─────────────────────────
    category = ""

    # روش ۱: از مسیر URL (مثلاً /mobile/ یا /tech/)
    path_parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
    if path_parts:
        # اولین بخش مسیر معمولاً دسته‌بندی است
        category = path_parts[0]

    # روش ۲: از متادیتا
    if not category:
        og_section = soup.find("meta", property="article:section")
        if og_section:
            category = og_section.get("content", "").strip()

    # ── ساختار نهایی خروجی ──────────────────────
    return {
        "url": url,
        "title": title,
        "headings": headings,
        "body": body_text,
        "date": pub_date,
        "category": category,
        "crawled_at": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────
# تابع اصلی خزنده (BFS)
# ─────────────────────────────────────────────

def crawl(seed_url: str = SEED_URL) -> list[dict]:
    """
    خزنده اصلی با رویکرد جستجوی سطح‌به‌سطح (BFS).
    از یک صف (deque) برای مدیریت URL‌ها استفاده می‌کند.

    مراحل:
    1. با seed_url شروع می‌کند
    2. صفحه را دانلود و پارس می‌کند
    3. لینک‌های جدید را به صف اضافه می‌کند
    4. تا رسیدن به MIN_PAGES یا خالی شدن صف ادامه می‌دهد
    """

    # صف URL‌هایی که باید کرال شوند
    queue = deque()
    queue.append(normalize_url(seed_url))

    # مجموعه URL‌هایی که قبلاً بازدید شده‌اند (جلوگیری از تکرار)
    visited = set()
    visited.add(normalize_url(seed_url))

    # لیست نتایج جمع‌آوری‌شده
    collected_pages = []

    print("=" * 60)
    print("  Zoomit Crawler — Started")
    print(f"  Starting URL: {seed_url}")
    print(f"  Target: Collecting at least {MIN_PAGES} pages")
    print("=" * 60)

    while queue and len(collected_pages) < MAX_PAGES:
        # URL بعدی را از ابتدای صف بردار
        current_url = queue.popleft()

        print(f"\n[{len(collected_pages)+1}] Crawling: {current_url}")

        # صفحه را دانلود کن
        soup = fetch_page(current_url)
        if soup is None:
            print("    → Failed to fetch page, skipping.")
            continue

        # داده‌های صفحه را استخراج کن
        page_data = extract_page_data(soup, current_url)
        if page_data is None:
            print("    → Insufficient content, skipping.")
        else:
            collected_pages.append(page_data)
            title_preview = page_data["title"][:50]
            print(f"    ✓ Saved | Title: {title_preview}")

        # لینک‌های جدید را استخراج و به صف اضافه کن
        new_links = extract_links(soup, current_url)
        added = 0
        for link in new_links:
            if link not in visited:
                visited.add(link)
                queue.append(link)
                added += 1
        print(f"    → {added} new links added to queue | Queue size: {len(queue)}")

        # تأخیر بین درخواست‌ها — محترمانه باشیم!
        time.sleep(REQUEST_DELAY)

    print("\n" + "=" * 60)
    print(f"  Crawler finished.")
    print(f"  Collected pages: {len(collected_pages)}")
    print(f"  Visited URLs: {len(visited)}")
    print("=" * 60)

    return collected_pages


# ─────────────────────────────────────────────
# ذخیره‌سازی نتایج
# ─────────────────────────────────────────────

def save_to_json(data: list[dict], filename: str = OUTPUT_FILE) -> None:
    """
    داده‌های جمع‌آوری‌شده را در قالب JSON ذخیره می‌کند.
    از ensure_ascii=False برای پشتیبانی از متن فارسی استفاده می‌شود.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Data saved to file '{filename}'.")
    print(f"  Number of records: {len(data)}")


# ─────────────────────────────────────────────
# نقطه ورود اصلی
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # اجرای خزنده
    pages = crawl()

    # بررسی اینکه آیا به حداقل تعداد صفحه رسیدیم
    if len(pages) < MIN_PAGES:
        print(f"\n⚠ Warning: Only {len(pages)} pages were collected (Target: {MIN_PAGES})")
    else:
        print(f"\n✓ Success: {len(pages)} pages were collected.")

    # ذخیره در فایل JSON
    save_to_json(pages)
