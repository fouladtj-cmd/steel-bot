"""
ربات روزانه کانال فولاد تهران جنوب
اجرا:  python steel_bot.py [morning|evening|all]
  morning = تقویم + اخبار آهن و فولاد
  evening = آمار و تحلیل بازار آهن
"""
import os
import sys
import datetime
from zoneinfo import ZoneInfo

import jdatetime
import requests

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL = os.environ["TELEGRAM_CHANNEL"]  # مثلا @steeltj_channel
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

WEEKDAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]

SYSTEM = (
    "تو دستیار تحریریه کانال تلگرام «فولاد تهران جنوب» (تامین و عرضه میلگرد، ورق، لوله و پروفیل) هستی. "
    "فقط فارسی روان و حرفه‌ای بنویس. برای یافتن اطلاعات از جستجوی وب استفاده کن. "
    "هیچ عدد، قیمت یا خبری را از خودت نساز؛ اگر داده معتبر پیدا نشد صریح بنویس «داده معتبر یافت نشد». "
    "برای هر خبر یا عدد منبعش را (نام سایت) ذکر کن. "
    "قالب خروجی: متن ساده تلگرام؛ فقط از تگ <b> برای تیتر استفاده کن. "
    "از مارک‌داون، جدول و لینک طولانی استفاده نکن. کل پیام کمتر از ۳۰۰۰ کاراکتر باشد. "
    "توصیه خرید یا فروش نکن."
)


def today_info():
    now = datetime.datetime.now(ZoneInfo("Asia/Tehran"))
    j = jdatetime.date.fromgregorian(date=now.date())
    return now, j


def ask(prompt):
    messages = [{"role": "user", "content": prompt}]
    data = {}
    for _ in range(5):
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 3000,
                "system": SYSTEM,
                "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
                "messages": messages,
            },
            timeout=300,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("stop_reason") == "pause_turn":
            messages.append({"role": "assistant", "content": data["content"]})
            continue
        break
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()


def send(text):
    for i in range(0, len(text), 4000):
        chunk = text[i:i + 4000]
        payload = {"chat_id": CHANNEL, "text": chunk, "parse_mode": "HTML",
                   "disable_web_page_preview": True}
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=60)
        if r.status_code == 400:  # اگر تگ HTML خراب بود، بدون فرمت بفرست
            payload.pop("parse_mode")
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=60)
        r.raise_for_status()


def calendar_post():
    now, j = today_info()
    header = (
        f"📅 <b>{WEEKDAYS[j.weekday()]} {j.day} {MONTHS[j.month - 1]} {j.year}</b>\n"
        f"{now.strftime('%d %B %Y')}\n"
    )
    extra = ask(
        f"تاریخ امروز: {j.day} {MONTHS[j.month - 1]} {j.year} شمسی ({now.date()}). "
        "مناسبت‌های رسمی و تعطیلی امروز ایران (شمسی، قمری، ملی) را از تقویم معتبر پیدا کن "
        "و در حداکثر ۳ خط بنویس. اگر مناسبت یا تعطیلی نبود فقط بنویس «امروز روز کاری عادی است». "
        "فقط همان مناسبت‌ها را بنویس، بدون مقدمه."
    )
    send(header + "\n" + extra)


def market_post():
    _, j = today_info()
    text = ask(
        f"امروز {j.day} {MONTHS[j.month - 1]} {j.year} است. وضعیت امروز بازار آهن ایران را بررسی کن: "
        "قیمت و روند میلگرد، تیرآهن، ورق و شمش (بازار آزاد و در صورت وجود بورس کالا)، "
        "نرخ دلار و تاثیرش، و تغییر نسبت به روز قبل. "
        "خروجی: تیتر «📊 بازار آهن امروز»، سپس ۴ تا ۶ خط عدد و روند، سپس یک جمع‌بندی دو خطی بی‌طرف. "
        "اگر عدد دقیق پیدا نشد، بازه یا «داده معتبر یافت نشد» بنویس."
    )
    send(text)


def news_post():
    _, j = today_info()
    text = ask(
        f"امروز {j.day} {MONTHS[j.month - 1]} {j.year} است. اخبار ۲۴ ساعت اخیر صنعت آهن و فولاد "
        "ایران (تولید، صادرات، مقررات، بورس کالا، انرژی) و جهان (قیمت جهانی، چین، تعرفه‌ها، سنگ‌آهن) "
        "را جستجو کن. مهم‌ترین ۳ خبر ایران و ۲ خبر جهان را انتخاب کن. "
        "خروجی: تیتر «📰 مهم‌ترین اخبار آهن و فولاد»، هر خبر در ۲ جمله با نام منبع."
    )
    send(text)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("morning", "all"):
        calendar_post()
        news_post()
    if mode in ("evening", "all"):
        market_post()
