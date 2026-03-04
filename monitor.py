import os
import time
import random
import requests
from bs4 import BeautifulSoup


# 상품 페이지 URL
PRODUCT_URL = "https://brand.naver.com/sonystore/products/12936145763"

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def send_telegram(msg):
    """텔레그램 메시지 전송 (429, 기타 에러도 감당)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        res = requests.post(url, data=data, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print("텔레그램 전송 실패:", e, flush=True)
        return None


def fetch_html():
    """상품 페이지 HTML 가져오기"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    res = requests.get(PRODUCT_URL, headers=headers, timeout=10)
    res.raise_for_status()
    return res.text


def is_purchase_button_visible(html):
    """네이버 브랜드스토어에서 '구매하기' 버튼이 있는지 확인"""
    soup = BeautifulSoup(html, "html.parser")
    btn = soup.select_one("div.sys_chk_buy a .blind")
    if btn:
        text = btn.get_text(strip=True)
        return "구매하기" in text
    return False


def is_soldout_text_visible(html):
    """"현재 구매하실 수 없는 상품" 같은 품절 문구가 있는지 확인"""
    soup = BeautifulSoup(html, "html.parser")
    strong = soup.select_one("strong")
    if strong:
        text = strong.get_text(strip=True)
        return "현재 구매하실 수 없는 상품" in text
    return False


def is_available(html):
    """상품이 구매 가능 상태인지 bool로 반환"""
    btn = is_purchase_button_visible(html)
    if not btn:
        return False  # 버튼이 없으면 품절
    soldout = is_soldout_text_visible(html)
    return btn and not soldout


print("네이버 브랜드스토어 재입고 모니터링 시작", flush=True)

last_status = None


while True:
    try:
        html = fetch_html()
        current = is_available(html)
        print(f"HTML 구조 확인: 구매 가능 = {current}", flush=True)

        if last_status is None:
            # 최초 1회 체크
            last_status = current
            if current:
                send_telegram(
                    "🔥 네이버 브랜드스토어: 현재 상품이 구매 가능 상태입니다.\n"
                    f"👉 구매 페이지: {PRODUCT_URL}"
                )
        else:
            if current != last_status:
                if current:
                    send_telegram(
                        "🔥 네이버 브랜드스토어: 재입고(구매 가능) 상태로 변경됐어요!\n"
                        f"👉 구매 페이지: {PRODUCT_URL}"
                    )
                else:
                    send_telegram("📦 네이버 브랜드스토어: 상품이 품절 상태로 변경됐어요.")
                last_status = current

        # 정상 종료 시, 60~90초 사이 랜덤 대기
        time.sleep(60 + random.uniform(0, 30))

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("429 Too Many Requests: 10분간 대기 후 재시도", flush=True)
            send_telegram("429 Too Many Requests: 너무 빠른 요청으로 인해 10분간 대기합니다.")
            time.sleep(600)   # 10분 대기
        else:
            print("HTTP 에러:", e, flush=True)
            time.sleep(30)    # 30초 대기 후 재시도

    except Exception as e:
        print("기타 에러:", e, flush=True)
        time.sleep(30)
