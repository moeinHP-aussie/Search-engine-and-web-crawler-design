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

# 🔍 سامانه هوشمند بازیابی اطلاعات و موتور جستجوی مقالات زومیت

این پروژه یک پیاده‌سازی جامع و ساختاریافته از **سیستم‌های بازیابی اطلاعات (Information Retrieval)** است که به صورت اختصاصی برای خزش، پیش‌پردازش، نمایه سازی و جستجوی مقالات فناوری وب‌سایت **زومیت** طراحی شده است. معماری سیستم به صورت ماژولار و در ۴ فاز مستقل پیاده‌سازی شده تا بالاترین سطح هماهنگی بین بخش‌های خزش داده و رتبه‌بندی نتایج حاصل شود.

---

### 🗺️ نمودار معماری سیستم (Architecture Diagram)
در نمودار زیر، جریان حرکت داده از وب‌سایت زومیت تا رسیدن به ایندکس‌های الستیک‌سرچ و در نهایت پاسخ به کوئری کاربر به تصویر کشیده شده است:

<p align="center">
  <img src="architecture.png" alt="System Architecture Diagram" width="80%">
</p>

---

### 🏗️ تشریح دقیق فازهای اجرایی پروژه

#### فاز ۱: خزنده وب هوشمند (Web Crawler)
مأموریت این فاز، استخراج داده‌های ساختاریافته از دل صفحات HTML زومیت است.
* **مکانیزم پیمایش:** پیاده‌سازی الگوریتم **BFS (جستجوی سطح اول)** با استفاده از یک صف (`Queue`) برای مدیریت آدرس‌ها. برای جلوگیری از چرخه بی‌انتهای خزش، تمام لینک‌های دیده‌شده در یک ساختار داده `Set` ذخیره می‌شوند.
* **استخراج داده (Parsing):** با استفاده از کتابخانه `BeautifulSoup4` و تحلیل ساختار DOM سایت زومیت، فیلدهای حیاتی شامل: عنوان اصلی (`title`)، هدینگ‌ها (`headings`)، بدنه مقاله (`body`) و آدرس صفحه (`url`) به صورت تفکیک‌شده استخراج می‌گردند.

#### فاز ۲: خط لوله پیش‌پردازش متن (NLP Preprocessing Pipeline)
زبان فارسی به دلیل ویژگی‌های ساختاری (مثل تنوع پیشوندها/پسوندها و نیم‌فاصله‌ها) نیازمند پردازش دقیق است. این فاز با تکیه بر کتابخانه `Hazm` مراحل زیر را طی می‌کند:
* **نرمال‌سازی (Normalization):** اصلاح کاراکترهای عربی (ي/ک) به فارسی (ی/ک)، تنظیم نیم‌فاصله‌ها و یکسان‌سازی علائم نگارشی.
* **توکن‌سازی (Tokenization):** شکستن متن به واحدهای معنادار (کلمات).
* **حذف کلمات توقف (Stop-words Removal):** فیلتر کردن کلمات پر تکرار و بی‌ارزش (مانند: از، به، که، در) بر اساس لیست سفارشی‌سازی شده.
* **ریشه‌یابی و بن‌واژه‌سازی (Lemmatization & Stemming):** کاهش کلمات به ریشه اصلی (مثلاً "می‌نویسند" -> "نوشت") جهت افزایش نرخ تطابق در زمان جستجو.

#### فاز ۳: پایگاه داده و ایندکسر (Elasticsearch Integration)
بهره‌گیری از **Elasticsearch 9.4** به عنوان هسته ذخیره‌سازی و موتور نمایه سازی اسناد.
* **طراحی نگاشت سفارشی (Custom Mapping):** فیلدها با ساختار مشخص تعریف شده‌اند. برای مثال، فیلد `url` به صورت `keyword` (بدون تحلیل متنی) و فیلدهای متنی به صورت `text` با تحلیلگرهای منطبق تعریف شده‌اند.
* **درج انبوه (Bulk Indexing):** اسناد پردازش‌شده فاز قبل، به جای درج تک‌به‌تک، در دسته‌های بهینه (Bulk) به الستیک‌سرچ ارسال می‌شوند تا کارایی و سرعت سیستم به حداکثر برسد.

#### فاز ۴: موتور جستجو و الگوریتم رتبه‌بندی (Search Engine & Scoring)
این فاز قلب تپنده پروژه است که وظیفه سنجش میزان شباهت کوئری کاربر با اسناد ایندکس‌شده را بر عهده دارد.
* **الگوریتم رتبه‌بندی BM25:** سیستم بر پایه فرمول ریاضیاتی BM25 کار می‌کند که فاکتورهای فرکانس اصطلاح (TF) و معکوس فرکانس سند (IDF) را در کنار جریمه طول سند بهینه‌سازی می‌کند.
* **وزن‌دهی پویا به فیلدها (Field Boosting):** از آنجا که در نسخه ۹ الستیک‌سرچ، پارامتر `boost` از بخش Mapping حذف شده است، منطق وزن‌دهی به بخش طراحی **Search Query** منتقل شد. در این مدل، کلمات یافت شده در **عنوان با ضریب ۳** و در **هدینگ‌ها با ضریب ۲** نسبت به بدنه اصلی متن امتیازدهی می‌شوند:
  $$\text{Score} = (3 \times \text{Score}_{\text{title}}) + (2 \times \text{Score}_{\text{headings}}) + (1 \times \text{Score}_{\text{body}})$$
* **جستجوی فازی (Fuzzy Search):** تنظیم پارامتر `fuzziness` برای پوشش و تصحیح خطاهای تایپی احتمالی کاربران در محیط‌های عملیاتی.
* **هایلایت و تکه‌چسبانی (Highlighting & Snippet Generation):** استخراج بخش‌های مرتبط سند که کلمه کلیدی در آن‌ها قرار دارد و هایلایت کردن آن‌ها با تگ‌های متنی جهت نمایش بهتر به کاربر.
* **رابط کاربری گرافیکی (GUI):** طراحی یک محیط بصری برای ورود کلمات کلیدی و نمایش نتایج رتبه‌بندی شده همراه با خلاصه متنی و لینک منبع.

---

## en English

# 🔍 Zoomit Persian Articles Search Engine & IR System

This project is a comprehensive and structured implementation of **Information Retrieval (IR)** principles, custom-built to crawl, preprocess, index, and search technology articles from the **Zoomit** website. The architecture is completely modular, split into 4 independent phases to ensure seamless data flow and highly accurate ranking.

---

### 🏗️ In-Depth Architectural Breakdown

#### Phase 1: Smart Web Crawler
The primary objective of this phase is to fetch and extract structured data from Zoomit's HTML pages.
* **Traversal Strategy:** Implements a **Breadth-First Search (BFS)** algorithm using a synchronized `Queue` to manage URLs. To prevent infinite loops and redundant network requests, visited URLs are tracked globally using a `Set`.
* **DOM Parsing:** Utilizing `BeautifulSoup4`, it parses the web documents and isolates critical fields: Title (`title`), Headings (`headings`), Document Body (`body`), and Source Link (`url`).

#### Phase 2: NLP Preprocessing Pipeline
Due to the morphological complexities of the Persian language (e.g., affixes, spacing, and zero-width non-joiners), text requires intensive cleaning via the `Hazm` library:
* **Normalization:** Standardizes Arabic characters to Persian (e.g., replacing ي with ی), corrects half-spaces (نیم‌فاصله), and cleans punctuation symbols.
* **Tokenization:** Breaks down raw sentences into individual word tokens.
* **Stop-words Removal:** Eliminates high-frequency, low-meaning words (such as "از", "به", "در") using a refined custom list.
* **Lemmatization & Stemming:** Reduces inflected or derived words to their base dictionary form (e.g., transforming verbs into their root infinity/past stem) to boost recall.

#### Phase 3: Database & Bulk Indexing
Leverages **Elasticsearch 9.4** to provide high-performance text search capabilities.
* **Custom Mapping Design:** Document schemas are explicitly mapped. Fields like `url` are treated as exact `keyword` types, whereas textual fields are mapped as `text` to undergo deep lexical analysis.
* **Bulk Operation:** To maximize indexing throughput and minimize I/O overhead, processed documents are transmitted using bulk APIs rather than individual inserts.

#### Phase 4: Search Engine & Scoring Logic
The retrieval engine evaluates and scores the semantic and structural relevance of documents against user queries.
* **BM25 Ranking Model:** Employs the probabilistic BM25 model, dynamically balancing Term Frequency (TF) and Inverse Document Frequency (IDF) while normalizing document length.
* **Query-Level Field Boosting:** Since explicit field-level boosting was deprecated within Elasticsearch 9 mapping definitions, the weighting logic was successfully shifted into the dynamic **Search Query compilation**. The scoring logic applies heavy weights to early-match structures:
  $$\text{Score} = (3 \times \text{Score}_{\text{title}}) + (2 \times \text{Score}_{\text{headings}}) + (1 \times \text{Score}_{\text{body}})$$
* **Fuzzy Queries:** Configures `fuzziness` thresholds to gracefully handle user typos and spelling variations.
* **Highlighters & Snippets:** Extracts short context snippets surrounding the matching query terms, wrapping them in visual markers for enhanced UI presentation.
* **Graphical User Interface (GUI):** A clean UI layer allowing users to input keywords, trigger queries, and inspect scored, highlighted results with deep links back to the original articles.
