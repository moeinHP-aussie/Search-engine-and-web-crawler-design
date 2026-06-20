<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Algorithm-BM25%20%7C%20BFS-red.svg" alt="Algorithm">
  <img src="https://img.shields.io/badge/Domain-Information%20Retrieval%20%7C%20NLP-cyan.svg" alt="Domain">
  <img src="https://img.shields.io/badge/Database-Elasticsearch%209.4-orange.svg" alt="Elasticsearch">
  <img src="https://img.shields.io/badge/Scraping-BeautifulSoup4-yellow.svg" alt="Scraping">
  <img src="https://img.shields.io/badge/NLP-Hazm-green.svg" alt="NLP">
</p>

<h3 align="center">
  <a href="#-فارسی">🇮🇷 فارسی</a> &bull; 
  <a href="#-english">EN English</a>
</h3>

---

## 🇮🇷 فارسی

# 🔍 موتور جستجوی فارسی سایت zoomit.ir
این پروژه یک موتور جستجوی کوچک و هوشمند برای مقالات سایت **زومیت** است که تمام مراحل بازیابی اطلاعات، از جمع‌آوری داده‌های خام تا رتبه‌بندی نتایج جستجو را پوشش می‌دهد.

### 🏗️ معماری سیستم (فازهای اجرایی)
این سامانه از ۴ فاز اصلی و ماژولار تشکیل شده است:
1. **خزنده وب (Web Crawler):** استفاده از الگوریتم BFS برای پیمایش سطح‌به‌سطح سایت و استخراج داده‌ها با `BeautifulSoup4`.
2. **پیش‌پردازش زبان طبیعی (NLP Preprocessor):** تمیزکاری، نرمال‌سازی، توکن‌سازی، حذف Stop-words و ریشه‌یابی (Lemmatization) کلمات فارسی با استفاده از کتابخانه `Hazm`.
3. **ایندکسر (Indexer):** استفاده از **Elasticsearch 9.4** برای ساخت Mapping سفارشی و ایندکس‌گذاری گروهی (Bulk Indexing) اسناد.
4. **موتور جستجو (Search Engine):** پیاده‌سازی الگوریتم **BM25** برای رتبه‌بندی هوشمند نتایج بر اساس ارتباط معنایی و فرکانس کلمات.

### ✨ ویژگی‌های کلیدی پردازش و جستجو
* **وزن‌دهی داینامیک فیلدها (Field Boosting):** اعمال وزن بیشتر برای کلمات یافت‌شده در عنوان (ضریب ۳) و هدینگ‌ها (ضریب ۲) نسبت به متن اصلی.
* **جستجوی تقریبی (Fuzzy Search):** پشتیبانی از اشتباهات تایپی کاربران در زمان جستجو.
* **هایلایت نتایج (Highlighting):** علامت‌گذاری کلمات کلیدی در خلاصه متن (Snippet) خروجی.
* **رابط گرافیکی (GUI):** دارای محیط کاربری برای نمایش خوانا و جذاب نتایج.

---

## EN English

# 🔍 Zoomit.ir Persian Search Engine
This project is a compact, intelligent search engine built for **Zoomit** articles. It covers the entire Information Retrieval (IR) pipeline, from crawling raw web data to ranking search results.

### 🏗️ System Architecture (Execution Phases)
The system is divided into 4 modular phases:
1. **Web Crawler:** Implements a Breadth-First Search (BFS) algorithm to crawl pages and extract DOM elements using `BeautifulSoup4`.
2. **NLP Preprocessor:** Cleans, normalizes, tokenizes, removes stop-words, and lemmatizes Persian text using the `Hazm` library.
3. **Indexer:** Utilizes **Elasticsearch 9.4** to create custom Persian mappings and index documents efficiently via Bulk Indexing.
4. **Search Engine:** Implements the **BM25** ranking algorithm to score and retrieve the most relevant documents based on user queries.

### ✨ Key Features
* **Dynamic Field Boosting:** Prioritizes matches found in the document `title` (weight x3) and `headings` (weight x2) over the regular body text.
* **Fuzzy Search:** Handles common user typos and spelling mistakes during the search.
* **Text Highlighting:** Automatically highlights the queried keywords within the generated snippets.
* **Graphical User Interface (GUI):** Includes a user-friendly interface to display structured search results.
