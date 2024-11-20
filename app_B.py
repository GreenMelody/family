import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import schedule
import time
import threading
import logging

# 로그 설정
logging.basicConfig(
    level=logging.INFO,  # 로그 수준 설정
    format="%(asctime)s [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s",  # 출력 형식
    handlers=[
        logging.StreamHandler(),  # 콘솔 출력
        logging.FileHandler("app_B.log", encoding="utf-8"),  # 파일 출력
    ]
)

# A 서버 정보
A_SERVER_URL = "http://127.0.0.1:5000"
API_KEY = "your_shared_secret_key"

# Selenium WebDriver 초기화
def initialize_webdriver():
    chrome_options = Options()
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(A_SERVER_URL)  # 프로그램 시작 시 초기 URL 접속
    logging.info(f"Initialized WebDriver and accessed {A_SERVER_URL}")
    return driver

# 크롤링 함수
def crawl_url(driver, url):
    wait = WebDriverWait(driver, 5)
    try:
        driver.get(url)  # 기존 브라우저로 URL 변경
        product_name = wait.until(EC.presence_of_element_located((By.ID, "product_name"))).text
        model_name = driver.find_element(By.ID, "model_name").text
        image_url = driver.find_element(By.ID, "image_url").text
        options = driver.find_element(By.ID, "options").text
        release_price = float(driver.find_element(By.ID, "release_price").text.replace(",", ""))
        employee_price = float(driver.find_element(By.ID, "employee_price").text.replace(",", ""))

        logging.info(f"")
        logging.info(f"Crawling URL: {url}")
        logging.info(f"product_name: {product_name}")
        logging.info(f"model_name: {model_name}")
        logging.info(f"image_url: {image_url}")
        logging.info(f"options: {options}")
        logging.info(f"release_price: {release_price}")
        logging.info(f"employee_price: {employee_price}\n")

        return {
            "status": "Success",
            "data": {
                "product_name": product_name,
                "model_name": model_name,
                "image_url": image_url,
                "options": options,
                "release_price": release_price,
                "employee_price": employee_price,
            }
        }
    except NoSuchElementException as e:
        return {
            "status": "Failed",
            "error_message": f"Element not found: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "Failed",
            "error_message": f"Unexpected error: {str(e)}"
        }

# 크롤링 결과 A 서버에 전달
def send_crawl_results(results):
    url = f"{A_SERVER_URL}/api/crawl-result"
    headers = {"API-Key": API_KEY, "Content-Type": "application/json"}
    response = requests.post(url, json={"results": results}, headers=headers)
    if response.status_code == 200:
        logging.info("Crawl results successfully sent to A server.")
    else:
        logging.error(f"Failed to send crawl results: {response.status_code} - {response.text}")

# URL 크롤링 작업
def crawl_task(driver, crawl_type):
    headers = {"API-Key": API_KEY}
    response = requests.get(f"{A_SERVER_URL}/api/url-list?type={crawl_type}", headers=headers)

    if response.status_code != 200:
        logging.error(f"Failed to fetch URLs: {response.status_code} - {response.text}")
        return

    urls = response.json().get("urls", [])
    if not urls:
        logging.error(f"No URLs to crawl for type: {crawl_type}")
        return

    results = []
    for url_entry in urls:
        url_id = url_entry["url_id"]
        url = url_entry["url"]
        crawl_result = crawl_url(driver, url)
        crawl_result["url_id"] = url_id
        results.append(crawl_result)

    # A 서버에 결과 전달
    send_crawl_results(results)

# 크롤링 일정 예약
def schedule_crawling(driver):
    # 2시: active와 pending 크롤링
    schedule.every().day.at("10:46").do(crawl_task, driver, crawl_type="all")
    schedule.every().day.at("10:46").do(crawl_task, driver, crawl_type="pending")
    # 8시, 16시, 22시: fail과 pending 크롤링
    schedule.every().day.at("08:45").do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at("08:45").do(crawl_task, driver, crawl_type="pending")

    schedule.every().day.at("08:47").do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at("08:47").do(crawl_task, driver, crawl_type="pending")

    schedule.every().day.at("08:48").do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at("08:48").do(crawl_task, driver, crawl_type="pending")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # WebDriver 초기화
    driver = initialize_webdriver()
    crawl_task(driver, "all")

    try:
        # 예약 작업 실행
        logging.info("Type 'exit' to stop the scheduler.")
        scheduler_thread = threading.Thread(target=schedule_crawling, args=(driver,), daemon=True)
        scheduler_thread.start()

        # 사용자 입력 대기
        while True:
            command = input("> ")
            if command.lower() in ["exit", "quit"]:
                logging.info("Exiting...")
                schedule.clear()  # 모든 작업 정리
                break
    except KeyboardInterrupt:
        logging.info("Exiting due to interrupt...")
        schedule.clear()  # 안전하게 정리
    finally:
        logging.info("Closing WebDriver...")
        driver.quit()  # WebDriver 닫기
        logging.info("WebDriver closed.")

