from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse

def normalize_url(url):
    parsed = urlparse(url)
    scheme = parsed.scheme or 'http'  # 스킴이 없으면 기본값으로 'http' 사용
    netloc = parsed.netloc or parsed.path.split('/')[0]
    path = parsed.path if parsed.netloc else '/' + '/'.join(parsed.path.split('/')[1:])
    normalized = urlunparse((scheme, netloc, path, '', '', ''))
    return normalized.rstrip('/')  # 마지막 '/' 제거

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
    url = normalize_url(raw_url)  # URL 표준화 적용
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM product WHERE url = ?", (url,))
    product = cursor.fetchone()

    if product:
        cursor.execute('''
            SELECT date, original_price, employee_price 
            FROM price_history 
            WHERE product_id = ? AND date BETWEEN ? AND ?
            ORDER BY date
        ''', (product['product_id'], start_date, end_date))
        price_history = cursor.fetchall()
        conn.close()

        return jsonify({
            'exists': True,
            'product': {
                'product_id': product['product_id'],
                'name': product['name'],
                'model': product['model'],
                'options': product['options'],
                'url': product['url'],
                'image_url': product['image_url']
            },
            'price_history': [{'date': row['date'], 'original_price': row['original_price'], 'employee_price': row['employee_price']} for row in price_history]
        })
    else:
        conn.close()
        return jsonify({'exists': False, 'message': "현재 해당 url에 대한 데이터가 없습니다. 해당 url에 대한 데이터를 수집하시겠습니까?"})

@app.route('/collect_data', methods=['POST'])
def collect_data():
    url = request.json.get('url')
    requested_at = datetime.now()
    conn = get_db_connection()
    cursor = conn.cursor()

    # user_requests 테이블에 요청 데이터 삽입
    cursor.execute("INSERT INTO user_requests (url, requested_at, status) VALUES (?, ?, 'pending')", (url, requested_at))
    conn.commit()
    conn.close()
    
    return jsonify({'message': '데이터 수집 요청이 성공적으로 접수되었습니다.'})

if __name__ == '__main__':
    app.run(debug=True)
