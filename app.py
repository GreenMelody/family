from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# 데이터베이스 연결 함수
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # 쿼리 결과를 dict처럼 사용하기 위함
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_product():
    url = request.json.get('url')
    conn = get_db_connection()
    cursor = conn.cursor()

    # URL이 DB에 있는지 확인
    cursor.execute("SELECT * FROM product WHERE url = ?", (url,))
    product = cursor.fetchone()

    if product:
        # URL이 DB에 있을 경우 해당 제품 정보와 가격 히스토리 반환
        cursor.execute("SELECT date, original_price, employee_price FROM price_history WHERE product_id = ?", (product['product_id'],))
        price_history = cursor.fetchall()
        conn.close()

        return jsonify({
            'exists': True,
            'product': {
                'product_id': product['product_id'],
                'name': product['name'],
                'model': product['model'],
                'options': product['options'],
                'image_url': product['image_url']
            },
            'price_history': [{'date': row['date'], 'original_price': row['original_price'], 'employee_price': row['employee_price']} for row in price_history]
        })
    else:
        # URL이 DB에 없을 경우 사용자에게 데이터 수집 여부를 묻도록 안내
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
