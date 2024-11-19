import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import schedule
import time

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
    print(f"Initialized WebDriver and accessed {A_SERVER_URL}")
    return driver

# 크롤링 함수
def crawl_url(driver, url):
    print(f"Crawling URL: {url}")
    wait = WebDriverWait(driver, 5)
    try:
        driver.get(url)  # 기존 브라우저로 URL 변경
        product_name = wait.until(EC.presence_of_element_located((By.ID, "product_name"))).text
        model_name = driver.find_element(By.ID, "model_name").text
        image_url = driver.find_element(By.ID, "image_url").text
        options = driver.find_element(By.ID, "options").text
        release_price = float(driver.find_element(By.ID, "release_price").text.replace(",", ""))
        employee_price = float(driver.find_element(By.ID, "employee_price").text.replace(",", ""))
        print(f"product_name: {product_name}")
        print(f"model_name: {model_name}")
        print(f"image_url: {image_url}")
        print(f"options: {options}")
        print(f"release_price: {release_price}")
        print(f"employee_price: {employee_price}")
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
        print("Crawl results successfully sent to A server.")
    else:
        print(f"Failed to send crawl results: {response.status_code} - {response.text}")

# URL 크롤링 작업
def crawl_task(driver, crawl_type):
    headers = {"API-Key": API_KEY}
    response = requests.get(f"{A_SERVER_URL}/api/url-list?type={crawl_type}", headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch URLs: {response.status_code} - {response.text}")
        return

    urls = response.json().get("urls", [])
    if not urls:
        print(f"No URLs to crawl for type: {crawl_type}")
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
    schedule.every().day.at("02:00").do(crawl_task, driver, crawl_type="all")
    # 8시, 16시, 22시: fail과 pending 크롤링
    schedule.every().day.at("08:00").do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at("16:00").do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at("22:00").do(crawl_task, driver, crawl_type="retry")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # WebDriver 초기화
    driver = initialize_webdriver()

    try:
        # 즉시 실행 테스트
        crawl_task(driver, "all")
        crawl_task(driver, "pending")

        # 예약 작업 실행
        # schedule_crawling(driver)
    finally:
        driver.quit()  # 프로그램 종료 시 WebDriver 닫기
