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
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

os.environ |= {
    'http_proxy': '',
    'https_proxy': '',
    'no_proxy': 'localhost, 127.0.0.1'
}

# A 서버 정보
A_SERVER_URL = "http://127.0.0.1:5000"
A_SERVER_URL = "http://127.0.0.1:5000"
INIT_URL = "http://127.0.0.1:5000"

API_KEY = ""

if "dev" in A_SERVER_URL:
    icon_color = "red"
else:
    icon_color = "blue"

# Selenium WebDriver 초기화
def initialize_webdriver():
    logging.info(f"== initialize_webdriver ==")
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
    driver.execute_script(f"window.open('{A_SERVER_URL}');")  # 새탭에 접속
    time.sleep(3)
    logging.info(f"Initialized WebDriver and accessed {INIT_URL}")
    return driver

# 크롤링 함수
def crawl_url(driver, url):
    logging.info(f"== crawl_url ==")
    driver.switch_to.window(driver.window_handles[0])
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
        logging.error(f"NoSuchElementException : {e}")
        logging.error(f"Error url : {url}")
        return {
            "status": "Failed",
            "error_message": f"Element not found"
        }
    except Exception as e:
        logging.error(f"Exception : {e}")
        logging.error(f"Error url : {url}")
        return {
            "status": "Failed",
            "error_message": f"Unexpected error"
        }

# 크롤링 결과 A 서버에 전달
def send_crawl_results(results):
    logging.info(f"== send_crawl_results ==")
    driver.switch_to.window(driver.window_handles[1])
    logging.info(f"Switch tab : {driver.current_url}")

    res = {"results":results}
    script = f"""
    return fetch('{A_SERVER_URL}/api/crawl-result', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json',
            'API-Key':'{API_KEY}'
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
    logging.info(f"== crawl_task ==")
    logging.info(f"Crawl type : {crawl_type}")
    icon.icon = create_image(64, 64, icon_color, "green")

    driver.switch_to.window(driver.window_handles[1])
    logging.info(f"Switch tab : {driver.current_url}")

    try:
        script = f"""
        return fetch('{A_SERVER_URL}/api/url-list?type={crawl_type}',{{
            method: 'GET',
            headers: {{
                'Content-Type':'application/json',
                'API-Key':'{API_KEY}'
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
    finally:
        icon.icon = create_image(64, 64, icon_color, "white")

def request_generate_product_list(driver):
    logging.info(f"== request_generate_product_list ==")
    driver.switch_to.window(driver.window_handles[1])
    logging.info(f"Switch tab : {driver.current_url}")

    script = f"""
    return fetch('{A_SERVER_URL}/api/generate-product-list', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/json',
            'API-Key':'{API_KEY}'
        }}
    }})
    .then(response => {{
        if (response.ok) {{
            return response.json();
        }} else {{
            throw new Error('HTTP ' + response.status + ' ' + response.statusText);
        }}
    }})
    .then(data => {{
        return {{status: 'success', data: data}};
    }})
    .catch(error => {{
        return {{status: 'error', message: error.toString()}};
    }});
    """
    try:
        response = driver.execute_script(script)
        if response["status"] == "success":
            logging.info(f"Successfully requested product list generation: {response['data']}")
        else:
            logging.error(f"Failed to generate product list: {response['message']}")
    except Exception as e:
        logging.error(f"Error while requesting product list generation: {e}")

# ping
def ping(driver):
    logging.info(f"== ping ==")
    driver.switch_to.window(driver.window_handles[1])
    logging.info(f"Switch tab : {driver.current_url}")

    script = f"""
    return fetch('{A_SERVER_URL}/api/ping',{{
        method: 'GET',
        headers: {{
            'Content-Type':'application/json'
        }}
    }})
    .then(response => response.status)
    .catch(() => 500);
    """
    response = driver.execute_script(script)

    if response == 200:
        logging.info(f"ping success")
        icon.icon = create_image(64, 64, icon_color, "green")
        time.sleep(1)
        icon.icon = create_image(64, 64, icon_color, "white")
    else:
        logging.error(f"ping failed")
        icon.icon = create_image(64, 64, icon_color, "red")
        time.sleep(1)
        icon.icon = create_image(64, 64, icon_color, "white")

# 크롤링 일정 예약
def schedule_crawling(driver):
    crawl_time = ["02:00", "08:00", "16:00", "22:00"]
    logging.info(f"crawl_time : {crawl_time}")

    # 2시: active와 pending 크롤링
    schedule.every().day.at(crawl_time[0]).do(crawl_task, driver, crawl_type="all")
    schedule.every().day.at(crawl_time[0]).do(crawl_task, driver, crawl_type="pending")
    schedule.every().day.at(crawl_time[0]).do(request_generate_product_list, driver)
    # 8시, 16시, 22시: fail과 pending 크롤링
    schedule.every().day.at(crawl_time[1]).do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at(crawl_time[1]).do(crawl_task, driver, crawl_type="pending")
    schedule.every().day.at(crawl_time[1]).do(request_generate_product_list, driver)

    schedule.every().day.at(crawl_time[2]).do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at(crawl_time[2]).do(crawl_task, driver, crawl_type="pending")
    schedule.every().day.at(crawl_time[2]).do(request_generate_product_list, driver)

    schedule.every().day.at(crawl_time[3]).do(crawl_task, driver, crawl_type="retry")
    schedule.every().day.at(crawl_time[3]).do(crawl_task, driver, crawl_type="pending")
    schedule.every().day.at(crawl_time[3]).do(request_generate_product_list, driver)

    while scheduler_running:
        schedule.run_pending()
        time.sleep(1)

driver = None
scheduler_running = True
scheduler_thread = None

# 트레이 아이콘용 이미지 생성
def create_image(width, height, color1, color2):
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        [(width // 4, height // 4), (width * 3 // 4, height * 3 // 4)], fill=color2
    )
    return image

def quit(icon):
    global scheduler_running
    logging.info(f"프로그램을 종료합니다.")
    schedule.clear()
    scheduler_running = False
    while scheduler_thread.is_alive():
        logging.info(f"wait till the thread end")
        time.sleep(1)
    logging.info(f"thread stopped")
    time.sleep(1)
    icon.stop()  # 트레이 아이콘 종료

# 크롤링 실행 메뉴
def manual_crawl(crawl_type):
    logging.info(f"Manual crawl requested for type: {crawl_type}")
    crawl_task(driver, crawl_type)

# 트레이 메뉴 구성
menu = Menu(
    MenuItem("Manual Crawl", Menu(
        MenuItem("Crawl All", lambda icon, item: manual_crawl("all")),
        MenuItem("Crawl Pending", lambda icon, item: manual_crawl("pending")),
        MenuItem("Crawl Retry", lambda icon, item: manual_crawl("retry")),
    )),
    MenuItem("Gen List", lambda icon, item: request_generate_product_list(driver)),
    MenuItem("Ping", lambda icon, item: ping(driver)),
    MenuItem("Quit", lambda icon, item: quit(icon)),
)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("app_B.log", encoding="utf-8")]
    )

    driver = initialize_webdriver()

    # 트레이 아이콘 생성
    icon = Icon(
        "Server B Crawler",
        icon=create_image(64, 64, icon_color, "white"),
        title="Server B",
        menu=menu,
    )

    try:
        scheduler_thread = threading.Thread(target=schedule_crawling, args=(driver,), daemon=True)
        scheduler_thread.start()
        logging.info(f"Scheduler thread started")
        icon.run()  # 트레이 아이콘 실행
    except KeyboardInterrupt:
        logging.info("Exiting due to interrupt...")
    finally:
        logging.info(f"Closing WebDriver...")
        if driver:
            driver.quit()
        logging.info(f"WebDriver closed.")
