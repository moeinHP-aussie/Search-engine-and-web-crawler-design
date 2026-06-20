"""
پروژه عملی دوم — بازیابی اطلاعات و جستجوی وب
فاز سوم: ایندکس‌گذاری در Elasticsearch
ورودی:  preprocessed_data.json  (خروجی فاز دوم)
نسخه Elasticsearch: 9.4.0 (بدون Security)
"""

import json
from elasticsearch import Elasticsearch, helpers


# ─────────────────────────────────────────────
# ثابت‌های پروژه
# ─────────────────────────────────────────────

INPUT_FILE = "preprocessed_data.json"

# آدرس Elasticsearch روی سیستم محلی
ES_HOST = "http://localhost:9200"

# نام ایندکسی که اسناد در آن ذخیره می‌شوند
INDEX_NAME = "zoomit_articles"


# ─────────────────────────────────────────────
# تعریف Mapping ایندکس
# ─────────────────────────────────────────────

# Mapping مشخص می‌کند هر فیلد چه نوع داده‌ای دارد
# و چطور باید ایندکس شود
INDEX_MAPPING = {
    "settings": {
        # تعداد shard و replica برای پروژه محلی
        "number_of_shards": 1,
        "number_of_replicas": 0,

        "analysis": {
            # آنالایزر سفارشی برای متن فارسی
            "analyzer": {
                "persian_analyzer": {
                    # standard tokenizer کلمات را جدا می‌کند
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",           # حروف کوچک
                        "persian_stop_filter", # حذف stop words
                    ]
                }
            },
            "filter": {
                # فیلتر stop words فارسی
                "persian_stop_filter": {
                    "type": "stop",
                    "stopwords": [
                        "و", "در", "به", "از", "که", "این", "را", "با",
                        "است", "آن", "یک", "هم", "تا", "بر", "خود",
                        "های", "شد", "شده", "می", "کرد", "هر", "ما",
                        "کند", "بود", "بین", "اما", "اگر", "نیز",
                        "وی", "او", "ها", "شما", "من", "آنها"
                    ]
                }
            }
        }
    },

    "mappings": {
        "properties": {

            # ── عنوان ─────────────────────────────────
            # نکته: از نسخه ۸ به بعد، boost در mapping حذف شده
            # وزن‌دهی (boost) را در query فاز چهارم اعمال می‌کنیم
            "title": {
                "type": "text",
                "analyzer": "persian_analyzer",
                "fields": {
                    # نسخه keyword برای مرتب‌سازی دقیق
                    "keyword": {"type": "keyword"}
                }
            },

            # توکن‌های پردازش‌شده عنوان (خروجی فاز ۲)
            "title_tokens": {
                "type": "text",
                "analyzer": "persian_analyzer"
            },

            # ── هدینگ‌ها ────────────────────────────────
            "headings": {
                "type": "text",
                "analyzer": "persian_analyzer"
            },

            "headings_tokens": {
                "type": "text",
                "analyzer": "persian_analyzer"
            },

            # ── متن اصلی ────────────────────────────────
            "body": {
                "type": "text",
                "analyzer": "persian_analyzer"
            },

            "body_tokens": {
                "type": "text",
                "analyzer": "persian_analyzer"
            },

            # ── فیلدهای اطلاعاتی (برای نمایش نتایج) ───
            "snippet": {
                "type": "text",
                "index": False   # snippet فقط برای نمایش است، نیازی به ایندکس ندارد
            },

            "url": {
                "type": "keyword",   # URL باید عیناً ذخیره شود
                "index": False       # نیازی به جستجو در URL نیست
            },

            "date": {
                "type": "keyword"
            },

            "category": {
                "type": "keyword"    # دسته‌بندی — برای فیلتر کردن
            },
        }
    }
}


# ─────────────────────────────────────────────
# اتصال به Elasticsearch
# ─────────────────────────────────────────────

def connect_to_elasticsearch() -> Elasticsearch:
    """
    اتصال به Elasticsearch محلی را برقرار می‌کند.
    نسخه 9.4.0 بدون Security — اتصال ساده با HTTP
    """
    es = Elasticsearch(ES_HOST)

    # بررسی اینکه آیا سرور در دسترس است
    if not es.ping():
        raise ConnectionError(
            f"✗ Cannot connect to Elasticsearch!\n"
            f"  Make sure service is running: {ES_HOST}"
        )

    print(f"✓ Connected to Elasticsearch: {ES_HOST}")

    # نمایش اطلاعات کلاستر
    info = es.info()
    print(f"  Version: {info['version']['number']}")
    print(f"  Cluster name: {info['cluster_name']}")

    return es


# ─────────────────────────────────────────────
# ساخت ایندکس
# ─────────────────────────────────────────────

def create_index(es: Elasticsearch) -> None:
    """
    ایندکس را با Mapping سفارشی می‌سازد.
    اگر ایندکس قبلاً وجود داشت، آن را حذف و دوباره می‌سازد.
    (مناسب برای محیط توسعه و تست)
    """
    # بررسی وجود ایندکس
    if es.indices.exists(index=INDEX_NAME):
        print(f"\n⚠ Index '{INDEX_NAME}' already exists.")
        answer = input("  Delete and recreate it? (y/n): ").strip().lower()

        if answer == "y":
            es.indices.delete(index=INDEX_NAME)
            print("  ✓ Old index deleted.")
        else:
            print("  → Existing index will be used.")
            return

    # ساخت ایندکس
    es.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
    print(f"✓ Index '{INDEX_NAME}' created successfully.")
    print("  Weighted ranking will be applied in Phase 4 (Query stage).")


# ─────────────────────────────────────────────
# آماده‌سازی اسناد برای Bulk Indexing
# ─────────────────────────────────────────────

def generate_bulk_actions(docs: list[dict]):
    """
    یک generator است که اسناد را یکی‌یکی برای helpers.bulk آماده می‌کند.
    استفاده از generator به جای لیست — مصرف حافظه کمتر
    """
    for doc in docs:
        yield {
            # عملیات: ایندکس کردن سند
            "_index": INDEX_NAME,
            # محتوای سند
            "_source": {
                "url":             doc.get("url", ""),
                "date":            doc.get("date", ""),
                "category":        doc.get("category", ""),
                "title":           doc.get("title", ""),
                "title_tokens":    doc.get("title_tokens", ""),
                "headings":        doc.get("headings", ""),
                "headings_tokens": doc.get("headings_tokens", ""),
                "body":            doc.get("body", ""),
                "body_tokens":     doc.get("body_tokens", ""),
                "snippet":         doc.get("snippet", ""),
            }
        }


# ─────────────────────────────────────────────
# ایندکس‌گذاری اسناد
# ─────────────────────────────────────────────

def index_documents(es: Elasticsearch, docs: list[dict]) -> None:
    """
    تمام اسناد را با helpers.bulk به‌صورت دسته‌ای ایندکس می‌کند.
    Bulk indexing بسیار سریع‌تر از ایندکس کردن یکی‌یکی است.

    پارامترها:
    - chunk_size: تعداد سندی که در هر درخواست HTTP ارسال می‌شود
    - raise_on_error: اگر True باشد، در صورت خطا متوقف می‌شود
    """
    print(f"\n⟳ در حال ایندکس‌گذاری {len(docs)} سند...")

    success_count, error_count = helpers.bulk(
        es,
        generate_bulk_actions(docs),
        chunk_size=50,          # هر بار ۵۰ سند ارسال کن
        raise_on_error=False,   # در صورت خطا، بقیه را ادامه بده
        stats_only=True         # فقط تعداد موفق/ناموفق را برگردان
    )

    print("✓ Indexing completed:")
    print(f"  Successful: {success_count} documents")
    print(f"  Failed:     {error_count} documents")

    # refresh برای قابل جستجو شدن فوری اسناد
    es.indices.refresh(index=INDEX_NAME)
    print("  ✓ Index refreshed.")



# ─────────────────────────────────────────────
# بررسی نتیجه ایندکس‌گذاری
# ─────────────────────────────────────────────

def verify_index(es: Elasticsearch) -> None:
    """
    بررسی می‌کند که ایندکس‌گذاری درست انجام شده.
    تعداد اسناد و اطلاعات ایندکس را نمایش می‌دهد.
    """
    # تعداد کل اسناد در ایندکس
    count_result = es.count(index=INDEX_NAME)
    total_docs = count_result["count"]

    # اطلاعات ایندکس
    stats = es.indices.stats(index=INDEX_NAME)
    size_bytes = stats["indices"][INDEX_NAME]["total"]["store"]["size_in_bytes"]
    size_kb = size_bytes / 1024

    print(f"\n── Index Statistics '{INDEX_NAME}' ──────────────")
    print(f"  Documents: {total_docs}")
    print(f"  Size:      {size_kb:.1f} KB")
    print(f"  Kibana:    http://localhost:5601")
    print(f"  API:       {ES_HOST}/{INDEX_NAME}/_search")
    print("─" * 45)

    # نمایش یک سند نمونه
    sample = es.search(
        index=INDEX_NAME,
        body={"query": {"match_all": {}}, "size": 1}
    )
    if sample["hits"]["hits"]:
        doc = sample["hits"]["hits"][0]["_source"]
        print("\n── Sample Indexed Document ──────────────────")
        print(f"  Title:    {doc.get('title', '')[:60]}")
        print(f"  Category: {doc.get('category', '')}")
        print(f"  Snippet:  {doc.get('snippet', '')[:80]}...")
        print("─" * 45)


# ─────────────────────────────────────────────
# نقطه ورود اصلی
# ─────────────────────────────────────────────

def run_indexing():
    """
    تابع اصلی که تمام مراحل فاز سوم را اجرا می‌کند:
    ۱. اتصال به Elasticsearch
    ۲. ساخت ایندکس با Mapping سفارشی
    ۳. بارگذاری داده‌های پیش‌پردازش‌شده
    ۴. Bulk indexing اسناد
    ۵. بررسی نتیجه
    """
    print("=" * 60)
    print("  Phase 3: Elasticsearch Indexing")
    print("=" * 60)

    # ── مرحله ۱: اتصال ──────────────────────────
    try:
        es = connect_to_elasticsearch()
    except ConnectionError as e:
        print(e)
        return

    # ── مرحله ۲: ساخت ایندکس ────────────────────
    create_index(es)

    # ── مرحله ۳: بارگذاری داده‌ها ───────────────
    print(f"\n⟳ Loading '{INPUT_FILE}' ...")

    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            docs = json.load(f)

        print(f"✓ {len(docs)} documents loaded.")
    except FileNotFoundError:
        print(f"✗ Error: '{INPUT_FILE}' not found.")
        print("  Please run Phase 2 first.")
        return

    # ── مرحله ۴: ایندکس‌گذاری ───────────────────
    index_documents(es, docs)

    # ── مرحله ۵: بررسی نتیجه ────────────────────
    verify_index(es)

    print("\n✓ Phase 3 completed successfully!")


if __name__ == "__main__":
    run_indexing()