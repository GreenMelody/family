import os
import json
import time
import logging
import schedule
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

os.environ |= {
    'http_proxy': '',
    'https_proxy': '',
    'no_proxy': 'localhost, 127.0.0.1'
}

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
INIT_URL = "http://127.0.0.1:5000"

# Selenium WebDriver 초기화
def initialize_webdriver():
    chrome_options = Options()
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument("--headless=old")
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--disable-webgl")
    # chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--start-maximized")
    # chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-usb-discovery")
    driver = webdriver.Chrome(options=chrome_options)
    # driver.set_window_position(-2000, 0)
    driver.get(INIT_URL)  # 프로그램 시작 시 초기 URL 접속
    time.sleep(3)
    logging.info(f"Initialized WebDriver and accessed {INIT_URL}")
    return driver

# 크롤링 함수
def crawl_url(driver, url):
    wait = WebDriverWait(driver, 5)

    try:
        driver.get(url)  # 기존 브라우저로 URL 변경
        product_name = wait.until(EC.presence_of_element_located((By.ID, "goodsNm"))).get_attribute("value")
        model_name = driver.find_element(By.ID, "mdlCode").get_attribute("value")
        image_url = driver.find_element(By.ID, "imgPath").get_attribute("value")
        options = driver.find_element(By.ID, "ga4OptionString").get_attribute("value")
        release_price = int(driver.find_element(By.ID, "originalSumPrice").get_attribute("value"))
        employee_price = int(driver.find_element(By.ID, "beforeBenefitPrice").get_attribute("value"))

        logging.info(f"="*50)
        logging.info(f"Crawling URL: {url}")
        logging.info(f"product_name: {product_name}")
        logging.info(f"model_name: {model_name}")
        logging.info(f"image_url: {image_url}")
        logging.info(f"options: {options}")
        logging.info(f"release_price: {release_price}")
        logging.info(f"employee_price: {employee_price}")
        logging.info(f"="*50)

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
        logging.info(f"NoSuchElementException : {e}")
        return {
            "status": "Failed",
            "error_message": f"Element not found"
        }
    except Exception as e:
        logging.info(f"Exception : {e}")
        return {
            "status": "Failed",
            "error_message": f"Unexpected error"
        }

# 크롤링 결과 A 서버에 전달
def send_crawl_results(results):
    res = {"results":results}
    script = f"""
    return fetch('{A_SERVER_URL}/api/crawl-result', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json'
        }},
        body: JSON.stringify({json.dumps(res)})
    }})
    .then(response => response.status)
    .catch(() => 500);
    """

    response = driver.execute_script(script)

    if response == 200:
        logging.info("Crawl results successfully sent to A server.")
    else:
        logging.error(f"Failed to send crawl results: {response}")

# URL 크롤링 작업
def crawl_task(driver, crawl_type):
    logging.info(f"Crawl type : {crawl_type}")

    script = f"""
    return fetch('{A_SERVER_URL}/api/url-list?type={crawl_type}',{{
        method: 'GET',
        headers: {{
            'Content-Type':'application/json'
        }}
    }})
    .then(response => {{
        return response.json().then(data => {{
            return {{
                status: response.status,
                statusText: response.statusText,
                data: data
            }};
        }});
    }})
    .catch(error => {{
        return {{
            status: 500,
            statusText: 'Internal Server Error',
            error: error.toString()
        }};
    }});
    """
    response = driver.execute_script(script)

    if response["status"] != 200:
        logging.error(f"Error: HTTP {response['status']} - {response['statusText']}")
        if "error" in response:
            logging.error(f"Error details: {response['error']}")
        return

    urls = response["data"].get("urls", [])
    logging.info(f"urls:{urls}")
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

    logging.info(f"results:{results}")
    # A 서버에 결과 전달
    if results:
        send_crawl_results(results)
    else:
        logging.info(f"No results to send")

# 크롤링 일정 예약
def schedule_crawling(driver):
    crawl_time=["02:00", "08:00", "16:00", "22:00"]

    # 2시: active와 pending 크롤링
    schedule.every().day.at(crawl_time[0]).do(crawl_task, driver, crawl_type="all")
    schedule.every().day.at(crawl_time[0]).do(crawl_task, driver, crawl_type="pending")
    # 8시, 16시, 22시: fail과 pending 크롤링
    schedule.every().day.at(crawl_time[1]).do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at(crawl_time[1]).do(crawl_task, driver, crawl_type="pending")

    schedule.every().day.at(crawl_time[2]).do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at(crawl_time[2]).do(crawl_task, driver, crawl_type="pending")

    schedule.every().day.at(crawl_time[3]).do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at(crawl_time[3]).do(crawl_task, driver, crawl_type="pending")

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    driver = initialize_webdriver()

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
            elif command.lower() in ["crawl-all"]:
                logging.info(f"Crawl urls whose status is active using command")
                crawl_task(driver, "all")
            elif command.lower() in ["crawl-pending"]:
                logging.info(f"Crawl urls whose status is pending using command")
                crawl_task(driver, "pending")
            elif command.lower() in ["crawl-retry"]:
                logging.info(f"Crawl urls whose status is fail using command")
                crawl_task(driver, "retry")
            else:
                print(f"crawl-all : Crawl urls whose status is active using command")
                print(f"crawl-pending : Crawl urls whose status is pending using command")
                print(f"crawl-retry : Crawl urls whose status is fail using command")
                print(f"exit : After clearing the schedule and quit the driver, exit this program")
                print(f"quit : Same as exit command")

    except KeyboardInterrupt:
        logging.info("Exiting due to interrupt...")
        schedule.clear()
    finally:
        logging.info("Closing WebDriver...")
        if driver:
            driver.quit()
        logging.info("WebDriver closed.")
