"""
پروژه عملی دوم — بازیابی اطلاعات و جستجوی وب
رابط گرافیکی موتور جستجو با PyQt6
طراحی: تاریک، مدرن، شبیه موتورهای جستجوی واقعی
"""

import sys
import webbrowser
from elasticsearch import Elasticsearch
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QScrollArea, QFrame, QSpinBox, QComboBox,
    QGraphicsDropShadowEffect, QSizePolicy, QProgressBar
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QTimer, QUrl
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QIcon,
    QLinearGradient, QPainter, QPixmap, QCursor
)


# ─────────────────────────────────────────────
# ثابت‌های پروژه
# ─────────────────────────────────────────────

ES_HOST    = "http://localhost:9200"
INDEX_NAME = "zoomit_articles"

# وزن فیلدها — مشابه فاز چهارم
SEARCH_FIELDS = [
    "title^3", "title_tokens^3",
    "headings^2", "headings_tokens^2",
    "body^1", "body_tokens^1",
]

# ─────────────────────────────────────────────
# پالت رنگی
# ─────────────────────────────────────────────

COLORS = {
    "bg_dark":      "#0d1117",   # پس‌زمینه اصلی — تقریباً مشکی
    "bg_card":      "#161b22",   # کارت‌های نتیجه
    "bg_input":     "#21262d",   # فیلد جستجو
    "bg_hover":     "#1c2128",   # hover کارت
    "accent":       "#e94560",   # قرمز-گلابی — رنگ اصلی برند
    "accent_dark":  "#c73652",   # hover دکمه
    "accent_glow":  "#e9456040", # سایه اکسنت
    "text_primary": "#e6edf3",   # متن اصلی
    "text_secondary":"#8b949e",  # متن ثانوی
    "text_muted":   "#484f58",   # متن کم‌رنگ
    "border":       "#30363d",   # حاشیه کارت‌ها
    "highlight":    "#e94560",   # کلمات highlight‌شده
    "score_high":   "#3fb950",   # امتیاز بالا
    "score_mid":    "#d29922",   # امتیاز متوسط
    "score_low":    "#8b949e",   # امتیاز پایین
    "category_bg":  "#21262d",   # پس‌زمینه تگ دسته‌بندی
    "link":         "#58a6ff",   # رنگ لینک
}


# ─────────────────────────────────────────────
# تِرد جستجو (برای جلوگیری از قفل شدن UI)
# ─────────────────────────────────────────────

class SearchThread(QThread):
    """
    جستجو را در یک thread جداگانه اجرا می‌کند
    تا رابط گرافیکی در حین جستجو منجمد نشود.
    """
    # سیگنال‌هایی که بعد از جستجو ارسال می‌شوند
    results_ready  = pyqtSignal(list)   # نتایج آماده شد
    error_occurred = pyqtSignal(str)    # خطا رخ داد

    def __init__(self, query_text: str, k: int):
        super().__init__()
        self.query_text = query_text
        self.k = k

    def run(self):
        """در این متد جستجو انجام می‌شود"""
        try:
            es = Elasticsearch(ES_HOST)
            if not es.ping():
                self.error_occurred.emit("اتصال به Elasticsearch برقرار نشد.")
                return

            # ساخت query با وزن‌دهی فیلدها
            query_body = {
                "query": {
                    "multi_match": {
                        "query":       self.query_text,
                        "fields":      SEARCH_FIELDS,
                        "type":        "best_fields",
                        "tie_breaker": 0.3,
                        "fuzziness":   "AUTO",
                    }
                },
                "size": self.k,
                "highlight": {
                    "fields": {
                        "body":  {"fragment_size": 250, "number_of_fragments": 1},
                        "title": {"number_of_fragments": 0},
                    },
                    "pre_tags":  ["<<<"],
                    "post_tags": [">>>"],
                }
            }

            response = es.search(index=INDEX_NAME, body=query_body)
            hits = response["hits"]["hits"]

            results = []
            for hit in hits:
                source    = hit["_source"]
                score     = hit["_score"]
                highlight = hit.get("highlight", {})

                # انتخاب بهترین snippet
                if "body" in highlight:
                    snippet = highlight["body"][0]
                else:
                    snippet = source.get("snippet", "")[:250]

                results.append({
                    "title":    source.get("title", "بدون عنوان"),
                    "snippet":  snippet,
                    "score":    round(score, 2),
                    "url":      source.get("url", ""),
                    "category": source.get("category", ""),
                    "date":     source.get("date", "")[:10] if source.get("date") else "",
                })

            self.results_ready.emit(results)

        except Exception as e:
            self.error_occurred.emit(str(e))


# ─────────────────────────────────────────────
# ویجت کارت نتیجه
# ─────────────────────────────────────────────

class ResultCard(QFrame):
    """
    یک کارت زیبا برای نمایش هر نتیجه جستجو.
    شامل: عنوان، snippet، امتیاز، دسته‌بندی، تاریخ، و لینک.
    """

    def __init__(self, result: dict, rank: int, parent=None):
        super().__init__(parent)
        self.url = result["url"]
        self._setup_ui(result, rank)
        self._setup_style()

    def _setup_style(self):
        """استایل کارت — حاشیه و پس‌زمینه تاریک"""
        self.setStyleSheet(f"""
            ResultCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 0px;
            }}
            ResultCard:hover {{
                background-color: {COLORS['bg_hover']};
                border: 1px solid {COLORS['accent']};
            }}
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # سایه ظریف زیر کارت
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def _setup_ui(self, result: dict, rank: int):
        """ساخت محتوای کارت"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # ── ردیف بالا: رتبه + عنوان + امتیاز ────────
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # شماره رتبه
        rank_label = QLabel(f"#{rank}")
        rank_label.setFixedWidth(32)
        rank_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        rank_label.setStyleSheet(f"color: {COLORS['accent']}; background: transparent;")
        rank_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(rank_label)

        # عنوان
        title_text = result["title"]
        title_label = QLabel(title_text)
        title_label.setFont(QFont("Tahoma", 12, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        title_label.setWordWrap(True)
        title_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        top_row.addWidget(title_label, stretch=1)

        # امتیاز — رنگ بر اساس مقدار
        score = result["score"]
        if score >= 25:
            score_color = COLORS["score_high"]
        elif score >= 10:
            score_color = COLORS["score_mid"]
        else:
            score_color = COLORS["score_low"]

        score_label = QLabel(f"⭐ {score}")
        score_label.setFont(QFont("Segoe UI", 10))
        score_label.setStyleSheet(
            f"color: {score_color}; background: {COLORS['bg_input']};"
            f"padding: 3px 10px; border-radius: 10px;"
        )
        score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_row.addWidget(score_label)

        layout.addLayout(top_row)

        # ── لینک ─────────────────────────────────────
        if result["url"]:
            url_short = result["url"].replace("https://", "").replace("www.", "")
            if len(url_short) > 70:
                url_short = url_short[:67] + "..."
            url_label = QLabel(f"🔗 {url_short}")
            url_label.setFont(QFont("Segoe UI", 9))
            url_label.setStyleSheet(f"color: {COLORS['link']}; background: transparent;")
            url_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            layout.addWidget(url_label)

        # ── Snippet با highlight ──────────────────────
        snippet_raw = result["snippet"]
        # تبدیل تگ‌های highlight به HTML
        snippet_html = (
            snippet_raw
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("<<<", f'<span style="color:{COLORS["accent"]}; font-weight:bold;">')
            .replace(">>>", "</span>")
        )

        snippet_label = QLabel()
        snippet_label.setText(f'<span style="color:{COLORS["text_secondary"]};">{snippet_html}</span>')
        snippet_label.setFont(QFont("Tahoma", 10))
        snippet_label.setWordWrap(True)
        snippet_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        snippet_label.setTextFormat(Qt.TextFormat.RichText)
        snippet_label.setStyleSheet("background: transparent;")
        layout.addWidget(snippet_label)

        # ── ردیف پایین: دسته‌بندی + تاریخ ───────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)
        bottom_row.addStretch()  # برای راست‌چین بودن

        if result["category"]:
            cat_label = QLabel(f"🏷 {result['category']}")
            cat_label.setFont(QFont("Segoe UI", 9))
            cat_label.setStyleSheet(
                f"color: {COLORS['text_secondary']};"
                f"background: {COLORS['category_bg']};"
                f"padding: 2px 8px; border-radius: 6px;"
                f"border: 1px solid {COLORS['border']};"
            )
            bottom_row.addWidget(cat_label)

        if result["date"]:
            date_label = QLabel(f"📅 {result['date']}")
            date_label.setFont(QFont("Segoe UI", 9))
            date_label.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
            bottom_row.addWidget(date_label)

        if result["category"] or result["date"]:
            layout.addLayout(bottom_row)

    def mousePressEvent(self, event):
        """با کلیک روی کارت، لینک در مرورگر باز می‌شود"""
        if self.url:
            webbrowser.open(self.url)
        super().mousePressEvent(event)


# ─────────────────────────────────────────────
# پنجره اصلی
# ─────────────────────────────────────────────

class SearchWindow(QMainWindow):
    """پنجره اصلی موتور جستجو"""

    def __init__(self):
        super().__init__()
        self.search_thread = None
        self._setup_window()
        self._setup_ui()
        self._check_connection()

    def _setup_window(self):
        """تنظیمات پنجره"""
        self.setWindowTitle("موتور جستجوی فارسی زومیت")
        self.setMinimumSize(900, 700)
        self.resize(1100, 800)

        # وسط صفحه نمایش
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width()  - 1100) // 2
        y = (screen.height() - 800)  // 2
        self.move(x, y)

        # پس‌زمینه اصلی تاریک
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLORS['bg_dark']}; }}")

    def _setup_ui(self):
        """ساخت رابط کاربری"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── هدر ──────────────────────────────────────
        main_layout.addWidget(self._build_header())

        # ── نوار جستجو ───────────────────────────────
        main_layout.addWidget(self._build_search_bar())

        # ── نوار وضعیت ───────────────────────────────
        self.status_bar = self._build_status_bar()
        main_layout.addWidget(self.status_bar)

        # ── نوار بارگذاری ────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # حالت نامحدود
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: transparent;
                border: none;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['accent']}, stop:1 #ff6b6b);
                border-radius: 2px;
            }}
        """)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # ── ناحیه نتایج ──────────────────────────────
        self.results_area = self._build_results_area()
        main_layout.addWidget(self.results_area, stretch=1)

    def _build_header(self) -> QWidget:
        """هدر بالای صفحه با لوگو"""
        header = QWidget()
        header.setFixedHeight(100)
        header.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['bg_card']}, stop:1 {COLORS['bg_dark']});
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(30, 0, 30, 0)

        # لوگو + نام
        logo_layout = QVBoxLayout()
        logo_layout.setSpacing(2)

        title_label = QLabel("🔍 موتور جستجوی زومیت")
        title_label.setFont(QFont("Tahoma", 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            background: transparent;
        """)
        title_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        subtitle_label = QLabel("جستجو در ۲۰۰ مقاله فناوری فارسی | Elasticsearch + BM25")
        subtitle_label.setFont(QFont("Segoe UI", 9))
        subtitle_label.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        subtitle_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        logo_layout.addWidget(title_label)
        logo_layout.addWidget(subtitle_label)
        logo_layout.addStretch()

        layout.addStretch()
        layout.addLayout(logo_layout)

        # نشانگر وضعیت اتصال
        self.connection_indicator = QLabel("● متصل")
        self.connection_indicator.setFont(QFont("Segoe UI", 10))
        self.connection_indicator.setStyleSheet(
            f"color: {COLORS['score_high']}; background: transparent;"
        )
        layout.addWidget(self.connection_indicator)

        return header

    def _build_search_bar(self) -> QWidget:
        """نوار جستجوی اصلی"""
        container = QWidget()
        container.setStyleSheet(f"background-color: {COLORS['bg_dark']};")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(60, 25, 60, 15)
        layout.setSpacing(12)

        # ── فیلد جستجو + دکمه ────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        # فیلد ورودی
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو در مقالات فناوری زومیت...")
        self.search_input.setFont(QFont("Tahoma", 13))
        self.search_input.setFixedHeight(52)
        self.search_input.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 26px;
                padding: 0 22px;
                selection-background-color: {COLORS['accent']};
            }}
            QLineEdit:focus {{
                border: 1.5px solid {COLORS['accent']};
                background-color: {COLORS['bg_card']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_muted']};
            }}
        """)
        self.search_input.returnPressed.connect(self._do_search)

        # دکمه جستجو
        self.search_btn = QPushButton("جستجو")
        self.search_btn.setFont(QFont("Tahoma", 12, QFont.Weight.Bold))
        self.search_btn.setFixedSize(110, 52)
        self.search_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.search_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['accent']}, stop:1 #ff6b6b);
                color: white;
                border: none;
                border-radius: 26px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['accent_dark']}, stop:1 {COLORS['accent']});
            }}
            QPushButton:pressed {{
                background-color: {COLORS['accent_dark']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['text_muted']};
            }}
        """)
        self.search_btn.clicked.connect(self._do_search)

        # سایه روی فیلد جستجو
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(COLORS["accent"]).darker(200))
        shadow.setOffset(0, 4)
        self.search_input.setGraphicsEffect(shadow)

        search_row.addWidget(self.search_btn)
        search_row.addWidget(self.search_input)

        # ── تنظیمات: تعداد نتایج + دکمه پاک ─────────
        options_row = QHBoxLayout()
        options_row.setSpacing(15)
        options_row.addStretch()

        # برچسب تعداد نتایج
        k_label = QLabel("تعداد نتایج:")
        k_label.setFont(QFont("Tahoma", 10))
        k_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent;")

        # spinner تعداد نتایج
        self.k_spinner = QSpinBox()
        self.k_spinner.setRange(1, 20)
        self.k_spinner.setValue(10)
        self.k_spinner.setFixedSize(65, 30)
        self.k_spinner.setStyleSheet(f"""
            QSpinBox {{
                background: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 0 5px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: {COLORS['border']};
                border-radius: 3px;
            }}
        """)

        # دکمه پاک کردن
        clear_btn = QPushButton("پاک کردن")
        clear_btn.setFont(QFont("Tahoma", 9))
        clear_btn.setFixedHeight(30)
        clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['accent']};
                color: {COLORS['accent']};
            }}
        """)
        clear_btn.clicked.connect(self._clear_results)

        options_row.addWidget(clear_btn)
        options_row.addWidget(k_label)
        options_row.addWidget(self.k_spinner)

        layout.addLayout(search_row)
        layout.addLayout(options_row)

        return container

    def _build_status_bar(self) -> QLabel:
        """نوار وضعیت زیر جستجو"""
        label = QLabel("")
        label.setFont(QFont("Segoe UI", 9))
        label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            background: transparent;
            padding: 2px 65px;
        """)
        label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        label.setAlignment(Qt.AlignmentFlag.AlignRight)
        return label

    def _build_results_area(self) -> QScrollArea:
        """ناحیه اسکرول‌پذیر برای نمایش نتایج"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['bg_dark']};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {COLORS['bg_card']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        # ویجت داخلی که نتایج در آن رندر می‌شوند
        self.results_widget = QWidget()
        self.results_widget.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setContentsMargins(60, 15, 60, 30)
        self.results_layout.setSpacing(12)
        self.results_layout.addStretch()

        # پیام اولیه (قبل از اولین جستجو)
        self._show_welcome_message()

        scroll.setWidget(self.results_widget)
        return scroll

    def _show_welcome_message(self):
        """پیام خوش‌آمد قبل از جستجو"""
        welcome = QLabel("🔍 یک کلمه یا عبارت فارسی جستجو کنید")
        welcome.setFont(QFont("Tahoma", 14))
        welcome.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        hint = QLabel("مثال:  هوش مصنوعی  |  گوشی سامسونگ  |  بهترین لپ‌تاپ")
        hint.setFont(QFont("Tahoma", 10))
        hint.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.results_layout.insertWidget(0, welcome)
        self.results_layout.insertWidget(1, hint)

    def _check_connection(self):
        """بررسی اتصال به Elasticsearch هنگام راه‌اندازی"""
        try:
            es = Elasticsearch(ES_HOST)
            if es.ping():
                count = es.count(index=INDEX_NAME)["count"]
                self.connection_indicator.setText(f"● {count:,} سند ایندکس‌شده")
                self.connection_indicator.setStyleSheet(
                    f"color: {COLORS['score_high']}; background: transparent;"
                )
            else:
                raise Exception("ping failed")
        except Exception:
            self.connection_indicator.setText("● عدم اتصال به Elasticsearch")
            self.connection_indicator.setStyleSheet(
                f"color: {COLORS['accent']}; background: transparent;"
            )

    # ── منطق جستجو ───────────────────────────────

    def _do_search(self):
        """شروع جستجو"""
        query = self.search_input.text().strip()
        if not query:
            self.search_input.setFocus()
            return

        # غیرفعال کردن دکمه در حین جستجو
        self.search_btn.setEnabled(False)
        self.search_btn.setText("...")
        self.progress_bar.show()
        self.status_bar.setText(f"در حال جستجو برای «{query}»...")

        # پاک کردن نتایج قبلی
        self._clear_results_widgets()

        # شروع thread جستجو
        k = self.k_spinner.value()
        self.search_thread = SearchThread(query, k)
        self.search_thread.results_ready.connect(self._on_results_ready)
        self.search_thread.error_occurred.connect(self._on_error)
        self.search_thread.start()

    def _on_results_ready(self, results: list):
        """نمایش نتایج بعد از اتمام جستجو"""
        self.search_btn.setEnabled(True)
        self.search_btn.setText("جستجو")
        self.progress_bar.hide()

        query = self.search_input.text().strip()
        count = len(results)

        if count == 0:
            self.status_bar.setText(f"نتیجه‌ای برای «{query}» پیدا نشد.")
            no_result = QLabel("😕 نتیجه‌ای پیدا نشد — کلمات دیگری امتحان کنید")
            no_result.setFont(QFont("Tahoma", 13))
            no_result.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
            no_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_result.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.results_layout.insertWidget(0, no_result)
        else:
            self.status_bar.setText(
                f"  {count} نتیجه برای «{query}» یافت شد"
                f"  (بالاترین امتیاز: {results[0]['score']})"
            )
            # اضافه کردن کارت‌ها با تأخیر کم (برای انیمیشن ورود)
            for i, result in enumerate(results):
                card = ResultCard(result, i + 1)
                self.results_layout.insertWidget(i, card)
                # اسکرول به بالا بعد از اولین کارت
                if i == 0:
                    QTimer.singleShot(50, lambda: self.results_area.verticalScrollBar().setValue(0))

    def _on_error(self, error_msg: str):
        """نمایش خطا"""
        self.search_btn.setEnabled(True)
        self.search_btn.setText("جستجو")
        self.progress_bar.hide()
        self.status_bar.setText(f"خطا: {error_msg}")

        err_label = QLabel(f"⚠️ {error_msg}")
        err_label.setFont(QFont("Tahoma", 11))
        err_label.setStyleSheet(f"color: {COLORS['accent']}; background: transparent;")
        err_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        err_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.results_layout.insertWidget(0, err_label)

    def _clear_results_widgets(self):
        """پاک کردن تمام کارت‌های نتیجه از ناحیه نمایش"""
        while self.results_layout.count() > 1:  # ۱ برای stretch
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_results(self):
        """پاک کردن جستجو و نتایج"""
        self.search_input.clear()
        self._clear_results_widgets()
        self.status_bar.setText("")
        self._show_welcome_message()
        self.search_input.setFocus()


# ─────────────────────────────────────────────
# نقطه ورود اصلی
# ─────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("موتور جستجوی زومیت")

    # تنظیم فونت پیش‌فرض برنامه
    default_font = QFont("Tahoma", 10)
    app.setFont(default_font)

    # فعال کردن High DPI
    app.setHighDpiPixmaps = True

    window = SearchWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
