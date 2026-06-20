"""
پروژه عملی دوم — بازیابی اطلاعات و جستجوی وب
فاز چهارم: موتور جستجو با رتبه‌بندی BM25 + وزن‌دهی فیلدها
"""

from elasticsearch import Elasticsearch


# ─────────────────────────────────────────────
# ثابت‌های پروژه
# ─────────────────────────────────────────────

ES_HOST    = "http://localhost:9200"
INDEX_NAME = "zoomit_articles"

# وزن هر فیلد در جستجو — همان منطق فاز سوم ولی اینجا اعمال می‌شود
# فرمت Elasticsearch: "نام_فیلد^وزن"
SEARCH_FIELDS = [
    "title^3",            # عنوان — وزن بالا
    "title_tokens^3",     # توکن‌های عنوان — وزن بالا
    "headings^2",         # هدینگ‌ها — وزن متوسط
    "headings_tokens^2",  # توکن‌های هدینگ — وزن متوسط
    "body^1",             # متن اصلی — وزن پایه
    "body_tokens^1",      # توکن‌های متن — وزن پایه
]

# تعداد پیش‌فرض نتایج
DEFAULT_K = 10

# طول snippet در نمایش نتایج
SNIPPET_LENGTH = 200


# ─────────────────────────────────────────────
# اتصال به Elasticsearch
# ─────────────────────────────────────────────

def connect_to_elasticsearch() -> Elasticsearch:
    """اتصال به Elasticsearch محلی"""
    es = Elasticsearch(ES_HOST)
    if not es.ping():
        raise ConnectionError(f"✗ Cannot connect to {ES_HOST}.")
    return es


# ─────────────────────────────────────────────
# تابع اصلی جستجو
# ─────────────────────────────────────────────

def search_query(query_text: str, k: int = DEFAULT_K) -> list[dict]:
    """
    جستجو در ایندکس Elasticsearch با رتبه‌بندی BM25 + وزن‌دهی فیلدها.

    پارامترها:
        query_text : متن جستجوی کاربر (یک یا چند کلمه)
        k          : تعداد نتایج برگشتی (Top-K)

    خروجی:
        لیستی از دیکشنری — هر آیتم یک نتیجه جستجو است
    """
    es = connect_to_elasticsearch()

    # ── ساخت Query ──────────────────────────────
    # از multi_match استفاده می‌کنیم تا در چند فیلد همزمان جستجو کند
    # نوع "best_fields": امتیاز بهترین فیلد را اصلی می‌گیرد
    # tie_breaker: کمی از امتیاز فیلدهای دیگر هم اضافه می‌کند
    query_body = {
        "query": {
            "multi_match": {
                "query":       query_text,
                "fields":      SEARCH_FIELDS,
                "type":        "best_fields",
                "tie_breaker": 0.3,
                # اگر کلمه دقیق پیدا نشد، با fuzziness جستجوی تقریبی انجام شود
                "fuzziness":   "AUTO",
            }
        },
        # تعداد نتایج
        "size": k,
        # highlight: بخش‌هایی از متن که با query مطابقت دارند را مشخص می‌کند
        "highlight": {
            "fields": {
                "body":   {"fragment_size": SNIPPET_LENGTH, "number_of_fragments": 1},
                "title":  {"number_of_fragments": 0},
            },
            # کلمات مطابق با query را با این تگ‌ها نشان می‌دهد
            "pre_tags":  [">>>"],
            "post_tags": ["<<<"],
        }
    }

    # ── اجرای جستجو ─────────────────────────────
    response = es.search(index=INDEX_NAME, body=query_body)

    # ── پردازش نتایج ────────────────────────────
    results = []
    hits = response["hits"]["hits"]

    for hit in hits:
        source    = hit["_source"]
        score     = hit["_score"]
        highlight = hit.get("highlight", {})

        # انتخاب snippet: اگر highlight داشت از آن استفاده کن، وگرنه snippet پیش‌فرض
        if "body" in highlight:
            # highlight کلمات مطابق را علامت‌گذاری کرده
            snippet = highlight["body"][0]
        else:
            # برگشت به snippet ذخیره‌شده در فاز ۲
            snippet = source.get("snippet", "")[:SNIPPET_LENGTH]

        results.append({
            "title":    source.get("title", "no title"),
            "snippet":  snippet,
            "score":    round(score, 4),
            "url":      source.get("url", ""),
            "category": source.get("category", ""),
            "date":     source.get("date", ""),
        })

    return results


# ─────────────────────────────────────────────
# نمایش نتایج
# ─────────────────────────────────────────────

def display_results(results: list[dict], query_text: str) -> None:
    """
    نتایج جستجو را به شکل خوانا در ترمینال نمایش می‌دهد.
    هر نتیجه شامل: عنوان، اسنیپت، امتیاز، و لینک
    """
    print("\n" + "═" * 65)
    print(f"  Search results for: «{query_text}»")
    print(f"  Number of results: {len(results)}")
    print("═" * 65)

    if not results:
        print("\n  No results found.")
        print("  Try different keywords.")
        return

    for i, result in enumerate(results, start=1):
        print(f"\n  [{i}] {result['title']}")
        print(f"  {'─' * 60}")

        # نمایش snippet — علامت‌های highlight را خواناتر کن
        snippet = result["snippet"].replace(">>>", "【").replace("<<<", "】")
        print(f"  {snippet}")

        print(f"\n  Score: {result['score']}")

        # نمایش دسته‌بندی و تاریخ (اگر وجود داشت)
        meta_parts = []
        if result["category"]:
            meta_parts.append(f"Category: {result['category']}")
        if result["date"]:
            meta_parts.append(f"Date: {result['date'][:10]}")
        if meta_parts:
            print(f"  {' | '.join(meta_parts)}")

        print(f"  🔗 {result['url']}")
        print(f"  {'─' * 60}")


# ─────────────────────────────────────────────
# نمونه Query های از پیش تعریف‌شده
# ─────────────────────────────────────────────

def run_sample_queries(sample_queries: list[str], k: int = 5) -> None:
    """
    چند query نمونه را اجرا می‌کند و نتایج را نمایش می‌دهد.
    این بخش برای گزارش پروژه مفید است.
    """
    print("\n" + "★" * 65)
    print("  Running sample queries for project report")
    print("★" * 65)

    for query in sample_queries:
        results = search_query(query, k=k)
        display_results(results, query)
        input("\n  Press Enter for next query...")


# ─────────────────────────────────────────────
# رابط کاربری تعاملی
# ─────────────────────────────────────────────

def interactive_search() -> None:
    """
    یک حلقه جستجوی تعاملی در ترمینال.
    کاربر می‌تواند هر query ای وارد کند و نتایج را ببیند.
    با تایپ 'خروج' یا 'exit' از برنامه خارج می‌شود.
    """
    print("\n" + "═" * 65)
    print("  Zoomit Persian Search Engine — Phase 4")
    print("  Type 'exit' or 'خروج' to quit")
    print("═" * 65)

    # بررسی اتصال قبل از شروع حلقه
    try:
        es = connect_to_elasticsearch()
        count = es.count(index=INDEX_NAME)["count"]
        print(f"\n✓ Search engine ready. ({count} indexed documents)")
    except Exception as e:
        print(f"✗ Error: {e}")
        return

    while True:
        print()
        query = input("  🔍 Search: ").strip()

        # شرط خروج
        if query.lower() in ("exit", "خروج", "quit", "q"):
            print("\n  Goodbye! 👋")
            break

        # نادیده گرفتن ورودی خالی
        if not query:
            continue

        # دریافت تعداد نتایج از کاربر
        k_input = input(f"  Number of results (default {DEFAULT_K}): ").strip()
        k = int(k_input) if k_input.isdigit() else DEFAULT_K

        # اجرای جستجو
        try:
            results = search_query(query, k=k)
            display_results(results, query)
        except Exception as e:
            print(f"  ✗ Search error: {e}")


# ─────────────────────────────────────────────
# نقطه ورود اصلی
# ─────────────────────────────────────────────

if __name__ == "__main__":

    # ── Query های نمونه برای گزارش پروژه ───────
    # این‌ها در گزارش نهایی به عنوان نمونه ارائه می‌شوند
    SAMPLE_QUERIES = [
        "هوش مصنوعی",           # جستجوی تک‌کلمه‌ای
        "گوشی سامسونگ",          # جستجوی دوکلمه‌ای
        "بهترین لپ‌تاپ ۲۰۲۵",    # جستجوی چندکلمه‌ای
        "آپدیت اندروید",         # جستجوی اصطلاح فنی
        "بررسی دوربین آیفون",    # جستجوی عبارتی
    ]

    print("=" * 65)
    print("  Phase 4: Zoomit Search Engine")
    print("=" * 65)
    print("\n  Choose a mode:")
    print("  [1] Interactive search")
    print("  [2] Run sample queries (for report)")

    choice = input("\n  Your choice (1 or 2): ").strip()

    if choice == "2":
        run_sample_queries(SAMPLE_QUERIES, k=5)
    else:
        # حالت پیش‌فرض: جستجوی تعاملی
        interactive_search()
