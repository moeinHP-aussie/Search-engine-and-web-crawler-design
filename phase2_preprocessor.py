"""
پروژه عملی دوم — بازیابی اطلاعات و جستجوی وب
فاز دوم: پیش‌پردازش متن فارسی با کتابخانه Hazm
ورودی:  crawled_data.json  (خروجی فاز اول)
خروجی: preprocessed_data.json
"""

import json
import re
from hazm import Normalizer, word_tokenize, Lemmatizer, stopwords_list


# ─────────────────────────────────────────────
# ثابت‌های پروژه
# ─────────────────────────────────────────────

INPUT_FILE  = "crawled_data.json"
OUTPUT_FILE = "preprocessed_data.json"

# حداقل طول توکن — کلمات خیلی کوتاه (یک یا دو حرف) معمولاً بی‌معنی‌اند
MIN_TOKEN_LEN = 2


# ─────────────────────────────────────────────
# بارگذاری ابزارهای Hazm
# ─────────────────────────────────────────────

# نرمال‌ساز: نیم‌فاصله، اعداد عربی، کاراکترهای یکسان‌سازی و ... را درست می‌کند
normalizer = Normalizer()

# لِماتایزر: کلمات را به ریشه‌شان تبدیل می‌کند
# مثال: «رفتند» → «رفت»، «کتاب‌ها» → «کتاب»
lemmatizer = Lemmatizer()

# لیست stop words فارسی از Hazm
# کلماتی مثل «و»، «در»، «که»، «این»، «با» که اطلاعات مفیدی ندارند
STOP_WORDS = set(stopwords_list())


# ─────────────────────────────────────────────
# توابع پیش‌پردازش
# ─────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    پاک‌سازی اولیه متن قبل از نرمال‌سازی:
    - URLها را حذف می‌کند
    - کاراکترهای HTML باقی‌مانده را حذف می‌کند
    - اعداد و نمادهای غیرفارسی را حذف می‌کند
    - فاصله‌های اضافه را حذف می‌کند
    """
    if not text:
        return ""

    # حذف URLهای احتمالی باقی‌مانده در متن
    text = re.sub(r"https?://\S+", " ", text)

    # حذف تگ‌های HTML احتمالی باقی‌مانده
    text = re.sub(r"<[^>]+>", " ", text)

    # حذف ایمیل‌ها
    text = re.sub(r"\S+@\S+\.\S+", " ", text)

    # حذف کاراکترهای خاص و علائم نگارشی انگلیسی — فارسی را نگه می‌داریم
    # کاراکترهای فارسی: \u0600-\u06FF و \uFB50-\uFDFF و \uFE70-\uFEFF
    text = re.sub(r"[^\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF\s]", " ", text)

    # چندین فاصله پشت‌سرهم را به یک فاصله تبدیل کن
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_text(text: str) -> str:
    """
    نرمال‌سازی متن فارسی با Hazm:
    - «ي» عربی → «ی» فارسی
    - «ك» عربی → «ک» فارسی
    - اعداد عربی (٣٤٥) → اعداد فارسی (۳۴۵)
    - نیم‌فاصله‌ها را درست می‌کند
    - کاراکترهای یونیکد غیراستاندارد را اصلاح می‌کند
    """
    if not text:
        return ""
    return normalizer.normalize(text)


def tokenize_text(text: str) -> list[str]:
    """
    توکن‌سازی: متن را به لیستی از کلمات تبدیل می‌کند.
    Hazm از قواعد زبان فارسی آگاه است (مثلاً نیم‌فاصله را می‌فهمد).
    """
    if not text:
        return []
    return word_tokenize(text)


def remove_stopwords(tokens: list[str]) -> list[str]:
    """
    کلمات بی‌معنی (stop words) را از لیست توکن‌ها حذف می‌کند.
    همچنین توکن‌های خیلی کوتاه را فیلتر می‌کند.
    مثال: ['این', 'مقاله', 'در', 'مورد'] → ['مقاله', 'مورد']
    """
    filtered = []
    for token in tokens:
        # توکن‌های کوتاه‌تر از حداقل طول را رد کن
        if len(token) < MIN_TOKEN_LEN:
            continue
        # stop word را رد کن
        if token in STOP_WORDS:
            continue
        filtered.append(token)
    return filtered


def lemmatize_tokens(tokens: list[str]) -> list[str]:
    """
    لِماتایزیشن: هر توکن را به ریشه اصلی خود تبدیل می‌کند.
    این کار «بازیابی» (Recall) را بهبود می‌دهد:
    کاربر «کتاب» را سرچ می‌کند و نتایج «کتاب‌ها» و «کتابی» را هم پیدا می‌کند.

    نکته: Hazm لِماتایزر برای افعال خروجی «ماضی#مضارع» می‌دهد.
    مثال: «می‌روند» → «رفت#رو»
    ما فقط بخش اول (ماضی) را نگه می‌داریم.
    """
    lemmatized = []
    for token in tokens:
        lemma = lemmatizer.lemmatize(token)
        # اگر خروجی شامل # بود (فعل)، بخش اول را بگیر
        if "#" in lemma:
            lemma = lemma.split("#")[0]
        # اگر لِما خالی شد، توکن اصلی را نگه دار
        if lemma:
            lemmatized.append(lemma)
        else:
            lemmatized.append(token)
    return lemmatized


def preprocess_field(text: str) -> dict:
    """
    یک فیلد متنی را کامل پیش‌پردازش می‌کند و دو نسخه برمی‌گرداند:
    - نسخه نرمال‌شده (برای نمایش snippet در نتایج جستجو)
    - نسخه توکن‌شده/لِماتایزشده (برای ایندکس‌گذاری)
    """
    # مرحله ۱: پاک‌سازی اولیه
    cleaned = clean_text(text)

    # مرحله ۲: نرمال‌سازی فارسی
    normalized = normalize_text(cleaned)

    # مرحله ۳: توکن‌سازی
    tokens = tokenize_text(normalized)

    # مرحله ۴: حذف stop words
    tokens_no_stop = remove_stopwords(tokens)

    # مرحله ۵: لِماتایزیشن
    lemmas = lemmatize_tokens(tokens_no_stop)

    return {
        "normalized": normalized,          # متن نرمال‌شده — برای snippet
        "tokens": " ".join(lemmas),        # توکن‌های پردازش‌شده — برای جستجو
    }


def preprocess_headings(headings: list[str]) -> dict:
    """
    لیست هدینگ‌ها را پیش‌پردازش می‌کند.
    هدینگ‌ها در فاز ۳ وزن بیشتری خواهند داشت.
    """
    all_headings_text = " ".join(headings)
    result = preprocess_field(all_headings_text)
    return result


# ─────────────────────────────────────────────
# تابع اصلی پردازش
# ─────────────────────────────────────────────

def preprocess_document(doc: dict) -> dict:
    """
    یک سند کامل را پیش‌پردازش می‌کند.
    ساختار ورودی: خروجی فاز اول (crawled_data.json)
    ساختار خروجی: آماده برای ایندکس‌گذاری در Elasticsearch
    """

    # ── پیش‌پردازش عنوان ────────────────────────
    title_processed = preprocess_field(doc.get("title", ""))

    # ── پیش‌پردازش هدینگ‌ها ─────────────────────
    headings_processed = preprocess_headings(doc.get("headings", []))

    # ── پیش‌پردازش متن اصلی ─────────────────────
    body_processed = preprocess_field(doc.get("body", ""))

    # ── ساخت سند نهایی ──────────────────────────
    return {
        # فیلدهای اصلی — همان‌طور که Elasticsearch نیاز دارد
        "url":      doc.get("url", ""),
        "date":     doc.get("date", ""),
        "category": doc.get("category", ""),

        # عنوان: هم نسخه اصلی (برای نمایش) هم نسخه پردازش‌شده (برای جستجو)
        "title":          title_processed["normalized"],
        "title_tokens":   title_processed["tokens"],

        # هدینگ‌ها: برای وزن‌دهی بیشتر در فاز ۳
        "headings":         " ".join(doc.get("headings", [])),
        "headings_tokens":  headings_processed["tokens"],

        # متن اصلی
        "body":         body_processed["normalized"],
        "body_tokens":  body_processed["tokens"],

        # اسنیپت: ۳۰۰ کاراکتر اول متن نرمال‌شده — برای نمایش در نتایج
        "snippet": body_processed["normalized"][:300],
    }


def run_preprocessing():
    """
    تابع اصلی که فایل crawled_data.json را می‌خواند،
    تمام اسناد را پیش‌پردازش می‌کند، و نتیجه را ذخیره می‌کند.
    """

    # ── بارگذاری داده‌های خام ────────────────────
    print("=" * 60)
    print("  Phase 2: Persian Text Preprocessing")
    print("=" * 60)

    print(f"\n⟳ Loading '{INPUT_FILE}' ...")
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            raw_docs = json.load(f)
    except FileNotFoundError:
        print(f"✗ Error: File '{INPUT_FILE}' not found.")
        print("  Run Phase 1 first.")
        return

    print(f"✓ {len(raw_docs)} documents loaded.\n")

    # ── پردازش هر سند ────────────────────────────
    processed_docs = []
    for i, doc in enumerate(raw_docs, start=1):
        print(f"[{i}/{len(raw_docs)}] پردازش: {doc.get('title', '')[:50]}")
        try:
            processed = preprocess_document(doc)
            processed_docs.append(processed)
        except Exception as e:
            # اگر یک سند خطا داد، بقیه را ادامه بده
            print(f"    ⚠ Error processing this document: {e}")
            continue

    # ── ذخیره‌سازی نتایج ─────────────────────────
    print(f"\n⟳ Saving to '{OUTPUT_FILE}' ...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(processed_docs, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(f"✓ Preprocessing completed.")
    print(f"  Processed documents: {len(processed_docs)}")
    print(f"  Output file: {OUTPUT_FILE}")
    print("=" * 60)

    # ── Display a sample for verification ────────────────
    if processed_docs:
        print("\n── First sample (for verification) ──")
        sample = processed_docs[0]
        print(f"  URL:     {sample['url']}")
        print(f"  Title:   {sample['title']}")
        print(f"  Title tokens: {sample['title_tokens'][:80]}...")
        print(f"  Body tokens:  {sample['body_tokens'][:80]}...")
    
# ─────────────────────────────────────────────
# نقطه ورود اصلی
# ─────────────────────────────────────────────

if __name__ == "__main__":
    run_preprocessing()
