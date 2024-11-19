from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

app = Flask(__name__)
DATABASE = "product_data.db"

API_KEY = "your_shared_secret_key"

# 허용된 도메인 설정
ALLOWED_DOMAIN = "www.example.com"

# 데이터베이스 연결 함수
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Row 객체로 반환
    return conn

# URL 유효성 검사
def validate_and_format_url(input_url):
    if not input_url.strip():
        return {"valid": False, "message": "상품 페이지 URL을 입력해주세요."}

    # URL이 http:// 또는 https://로 시작하지 않을 경우 https:// 추가
    if not input_url.startswith(("http://", "https://")):
        input_url = "https://" + input_url

    # URL 파싱
    parsed_url = urlparse(input_url)

    # 도메인 검사
    if parsed_url.netloc != ALLOWED_DOMAIN:
        return {"valid": False, "message": f"올바르지 않은 도메인입니다. {ALLOWED_DOMAIN}의 상품 페이지 URL을 입력해주세요."}

    return {"valid": True, "url": input_url}

# 기본 페이지 렌더링
@app.route("/")
def index():
    return render_template("index.html")

@app.before_request
def verify_api_key():
    # static 파일 요청 및 일반 사용자 웹 요청은 제외
    if request.endpoint in ["index", "static"]:
        return

    # API 요청에만 API 키 검증
    if request.endpoint.startswith("api"):
        api_key = request.headers.get("API-Key")
        if api_key != API_KEY:
            return jsonify({"error": "Invalid API Key"}), 403

# URL 상태 확인 API
# URL 상태 확인 API
@app.route("/api/url-status", methods=["GET"])
def url_status():
    url = request.args.get("url")
    if not url:
        return jsonify({"status": "error", "message": "URL을 입력해주세요."}), 400

    validation_result = validate_and_format_url(url)
    if not validation_result["valid"]:
        return jsonify({"status": "error", "message": validation_result["message"]}), 400

    formatted_url = validation_result["url"]

    conn = get_db_connection()
    cur = conn.cursor()

    # URL 데이터 가져오기
    cur.execute("SELECT * FROM url WHERE url = ?", (formatted_url,))
    url_row = cur.fetchone()

    if not url_row:
        # URL이 데이터베이스에 없으면 추가
        cur.execute("""
            INSERT INTO url (url, status, added_date) VALUES (?, 'pending', DATETIME('now'))
        """, (formatted_url,))
        url_id = cur.lastrowid

        # user_request에 요청 추가
        cur.execute("""
            INSERT INTO user_request (url_id, status, requested_at) VALUES (?, 'Pending', DATETIME('now'))
        """, (url_id,))

        conn.commit()
        conn.close()

        # 사용자에게 데이터 수집 시작 메시지 전달
        return jsonify({
            "status": "pending",
            "message": "해당 URL은 수집된 데이터가 없습니다. 지금부터 데이터 수집을 시작합니다."
        })

    # URL이 이미 데이터베이스에 있는 경우 상태별 처리
    if url_row["status"] == "active":
        cur.execute("SELECT * FROM product WHERE url_id = ?", (url_row["url_id"],))
        product = cur.fetchone()

        cur.execute("""
            SELECT date_recorded AS date, release_price, employee_price
            FROM price_history WHERE product_id = ?
            ORDER BY date_recorded
        """, (product["product_id"],))
        prices = [dict(row) for row in cur.fetchall()]

        conn.close()
        return jsonify({
            "status": "active",
            "start_date": url_row["added_date"],
            "product_name": product["product_name"],
            "image_url": product["image_url"],
            "model_name": product["model_name"],
            "options": product["options"],
            "product_url": url_row["url"],
            "prices": prices
        })
    elif url_row["status"] == "inactive":
        cur.execute("SELECT * FROM product WHERE url_id = ?", (url_row["url_id"],))
        product = cur.fetchone()

        cur.execute("""
            SELECT date_recorded AS date, release_price, employee_price
            FROM price_history WHERE product_id = ?
            ORDER BY date_recorded
        """, (product["product_id"],))
        prices = [dict(row) for row in cur.fetchall()]

        conn.close()
        return jsonify({
            "status": "inactive",
            "message": "해당 URL은 3일 이상 데이터 수집이 정상적이지 않아 더 이상 업데이트 되지 않습니다. 이전 데이터만 확인이 가능합니다.",
            "product_name": product["product_name"],
            "prices": prices,
            "image_url": product["image_url"],
            "model_name": product["model_name"],
            "options": product["options"],
            "product_url": url_row["url"]
        })
    elif url_row["status"] == "pending":
        conn.close()
        return jsonify({
            "status": "pending",
            "message": "해당 URL은 데이터 수집 대기 중입니다."
        })

# URL 데이터 요청 API (날짜 범위)
@app.route("/api/url-data", methods=["GET"])
def url_data():
    url = request.args.get("url")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    conn = get_db_connection()
    cur = conn.cursor()

    # URL에 해당하는 product_id 찾기
    cur.execute("""
        SELECT product_id FROM product
        WHERE url_id = (SELECT url_id FROM url WHERE url = ?)
    """, (url,))
    product_row = cur.fetchone()

    if not product_row:
        conn.close()
        return jsonify({"status": "error", "message": "URL에 해당하는 상품을 찾을 수 없습니다."}), 404

    product_id = product_row["product_id"]

    # 가격 데이터 가져오기
    cur.execute("""
        SELECT date_recorded AS date, release_price, employee_price
        FROM price_history
        WHERE product_id = ? AND date_recorded BETWEEN ? AND ?
        ORDER BY date_recorded
    """, (product_id, start_date, end_date))
    prices = [dict(row) for row in cur.fetchall()]

    conn.close()
    return jsonify({"status": "success", "prices": prices})

# B 서버: URL 리스트 제공
@app.route("/api/url-list", methods=["GET"])
def url_list():
    type_param = request.args.get("type", "all")
    conn = get_db_connection()
    cur = conn.cursor()

    if type_param == "retry":
        # 실패한 URL 가져오기
        cur.execute("""
            SELECT url_id, url
            FROM url
            WHERE status = 'active'
              AND url_id IN (
                  SELECT url_id
                  FROM crawl_log
                  WHERE status = 'Failed'
                  GROUP BY url_id
                  HAVING COUNT(*) >= 1
              )
        """)
    else:
        # 전체 URL 가져오기
        cur.execute("SELECT url_id, url FROM url WHERE status = 'active'")

    urls = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify({"urls": urls})

# B 서버: 크롤링 결과 저장
@app.route("/api/crawl-result", methods=["POST"])
def crawl_result():
    results = request.json.get("results", [])
    conn = get_db_connection()
    cur = conn.cursor()

    for result in results:
        url_id = result["url_id"]
        status = result["status"]
        error_message = result.get("error_message")
        data = result.get("data")

        if status == "Success":
            # 성공 처리
            product_name = data["product_name"]
            model_name = data["model_name"]
            image_url = data["image_url"]
            options = data["options"]
            release_price = data["release_price"]
            employee_price = data["employee_price"]

            # 상품 정보 저장
            cur.execute("""
                INSERT OR IGNORE INTO product (url_id, product_name, image_url, model_name, options)
                VALUES (?, ?, ?, ?, ?)
            """, (url_id, product_name, image_url, model_name, options))

            # 가격 정보 저장
            cur.execute("""
                INSERT INTO price_history (product_id, date_recorded, release_price, employee_price)
                VALUES ((SELECT product_id FROM product WHERE url_id = ?), DATE('now'), ?, ?)
            """, (url_id, release_price, employee_price))

            # 실패 횟수 초기화 및 마지막 시도 시간 갱신
            cur.execute("""
                UPDATE url
                SET fail_count = 0, last_attempt = DATETIME('now')
                WHERE url_id = ?
            """, (url_id,))

        elif status == "Failed":
            # 실패 처리: 실패 횟수 증가 및 마지막 시도 시간 갱신
            cur.execute("""
                UPDATE url
                SET fail_count = fail_count + 1, last_attempt = DATETIME('now')
                WHERE url_id = ?
            """, (url_id,))

            # 크롤링 실패 기록
            cur.execute("""
                INSERT INTO crawl_log (url_id, attempt_time, status, error_message)
                VALUES (?, DATETIME('now'), 'Failed', ?)
            """, (url_id, error_message))

            # 실패 횟수가 3 이상이고 최근 3일 동안 실패한 경우 inactive 상태로 변경
            cur.execute("""
                UPDATE url
                SET status = 'inactive'
                WHERE url_id = ? AND fail_count >= 3 AND last_attempt <= DATETIME('now', '-3 days')
            """, (url_id,))

    conn.commit()
    conn.close()
    return jsonify({"message": "Crawl results processed successfully."})

if __name__ == "__main__":
    app.run(debug=True)
