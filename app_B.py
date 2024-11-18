import requests
import time
import schedule
from datetime import datetime
from bs4 import BeautifulSoup  # 크롤링용
import logging

# A 서버 URL 및 인증 키
A_SERVER_URL = "http://127.0.0.1:5000"  # A 서버 URL
API_KEY = "your_api_key_here"           # A 서버와 통신할 API 키

# 로그 설정
logging.basicConfig(
    filename="app_B.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def fetch_url_list(type="all"):
    """
    A 서버에서 URL 리스트 가져오기
    type: 'all' (1시 전체 크롤링), 'retry' (재시도 크롤링)
    """
    try:
        response = requests.get(
            f"{A_SERVER_URL}/api/url-list",
            headers={"Authorization": f"Bearer {API_KEY}"},
            params={"type": type}
        )
        if response.status_code == 200:
            return response.json().get("urls", [])
        else:
            logging.error(f"Failed to fetch URL list: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logging.error(f"Error fetching URL list: {e}")
        return []

def send_crawl_results(results):
    """
    크롤링 결과를 A 서버에 전송
    """
    try:
        response = requests.post(
            f"{A_SERVER_URL}/api/crawl-result",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={"results": results}
        )
        if response.status_code == 200:
            logging.info("Successfully sent crawl results to A server.")
        else:
            logging.error(f"Failed to send crawl results: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Error sending crawl results: {e}")

def crawl_url(url):
    """
    개별 URL 크롤링 수행
    """
    try:
        # 예시 크롤링 로직 (BeautifulSoup 사용)
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 크롤링 결과 예시
            product_name = soup.select_one("h1.product-title").text.strip()
            product_model = soup.select_one(".model-number").text.strip()
            product_image_url = soup.select_one("img.product-image")["src"]
            options = soup.select_one(".product-options").text.strip()
            release_price = float(soup.select_one(".release-price").text.strip().replace(",", ""))
            employee_price = float(soup.select_one(".employee-price").text.strip().replace(",", ""))

            return {
                "status": "Success",
                "data": {
                    "product_name": product_name,
                    "model_name": product_model,
                    "image_url": product_image_url,
                    "options": options,
                    "release_price": release_price,
                    "employee_price": employee_price
                }
            }
        else:
            return {"status": "Failed", "error_message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "Failed", "error_message": str(e)}

def perform_crawl(type="all"):
    """
    크롤링 수행 (전체 또는 재시도)
    """
    logging.info(f"Starting crawl for type: {type}")
    url_list = fetch_url_list(type)
    results = []

    for url_data in url_list:
        url_id = url_data["url_id"]
        url = url_data["url"]

        logging.info(f"Starting crawl for URL: {url}")
        crawl_result = crawl_url(url)

        if crawl_result["status"] == "Success":
            results.append({
                "url_id": url_id,
                "status": "Success",
                "error_message": None,
                "data": crawl_result["data"]
            })
            logging.info(f"Successfully crawled URL: {url}")
        else:
            results.append({
                "url_id": url_id,
                "status": "Failed",
                "error_message": crawl_result["error_message"]
            })
            logging.error(f"Failed to crawl URL: {url} - Error: {crawl_result['error_message']}")

    send_crawl_results(results)
    logging.info(f"Completed crawl for type: {type}")

# 스케줄링
schedule.every().day.at("01:00").do(lambda: perform_crawl(type="all"))  # 전체 크롤링
schedule.every().day.at("07:00").do(lambda: perform_crawl(type="retry"))  # 재시도 크롤링
schedule.every().day.at("13:00").do(lambda: perform_crawl(type="retry"))  # 재시도 크롤링
schedule.every().day.at("19:00").do(lambda: perform_crawl(type="retry"))  # 재시도 크롤링

if __name__ == "__main__":
    logging.info("B Server started.")
    while True:
        schedule.run_pending()
        time.sleep(1)


# 인증 추가
# API_KEY = "your_shared_secret_key"

# def get_url_list_from_a_server():
#     headers = {"API-Key": API_KEY}
#     response = requests.get("http://A_SERVER_ADDRESS/api/url-list", headers=headers)
#     if response.status_code == 403:
#         print("API Key 인증 실패")
#         return None
#     return response.json()