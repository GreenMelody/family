from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse
import re

# 화이트리스트 정의
WHITELIST_DOMAINS = [
    r'^example\.com$',      # 정확히 example.com만 허용
    r'^.*\.example\.com$',  # example.com의 모든 하위 도메인 허용
    r'^exp\.com$',          # 정확히 exp.com만 허용
    r'^.*\.exp\.com$',      # exp.com의 모든 하위 도메인 허용
]

# 화이트리스트 확인 함수
def is_url_allowed(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc  # URL에서 도메인 추출
    for pattern in WHITELIST_DOMAINS:
        if re.match(pattern, domain):
            return True
    return False

def normalize_url(url):
    parsed = urlparse(url)
    scheme = parsed.scheme or 'http'  # 스킴이 없으면 기본값으로 'http' 사용
    netloc = parsed.netloc or parsed.path.split('/')[0]
    path = parsed.path if parsed.netloc else '/' + '/'.join(parsed.path.split('/')[1:])
    normalized = urlunparse((scheme, netloc, path, '', '', ''))
    return normalized.rstrip('/')  # 마지막 '/' 제거

def validate_url_or_reject(url, cursor):
    normalized_url = normalize_url(url)
    if not is_url_allowed(normalized_url):
        # 허용되지 않는 URL은 user_requests에 rejected로 기록
        requested_at = datetime.now()
        cursor.execute('''
            INSERT INTO user_requests (url, requested_at, status)
            VALUES (?, ?, 'rejected')
        ''', (normalized_url, requested_at))
        return False, "허용되지 않은 URL입니다."
    return True, normalized_url

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_product():
    data = request.json
    raw_url = data.get('url')

    conn = get_db_connection()
    cursor = conn.cursor()

    valid, result = validate_url_or_reject(raw_url, cursor)
    if not valid:
        conn.commit()
        conn.close()
        return jsonify({'exists': False, 'message': result}), 400

    url = result  # 정상화된 URL
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    # 상태와 요청 시간 조회
    cursor.execute('''
        SELECT status, requested_at 
        FROM user_requests 
        WHERE url = ? 
        ORDER BY requested_at DESC
        LIMIT 1
    ''', (url,))
    request_info = cursor.fetchone()

    status_message = None
    if request_info:
        status, requested_at = request_info['status'], request_info['requested_at']
        try:
            requested_date = datetime.strptime(requested_at, "%Y-%m-%d %H:%M:%S.%f").date().strftime('%Y년 %m월 %d일')
        except ValueError:  # 마이크로초가 없는 경우 처리
            requested_date = datetime.strptime(requested_at, "%Y-%m-%d %H:%M:%S").date().strftime('%Y년 %m월 %d일')

        if status == 'pending':
            status_message = f"{requested_date}에 수집 요청 받아 데이터 수집 대기 중인 URL입니다."
        elif status == 'in_progress':
            status_message = f"{requested_date}부터 데이터 수집 중인 URL입니다."
        elif status == 'completed':
            status_message = f"{requested_date}에 데이터 수집이 완료된 URL입니다."
        elif status == 'failed':
            status_message = f"{requested_date}에 데이터 수집이 실패한 URL입니다."
        elif status == 'rejected':
            status_message = f"{requested_date}에 허용되지 않은 URL로 수집 요청이 거부된 URL입니다."

    # 제품 데이터 조회
    cursor.execute("SELECT * FROM product WHERE url = ?", (url,))
    product = cursor.fetchone()

    if product:
        # 제품 데이터가 있으면 반환
        product_data = {
            'product_id': product['product_id'],
            'name': product['name'],
            'model': product['model'],
            'options': product['options'],
            'url': product['url'],
            'image_url': product['image_url']
        }

        cursor.execute('''
            SELECT date, original_price, employee_price 
            FROM price_history 
            WHERE product_id = ? AND date BETWEEN ? AND ?
            ORDER BY date
        ''', (product['product_id'], start_date, end_date))
        price_history = cursor.fetchall()

        price_history_data = [
            {'date': row['date'], 'original_price': row['original_price'], 'employee_price': row['employee_price']}
            for row in price_history
        ]

        conn.close()

        return jsonify({
            'exists': True,
            'product': product_data,
            'price_history': price_history_data,
            'status_message': status_message
        })
    else:
        conn.close()
        return jsonify({
            'exists': False,
            'message': "현재 해당 url에 대한 데이터가 없습니다. 해당 url에 대한 데이터를 수집하시겠습니까?",
            'status_message': status_message
        })

@app.route('/collect_data', methods=['POST'])
def collect_data():
    raw_url = request.json.get('url')
    url = normalize_url(raw_url)  # URL 표준화 적용

    conn = get_db_connection()
    cursor = conn.cursor()

    valid, result = validate_url_or_reject(raw_url, cursor)
    if not valid:
        conn.commit()
        conn.close()
        return jsonify({'message': result}), 400

    url = result  # 정상화된 URL

    # URL 중복 확인
    cursor.execute('''
        SELECT * FROM user_requests WHERE url = ? AND status = 'pending'
    ''', (url,))
    existing_request = cursor.fetchone()

    if existing_request:
        conn.close()
        return jsonify({'message': '이미 수집 대기 중인 URL입니다.'}), 200

    # 데이터 수집 요청 기록
    requested_at = datetime.now()
    cursor.execute('''
        INSERT INTO user_requests (url, requested_at, status)
        VALUES (?, ?, 'pending')
    ''', (url, requested_at))
    conn.commit()
    conn.close()

    return jsonify({'message': '데이터 수집 요청이 성공적으로 접수되었습니다.'})

if __name__ == '__main__':
    app.run(debug=True)
